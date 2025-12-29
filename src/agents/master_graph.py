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
from typing import Literal, Optional, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

from src.agents.state import (
    MasterState,
    PatchPlan,
    CommandPlan,
    ApprovalRequest,
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
from src.core.guardrails import truncate_output

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL REGISTRY (Phase 4)
# ============================================================================

from src.tools.registry import ToolRegistry

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

from src.core.llm_client import LLMClient, LLMResponse
from src.core.prompts import AGENT_MODE_PROMPT, ASK_MODE_PROMPT, PLAN_MODE_PROMPT, PLC_ENHANCEMENT


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
        # MEMORY POLICY: Bounded Messages + Rolling Summary
        # ====================================================================

        messages = state["messages"]
        rolling_summary = state["rolling_summary"]

        # Truncate if exceeds limit
        if len(messages) > MESSAGE_HISTORY_LIMIT * 2:
            recent_messages, old_summary = truncate_messages(messages, MESSAGE_HISTORY_LIMIT)
            state["messages"] = recent_messages

            # Merge with existing rolling summary
            if rolling_summary:
                state["rolling_summary"] = f"{rolling_summary}\n\n--- Older Context ---\n{old_summary}"
            else:
                state["rolling_summary"] = old_summary

            logger.info(f"Truncated messages: {len(messages)} -> {len(recent_messages)}")

        # ====================================================================
        # LLM CALL WITH FUNCTION CALLING
        # ====================================================================

        await emit_status("Cogitating")

        try:
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

            # Add rolling summary if exists
            if state["rolling_summary"]:
                llm_messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary:\n{state['rolling_summary']}"
                })

            # Add recent messages
            llm_messages.extend(state["messages"])

            # Get model from settings
            model = state["settings_snapshot"].get("models", {}).get("master_agent", "gpt-5-mini")

            # Call LLM with function calling
            logger.info(f"LLM call: model={model}, mode={mode}, tools={len(tool_schemas)}")
            llm_response: LLMResponse = llm_client.generate(
                model=model,
                messages=llm_messages,
                system_prompt=system_prompt,
                tools=tool_schemas if tool_schemas else None,
                temperature=0.7,
                max_tokens=4096
            )

            # Log token usage
            logger.info(f"LLM response: tokens={llm_response.usage['total_tokens']}, tool_calls={len(llm_response.tool_calls)}")

            # ====================================================================
            # DECISION BRANCHING
            # ====================================================================

            # Check if LLM wants to call tools
            if llm_response.tool_calls:
                # Tool call path - take first tool call (single tool execution per iteration)
                tool_call = llm_response.tool_calls[0]
                tool_name = tool_call.name
                tool_args = tool_call.arguments

                # Store tool request in tool_result (temporary container)
                state["tool_result"] = ToolOutput(
                    tool_name=tool_name,
                    success=False,  # Not executed yet
                    result={"pending": True, "args": tool_args},
                    error=None,
                    timestamp=datetime.now().isoformat()
                )

                # Log
                log_entry = f"{datetime.now().isoformat()} - Master: Requesting tool {tool_name}"
                state["execution_log"].append(log_entry)

                await emit_tool_requested(tool_name, tool_args)

                logger.info(f"Master agent requesting tool: {tool_name}")
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

async def tool_execution_node(state: MasterState) -> MasterState:
    """
    Tool Execution Node - The Hands of Pulse IDE.

    Responsibilities:
    1. Set vibe status to Action category
    2. Check if tool requires approval (apply_patch, run_terminal_cmd)
    3. If approval required:
       - Create ApprovalRequest
       - Call interrupt() to pause graph
       - Wait for UI to resume with approval/denial
    4. If no approval or approval granted:
       - Execute tool (stub in Phase 3)
       - Store result in tool_result
       - Transition back to master_agent_node

    Args:
        state: Current MasterState.

    Returns:
        Updated MasterState.
    """
    await emit_node_entered("tool_execution")
    await emit_status("Preparing")

    try:
        # Check cancellation
        if state["is_cancelled"]:
            logger.info("Tool execution cancelled")
            await emit_node_exited("tool_execution")
            return state

        # Get pending tool request
        if not state["tool_result"] or not state["tool_result"].result.get("pending"):
            logger.error("tool_execution_node called but no pending tool request")
            await emit_node_exited("tool_execution")
            return state

        tool_name = state["tool_result"].tool_name
        tool_args = state["tool_result"].result["args"]

        # ====================================================================
        # APPROVAL GATING
        # ====================================================================

        # Phase 5: Terminal commands now use plan_terminal_cmd (not run_terminal_cmd directly)
        requires_approval = tool_name in ["apply_patch", "plan_terminal_cmd"]

        if requires_approval:
            await emit_status("Connecting")

            # Create approval request
            if tool_name == "apply_patch":
                # Generate patch plan using real preview_patch tool
                try:
                    registry = get_tool_registry()
                    patch_plan = registry.invoke_tool(tool_name, tool_args)

                    # Check if invoke_tool returned a PatchPlan or ToolOutput
                    if hasattr(patch_plan, 'result') and hasattr(patch_plan.result, 'model_dump'):
                        # ToolOutput wrapping PatchPlan
                        approval_data = patch_plan.result.model_dump()
                    elif hasattr(patch_plan, 'model_dump'):
                        # Direct PatchPlan
                        approval_data = patch_plan.model_dump()
                    else:
                        # ToolOutput with dict result
                        approval_data = patch_plan.result if isinstance(patch_plan.result, dict) else {}

                    approval_type = "patch"
                except Exception as e:
                    logger.error(f"Patch preview failed: {e}", exc_info=True)
                    state["tool_result"] = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Patch preview failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )
                    await emit_node_exited("tool_execution")
                    return state

            elif tool_name == "plan_terminal_cmd":
                # Phase 5: Generate command plan using real plan_terminal_cmd tool
                try:
                    registry = get_tool_registry()
                    command_plan = registry.invoke_tool(tool_name, tool_args)

                    # Check if invoke_tool returned a CommandPlan or ToolOutput
                    if hasattr(command_plan, 'result') and hasattr(command_plan.result, 'model_dump'):
                        # ToolOutput wrapping CommandPlan
                        approval_data = command_plan.result.model_dump()
                    elif hasattr(command_plan, 'model_dump'):
                        # Direct CommandPlan
                        approval_data = command_plan.model_dump()
                    else:
                        # ToolOutput with dict result
                        approval_data = command_plan.result if isinstance(command_plan.result, dict) else {}

                    approval_type = "terminal"
                except Exception as e:
                    logger.error(f"Terminal plan creation failed: {e}", exc_info=True)
                    state["tool_result"] = ToolOutput(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Terminal plan creation failed: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    )
                    await emit_node_exited("tool_execution")
                    return state

            else:
                # Should not reach here
                logger.error(f"Unknown approval tool: {tool_name}")
                await emit_node_exited("tool_execution")
                return state

            # Emit approval requested event
            await emit_approval_requested(approval_type, approval_data)

            # Log
            log_entry = f"{datetime.now().isoformat()} - Approval requested: {approval_type}"
            state["execution_log"].append(log_entry)

            # ================================================================
            # INTERRUPT: Pause graph and wait for user approval
            # ================================================================

            logger.info(f"Pausing for {approval_type} approval")

            # The interrupt() function pauses the graph here
            # UI will resume with Command(resume={"approved": True/False})
            user_decision = interrupt(
                {
                    "type": approval_type,
                    "data": approval_data,
                    "message": f"Approval required for {approval_type}"
                }
            )

            # After resume, user_decision contains the approval result
            approved = user_decision.get("approved", False) if isinstance(user_decision, dict) else False

            logger.info(f"Approval decision: {'approved' if approved else 'denied'}")

            if not approved:
                # User denied approval
                state["tool_result"] = ToolOutput(
                    tool_name=tool_name,
                    success=False,
                    result="",
                    error="User denied approval",
                    timestamp=datetime.now().isoformat()
                )

                # Add denial to message history
                state["messages"].append({
                    "role": "assistant",
                    "content": f"Action cancelled: User denied approval for {tool_name}."
                })

                log_entry = f"{datetime.now().isoformat()} - Approval denied by user"
                state["execution_log"].append(log_entry)

                logger.info("Approval denied, returning to master agent")
                await emit_node_exited("tool_execution")
                return state

            # User approved - proceed with execution
            log_entry = f"{datetime.now().isoformat()} - Approval granted by user"
            state["execution_log"].append(log_entry)

        # ====================================================================
        # TOOL EXECUTION
        # ====================================================================

        await emit_status("Completing")

        # Execute tool (real execution in Phase 4+)
        if tool_name == "apply_patch" and approved:
            # Special handling: execute approved patch
            try:
                registry = get_tool_registry()
                # Reconstruct PatchPlan from approval_data
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
        elif tool_name == "plan_terminal_cmd" and approved:
            # Phase 5: Execute approved terminal command
            try:
                registry = get_tool_registry()
                # Reconstruct CommandPlan from approval_data
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
        else:
            # Normal tool execution (no approval required)
            tool_output = await execute_tool_real(tool_name, tool_args, state)

        # Store result
        state["tool_result"] = tool_output

        # Emit event
        await emit_tool_executed(tool_name, tool_output.success, tool_output.result)

        # Update files_touched if applicable
        if tool_name in ["apply_patch", "manage_file_ops"] and tool_output.success:
            file_path = tool_args.get("file_path", "")
            if file_path and file_path not in state["files_touched"]:
                state["files_touched"].append(file_path)

        # Add tool result to message history
        state["messages"].append({
            "role": "assistant",
            "content": f"Tool {tool_name} executed: {tool_output.result}"
        })

        # Log
        log_entry = f"{datetime.now().isoformat()} - Tool executed: {tool_name} (success={tool_output.success})"
        state["execution_log"].append(log_entry)

        logger.info(f"Tool execution complete: {tool_name}")
        await emit_node_exited("tool_execution")
        return state

    except asyncio.CancelledError:
        # Handle async cancellation
        state["is_cancelled"] = True
        logger.info("Tool execution cancelled via asyncio")
        raise

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Tool execution error: {str(e)}"
        state["tool_result"] = ToolOutput(
            tool_name=state["tool_result"].tool_name if state["tool_result"] else "unknown",
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

    # If tool_result exists and is pending, go to tool_execution
    if state["tool_result"] and state["tool_result"].result.get("pending"):
        return "tool_execution"

    # If tool_result exists and is complete, go back to master_agent
    if state["tool_result"] and not state["tool_result"].result.get("pending"):
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
            "master_agent": "master_agent",
            END: END
        }
    )

    # Compile with checkpointer for interrupt support
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("Master graph compiled successfully")
    return app


__all__ = [
    "create_master_graph",
    "master_agent_node",
    "tool_execution_node",
]
