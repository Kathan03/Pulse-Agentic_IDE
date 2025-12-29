"""
Safety Guardrails for Pulse IDE v2.6.

Enforces:
- Project-root boundary (prevents path traversal)
- Denylist patterns (sensitive files/directories)
- Tool output size caps and log bounds

All file operations and tool executions must validate through these guardrails.
"""

import re
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Denylist patterns for sensitive files/directories
DENYLIST_PATTERNS = [
    # Environment and credentials
    r"\.env$",
    r"\.env\..*$",
    r"credentials\.json$",
    r"secrets\.json$",
    r"\.aws/",
    r"\.ssh/",
    r"id_rsa",
    r"id_ed25519",
    r"\.pem$",

    # Git internals (read-only allowed, writes denied)
    r"\.git/config$",
    r"\.git/hooks/",
    r"\.git/objects/",

    # System directories
    r"^/etc/",
    r"^C:\\Windows\\",
    r"^C:\\Program Files",

    # Binary executables (unless explicitly allowed)
    r"\.exe$",
    r"\.dll$",
    r"\.so$",
    r"\.dylib$",
]

# Tool output size limits (characters)
TERMINAL_OUTPUT_MAX_CHARS = 10_000
LOG_OUTPUT_MAX_CHARS = 5_000
GENERAL_OUTPUT_MAX_CHARS = 50_000

# Log file rotation limits
MAX_LOG_FILES = 10
MAX_LOG_FILE_SIZE_MB = 1


# ============================================================================
# PROJECT-ROOT BOUNDARY ENFORCEMENT
# ============================================================================

class PathViolationError(Exception):
    """Raised when path operation violates project-root boundary."""
    pass


def validate_path(path: Path, project_root: Path, allow_read_only: bool = False) -> Path:
    """
    Validate path is within project root and not on denylist.

    Args:
        path: Path to validate (can be relative or absolute).
        project_root: Absolute project root directory.
        allow_read_only: If True, allow read access to git internals.

    Returns:
        Resolved absolute Path if valid.

    Raises:
        PathViolationError: If path violates boundaries or is denylisted.

    Example:
        >>> project_root = Path("/workspace/my_project")
        >>> validate_path(Path("src/main.st"), project_root)
        Path('/workspace/my_project/src/main.st')

        >>> validate_path(Path("../etc/passwd"), project_root)
        PathViolationError: Path attempts to escape project root
    """
    # Resolve to absolute path and canonicalize
    if not path.is_absolute():
        path = project_root / path

    resolved_path = path.resolve()
    resolved_root = project_root.resolve()

    # Check 1: Ensure path is within project root
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise PathViolationError(
            f"Path attempts to escape project root: {path} "
            f"(resolved: {resolved_path}, root: {resolved_root})"
        )

    # Check 2: Validate against denylist
    _check_denylist(resolved_path, allow_read_only=allow_read_only)

    return resolved_path


def _check_denylist(path: Path, allow_read_only: bool = False) -> None:
    """
    Check if path matches denylist patterns.

    Args:
        path: Absolute path to check.
        allow_read_only: If True, allow .git/ read access.

    Raises:
        PathViolationError: If path matches denylist pattern.
    """
    path_str = str(path)

    for pattern in DENYLIST_PATTERNS:
        if re.search(pattern, path_str, re.IGNORECASE):
            # Special case: allow .git/ reads for repository info
            if allow_read_only and ".git" in pattern:
                logger.debug(f"Allowing read-only access to: {path}")
                continue

            raise PathViolationError(
                f"Path matches denylist pattern '{pattern}': {path}"
            )


def is_path_safe(path: Path, project_root: Path, allow_read_only: bool = False) -> bool:
    """
    Check if path is safe without raising exception.

    Args:
        path: Path to check.
        project_root: Project root directory.
        allow_read_only: If True, allow read-only access to .git/

    Returns:
        True if path is safe, False otherwise.
    """
    try:
        validate_path(path, project_root, allow_read_only=allow_read_only)
        return True
    except PathViolationError:
        return False


# ============================================================================
# TOOL OUTPUT SIZE CAPS
# ============================================================================

def truncate_output(
    output: str,
    max_chars: int = GENERAL_OUTPUT_MAX_CHARS,
    truncation_message: Optional[str] = None
) -> str:
    """
    Truncate output to maximum character limit with clear indicator.

    Args:
        output: Output string to truncate.
        max_chars: Maximum characters allowed.
        truncation_message: Custom truncation message (optional).

    Returns:
        Truncated output with indicator if needed.

    Example:
        >>> truncate_output("x" * 100, max_chars=50)
        'xxxxxxxxxx... [output truncated: 100 chars → 50 chars]'
    """
    if len(output) <= max_chars:
        return output

    if truncation_message is None:
        truncation_message = f"[output truncated: {len(output)} chars → {max_chars} chars]"

    # Keep first portion and add truncation indicator
    truncated = output[:max_chars - len(truncation_message) - 10]
    return f"{truncated}... {truncation_message}"


def truncate_terminal_output(output: str) -> str:
    """
    Truncate terminal command output to safe display size.

    Args:
        output: Terminal output string.

    Returns:
        Truncated output with indicator if needed.
    """
    return truncate_output(
        output,
        max_chars=TERMINAL_OUTPUT_MAX_CHARS,
        truncation_message="[terminal output truncated]"
    )


def truncate_log_output(output: str) -> str:
    """
    Truncate log output to bounded size.

    Args:
        output: Log output string.

    Returns:
        Truncated output with indicator if needed.
    """
    return truncate_output(
        output,
        max_chars=LOG_OUTPUT_MAX_CHARS,
        truncation_message="[log output truncated]"
    )


# ============================================================================
# LOG FILE ROTATION BOUNDS
# ============================================================================

def enforce_log_rotation(log_dir: Path) -> None:
    """
    Enforce log file rotation limits (max files and max size).

    Removes oldest log files if count exceeds MAX_LOG_FILES.
    Warns if any log file exceeds MAX_LOG_FILE_SIZE_MB.

    Args:
        log_dir: Directory containing log files.
    """
    if not log_dir.exists() or not log_dir.is_dir():
        return

    # Get all log files sorted by modification time (newest first)
    log_files = sorted(
        log_dir.glob("*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    # Remove excess log files
    if len(log_files) > MAX_LOG_FILES:
        files_to_remove = log_files[MAX_LOG_FILES:]
        logger.info(f"Removing {len(files_to_remove)} old log files")
        for log_file in files_to_remove:
            log_file.unlink()

    # Check file sizes
    max_size_bytes = MAX_LOG_FILE_SIZE_MB * 1024 * 1024
    for log_file in log_files[:MAX_LOG_FILES]:
        size_bytes = log_file.stat().st_size
        if size_bytes > max_size_bytes:
            logger.warning(
                f"Log file exceeds size limit: {log_file.name} "
                f"({size_bytes / 1024 / 1024:.2f} MB > {MAX_LOG_FILE_SIZE_MB} MB)"
            )


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_file_operation(
    operation: str,
    file_path: Path,
    project_root: Path
) -> None:
    """
    Validate file operation is allowed.

    Args:
        operation: Operation type ("read", "write", "delete").
        file_path: Target file path.
        project_root: Project root directory.

    Raises:
        PathViolationError: If operation violates guardrails.
    """
    # Read operations can access .git/ (read-only)
    allow_read_only = (operation == "read")

    validate_path(file_path, project_root, allow_read_only=allow_read_only)

    logger.debug(f"File operation validated: {operation} {file_path}")


def is_file_binary(file_path: Path, sample_size: int = 8192) -> bool:
    """
    Heuristic check if file is binary (non-text).

    Args:
        file_path: Path to file.
        sample_size: Bytes to sample for detection.

    Returns:
        True if file appears to be binary.
    """
    if not file_path.exists():
        return False

    try:
        with file_path.open("rb") as f:
            chunk = f.read(sample_size)

        # Check for null bytes (strong binary indicator)
        if b"\x00" in chunk:
            return True

        # Check for high ratio of non-ASCII characters
        non_ascii_count = sum(1 for byte in chunk if byte > 127)
        if len(chunk) > 0 and non_ascii_count / len(chunk) > 0.3:
            return True

        return False

    except Exception:
        # If we can't read it, assume binary to be safe
        return True


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "PathViolationError",
    "validate_path",
    "is_path_safe",
    "validate_file_operation",
    "truncate_output",
    "truncate_terminal_output",
    "truncate_log_output",
    "enforce_log_rotation",
    "is_file_binary",
    "TERMINAL_OUTPUT_MAX_CHARS",
    "LOG_OUTPUT_MAX_CHARS",
    "MAX_LOG_FILES",
    "MAX_LOG_FILE_SIZE_MB",
]
