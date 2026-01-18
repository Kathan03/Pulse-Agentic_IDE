"""
Master Agent Runtime for Pulse IDE v2.6 (Phase 3).

Provides the entrypoint for running the Master Agent with:
- Single active run enforcement (global lock)
- Cancellation support
- Integration with Phase 2 foundations (settings, workspace)
- Event streaming
- Clean error handling

Usage:
    from src.agents.runtime import run_agent, cancel_current_run

    # Start a run
    result = await run_agent(
        user_input="Add a timer to the conveyor logic",
        project_root="/path/to/workspace"
    )

    # Cancel from another context (e.g., UI button)
    cancel_current_run()
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from src.agents.master_graph import create_master_graph
from src.agents.state import create_initial_master_state
from src.core.settings import get_settings_manager
from src.core.workspace import ensure_workspace_initialized
from src.core.events import (
    emit_run_started,
    emit_run_completed,
    emit_run_cancelled,
    emit_status,
    get_event_bus,
)
from src.core.db import (
    create_or_resume_conversation,
    generate_conversation_title,
    ConversationDB,
)

logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL RUN TRACKING (Single Active Run Enforcement)
# ============================================================================

_current_run_id: Optional[str] = None
_run_lock = asyncio.Lock()
_cancellation_event: Optional[asyncio.Event] = None

# Interrupt/approval state
_waiting_for_approval: bool = False
_current_project_root: Optional[str] = None

# Conversation persistence (Task F1)
_current_conversation_id: Optional[str] = None
_current_conversation_db: Optional[ConversationDB] = None


class RunAlreadyActiveError(Exception):
    """Raised when attempting to start a run while another is active."""
    pass


def get_current_run_id() -> Optional[str]:
    """
    Get ID of currently active run.

    Returns:
        Run ID string or None if no run is active.
    """
    return _current_run_id


def is_run_active() -> bool:
    """
    Check if a run is currently active.

    Returns:
        True if a run is active, False otherwise.
    """
    return _current_run_id is not None


def cancel_current_run() -> bool:
    """
    Cancel the currently active run.

    Returns:
        True if cancellation signal was sent, False if no run is active.

    Example:
        >>> # From UI cancel button handler
        >>> if cancel_current_run():
        ...     print("Run cancelled")
    """
    global _cancellation_event

    if not is_run_active():
        logger.warning("cancel_current_run called but no run is active")
        return False

    if _cancellation_event is not None:
        _cancellation_event.set()
        logger.info(f"Cancellation signal sent for run {_current_run_id}")
        return True

    return False


def get_current_conversation_id() -> Optional[str]:
    """
    Get ID of the current conversation.

    Returns:
        Conversation ID string or None if no conversation is active.
    """
    return _current_conversation_id


def get_conversation_db() -> Optional[ConversationDB]:
    """
    Get the current conversation database instance.

    Returns:
        ConversationDB instance or None if no conversation is active.
    """
    return _current_conversation_db


def save_message_to_conversation(
    role: str,
    content: str,
    tool_calls: Optional[list] = None
) -> bool:
    """
    Save a message to the current conversation.

    Args:
        role: Message role ("user", "assistant", or "tool").
        content: Message content.
        tool_calls: Optional list of tool call dicts.

    Returns:
        True if message was saved, False if no active conversation.
    """
    if _current_conversation_db is None or _current_conversation_id is None:
        logger.warning("Cannot save message: No active conversation")
        return False

    message_id = _current_conversation_db.save_message(
        conversation_id=_current_conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls
    )

    return message_id is not None


# ============================================================================
# MASTER AGENT ENTRYPOINT
# ============================================================================

async def run_agent(
    user_input: str,
    project_root: str,
    max_iterations: int = 10,
    config: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    mode: str = "agent",
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the Master Agent for a single user request.

    This is the main entrypoint for executing the Master Agent. It:
    1. Enforces single active run (global lock)
    2. Initializes workspace if needed (Phase 2)
    3. Loads settings snapshot (Phase 2)
    4. Creates initial MasterState
    5. Executes Master Graph with interrupts
    6. Handles cancellation cleanly
    7. Returns final result

    Args:
        user_input: User's request or question.
        project_root: Absolute path to workspace root directory.
        max_iterations: Maximum graph iterations to prevent infinite loops (default: 10).
        config: Optional runtime config overrides (for testing).
        conversation_id: Optional conversation ID to resume (creates new if not provided).
        mode: Agent mode - "agent" (full tools), "ask" (read-only), or "plan" (planning).

    Returns:
        Dict with run results:
        {
            "run_id": str,
            "conversation_id": str,
            "success": bool,
            "response": str,
            "files_touched": List[str],
            "execution_log": List[str],
            "cancelled": bool,
            "error": Optional[str]
        }

    Raises:
        RunAlreadyActiveError: If another run is already active.
        ValueError: If project_root is invalid.

    Example:
        >>> result = await run_agent(
        ...     user_input="Add a 5-second timer to the conveyor start sequence",
        ...     project_root="/workspace/my_plc_project"
        ... )
        >>> print(result["response"])
    """
    global _current_run_id, _cancellation_event, _current_conversation_id, _current_conversation_db, _waiting_for_approval, _current_project_root

    # ========================================================================
    # SINGLE RUN ENFORCEMENT
    # ========================================================================

    async with _run_lock:
        if is_run_active():
            raise RunAlreadyActiveError(
                f"Cannot start new run: Run {_current_run_id} is already active. "
                "Call cancel_current_run() first."
            )

        # Use provided run_id or generate unique run ID
        if run_id is None:
            run_id = str(uuid.uuid4())
        _current_run_id = run_id
        _cancellation_event = asyncio.Event()

        logger.info(f"Starting run {run_id}")
        await emit_run_started(run_id)
        
        # Emit early status so frontend knows we're alive
        await emit_status("Starting")
        
        # Debug: Log EventBus subscriber count
        event_bus = get_event_bus()
        logger.info(f"EventBus has {len(event_bus._queues)} subscriber(s)")

    try:
        # ====================================================================
        # WORKSPACE INITIALIZATION (Phase 2)
        # ====================================================================

        project_root_path = Path(project_root).resolve()

        if not project_root_path.exists() or not project_root_path.is_dir():
            raise ValueError(f"Invalid project root: {project_root}")

        # Ensure workspace is initialized (.pulse/ directory)
        ensure_workspace_initialized(str(project_root_path))
        logger.info(f"Workspace initialized: {project_root_path}")
        
        # Store project root for resume
        _current_project_root = str(project_root_path)

        # ====================================================================
        # CONVERSATION PERSISTENCE (Task F1)
        # ====================================================================

        # Create or resume conversation
        _current_conversation_db, _current_conversation_id = create_or_resume_conversation(
            project_root=str(project_root_path),
            conversation_id=conversation_id,
            title=generate_conversation_title(user_input) if not conversation_id else None
        )
        logger.info(f"Conversation: {_current_conversation_id}")

        # Load previous messages from conversation history for context
        previous_messages = []
        if conversation_id and _current_conversation_db:
            # This is a resumed conversation - load history
            try:
                # Load up to 20 recent messages for context
                # Note: get_messages returns ordered list (oldest first)
                db_messages = _current_conversation_db.get_messages(
                    conversation_id=_current_conversation_id,
                    limit=20
                )
                for msg in db_messages:
                    # Map DB schema to message schema
                    role = msg.get("role")
                    content = msg.get("content")
                    if role and content:
                        previous_messages.append({
                            "role": role,
                            "content": content
                        })
                logger.info(f"Loaded {len(previous_messages)} previous messages from conversation")
            except Exception as e:
                logger.error(f"Failed to load conversation history: {e}")

        # Save user's message to conversation history
        _current_conversation_db.save_message(
            conversation_id=_current_conversation_id,
            role="user",
            content=user_input
        )

        # ====================================================================
        # SETTINGS SNAPSHOT (Phase 2)
        # ====================================================================

        settings_mgr = get_settings_manager()
        master_model = settings_mgr.get_model("master_agent")
        
        # Auto-detect provider from model name
        def detect_provider(model_name: str) -> str:
            model_lower = model_name.lower()
            if model_lower.startswith("claude"):
                return "anthropic"
            elif model_lower.startswith("gemini"):
                return "google"
            else:
                return "openai"  # Default for gpt-* models
        
        settings_snapshot = {
            "provider": detect_provider(master_model),
            "model": master_model,  # Direct model key for backwards compat
            "models": {
                "master_agent": master_model,
                "crew_coder": settings_mgr.get_model("crew_coder"),
                "autogen_auditor": settings_mgr.get_model("autogen_auditor"),
            },
            "enable_crew": settings_mgr.get_preference("enable_crew", True),
            "enable_autogen": settings_mgr.get_preference("enable_autogen", True),
        }

        logger.info(f"Settings snapshot: {settings_snapshot}")

        # ====================================================================
        # INITIAL STATE CREATION
        # ====================================================================

        initial_state = create_initial_master_state(
            user_input=user_input,
            project_root=str(project_root_path),
            settings_snapshot=settings_snapshot,
            mode=mode
        )

        # Prepend previous messages to state (new message already added by create_initial_master_state)
        if previous_messages:
            # We want: [old_msg_1, old_msg_2, ..., current_msg]
            # initial_state["messages"] currently has [current_msg]
            initial_state["messages"] = previous_messages + initial_state["messages"]
            logger.info(f"Final message count: {len(initial_state['messages'])}")

        logger.info("Initial MasterState created")

        # ====================================================================
        # GRAPH EXECUTION
        # ====================================================================

        # Create graph (with checkpointer for interrupt support)
        graph = create_master_graph(project_root=project_root_path)

        # Execute graph with config
        thread_config = {
            "configurable": {
                "thread_id": run_id,
                **(config or {})
            },
            "recursion_limit": max_iterations
        }

        logger.info("Starting graph execution")

        final_state = None
        iteration = 0

        async for state_update in graph.astream(initial_state, thread_config):
            # Check for cancellation
            if _cancellation_event.is_set():
                logger.info("Cancellation detected, aborting graph")
                # Update state to reflect cancellation
                if final_state is None:
                    final_state = initial_state
                final_state["is_cancelled"] = True
                await emit_run_cancelled(run_id)
                break

            # Track state updates
            final_state = state_update

            iteration += 1
            if iteration >= max_iterations:
                logger.warning(f"Max iterations ({max_iterations}) reached, stopping graph")
                break

        # If no state updates (shouldn't happen), use initial state
        if final_state is None:
            final_state = initial_state

        logger.info("Graph execution complete")
        
        # ====================================================================
        # CHECK FOR INTERRUPT (waiting for approval)
        # ====================================================================
        # When graph is paused for approval, we need to wait, not complete
        try:
            graph_state = graph.get_state(thread_config)
            if graph_state and hasattr(graph_state, 'next') and graph_state.next:
                # Graph has more nodes to execute - it's paused (interrupted)
                logger.info(f"Graph is paused at: {graph_state.next}, waiting for approval")
                _waiting_for_approval = True
                
                # Return waiting status - don't cleanup, don't send run_result
                return {
                    "run_id": run_id,
                    "conversation_id": _current_conversation_id,
                    "success": False,
                    "response": "",
                    "files_touched": [],
                    "execution_log": [],
                    "cancelled": False,
                    "error": None,
                    "waiting_for_approval": True  # Special flag
                }
        except Exception as e:
            logger.warning(f"Could not check graph state: {e}")

        # ====================================================================
        # RESULT CONSTRUCTION
        # ====================================================================

        # Extract final state from graph output
        # LangGraph astream returns dict with node names as keys
        # We need to extract the actual state
        if isinstance(final_state, dict):
            # Get the last node's state
            actual_state = None
            for node_name in ["master_agent", "tool_execution"]:
                if node_name in final_state:
                    actual_state = final_state[node_name]
                    break

            if actual_state is None:
                # Fallback: use initial state
                actual_state = initial_state
                logger.warning("Could not extract final state from graph output, using initial state")
        else:
            actual_state = final_state

        success = not actual_state["is_cancelled"] and actual_state["agent_response"] != ""
        cancelled = actual_state["is_cancelled"]

        # Save agent's response to conversation history (Task F1)
        if actual_state["agent_response"] and _current_conversation_db:
            _current_conversation_db.save_message(
                conversation_id=_current_conversation_id,
                role="assistant",
                content=actual_state["agent_response"]
            )

        result = {
            "run_id": run_id,
            "conversation_id": _current_conversation_id,
            "success": success,
            "response": actual_state["agent_response"],
            "files_touched": actual_state["files_touched"],
            "execution_log": actual_state["execution_log"],
            "cancelled": cancelled,
            "error": None
        }

        logger.info(f"Run {run_id} completed (success={success}, cancelled={cancelled})")
        await emit_run_completed(run_id, success)

        return result

    except asyncio.CancelledError:
        # Handle asyncio task cancellation
        logger.info(f"Run {run_id} cancelled via asyncio")
        await emit_run_cancelled(run_id)

        return {
            "run_id": run_id,
            "conversation_id": _current_conversation_id,
            "success": False,
            "response": "Run cancelled.",
            "files_touched": [],
            "execution_log": [],
            "cancelled": True,
            "error": None
        }

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Run {run_id} failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await emit_run_completed(run_id, success=False)

        return {
            "run_id": run_id,
            "conversation_id": _current_conversation_id,
            "success": False,
            "response": f"An error occurred: {str(e)}",
            "files_touched": [],
            "execution_log": [],
            "cancelled": False,
            "error": str(e)
        }

    finally:
        # ====================================================================
        # CLEANUP: Release global lock and conversation state
        # ====================================================================
        # Skip cleanup if waiting for approval - run needs to stay active
        if not _waiting_for_approval:
            async with _run_lock:
                _current_run_id = None
                _cancellation_event = None
                _current_conversation_id = None
                _current_conversation_db = None
                _current_project_root = None
                logger.info(f"Run {run_id} cleanup complete, lock released")
        else:
            logger.info(f"Run {run_id} paused for approval, skipping cleanup")


# ============================================================================
# INTERRUPT RESUME HELPER
# ============================================================================

async def resume_with_approval(
    run_id: str,
    approved: bool,
    project_root: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Resume an interrupted run with approval decision.

    This function is called by the UI when user approves/denies a patch or terminal command.

    Args:
        run_id: Run ID to resume (must match current active run).
        approved: User's approval decision (True = approved, False = denied).
        project_root: Project root directory for tool execution.
        config: Optional config (must include thread_id matching run_id).

    Returns:
        Updated run result after resuming.

    Raises:
        ValueError: If run_id doesn't match current active run.

    Example:
        >>> # User clicks "Approve" in patch preview modal
        >>> result = await resume_with_approval(run_id, approved=True)
    """
    global _waiting_for_approval, _current_run_id, _cancellation_event, _current_conversation_id, _current_conversation_db, _current_project_root
    
    if run_id != _current_run_id:
        raise ValueError(
            f"Cannot resume run {run_id}: Current active run is {_current_run_id}"
        )

    logger.info(f"Resuming run {run_id} with approval={approved}")
    
    # Reset waiting flag
    _waiting_for_approval = False

    # Use stored project_root if not provided
    effective_project_root = project_root or _current_project_root
    project_root_path = Path(effective_project_root) if effective_project_root else None
    graph = create_master_graph(project_root=project_root_path)

    # Resume with Command
    from langgraph.types import Command

    thread_config = {
        "configurable": {
            "thread_id": run_id,
            **(config or {})
        }
    }

    # Resume graph with approval decision
    resume_value = {"approved": approved}

    final_state = None
    async for state_update in graph.astream(Command(resume=resume_value), thread_config):
        # Check for cancellation
        if _cancellation_event and _cancellation_event.is_set():
            logger.info("Cancellation detected during resume")
            break

        final_state = state_update

    # Extract final state (same logic as run_agent)
    if isinstance(final_state, dict):
        actual_state = None
        for node_name in ["master_agent", "tool_execution"]:
            if node_name in final_state:
                actual_state = final_state[node_name]
                break
        if actual_state is None:
            actual_state = {}
    else:
        actual_state = final_state or {}

    success = not actual_state.get("is_cancelled", False) and actual_state.get("agent_response", "") != ""

    result = {
        "run_id": run_id,
        "conversation_id": _current_conversation_id,
        "success": success,
        "response": actual_state.get("agent_response", ""),
        "files_touched": actual_state.get("files_touched", []),
        "execution_log": actual_state.get("execution_log", []),
        "cancelled": actual_state.get("is_cancelled", False),
        "error": None
    }

    logger.info(f"Resume complete for run {run_id}")
    
    # Cleanup after resume
    async with _run_lock:
        _current_run_id = None
        _cancellation_event = None
        _current_conversation_id = None
        _current_conversation_db = None
        _current_project_root = None
        logger.info(f"Run {run_id} cleanup complete after resume")
    
    return result


__all__ = [
    "run_agent",
    "cancel_current_run",
    "get_current_run_id",
    "is_run_active",
    "resume_with_approval",
    "RunAlreadyActiveError",
    # Conversation persistence (Task F1)
    "get_current_conversation_id",
    "get_conversation_db",
    "save_message_to_conversation",
]
