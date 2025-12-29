"""
Tests for src/agents/state.py - MasterState Schema.

Tests:
- State model structure and defaults
- PatchPlan and CommandPlan models
- ApprovalRequest and ToolOutput models
- create_initial_master_state helper
- truncate_messages memory policy
"""

import pytest
from datetime import datetime

from src.agents.state import (
    MasterState,
    PatchPlan,
    CommandPlan,
    ApprovalRequest,
    ToolOutput,
    create_initial_master_state,
    truncate_messages,
    MESSAGE_HISTORY_LIMIT,
)


class TestPatchPlan:
    """Tests for PatchPlan model."""

    def test_patch_plan_required_fields(self):
        """Test PatchPlan with required fields."""
        plan = PatchPlan(
            file_path="main.st",
            diff="--- a/main.st\n+++ b/main.st",
            rationale="Add timer logic"
        )

        assert plan.file_path == "main.st"
        assert plan.diff.startswith("---")
        assert plan.rationale == "Add timer logic"
        assert plan.action == "modify"  # Default

    def test_patch_plan_all_actions(self):
        """Test PatchPlan with all action types."""
        for action in ["create", "modify", "delete"]:
            plan = PatchPlan(
                file_path="test.st",
                diff="...",
                rationale="Test",
                action=action
            )
            assert plan.action == action

    def test_patch_plan_serialization(self):
        """Test PatchPlan model_dump for serialization."""
        plan = PatchPlan(
            file_path="test.st",
            diff="diff content",
            rationale="Test reason",
            action="create"
        )

        data = plan.model_dump()

        assert data["file_path"] == "test.st"
        assert data["diff"] == "diff content"
        assert data["rationale"] == "Test reason"
        assert data["action"] == "create"


class TestCommandPlan:
    """Tests for CommandPlan model."""

    def test_command_plan_required_fields(self):
        """Test CommandPlan with required fields."""
        plan = CommandPlan(
            command="pip install pytest",
            rationale="Install testing framework",
            risk_label="MEDIUM"
        )

        assert plan.command == "pip install pytest"
        assert plan.rationale == "Install testing framework"
        assert plan.risk_label == "MEDIUM"
        assert plan.working_dir is None  # Optional

    def test_command_plan_all_risk_levels(self):
        """Test CommandPlan with all risk levels."""
        for risk in ["LOW", "MEDIUM", "HIGH"]:
            plan = CommandPlan(
                command="test",
                rationale="Test",
                risk_label=risk
            )
            assert plan.risk_label == risk

    def test_command_plan_with_working_dir(self):
        """Test CommandPlan with optional working_dir."""
        plan = CommandPlan(
            command="npm install",
            rationale="Install deps",
            risk_label="MEDIUM",
            working_dir="/path/to/project"
        )

        assert plan.working_dir == "/path/to/project"


class TestApprovalRequest:
    """Tests for ApprovalRequest model."""

    def test_approval_request_patch_type(self):
        """Test ApprovalRequest for patch approval."""
        request = ApprovalRequest(
            type="patch",
            data={"file_path": "main.st", "diff": "..."},
            approved=None  # Pending
        )

        assert request.type == "patch"
        assert request.approved is None

    def test_approval_request_terminal_type(self):
        """Test ApprovalRequest for terminal approval."""
        request = ApprovalRequest(
            type="terminal",
            data={"command": "rm -rf /tmp/test", "risk_label": "HIGH"},
            approved=None
        )

        assert request.type == "terminal"

    def test_approval_request_states(self):
        """Test ApprovalRequest approval states."""
        # Pending
        pending = ApprovalRequest(type="patch", data={}, approved=None)
        assert pending.approved is None

        # Approved
        approved = ApprovalRequest(type="patch", data={}, approved=True)
        assert approved.approved is True

        # Denied
        denied = ApprovalRequest(type="patch", data={}, approved=False)
        assert denied.approved is False


class TestToolOutput:
    """Tests for ToolOutput model."""

    def test_tool_output_success(self):
        """Test ToolOutput for successful execution."""
        output = ToolOutput(
            tool_name="search_workspace",
            success=True,
            result={"matches": ["file1.st", "file2.st"]},
            timestamp=datetime.now().isoformat()
        )

        assert output.tool_name == "search_workspace"
        assert output.success is True
        assert output.error is None

    def test_tool_output_failure(self):
        """Test ToolOutput for failed execution."""
        output = ToolOutput(
            tool_name="apply_patch",
            success=False,
            result="",
            error="User denied approval",
            timestamp=datetime.now().isoformat()
        )

        assert output.success is False
        assert output.error == "User denied approval"


class TestCreateInitialMasterState:
    """Tests for create_initial_master_state helper."""

    def test_creates_valid_state(self):
        """Test that helper creates valid MasterState."""
        state = create_initial_master_state(
            user_input="Add a timer to the conveyor logic",
            project_root="/workspace/my_project",
            settings_snapshot={"provider": "openai", "model": "gpt-4o"}
        )

        # Check all required fields
        assert "messages" in state
        assert "rolling_summary" in state
        assert "current_status" in state
        assert "pending_interrupt" in state
        assert "is_cancelled" in state
        assert "tool_result" in state
        assert "patch_plans" in state
        assert "terminal_commands" in state
        assert "files_touched" in state
        assert "workspace_context" in state
        assert "settings_snapshot" in state
        assert "agent_response" in state
        assert "execution_log" in state

    def test_initial_message_contains_user_input(self):
        """Test that initial state contains user message."""
        state = create_initial_master_state(
            user_input="What is structured text?",
            project_root="/workspace",
            settings_snapshot={}
        )

        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "user"
        assert state["messages"][0]["content"] == "What is structured text?"

    def test_initial_status_is_wondering(self):
        """Test that initial vibe status is 'Wondering'."""
        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )

        assert state["current_status"] == "Wondering"

    def test_initial_state_is_not_cancelled(self):
        """Test that initial state is not cancelled."""
        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )

        assert state["is_cancelled"] is False

    def test_initial_lists_are_empty(self):
        """Test that initial lists are empty."""
        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )

        assert state["patch_plans"] == []
        assert state["terminal_commands"] == []
        assert state["files_touched"] == []
        assert state["execution_log"] == []

    def test_workspace_context_contains_project_root(self):
        """Test that workspace_context has project_root."""
        state = create_initial_master_state(
            user_input="Test",
            project_root="/my/project",
            settings_snapshot={}
        )

        assert state["workspace_context"]["project_root"] == "/my/project"


class TestTruncateMessages:
    """Tests for truncate_messages memory policy."""

    def test_no_truncation_below_limit(self):
        """Test that messages below limit are not truncated."""
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(5)
        ]

        recent, summary = truncate_messages(messages, limit=10)

        assert recent == messages
        assert summary == ""

    def test_truncation_at_limit(self):
        """Test truncation when at double the limit (turns)."""
        # Create 30 messages (15 turns, each turn = user + assistant)
        messages = []
        for i in range(15):
            messages.append({"role": "user", "content": f"User message {i}"})
            messages.append({"role": "assistant", "content": f"Assistant reply {i}"})

        recent, summary = truncate_messages(messages, limit=5)

        # Should keep last 10 messages (5 turns * 2)
        assert len(recent) == 10
        assert summary != ""

    def test_summary_contains_old_messages(self):
        """Test that summary contains content from old messages."""
        messages = [
            {"role": "user", "content": "First important question"},
            {"role": "assistant", "content": "First important answer"},
        ]
        # Add more to exceed limit
        for i in range(20):
            messages.append({"role": "user", "content": f"Message {i}"})
            messages.append({"role": "assistant", "content": f"Reply {i}"})

        _, summary = truncate_messages(messages, limit=5)

        assert "First important" in summary

    def test_recent_messages_are_most_recent(self):
        """Test that recent messages are the most recent ones."""
        messages = []
        for i in range(20):
            messages.append({"role": "user", "content": f"Message {i}"})
            messages.append({"role": "assistant", "content": f"Reply {i}"})

        recent, _ = truncate_messages(messages, limit=5)

        # Last message should be about "19"
        assert "19" in recent[-1]["content"]

    def test_message_limit_constant(self):
        """Test that MESSAGE_HISTORY_LIMIT is defined."""
        assert MESSAGE_HISTORY_LIMIT > 0
        assert MESSAGE_HISTORY_LIMIT <= 20  # Reasonable upper bound


class TestMasterStateTypedDict:
    """Tests for MasterState TypedDict structure."""

    def test_master_state_is_typed_dict(self):
        """Test that MasterState is a TypedDict."""
        # MasterState is a TypedDict, so it's a dict subclass
        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )

        assert isinstance(state, dict)

    def test_master_state_fields_accessible(self):
        """Test that all fields are accessible via keys."""
        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )

        # All required fields should be accessible
        _ = state["messages"]
        _ = state["rolling_summary"]
        _ = state["current_status"]
        _ = state["pending_interrupt"]
        _ = state["is_cancelled"]
        _ = state["tool_result"]
        _ = state["patch_plans"]
        _ = state["terminal_commands"]
        _ = state["files_touched"]
        _ = state["workspace_context"]
        _ = state["settings_snapshot"]
        _ = state["agent_response"]
        _ = state["execution_log"]
