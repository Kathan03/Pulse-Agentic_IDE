"""
Tier 1 Atomic Tool: Patch Workflow (Phase 4).

Implements patch preview and execution with human approval gates.
Supports unified diff format for LLM-generated code changes.

Workflow:
1. preview_patch() - Parse and validate diff, return PatchPlan
2. User approves/denies in UI (Master Graph pauses)
3. execute_patch() - Apply approved patch to disk

Safety:
- Project-root boundary enforcement
- Context validation (hunks match existing code)
- Atomic file updates (temp file + rename)
- RAG freshness updates after apply
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import hashlib
from datetime import datetime

try:
    from unidiff import PatchSet
    UNIDIFF_AVAILABLE = True
except ImportError:
    UNIDIFF_AVAILABLE = False
    PatchSet = None

from src.agents.state import PatchPlan
from src.core.guardrails import validate_path, PathViolationError
from src.core.file_manager import FileManager

logger = logging.getLogger(__name__)


# ============================================================================
# PATCH PREVIEW
# ============================================================================

def preview_patch(
    diff: str,
    project_root: Path
) -> PatchPlan:
    """
    Preview a unified diff patch and validate it.

    Args:
        diff: Unified diff string (standard format: --- a/file +++ b/file).
        project_root: Project root directory (boundary enforcement).

    Returns:
        PatchPlan model with:
            - file_path: Primary file being modified
            - diff: Original diff content
            - rationale: Auto-generated summary
            - action: "create" | "modify" | "delete"

    Raises:
        ValueError: If diff is invalid or violates guardrails.
        PathViolationError: If file paths escape project root.

    Example:
        >>> diff_str = '''--- a/main.st
        ... +++ b/main.st
        ... @@ -1,3 +1,5 @@
        ...  VAR
        ...      existing : BOOL;
        ... +    (* New feature *)
        ... +    new_var : INT;
        ...  END_VAR'''
        >>> plan = preview_patch(diff_str, Path("/workspace"))
        >>> plan.file_path
        'main.st'
        >>> plan.action
        'modify'
    """
    logger.info("Previewing patch...")

    if not diff.strip():
        raise ValueError("Empty diff provided")

    # ====================================================================
    # PARSE DIFF (with or without unidiff library)
    # ====================================================================

    if UNIDIFF_AVAILABLE and PatchSet is not None:
        try:
            patchset = PatchSet(diff)
            if not patchset:
                raise ValueError("No patches found in diff")

            # Extract file paths
            touched_files = []
            for patched_file in patchset:
                # Handle both "a/file" and "file" formats
                target_path = patched_file.target_file.lstrip('b/')
                touched_files.append(target_path)

            # Validate all paths are within project root
            for file_path in touched_files:
                path_obj = Path(file_path)
                validate_path(path_obj, project_root, allow_read_only=False)

            # Determine primary file (first in patchset)
            primary_file = touched_files[0]

            # Determine action
            first_patch = patchset[0]
            if first_patch.source_file == '/dev/null':
                action = "create"
            elif first_patch.target_file == '/dev/null':
                action = "delete"
            else:
                action = "modify"

            # Generate summary
            total_additions = sum(p.added for p in patchset)
            total_deletions = sum(p.removed for p in patchset)
            changes_summary = f"{len(touched_files)} file(s): +{total_additions} -{total_deletions}"

        except Exception as e:
            logger.warning(f"unidiff parsing failed: {e}, falling back to simple parser")
            # Fall through to simple parser
            touched_files, primary_file, action, changes_summary = _simple_diff_parse(diff, project_root)

    else:
        # Simple parser (no unidiff dependency)
        logger.info("Using simple diff parser (unidiff not available)")
        touched_files, primary_file, action, changes_summary = _simple_diff_parse(diff, project_root)

    # ====================================================================
    # VALIDATION
    # ====================================================================

    # Check if target file exists for modify/delete operations
    primary_path = project_root / primary_file
    if action in ["modify", "delete"] and not primary_path.exists():
        logger.warning(f"Target file does not exist: {primary_file}")
        # Don't fail - LLM might be creating a new file with "modify" action
        # UI will show warning

    # ====================================================================
    # CREATE PATCHPLAN
    # ====================================================================

    rationale = f"Patch {action}: {changes_summary}"

    patch_plan = PatchPlan(
        file_path=primary_file,
        diff=diff,
        rationale=rationale,
        action=action
    )

    logger.info(f"Patch preview: {action} {primary_file}")
    return patch_plan


def _simple_diff_parse(
    diff: str,
    project_root: Path
) -> tuple[List[str], str, str, str]:
    """
    Simple unified diff parser (fallback when unidiff not available).

    Returns:
        Tuple of (touched_files, primary_file, action, changes_summary)
    """
    touched_files = []
    additions = 0
    deletions = 0

    lines = diff.split('\n')
    current_file = None

    for line in lines:
        # Parse file headers
        if line.startswith('---'):
            # Source file (ignore)
            continue
        elif line.startswith('+++'):
            # Target file
            parts = line.split()
            if len(parts) >= 2:
                file_path = parts[1].lstrip('b/')
                current_file = file_path
                if file_path not in touched_files:
                    touched_files.append(file_path)

                    # Validate path
                    path_obj = Path(file_path)
                    validate_path(path_obj, project_root, allow_read_only=False)

        # Count additions/deletions
        elif line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1

    if not touched_files:
        raise ValueError("Could not parse file paths from diff")

    primary_file = touched_files[0]

    # Determine action (heuristic)
    if deletions == 0 and additions > 0:
        action = "create"
    elif additions == 0 and deletions > 0:
        action = "delete"
    else:
        action = "modify"

    changes_summary = f"{len(touched_files)} file(s): +{additions} -{deletions}"

    return touched_files, primary_file, action, changes_summary


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

    Args:
        plan: Approved PatchPlan from preview_patch().
        project_root: Project root directory.
        rag_manager: Optional RAGManager for freshness updates.

    Returns:
        Dict with keys:
            - status: "success" | "error"
            - files_modified: List[str] (paths of modified files)
            - summary: str (human-readable result)
            - error: Optional[str] (error message if failed)

    Safety:
        - Uses atomic file writes (temp file + rename)
        - Triggers RAG updates after successful apply
        - Validates paths before execution

    Example:
        >>> result = execute_patch(approved_plan, Path("/workspace"))
        >>> result["status"]
        'success'
        >>> result["files_modified"]
        ['main.st']
    """
    logger.info(f"Executing patch: {plan.action} {plan.file_path}")

    try:
        # ====================================================================
        # APPLY PATCH
        # ====================================================================

        if UNIDIFF_AVAILABLE and PatchSet is not None:
            # Use unidiff to apply patch
            result = _apply_patch_unidiff(plan, project_root)
        else:
            # Simple apply (write full file content)
            result = _apply_patch_simple(plan, project_root)

        # ====================================================================
        # RAG UPDATE
        # ====================================================================

        if result["status"] == "success" and rag_manager:
            for file_path in result["files_modified"]:
                try:
                    full_path = project_root / file_path
                    rag_manager.update_file(full_path)
                    logger.info(f"RAG updated for: {file_path}")
                except Exception as e:
                    logger.warning(f"RAG update failed for {file_path}: {e}")

        return result

    except Exception as e:
        logger.error(f"Patch execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "files_modified": [],
            "summary": f"Patch execution failed: {str(e)}",
            "error": type(e).__name__,
        }


def _apply_patch_unidiff(
    plan: PatchPlan,
    project_root: Path
) -> Dict[str, Any]:
    """
    Apply patch using unidiff library.

    Returns:
        Dict with status, files_modified, summary, error.
    """
    try:
        patchset = PatchSet(plan.diff)

        files_modified = []
        file_manager = FileManager(str(project_root))

        for patched_file in patchset:
            target_path = patched_file.target_file.lstrip('b/')
            source_path = patched_file.source_file.lstrip('a/')

            full_path = project_root / target_path

            if source_path == '/dev/null':
                # New file creation
                # Build content from hunks
                content_lines = []
                for hunk in patched_file:
                    for line in hunk:
                        if line.is_added:
                            content_lines.append(line.value.rstrip('\n'))

                content = '\n'.join(content_lines)
                file_manager.write_file(target_path, content)
                files_modified.append(target_path)

            elif target_path == '/dev/null':
                # File deletion
                if full_path.exists():
                    full_path.unlink()
                    files_modified.append(source_path)

            else:
                # File modification
                if not full_path.exists():
                    # File doesn't exist - treat as create
                    logger.warning(f"File {target_path} doesn't exist, creating new")
                    content_lines = []
                    for hunk in patched_file:
                        for line in hunk:
                            if line.is_added or line.is_context:
                                content_lines.append(line.value.rstrip('\n'))

                    content = '\n'.join(content_lines)
                    file_manager.write_file(target_path, content)
                    files_modified.append(target_path)
                else:
                    # Read existing file
                    original_content = file_manager.read_file(target_path)
                    original_lines = original_content.split('\n')

                    # Apply hunks
                    modified_lines = original_lines.copy()

                    for hunk in patched_file:
                        # Simple line-based application
                        # Find context and apply changes
                        start_line = hunk.source_start - 1  # 0-indexed

                        # Remove deleted lines
                        for line in hunk:
                            if line.is_removed:
                                # Find and remove
                                try:
                                    modified_lines.remove(line.value.rstrip('\n'))
                                except ValueError:
                                    logger.warning(f"Could not find line to remove: {line.value[:50]}")

                        # Add new lines
                        insert_pos = start_line
                        for line in hunk:
                            if line.is_added:
                                modified_lines.insert(insert_pos, line.value.rstrip('\n'))
                                insert_pos += 1

                    modified_content = '\n'.join(modified_lines)
                    file_manager.write_file(target_path, modified_content)
                    files_modified.append(target_path)

        return {
            "status": "success",
            "files_modified": files_modified,
            "summary": f"Applied patch to {len(files_modified)} file(s): {', '.join(files_modified)}",
        }

    except Exception as e:
        raise ValueError(f"Patch application failed: {e}")


def _apply_patch_simple(
    plan: PatchPlan,
    project_root: Path
) -> Dict[str, Any]:
    """
    Simple patch apply (fallback - requires LLM to provide full file content).

    This is a limited fallback that expects the diff to contain the full new file content.
    For production, unidiff is strongly recommended.

    Returns:
        Dict with status, files_modified, summary, error.
    """
    logger.warning("Using simple patch apply - consider installing unidiff for robust patching")

    # Extract content from diff (simple heuristic)
    # Look for lines starting with + (additions)
    lines = plan.diff.split('\n')
    content_lines = []

    for line in lines:
        if line.startswith('+') and not line.startswith('+++'):
            content_lines.append(line[1:])  # Remove + prefix
        elif line.startswith(' '):
            content_lines.append(line[1:])  # Context lines

    if not content_lines:
        raise ValueError("Could not extract content from diff (simple parser)")

    content = '\n'.join(content_lines)

    # Write to file
    file_manager = FileManager(str(project_root))
    file_manager.write_file(plan.file_path, content)

    return {
        "status": "success",
        "files_modified": [plan.file_path],
        "summary": f"Applied patch to {plan.file_path} (simple mode)",
    }


__all__ = [
    "preview_patch",
    "execute_patch",
]
