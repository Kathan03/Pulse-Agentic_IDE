"""
Test Tier 3 Tool Toggles (Phase 6).

Verifies that:
1. enable_crew OFF → implement_feature returns no-spend response
2. enable_autogen OFF → diagnose_project runs Stage A only
3. Toggles ON → full functionality works

Run with: pytest tests/test_tier3_toggles.py -v
"""

import pytest
import asyncio
from pathlib import Path
from src.core.settings import SettingsManager
from src.tools.builder_crew import implement_feature
from src.tools.auditor_swarm import diagnose_project


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with sample PLC files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create a sample .st file
    sample_file = workspace / "test.st"
    sample_file.write_text("""
VAR
    bMotorRun : BOOL;
    T_Delay : TON;
END_VAR

(* Main logic *)
bMotorRun := T_Delay.Q;
""")

    return workspace


@pytest.fixture
def settings_manager_mock(monkeypatch):
    """Create a mock SettingsManager for testing."""
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
                    "enable_autogen": True,
                    "enable_crew": True
                }
            }

        def load_settings(self):
            return self.settings.copy()

        def save_settings(self, settings):
            self.settings = settings
            return True

        def set_preference(self, key, value):
            self.settings["preferences"][key] = value
            return True

        def get_preference(self, key, default=None):
            return self.settings.get("preferences", {}).get(key, default)

    mock_manager = MockSettingsManager()

    # Monkey-patch the get_settings_manager function
    def mock_get_settings_manager():
        return mock_manager

    monkeypatch.setattr(
        "src.tools.builder_crew.get_settings_manager",
        mock_get_settings_manager
    )
    monkeypatch.setattr(
        "src.tools.auditor_swarm.get_settings_manager",
        mock_get_settings_manager
    )

    return mock_manager


# ============================================================================
# TEST: enable_crew TOGGLE
# ============================================================================

@pytest.mark.asyncio
async def test_implement_feature_toggle_off(temp_workspace, settings_manager_mock):
    """
    Test: enable_crew OFF → implement_feature returns no-spend response.

    Expected:
    - No API calls made
    - Returns structured dict with empty patch_plans
    - metadata.crew_enabled = False
    """
    # Disable CrewAI toggle
    settings_manager_mock.set_preference("enable_crew", False)

    # Call implement_feature
    result = await implement_feature(
        request="Add a timer to the conveyor logic",
        project_root=temp_workspace,
        context={}
    )

    # Verify no-spend response
    assert result["patch_plans"] == []
    assert "disabled" in result["summary"].lower()
    assert result["metadata"]["crew_enabled"] is False
    assert result["metadata"]["budget_mode"] == "disabled"

    print("✓ Test passed: enable_crew OFF → no spend")


@pytest.mark.asyncio
async def test_implement_feature_toggle_on_no_api_key(temp_workspace, settings_manager_mock):
    """
    Test: enable_crew ON but no API key → returns error response.

    Expected:
    - Returns error message about missing API key
    - No API calls made
    """
    # Enable CrewAI toggle
    settings_manager_mock.set_preference("enable_crew", True)

    # Remove API key
    settings_manager_mock.settings["api_keys"]["openai"] = ""

    # Call implement_feature
    result = await implement_feature(
        request="Add a timer to the conveyor logic",
        project_root=temp_workspace,
        context={}
    )

    # Verify error response
    assert result["patch_plans"] == []
    assert "api key" in result["summary"].lower() or "error" in result["summary"].lower()
    assert result["metadata"].get("error") == "missing_api_key"

    print("✓ Test passed: enable_crew ON but no API key → error response")


# ============================================================================
# TEST: enable_autogen TOGGLE
# ============================================================================

@pytest.mark.asyncio
async def test_diagnose_project_toggle_off(temp_workspace, settings_manager_mock):
    """
    Test: enable_autogen OFF → diagnose_project runs Stage A only.

    Expected:
    - Runs deterministic checks (Stage A)
    - No AutoGen debate (Stage B)
    - metadata.autogen_enabled = False
    - metadata.stage = "A_only"
    """
    # Disable AutoGen toggle
    settings_manager_mock.set_preference("enable_autogen", False)

    # Call diagnose_project
    result = await diagnose_project(
        focus_area="file structure",
        project_root=temp_workspace,
        context={}
    )

    # Verify Stage A only
    assert "risk_level" in result
    assert "findings" in result
    assert "prioritized_fixes" in result
    assert "verification_steps" in result
    assert result["metadata"]["autogen_enabled"] is False
    assert result["metadata"]["stage"] == "A_only"
    assert result["metadata"]["deterministic_checks"] is True

    print("✓ Test passed: enable_autogen OFF → Stage A only")


@pytest.mark.asyncio
async def test_diagnose_project_toggle_on_no_api_key(temp_workspace, settings_manager_mock):
    """
    Test: enable_autogen ON but no API key → falls back to Stage A.

    Expected:
    - Runs Stage A (deterministic checks)
    - Stage B skipped due to missing API key
    - metadata.error = "missing_api_key"
    """
    # Enable AutoGen toggle
    settings_manager_mock.set_preference("enable_autogen", True)

    # Remove API key
    settings_manager_mock.settings["api_keys"]["openai"] = ""

    # Call diagnose_project
    result = await diagnose_project(
        focus_area="file structure",
        project_root=temp_workspace,
        context={}
    )

    # Verify Stage A fallback
    assert "risk_level" in result
    assert result["metadata"]["autogen_enabled"] is False
    assert result["metadata"].get("error") == "missing_api_key"

    print("✓ Test passed: enable_autogen ON but no API key → Stage A fallback")


# ============================================================================
# TEST: BUDGET CONTROLS
# ============================================================================

@pytest.mark.asyncio
async def test_diagnose_project_stage_a_only(temp_workspace, settings_manager_mock):
    """
    Test: Deterministic Stage A produces valid output structure.

    Expected:
    - Returns valid JSON with all required keys
    - findings list may be empty or populated
    - risk_level is one of: HIGH, MEDIUM, LOW
    """
    # Disable AutoGen to test Stage A in isolation
    settings_manager_mock.set_preference("enable_autogen", False)

    # Call diagnose_project
    result = await diagnose_project(
        focus_area="syntax validation",
        project_root=temp_workspace,
        context={}
    )

    # Verify required keys
    required_keys = {"risk_level", "findings", "prioritized_fixes", "verification_steps", "metadata"}
    assert required_keys.issubset(result.keys())

    # Verify risk_level is valid
    assert result["risk_level"] in ["HIGH", "MEDIUM", "LOW"]

    # Verify findings structure
    for finding in result["findings"]:
        assert "severity" in finding
        assert "file" in finding
        assert "line" in finding
        assert "message" in finding
        assert finding["severity"] in ["ERROR", "WARNING", "INFO"]

    print("✓ Test passed: Stage A produces valid output structure")


# ============================================================================
# TEST: PHASE 7 UI COMPONENTS
# ============================================================================

class TestUIBridge:
    """Tests for UIBridge async event handling."""

    def test_ui_bridge_singleton(self):
        """Test that get_ui_bridge returns singleton."""
        from src.ui.bridge import get_ui_bridge, reset_ui_bridge

        reset_ui_bridge()
        bridge1 = get_ui_bridge()
        bridge2 = get_ui_bridge()
        assert bridge1 is bridge2

    def test_ui_state_defaults(self):
        """Test UIState default values."""
        from src.ui.bridge import UIState

        state = UIState()
        assert state.is_running is False
        assert state.pending_approval is None
        assert state.current_vibe == ""
        assert state.queued_input is None
        assert state.current_run_id is None

    def test_ui_state_reset(self):
        """Test UIState reset method."""
        from src.ui.bridge import UIState

        state = UIState()
        state.is_running = True
        state.pending_approval = {"type": "patch"}
        state.current_vibe = "Wondering"
        state.current_run_id = "test-123"
        state.queued_input = "queued message"

        state.reset()

        assert state.is_running is False
        assert state.pending_approval is None
        assert state.current_vibe == ""
        assert state.current_run_id is None
        # queued_input is preserved
        assert state.queued_input == "queued message"

    def test_start_run_lock(self):
        """Test single-run lock enforcement."""
        from src.ui.bridge import UIBridge

        bridge = UIBridge()

        # First run should succeed
        assert bridge.start_run("run-1") is True
        assert bridge.state.is_running is True
        assert bridge.state.current_run_id == "run-1"

        # Second run should fail
        assert bridge.start_run("run-2") is False
        assert bridge.state.current_run_id == "run-1"  # Still first run

        # End run
        bridge.end_run()
        assert bridge.state.is_running is False

        # Now should succeed
        assert bridge.start_run("run-3") is True

    def test_queue_input(self):
        """Test input queuing during runs."""
        from src.ui.bridge import UIBridge

        bridge = UIBridge()
        bridge.start_run("run-1")

        bridge.queue_input("test message")
        assert bridge.state.queued_input == "test message"

        queued = bridge.get_queued_input()
        assert queued == "test message"
        assert bridge.state.queued_input is None  # Cleared after get


class TestVibeCategories:
    """Tests for VibeLoader component."""

    def test_vibe_categories(self):
        """Test vibe word categorization."""
        from src.ui.bridge import get_vibe_category, VibeCategory

        assert get_vibe_category("Wondering") == VibeCategory.THINKING
        assert get_vibe_category("Cogitating") == VibeCategory.THINKING
        assert get_vibe_category("Mustering") == VibeCategory.CONTEXT
        assert get_vibe_category("Completing") == VibeCategory.ACTION
        assert get_vibe_category("Unknown") is None


class TestUIEvents:
    """Tests for UI event types."""

    def test_ui_event_creation(self):
        """Test UIEvent creation."""
        from src.ui.bridge import UIEvent

        event = UIEvent(type="test_event", data={"key": "value"})
        assert event.type == "test_event"
        assert event.data["key"] == "value"
        assert event.timestamp is not None

    def test_ui_event_from_core_event(self):
        """Test UIEvent.from_core_event conversion."""
        from src.ui.bridge import UIEvent
        from src.core.events import Event, EventType

        core_event = Event(EventType.STATUS_CHANGED, {"status": "Wondering"})
        ui_event = UIEvent.from_core_event(core_event)

        assert ui_event.type == "status_changed"
        assert ui_event.data["status"] == "Wondering"


class TestProcessCleanup:
    """Tests for process cleanup."""

    def test_cleanup_processes_empty(self):
        """Test cleanup with no processes."""
        from src.core.processes import cleanup_processes, list_processes

        # Should not raise even with no processes
        report = cleanup_processes()
        assert report["total"] == 0
        assert report["killed"] == 0
        assert report["failed"] == []


if __name__ == "__main__":
    # Run tests manually
    import sys

    asyncio.run(pytest.main([__file__, "-v", "-s"]))
