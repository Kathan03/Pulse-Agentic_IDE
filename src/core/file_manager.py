"""
File Manager - Secure Persistence Layer for Pulse IDE

Provides atomic file operations with path traversal protection.
All file I/O operations are sandboxed to the workspace root.
"""

import os
import tempfile
from pathlib import Path
from typing import List


class FileManager:
    """
    Secure file manager with atomic writes and path validation.

    All operations are constrained to the workspace root directory
    to prevent path traversal attacks.
    """

    def __init__(self, base_path: str):
        """
        Initialize FileManager with a workspace root directory.

        Args:
            base_path: Root directory for all file operations (workspace root)

        Raises:
            ValueError: If base_path doesn't exist or is not a directory
        """
        # Convert to absolute path and resolve symlinks
        self.base_path = Path(base_path).resolve()

        # Validate that base_path exists and is a directory
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {self.base_path}")
        if not self.base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {self.base_path}")

    def _validate_path(self, rel_path: str) -> Path:
        """
        Validate and resolve a path to ensure it's within the workspace.

        Args:
            rel_path: Relative or absolute path to validate

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path escapes the workspace root
        """
        # Convert to Path and resolve to absolute path
        if os.path.isabs(rel_path):
            # If absolute path, use it directly
            target_path = Path(rel_path).resolve()
        else:
            # If relative path, join with base_path
            target_path = (self.base_path / rel_path).resolve()

        # Security check: Ensure target_path is within base_path
        try:
            # This will raise ValueError if target_path is not relative to base_path
            target_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(
                f"Path traversal detected: '{rel_path}' resolves to '{target_path}' "
                f"which is outside workspace root '{self.base_path}'"
            )

        return target_path

    def write_file(self, rel_path: str, content: str, encoding: str = 'utf-8') -> None:
        """
        Atomically write content to a file.

        Uses a temporary file in the same directory to ensure atomic operation.
        This prevents file corruption if the write is interrupted.

        Args:
            rel_path: Path to the file (relative to workspace or absolute)
            content: Text content to write
            encoding: Text encoding (default: utf-8)

        Raises:
            ValueError: If path is outside workspace
            OSError: If write operation fails
        """
        # Validate and resolve path
        target_path = self._validate_path(rel_path)

        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in the same directory as target
        # This ensures atomic rename works (same filesystem)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp"
        )

        try:
            # Write content to temp file
            with os.fdopen(temp_fd, 'w', encoding=encoding) as temp_file:
                temp_file.write(content)
                # Force flush to disk (critical for atomic writes)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            # Atomically replace target file with temp file
            # os.replace is atomic on all platforms
            os.replace(temp_path, target_path)

        except Exception as e:
            # Clean up temp file if something went wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Temp file already removed or doesn't exist
            raise OSError(f"Failed to write file '{target_path}': {e}") from e

    def read_file(self, rel_path: str, encoding: str = 'utf-8') -> str:
        """
        Read content from a file.

        Args:
            rel_path: Path to the file (relative to workspace or absolute)
            encoding: Text encoding (default: utf-8)

        Returns:
            File content as string

        Raises:
            ValueError: If path is outside workspace
            FileNotFoundError: If file doesn't exist
            OSError: If read operation fails
        """
        # Validate and resolve path
        target_path = self._validate_path(rel_path)

        # Check if file exists
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")

        if not target_path.is_file():
            raise OSError(f"Path is not a file: {target_path}")

        # Read and return content
        try:
            with open(target_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            raise OSError(f"Failed to read file '{target_path}': {e}") from e

    def list_files(self, rel_path: str = ".") -> List[str]:
        """
        List files and directories in a path.

        Args:
            rel_path: Path to directory (relative to workspace or absolute)

        Returns:
            List of file/directory names (not full paths)

        Raises:
            ValueError: If path is outside workspace
            FileNotFoundError: If directory doesn't exist
            OSError: If path is not a directory
        """
        # Validate and resolve path
        target_path = self._validate_path(rel_path)

        # Check if directory exists
        if not target_path.exists():
            raise FileNotFoundError(f"Directory not found: {target_path}")

        if not target_path.is_dir():
            raise OSError(f"Path is not a directory: {target_path}")

        # List directory contents
        try:
            return [item.name for item in target_path.iterdir()]
        except Exception as e:
            raise OSError(f"Failed to list directory '{target_path}': {e}") from e

    def file_exists(self, rel_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            rel_path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            target_path = self._validate_path(rel_path)
            return target_path.exists() and target_path.is_file()
        except (ValueError, OSError):
            return False

    def directory_exists(self, rel_path: str) -> bool:
        """
        Check if a directory exists.

        Args:
            rel_path: Path to check

        Returns:
            True if directory exists, False otherwise
        """
        try:
            target_path = self._validate_path(rel_path)
            return target_path.exists() and target_path.is_dir()
        except (ValueError, OSError):
            return False

    def get_absolute_path(self, rel_path: str) -> str:
        """
        Get the absolute path for a relative path.

        Args:
            rel_path: Relative or absolute path

        Returns:
            Absolute path as string

        Raises:
            ValueError: If path is outside workspace
        """
        return str(self._validate_path(rel_path))

    def get_workspace_root(self) -> str:
        """
        Get the workspace root directory.

        Returns:
            Absolute path to workspace root
        """
        return str(self.base_path)
