# Pulse IDE - Complete Project Structure Analysis

**Generated:** 2025-12-24
**Flet Version:** 0.28.3
**Architecture:** Hub-and-Spoke with LangGraph Master Loop

---

## Table of Contents

1. [Complete File Tree](#complete-file-tree)
2. [Layer-by-Layer Analysis](#layer-by-layer-analysis)
3. [Dependency Graph](#dependency-graph)
4. [Architecture Summary](#architecture-summary)
5. [Critical Import Chains](#critical-import-chains)

---

## Complete File Tree

```
Pulse/
├── main.py                          # Application entry point + shutdown handler
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template (dev only)
├── .gitignore                       # Git ignore patterns
├── README.md                        # Project documentation
│
├── src/                             # Source code root
│   ├── __init__.py
│   │
│   ├── ui/                          # Flet UI Components (Presentation Layer)
│   │   ├── __init__.py
│   │   ├── app.py                   # Main Flet application controller (VS Code layout)
│   │   ├── menu_bar.py              # VS Code-style menu bar (File, View, Settings, Help)
│   │   ├── sidebar.py               # Workspace file tree + vibe status
│   │   ├── editor.py                # EditorManager: Tabbed editor with Pulse Chat
│   │   ├── terminal.py              # Integrated terminal panel
│   │   ├── log_panel.py             # Chat/log display panel with welcome screen
│   │   ├── status_bar.py            # Status bar (mode + workspace info)
│   │   ├── bridge.py                # UIBridge (async event transport)
│   │   ├── theme.py                 # VSCodeColors + Fonts + Spacing
│   │   └── components/              # Reusable UI widgets
│   │       ├── __init__.py
│   │       ├── approval.py          # Patch + Terminal approval modals
│   │       ├── vibe_loader.py       # Vibe status words display
│   │       ├── settings_modal.py    # Settings UI (API keys + models)
│   │       ├── code_preview_panel.py # Code preview with diff highlight
│   │       ├── clarification_dialog.py # Clarification prompts
│   │       ├── resizable_splitter.py # Draggable splitters (V + H)
│   │       └── loading_animation.py # Loading spinner
│   │
│   ├── agents/                      # LangGraph Master Agent (Hub-and-Spoke)
│   │   ├── __init__.py
│   │   ├── master_graph.py          # Unified Master Loop (LangGraph)
│   │   ├── runtime.py               # Entrypoint for agent execution
│   │   └── state.py                 # Master state schema + approval models
│   │
│   ├── core/                        # Core Business Logic & Infrastructure
│   │   ├── __init__.py
│   │   ├── events.py                # Async event bus + EventType enum
│   │   ├── settings.py              # SettingsManager (platformdirs)
│   │   ├── workspace.py             # WorkspaceManager (.pulse/ init)
│   │   ├── file_manager.py          # FileManager (atomic writes, path validation)
│   │   ├── guardrails.py            # Safety validation + denylist + path checks
│   │   ├── prompts.py               # Centralized prompt registry
│   │   ├── context_manager.py       # Workspace intelligence
│   │   └── processes.py             # Process lifecycle tracking
│   │
│   └── tools/                       # Tool Belt (3 Tiers)
│       ├── __init__.py
│       ├── registry.py              # ToolRegistry (registration + invocation)
│       ├── file_ops.py              # [TIER 1] manage_file_ops (read/write/delete)
│       ├── patching.py              # [TIER 1] apply_patch (preview + execute)
│       ├── rag.py                   # [TIER 1] search_workspace + RAGManager
│       ├── terminal.py              # [TIER 2] run_terminal_cmd (stub, Phase 5)
│       ├── deps.py                  # [TIER 2] dependency_manager (stub)
│       ├── builder_crew.py          # [TIER 3] implement_feature (CrewAI)
│       └── auditor_swarm.py         # [TIER 3] diagnose_project (AutoGen)
│
├── data/                            # Global Persistence (deprecated, use platformdirs)
│   └── .gitkeep
│
├── workspace/                       # User workspace (example/default)
│   ├── .pulse/                      # Workspace-local state (gitignored)
│   │   ├── history.sqlite           # SQLite session/state DB
│   │   ├── chroma_db/               # Chroma vector store
│   │   └── logs/                    # Bounded log files (optional)
│   └── .keep
│
├── tests/                           # Test Suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_agents/                 # Agent orchestration tests
│   ├── test_core/                   # Core functionality tests
│   └── test_ui/                     # UI component tests
│
└── .github/                         # CI/CD Pipeline
    └── workflows/
        └── ci-cd.yml                # GitHub Actions workflow (Windows .exe builds)
```

---

## Layer-by-Layer Analysis

### LAYER 1: Entry Point

#### **main.py** — Application Bootstrap
- **What:** Application entry point for Flet desktop app
- **Why:** Single entry point for desktop launcher
- **How:** Calls `ft.app(target=main)` where `main` imports from `src.ui.app`
- **Dependencies:**
  - `flet as ft`
  - `src.ui.app::main`
- **Exports:**
  - Function: `main(page: ft.Page)`

---

### LAYER 2: UI Layer (src/ui/)

#### **app.py** — Main UI Controller [CORE]
- **What:** PulseApp class managing entire UI layout + agent integration
- **Why:** Central orchestrator for VS Code-style IDE with agent backend
- **How:**
  1. Builds layout: Menu bar → (Sidebar | Editor | Terminal) → Status bar
  2. Connects UIBridge for async event streaming
  3. Enforces single-run lock (`is_running` flag)
  4. Handles approval modals (patch, terminal)
  5. Manages keyboard shortcuts (Ctrl+S, Ctrl+`, Ctrl+B, Ctrl+,)
  6. Cleanup on exit (processes + database)
- **Dependencies:**
  - **UI Components:** `sidebar`, `editor`, `log_panel`, `terminal`, `status_bar`, `menu_bar`, `resizable_splitter`, `vibe_loader`, `settings_modal`, `approval`
  - **Core:** `file_manager`, `processes`, `events`
  - **Agents:** `master_graph::create_master_graph`
  - **Theme:** `VSCodeColors`, `Spacing`
- **Exports:**
  - Class: `PulseApp`
  - Function: `main(page: ft.Page)`

---

#### **bridge.py** — Event Transport Layer [CORE]
- **What:** UIBridge singleton for async event streaming from backend to Flet
- **Why:** Prevents UI blocking during agent execution
- **How:**
  1. Subscribes to EventBus
  2. Buffers vibe updates, approval requests, responses
  3. Queues user input if run already active
  4. Callbacks notify Flet components of state changes
- **Dependencies:**
  - **Core:** `events::EventBus`, `Event`, `EventType`, `get_event_bus`
- **Exports:**
  - Enum: `VibeCategory`
  - Dict: `VIBE_WORDS`
  - Function: `get_vibe_category(vibe: str)`
  - Class: `UIState` (dataclass)
  - Class: `UIEvent` (dataclass)
  - Class: `UIBridge` (singleton)
  - Function: `get_ui_bridge()`

---

#### **sidebar.py** — File Explorer
- **What:** Workspace file tree explorer (VS Code-style)
- **Why:** Navigate workspace files, open in editor
- **How:**
  1. Recursive directory listing with expand/collapse
  2. Click file to open in EditorManager tabs
  3. Display dirty file indicators
  4. Workspace switching dropdown
- **Dependencies:**
  - **UI:** `theme::VSCodeColors`, `Fonts`, `Spacing`
  - **External:** `flet`, `pathlib`, `os`, `json`
- **Exports:**
  - Class: `Sidebar`

---

#### **editor.py** — Tabbed Editor Manager
- **What:** VS Code-style tabbed interface for multiple files + Pulse Chat
- **Why:** Multi-file editing with permanent Pulse Chat tab
- **How:**
  1. Tab 0 is permanent "Pulse Chat" tab
  2. Dynamic file tabs with close buttons (×)
  3. Dirty state tracking
  4. Welcome screen when no files open
- **Dependencies:**
  - **UI:** `theme`, `log_panel::LogPanel`
  - **External:** `flet`, `pathlib`
- **Exports:**
  - Class: `EditorManager`

---

#### **log_panel.py** — Chat/Log Display with Welcome Screen
- **What:** Chat-style log panel with Claude Code-inspired welcome screen
- **Why:** Primary interface for agent interaction
- **How:**
  1. Shows welcome screen (logo + peacock art) initially
  2. Hides welcome screen on first message
  3. Displays user and agent messages with modern styling
  4. Centralized message management (all messages added here)
- **Dependencies:**
  - **UI:** `theme`, `components.loading_animation`
  - **External:** `flet`
- **Exports:**
  - Class: `LogPanel`

---

#### **terminal.py** — Integrated Terminal Panel
- **What:** Integrated terminal at bottom of IDE
- **Why:** Execute commands, display output
- **How:**
  1. Terminal rendering (black background, monospace)
  2. Command execution (route to run_terminal_cmd tool in Phase 5)
  3. Command history (↑/↓ keys)
  4. Process cleanup on app close
- **Dependencies:**
  - **UI:** `theme::VSCodeColors`
  - **External:** `flet`
- **Exports:**
  - Class: `TerminalPanel`

---

#### **theme.py** — VS Code Color Theme
- **What:** Centralized theme definitions
- **Why:** Consistent visual styling across entire app
- **How:** Export color constants, font sizes, spacing values
- **Dependencies:** None
- **Exports:**
  - Class: `VSCodeColors` (color constants)
  - Class: `Fonts` (font sizes)
  - Class: `Spacing` (padding/margin constants)
  - Function: `create_logo_image()`

---

#### **components/** — Reusable UI Widgets

**approval.py:**
- **What:** Patch and terminal command approval modals
- **Exports:**
  - Function: `show_patch_approval(page, data, on_approve, on_deny)`
  - Function: `show_terminal_approval(page, data, on_execute, on_deny)`

**vibe_loader.py:**
- **What:** Display contextual vibe words (Wondering, Preparing, etc.)
- **Exports:**
  - Class: `VibeLoader`
  - Class: `VibeStatusBar`

**settings_modal.py:**
- **What:** Configure API keys + model selection
- **Exports:**
  - Class: `SettingsModal`

**resizable_splitter.py:**
- **What:** Resizable pane dividers (vertical/horizontal)
- **Exports:**
  - Class: `VerticalSplitter`
  - Class: `HorizontalSplitter`

**loading_animation.py:**
- **What:** Modern loading spinner (Meta-inspired)
- **Exports:**
  - Class: `LoadingAnimation(ft.Container)` ⚠️ Uses modern Flet pattern (not UserControl)

---

### LAYER 3: Agent Layer (src/agents/)

#### **master_graph.py** — Core Orchestration Engine [CORE]
- **What:** LangGraph-based master loop with 2 async nodes (master_agent + tool_execution)
- **Why:** Hub-and-spoke architecture replacing multi-agent routing
- **How:**
  1. **master_agent_node:** Decides tool sequence, calls LLM, populates agent_response or tool_result
  2. **tool_execution_node:** Executes tools, handles approval interrupts (patch/terminal), updates state
  3. **should_continue:** Routes between nodes based on state
  4. **Memory Policy:** Bounded messages (last 10 turns) + rolling summary
  5. **Interrupt Flow:** `interrupt()` pauses graph, waits for UI approval, resumes with `Command(resume={approved: bool})`
- **Dependencies:**
  - **LangGraph:** `StateGraph`, `END`, `MemorySaver`, `Command`, `interrupt`
  - **State:** `agents.state::MasterState`, `PatchPlan`, `CommandPlan`, `ApprovalRequest`, `ToolOutput`
  - **Core:** `events` (emit_status, etc.), `prompts::MASTER_SYSTEM_PROMPT`, `guardrails::truncate_output`
  - **Tools:** `registry::ToolRegistry`
- **Exports:**
  - Function: `create_master_graph(project_root: Optional[Path]) -> StateGraph`
  - Async Function: `master_agent_node(state: MasterState) -> MasterState` ⚠️ **ASYNC**
  - Async Function: `tool_execution_node(state: MasterState) -> MasterState` ⚠️ **ASYNC**
  - Function: `should_continue(state: MasterState) -> Literal["tool_execution", "master_agent", "__end__"]`

**⚠️ CRITICAL:** Both nodes are `async def`, so must use `.astream()` not `.stream()`

---

#### **runtime.py** — Run Entrypoint
- **What:** High-level `run_agent()` function with single-run lock enforcement
- **Why:** User-facing API for starting agent runs, manages lifecycle
- **How:**
  1. Acquire global lock (raises `RunAlreadyActiveError` if active)
  2. Initialize workspace (`.pulse/` directory)
  3. Load settings snapshot
  4. Create initial MasterState
  5. Stream graph execution with max_iterations safety
  6. Handle cancellation cleanly
  7. Release lock in finally
- **Dependencies:**
  - **Agents:** `master_graph::create_master_graph`, `state::create_initial_master_state`
  - **Core:** `settings::get_settings_manager`, `workspace::ensure_workspace_initialized`, `context_manager::detect_workspace_type`, `events::emit_run_started/completed/cancelled`
- **Exports:**
  - Class: `RunAlreadyActiveError` (exception)
  - Async Function: `run_agent(user_input, project_root, max_iterations=10, config=None)`
  - Async Function: `resume_with_approval(run_id, approved, config=None)`
  - Function: `get_current_run_id() -> Optional[str]`
  - Function: `is_run_active() -> bool`
  - Function: `cancel_current_run() -> bool`

---

#### **state.py** — State Schema
- **What:** LangGraph state definition (TypedDict + Pydantic models)
- **Why:** Single source of truth for all state fields
- **How:** Defines `MasterState`, `PatchPlan`, `CommandPlan`, `ApprovalRequest`, `ToolOutput`, message truncation logic
- **Dependencies:** `typing`, `pydantic`
- **Exports:**
  - Constant: `MESSAGE_HISTORY_LIMIT = 10`
  - Class: `PatchPlan` (BaseModel)
  - Class: `CommandPlan` (BaseModel)
  - Class: `ApprovalRequest` (BaseModel)
  - Class: `ToolOutput` (BaseModel)
  - TypedDict: `MasterState`
  - Function: `create_initial_master_state(...) -> MasterState`
  - Function: `truncate_messages(messages, limit) -> Tuple[List, str]`

---

### LAYER 4: Core Layer (src/core/)

#### **events.py** — Event Bus [CORE]
- **What:** Minimal async event bus using `asyncio.Queue`
- **Why:** Decouple backend (master_graph) from UI (Flet)
- **How:**
  1. `publish(event)`: Add event to all subscriber queues
  2. `subscribe()`: Return new asyncio.Queue for listening
  3. Rate limiting for status updates (2.0s intervals)
- **Dependencies:** `asyncio`, `time`, `datetime`, `logging`, `enum`
- **Exports:**
  - Enum: `EventType`
  - Class: `Event`
  - Class: `EventBus`
  - Function: `get_event_bus() -> EventBus` (singleton)
  - Async Functions: `emit_status()`, `emit_node_entered()`, `emit_node_exited()`, `emit_tool_requested()`, `emit_tool_executed()`, `emit_approval_requested()`, `emit_run_started()`, `emit_run_completed()`, `emit_run_cancelled()`
  - Async Generator: `iter_queue(queue)`

---

#### **settings.py** — Settings Management [CORE]
- **What:** SettingsManager using platformdirs for OS-standard config storage
- **Why:** Store API keys + model selections outside workspace (not in git)
- **Storage Paths (platformdirs):**
  - Windows: `%APPDATA%\Pulse\config.json`
  - Linux: `~/.config/pulse/config.json`
  - macOS: `~/Library/Application Support/Pulse/config.json`
- **Dependencies:** `json`, `pathlib`, `platformdirs::user_config_dir`
- **Exports:**
  - Class: `SettingsManager`
  - Function: `get_settings_manager() -> SettingsManager` (singleton)

---

#### **workspace.py** — Workspace Initialization
- **What:** WorkspaceManager creates `.pulse/` directory structure
- **Why:** Store workspace-local state (SQLite, Chroma vector store, logs)
- **How:**
  1. Create `.pulse/` directory
  2. Initialize SQLite DB (`.pulse/history.sqlite`)
  3. Create Chroma directory (`.pulse/chroma_db/`)
  4. Create logs directory (`.pulse/logs/`)
  5. Update `.gitignore` to exclude `.pulse/`
- **Dependencies:** `sqlite3`, `pathlib`, `logging`
- **Exports:**
  - Class: `WorkspaceManager`
  - Function: `ensure_workspace_initialized(project_root: str) -> WorkspaceManager`

---

#### **file_manager.py** — Secure File Operations
- **What:** FileManager with path validation + atomic writes
- **Why:** Prevent directory traversal attacks, ensure data integrity
- **How:**
  1. Validate all paths stay within `base_path` (project root)
  2. Reject `../` escape attempts
  3. Atomic writes: Write to temp file → rename
  4. Operations: read, write, delete, list, exists, is_directory
- **Dependencies:** `os`, `tempfile`, `pathlib`
- **Exports:**
  - Class: `FileManager`

---

#### **guardrails.py** — Safety Validation
- **What:** Security layer for file operations + output capping
- **Why:** Prevent sensitive file access, memory bloat, binary file corruption
- **Denylist Patterns:**
  - Environment: `.env`, `.env.*`, `credentials.json`, `secrets.json`, `.aws/`, `.ssh/`, `*.pem`, `*.key`
  - Git: `.git/config`, `.git/hooks/`, `.git/objects/` (read-only ok, writes denied)
  - System: `/etc/`, `C:\Windows\`, `C:\Program Files`
  - Binaries: `*.exe`, `*.dll`, `*.so`, `*.dylib`
- **Dependencies:** `re`, `pathlib`, `logging`
- **Exports:**
  - Constant: `DENYLIST_PATTERNS`
  - Constant: `TERMINAL_OUTPUT_MAX_CHARS = 10_000`
  - Exception: `PathViolationError`
  - Function: `validate_path(path, project_root, allow_read_only)`
  - Function: `validate_file_operation(path, operation, project_root)`
  - Function: `truncate_output(text, max_chars)`
  - Function: `is_file_binary(path)`

---

#### **prompts.py** — Centralized Prompt Registry
- **What:** Single source of truth for all agent prompts
- **Why:** Enable easy A/B testing, prevent hardcoded prompts
- **Dependencies:** None
- **Exports:**
  - String: `MASTER_SYSTEM_PROMPT`
  - String: `MASTER_SYSTEM_PROMPT_CHEAP`
  - String: `CREW_PLANNER_PROMPT`
  - String: `CREW_CODER_PROMPT`
  - String: `CREW_REVIEWER_PROMPT`
  - String: `AUTOGEN_AUDITOR_PROMPT`

---

### LAYER 5: Tool Belt Layer (src/tools/)

#### **registry.py** — Tool Registry [CORE]
- **What:** Central registry for tool registration and invocation
- **Why:** Consistent tool metadata, parameter validation, result wrapping
- **How:**
  1. `register_tool(ToolDefinition)`: Add tool with metadata
  2. `invoke_tool(name, args)`: Validate args, call tool function, wrap in ToolOutput
  3. `execute_patch_approved()`, `execute_terminal_cmd_approved()`: Special handlers for approved operations
- **Registered Tools (Phase 4):**
  - Tier 1: `manage_file_ops`, `apply_patch`, `search_workspace`
  - Tier 2: `run_terminal_cmd` (Phase 5), `dependency_manager` (Phase 5)
  - Tier 3: `implement_feature` (Phase 5+), `diagnose_project` (Phase 5+)
- **Dependencies:**
  - **Tools:** `file_ops::manage_file_ops`, `patching::{preview_patch, execute_patch}`, `rag::{search_workspace, RAGManager}`
  - **State:** `agents.state::ToolOutput`
- **Exports:**
  - Class: `ToolDefinition`
  - Class: `ToolRegistry`

---

#### **file_ops.py** — Tier 1: File Operations
- **What:** `manage_file_ops()` function for read/write/delete/list
- **Why:** Safe file operations with guardrails + RAG updates
- **Operations:** read, write, delete, list
- **Dependencies:**
  - **Core:** `file_manager::FileManager`, `guardrails::{validate_file_operation, truncate_output}`
- **Exports:**
  - Async Function: `manage_file_ops(operation, path, project_root, content=None, rag_manager=None) -> Dict`

---

#### **patching.py** — Tier 1: Code Patches
- **What:** `preview_patch()` + `execute_patch()` for unified diff application
- **Why:** Atomic code changes with approval flow
- **Flow:** Preview → Approve → Execute
- **Dependencies:**
  - **Core:** `file_manager::FileManager`
- **Exports:**
  - Function: `preview_patch(diff: str, project_root: Path) -> PatchPlan`
  - Function: `execute_patch(patch_plan: PatchPlan, project_root: Path) -> ToolOutput`

---

#### **rag.py** — Tier 1: Semantic Search
- **What:** `search_workspace()` + RAGManager for Chroma vector store
- **Why:** Answer questions like "Where is Motor_1 defined?"
- **Storage:** `.pulse/chroma_db/`
- **Dependencies:** `chromadb`, `sentence-transformers`
- **Exports:**
  - Class: `RAGManager`
  - Function: `search_workspace(query: str, project_root: Path, rag_manager: RAGManager) -> List[Dict]`

---

## Dependency Graph

```
main.py
  → src.ui.app

src.ui.app
  → src.ui.sidebar
  → src.ui.editor
  → src.ui.log_panel
  → src.ui.terminal
  → src.ui.status_bar
  → src.ui.menu_bar
  → src.ui.components.resizable_splitter
  → src.ui.components.vibe_loader
  → src.ui.components.settings_modal
  → src.ui.components.approval
  → src.ui.bridge
  → src.ui.theme
  → src.core.file_manager
  → src.core.processes
  → src.core.events
  → src.agents.master_graph

src.ui.bridge
  → src.core.events

src.ui.components.settings_modal
  → src.core.settings

src.agents.master_graph
  → src.agents.state
  → src.core.events
  → src.core.prompts
  → src.core.guardrails
  → src.tools.registry

src.agents.runtime
  → src.agents.master_graph
  → src.agents.state
  → src.core.settings
  → src.core.workspace
  → src.core.context_manager
  → src.core.events

src.tools.registry
  → src.agents.state
  → src.tools.file_ops
  → src.tools.patching
  → src.tools.rag

src.tools.file_ops
  → src.core.file_manager
  → src.core.guardrails

src.tools.patching
  → src.core.file_manager

src.core.file_manager
  → (external: os, tempfile, pathlib)

src.core.guardrails
  → (external: re, pathlib, logging)

src.core.settings
  → (external: json, pathlib, platformdirs)

src.core.workspace
  → (external: sqlite3, pathlib, logging)

src.core.events
  → (external: asyncio, time, datetime, logging, enum)
```

---

## Architecture Summary

### Overall Design Pattern: **Hub-and-Spoke with LangGraph**

**Hub (Master Agent)**
- Single decision-making node (master_agent_node in master_graph.py)
- Receives user input, decides tool sequence
- Returns final response to UI

**Spokes (Tool Belt)**
- Tier 1: Atomic operations (file I/O, patching, search)
- Tier 2: Permissioned tools (terminal, dependencies)
- Tier 3: Agentic subsystems (CrewAI, AutoGen)

**Approval Flow (Interrupt-Based)**
- Master decides tool → tool_execution node → interrupt() if approval needed
- UI shows approval modal → user approve/deny
- Resume with Command(resume={approved: bool})

**State Management**
- MasterState TypedDict with bounded message history
- Rolling summary for memory policy (last 10 turns verbatim)
- Single-run lock enforced at runtime layer

**UI Integration**
- UIBridge transports events from master_graph to Flet
- Vibe status words for contextual feedback
- Approval modals for patches/terminal commands
- Modern Claude Code-style welcome screen

---

## Critical Import Chains

### Path 1: User Input → Agent Execution
```
app.py::_handle_agent_query()
  → master_graph.py::create_master_graph()
    → master_graph.py::master_agent_node() [ASYNC]
      → call_llm_stub() [Phase 3] or real LLM [Phase 5+]
      → decide tool
      → tool_execution_node() [ASYNC]
        → registry.py::invoke_tool()
        → (tool function execution)
        → update tool_result
        → back to master_agent_node (via should_continue routing)
```

⚠️ **CRITICAL:** Must use `async for event in graph.astream()` not `.stream()`

### Path 2: File Operation → Safety Checks
```
registry.py::invoke_tool("manage_file_ops", args)
  → file_ops.py::manage_file_ops()
    → guardrails.py::validate_file_operation()
      → guardrails.py::validate_path()
      → DENYLIST check
    → file_manager.py::FileManager (read/write/delete/list)
      → atomic writes with temp file
    → RAG update on write/delete
```

### Path 3: Approval Flow
```
tool_execution_node() [needs approval]
  → interrupt(approval_data)
  → UI: app.py::_on_approval_request()
  → show_patch_approval() or show_terminal_approval()
  → user approve/deny
  → bridge.py::submit_approval()
  → graph.astream(Command(resume={approved: bool}))
  → back to tool_execution_node (after interrupt point)
  → execute_tool_approved() or return denial
```

---

## Summary Statistics

- **Total Python files in src/:** 40
- **UI components:** 17 files (Flet-based)
- **Agent layer:** 3 files (LangGraph orchestration)
- **Core infrastructure:** 8 files (settings, workspace, file ops, events, etc.)
- **Tool belt:** 9 files (registry + tools + subsystems)
- **Flet version:** 0.28.3 (latest)
- **Architecture:** Hub-and-Spoke with LangGraph master loop
- **Approval gates:** Patch preview + Terminal command preview

---

## Flet API Changes

### ⚠️ UserControl Removed (Flet 0.21.0+)

**Old Pattern (pre-0.21.0):**
```python
class MyControl(ft.UserControl):
    def build(self):
        return ft.Container(...)
```

**New Pattern (0.28.3):**
```python
class MyControl(ft.Container):
    def __init__(self):
        # Build content
        super().__init__(content=...)
```

**Key Changes:**
- Inherit directly from the control type you're building
- No `build()` method (construct in `__init__`)
- Lifecycle methods (`did_mount`, `will_unmount`) still work

**Example in Project:**
- `src/ui/components/loading_animation.py` uses `class LoadingAnimation(ft.Container)` ✅

---

## Key Files to Understand First

1. **main.py** - Entry point
2. **src/ui/app.py** - Main UI controller + integration
3. **src/agents/master_graph.py** - Core orchestration engine (⚠️ async nodes)
4. **src/agents/runtime.py** - High-level run entrypoint
5. **src/agents/state.py** - State schema
6. **src/core/events.py** - Event bus
7. **src/tools/registry.py** - Tool orchestration
8. **src/ui/bridge.py** - Event transport to UI
9. **src/ui/log_panel.py** - Chat interface with welcome screen

---

*This documentation was generated on 2025-12-24 for Pulse IDE v2.6.*
