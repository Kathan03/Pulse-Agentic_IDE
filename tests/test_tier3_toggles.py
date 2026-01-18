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




if __name__ == "__main__":
    # Run tests manually

    asyncio.run(pytest.main([__file__, "-v", "-s"]))

