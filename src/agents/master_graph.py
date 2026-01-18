"""
Master Agent Graph for Pulse IDE v2.6 (Phase 3).

Implements the Unified Master Loop (hub-and-spoke) architecture:
- master_agent_node: The Brain (LLM decision-making)
- tool_execution_node: The Hands (tool execution with approval gates)

Key Features:
- Interrupt-based approvals (patch/terminal)
- Bounded message history with rolling summary
- Vibe status streaming
- Clean cancellation support
- Single active run enforcement

LangGraph Architecture:
- Uses interrupt() for human-in-the-loop approvals
- Resumes with Command(resume=...)
- Checkpointing for deterministic pause/resume
"""

import asyncio
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
import logging
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from src.agents.state import (
    MasterState,
    CommandPlan,
    ToolOutput,
    truncate_messages,
    MESSAGE_HISTORY_LIMIT,
)
from src.core.events import (
    emit_status,
    emit_node_entered,
    emit_node_exited,
    emit_tool_requested,
    emit_tool_executed,
    emit_approval_requested,
)

logger = logging.getLogger(__name__)

# Global checkpointer singleton for interrupt/resume support
_graph_checkpointer: Optional['MemorySaver'] = None


# ============================================================================
# G1: ERROR RECOVERY PATTERNS
# ============================================================================
#
# This module implements robust error handling for LLM API calls:
# - User-friendly error messages for common failure modes
# - Exponential backoff with retry logic for transient failures
# - Graceful degradation when APIs are unavailable
#
# Benefits:
# - Users see clear, actionable error messages instead of raw exceptions
# - Transient rate limits and network issues auto-recover
# - System remains responsive even during API instability
# ============================================================================

# User-friendly error messages for common API errors
ERROR_MESSAGES = {
    "rate_limit": (
        "API rate limit reached. Please wait a moment and try again. "
        "If this persists, consider upgrading your API plan."
    ),
    "api_key_invalid": (
        "API key is invalid or expired. Please check Settings → API Keys "
        "and ensure your key is correct."
    ),
    "api_key_missing": (
        "API key not configured. Please add your API key in Settings → API Keys."
    ),
    "network": (
        "Network error. Please check your internet connection and try again."
    ),
    "timeout": (
        "Request timed out. The server may be overloaded. Please try again."
    ),
    "server_error": (
        "The API server encountered an error. This is usually temporary. "
        "Please try again in a few moments."
    ),
    "model_unavailable": (
        "The selected model is currently unavailable. Please try a different model "
        "or wait a few minutes."
    ),
    "context_length": (
        "The conversation is too long for this model. Try starting a new conversation "
        "or using a model with a larger context window."
    ),
    "unknown": (
        "An unexpected error occurred. Please try again. If the problem persists, "
        "check the logs for details."
    ),
}


def classify_error(error: Exception) -> str:
    """
    Classify an exception into a user-friendly error category.

    Args:
        error: The exception that was raised.

    Returns:
        Error category key from ERROR_MESSAGES.

    Example:
        >>> import openai
        >>> classify_error(openai.RateLimitError("Rate limit exceeded"))
        "rate_limit"
    """
    error_str = str(error).lower()

    # Rate limit errors
    if "rate" in error_str and "limit" in error_str:
        return "rate_limit"
    if "429" in error_str or "too many requests" in error_str:
        return "rate_limit"

    # Authentication errors
    if "authentication" in error_str or "invalid api key" in error_str:
        return "api_key_invalid"
    if "401" in error_str or "unauthorized" in error_str:
        return "api_key_invalid"
    if "api key not" in error_str or "key not configured" in error_str:
        return "api_key_missing"

    # Network errors
    if "connection" in error_str or "network" in error_str:
        return "network"
    if "timeout" in error_str or "timed out" in error_str:
        return "timeout"
    if "ssl" in error_str or "certificate" in error_str:
        return "network"

    # Server errors
    if "500" in error_str or "502" in error_str or "503" in error_str:
        return "server_error"
    if "internal server error" in error_str or "service unavailable" in error_str:
        return "server_error"

    # Model-specific errors
    if "model" in error_str and ("unavailable" in error_str or "not found" in error_str):
        return "model_unavailable"
    if "context" in error_str and "length" in error_str:
        return "context_length"
    if "maximum" in error_str and "token" in error_str:
        return "context_length"

    return "unknown"


def get_user_friendly_error(error: Exception) -> str:
    """
    Get a user-friendly error message for an exception.

    Args:
        error: The exception that was raised.

    Returns:
        User-friendly error message string.

    Example:
        >>> get_user_friendly_error(ValueError("Rate limit exceeded"))
        "API rate limit reached. Please wait a moment and try again..."
    """
    category = classify_error(error)
    return ERROR_MESSAGES.get(category, ERROR_MESSAGES["unknown"])


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is transient and worth retrying.

    Args:
        error: The exception that was raised.

    Returns:
        True if the error might resolve with a retry, False otherwise.

    Example:
        >>> is_retryable_error(RuntimeError("Rate limit exceeded"))
        True
        >>> is_retryable_error(ValueError("Invalid API key"))
        False
    """
    category = classify_error(error)

    # These errors might resolve with a retry
    retryable_categories = {"rate_limit", "timeout", "server_error", "network"}

    return category in retryable_categories


async def call_llm_with_retry(
    llm_client: 'LLMClient',
    model: str,
    messages: list,
    system_prompt: str,
    tools: list = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> 'LLMResponse':
    """
    Call LLM with automatic retry and exponential backoff (G1 Enhancement).

    This function wraps LLM API calls with intelligent retry logic:
    - Exponential backoff for rate limits (2^attempt seconds)
    - Fixed delay for server errors (1 second)
    - No retry for authentication or configuration errors
    - User-friendly error messages on final failure

    Args:
        llm_client: Initialized LLMClient instance.
        model: Model identifier (e.g., "gpt-5-mini").
        messages: Conversation history in OpenAI format.
        system_prompt: System prompt for the model.
        tools: Optional list of tool schemas.
        temperature: Sampling temperature (default 0.0 for deterministic).
        max_tokens: Maximum tokens to generate.
        max_retries: Maximum number of retry attempts (default 3).
        base_delay: Base delay in seconds for exponential backoff (default 1.0).

    Returns:
        LLMResponse on success.

    Raises:
        RuntimeError: If all retries fail, with user-friendly error message.
        ValueError: If configuration error (API key issues), not retried.

    Example:
        >>> client = LLMClient()
        >>> response = await call_llm_with_retry(
        ...     client, "gpt-5-mini",
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     system_prompt="You are helpful."
        ... )
        >>> response.content
        "Hello! How can I help you?"
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Make the LLM call
            logger.info(f"[G1] LLM call attempt {attempt + 1}/{max_retries}")

            response = llm_client.generate(
                model=model,
                messages=messages,
                system_prompt=system_prompt,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Success!
            if attempt > 0:
                logger.info(f"[G1] LLM call succeeded after {attempt + 1} attempts")

            return response

        except ValueError as e:
            # Configuration errors (API key issues) - don't retry
            logger.warning(f"[G1] Configuration error (not retrying): {e}")
            raise

        except Exception as e:
            last_error = e
            error_category = classify_error(e)

            logger.warning(f"[G1] LLM call failed (attempt {attempt + 1}/{max_retries}): {error_category} - {e}")

            # Check if this error is retryable
            if not is_retryable_error(e):
                logger.info(f"[G1] Error not retryable ({error_category}), giving up")
                break

            # Check if we have retries left
            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff for rate limits
                if error_category == "rate_limit":
                    delay = base_delay * (2 ** attempt)  # Exponential: 1s, 2s, 4s
                    logger.info(f"[G1] Rate limit hit, waiting {delay}s before retry (exponential backoff)")
                else:
                    delay = base_delay  # Fixed delay for other errors
                    logger.info(f"[G1] Transient error, waiting {delay}s before retry")

                await asyncio.sleep(delay)
            else:
                logger.warning(f"[G1] All {max_retries} retry attempts exhausted")

    # All retries failed - return user-friendly error
    user_message = get_user_friendly_error(last_error)
    logger.error(f"[G1] LLM call failed after {max_retries} attempts: {user_message}")

    raise RuntimeError(user_message)


def create_error_response(error_message: str) -> dict:
    """
    Create a structured error response for the agent.

    This is used when LLM calls fail after all retries.

    Args:
        error_message: User-friendly error message.

    Returns:
        Dict with error information for state update.

    Example:
        >>> create_error_response("API rate limit reached...")
        {"error": True, "message": "API rate limit reached...", "recoverable": True}
    """
    return {
        "error": True,
        "message": error_message,
        "recoverable": "rate limit" in error_message.lower() or "try again" in error_message.lower(),
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# TOOL REGISTRY (Phase 4)
# ============================================================================

from src.tools.registry import ToolRegistry  # noqa: E402

# Global tool registry (initialized in create_master_graph)
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        raise RuntimeError("Tool registry not initialized. Call create_master_graph() first.")
    return _tool_registry


# ============================================================================
# REAL LLM CLIENT (Phase 1)
# ============================================================================

from src.core.llm_client import LLMClient, LLMResponse, get_session_tracker  # noqa: E402
from src.core.prompts import AGENT_MODE_PROMPT, ASK_MODE_PROMPT, PLAN_MODE_PROMPT, PLC_ENHANCEMENT  # noqa: E402


# ============================================================================
# REAL TOOL EXECUTION (Phase 4 - Replaces Stubs)
# ============================================================================

async def execute_tool_real(
    tool_name: str,
    args: Dict[str, Any],
    state: MasterState
) -> ToolOutput:
    """
    Real tool execution using ToolRegistry (Phase 4).

    Args:
        tool_name: Tool to execute.
        args: Tool arguments.
        state: Current master state.

    Returns:
        ToolOutput with result or error.
    """
    # Check cancellation
    if state["is_cancelled"]:
        return ToolOutput(
            tool_name=tool_name,
            success=False,
            result="",
            error="Run cancelled by user",
            timestamp=datetime.now().isoformat()
        )

    # Get tool registry
    try:
        registry = get_tool_registry()
    except RuntimeError as e:
        return ToolOutput(
            tool_name=tool_name,
            success=False,
            result="",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

    # Invoke tool via registry
    return registry.invoke_tool(tool_name, args)


def create_stub_command_plan(command: str) -> CommandPlan:
    """Create stub command plan for terminal commands (Tier 2 - Phase 5)."""
    # Simple risk assessment
    risk = "HIGH" if any(word in command.lower() for word in ["rm", "delete", "drop"]) else "MEDIUM"
    if any(word in command.lower() for word in ["ls", "cat", "echo", "git status"]):
        risk = "LOW"

    return CommandPlan(
        command=command,
        rationale=f"Executing command: {command}",
        risk_label=risk
    )


# ============================================================================
# A3: INTELLIGENT MEMORY MANAGEMENT
# ============================================================================

SUMMARIZATION_PROMPT = """Summarize this conversation history in 2-3 concise sentences.

Focus on:
1. The user's main goal or request
2. Key files that were discussed or modified
3. Important decisions made (approved patches, user preferences)
4. Current progress state (what's been completed, what's remaining)

Be factual and specific. Include file paths, function names, and concrete details.
Do NOT include pleasantries or filler words."""


def format_messages_for_summary(messages: List[Dict[str, Any]]) -> str:
    """
    Format messages into a readable string for summarization.

    Args:
        messages: List of message dicts with role and content.

    Returns:
        Formatted string representation of the conversation.
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Handle tool messages
        if role == "tool":
            tool_id = msg.get("tool_call_id", "unknown")
            lines.append(f"[Tool Result ({tool_id})]: {content[:200]}...")
        # Handle assistant messages with tool calls
        elif role == "assistant" and msg.get("tool_calls"):
            tool_names = [tc.get("function", {}).get("name", "unknown") for tc in msg.get("tool_calls", [])]
            lines.append(f"Assistant: [Called tools: {', '.join(tool_names)}]")
        # Handle regular messages
        elif content:
            # Truncate long content for summarization
            truncated = content[:500] + "..." if len(content) > 500 else content
            lines.append(f"{role.capitalize()}: {truncated}")

    return "\n".join(lines)


async def summarize_old_messages(
    messages: List[Dict[str, Any]],
    llm_client: 'LLMClient',
    model: str = "gpt-4o-mini"
) -> str:
    """
    Use LLM to create intelligent summary of old messages (A3 Enhancement).

    This replaces simple text concatenation with a semantic summary that
    preserves important context while reducing token usage.

    Args:
        messages: List of old messages to summarize.
        llm_client: LLM client instance for API calls.
        model: Model to use for summarization (default: gpt-4o-mini for speed/cost).

    Returns:
        Concise summary string of the conversation history.

    Example:
        >>> old_messages = [{"role": "user", "content": "Add a timer..."}, ...]
        >>> summary = await summarize_old_messages(old_messages, llm_client)
        >>> print(summary)
        "User requested adding a TON timer to conveyor logic in main.st.
         Modified motor_control function. Timer added and approved."
    """
    if not messages:
        return ""

    try:
        # Format messages for summarization
        conversation_text = format_messages_for_summary(messages)

        # Call LLM with summarization prompt
        response = llm_client.generate(
            model=model,
            messages=[{"role": "user", "content": f"Conversation to summarize:\n\n{conversation_text}"}],
            system_prompt=SUMMARIZATION_PROMPT,
            temperature=0.0,  # Deterministic for consistent summaries
            max_tokens=300  # Keep summaries concise
        )

        summary = response.content.strip()
        logger.info(f"[A3] Generated summary ({len(summary)} chars) from {len(messages)} messages")
        return summary

    except Exception as e:
        # Fallback to simple truncation if LLM fails
        logger.warning(f"[A3] LLM summarization failed, using fallback: {e}")
        return _fallback_summarize(messages)


def _fallback_summarize(messages: List[Dict[str, Any]]) -> str:
    """
    Fallback summarization when LLM is unavailable.

    Simple concatenation with truncation (original behavior).
    """
    summary_lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content:
            summary_lines.append(f"{role}: {content[:100]}...")

    return "\n".join(summary_lines[-5:])  # Keep last 5 entries


def extract_important_context(state: MasterState) -> List[str]:
    """
    Extract key facts that should always be preserved.

    These facts are never summarized away and are always included
    in the LLM context.

    Args:
        state: Current MasterState.

    Returns:
        List of important context strings.
    """
    important = list(state.get("important_context", []))

    # Add files touched
    files_touched = state.get("files_touched", [])
    if files_touched:
        files_str = ", ".join(files_touched[-10:])  # Last 10 files
        context_entry = f"Files modified this session: {files_str}"
        if context_entry not in important:
            important.append(context_entry)

    # Extract errors from execution log
    errors = [
        log for log in state.get("execution_log", [])
        if "ERROR" in log or "failed" in log.lower()
    ]
    for error in errors[-3:]:  # Last 3 errors
        if error not in important:
            important.append(f"Error encountered: {error}")

    # Add approval decisions
    for log in state.get("execution_log", []):
        if "Approval granted" in log or "Approval denied" in log:
            if log not in important:
                important.append(log)

    return important


# ============================================================================
# NODE A: MASTER AGENT (The Brain)
# ============================================================================

async def master_agent_node(state: MasterState) -> MasterState:
    """
    Master Agent Node - The Brain of Pulse IDE.

    Responsibilities:
    1. Set vibe status to Thinking category
    2. Apply memory policy (bounded messages + rolling summary)
    3. Call LLM with system prompt and context
    4. Decide outcome:
       - Direct answer → populate agent_response, END
       - Tool call → record tool request, transition to tool_execution_node

    Args:
        state: Current MasterState.

    Returns:
        Updated MasterState.
    """
    await emit_node_entered("master_agent")
    await emit_status("Wondering")

    try:
        # Check cancellation
        if state["is_cancelled"]:
            state["agent_response"] = "Run cancelled by user."
            logger.info("Run cancelled, returning to user")
            await emit_node_exited("master_agent")
            return state

        # ====================================================================
        # A1: Clear tool_results from previous iteration
        # ====================================================================
        # Tool results have already been added to message history by tool_execution_node
        # Clear them to prevent routing loop
        if state.get("tool_results"):
            logger.info(f"[A1] Clearing {len(state['tool_results'])} tool result(s) from previous iteration")
            state["tool_results"] = []

        # ====================================================================
        # A3: ENHANCED MEMORY POLICY - Intelligent Summarization
        # ====================================================================

        messages = state["messages"]
        rolling_summary = state.get("rolling_summary", "")
        conversation_summary = state.get("conversation_summary", "")

        # Truncate if exceeds limit
        if len(messages) > MESSAGE_HISTORY_LIMIT * 2:
            # Split into old and recent messages
            old_messages = messages[:len(messages) - (MESSAGE_HISTORY_LIMIT * 2)]
            recent_messages = messages[len(messages) - (MESSAGE_HISTORY_LIMIT * 2):]

            # Initialize LLM client for summarization
            try:
                llm_client = LLMClient()
                # Use a fast/cheap model for summarization
                summary_model = state["settings_snapshot"].get("models", {}).get("summarization", "gpt-4o-mini")
                new_summary = await summarize_old_messages(old_messages, llm_client, model=summary_model)
            except Exception as e:
                # Fallback to simple summarization if LLM fails
                logger.warning(f"[A3] LLM summarization unavailable, using fallback: {e}")
                new_summary = _fallback_summarize(old_messages)

            state["messages"] = recent_messages

            # Update conversation summary (intelligent summary)
            if conversation_summary:
                state["conversation_summary"] = f"{conversation_summary}\n\n{new_summary}"
            else:
                state["conversation_summary"] = new_summary

            # Keep rolling_summary for backwards compatibility
            _, old_text_summary = truncate_messages(old_messages, MESSAGE_HISTORY_LIMIT)
            if rolling_summary:
                state["rolling_summary"] = f"{rolling_summary}\n\n--- Older Context ---\n{old_text_summary}"
            else:
                state["rolling_summary"] = old_text_summary

            # Update important context with key facts
            state["important_context"] = extract_important_context(state)

            logger.info(f"[A3] Truncated messages: {len(messages)} -> {len(recent_messages)}, summary: {len(state['conversation_summary'])} chars")

        # ====================================================================
        # LLM CALL WITH FUNCTION CALLING
        # ====================================================================

        await emit_status("Cogitating")

        try:
            # G3: Check cancellation again before expensive LLM call
            if state["is_cancelled"]:
                state["agent_response"] = "Run cancelled by user."
                logger.info("[G3] Run cancelled before LLM call")
                await emit_node_exited("master_agent")
                return state

            # Initialize LLM client
            llm_client = LLMClient()

            # Get mode from state (default to "agent")
            mode = state.get("mode", "agent")

            # Select system prompt based on mode
            if mode == "ask":
                system_prompt = ASK_MODE_PROMPT
            elif mode == "plan":
                system_prompt = PLAN_MODE_PROMPT
            else:
                system_prompt = AGENT_MODE_PROMPT

            # Detect PLC context and enhance prompt if .st files present
            if state.get("files_touched"):
                has_st_files = any(f.endswith(".st") for f in state["files_touched"])
                if has_st_files:
                    system_prompt += PLC_ENHANCEMENT

            # Get tool schemas from registry
            registry = get_tool_registry()
            tool_schemas = registry.get_tool_schemas(mode=mode)

            # Build LLM context
            llm_messages = []

            # A3: Add important context first (always preserved)
            important_context = state.get("important_context", [])
            if important_context:
                llm_messages.append({
                    "role": "system",
                    "content": "KEY CONTEXT (always relevant):\n" + "\n".join(f"• {ctx}" for ctx in important_context)
                })

            # A3: Add intelligent conversation summary (preferred over rolling_summary)
            conversation_summary = state.get("conversation_summary", "")
            if conversation_summary:
                llm_messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary:\n{conversation_summary}"
                })
            # Fallback to rolling summary if no intelligent summary
            elif state.get("rolling_summary"):
                llm_messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary:\n{state['rolling_summary']}"
                })

            # Add recent messages
            llm_messages.extend(state["messages"])

            # Get model from settings
            model = state["settings_snapshot"].get("models", {}).get("master_agent", "gpt-5-mini")

            # ================================================================
            # G1: Call LLM with retry and exponential backoff
            # ================================================================
            # Use call_llm_with_retry for automatic retry on transient errors:
            # - Rate limits: exponential backoff (1s, 2s, 4s)
            # - Server errors: fixed 1s delay retry
            # - Network issues: fixed 1s delay retry
            # - Auth errors: fail immediately with user-friendly message
            # ================================================================
            logger.info(f"LLM call: model={model}, mode={mode}, tools={len(tool_schemas)}")
            llm_response: LLMResponse = await call_llm_with_retry(
                llm_client=llm_client,
                model=model,
                messages=llm_messages,
                system_prompt=system_prompt,
                tools=tool_schemas if tool_schemas else None,
                temperature=0.0,  # Deterministic, faster, consistent (Claude Code approach)
                max_tokens=4096,
                max_retries=3,
                base_delay=1.0
            )

            # Track usage in session tracker (Task G2)
            tracker = get_session_tracker()
            tracker.add(llm_response.usage)

            # Log token usage
            logger.info(f"LLM response: tokens={llm_response.usage.total_tokens}, cost=${llm_response.usage.estimated_cost_usd:.6f}, tool_calls={len(llm_response.tool_calls)}")

            # ====================================================================
            # DECISION BRANCHING
            # ====================================================================

            # Check if LLM wants to call tools
            if llm_response.tool_calls:
                # =============================================================
                # A1 OPTIMIZATION: Process ALL tool calls per iteration
                # =============================================================
                # Store ALL tool calls in pending_tool_calls (not just first)
                # This reduces unnecessary LLM round-trips
                import json

                # Clear previous tool results and pending calls
                state["pending_tool_calls"] = []
                state["tool_results"] = []

                # Build list of all pending tool calls
                tool_calls_for_message = []
                for tool_call in llm_response.tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments

                    # Add to pending list
                    state["pending_tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_name,
                        "arguments": tool_args
                    })

                    # Build tool_calls array for message history
                    tool_calls_for_message.append({
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
                        }
                    })

                    # Log each tool request
                    log_entry = f"{datetime.now().isoformat()} - Master: Requesting tool {tool_name}"
                    state["execution_log"].append(log_entry)
                    await emit_tool_requested(tool_name, tool_args)

                # CRITICAL: Add assistant's tool calls to message history (ALL at once)
                # OpenAI format supports multiple tool_calls in one assistant message
                state["messages"].append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls_for_message
                })

                # Set tool_result to indicate pending execution (backwards compatibility)
                first_call = llm_response.tool_calls[0]
                state["tool_result"] = ToolOutput(
                    tool_name=first_call.name,
                    success=False,  # Not executed yet
                    result={"pending": True, "args": first_call.arguments, "tool_call_id": first_call.id},
                    error=None,
                    timestamp=datetime.now().isoformat()
                )

                logger.info(f"Master agent requesting {len(llm_response.tool_calls)} tool(s): {[tc.name for tc in llm_response.tool_calls]}")
                await emit_node_exited("master_agent")
                return state

            # Direct answer path (no tool calls)
            elif llm_response.content:
                content = llm_response.content
                state["agent_response"] = content

                # Add to message history
                state["messages"].append({
                    "role": "assistant",
                    "content": content
                })

                # Log
                log_entry = f"{datetime.now().isoformat()} - Master: Direct answer provided"
                state["execution_log"].append(log_entry)

                logger.info("Master agent providing direct answer, ending graph")
                await emit_node_exited("master_agent")
                return state

            else:
                # Empty response (should not happen)
                state["agent_response"] = "I apologize, but I didn't generate a response. Please try again."
                logger.warning("LLM returned empty response")
                await emit_node_exited("master_agent")
                return state

        except ValueError as e:
            # API key not configured or invalid
            error_msg = str(e)
            state["agent_response"] = f"Configuration Error: {error_msg}"
            state["execution_log"].append(f"{datetime.now().isoformat()} - ERROR: {error_msg}")
            logger.error(f"LLM configuration error: {error_msg}")
            await emit_node_exited("master_agent")
            return state

        except RuntimeError as e:
            # API call failed
            error_msg = str(e)
            state["agent_response"] = f"LLM Error: {error_msg}"
            state["execution_log"].append(f"{datetime.now().isoformat()} - ERROR: {error_msg}")
            logger.error(f"LLM runtime error: {error_msg}")
            await emit_node_exited("master_agent")
            return state

    except asyncio.CancelledError:
        # Handle async cancellation
        state["is_cancelled"] = True
        state["agent_response"] = "Run cancelled."
        logger.info("Master agent cancelled via asyncio")
        raise

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Master agent error: {str(e)}"
        state["agent_response"] = f"An error occurred: {str(e)}"
        state["execution_log"].append(f"{datetime.now().isoformat()} - ERROR: {error_msg}")
        logger.error(error_msg, exc_info=True)
        await emit_node_exited("master_agent")
        return state


# ============================================================================
# NODE B: TOOL EXECUTION (The Hands)
# ============================================================================

# ============================================================================
# E1: PARALLEL TOOL EXECUTION INFRASTRUCTURE
# ============================================================================
#
# This module implements intelligent parallel tool execution:
# - Read-only tools (file reads, searches) run concurrently
# - Approval-required tools (patches, terminal) run sequentially
# - Tools with dependencies are detected and ordered properly
#
# Benefits:
# - Multiple file reads execute in ~1 request instead of N sequential
# - Search operations parallelize for faster codebase exploration
# - Maintains safety by keeping approval gates sequential
# ============================================================================

# Tools categorized by their execution characteristics
APPROVAL_REQUIRED_TOOLS = frozenset({
    "apply_patch",
    "plan_terminal_cmd",
    "run_terminal_cmd"
})

READ_ONLY_TOOLS = frozenset({
    "search_workspace",
    "web_search",
    "diagnose_project",  # Read-only analysis
})

# Tools that are read-only based on their action parameter
CONDITIONAL_READ_ONLY = {
    "manage_file_ops": {"read", "list"}  # read/list actions are read-only
}


def is_read_only(tool_call: Dict[str, Any]) -> bool:
    """
    Determine if a tool call is read-only (safe for parallel execution).

    E1 Enhancement: Intelligent tool categorization based on:
    1. Tool name (some tools are always read-only)
    2. Tool arguments (e.g., manage_file_ops with action="read")

    Args:
        tool_call: Dict with 'name' and 'arguments' keys.

    Returns:
        True if the tool is read-only and safe for parallel execution.

    Examples:
        >>> is_read_only({"name": "search_workspace", "arguments": {"query": "foo"}})
        True
        >>> is_read_only({"name": "manage_file_ops", "arguments": {"action": "read"}})
        True
        >>> is_read_only({"name": "manage_file_ops", "arguments": {"action": "write"}})
        False
        >>> is_read_only({"name": "apply_patch", "arguments": {...}})
        False
    """
    tool_name = tool_call.get("name", "")
    tool_args = tool_call.get("arguments", {})

    # Check if it requires approval (definitely not read-only)
    if tool_name in APPROVAL_REQUIRED_TOOLS:
        return False

    # Check if it's always read-only
    if tool_name in READ_ONLY_TOOLS:
        return True

    # Check conditional read-only tools based on arguments
    if tool_name in CONDITIONAL_READ_ONLY:
        read_only_actions = CONDITIONAL_READ_ONLY[tool_name]
        action = tool_args.get("action", "").lower()
        return action in read_only_actions

    # Default: assume not read-only for safety
    return False


def detect_tool_dependencies(tool_calls: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Detect dependencies between tool calls and group them for execution.

    E1 Enhancement: Identifies when tools depend on each other's results.

    Dependency patterns detected:
    1. Read → Modify → Read on same file (must be sequential)
    2. Multiple writes to same file (must be sequential)
    3. Independent operations (can be parallel)

    Args:
        tool_calls: List of tool call dicts.

    Returns:
        List of batches where each batch can be executed in parallel,
        but batches must be executed sequentially.

    Example:
        >>> calls = [
        ...     {"name": "manage_file_ops", "arguments": {"action": "read", "file_path": "a.py"}},
        ...     {"name": "manage_file_ops", "arguments": {"action": "read", "file_path": "b.py"}},
        ...     {"name": "apply_patch", "arguments": {"file_path": "a.py", ...}},
        ... ]
        >>> batches = detect_tool_dependencies(calls)
        >>> # Returns: [[read_a, read_b], [patch_a]]
        >>> # First batch runs in parallel, second runs after
    """
    if not tool_calls:
        return []

    # Track file paths that have been touched
    files_modified = set()
    batches = []
    current_batch = []

    for call in tool_calls:
        tool_name = call.get("name", "")
        tool_args = call.get("arguments", {})
        file_path = tool_args.get("file_path", "")

        # Check if this call depends on a previous modification
        has_dependency = False

        if file_path:
            # If this file was modified in a previous batch, we need a new batch
            if file_path in files_modified:
                has_dependency = True

            # If this is a write operation, mark the file as modified
            if tool_name in APPROVAL_REQUIRED_TOOLS or \
               (tool_name == "manage_file_ops" and tool_args.get("action", "").lower() in {"write", "delete", "create"}):
                files_modified.add(file_path)

        # Start a new batch if there's a dependency or if we hit an approval tool
        if has_dependency or tool_name in APPROVAL_REQUIRED_TOOLS:
            if current_batch:
                batches.append(current_batch)
                current_batch = []

        current_batch.append(call)

        # Approval tools always get their own batch
        if tool_name in APPROVAL_REQUIRED_TOOLS:
            batches.append(current_batch)
            current_batch = []

    # Add remaining calls
    if current_batch:
        batches.append(current_batch)

    return batches


def can_execute_in_parallel(tool_calls: List[Dict[str, Any]]) -> bool:
    """
    Check if multiple tool calls can be executed in parallel.

    E1 Enhancement: Uses is_read_only() for intelligent categorization.

    Parallel execution is ONLY safe when:
    1. All tools are read-only (no modifications)
    2. No tools require approval (no human-in-the-loop gates)
    3. Tools don't depend on each other's results (no shared file paths for writes)

    Args:
        tool_calls: List of tool call dicts with name and arguments.

    Returns:
        True if parallel execution is safe, False otherwise.

    Examples:
        >>> can_execute_in_parallel([
        ...     {"name": "search_workspace", "arguments": {"query": "foo"}},
        ...     {"name": "search_workspace", "arguments": {"query": "bar"}}
        ... ])
        True

        >>> can_execute_in_parallel([
        ...     {"name": "apply_patch", "arguments": {...}},
        ...     {"name": "search_workspace", "arguments": {"query": "foo"}}
        ... ])
        False
    """
    # Need at least 2 tools to parallelize
    if len(tool_calls) < 2:
        return False

    # Check if all tools are read-only
    for tool_call in tool_calls:
        if not is_read_only(tool_call):
            return False

    # Check for file conflicts (same file accessed by multiple tools)
    file_paths = []
    for tool_call in tool_calls:
        file_path = tool_call.get("arguments", {}).get("file_path", "")
        if file_path:
            file_paths.append(file_path)

    # If same file is accessed multiple times, be conservative and go sequential
    # (Even reads might have ordering expectations from user)
    if len(file_paths) != len(set(file_paths)):
        logger.debug("[E1] Same file accessed multiple times, using sequential execution")
        return False

    return True


async def execute_tools_parallel(
    tool_calls: List[Dict[str, Any]],
    state: MasterState
) -> List[ToolOutput]:
    """
    Execute multiple tools in parallel using asyncio.gather().

    This optimization is used for independent, non-approval tools like:
    - Multiple search_workspace calls
    - Multiple web_search calls
    - Parallel subsystem calls (implement_feature + diagnose_project)

    Args:
        tool_calls: List of tool call dicts with 'name' and 'arguments'.
        state: Current MasterState.

    Returns:
        List of ToolOutput results (same order as tool_calls).

    Example:
        tool_calls = [
            {"name": "search_workspace", "arguments": {"query": "auth"}},
            {"name": "search_workspace", "arguments": {"query": "database"}},
            {"name": "web_search", "arguments": {"query": "JWT best practices"}}
        ]
        results = await execute_tools_parallel(tool_calls, state)
        # All 3 execute simultaneously, returns in ~5s instead of ~15s
    """
    logger.info(f"[OPTIMIZATION] Executing {len(tool_calls)} tools in parallel")

    # Create tasks for each tool
    tasks = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["arguments"]
        # Create coroutine for tool execution
        task = execute_tool_real(tool_name, tool_args, state)
        tasks.append(task)

    # Execute all tools in parallel
    start_time = datetime.now()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Convert exceptions to error ToolOutputs
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append(ToolOutput(
                tool_name=tool_calls[i]["name"],
                success=False,
                result="",
                error=str(result),
                timestamp=datetime.now().isoformat()
            ))
        else:
            final_results.append(result)

    logger.info(f"[OPTIMIZATION] Parallel execution complete in {elapsed:.1f}s: {len(final_results)} results")
    return final_results


async def tool_execution_node(state: MasterState) -> MasterState:
    """
    Tool Execution Node - The Hands of Pulse IDE.

    A1 OPTIMIZATION: Processes ALL tool calls per iteration.

    Responsibilities:
    1. Set vibe status to Action category
    2. Get ALL pending tool calls from state["pending_tool_calls"]
    3. Separate into parallel-safe (read-only) and sequential (approval-required)
    4. Execute parallel-safe tools concurrently using asyncio.gather()
    5. For approval-required tools:
       - Create ApprovalRequest
       - Call interrupt() to pause graph
       - Wait for UI to resume with approval/denial
    6. Add ALL tool results to message history
    7. Transition back to master_agent_node for synthesis

    Args:
        state: Current MasterState.

    Returns:
        Updated MasterState.
    """
    await emit_node_entered("tool_execution")
    await emit_status("Preparing")
    import json

    try:
        # Check cancellation
        if state["is_cancelled"]:
            logger.info("Tool execution cancelled")
            await emit_node_exited("tool_execution")
            return state

        # =================================================================
        # A1: Get ALL pending tool calls
        # =================================================================
        pending_calls = state.get("pending_tool_calls", [])

        # Fallback for backwards compatibility (single tool_result)
        if not pending_calls and state["tool_result"] and isinstance(state["tool_result"].result, dict) and state["tool_result"].result.get("pending"):
            # Convert old single-tool format to new multi-tool format
            pending_calls = [{
                "id": state["tool_result"].result.get("tool_call_id", "unknown"),
                "name": state["tool_result"].tool_name,
                "arguments": state["tool_result"].result["args"]
            }]

        if not pending_calls:
            logger.error("tool_execution_node called but no pending tool calls")
            await emit_node_exited("tool_execution")
            return state

        logger.info(f"[A1] Processing {len(pending_calls)} tool call(s): {[tc['name'] for tc in pending_calls]}")

        # =================================================================
        # E1: INTELLIGENT TOOL BATCHING AND PARALLEL EXECUTION
        # =================================================================
        # Use detect_tool_dependencies() to group tools into executable batches.
        # Each batch is either:
        # 1. Parallel-safe: Multiple read-only tools run concurrently
        # 2. Sequential: Approval-required or dependent tools run one-at-a-time
        # =================================================================

        # Separate into read-only (parallel-safe) and approval-required
        parallel_safe_calls = []
        approval_calls = []

        for call in pending_calls:
            if call["name"] in APPROVAL_REQUIRED_TOOLS:
                approval_calls.append(call)
            elif is_read_only(call):
                parallel_safe_calls.append(call)
            else:
                # Non-read-only, non-approval tools: execute sequentially for safety
                # Add to approval_calls to ensure sequential handling
                approval_calls.append(call)

        logger.info(f"[E1] Tool categorization: {len(parallel_safe_calls)} parallel-safe, {len(approval_calls)} sequential")

        # =================================================================
        # Execute parallel-safe tools concurrently
        # =================================================================
        if parallel_safe_calls:
            # F2: Contextual status based on tool types
            tool_names = [c["name"] for c in parallel_safe_calls]
            if all(n == "manage_file_ops" for n in tool_names):
                await emit_status("Reading files")
            elif all(n == "search_workspace" for n in tool_names):
                await emit_status("Searching codebase")
            elif all(n == "web_search" for n in tool_names):
                await emit_status("Searching the web")
            else:
                await emit_status(f"Executing {len(parallel_safe_calls)} tools")

            # Use can_execute_in_parallel() for final safety check
            if can_execute_in_parallel(parallel_safe_calls):
                # Use parallel execution for multiple read-only tools
                logger.info(f"[E1] Executing {len(parallel_safe_calls)} tools in parallel")
                parallel_results = await execute_tools_parallel(
                    [{"name": c["name"], "arguments": c["arguments"]} for c in parallel_safe_calls],
                    state
                )
            else:
                # Sequential execution (single tool or dependency conflict)
                logger.info(f"[E1] Executing {len(parallel_safe_calls)} tool(s) sequentially")
                parallel_results = []
                for i, call in enumerate(parallel_safe_calls):
                    # F2: Progress for multi-file reads
                    if len(parallel_safe_calls) > 1 and call["name"] == "manage_file_ops":
                        await emit_status(f"Reading file {i+1}/{len(parallel_safe_calls)}")
                    result = await execute_tool_real(call["name"], call["arguments"], state)
                    parallel_results.append(result)

            # Add results to tool_results and message history
            for i, call in enumerate(parallel_safe_calls):
                tool_output = parallel_results[i]
                state["tool_results"].append(tool_output)

                # Emit event
                await emit_tool_executed(call["name"], tool_output.success, tool_output.result)

                # Update files_touched if applicable
                if call["name"] in ["apply_patch", "manage_file_ops"] and tool_output.success:
                    file_path = call["arguments"].get("file_path", "")
                    if file_path and file_path not in state["files_touched"]:
                        state["files_touched"].append(file_path)

                # Add tool result to message history
                tool_result_content = json.dumps({
                    "success": tool_output.success,
                    "result": tool_output.result,
                    "error": tool_output.error
                })
                state["messages"].append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": tool_result_content
                })

                # Log
                log_entry = f"{datetime.now().isoformat()} - Tool executed: {call['name']} (success={tool_output.success})"
                state["execution_log"].append(log_entry)

        # =================================================================
        # E1: Execute sequential tools (approval-required and non-read-only)
        # =================================================================
        # This handles:
        # 1. Approval-required tools (apply_patch, plan_terminal_cmd) - need user consent
        # 2. Non-read-only tools (manage_file_ops with write) - run sequentially for safety
        # =================================================================
        # G3: Track completion for informative cancellation response
        completed_sequential = 0
        total_sequential = len(approval_calls)
        
        for call in approval_calls:
            # G3: Check cancellation before each tool with informative response
            if state["is_cancelled"]:
                completed_total = len(parallel_safe_calls) + completed_sequential
                total_tools = len(parallel_safe_calls) + total_sequential
                state["agent_response"] = f"Cancelled by user. Completed {completed_total} of {total_tools} tools."
                logger.info(f"[G3] Run cancelled after {completed_total}/{total_tools} tools")
                break

            tool_name = call["name"]
            tool_args = call["arguments"]
            tool_call_id = call["id"]

            await emit_status("Connecting")

            # Check if this tool requires approval or is just sequential
            requires_approval = tool_name in APPROVAL_REQUIRED_TOOLS

            # Special handling for manage_file_ops: only approval if NOT read/list/search
            if tool_name == "manage_file_ops":
                op = tool_args.get("operation", "read").lower()
                if op in ["read", "list", "search"]:
                    requires_approval = False
                else:
                    requires_approval = True

            if not requires_approval:
                # Non-approval sequential tool: execute directly without approval gate
                logger.info(f"[E1] Executing sequential tool (no approval): {tool_name}")
                await emit_status("Completing")
                tool_output = await execute_tool_real(tool_name, tool_args, state)

                # Store result
                state["tool_results"].append(tool_output)

                # Emit event
                await emit_tool_executed(tool_name, tool_output.success, tool_output.result)

                # Update files_touched if applicable
                if tool_name in ["manage_file_ops"] and tool_output.success:
                    file_path = tool_args.get("file_path", "")
                    if file_path and file_path not in state["files_touched"]:
                        state["files_touched"].append(file_path)

                # Add tool result to message history
                tool_result_content = json.dumps({
                    "success": tool_output.success,
                    "result": tool_output.result,
                    "error": tool_output.error
                })
                state["messages"].append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result_content
                })

                log_entry = f"{datetime.now().isoformat()} - Tool executed: {tool_name} (success={tool_output.success})"
                state["execution_log"].append(log_entry)
                completed_sequential += 1  # G3: Track completion
                continue

            # =========================================================
            # Approval-required tool: request user consent
            # =========================================================
            approval_data = None
            approval_type = None

            if tool_name == "apply_patch":
                try:
                    registry = get_tool_registry()
                    patch_plan = registry.invoke_tool(tool_name, tool_args)

                    if hasattr(patch_plan, 'result') and hasattr(patch_plan.result, 'model_dump'):
                        approval_data = patch_plan.result.model_dump()
                    elif hasattr(patch_plan, 'model_dump'):
                        approval_data = patch_plan.model_dump()
                    else:
                        approval_data = patch_plan.result if isinstance(patch_plan.result, dict) else {}

                    approval_type = "patch"
                except Exception as e:
                    logger.error(f"Patch preview failed: {e}", exc_info=True)
                    error_output = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Patch preview failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )
                    state["tool_results"].append(error_output)
                    state["messages"].append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"success": False, "error": str(e)})
                    })
                    continue

            elif tool_name == "plan_terminal_cmd":
                try:
                    registry = get_tool_registry()
                    command_plan = registry.invoke_tool(tool_name, tool_args)

                    if hasattr(command_plan, 'result') and hasattr(command_plan.result, 'model_dump'):
                        approval_data = command_plan.result.model_dump()
                    elif hasattr(command_plan, 'model_dump'):
                        approval_data = command_plan.model_dump()
                    else:
                        approval_data = command_plan.result if isinstance(command_plan.result, dict) else {}

                    approval_type = "terminal"
                except Exception as e:
                    logger.error(f"Terminal plan creation failed: {e}", exc_info=True)
                    error_output = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Terminal plan creation failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )
                    state["tool_results"].append(error_output)
                    state["messages"].append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"success": False, "error": str(e)})
                    })
                    state["messages"].append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"success": False, "error": str(e)})
                    })
                    continue

            elif tool_name == "manage_file_ops":
                try:
                    # Construct approval data for file operations
                    op = tool_args.get("operation", "unknown")
                    raw_path = tool_args.get("path", "unknown")
                    content = tool_args.get("content", "")
                    
                    # Construct absolute path by joining project_root with relative path
                    project_root = state.get("project_root", "")
                    if raw_path and not (raw_path.startswith('/') or ':' in raw_path):
                        # Relative path - prepend project_root
                        import os
                        abs_path = os.path.normpath(os.path.join(project_root, raw_path))
                    else:
                        abs_path = raw_path
                    
                    approval_data = {
                        "operation": op,
                        "path": abs_path,
                        "content": content,
                        "diff": None  # TODO: generate diff for update/create
                    }
                    
                    # For file creation/updates, we might want to generate a diff if content is provided
                    # But for now, just showing the content in the approval is sufficient
                    
                    approval_type = "file_write"
                except Exception as e:
                    logger.error(f"File op approval prep failed: {e}", exc_info=True)
                    # Fallback to error
                    error_output = ToolOutput(tool_name=tool_name, success=False, result="", error=str(e), timestamp=datetime.now().isoformat())
                    state["tool_results"].append(error_output)
                    continue

            # Emit approval requested event
            await emit_approval_requested(approval_type, approval_data)

            # F2: User-friendly status during approval wait
            await emit_status("Waiting for approval")

            log_entry = f"{datetime.now().isoformat()} - Approval requested: {approval_type}"
            state["execution_log"].append(log_entry)

            # INTERRUPT: Pause graph and wait for user approval
            logger.info(f"Pausing for {approval_type} approval")
            user_decision = interrupt({
                "type": approval_type,
                "data": approval_data,
                "message": f"Approval required for {approval_type}"
            })

            approved = user_decision.get("approved", False) if isinstance(user_decision, dict) else False
            logger.info(f"Approval decision: {'approved' if approved else 'denied'}")

            if not approved:
                # User denied approval
                denied_output = ToolOutput(
                    tool_name=tool_name,
                    success=False,
                    result="",
                    error="User denied approval",
                    timestamp=datetime.now().isoformat()
                )
                state["tool_results"].append(denied_output)
                state["messages"].append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({"success": False, "error": "User denied approval"})
                })

                log_entry = f"{datetime.now().isoformat()} - Approval denied by user"
                state["execution_log"].append(log_entry)
                continue

            # User approved - execute the tool
            log_entry = f"{datetime.now().isoformat()} - Approval granted by user"
            state["execution_log"].append(log_entry)

            # F2: Specific status for patch/terminal operations
            if tool_name == "apply_patch":
                await emit_status("Applying patch")
            elif tool_name == "plan_terminal_cmd":
                await emit_status("Running command")
            else:
                await emit_status("Completing")

            if tool_name == "apply_patch":
                try:
                    registry = get_tool_registry()
                    from src.agents.state import PatchPlan
                    patch_plan = PatchPlan(**approval_data)
                    tool_output = registry.execute_patch_approved(patch_plan)
                except Exception as e:
                    logger.error(f"Patch execution failed: {e}", exc_info=True)
                    tool_output = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Patch execution failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )
            elif tool_name == "plan_terminal_cmd":
                try:
                    registry = get_tool_registry()
                    from src.agents.state import CommandPlan
                    command_plan = CommandPlan(**approval_data)
                    tool_output = registry.execute_terminal_cmd_approved(command_plan)
                except Exception as e:
                    logger.error(f"Terminal command execution failed: {e}", exc_info=True)
                    tool_output = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Terminal command execution failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )

            elif tool_name == "manage_file_ops":
                try:
                    # Execute the file operation directly after approval
                    await emit_status(f"Executing {tool_args.get('operation', 'file op')}")
                    tool_output = await execute_tool_real(tool_name, tool_args, state)
                except Exception as e:
                    logger.error(f"File op execution failed: {e}", exc_info=True)
                    tool_output = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"File op execution failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )

            # Store result
            state["tool_results"].append(tool_output)

            # Emit event
            await emit_tool_executed(tool_name, tool_output.success, tool_output.result)

            # Update files_touched if applicable
            if tool_name in ["apply_patch", "manage_file_ops"] and tool_output.success:
                file_path = tool_args.get("file_path", "")
                if file_path and file_path not in state["files_touched"]:
                    state["files_touched"].append(file_path)

            # Add tool result to message history
            tool_result_content = json.dumps({
                "success": tool_output.success,
                "result": tool_output.result,
                "error": tool_output.error
            })
            state["messages"].append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_result_content
            })

            log_entry = f"{datetime.now().isoformat()} - Tool executed: {tool_name} (success={tool_output.success})"
            state["execution_log"].append(log_entry)

        # =================================================================
        # Clear pending tool calls (all processed)
        # =================================================================
        state["pending_tool_calls"] = []

        # Update tool_result for backwards compatibility (last result)
        if state["tool_results"]:
            state["tool_result"] = state["tool_results"][-1]
        else:
            state["tool_result"] = None

        logger.info(f"[A1] Tool execution complete: {len(state['tool_results'])} tool(s) executed")
        await emit_node_exited("tool_execution")
        return state

    except asyncio.CancelledError:
        state["is_cancelled"] = True
        logger.info("Tool execution cancelled via asyncio")
        raise

    except Exception as e:
        # Re-raise GraphInterrupt so the graph can pause for approval
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            logger.info("GraphInterrupt raised - graph will pause for approval")
            raise
        
        error_msg = f"Tool execution error: {str(e)}"
        state["tool_result"] = ToolOutput(
            tool_name=state.get("pending_tool_calls", [{}])[0].get("name", "unknown") if state.get("pending_tool_calls") else "unknown",
            success=False,
            result="",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )
        state["execution_log"].append(f"{datetime.now().isoformat()} - ERROR: {error_msg}")
        logger.error(error_msg, exc_info=True)
        await emit_node_exited("tool_execution")
        return state


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_continue(state: MasterState) -> Literal["tool_execution", "master_agent", "__end__"]:
    """
    Determine next node based on state.

    Routes between master_agent, tool_execution, and END based on current state.

    A1 OPTIMIZATION: Now checks pending_tool_calls for multi-tool execution.

    Args:
        state: Current MasterState.

    Returns:
        Next node name or END.
    """
    # If cancelled, end
    if state["is_cancelled"]:
        return END

    # If agent_response is set, end (direct answer provided)
    if state["agent_response"]:
        return END

    # A1: Check if there are pending tool calls to execute
    pending_calls = state.get("pending_tool_calls", [])
    if pending_calls:
        return "tool_execution"

    # Backwards compatibility: check tool_result for pending single tool
    if state["tool_result"]:
        if isinstance(state["tool_result"].result, dict) and state["tool_result"].result.get("pending"):
            return "tool_execution"

        # Tool result is complete (not pending), go back to master_agent for synthesis
        if not (isinstance(state["tool_result"].result, dict) and state["tool_result"].result.get("pending")):
            return "master_agent"

    # A1: Check if tool_results has items (tools were executed, return to master for synthesis)
    if state.get("tool_results"):
        return "master_agent"

    # Default: end (should not reach here)
    return END


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_master_graph(project_root: Optional[Path] = None) -> StateGraph:
    """
    Create Master Agent LangGraph with tool registry.

    Args:
        project_root: Project root directory (for tool boundary enforcement).
                     Defaults to current working directory.

    Returns:
        Compiled StateGraph with checkpointing.
    """
    # Initialize global tool registry
    global _tool_registry
    if project_root is None:
        project_root = Path.cwd()

    _tool_registry = ToolRegistry(project_root)
    _tool_registry.register_tier1_tools()
    _tool_registry.register_tier2_tools()  # Phase 5: Terminal + Dependency Manager
    _tool_registry.register_tier3_tools()  # Tier 3: Web search, CrewAI, AutoGen

    logger.info(f"Tool registry initialized with {len(_tool_registry.tools)} tools")

    # Create graph
    workflow = StateGraph(MasterState)

    # Add nodes
    workflow.add_node("master_agent", master_agent_node)
    workflow.add_node("tool_execution", tool_execution_node)

    # Set entry point
    workflow.set_entry_point("master_agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "master_agent",
        should_continue,
        {
            "tool_execution": "tool_execution",
            "master_agent": "master_agent",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "tool_execution",
        should_continue,
        {
            "tool_execution": "tool_execution",  # For interrupt resume
            "master_agent": "master_agent",
            END: END
        }
    )

    # Compile with checkpointer for interrupt support
    # Use global singleton checkpointer so interrupt state persists across graph creations
    global _graph_checkpointer
    if _graph_checkpointer is None:
        _graph_checkpointer = MemorySaver()
    
    app = workflow.compile(checkpointer=_graph_checkpointer)

    logger.info("Master graph compiled successfully")
    return app


__all__ = [
    "create_master_graph",
    "master_agent_node",
    "tool_execution_node",
    # E1: Parallel execution helpers
    "is_read_only",
    "can_execute_in_parallel",
    "detect_tool_dependencies",
    "execute_tools_parallel",
    # G1: Error recovery helpers
    "ERROR_MESSAGES",
    "classify_error",
    "get_user_friendly_error",
    "is_retryable_error",
    "call_llm_with_retry",
    "create_error_response",
]
