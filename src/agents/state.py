"""
Master Agent State Schema for Pulse IDE v2.6 (Phase 3).

Defines MasterState for the Unified Master Loop (hub-and-spoke) architecture.
This state schema supports:
- Bounded message history with rolling summary
- Interrupt-based approvals (patch/terminal)
- Vibe status streaming
- Clean cancellation
- Context containment (CrewAI/AutoGen transcripts excluded)

Memory Policy:
- Keep last N turns verbatim in `messages`
- Store older turns in `rolling_summary`
- Store full transcripts in SQLite (but not in LLM context)
"""

from typing import TypedDict, List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# CONSTANTS
# ============================================================================

# Memory policy: keep last N message turns in context
MESSAGE_HISTORY_LIMIT = 10  # Keep last 10 turns (20 messages: 10 user + 10 assistant)


# ============================================================================
# APPROVAL REQUEST MODELS
# ============================================================================

class PatchPlan(BaseModel):
    """
    Structured patch plan for code changes requiring approval.

    Attributes:
        file_path: Target file path (relative to project root).
        diff: Unified diff string.
        rationale: Explanation of why this change is needed.
        action: Type of change ("create", "modify", "delete").
        original_content: Original file content (for preview).
        patched_content: Patched file content (for preview and execution).
        additions: Number of lines added.
        deletions: Number of lines deleted.
    """
    file_path: str = Field(..., description="Target file path (relative to project root)")
    diff: str = Field(..., description="Unified diff string")
    rationale: str = Field(..., description="Explanation of why this change is needed")
    action: Literal["create", "modify", "delete"] = Field(default="modify", description="Type of change")
    original_content: Optional[str] = Field(None, description="Original file content (for preview)")
    patched_content: Optional[str] = Field(None, description="Patched file content (for preview and execution)")
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")


class CommandPlan(BaseModel):
    """
    Structured terminal command plan requiring approval.

    Attributes:
        command: Shell command to execute.
        rationale: Explanation of why this command is needed.
        risk_label: Risk assessment ("LOW", "MEDIUM", "HIGH").
        working_dir: Working directory for command execution (optional).
    """
    command: str = Field(..., description="Shell command to execute")
    rationale: str = Field(..., description="Explanation of why this command is needed")
    risk_label: Literal["LOW", "MEDIUM", "HIGH"] = Field(..., description="Risk assessment")
    working_dir: Optional[str] = Field(None, description="Working directory for command execution")


class ApprovalRequest(BaseModel):
    """
    Generic approval request container for interrupts.

    Attributes:
        type: Type of approval ("patch" or "terminal").
        data: Structured data (PatchPlan or CommandPlan).
        approved: User's approval decision (None = pending, True = approved, False = denied).
    """
    type: Literal["patch", "terminal"] = Field(..., description="Type of approval")
    data: Dict[str, Any] = Field(..., description="Structured data (PatchPlan or CommandPlan as dict)")
    approved: Optional[bool] = Field(None, description="User's approval decision")


# ============================================================================
# TOOL RESULT MODELS
# ============================================================================

class ToolOutput(BaseModel):
    """
    Structured output from a tool execution.

    Attributes:
        tool_name: Name of the tool that was executed.
        success: Whether the tool executed successfully.
        result: Tool output (structured or string).
        error: Error message if tool failed (optional).
        timestamp: ISO timestamp of execution.
        summary: Human-readable 1-line summary of the result (helps LLM quickly understand).
        next_steps: Suggested follow-up actions based on result (helps LLM decide what to do next).
    """
    tool_name: str = Field(..., description="Name of the tool that was executed")
    success: bool = Field(..., description="Whether the tool executed successfully")
    result: Any = Field(..., description="Tool output (structured or string)")
    error: Optional[str] = Field(None, description="Error message if tool failed")
    timestamp: str = Field(..., description="ISO timestamp of execution")
    summary: str = Field(default="", description="Human-readable 1-line summary of the result")
    next_steps: List[str] = Field(default_factory=list, description="Suggested follow-up actions")


# ============================================================================
# MASTER STATE (Phase 3)
# ============================================================================

class MasterState(TypedDict):
    """
    Master Agent State for Pulse v2.6 Unified Master Loop.

    This TypedDict defines the core state for the hub-and-spoke architecture.
    All fields are required unless marked Optional.

    Memory Management:
        messages: Bounded list of recent messages (last N turns verbatim).
        rolling_summary: String summary of older context beyond message limit.

    Execution Control:
        current_status: Vibe status word for UI display (e.g., "Wondering", "Preparing").
        pending_interrupt: Active approval request (pauses graph execution).
        is_cancelled: Cancellation flag (propagates to tools).

    Tool Execution:
        tool_result: Structured result from last tool call.
        patch_plans: List of pending patches (for batch approval if needed).
        terminal_commands: List of pending terminal commands.
        files_touched: Files created/modified during execution.

    Workspace Context:
        workspace_context: Dict containing project_root, file tree, etc.
        settings_snapshot: Settings at run start (provider, model, toggles, budget).

    Output:
        agent_response: Final response to display in Pulse Chat.
        execution_log: Timestamped log of agent actions (bounded).
    """

    # ========================================================================
    # Memory Management (Bounded Context)
    # ========================================================================

    messages: List[Dict[str, Any]]
    """
    Bounded list of recent messages for LLM context.

    Format: List of dicts with keys: {"role": "user"|"assistant", "content": str}
    Policy: Keep last MESSAGE_HISTORY_LIMIT turns (e.g., last 10 user+assistant pairs).
    Older messages are summarized into rolling_summary.
    """

    rolling_summary: str
    """
    String summary of older context beyond message limit.

    When messages list exceeds MESSAGE_HISTORY_LIMIT, oldest messages are:
    1. Summarized into this field
    2. Removed from messages list
    3. Stored in SQLite for full transcript (Phase 4)
    """

    conversation_summary: str
    """
    LLM-generated intelligent summary of older messages.

    Unlike rolling_summary (simple concatenation), this is generated by
    a fast/cheap LLM model focusing on:
    - User's original goal
    - Files discussed/modified
    - Decisions made (approved patches, etc.)
    - Current progress state

    Updated when messages exceed MESSAGE_HISTORY_LIMIT.
    """

    important_context: List[str]
    """
    Key facts to always preserve across summarization.

    Contains critical context that should never be lost:
    - User's original request (first message)
    - Files touched during session
    - Errors encountered and how they were resolved
    - Key decisions made (approvals, denials, user preferences)

    These are prepended to LLM context even after summarization.
    """

    # ========================================================================
    # Execution Control
    # ========================================================================

    current_status: str
    """
    Current vibe status word for UI display.

    Categories:
    - Thinking: Wondering, Stewing, Cogitating, Hoping, Exploring, Preparing
    - Context Building: Mustering, Coalescing, Ideating
    - Action: Completing, Messaging, Uploading, Connecting, Affirming, Rejoicing

    Updated by nodes before long operations (LLM calls, tool execution).
    Rate-limited by event bus (2-3 second updates).
    """

    pending_interrupt: Optional[ApprovalRequest]
    """
    Active approval request (pauses graph execution).

    When set:
    - Graph pauses at interrupt_wait_node
    - UI displays approval modal (patch preview or terminal approval)
    - User approves/denies
    - Graph resumes with updated state

    When None: No pending approval, graph continues normally.
    """

    is_cancelled: bool
    """
    Cancellation flag (propagates to tools and LLM calls).

    Set to True when user cancels run. All nodes and tools should check
    this flag and abort cleanly if True.
    """

    mode: str
    """
    Agent operation mode.

    Values:
    - "agent": Full tool access, can modify files and run commands.
    - "ask": Read-only mode, can search/explore but not modify.
    - "plan": Planning mode, no execution, generates implementation plans.

    Determines which tools are available and system prompt to use.
    """

    # ========================================================================
    # Tool Execution Results
    # ========================================================================

    tool_result: Optional[ToolOutput]
    """
    Structured result from last tool call.

    Stores output from most recent tool execution. Master agent uses this
    to determine next action (continue, ask for clarification, return response).
    """

    pending_tool_calls: List[Dict[str, Any]]
    """
    List of pending tool calls to execute in current iteration.

    When LLM returns multiple tool calls, ALL are stored here.
    tool_execution_node processes them in sequence (or parallel for read-only tools).
    Each dict contains: {"id": str, "name": str, "arguments": dict}

    This enables processing ALL tool calls per iteration instead of just the first,
    reducing unnecessary LLM round-trips.
    """

    tool_results: List[ToolOutput]
    """
    List of results from all tool calls in current iteration.

    Accumulated as pending_tool_calls are executed.
    All results are added to message history before returning to master_agent.
    """

    patch_plans: List[PatchPlan]
    """
    List of pending patches awaiting approval.

    Populated by master_agent_node or tool_execution_node.
    Consumed by interrupt_wait_node for approval flow.
    """

    terminal_commands: List[CommandPlan]
    """
    List of pending terminal commands awaiting approval.

    Populated by master_agent_node or tool_execution_node.
    Consumed by interrupt_wait_node for approval flow.
    """

    files_touched: List[str]
    """
    Files created/modified during execution.

    Updated by apply_patch and manage_file_ops tools.
    Used for:
    - Opening modified files in editor tabs (Phase 7 UI)
    - Test validation (Phase 6)
    """

    approvals_requested: List[str]
    """
    List of approval keys already requested in this run.

    Used to deduplicate approval requests when LLM requests
    the same tool multiple times for the same file/command.

    Format: List of strings like "patch:snake.py" or "terminal:git status"
    """

    # ========================================================================
    # Workspace Context
    # ========================================================================

    workspace_context: Dict[str, Any]
    """
    Workspace metadata and structure.

    Required keys:
    - project_root: str (absolute path to workspace root)

    Optional keys:
    - file_tree: str (hierarchical directory tree discovered dynamically)
    - active_files: List[str] (files currently open in editor)
    - recent_changes: List[str] (recent modifications for context)

    Note: Workspace type is discovered dynamically via tools, not stored statically.
    """

    settings_snapshot: Dict[str, Any]
    """
    Snapshot of settings at run start.

    Keys:
    - provider: str ("openai" or "anthropic")
    - model: str (e.g., "gpt-4o", "claude-sonnet-4.5")
    - enable_crew: bool
    - enable_autogen: bool
    - budget: Optional[Dict] (token/cost limits)

    Immutable during run (prevents mid-run config changes).
    """

    # ========================================================================
    # Output & Feedback
    # ========================================================================

    agent_response: str
    """
    Final response to display in Pulse Chat.

    Populated by master_agent_node when ready to return to user.
    Displayed in Pulse Chat tab (Phase 7 UI).
    """

    execution_log: List[str]
    """
    Timestamped log of agent actions (bounded).

    Format: List of strings like "2024-01-15 10:30:00 - Searching workspace for Motor_1"
    Bounded to prevent unbounded growth (e.g., last 50 entries).
    Displayed in Agent Panel (Phase 7 UI).
    """


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_initial_master_state(
    user_input: str,
    project_root: str,
    settings_snapshot: Dict[str, Any],
    mode: str = "agent"
) -> MasterState:
    """
    Create initial MasterState for a new agent run.

    Args:
        user_input: User's request or question.
        project_root: Absolute path to workspace root.
        settings_snapshot: Settings snapshot from SettingsManager.
        mode: Agent mode - "agent", "ask", or "plan" (default: "agent").

    Returns:
        MasterState: Initial state with default values.

    Example:
        >>> state = create_initial_master_state(
        ...     user_input="Add a timer to the conveyor logic",
        ...     project_root="/workspace/my_plc_project",
        ...     settings_snapshot={"provider": "openai", "model": "gpt-4o", ...}
        ... )
    """
    return MasterState(
        # Memory
        messages=[{"role": "user", "content": user_input}],
        rolling_summary="",
        conversation_summary="",
        important_context=[f"Original request: {user_input}"],  # Always preserve user's initial request

        # Execution control
        current_status="Wondering",
        pending_interrupt=None,
        is_cancelled=False,
        mode=mode,

        # Tool execution
        tool_result=None,
        pending_tool_calls=[],
        tool_results=[],
        patch_plans=[],
        terminal_commands=[],
        files_touched=[],
        approvals_requested=[],  # For deduplication

        # Workspace context
        workspace_context={
            "project_root": project_root,
        },
        settings_snapshot=settings_snapshot,

        # Output
        agent_response="",
        execution_log=[],
    )


def truncate_messages(
    messages: List[Dict[str, Any]],
    limit: int = MESSAGE_HISTORY_LIMIT
) -> tuple[List[Dict[str, Any]], str]:
    """
    Truncate message history to last N turns, summarizing older messages.

    Args:
        messages: Full message list.
        limit: Maximum number of turns to keep (default: MESSAGE_HISTORY_LIMIT).

    Returns:
        Tuple of (truncated_messages, summary_of_removed_messages).

    Example:
        >>> messages = [{"role": "user", "content": "..."}, ...]  # 20 messages
        >>> recent, summary = truncate_messages(messages, limit=10)
        >>> len(recent)  # 10 messages (last 5 turns)
        10
    """
    if len(messages) <= limit * 2:  # Each turn = user + assistant
        return messages, ""

    # Split into old and recent
    old_messages = messages[:len(messages) - (limit * 2)]
    recent_messages = messages[len(messages) - (limit * 2):]

    # Summarize old messages (simple concatenation for Phase 3)
    # TODO Phase 4: Use LLM to generate intelligent summary
    summary_lines = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:100]  # First 100 chars
        summary_lines.append(f"{role}: {content}...")

    summary = "\n".join(summary_lines)

    return recent_messages, summary


__all__ = [
    "MasterState",
    "PatchPlan",
    "CommandPlan",
    "ApprovalRequest",
    "ToolOutput",
    "create_initial_master_state",
    "truncate_messages",
    "MESSAGE_HISTORY_LIMIT",
]
