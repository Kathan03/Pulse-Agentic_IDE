"""
Test Suite for Execution Nodes (Coder & Tester).

Tests the Coder and Tester nodes to verify:
1. Coder Node generates code and writes files to disk
2. Tester Node performs static analysis and detects errors
3. State updates are handled correctly
4. File I/O operations work as expected

Run with: pytest tests/test_execution.py -v
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import AIMessage

from src.agents.coder_node import coder_node
from src.agents.tester_node import tester_node
from src.core.state import AgentState, create_initial_state
from src.core.crew_factory import CodeOutput


class TestCoderNode:
    """Test cases for Coder Agent Node functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_coder_node_with_empty_plan(self, temp_workspace):
        """Test Coder node handles empty plan gracefully."""
        state = create_initial_state(
            user_request="Test request",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["plan"] = []

        result = coder_node(state)

        assert "files_touched" in result
        assert len(result["files_touched"]) == 0
        assert "code_changes" in result
        assert "error" in result["code_changes"].lower()
        print("\n[OK] Coder node handles empty plan correctly")

    @patch('src.agents.coder_node.CrewFactory')
    def test_coder_node_creates_file(self, mock_factory_class, temp_workspace):
        """Test Coder node generates code and writes file to disk."""
        # Mock the crew result
        mock_code_output = CodeOutput(
            code="VAR\n  x : INT;\nEND_VAR",
            explanation="Added integer variable x"
        )

        mock_result = Mock()
        mock_result.pydantic = mock_code_output

        mock_crew = Mock()
        mock_crew.kickoff.return_value = mock_result

        mock_factory = Mock()
        mock_factory.create_coder_crew.return_value = mock_crew
        mock_factory_class.return_value = mock_factory

        # Create state with plan
        state = create_initial_state(
            user_request="Add a variable",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["plan"] = ["Add variable x to main.st"]

        # Execute coder node
        result = coder_node(state)

        # Verify factory and crew were called
        mock_factory.create_coder_crew.assert_called()
        mock_crew.kickoff.assert_called_once()

        # Verify result structure
        assert "files_touched" in result
        assert len(result["files_touched"]) == 1
        assert "main.st" in result["files_touched"][0]

        # Verify file exists on disk
        file_path = Path(temp_workspace) / "main.st"
        assert file_path.exists()

        # Verify file content
        content = file_path.read_text()
        assert "VAR" in content
        assert "x : INT" in content
        assert "END_VAR" in content

        print("\n[OK] Coder node creates file with correct content")

    @patch('src.agents.coder_node.CrewFactory')
    def test_coder_node_modifies_existing_file(self, mock_factory_class, temp_workspace):
        """Test Coder node modifies existing file."""
        # Create existing file
        existing_file = Path(temp_workspace) / "main.st"
        existing_file.write_text("PROGRAM Main\nEND_PROGRAM")

        # Mock the crew result
        mock_code_output = CodeOutput(
            code="PROGRAM Main\nVAR\n  bRunning : BOOL;\nEND_VAR\nEND_PROGRAM",
            explanation="Added boolean variable"
        )

        mock_result = Mock()
        mock_result.pydantic = mock_code_output

        mock_crew = Mock()
        mock_crew.kickoff.return_value = mock_result

        mock_factory = Mock()
        mock_factory.create_coder_crew.return_value = mock_crew
        mock_factory_class.return_value = mock_factory

        # Create state
        state = create_initial_state(
            user_request="Add boolean variable",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["plan"] = ["Add bRunning variable to main.st"]

        # Execute
        result = coder_node(state)

        # Verify file was modified
        assert "files_touched" in result
        assert "main.st" in result["files_touched"]

        # Verify new content
        content = existing_file.read_text()
        assert "bRunning" in content
        assert "BOOL" in content

        print("\n[OK] Coder node modifies existing file")

    @patch('src.agents.coder_node.CrewFactory')
    def test_coder_node_cleans_markdown(self, mock_factory_class, temp_workspace):
        """Test Coder node removes markdown formatting from code."""
        # Mock crew result with markdown
        mock_code_output = CodeOutput(
            code="```iecst\nVAR\n  x : INT;\nEND_VAR\n```",
            explanation="Code with markdown"
        )

        mock_result = Mock()
        mock_result.pydantic = mock_code_output

        mock_crew = Mock()
        mock_crew.kickoff.return_value = mock_result

        mock_factory = Mock()
        mock_factory.create_coder_crew.return_value = mock_crew
        mock_factory_class.return_value = mock_factory

        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["plan"] = ["Add code to main.st"]

        result = coder_node(state)

        # Verify file content has no markdown
        file_path = Path(temp_workspace) / "main.st"
        content = file_path.read_text()
        assert "```" not in content
        assert "VAR" in content

        print("\n[OK] Coder node removes markdown formatting")

    @patch('src.agents.coder_node.CrewFactory')
    def test_coder_node_handles_multiple_steps(self, mock_factory_class, temp_workspace):
        """Test Coder node processes multiple plan steps."""
        # Mock crew results
        mock_factory = Mock()

        # Different results for different calls
        results = [
            Mock(pydantic=CodeOutput(code="VAR\n  x : INT;\nEND_VAR", explanation="Step 1")),
            Mock(pydantic=CodeOutput(code="VAR\n  y : BOOL;\nEND_VAR", explanation="Step 2"))
        ]

        mock_crew = Mock()
        mock_crew.kickoff.side_effect = results
        mock_factory.create_coder_crew.return_value = mock_crew
        mock_factory_class.return_value = mock_factory

        state = create_initial_state(
            user_request="Multi-step request",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["plan"] = [
            "Add integer variable to main.st",
            "Add boolean variable to util.st"
        ]

        result = coder_node(state)

        # Verify both files were touched
        assert "files_touched" in result
        assert len(result["files_touched"]) == 2
        assert any("main.st" in f for f in result["files_touched"])
        assert any("util.st" in f for f in result["files_touched"])

        # Verify both files exist
        assert (Path(temp_workspace) / "main.st").exists()
        assert (Path(temp_workspace) / "util.st").exists()

        print("\n[OK] Coder node handles multiple steps")


class TestTesterNode:
    """Test cases for Tester Agent Node functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_tester_node_with_no_files(self, temp_workspace):
        """Test Tester node handles empty files_touched list."""
        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["files_touched"] = []

        result = tester_node(state)

        assert "test_results" in result
        assert result["test_results"]["status"] == "skipped"
        print("\n[OK] Tester node handles empty files list")

    def test_tester_node_detects_var_mismatch(self, temp_workspace):
        """Test Tester node detects mismatched VAR/END_VAR."""
        # Create file with mismatched VAR/END_VAR
        test_file = Path(temp_workspace) / "test.st"
        test_file.write_text("""
PROGRAM Test
VAR
  x : INT;
VAR
  y : BOOL;
END_VAR
END_PROGRAM
        """)

        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["files_touched"] = ["test.st"]

        result = tester_node(state)

        # Verify error was detected
        assert "messages" in result
        assert len(result["messages"]) > 0
        message_content = result["messages"][0].content
        assert "CRITICAL ERROR" in message_content
        assert "Mismatched VAR/END_VAR" in message_content

        # Verify test failed
        assert "test_results" in result
        assert result["test_results"]["status"] == "failed"

        print("\n[OK] Tester node detects VAR/END_VAR mismatch")

    def test_tester_node_detects_empty_if_block(self, temp_workspace):
        """Test Tester node detects empty IF blocks."""
        # Create file with empty IF block
        test_file = Path(temp_workspace) / "test.st"
        test_file.write_text("""
PROGRAM Test
VAR
  bCondition : BOOL;
END_VAR

IF bCondition THEN
END_IF

END_PROGRAM
        """)

        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["files_touched"] = ["test.st"]

        result = tester_node(state)

        # Verify warning was detected
        assert "messages" in result
        message_content = result["messages"][0].content
        assert "WARNING" in message_content
        assert "Empty IF block" in message_content

        print("\n[OK] Tester node detects empty IF blocks")

    def test_tester_node_passes_valid_code(self, temp_workspace):
        """Test Tester node passes valid code."""
        # Create valid file
        test_file = Path(temp_workspace) / "test.st"
        test_file.write_text("""
PROGRAM Test
VAR
  x : INT;
  bRunning : BOOL;
END_VAR

x := 42;
bRunning := TRUE;

IF bRunning THEN
  x := x + 1;
END_IF

END_PROGRAM
        """)

        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["files_touched"] = ["test.st"]

        result = tester_node(state)

        # Verify test passed
        assert "test_results" in result
        # Note: May have warnings about semicolons, but should pass critical checks
        message_content = result["messages"][0].content
        assert "CRITICAL ERROR" not in message_content

        print("\n[OK] Tester node passes valid code")

    def test_tester_node_handles_multiple_files(self, temp_workspace):
        """Test Tester node validates multiple files."""
        # Create multiple test files
        file1 = Path(temp_workspace) / "main.st"
        file1.write_text("PROGRAM Main\nVAR\nEND_VAR\nEND_PROGRAM")

        file2 = Path(temp_workspace) / "util.st"
        file2.write_text("PROGRAM Util\nVAR\nEND_VAR\nEND_PROGRAM")

        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["files_touched"] = ["main.st", "util.st"]

        result = tester_node(state)

        # Verify both files were tested
        assert "test_results" in result
        assert result["test_results"]["files_tested"] == 2

        message_content = result["messages"][0].content
        assert "main.st" in message_content
        assert "util.st" in message_content

        print("\n[OK] Tester node handles multiple files")

    def test_tester_node_handles_missing_file(self, temp_workspace):
        """Test Tester node handles missing file gracefully."""
        state = create_initial_state(
            user_request="Test",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["files_touched"] = ["nonexistent.st"]

        result = tester_node(state)

        # Verify error is reported
        assert "messages" in result
        message_content = result["messages"][0].content
        assert "ERROR" in message_content
        assert "not found" in message_content.lower()

        print("\n[OK] Tester node handles missing files")


class TestCoderTesterIntegration:
    """Integration tests combining Coder and Tester nodes."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @patch('src.agents.coder_node.CrewFactory')
    def test_coder_tester_pipeline(self, mock_factory_class, temp_workspace):
        """Test complete Coder -> Tester pipeline."""
        # Step 1: Coder creates file
        mock_code_output = CodeOutput(
            code="PROGRAM Main\nVAR\n  x : INT;\nEND_VAR\nx := 10;\nEND_PROGRAM",
            explanation="Created main program"
        )

        mock_result = Mock()
        mock_result.pydantic = mock_code_output

        mock_crew = Mock()
        mock_crew.kickoff.return_value = mock_result

        mock_factory = Mock()
        mock_factory.create_coder_crew.return_value = mock_crew
        mock_factory_class.return_value = mock_factory

        state = create_initial_state(
            user_request="Create main program",
            mode="agent",
            workspace_path=temp_workspace
        )
        state["plan"] = ["Create PROGRAM Main in main.st"]

        # Execute Coder
        coder_result = coder_node(state)

        # Step 2: Update state with Coder results
        state["files_touched"] = coder_result["files_touched"]

        # Execute Tester
        tester_result = tester_node(state)

        # Verify pipeline worked
        assert "files_touched" in coder_result
        assert len(coder_result["files_touched"]) == 1

        assert "test_results" in tester_result
        assert tester_result["test_results"]["files_tested"] == 1

        print("\n[OK] Coder->Tester pipeline works correctly")


# ============================================================================
# Manual Test Runner
# ============================================================================

def run_manual_tests():
    """
    Run manual tests without pytest for quick verification.

    Usage: python tests/test_execution.py
    """
    print("="*70)
    print("MANUAL EXECUTION NODE TESTS")
    print("="*70)

    try:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Coder Node
            print("\n[1/2] Testing Coder Node (mocked)...")
            print("-" * 70)

            with patch('src.agents.coder_node.CrewFactory') as mock_factory_class:
                mock_code_output = CodeOutput(
                    code="VAR x : INT; END_VAR",
                    explanation="Test code"
                )
                mock_result = Mock()
                mock_result.pydantic = mock_code_output

                mock_crew = Mock()
                mock_crew.kickoff.return_value = mock_result

                mock_factory = Mock()
                mock_factory.create_coder_crew.return_value = mock_crew
                mock_factory_class.return_value = mock_factory

                state = create_initial_state(
                    user_request="Test",
                    mode="agent",
                    workspace_path=tmpdir
                )
                state["plan"] = ["Add code to main.st"]

                result = coder_node(state)

                assert "files_touched" in result
                assert len(result["files_touched"]) > 0
                print(f"[OK] Coder node created: {result['files_touched']}")

            # Test 2: Tester Node
            print("\n[2/2] Testing Tester Node...")
            print("-" * 70)

            test_file = Path(tmpdir) / "test.st"
            test_file.write_text("VAR\nEND_VAR\nIF x THEN\nEND_IF")

            state = create_initial_state(
                user_request="Test",
                mode="agent",
                workspace_path=tmpdir
            )
            state["files_touched"] = ["test.st"]

            result = tester_node(state)

            assert "messages" in result
            assert "WARNING" in result["messages"][0].content
            print("[OK] Tester node detected empty IF block")

        print("\n" + "="*70)
        print("[SUCCESS] ALL MANUAL TESTS PASSED")
        print("="*70)
        print("\nTo run FULL test suite:")
        print("  pytest tests/test_execution.py -v")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_manual_tests()
