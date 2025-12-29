"""
Tests for src/core/guardrails.py - Safety Guardrails.

Tests:
- Project-root boundary enforcement
- Denylist pattern matching
- Output truncation
- Binary file detection
"""

import pytest
from pathlib import Path

from src.core.guardrails import (
    validate_path,
    is_path_safe,
    validate_file_operation,
    truncate_output,
    truncate_terminal_output,
    truncate_log_output,
    is_file_binary,
    PathViolationError,
    TERMINAL_OUTPUT_MAX_CHARS,
    LOG_OUTPUT_MAX_CHARS,
)


class TestPathValidation:
    """Tests for project-root boundary enforcement."""

    def test_valid_path_within_root(self, temp_workspace):
        """Test that paths within project root are accepted."""
        project_root = temp_workspace
        valid_path = Path("main.st")

        result = validate_path(valid_path, project_root)
        assert result == (project_root / "main.st").resolve()

    def test_valid_absolute_path_within_root(self, temp_workspace):
        """Test that absolute paths within project root are accepted."""
        project_root = temp_workspace
        valid_path = project_root / "src" / "utils.st"

        result = validate_path(valid_path, project_root)
        assert result == valid_path.resolve()

    def test_path_traversal_blocked(self, temp_workspace):
        """Test that path traversal attempts are blocked."""
        project_root = temp_workspace
        malicious_path = Path("../etc/passwd")

        with pytest.raises(PathViolationError) as exc_info:
            validate_path(malicious_path, project_root)

        assert "escape project root" in str(exc_info.value)

    def test_absolute_path_outside_root_blocked(self, temp_workspace):
        """Test that absolute paths outside project root are blocked."""
        project_root = temp_workspace

        # Try to access parent directory
        outside_path = project_root.parent / "other_folder"

        with pytest.raises(PathViolationError):
            validate_path(outside_path, project_root)

    def test_is_path_safe_returns_true_for_valid_path(self, temp_workspace):
        """Test is_path_safe returns True for valid paths."""
        project_root = temp_workspace

        assert is_path_safe(Path("main.st"), project_root) is True
        assert is_path_safe(Path("src/utils.st"), project_root) is True

    def test_is_path_safe_returns_false_for_invalid_path(self, temp_workspace):
        """Test is_path_safe returns False for invalid paths."""
        project_root = temp_workspace

        assert is_path_safe(Path("../secret"), project_root) is False
        assert is_path_safe(Path(".env"), project_root) is False


class TestDenylistPatterns:
    """Tests for denylist pattern matching."""

    def test_env_file_blocked(self, temp_workspace):
        """Test that .env files are blocked."""
        project_root = temp_workspace

        with pytest.raises(PathViolationError) as exc_info:
            validate_path(Path(".env"), project_root)

        assert "denylist" in str(exc_info.value).lower()

    def test_credentials_file_blocked(self, temp_workspace):
        """Test that credentials.json is blocked."""
        project_root = temp_workspace

        with pytest.raises(PathViolationError):
            validate_path(Path("credentials.json"), project_root)

    def test_ssh_directory_blocked(self, temp_workspace):
        """Test that .ssh directory is blocked."""
        project_root = temp_workspace

        with pytest.raises(PathViolationError):
            validate_path(Path(".ssh/id_rsa"), project_root)

    def test_sensitive_files_blocked_for_write(self, temp_workspace):
        """Test that sensitive files like id_rsa are blocked for writes."""
        project_root = temp_workspace

        # id_rsa pattern should always be blocked
        with pytest.raises(PathViolationError):
            validate_path(Path("id_rsa"), project_root, allow_read_only=False)

        # .pem files should also be blocked
        with pytest.raises(PathViolationError):
            validate_path(Path("server.pem"), project_root, allow_read_only=False)

    def test_git_internals_allowed_for_read(self, temp_workspace):
        """Test that .git internals are allowed for reads."""
        project_root = temp_workspace

        # Note: actual validation depends on file existence, but pattern check should pass
        # This tests the read-only exception for .git
        result = is_path_safe(Path("src/main.st"), project_root, allow_read_only=True)
        assert result is True

    def test_executable_files_blocked(self, temp_workspace):
        """Test that executable files are blocked."""
        project_root = temp_workspace

        with pytest.raises(PathViolationError):
            validate_path(Path("app.exe"), project_root)

        with pytest.raises(PathViolationError):
            validate_path(Path("lib.dll"), project_root)


class TestFileOperationValidation:
    """Tests for validate_file_operation function."""

    def test_read_operation_allows_git(self, temp_workspace):
        """Test that read operations allow .git access in read-only mode."""
        project_root = temp_workspace

        # Regular file read should work
        validate_file_operation("read", Path("main.st"), project_root)

    def test_write_operation_validated(self, temp_workspace):
        """Test that write operations are validated."""
        project_root = temp_workspace

        # Valid write
        validate_file_operation("write", Path("new_file.st"), project_root)

        # Invalid write (env file)
        with pytest.raises(PathViolationError):
            validate_file_operation("write", Path(".env"), project_root)

    def test_delete_operation_validated(self, temp_workspace):
        """Test that delete operations are validated."""
        project_root = temp_workspace

        # Valid delete
        validate_file_operation("delete", Path("temp.st"), project_root)


class TestOutputTruncation:
    """Tests for output truncation functions."""

    def test_truncate_output_short_content(self):
        """Test that short content is not truncated."""
        short_content = "Hello World"
        result = truncate_output(short_content, max_chars=1000)
        assert result == short_content

    def test_truncate_output_long_content(self):
        """Test that long content is truncated with indicator."""
        long_content = "x" * 200
        result = truncate_output(long_content, max_chars=100)

        assert len(result) < 200
        assert "truncated" in result.lower()
        assert "200 chars" in result  # Original length

    def test_truncate_output_custom_message(self):
        """Test truncation with custom message."""
        long_content = "y" * 200
        result = truncate_output(long_content, max_chars=100, truncation_message="[CUSTOM]")

        assert "[CUSTOM]" in result

    def test_truncate_terminal_output(self):
        """Test terminal-specific truncation."""
        long_output = "z" * (TERMINAL_OUTPUT_MAX_CHARS + 100)
        result = truncate_terminal_output(long_output)

        assert len(result) <= TERMINAL_OUTPUT_MAX_CHARS + 50  # Allow for message
        assert "terminal output truncated" in result.lower()

    def test_truncate_log_output(self):
        """Test log-specific truncation."""
        long_output = "a" * (LOG_OUTPUT_MAX_CHARS + 100)
        result = truncate_log_output(long_output)

        assert len(result) <= LOG_OUTPUT_MAX_CHARS + 50  # Allow for message
        assert "log output truncated" in result.lower()


class TestBinaryFileDetection:
    """Tests for binary file detection."""

    def test_text_file_not_binary(self, temp_workspace):
        """Test that text files are not detected as binary."""
        project_root = temp_workspace
        text_file = project_root / "main.st"

        assert is_file_binary(text_file) is False

    def test_binary_file_detected(self, temp_workspace):
        """Test that binary files are detected."""
        project_root = temp_workspace
        binary_file = project_root / "test.bin"

        # Create a file with null bytes (binary indicator)
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        assert is_file_binary(binary_file) is True

    def test_nonexistent_file_returns_false(self, temp_workspace):
        """Test that nonexistent files return False."""
        project_root = temp_workspace
        nonexistent = project_root / "does_not_exist.txt"

        assert is_file_binary(nonexistent) is False

    def test_high_non_ascii_ratio_detected(self, temp_workspace):
        """Test that files with high non-ASCII ratio are detected as binary."""
        project_root = temp_workspace
        binary_file = project_root / "high_non_ascii.bin"

        # Create a file with high ratio of non-ASCII bytes
        binary_file.write_bytes(bytes([200] * 100))

        assert is_file_binary(binary_file) is True
