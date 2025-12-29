"""
Tests for src/tools/file_ops.py - Tier 1 File Operations.

Tests:
- Read file operations (success and error cases)
- Write file operations with mock FileManager
- Delete file operations
- List directory operations
- Guardrail integration (boundary enforcement)
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tools.file_ops import manage_file_ops


class TestReadOperations:
    """Tests for file read operations."""

    def test_read_existing_file(self, temp_workspace):
        """Test reading an existing file."""
        result = manage_file_ops(
            operation="read",
            path="main.st",
            project_root=temp_workspace
        )

        assert result["status"] == "success"
        assert result["operation"] == "read"
        assert "content" in result
        assert "PROGRAM Main" in result["content"]

    def test_read_file_in_subdirectory(self, temp_workspace):
        """Test reading a file in a subdirectory."""
        result = manage_file_ops(
            operation="read",
            path="src/utils.st",
            project_root=temp_workspace
        )

        assert result["status"] == "success"
        assert "FUNCTION_BLOCK" in result["content"]

    def test_read_nonexistent_file(self, temp_workspace):
        """Test reading a file that doesn't exist."""
        result = manage_file_ops(
            operation="read",
            path="nonexistent.st",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "not found" in result["summary"].lower()
        assert result["error"] == "FileNotFoundError"

    def test_read_directory_fails(self, temp_workspace):
        """Test that reading a directory returns error."""
        result = manage_file_ops(
            operation="read",
            path="src",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "not a file" in result["summary"].lower()

    def test_read_denied_path(self, temp_workspace):
        """Test that reading denied paths is blocked."""
        result = manage_file_ops(
            operation="read",
            path=".env",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "PathViolationError" in result["error"]


class TestWriteOperations:
    """Tests for file write operations."""

    def test_write_new_file(self, temp_workspace):
        """Test writing a new file."""
        result = manage_file_ops(
            operation="write",
            path="new_file.st",
            project_root=temp_workspace,
            content="PROGRAM NewProgram\nEND_PROGRAM"
        )

        assert result["status"] == "success"
        assert "new_file.st" in result["path"]

        # Verify file was written
        new_file = temp_workspace / "new_file.st"
        assert new_file.exists()
        assert "NewProgram" in new_file.read_text()

    def test_write_without_content_fails(self, temp_workspace):
        """Test that write without content returns error."""
        result = manage_file_ops(
            operation="write",
            path="no_content.st",
            project_root=temp_workspace,
            content=None
        )

        assert result["status"] == "error"
        assert "content" in result["summary"].lower()

    def test_write_to_subdirectory(self, temp_workspace):
        """Test writing to a file in a subdirectory."""
        result = manage_file_ops(
            operation="write",
            path="src/new_util.st",
            project_root=temp_workspace,
            content="FUNCTION NewHelper\nEND_FUNCTION"
        )

        assert result["status"] == "success"

        # Verify file was written
        new_file = temp_workspace / "src" / "new_util.st"
        assert new_file.exists()

    def test_write_denied_path(self, temp_workspace):
        """Test that writing to denied paths is blocked."""
        result = manage_file_ops(
            operation="write",
            path=".env",
            project_root=temp_workspace,
            content="SECRET=123"
        )

        assert result["status"] == "error"

    def test_write_with_rag_manager(self, temp_workspace):
        """Test that RAG manager is called on write."""
        mock_rag = MagicMock()

        result = manage_file_ops(
            operation="write",
            path="rag_test.st",
            project_root=temp_workspace,
            content="PROGRAM Test\nEND_PROGRAM",
            rag_manager=mock_rag
        )

        assert result["status"] == "success"
        mock_rag.update_file.assert_called_once()


class TestDeleteOperations:
    """Tests for file delete operations."""

    def test_delete_existing_file(self, temp_workspace):
        """Test deleting an existing file."""
        # Create a file to delete
        file_to_delete = temp_workspace / "to_delete.st"
        file_to_delete.write_text("DELETE ME")

        result = manage_file_ops(
            operation="delete",
            path="to_delete.st",
            project_root=temp_workspace
        )

        assert result["status"] == "success"
        assert not file_to_delete.exists()

    def test_delete_nonexistent_file(self, temp_workspace):
        """Test deleting a file that doesn't exist."""
        result = manage_file_ops(
            operation="delete",
            path="nonexistent.st",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "not found" in result["summary"].lower()

    def test_delete_directory_fails(self, temp_workspace):
        """Test that deleting a directory returns error."""
        result = manage_file_ops(
            operation="delete",
            path="src",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "not a file" in result["summary"].lower()


class TestListOperations:
    """Tests for directory list operations."""

    def test_list_directory(self, temp_workspace):
        """Test listing a directory."""
        result = manage_file_ops(
            operation="list",
            path=".",
            project_root=temp_workspace
        )

        assert result["status"] == "success"
        assert "content" in result
        assert "main.st" in result["content"]

    def test_list_subdirectory(self, temp_workspace):
        """Test listing a subdirectory."""
        result = manage_file_ops(
            operation="list",
            path="src",
            project_root=temp_workspace
        )

        assert result["status"] == "success"
        assert "utils.st" in result["content"]

    def test_list_nonexistent_directory(self, temp_workspace):
        """Test listing a directory that doesn't exist."""
        result = manage_file_ops(
            operation="list",
            path="nonexistent_dir",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "not found" in result["summary"].lower()

    def test_list_file_fails(self, temp_workspace):
        """Test that listing a file returns error."""
        result = manage_file_ops(
            operation="list",
            path="main.st",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "not a directory" in result["summary"].lower()


class TestBoundaryEnforcement:
    """Tests for project-root boundary enforcement."""

    def test_path_traversal_blocked(self, temp_workspace):
        """Test that path traversal is blocked."""
        result = manage_file_ops(
            operation="read",
            path="../../../etc/passwd",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "PathViolationError" in result["error"]

    def test_absolute_path_outside_root_blocked(self, temp_workspace):
        """Test that absolute paths outside root are blocked."""
        result = manage_file_ops(
            operation="read",
            path="/etc/passwd",
            project_root=temp_workspace
        )

        assert result["status"] == "error"


class TestInvalidOperations:
    """Tests for invalid operation handling."""

    def test_unknown_operation(self, temp_workspace):
        """Test that unknown operations return error."""
        result = manage_file_ops(
            operation="invalid_op",
            path="main.st",
            project_root=temp_workspace
        )

        assert result["status"] == "error"
        assert "unknown operation" in result["summary"].lower()
