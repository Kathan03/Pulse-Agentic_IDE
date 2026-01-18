"""
Pytest Configuration and Shared Fixtures for Pulse IDE v2.6.

Provides common fixtures for:
- Temporary workspaces
- Mock settings managers
- Mock LLM clients
- Temporary files
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock


# ============================================================================
# WORKSPACE FIXTURES
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """
    Create a temporary workspace directory with sample files.

    Returns:
        Path: Temporary workspace directory.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create sample .st file
    sample_st = workspace / "main.st"
    sample_st.write_text("""
PROGRAM Main
VAR
    bMotorRun : BOOL;
    iCounter : INT;
    tmrDelay : TON;
END_VAR

(* Main program logic *)
bMotorRun := TRUE;
END_PROGRAM
""")

    # Create sample subdirectory
    (workspace / "src").mkdir()
    (workspace / "src" / "utils.st").write_text("""
FUNCTION_BLOCK TimerHelper
VAR
    tmrInternal : TON;
END_VAR
END_FUNCTION_BLOCK
""")

    # Create .pulse directory (workspace initialization)
    pulse_dir = workspace / ".pulse"
    pulse_dir.mkdir()

    return workspace


@pytest.fixture
def empty_workspace(tmp_path):
    """
    Create an empty temporary workspace directory.

    Returns:
        Path: Empty temporary workspace directory.
    """
    workspace = tmp_path / "empty_workspace"
    workspace.mkdir()
    return workspace


# ============================================================================
# SETTINGS FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings_manager():
    """
    Create a mock SettingsManager with default settings.

    Returns:
        MockSettingsManager: Mock settings manager instance.
    """
    class MockSettingsManager:
        def __init__(self):
            self.settings = {
                "api_keys": {
                    "openai": "sk-test-key",
                    "anthropic": ""
                },
                "models": {
                    "master_agent": "gpt-4o",
                    "crew_coder": "gpt-4o",
                    "autogen_auditor": "gpt-4o-mini"
                },
                "preferences": {
                    "theme": "dark",
                    "enable_crew": True,
                    "enable_autogen": True
                }
            }

        def load_settings(self):
            return self.settings.copy()

        def save_settings(self, settings):
            self.settings = settings
            return True

        def get_preference(self, key, default=None):
            return self.settings.get("preferences", {}).get(key, default)

        def set_preference(self, key, value):
            self.settings["preferences"][key] = value
            return True

        def get_model(self, key):
            return self.settings.get("models", {}).get(key, "gpt-4o")

        def get_config_file_path(self):
            return Path("/mock/config.json")

        def reset_to_defaults(self):
            self.settings = {
                "api_keys": {"openai": "", "anthropic": ""},
                "models": {
                    "master_agent": "gpt-4o",
                    "crew_coder": "gpt-4o",
                    "autogen_auditor": "gpt-4o-mini"
                },
                "preferences": {
                    "theme": "dark",
                    "enable_crew": True,
                    "enable_autogen": True
                }
            }
            return True

    return MockSettingsManager()


@pytest.fixture
def patched_settings_manager(mock_settings_manager, monkeypatch):
    """
    Patch get_settings_manager to return mock.

    Returns:
        MockSettingsManager: The mock settings manager.
    """
    def mock_get_settings_manager():
        return mock_settings_manager

    monkeypatch.setattr(
        "src.core.settings.get_settings_manager",
        mock_get_settings_manager
    )

    return mock_settings_manager


# ============================================================================
# LLM FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """
    Factory fixture for creating mock LLM responses.

    Returns:
        Callable: Function to create mock responses.
    """
    def _create_response(response_type="direct_answer", content="Mock response", tool=None, args=None):
        if response_type == "direct_answer":
            return {"type": "direct_answer", "content": content}
        elif response_type == "tool_call":
            return {"type": "tool_call", "tool": tool, "args": args or {}}
        else:
            return {"type": response_type}

    return _create_response


# ============================================================================
# ASYNC FIXTURES
# ============================================================================

@pytest.fixture
def event_loop():
    """
    Create event loop for async tests.

    Returns:
        asyncio.AbstractEventLoop: Event loop instance.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# TOOL FIXTURES
# ============================================================================

@pytest.fixture
def mock_subprocess(monkeypatch):
    """
    Mock subprocess.Popen for terminal tests.

    Returns:
        MagicMock: Mock Popen class.
    """
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"stdout output", b"")
    mock_process.poll.return_value = 0
    mock_process.pid = 12345

    mock_popen = MagicMock(return_value=mock_process)

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    return mock_popen


# ============================================================================
# STATE FIXTURES
# ============================================================================

@pytest.fixture
def initial_master_state(temp_workspace):
    """
    Create initial MasterState for testing.

    Returns:
        MasterState: Initial state dictionary.
    """
    from src.agents.state import create_initial_master_state

    return create_initial_master_state(
        user_input="Test request",
        project_root=str(temp_workspace),
        settings_snapshot={
            "provider": "openai",
            "model": "gpt-4o",
            "enable_crew": True,
            "enable_autogen": True
        }
    )


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_global_state():
    """
    Cleanup global state after each test.
    """
    yield

    # Reset process registry
    try:
        from src.core.processes import _process_registry
        _process_registry.clear()
    except (ImportError, NameError):
        pass

