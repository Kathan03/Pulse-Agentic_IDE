# Pulse IDE v2.6 - Architecture Deep Dive

**Target Audience:** Python developers learning to build Agentic IDEs

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Pattern: Hub-and-Spoke](#architecture-pattern-hub-and-spoke)
3. [The Master Graph](#the-master-graph)
4. [Tool Belt System](#tool-belt-system)
5. [UI Bridge & Event Streaming](#ui-bridge--event-streaming)
6. [Human-in-the-Loop Approvals](#human-in-the-loop-approvals)
7. [File Map](#file-map)
8. [Data Flow Diagrams](#data-flow-diagrams)

---

## Overview

Pulse IDE is an **Agentic AI IDE** for PLC (Programmable Logic Controller) coding. It demonstrates how to build a local-first, human-in-the-loop AI assistant that can:

- Read and write code files safely
- Execute terminal commands with approval
- Use RAG for workspace search
- Orchestrate complex tasks via CrewAI and AutoGen

**Key Constraints:**
- **Single active run only** (global lock prevents concurrent agent loops)
- **Human confirmation required** for patches and terminal commands
- **UI never freezes** during long operations (async event streaming)
- **Local-first** (all data stays on user's machine, except LLM API calls)

---

## Architecture Pattern: Hub-and-Spoke

### Why Not a Router?

The original architecture used a **Router Pattern**:

```
User Request → Router Node → Category Classifier
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
Planner Node   Coder Node     QA Node
    ↓               ↓               ↓
    ... more routing ...
```

**Problems with Router Pattern:**
1. **Complex routing logic** - N categories = N branches to maintain
2. **State explosion** - Each branch modifies state differently
3. **Context leakage** - Hard to control what information flows where
4. **Testing difficulty** - Many paths to test

### Hub-and-Spoke Solution

Pulse v2.6 uses a **Hub-and-Spoke** (Unified Master Loop) pattern:

```
                    ┌─────────────────────────────────────┐
                    │         UNIFIED MASTER LOOP          │
                    │       (LangGraph StateGraph)         │
                    │                                      │
                    │   ┌──────────────────────────────┐  │
                    │   │   MASTER AGENT NODE          │  │
                    │   │   (The Brain)                │  │
                    │   │   • Analyzes request         │  │
                    │   │   • Decides which tool       │  │
                    │   │   • Returns response         │  │
                    │   └─────────────┬────────────────┘  │
                    │                 │                    │
                    │   ┌─────────────▼────────────────┐  │
                    │   │   TOOL EXECUTION NODE        │  │
                    │   │   (The Hands)                │  │
                    │   │   • Executes tool            │  │
                    │   │   • Handles approvals        │  │
                    │   │   • Returns result           │  │
                    │   └──────────────────────────────┘  │
                    │                                      │
                    │            TOOL BELT                 │
                    │   ┌──────┬──────┬──────┐            │
                    │   │Tier1 │Tier2 │Tier3 │            │
                    │   │Atomic│Perm. │Agent.│            │
                    │   └──────┴──────┴──────┘            │
                    └─────────────────────────────────────┘
```

**Benefits of Hub-and-Spoke:**
1. **Single decision point** - Master Agent makes ALL decisions
2. **Tool isolation** - Tools are stateless functions
3. **Context containment** - CrewAI/AutoGen transcripts never enter Master context
4. **Deterministic interrupts** - Graph pauses cleanly for approvals
5. **Easy testing** - Mock tools, test Master in isolation

---

## The Master Graph

### State Schema: `MasterState`

Located in `src/agents/state.py`, `MasterState` is a TypedDict that flows through the graph:

```python
class MasterState(TypedDict):
    # Memory Management (Bounded Context)
    messages: List[Dict[str, Any]]      # Recent messages (last N turns)
    rolling_summary: str                 # Summary of older context

    # Execution Control
    current_status: str                  # Vibe status ("Wondering", "Preparing")
    pending_interrupt: Optional[ApprovalRequest]  # Active approval request
    is_cancelled: bool                   # Cancellation flag

    # Tool Execution
    tool_result: Optional[ToolOutput]    # Result from last tool
    patch_plans: List[PatchPlan]         # Pending patches
    terminal_commands: List[CommandPlan] # Pending terminal commands
    files_touched: List[str]             # Modified files

    # Workspace Context
    workspace_context: Dict[str, Any]    # project_root, workspace_type
    settings_snapshot: Dict[str, Any]    # provider, model, toggles

    # Output
    agent_response: str                  # Final response to user
    execution_log: List[str]             # Timestamped action log
```

### Nodes

**1. `master_agent_node` (The Brain)**

```
┌────────────────────────────────────────────────────────┐
│                  master_agent_node                      │
├────────────────────────────────────────────────────────┤
│ 1. Check cancellation                                  │
│ 2. Apply memory policy (truncate messages)             │
│ 3. Build LLM context (rolling_summary + messages)      │
│ 4. Call LLM with system prompt                         │
│ 5. Parse LLM response:                                 │
│    - Direct answer → set agent_response, return END    │
│    - Tool call → set tool_result (pending), continue   │
└────────────────────────────────────────────────────────┘
```

**2. `tool_execution_node` (The Hands)**

```
┌────────────────────────────────────────────────────────┐
│                 tool_execution_node                     │
├────────────────────────────────────────────────────────┤
│ 1. Check cancellation                                  │
│ 2. Get pending tool request from tool_result           │
│ 3. Check if tool requires approval:                    │
│    - apply_patch → YES                                 │
│    - plan_terminal_cmd → YES                           │
│    - others → NO                                       │
│ 4. If approval required:                               │
│    - Create ApprovalRequest                            │
│    - Call interrupt() ← GRAPH PAUSES HERE              │
│    - Wait for resume with user decision                │
│    - If denied: return error to master                 │
│ 5. Execute tool via ToolRegistry                       │
│ 6. Store result in tool_result                         │
│ 7. Return to master_agent_node                         │
└────────────────────────────────────────────────────────┘
```

### Graph Flow

```
                     START
                       │
                       ▼
              ┌────────────────┐
              │ master_agent   │◄──────────────┐
              │ _node          │               │
              └───────┬────────┘               │
                      │                        │
        ┌─────────────┼─────────────┐         │
        ▼             ▼             ▼         │
    direct        tool_call     cancelled     │
    answer            │             │         │
        │             ▼             ▼         │
        │      ┌────────────┐    END         │
        │      │ tool_exec  │                │
        │      │ _node      │────────────────┘
        │      └────────────┘   (loop back)
        │             │
        │             ▼ (if approval needed)
        │      ┌────────────┐
        │      │ interrupt()│ ← GRAPH PAUSES
        │      │ (wait UI)  │
        │      └────────────┘
        │             │
        ▼             ▼
       END      approved/denied
```

### Interrupt Mechanism

LangGraph's `interrupt()` function pauses graph execution:

```python
# In tool_execution_node
user_decision = interrupt({
    "type": "patch",
    "data": patch_plan.model_dump(),
    "message": "Approval required for patch"
})

# Graph pauses here...
# UI shows approval modal...
# User clicks Approve/Deny...
# UI calls: graph.astream(Command(resume={"approved": True}), config)
# Graph resumes, user_decision = {"approved": True}
```

---

## Tool Belt System

### Three-Tier Architecture

| Tier | Name | Description | Examples | Approval |
|------|------|-------------|----------|----------|
| 1 | Atomic | Fast, deterministic operations | `manage_file_ops`, `search_workspace` | No |
| 1 | Atomic | Code patches | `apply_patch` | **YES** |
| 2 | Permissioned | Terminal commands | `plan_terminal_cmd`, `run_terminal_cmd` | **YES** |
| 2 | Permissioned | Dependency detection | `dependency_manager` | No |
| 3 | Agentic | CrewAI workflows | `implement_feature` | No (returns PatchPlan) |
| 3 | Agentic | AutoGen diagnostics | `diagnose_project` | No (returns JSON) |

### Tool Registry

Located in `src/tools/registry.py`, the `ToolRegistry` class:

1. **Registers tools** with metadata (name, description, parameters)
2. **Validates arguments** before invocation
3. **Wraps tool functions** with error handling
4. **Returns `ToolOutput`** for consistent results

```python
registry = ToolRegistry(project_root=Path("/workspace"))
registry.register_tier1_tools()
registry.register_tier2_tools()
registry.register_tier3_tools()

result = registry.invoke_tool("search_workspace", {"query": "timer logic"})
# Returns: ToolOutput(success=True, result=[...], ...)
```

### CrewAI and AutoGen Integration

**Key Pattern: Context Containment**

CrewAI and AutoGen run multi-step workflows with verbose transcripts.
We **NEVER** pass these transcripts to the Master Agent.

```python
# In builder_crew.py
async def implement_feature(request, project_root, context):
    # Run CrewAI crew in background thread
    result = await asyncio.to_thread(crew.kickoff)

    # Return ONLY structured output (not transcript!)
    return {
        "patch_plans": extract_patches(result),
        "summary": generate_summary(result),
        "verification_steps": extract_verification(result),
        "metadata": {"crew_enabled": True, ...}
    }
```

**Why `asyncio.to_thread`?**

CrewAI/AutoGen are blocking operations that can take 30+ seconds.
Running them directly would freeze the Flet UI.

```python
# BAD - Freezes UI
result = crew.kickoff()

# GOOD - UI stays responsive
result = await asyncio.to_thread(crew.kickoff)
```

---

## UI Bridge & Event Streaming

### The Problem

Flet is a single-threaded UI framework. Long operations block the event loop.

### The Solution: UIBridge

Located in `src/ui/bridge.py`, the `UIBridge` class:

1. **Subscribes to EventBus** (async queue)
2. **Processes events** in the background
3. **Updates UI state** without blocking
4. **Handles approvals** via Future/resolve pattern

```
┌─────────────────────────────────────────────────────────┐
│                        UI LAYER                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ MenuBar     │    │ ChatPanel   │    │ Terminal    │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                           │                              │
│                           ▼                              │
│                    ┌─────────────┐                       │
│                    │  UIBridge   │                       │
│                    │ (singleton) │                       │
│                    └──────┬──────┘                       │
└───────────────────────────┼──────────────────────────────┘
                            │
                            ▼
┌───────────────────────────┼──────────────────────────────┐
│                    ┌──────┴──────┐                       │
│                    │  EventBus   │                       │
│                    │ (async Q)   │                       │
│                    └──────┬──────┘                       │
│                           │                              │
│                           ▼                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ master_     │───▶│ Events:     │───▶│ tool_       │ │
│  │ agent_node  │    │ STATUS      │    │ execution   │ │
│  │             │    │ APPROVAL    │    │ _node       │ │
│  └─────────────┘    │ RUN_*       │    └─────────────┘ │
│                     └─────────────┘                     │
│                      BACKEND LAYER                       │
└─────────────────────────────────────────────────────────┘
```

### Event Types

| Event | Source | Consumer | Purpose |
|-------|--------|----------|---------|
| `STATUS_CHANGED` | Nodes | VibeLoader | Update "Pulse is Wondering..." |
| `APPROVAL_REQUESTED` | tool_execution | ApprovalModal | Show patch/terminal preview |
| `RUN_STARTED` | runtime | UIBridge | Lock input, show Stop button |
| `RUN_COMPLETED` | runtime | UIBridge | Unlock input, hide loader |
| `NODE_ENTERED` | Nodes | Log panel | Debug logging |
| `TOOL_EXECUTED` | tool_execution | Log panel | Show tool results |

---

## Human-in-the-Loop Approvals

### Patch Approval Flow

```
1. User: "Add a timer variable to main.st"
                 │
                 ▼
2. Master Agent: "I'll modify main.st"
   → tool_result = {tool: "apply_patch", args: {diff: "..."}}
                 │
                 ▼
3. Tool Execution Node:
   → preview_patch() returns PatchPlan
   → emit_approval_requested("patch", patch_plan)
   → interrupt({type: "patch", data: ...})
   ← GRAPH PAUSES
                 │
                 ▼
4. UIBridge receives event:
   → Shows PatchApprovalModal
   → User sees diff preview
   → User clicks [Approve] or [Deny]
                 │
                 ▼
5. UIBridge.submit_approval(approved=True):
   → Resume graph with Command(resume={"approved": True})
   → Graph continues from interrupt point
                 │
                 ▼
6. Tool Execution Node:
   → execute_patch(patch_plan)
   → files_touched.append("main.st")
   → Return to master_agent_node
                 │
                 ▼
7. Master Agent: "Done! I added the timer variable."
```

### Terminal Command Flow

```
1. User: "Run npm install"
                 │
                 ▼
2. Master Agent: "I'll install dependencies"
   → tool_result = {tool: "plan_terminal_cmd", args: {command: "npm install"}}
                 │
                 ▼
3. Tool Execution Node:
   → plan_terminal_cmd() returns CommandPlan with risk_label: "MEDIUM"
   → emit_approval_requested("terminal", command_plan)
   → interrupt({type: "terminal", data: ...})
   ← GRAPH PAUSES
                 │
                 ▼
4. UIBridge receives event:
   → Shows TerminalApprovalModal
   → User sees: "$ npm install" with MEDIUM risk badge
   → User clicks [Execute] or [Deny]
                 │
                 ▼
5. If approved:
   → run_terminal_cmd(command_plan)
   → Subprocess executed with timeout
   → stdout/stderr captured
   → Return result to master_agent_node
```

---

## File Map

### Core Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `main.py` | Application entry point | `src.ui.app` |
| `src/ui/app.py` | Main Flet application (PulseApp class) | UIBridge, MenuBar, Sidebar, Editor, Terminal |
| `src/ui/bridge.py` | Async event streaming between backend and UI | EventBus |
| `src/ui/menu_bar.py` | VS Code-style menu bar (File, View, Settings, Help) | Theme |

### Agent Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/agents/__init__.py` | Package exports (MasterState, create_master_graph, etc.) | state, master_graph, runtime |
| `src/agents/state.py` | MasterState TypedDict + PatchPlan, CommandPlan models | Pydantic |
| `src/agents/master_graph.py` | LangGraph StateGraph with master_agent_node & tool_execution_node | state, events, prompts, guardrails, registry |
| `src/agents/runtime.py` | run_agent() entrypoint with global lock | master_graph, settings, workspace, events |

### Tool Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/tools/registry.py` | Tool registration and invocation | state (ToolOutput), all tool modules |
| `src/tools/file_ops.py` | Tier 1: File CRUD operations | guardrails, rag |
| `src/tools/patching.py` | Tier 1: Unified diff preview and execution | state (PatchPlan), guardrails |
| `src/tools/rag.py` | Tier 1: Semantic search via ChromaDB | chroma_db_rag |
| `src/tools/terminal.py` | Tier 2: Terminal command planning and execution | state (CommandPlan), processes |
| `src/tools/deps.py` | Tier 2: Dependency detection and proposals | - |
| `src/tools/builder_crew.py` | Tier 3: CrewAI feature implementation | settings, prompts |
| `src/tools/auditor_swarm.py` | Tier 3: AutoGen project diagnostics | settings |

### Core Infrastructure Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/core/settings.py` | Settings management via platformdirs | platformdirs |
| `src/core/events.py` | EventBus for async event streaming | asyncio |
| `src/core/prompts.py` | Centralized prompt registry | - |
| `src/core/guardrails.py` | Path validation and output truncation | - |
| `src/core/workspace.py` | Workspace initialization (.pulse/ directory) | - |
| `src/core/context_manager.py` | Workspace type detection (PLC, IDE, General) | - |
| `src/core/processes.py` | Subprocess tracking and cleanup | - |
| `src/core/file_manager.py` | Safe file I/O with project-root boundary | guardrails |

### UI Component Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/ui/components/approval.py` | Patch and Terminal approval modals | Theme |
| `src/ui/components/settings_modal.py` | Settings UI (API keys, models, toggles) | settings |
| `src/ui/components/vibe_loader.py` | "Pulse is Wondering..." status display | Theme, bridge |
| `src/ui/components/resizable_splitter.py` | Draggable panel splitters | Theme |

---

## Data Flow Diagrams

### Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                  │
│                       "Add a timer to main.st"                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         src/ui/app.py                                     │
│                       PulseApp._handle_agent_query()                      │
│  1. Check is_running (single-run lock)                                   │
│  2. Set is_running = True                                                │
│  3. page.run_thread(run_agent_in_background)                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      src/agents/runtime.py                                │
│                         run_agent()                                       │
│  1. Acquire global lock                                                  │
│  2. Initialize workspace (.pulse/)                                        │
│  3. Create initial MasterState                                           │
│  4. graph.astream(initial_state, config)                                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    src/agents/master_graph.py                             │
│                      master_agent_node()                                  │
│  1. emit_status("Wondering")                                             │
│  2. call_llm_stub(messages, MASTER_SYSTEM_PROMPT)                        │
│  3. LLM returns: {type: "tool_call", tool: "apply_patch", args: {...}}   │
│  4. tool_result = ToolOutput(pending=True, ...)                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    src/agents/master_graph.py                             │
│                     tool_execution_node()                                 │
│  1. emit_status("Preparing")                                             │
│  2. preview_patch() → PatchPlan                                          │
│  3. emit_approval_requested("patch", patch_plan)                         │
│  4. user_decision = interrupt({...})  ← PAUSE                            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      │    GRAPH PAUSED           │
                      │    Waiting for UI         │
                      └─────────────┬─────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       src/ui/bridge.py                                    │
│                        UIBridge                                           │
│  1. Receives APPROVAL_REQUESTED event                                    │
│  2. Calls _on_approval_request("patch", data)                            │
│  3. src/ui/app.py shows PatchApprovalModal                               │
│  4. User clicks [Approve]                                                │
│  5. bridge.submit_approval(approved=True)                                │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    src/agents/master_graph.py                             │
│                     tool_execution_node() (resumed)                       │
│  1. user_decision = {"approved": True}                                   │
│  2. execute_patch(patch_plan) via ToolRegistry                           │
│  3. files_touched.append("main.st")                                      │
│  4. Return to master_agent_node                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    src/agents/master_graph.py                             │
│                      master_agent_node()                                  │
│  1. See tool_result.success = True                                       │
│  2. agent_response = "Done! Added timer to main.st"                      │
│  3. Return END                                                           │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       src/ui/app.py                                       │
│                  run_agent_in_background() completes                      │
│  1. Display agent_response in chat panel                                 │
│  2. Reload editor tabs (file modified)                                   │
│  3. is_running = False                                                   │
│  4. Check queued_input                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Next Steps for Developers

1. **Read the tests** in `tests/` to understand expected behavior
2. **Replace the LLM stub** in `master_graph.py` with real OpenAI/Anthropic calls
3. **Add more tools** by extending `ToolRegistry.register_tier*_tools()`
4. **Customize prompts** in `src/core/prompts.py` for your domain

---

*Last updated: December 2024*
*Pulse IDE v2.6 - Unified Master Loop Architecture*
