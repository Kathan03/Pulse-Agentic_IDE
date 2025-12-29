"""
Agent nodes for the Pulse IDE LangGraph workflow.

=== V2.6 Unified Master Loop Architecture ===

This module provides the Unified Master Loop (hub-and-spoke) architecture:

- state: MasterState schema with bounded memory and approval models
- master_graph: Hub-and-spoke architecture with interrupt support
- runtime: Entrypoint with global lock and cancellation

The Master Agent (The Brain) orchestrates work through a Tool Belt (The Hands):
- Tier 1: Atomic tools (file ops, patches, search)
- Tier 2: Permissioned tools (terminal commands, dependencies)
- Tier 3: Agentic tools (CrewAI builder, AutoGen auditor)

Key Features:
- Single active run only (global lock)
- Human-in-the-loop approvals for patches and terminal commands
- Bounded message history with rolling summary
- Vibe status streaming
- Clean cancellation support
"""

# Phase 3: Master Agent State
from src.agents.state import (
    MasterState,
    PatchPlan,
    CommandPlan,
    ApprovalRequest,
    ToolOutput,
    create_initial_master_state,
    truncate_messages,
)

# Phase 3: Master Graph
from src.agents.master_graph import (
    create_master_graph,
    master_agent_node,
    tool_execution_node,
)

# Phase 3: Runtime (with global lock)
from src.agents.runtime import (
    run_agent,
    cancel_current_run,
    get_current_run_id,
    is_run_active,
    resume_with_approval,
    RunAlreadyActiveError,
)

__all__ = [
    # State models
    "MasterState",
    "PatchPlan",
    "CommandPlan",
    "ApprovalRequest",
    "ToolOutput",
    "create_initial_master_state",
    "truncate_messages",

    # Master Graph
    "create_master_graph",
    "master_agent_node",
    "tool_execution_node",

    # Runtime
    "run_agent",
    "cancel_current_run",
    "get_current_run_id",
    "is_run_active",
    "resume_with_approval",
    "RunAlreadyActiveError",
]
