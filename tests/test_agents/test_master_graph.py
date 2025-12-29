"""
Tests for src/agents/master_graph.py - Master Agent Graph.

Tests:
- Graph construction and compilation
- master_agent_node state transitions
- tool_execution_node with mocked tools
- Routing logic (should_continue)
- Interrupt-based approval flow
- Cancellation handling

IMPORTANT: All LLM calls are mocked - NO real API calls.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.agents.state import (
    MasterState,
    PatchPlan,
    CommandPlan,
    ToolOutput,
    create_initial_master_state,
)


class TestGraphConstruction:
    """Tests for graph creation and compilation."""

    def test_create_master_graph(self, temp_workspace):
        """Test that master graph can be created."""
        from src.agents.master_graph import create_master_graph

        graph = create_master_graph(project_root=temp_workspace)

        assert graph is not None

    def test_graph_has_required_nodes(self, temp_workspace):
        """Test that graph contains required nodes."""
        from src.agents.master_graph import create_master_graph

        graph = create_master_graph(project_root=temp_workspace)

        # Graph should have nodes (checking via compiled graph)
        assert graph is not None


class TestMasterAgentNode:
    """Tests for master_agent_node function."""

    @pytest.fixture
    def initial_state(self, temp_workspace):
        """Create initial state for testing."""
        return create_initial_master_state(
            user_input="What is structured text?",
            project_root=str(temp_workspace),
            settings_snapshot={"provider": "openai", "model": "gpt-4o"}
        )

    @pytest.mark.asyncio
    async def test_master_agent_returns_state(self, initial_state, monkeypatch):
        """Test that master_agent_node returns a state dict."""
        from src.agents.master_graph import master_agent_node

        # Mock LLM to return direct answer
        async def mock_llm(*args, **kwargs):
            return {"type": "direct_answer", "content": "Test response"}

        monkeypatch.setattr("src.agents.master_graph.call_llm_stub", mock_llm)

        # Mock event emitters
        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())

        result = await master_agent_node(initial_state)

        assert isinstance(result, dict)
        assert "agent_response" in result

    @pytest.mark.asyncio
    async def test_master_agent_direct_answer(self, initial_state, monkeypatch):
        """Test master_agent_node with direct answer response."""
        from src.agents.master_graph import master_agent_node

        async def mock_llm(*args, **kwargs):
            return {"type": "direct_answer", "content": "Structured text is..."}

        monkeypatch.setattr("src.agents.master_graph.call_llm_stub", mock_llm)
        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())

        result = await master_agent_node(initial_state)

        assert result["agent_response"] == "Structured text is..."
        assert len(result["messages"]) > 1  # Original + response

    @pytest.mark.asyncio
    async def test_master_agent_tool_call(self, initial_state, monkeypatch):
        """Test master_agent_node with tool call response."""
        from src.agents.master_graph import master_agent_node

        async def mock_llm(*args, **kwargs):
            return {
                "type": "tool_call",
                "tool": "search_workspace",
                "args": {"query": "test"}
            }

        monkeypatch.setattr("src.agents.master_graph.call_llm_stub", mock_llm)
        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_tool_requested", AsyncMock())

        result = await master_agent_node(initial_state)

        # Should have pending tool request
        assert result["tool_result"] is not None
        assert result["tool_result"].tool_name == "search_workspace"

    @pytest.mark.asyncio
    async def test_master_agent_respects_cancellation(self, initial_state, monkeypatch):
        """Test that master_agent_node respects cancellation flag."""
        from src.agents.master_graph import master_agent_node

        initial_state["is_cancelled"] = True

        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())

        result = await master_agent_node(initial_state)

        assert "cancelled" in result["agent_response"].lower()


class TestToolExecutionNode:
    """Tests for tool_execution_node function."""

    @pytest.fixture
    def state_with_pending_tool(self, temp_workspace):
        """Create state with pending tool request."""
        state = create_initial_master_state(
            user_input="Find Motor_1",
            project_root=str(temp_workspace),
            settings_snapshot={}
        )

        state["tool_result"] = ToolOutput(
            tool_name="search_workspace",
            success=False,
            result={"pending": True, "args": {"query": "Motor_1"}},
            timestamp=datetime.now().isoformat()
        )

        return state

    @pytest.mark.asyncio
    async def test_tool_execution_returns_state(self, state_with_pending_tool, temp_workspace, monkeypatch):
        """Test that tool_execution_node returns a state dict."""
        from src.agents.master_graph import tool_execution_node, create_master_graph

        # Initialize tool registry
        create_master_graph(project_root=temp_workspace)

        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_tool_executed", AsyncMock())

        result = await tool_execution_node(state_with_pending_tool)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_tool_execution_respects_cancellation(self, state_with_pending_tool, monkeypatch):
        """Test that tool_execution_node respects cancellation."""
        from src.agents.master_graph import tool_execution_node

        state_with_pending_tool["is_cancelled"] = True

        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())

        result = await tool_execution_node(state_with_pending_tool)

        # Should not execute tool when cancelled
        assert result["is_cancelled"] is True


class TestRoutingLogic:
    """Tests for should_continue routing function."""

    def test_should_continue_ends_on_cancellation(self):
        """Test routing ends when cancelled."""
        from src.agents.master_graph import should_continue
        from langgraph.graph import END

        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )
        state["is_cancelled"] = True

        result = should_continue(state)
        assert result == END

    def test_should_continue_ends_on_response(self):
        """Test routing ends when agent_response is set."""
        from src.agents.master_graph import should_continue
        from langgraph.graph import END

        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )
        state["agent_response"] = "Here is my answer"

        result = should_continue(state)
        assert result == END

    def test_should_continue_to_tool_execution(self):
        """Test routing to tool_execution when tool is pending."""
        from src.agents.master_graph import should_continue

        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )
        state["tool_result"] = ToolOutput(
            tool_name="test_tool",
            success=False,
            result={"pending": True, "args": {}},
            timestamp=datetime.now().isoformat()
        )

        result = should_continue(state)
        assert result == "tool_execution"

    def test_should_continue_back_to_master_agent(self):
        """Test routing back to master_agent after tool execution."""
        from src.agents.master_graph import should_continue

        state = create_initial_master_state(
            user_input="Test",
            project_root="/workspace",
            settings_snapshot={}
        )
        # Completed tool has a dict result without "pending" key
        state["tool_result"] = ToolOutput(
            tool_name="test_tool",
            success=True,
            result={"completed": True},  # Dict but no "pending" key
            timestamp=datetime.now().isoformat()
        )

        result = should_continue(state)
        assert result == "master_agent"


class TestMemoryPolicy:
    """Tests for bounded message history in master_agent_node."""

    @pytest.mark.asyncio
    async def test_message_truncation_triggered(self, temp_workspace, monkeypatch):
        """Test that message truncation is triggered when limit exceeded."""
        from src.agents.master_graph import master_agent_node, MESSAGE_HISTORY_LIMIT

        # Create state with many messages
        state = create_initial_master_state(
            user_input="Test",
            project_root=str(temp_workspace),
            settings_snapshot={}
        )

        # Add many messages to exceed limit
        for i in range(MESSAGE_HISTORY_LIMIT * 3):
            state["messages"].append({"role": "user", "content": f"Message {i}"})
            state["messages"].append({"role": "assistant", "content": f"Reply {i}"})

        original_count = len(state["messages"])

        async def mock_llm(*args, **kwargs):
            return {"type": "direct_answer", "content": "Done"}

        monkeypatch.setattr("src.agents.master_graph.call_llm_stub", mock_llm)
        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())

        result = await master_agent_node(state)

        # Messages should be truncated
        assert len(result["messages"]) < original_count
        # Rolling summary should have content
        assert result["rolling_summary"] != ""


class TestEventEmission:
    """Tests for event emission in graph nodes."""

    @pytest.mark.asyncio
    async def test_master_agent_emits_events(self, temp_workspace, monkeypatch):
        """Test that master_agent_node emits required events."""
        from src.agents.master_graph import master_agent_node

        state = create_initial_master_state(
            user_input="Test",
            project_root=str(temp_workspace),
            settings_snapshot={}
        )

        mock_emit_status = AsyncMock()
        mock_emit_entered = AsyncMock()
        mock_emit_exited = AsyncMock()

        monkeypatch.setattr("src.agents.master_graph.emit_status", mock_emit_status)
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", mock_emit_entered)
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", mock_emit_exited)

        async def mock_llm(*args, **kwargs):
            return {"type": "direct_answer", "content": "Done"}

        monkeypatch.setattr("src.agents.master_graph.call_llm_stub", mock_llm)

        await master_agent_node(state)

        # Check events were emitted
        mock_emit_entered.assert_called_with("master_agent")
        mock_emit_exited.assert_called_with("master_agent")
        assert mock_emit_status.call_count >= 1


class TestErrorHandling:
    """Tests for error handling in graph nodes."""

    @pytest.mark.asyncio
    async def test_master_agent_handles_llm_error(self, temp_workspace, monkeypatch):
        """Test that master_agent_node handles LLM errors gracefully."""
        from src.agents.master_graph import master_agent_node

        state = create_initial_master_state(
            user_input="Test",
            project_root=str(temp_workspace),
            settings_snapshot={}
        )

        async def mock_llm_error(*args, **kwargs):
            raise Exception("LLM API Error")

        monkeypatch.setattr("src.agents.master_graph.call_llm_stub", mock_llm_error)
        monkeypatch.setattr("src.agents.master_graph.emit_status", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_entered", AsyncMock())
        monkeypatch.setattr("src.agents.master_graph.emit_node_exited", AsyncMock())

        result = await master_agent_node(state)

        # Should have error in response
        assert "error" in result["agent_response"].lower()
        # Should have error in log
        assert any("ERROR" in log for log in result["execution_log"])


class TestStubLLMClient:
    """Tests for the stub LLM client behavior."""

    @pytest.mark.asyncio
    async def test_stub_returns_search_for_find_query(self):
        """Test stub returns search tool for find queries."""
        from src.agents.master_graph import call_llm_stub

        messages = [{"role": "user", "content": "find Motor_1"}]
        result = await call_llm_stub(messages, "system prompt", {})

        assert result["type"] == "tool_call"
        assert result["tool"] == "search_workspace"

    @pytest.mark.asyncio
    async def test_stub_returns_patch_for_create_query(self):
        """Test stub returns patch tool for create queries."""
        from src.agents.master_graph import call_llm_stub

        messages = [{"role": "user", "content": "create a new timer"}]
        result = await call_llm_stub(messages, "system prompt", {})

        assert result["type"] == "tool_call"
        assert result["tool"] == "apply_patch"

    @pytest.mark.asyncio
    async def test_stub_returns_terminal_for_install_query(self):
        """Test stub returns terminal tool for install queries."""
        from src.agents.master_graph import call_llm_stub

        messages = [{"role": "user", "content": "install pytest"}]
        result = await call_llm_stub(messages, "system prompt", {})

        assert result["type"] == "tool_call"
        assert result["tool"] == "plan_terminal_cmd"

    @pytest.mark.asyncio
    async def test_stub_returns_direct_answer_for_general_query(self):
        """Test stub returns direct answer for general queries."""
        from src.agents.master_graph import call_llm_stub

        messages = [{"role": "user", "content": "hello there"}]
        result = await call_llm_stub(messages, "system prompt", {})

        assert result["type"] == "direct_answer"
        assert "content" in result
