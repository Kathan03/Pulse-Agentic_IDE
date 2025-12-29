"""
Tier 1 Atomic Tool: File Operations (Phase 4).

Provides safe file operations with project-root boundary enforcement.
Wraps FileManager and integrates with guardrails for security.

Tool: manage_file_ops
Operations: read, write, delete, list
Safety: Project-root validation, denylist enforcement, RAG integration
"""

from pathlib import Path
from typing import Dict, Any, Literal, Optional
import logging

from src.core.file_manager import FileManager
from src.core.guardrails import (
    validate_file_operation,
    truncate_output,
    GENERAL_OUTPUT_MAX_CHARS,
    is_file_binary,
)

logger = logging.getLogger(__name__)


# ============================================================================
# TIER 1 TOOL: manage_file_ops
# ============================================================================

def manage_file_ops(
    operation: Literal["read", "write", "delete", "list"],
    path: str,
    project_root: Path,
    content: Optional[str] = None,
    rag_manager: Optional[Any] = None  # RAGManager instance (for updates)
) -> Dict[str, Any]:
    """
    Tier 1 atomic tool for file operations.

    Args:
        operation: Operation type ("read", "write", "delete", "list").
        path: File/directory path (relative to project_root or absolute).
        project_root: Project root directory (boundary enforcement).
        content: File content (required for write operation).
        rag_manager: Optional RAGManager instance (for freshness updates).

    Returns:
        Dict with keys:
            - operation: str (echoed operation)
            - path: str (resolved path)
            - status: str ("success" or "error")
            - summary: str (human-readable result)
            - content: Optional[str] (file content for read)
            - error: Optional[str] (error message if failed)

    Safety:
        - All paths validated against project_root
        - Denylist patterns rejected
        - Binary files handled safely
        - Output truncated to caps
        - RAG updates triggered on write/delete

    Example:
        >>> result = manage_file_ops(
        ...     operation="read",
        ...     path="src/main.st",
        ...     project_root=Path("/workspace/my_project")
        ... )
        >>> result["status"]
        'success'
        >>> result["content"]
        'PROGRAM Main\\n  VAR...'
    """
    logger.info(f"File operation: {operation} on {path}")

    resolved_path = None

    try:
        # ====================================================================
        # VALIDATION: Project-root boundary + denylist
        # ====================================================================

        path_obj = Path(path)
        validate_file_operation(operation, path_obj, project_root)

        # Resolve to absolute path
        if not path_obj.is_absolute():
            resolved_path = project_root / path_obj
        else:
            resolved_path = path_obj

        resolved_path = resolved_path.resolve()

        # ====================================================================
        # OPERATION EXECUTION
        # ====================================================================

        file_manager = FileManager(str(project_root))

        # READ operation
        if operation == "read":
            if not resolved_path.exists():
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"File not found: {resolved_path.name}",
                    "error": "FileNotFoundError",
                }

            if not resolved_path.is_file():
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"Path is not a file: {resolved_path.name}",
                    "error": "NotAFileError",
                }

            # Check if binary
            if is_file_binary(resolved_path):
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"Binary file cannot be read as text: {resolved_path.name}",
                    "error": "BinaryFileError",
                }

            # Read content
            file_content = file_manager.read_file(str(resolved_path.relative_to(project_root)))

            # Truncate if too large
            truncated_content = truncate_output(file_content, max_chars=GENERAL_OUTPUT_MAX_CHARS)

            return {
                "operation": operation,
                "path": str(resolved_path.relative_to(project_root)),
                "status": "success",
                "summary": f"Read {len(file_content)} characters from {resolved_path.name}",
                "content": truncated_content,
            }

        # WRITE operation
        elif operation == "write":
            if content is None:
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": "Write operation requires 'content' parameter",
                    "error": "MissingContentError",
                }

            # Write content atomically
            file_manager.write_file(str(resolved_path.relative_to(project_root)), content)

            # Trigger RAG update
            if rag_manager:
                try:
                    rag_manager.update_file(resolved_path)
                    logger.info(f"RAG updated for: {resolved_path}")
                except Exception as e:
                    logger.warning(f"RAG update failed for {resolved_path}: {e}")

            return {
                "operation": operation,
                "path": str(resolved_path.relative_to(project_root)),
                "status": "success",
                "summary": f"Wrote {len(content)} characters to {resolved_path.name}",
            }

        # DELETE operation
        elif operation == "delete":
            if not resolved_path.exists():
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"File not found: {resolved_path.name}",
                    "error": "FileNotFoundError",
                }

            if not resolved_path.is_file():
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"Path is not a file: {resolved_path.name}",
                    "error": "NotAFileError",
                }

            # Delete file
            resolved_path.unlink()

            # Trigger RAG removal
            if rag_manager:
                try:
                    rag_manager.remove_file(resolved_path)
                    logger.info(f"RAG entry removed for: {resolved_path}")
                except Exception as e:
                    logger.warning(f"RAG removal failed for {resolved_path}: {e}")

            return {
                "operation": operation,
                "path": str(resolved_path.relative_to(project_root)),
                "status": "success",
                "summary": f"Deleted {resolved_path.name}",
            }

        # LIST operation
        elif operation == "list":
            if not resolved_path.exists():
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"Directory not found: {resolved_path.name}",
                    "error": "DirectoryNotFoundError",
                }

            if not resolved_path.is_dir():
                return {
                    "operation": operation,
                    "path": str(resolved_path.relative_to(project_root)),
                    "status": "error",
                    "summary": f"Path is not a directory: {resolved_path.name}",
                    "error": "NotADirectoryError",
                }

            # List directory contents
            items = file_manager.list_files(str(resolved_path.relative_to(project_root)))

            # Build tree view (simple bounded format)
            tree_lines = []
            for item in sorted(items)[:100]:  # Limit to 100 items
                item_path = resolved_path / item
                if item_path.is_dir():
                    tree_lines.append(f"📁 {item}/")
                else:
                    tree_lines.append(f"📄 {item}")

            tree_view = "\n".join(tree_lines)

            if len(items) > 100:
                tree_view += f"\n... ({len(items) - 100} more items)"

            return {
                "operation": operation,
                "path": str(resolved_path.relative_to(project_root)),
                "status": "success",
                "summary": f"Listed {len(items)} items in {resolved_path.name}",
                "content": tree_view,
            }

        else:
            return {
                "operation": operation,
                "path": str(path),
                "status": "error",
                "summary": f"Unknown operation: {operation}",
                "error": "InvalidOperationError",
            }

    except Exception as e:
        logger.error(f"File operation failed: {operation} {path} - {e}", exc_info=True)
        return {
            "operation": operation,
            "path": str(path),
            "status": "error",
            "summary": f"Operation failed: {str(e)}",
            "error": type(e).__name__,
        }


__all__ = ["manage_file_ops"]
