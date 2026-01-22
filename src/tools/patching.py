"""
Tier 1 Atomic Tool: Patch Workflow (Phase 4 - Rewritten).

Implements robust patch preview and execution with human approval gates.
Based on industry best practices from Aider, Cursor, and Windsurf.

Edit Formats Supported:
1. Search/Replace Blocks (primary - most reliable)
2. Unified Diff (fallback - for complex multi-file changes)
3. Whole File (for new file creation)

Workflow:
1. preview_patch() - Parse diff/content, validate, return PatchPlan with preview
2. User approves/denies in UI (Master Graph pauses)
3. execute_patch() - Apply approved patch to disk

Safety:
- Project-root boundary enforcement
- Content verification before/after apply
- Atomic file updates (temp file + rename)
- RAG freshness updates after apply
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
import difflib
import re
import tempfile
import shutil

try:
    from unidiff import PatchSet
    UNIDIFF_AVAILABLE = True
except ImportError:
    UNIDIFF_AVAILABLE = False
    PatchSet = None

from src.agents.state import PatchPlan
from src.core.guardrails import validate_path
from src.core.file_manager import FileManager

logger = logging.getLogger(__name__)


# ============================================================================
# DIFF STATISTICS CALCULATION
# ============================================================================

def calculate_diff_stats(original: str, new_content: str) -> Tuple[int, int]:
    """
    Calculate accurate (+additions, -deletions) between two strings.

    PERMANENT FIX: Uses actual line count comparison for new file creation
    and file clearing, with SequenceMatcher for modifications to ensure
    accurate counts regardless of CRLF/LF differences.

    Args:
        original: Original file content (empty string for new files)
        new_content: New file content

    Returns:
        Tuple of (additions, deletions)
    """
    # Normalize line endings to avoid CRLF/LF mismatches
    original_normalized = original.replace('\r\n', '\n').replace('\r', '\n') if original else ''
    new_normalized = new_content.replace('\r\n', '\n').replace('\r', '\n') if new_content else ''

    original_lines = original_normalized.splitlines() if original_normalized.strip() else []
    new_lines = new_normalized.splitlines() if new_normalized.strip() else []

    # PERMANENT FIX: For new files, all lines are additions (use actual count)
    if not original_lines and new_lines:
        return (len(new_lines), 0)

    # PERMANENT FIX: For clearing file, all original lines are deletions
    if original_lines and not new_lines:
        return (0, len(original_lines))

    # For modifications, use SequenceMatcher for accurate line-by-line comparison
    matcher = difflib.SequenceMatcher(None, original_lines, new_lines)

    additions = 0
    deletions = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            deletions += (i2 - i1)
            additions += (j2 - j1)
        elif tag == 'delete':
            deletions += (i2 - i1)
        elif tag == 'insert':
            additions += (j2 - j1)
        # 'equal' means no change

    return (additions, deletions)


def generate_unified_diff(original: str, new_content: str, file_path: str) -> str:
    """
    Generate a proper unified diff string from original and new content.

    Args:
        original: Original file content
        new_content: New file content
        file_path: File path for diff header

    Returns:
        Unified diff string
    """
    original_lines = original.splitlines(keepends=True) if original else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []

    diff_lines = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f'a/{file_path}',
        tofile=f'b/{file_path}',
    )

    return ''.join(diff_lines)


# ============================================================================
# SEARCH/REPLACE BLOCK PARSER (Aider-style)
# ============================================================================

def parse_search_replace_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Parse Aider-style search/replace blocks from text.

    Format:
        filename.py
        <<<<<<< SEARCH
        old code here
        =======
        new code here
        >>>>>>> REPLACE

    Args:
        text: Text containing search/replace blocks

    Returns:
        List of dicts with {file_path, search, replace}
    """
    blocks = []

    # Pattern to match search/replace blocks
    # Captures: filename, search content, replace content
    pattern = r'^(\S+)\s*\n<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'

    matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)

    for match in matches:
        blocks.append({
            'file_path': match.group(1).strip(),
            'search': match.group(2),
            'replace': match.group(3),
        })

    return blocks


def apply_search_replace(
    content: str,
    search: str,
    replace: str,
    fuzzy: bool = True
) -> Tuple[str, bool]:
    """
    Apply a single search/replace operation to content.

    Implements fuzzy matching fallback when exact match fails.

    Args:
        content: Original file content
        search: Text to search for
        replace: Text to replace with
        fuzzy: Whether to use fuzzy matching if exact fails

    Returns:
        Tuple of (new_content, success)
    """
    # Try exact match first
    if search in content:
        # Replace only first occurrence to avoid unintended changes
        new_content = content.replace(search, replace, 1)
        return (new_content, True)

    if not fuzzy:
        return (content, False)

    # Fuzzy matching: normalize whitespace and try again
    def normalize_whitespace(s: str) -> str:
        """Normalize whitespace while preserving structure."""
        lines = s.splitlines()
        return '\n'.join(line.rstrip() for line in lines)

    normalized_search = normalize_whitespace(search)
    normalized_content = normalize_whitespace(content)

    if normalized_search in normalized_content:
        # Found with normalized whitespace - need to find original position
        # Use line-by-line matching
        search_lines = search.splitlines()
        content_lines = content.splitlines()

        # Find the starting line
        for i in range(len(content_lines) - len(search_lines) + 1):
            match = True
            for j, search_line in enumerate(search_lines):
                if content_lines[i + j].rstrip() != search_line.rstrip():
                    match = False
                    break

            if match:
                # Found match at line i
                new_lines = (
                    content_lines[:i] +
                    replace.splitlines() +
                    content_lines[i + len(search_lines):]
                )
                return ('\n'.join(new_lines), True)

    # No match found
    logger.warning(f"Could not find search block (first 50 chars): {search[:50]}...")
    return (content, False)


# ============================================================================
# PATCH PREVIEW
# ============================================================================

def preview_patch(
    diff: str,
    project_root: Path,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
) -> PatchPlan:
    """
    Preview a patch and validate it.

    Supports multiple formats:
    1. Search/Replace blocks (detected automatically)
    2. Unified diff (standard format)
    3. Direct content (when content parameter provided)

    Args:
        diff: Diff string (unified diff, search/replace blocks, or raw content)
        project_root: Project root directory (boundary enforcement)
        content: Optional direct content for whole-file writes
        file_path: Optional file path (required if content is provided)

    Returns:
        PatchPlan model with preview data including original and patched content

    Raises:
        ValueError: If diff is invalid or violates guardrails
    """
    logger.info("Previewing patch...")

    # ====================================================================
    # DETECT FORMAT AND PARSE
    # ====================================================================

    # Format 1: Direct content (whole file write)
    if content is not None and file_path is not None:
        return _preview_whole_file(content, file_path, project_root)

    # Format 2: Search/Replace blocks
    sr_blocks = parse_search_replace_blocks(diff)
    if sr_blocks:
        return _preview_search_replace(sr_blocks, project_root)

    # Format 3: Unified diff
    if diff.strip():
        return _preview_unified_diff(diff, project_root)

    raise ValueError("Empty or unrecognized patch format")


def _preview_whole_file(
    content: str,
    file_path: str,
    project_root: Path
) -> PatchPlan:
    """Preview a whole-file write operation."""
    # Validate path
    path_obj = Path(file_path)
    validate_path(path_obj, project_root, allow_read_only=False)

    full_path = project_root / file_path

    # Determine action and get original content
    if full_path.exists():
        try:
            original_content = full_path.read_text(encoding='utf-8')
        except Exception:
            original_content = ''
        action = "modify"
    else:
        original_content = ''
        action = "create"

    # Calculate diff stats
    additions, deletions = calculate_diff_stats(original_content, content)

    # Generate diff for preview
    diff_str = generate_unified_diff(original_content, content, file_path)

    changes_summary = f"+{additions} -{deletions} lines"
    rationale = f"{action.capitalize()} file: {changes_summary}"

    return PatchPlan(
        file_path=file_path,
        diff=diff_str,
        rationale=rationale,
        action=action,
        original_content=original_content,
        patched_content=content,
        additions=additions,
        deletions=deletions,
    )


def _preview_search_replace(
    blocks: List[Dict[str, Any]],
    project_root: Path
) -> PatchPlan:
    """Preview search/replace block operations."""
    if not blocks:
        raise ValueError("No search/replace blocks found")

    # For now, handle first file only (can extend for multi-file later)
    first_block = blocks[0]
    file_path = first_block['file_path']

    # Validate path
    path_obj = Path(file_path)
    validate_path(path_obj, project_root, allow_read_only=False)

    full_path = project_root / file_path

    # Read original content
    if full_path.exists():
        try:
            original_content = full_path.read_text(encoding='utf-8')
        except Exception:
            original_content = ''
        action = "modify"
    else:
        original_content = ''
        action = "create"

    # Apply all blocks for this file to generate preview
    patched_content = original_content
    for block in blocks:
        if block['file_path'] == file_path:
            patched_content, success = apply_search_replace(
                patched_content,
                block['search'],
                block['replace'],
                fuzzy=True
            )
            if not success:
                logger.warning(f"Search block not found in {file_path}")

    # Calculate diff stats
    additions, deletions = calculate_diff_stats(original_content, patched_content)

    # Generate diff for preview
    diff_str = generate_unified_diff(original_content, patched_content, file_path)

    changes_summary = f"+{additions} -{deletions} lines"
    rationale = f"Search/Replace {action}: {changes_summary}"

    return PatchPlan(
        file_path=file_path,
        diff=diff_str,
        rationale=rationale,
        action=action,
        original_content=original_content,
        patched_content=patched_content,
        additions=additions,
        deletions=deletions,
    )


def _preview_unified_diff(
    diff: str,
    project_root: Path
) -> PatchPlan:
    """Preview a unified diff."""
    if not diff.strip():
        raise ValueError("Empty diff provided")

    # Parse to extract file info and validate
    touched_files, primary_file, action = _parse_diff_metadata(diff)

    # Validate all paths
    for file_path in touched_files:
        path_obj = Path(file_path)
        validate_path(path_obj, project_root, allow_read_only=False)

    full_path = project_root / primary_file

    # Read original content
    if full_path.exists():
        try:
            original_content = full_path.read_text(encoding='utf-8')
        except Exception:
            original_content = ''
    else:
        original_content = ''

    # Apply diff to generate patched content preview
    patched_content = _apply_diff_to_content(diff, original_content, primary_file)

    # Calculate accurate diff stats
    additions, deletions = calculate_diff_stats(original_content, patched_content)

    changes_summary = f"{len(touched_files)} file(s): +{additions} -{deletions}"
    rationale = f"Patch {action}: {changes_summary}"

    return PatchPlan(
        file_path=primary_file,
        diff=diff,
        rationale=rationale,
        action=action,
        original_content=original_content,
        patched_content=patched_content,
        additions=additions,
        deletions=deletions,
    )


def _parse_diff_metadata(diff: str) -> Tuple[List[str], str, str]:
    """
    Parse diff to extract file paths and action type.

    Returns:
        Tuple of (touched_files, primary_file, action)
    """
    touched_files = []
    source_file = None
    target_file = None

    for line in diff.split('\n'):
        if line.startswith('--- '):
            parts = line.split()
            if len(parts) >= 2:
                source_file = parts[1].lstrip('a/')
        elif line.startswith('+++ '):
            parts = line.split()
            if len(parts) >= 2:
                target_file = parts[1].lstrip('b/')
                if target_file and target_file != '/dev/null':
                    if target_file not in touched_files:
                        touched_files.append(target_file)

    if not touched_files:
        raise ValueError("Could not parse file paths from diff")

    primary_file = touched_files[0]

    # Determine action
    if source_file == '/dev/null':
        action = "create"
    elif target_file == '/dev/null':
        action = "delete"
    else:
        action = "modify"

    return touched_files, primary_file, action


def _apply_diff_to_content(diff: str, original: str, file_path: str) -> str:
    """
    Apply unified diff to original content to generate patched content.

    Uses line-by-line application with context matching.
    """
    if UNIDIFF_AVAILABLE and PatchSet is not None:
        try:
            return _apply_diff_unidiff(diff, original)
        except Exception as e:
            logger.warning(f"unidiff application failed: {e}, using simple parser")

    return _apply_diff_simple(diff, original)


def _apply_diff_unidiff(diff: str, original: str) -> str:
    """Apply diff using unidiff library."""
    patchset = PatchSet(diff)

    if not patchset:
        return original

    patched_file = patchset[0]

    # Handle new file creation
    source = patched_file.source_file.lstrip('a/') if hasattr(patched_file, 'source_file') else ''
    if source == '/dev/null' or not original.strip():
        # New file - extract all additions
        lines = []
        for hunk in patched_file:
            for line in hunk:
                if line.is_added:
                    lines.append(line.value.rstrip('\n'))
        return '\n'.join(lines)

    # Apply hunks to existing content
    original_lines = original.splitlines()
    result_lines = original_lines.copy()

    # Process hunks in reverse order to maintain line numbers
    hunks = list(patched_file)
    for hunk in reversed(hunks):
        # Calculate the range to modify
        start = max(0, hunk.source_start - 1)
        length = hunk.source_length

        # Build replacement lines
        new_lines = []
        for line in hunk:
            if line.is_context or line.is_added:
                new_lines.append(line.value.rstrip('\n'))

        # Replace the range
        result_lines[start:start + length] = new_lines

    return '\n'.join(result_lines)


def _apply_diff_simple(diff: str, original: str) -> str:
    """Simple diff application - extracts additions and context."""
    lines = diff.split('\n')
    content_lines = []

    # For new files, just extract additions
    if not original.strip():
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                content_lines.append(line[1:])
        return '\n'.join(content_lines) if content_lines else original

    # For modifications, use additions + context
    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            content_lines.append(line[1:])
        elif line.startswith(' '):
            content_lines.append(line[1:])

    return '\n'.join(content_lines) if content_lines else original


# ============================================================================
# PATCH EXECUTION
# ============================================================================

def execute_patch(
    plan: PatchPlan,
    project_root: Path,
    rag_manager: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Execute an approved patch plan.

    Uses the pre-computed patched_content from preview for reliable application.
    Falls back to diff-based application if patched_content not available.

    Args:
        plan: Approved PatchPlan from preview_patch()
        project_root: Project root directory
        rag_manager: Optional RAGManager for freshness updates

    Returns:
        Dict with keys:
            - status: "success" | "error" | "no_change"
            - files_modified: List[str]
            - summary: str
            - error: Optional[str]
    """
    logger.info(f"Executing patch: {plan.action} {plan.file_path}")

    try:
        full_path = project_root / plan.file_path
        file_manager = FileManager(str(project_root))

        # ====================================================================
        # GET CONTENT TO WRITE
        # ====================================================================

        # Prefer pre-computed patched_content (from preview)
        if hasattr(plan, 'patched_content') and plan.patched_content is not None:
            new_content = plan.patched_content
        else:
            # Fallback: apply diff to current content
            if full_path.exists():
                original = full_path.read_text(encoding='utf-8')
            else:
                original = ''
            new_content = _apply_diff_to_content(plan.diff, original, plan.file_path)

        # ====================================================================
        # VERIFY CHANGE IS MEANINGFUL
        # ====================================================================

        if full_path.exists():
            current_content = full_path.read_text(encoding='utf-8')
        else:
            current_content = ''

        if new_content == current_content:
            logger.warning(f"Patch would result in no change to {plan.file_path}")
            return {
                "status": "no_change",
                "files_modified": [],
                "summary": f"No actual changes to apply to {plan.file_path}",
            }

        # ====================================================================
        # HANDLE DELETE ACTION
        # ====================================================================

        if plan.action == "delete":
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Deleted file: {plan.file_path}")
                return {
                    "status": "success",
                    "files_modified": [plan.file_path],
                    "summary": f"Deleted {plan.file_path}",
                }
            else:
                return {
                    "status": "no_change",
                    "files_modified": [],
                    "summary": f"File {plan.file_path} does not exist",
                }

        # ====================================================================
        # ATOMIC WRITE
        # ====================================================================

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first, then rename (atomic on most systems)
        temp_dir = full_path.parent
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=temp_dir,
            delete=False,
            suffix='.tmp'
        ) as tmp:
            tmp.write(new_content)
            tmp_path = Path(tmp.name)

        # Atomic rename
        shutil.move(str(tmp_path), str(full_path))

        logger.info(f"Applied patch to {plan.file_path}")

        # ====================================================================
        # VERIFY WRITE
        # ====================================================================

        written_content = full_path.read_text(encoding='utf-8')
        if written_content != new_content:
            logger.error("Written content doesn't match expected!")
            return {
                "status": "error",
                "files_modified": [],
                "summary": "Write verification failed",
                "error": "Content mismatch after write",
            }

        # ====================================================================
        # RAG UPDATE
        # ====================================================================

        if rag_manager:
            try:
                rag_manager.update_file(full_path)
                logger.info(f"RAG updated for: {plan.file_path}")
            except Exception as e:
                logger.warning(f"RAG update failed: {e}")

        # Calculate final stats
        additions, deletions = calculate_diff_stats(current_content, new_content)

        return {
            "status": "success",
            "files_modified": [plan.file_path],
            "summary": f"Applied patch to {plan.file_path} (+{additions} -{deletions})",
        }

    except Exception as e:
        logger.error(f"Patch execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "files_modified": [],
            "summary": f"Patch execution failed: {str(e)}",
            "error": str(e),
        }


# ============================================================================
# CONTENT-BASED OPERATIONS (for CrewAI/direct writes)
# ============================================================================

def preview_content_write(
    file_path: str,
    content: str,
    project_root: Path
) -> PatchPlan:
    """
    Preview a direct content write operation.

    Used when we have full file content (e.g., from CrewAI code extraction).

    Args:
        file_path: Target file path
        content: Full content to write
        project_root: Project root directory

    Returns:
        PatchPlan with preview data
    """
    return _preview_whole_file(content, file_path, project_root)


def execute_content_write(
    file_path: str,
    content: str,
    project_root: Path,
    rag_manager: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Execute a direct content write.

    Bypasses diff parsing for cases where we have full content.

    Args:
        file_path: Target file path
        content: Full content to write
        project_root: Project root directory
        rag_manager: Optional RAGManager

    Returns:
        Result dict with status, files_modified, summary
    """
    plan = preview_content_write(file_path, content, project_root)
    return execute_patch(plan, project_root, rag_manager)


__all__ = [
    "preview_patch",
    "execute_patch",
    "preview_content_write",
    "execute_content_write",
    "calculate_diff_stats",
    "generate_unified_diff",
    "parse_search_replace_blocks",
    "apply_search_replace",
]
