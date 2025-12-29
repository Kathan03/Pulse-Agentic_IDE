# Pulse - Agentic AI IDE for PLC Coding
**Version:** 2.6 - Unified Master Loop / Hub-and-Spoke Architecture
## CORE CONSTRAINTS (Strict Adherence Required)
1. **Platform:** Windows Desktop Application (Local-first).
2. **UI Framework:** Python + Flet (No web frameworks like React/Vue).
3. **Orchestration:** LangGraph Unified Master Loop (hub-and-spoke) + CrewAI/Autogen (specialized subsystems only).
4. **Persistence:** SQLite (State) + Local File System (Workspace) + platformdirs (Global Settings).
5. **No Cloud:** All processing and storage are local (except LLM API calls).
6. **User Configurable Secrets:** API Keys stored via platformdirs (OS-standard path), managed through Settings UI, NEVER in workspace.
7. **CI/CD:** GitHub Actions must build Windows .exe on release tags (e.g., v0.1.0).
8. **Concurrency Policy:** **Single active agent run only** (global lock, no parallel agent loops).
9. **Approval Gates:** **Human confirmation required** for patch application and terminal commands.
## PROJECT SCOPE
We are building a **fully functional IDE** where an Automation Engineer can:
- Open a local folder (Workspace) with a professional file explorer
- View/Edit `.st` (Structured Text) files in a **VS Code-style tabbed editor**
- Use an **integrated terminal** at the bottom of the IDE
- **Resize all panels** (sidebar, editor, terminal) with draggable splitters
- Input natural language tasks via **Pulse Chat** (permanent first tab in editor)
- Watch the **Unified Master Agent** orchestrate work through a **Tool Belt**
- **Preview and approve** code patches before they are applied
- **Preview and approve** terminal commands before they execute
- Open multiple files simultaneously in **separate tabs** with close buttons
- Access settings via **VS Code-style menu bar** (File, View, Settings, Help)
- Configure API keys and models through **Settings UI** (stored via platformdirs)
**PLC v1 Scope:**
- **Text generation only** for `.st` (Structured Text), `.scl`, `.mat` files
- **No vendor compiler integration** (plugin seam reserved for future)
- **No live PLC connection** (local code editing and generation only)
**Scope Philosophy:**
- **UI:** Fully functional IDE experience (VS Code-level UX)
- **Agents:** Unified Master Loop (The Brain) + Tool Belt (The Hands)
- **Safety:** Human-in-the-loop approvals for patches and terminal commands
## ARCHITECTURE
### Complete Directory Structure (Source of Truth)
```
Pulse/
├── main.py # Application entry point + shutdown handler
├── requirements.txt # Python dependencies (includes crewai, autogen, platformdirs)
├── .env.example # Environment variables template (dev only)
├── .gitignore # Git ignore patterns
├── README.md # Project documentation
├── src/ # Source code root
│ ├── __init__.py
│ │
│ ├── ui/ # Flet UI Components (Presentation Layer)
│ │ ├── __init__.py
│ │ ├── app.py # Main Flet application controller (VS Code layout)
│ │ ├── menu_bar.py # VS Code-style menu bar (File, View, Settings, Help)
│ │ ├── sidebar.py # Workspace file tree + vibe status
│ │ ├── editor.py # EditorManager: Tabbed editor with Pulse Chat
│ │ ├── terminal.py # Integrated terminal panel
│ │ ├── agent_panel.py # Agent status + feedback
│ │ ├── settings_modal.py # Settings UI (API keys, models) - NEW
│ │ └── components/ # Reusable UI widgets
│ │ ├── __init__.py
│ │ ├── file_tree.py # Workspace folder tree widget
│ │ ├── patch_preview_modal.py # Patch approval dialog - NEW
│ │ ├── terminal_approval_modal.py # Terminal command approval - NEW
│ │ ├── vibe_loader.py # Vibe status words display - NEW
│ │ └── resizable_splitter.py # Draggable splitters for resizing
│ │
│ ├── agents/ # LangGraph Master Agent (Hub-and-Spoke)
│ │ ├── __init__.py
│ │ ├── master_graph.py # Unified Master Loop (LangGraph) - RENAMED
│ │ ├── master_agent.py # Master Agent node (The Brain) - NEW
│ │ └── subsystems/ # Specialized subsystems (The Hands) - NEW
│ │ ├── __init__.py
│ │ ├── crew_implementer.py # CrewAI: Planner → Coder → Reviewer
│ │ └── autogen_auditor.py # AutoGen: Project diagnostics
│ │
│ ├── core/ # Core Business Logic & Infrastructure
│ │ ├── __init__.py
│ │ ├── state.py # LangGraph state schema (Pydantic models)
│ │ ├── config.py # Application configuration (platformdirs)
│ │ ├── prompts.py # Prompt registry (mode-based system prompts) - NEW
│ │ ├── workspace.py # Workspace utilities (dynamic discovery, NO static classification)
│ │ ├── file_manager.py # Workspace file I/O (project-root restricted)
│ │ ├── db.py # SQLite session persistence (.pulse/history.sqlite)
│ │ ├── rag.py # Chroma vector store (.pulse/chroma_db/)
│ │ ├── llm_client.py # LLM provider abstraction (OpenAI + Anthropic) - NEW
│ │ ├── events.py # Event bus for UI updates - NEW
│ │ ├── settings.py # Settings management via platformdirs - NEW
│ │ ├── guardrails.py # Safety validation and denylist patterns - NEW
│ │ ├── processes.py # Process management for terminal commands - NEW
│ │ └── shutdown_handler.py # Graceful shutdown + zombie killer - NEW
│ │
│ └── tools/ # Tool Belt (3 Tiers)
│ ├── __init__.py
│ ├── registry.py # Tool registration and execution - NEW
│ ├── file_ops.py # manage_file_ops (Tier 1)
│ ├── patching.py # apply_patch (Tier 1)
│ ├── rag.py # search_workspace (Tier 1)
│ ├── terminal.py # run_terminal_cmd (Tier 2)
│ ├── deps.py # dependency_manager (Tier 2)
│ ├── web_search.py # web_search via DuckDuckGo (Tier 3) - NEW
│ ├── builder_crew.py # implement_feature via CrewAI (Tier 3)
│ ├── auditor_swarm.py # diagnose_project via AutoGen (Tier 3)
│ ├── logger.py # Structured logging utility (bounded)
│ └── validation.py # Input validation helpers
├── data/ # Global Persistence (platformdirs) - DEPRECATED
│ └── .gitkeep # Use platformdirs instead
├── workspace/ # User workspace (example/default)
│ ├── .pulse/ # Workspace-local state (gitignored) - NEW
│ │ ├── history.sqlite # SQLite session/state DB
│ │ ├── chroma_db/ # Chroma vector store
│ │ └── logs/ # Bounded log files (optional)
│ └── .keep # Placeholder
├── tests/ # Test Suite
│ ├── __init__.py
│ ├── conftest.py # Pytest fixtures
│ ├── test_agents/ # Agent orchestration tests
│ │ ├── __init__.py
│ │ ├── test_master_graph.py # Master loop tests
│ │ └── test_tool_belt.py # Tool belt tier tests
│ ├── test_core/ # Core functionality tests
│ │ ├── __init__.py
│ │ ├── test_file_manager.py
│ │ ├── test_db.py
│ │ ├── test_rag.py
│ │ └── test_shutdown.py # Shutdown handler tests - NEW
│ └── test_ui/ # UI component tests
│ └── __init__.py
└── .github/ # CI/CD Pipeline
    └── workflows/
        └── ci-cd.yml # GitHub Actions workflow (Windows .exe builds)
```
### Directory Responsibilities
**`/src/ui` - Presentation Layer (VS Code-like IDE):**
- `app.py` - Main layout controller with resizable panes
- `menu_bar.py` - VS Code-style menu bar (File, View, Settings, Help)
- `settings_modal.py` - Settings UI (API keys, model selection; saves via platformdirs)
- `editor.py` - EditorManager with Pulse Chat (Tab 0, permanent) + dynamic file tabs
- `terminal.py`, `sidebar.py`, `agent_panel.py` - Terminal panel, file tree + vibe status, agent feedback
- `components/` - patch_preview_modal, terminal_approval_modal, vibe_loader, resizable_splitter
**`/src/agents` - Hub-and-Spoke Architecture:**
- `master_graph.py` - Unified Master Loop (LangGraph, single active run)
- `master_agent.py` - Master Agent (The Brain, decides tool usage)
- `subsystems/` - crew_implementer (CrewAI), autogen_auditor (AutoGen diagnostics)
**`/src/core` - Business Logic & Infrastructure:**
- `state.py` - LangGraph state schema (Pydantic models)
- `prompts.py` - Centralized prompt registry (mode-based system prompts)
- `workspace.py` - Workspace utilities (dynamic discovery via tools, NO static classification)
- `file_manager.py` - File operations (project-root restricted, atomic writes)
- `db.py`, `rag.py` - SQLite (`.pulse/history.sqlite`), Chroma (`.pulse/chroma_db/`)
- `llm_client.py` - LLM provider abstraction (OpenAI + Anthropic with function calling)
- `shutdown_handler.py`, `config.py` - Graceful cleanup, settings via platformdirs
**`/src/tools` - Tool Belt (3 Tiers):**
- `tier1_atomic.py` - manage_file_ops, apply_patch, search_workspace
- `tier2_permissioned.py` - run_terminal_cmd, dependency_manager
- `tier3_intelligence.py` - web_search (DuckDuckGo), implement_feature (CrewAI), diagnose_project (AutoGen)
- `logger.py`, `validation.py` - Bounded logging, input validation
### Technology Stack
- **Language:** Python 3.x
- **UI:** Flet (Python-driven desktop UI, VS Code-style)
- **Editor:** Tabbed EditorManager with Pulse Chat integration
- **Terminal:** Integrated terminal panel (Flet components)
- **Orchestration:**
  - **LangGraph** - Unified Master Loop (hub-and-spoke architecture)
  - **CrewAI/Autogen** - Specialized subsystems (offloaded via `asyncio.to_thread`)
- **Agent Implementation Pattern (v2.6):**
  - **Master Agent (The Brain):** LangGraph node with access to Tool Belt
  - **Tool Belt (The Hands):** 3-tier tool system (Atomic, Permissioned, Agentic)
  - **Subsystems:** CrewAI/Autogen work runs in background threads; only structured summaries return to Master
  - **Concurrency:** Single active run only (global lock); no parallel agent loops
  - **UI Responsiveness:** `await asyncio.to_thread(crew.kickoff)` to prevent UI freeze
- **LLM:** OpenAI (GPT-5.x, GPT-4.1.x) + Anthropic (Claude 4.5 series) with function calling
- **Persistence:**
  - SQLite for sessions and state (`.pulse/history.sqlite` in workspace)
  - Chroma (local vector store) for RAG (`.pulse/chroma_db/` in workspace)
  - platformdirs for global settings (API keys, model selection)
  - Bounded logs in `.pulse/logs/` (optional)
- **Settings Management:** platformdirs (OS-standard paths: `~/.config/pulse` on Linux, `%APPDATA%\pulse` on Windows)
- **Packaging:** PyInstaller or flet pack for Windows .exe
- **CI/CD:** GitHub Actions
### Hub-and-Spoke Architecture (v2.6 Unified Master Loop)
**Purpose:** Replace multi-agent routing with a single Master Agent that orchestrates work through a Tool Belt.
**Core Concept:**
- **The Brain:** Unified Master Agent (LangGraph node) makes all decisions
- **The Hands:** Tool Belt (3 tiers) executes specific actions
- **Single-Run Lock:** Only one agent run active at a time (no concurrency)
- **Context Containment:** CrewAI/AutoGen transcripts never enter Master context (summaries only)
**Architecture Diagram:**
**Key Principles:**
1. **Single Active Run:** Global lock prevents concurrent agent loops
2. **Human Approvals:** Patches and terminal commands pause execution for user review
3. **Context Containment:** CrewAI/AutoGen work is blocking; transcripts discarded; only structured artifacts (PatchPlan, JSON) return to Master
4. **UI Responsiveness:** Subsystems run via `await asyncio.to_thread(...)` to prevent UI freeze
5. **Deterministic Resumption:** Interrupts (approvals) pause and resume graph deterministically
6. **Dynamic Workspace Understanding:** NO static context_manager - Master Agent discovers project structure via tools (Claude Code approach)
---
### Supported LLM Models
**Pulse v1.0 supports the following models for user selection in Settings UI:**
**OpenAI GPT-5.x Series:**
- `gpt-5.2` - Latest flagship model
- `gpt-5.1` - Previous generation
- `gpt-5` - Base model
- `gpt-5-mini` - Lightweight variant (default for master_agent)
- `gpt-5-nano` - Ultra-lightweight (default for subsystems)
- `gpt-5.1-codex` - Code-specialized variant
- `gpt-5.2-pro` - Professional tier
**OpenAI GPT-4.1.x Series (Legacy Support):**
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4.1-nano`
**Anthropic Claude 4.5 Series:**
- `claude-opus-4-5` - Largest model
- `claude-sonnet-4-5` - Balanced model
- `claude-haiku-4-5` - Fastest model
**Default Model Configuration** (in `src/core/settings.py`):
```python
"models": {
    "master_agent": "gpt-5-mini",
    "crew_coder": "gpt-5-nano",
    "autogen_auditor": "gpt-5-nano"
}
```
**Note:** These defaults optimize for cost and speed while maintaining quality. Users can change models via Settings UI.
---
### State Schema (LangGraph State Management)
**Core State Class:** `PulseState` (defined in `src/core/state.py`)
**Key Fields (Pulse v2.6):**
**Input Fields:**
- `user_input: str` - Original user request
- `workspace_path: str` - Current workspace directory (absolute path)
- `project_root: str` - Absolute project root (all file ops must stay within this boundary)
- `mode: str` - Current interaction mode ("agent", "ask", or "plan")
**Execution Control:**
- `run_id: str` - Unique ID for current run (for cancellation)
- `is_running: bool` - Global lock flag (only one active run)
- `is_cancelled: bool` - Cancellation flag (propagates to tools)
- `pending_approval: Optional[ApprovalRequest]` - Active approval (patch or terminal command)
**Tool Execution:**
- `patch_plans: List[PatchPlan]` - Pending patches (unified diffs) awaiting approval
- `terminal_commands: List[CommandPlan]` - Pending terminal commands (with rationale + risk label)
- `files_touched: List[str]` - Files created/modified during execution
- `tool_outputs: List[ToolOutput]` - Bounded outputs from tool calls
**Workspace Context:**
- `workspace_summary: Optional[str]` - High-level workspace structure summary
- `active_files: List[str]` - Files currently open in editor tabs
- `recent_changes: List[str]` - Recent modifications (for context)
**Output & Feedback:**
- `agent_response: str` - Final response to display in Pulse Chat
- `execution_log: List[str]` - Timestamped log of agent actions (bounded)
- `vibe_status: Optional[str]` - Current vibe word ("Wondering", "Preparing", etc.)
**Approval Flow Example:**
## TOOL BELT ARCHITECTURE (v2.6)
**Purpose:** Replace individual agent nodes with a unified Tool Belt that the Master Agent orchestrates.
### Architecture Pattern: Master Agent + Tool Belt
**Pattern:**
**Why This Pattern:**
- **Single Brain:** One Master Agent makes all decisions (no router, no multi-agent loops)
- **Modular Hands:** Tool Belt provides capabilities on demand
- **Context Control:** CrewAI/AutoGen transcripts discarded; only artifacts return
- **UI Responsiveness:** Blocking work offloaded via `asyncio.to_thread`
---
### TIER 1: Atomic Tools
**Purpose:** Fast, deterministic operations with no approval required (unless patch/terminal).
#### 1.1 `manage_file_ops`
- **Operations:** Create, Read, Update, Delete files
- **Safety:** **Project-root boundary enforcement** (all paths validated against `state.project_root`)
- **Denylist:** Refuses operations on `.env`, `credentials.json`, `.git/`, etc.
- **Returns:** File content or confirmation
#### 1.2 `apply_patch`
- **Input:** PatchPlan (file_path, unified diff, rationale)
- **Flow:** Generate diff → Preview in UI → **User approval required** → Apply to file
- **Safety:** Atomic write (temp file + rename)
- **Returns:** Success confirmation
#### 1.3 `search_workspace`
- **Purpose:** Semantic search over workspace files via RAG
- **Implementation:** Query Chroma vector store (`.pulse/chroma_db/`)
- **Returns:** Relevant file excerpts with paths
- **Use Case:** Answer questions like "Where is Motor_1 defined?"
---
### TIER 2: Permissioned Tools
**Purpose:** Potentially risky operations requiring explicit user approval.
#### 2.1 `run_terminal_cmd`
- **Input:** CommandPlan (command, rationale, risk_label: "LOW" | "MEDIUM" | "HIGH")
- **Flow:** Display CommandPlan in UI → **User approval required** → Execute in terminal
- **Safety:** User sees full command and rationale before execution
- **Returns:** stdout, stderr, exit code (bounded output)
#### 2.2 `dependency_manager`
- **Purpose:** Detect project tooling (venv, package.json, requirements.txt) and propose safe commands
- **Flow:** Scan workspace → Generate CommandPlan → Route to `run_terminal_cmd`
- **Examples:** "Install dependencies?" → `pip install -r requirements.txt` (MEDIUM risk)
- **Returns:** Detection results and proposed commands
---
### TIER 3: Intelligence Tools (Web + Subsystems)
**Purpose:** Complex tasks requiring external intelligence (web search) or specialized subsystems (CrewAI/AutoGen).
#### 3.1 `web_search`
- **Purpose:** Search the web for documentation, Stack Overflow answers, and technical resources
- **Implementation:** DuckDuckGo search (free, no API key required)
- **Flow:** Query → DuckDuckGo API → Parse results → Return formatted results with URLs
- **Use Cases:**
  - "How do I use Flet's ExpansionTile?" → Searches flet.dev docs
  - "Siemens TIA Portal timer examples" → Finds official Siemens resources
  - "Python asyncio best practices 2025" → Returns Stack Overflow + blog posts
- **Returns:** List of search results with title, URL, snippet
- **Error Handling:** Graceful degradation when offline (falls back to training data)
#### 3.2 `implement_feature`
- **Purpose:** Full feature implementation via CrewAI mini-crew
- **Flow:**
  1. **Planner agent:** Analyze request → Generate implementation plan
  2. **Coder agent:** Write code based on plan
  3. **Reviewer agent:** Review for quality and best practices
- **Execution:** `await asyncio.to_thread(crew.kickoff)` to prevent UI freeze
- **Context Containment:** Crew transcript discarded; only structured output returns
- **Returns:** `FeatureResult(patches: List[PatchPlan], summary: str, verification_steps: List[str])`
#### 3.3 `diagnose_project`
- **Purpose:** Project health audit via AutoGen debate
- **Flow:**
  1. Deterministic checks (file structure, imports, syntax)
  2. Optional AutoGen auditor debate (finds subtle issues)
- **Execution:** `await asyncio.to_thread(autogen_group.run)`
- **Context Containment:** Debate transcript discarded; only JSON returns
- **Returns:** `DiagnosisResult(risk_level: str, findings: List[Finding], fixes: List[Fix], verification_steps: List[str])`
**Strict Output Format:**
```json
{"risk_level":"HIGH","findings":[{"severity":"ERROR","file":"main.st","line":42,"message":"..."}],"prioritized_fixes":[{"priority":1,"action":"...","rationale":"..."}],"verification_steps":["1. Run tests","2. Check build"]}
```
## UNIFIED MASTER LOOP (v2.6 Interaction Model)
**Philosophy:** Single Master Agent with 3 operational modes - behavior adapts via mode-based system prompts.
**3 Modes (User Selectable):**
1. **Agent Mode** - Full access to all tools (can modify files, run commands, search web)
2. **Ask Mode** - Read-only access (can search workspace/web, cannot modify files or run commands)
3. **Plan Mode** - Planning only (can search workspace, generates implementation plans without executing)
**Key Concept:** These are NOT separate agents - they are the SAME Master Agent with different system prompts and tool access restrictions.
**Mode Selection:** User selects mode from dropdown in UI (similar to Cursor's mode selector).
### Single Interaction Flow
**User Experience:**
1. User enters request in **Pulse Chat** tab
2. **Master Agent analyzes** request and decides tool sequence
3. For **code changes:**
   - Master generates or delegates to `implement_feature` (CrewAI)
   - **Patch preview modal** appears with diff
   - User approves or rejects
   - Approved patches applied atomically
   - Modified files open in tabs
4. For **terminal commands:**
   - Master generates CommandPlan (command + rationale + risk label)
   - **Terminal approval modal** appears
   - User approves or rejects
   - Approved commands execute in terminal
5. For **questions:**
   - Master uses `search_workspace` (RAG) or direct LLM
   - Answers appear in Pulse Chat with file references
6. Master summarizes actions and results
**Mode-Based Behavior:**
- **Agent Mode:** Master has access to `apply_patch`, `run_terminal_cmd`, `web_search`, all Tier 1-3 tools
- **Ask Mode:** Master has access to `search_workspace`, `manage_file_ops` (read-only), `web_search` only
- **Plan Mode:** Master has access to `search_workspace`, `manage_file_ops` (read-only) only
**Human-in-the-Loop Gates:**
- **Patch approval:** ALL code changes previewed before application
- **Terminal approval:** ALL commands shown with risk labels before execution
**Use Cases:**
- **"Add a timer to the conveyor logic"**
  - Master calls `implement_feature` (CrewAI: Plan → Code → Review)
  - Returns PatchPlan with diff
  - User sees preview, approves
  - Patch applied, file opens in tab
- **"Install pytest"**
  - Master generates CommandPlan: `pip install pytest` (MEDIUM risk)
  - User sees rationale ("Install testing framework"), approves
  - Command executes in terminal
- **"What does StartMotor do?"**
  - Master calls `search_workspace` (RAG query)
  - Returns file excerpts with context
  - Displays in Pulse Chat with clickable file links
## SYSTEM REQUIREMENTS (v2.6)
### Prompt Registry
**Purpose:** Centralize all prompts for maintainability and A/B testing.
**Implementation:** `src/core/prompts.py`
**Required Prompts:**
```python
# Master Agent
MASTER_SYSTEM_PROMPT = """You are the Pulse Master Agent..."""

# CrewAI subsystem
CREW_PLANNER_PROMPT = """Analyze the request and generate a plan..."""
CREW_CODER_PROMPT = """Implement the plan step by step..."""
CREW_REVIEWER_PROMPT = """Review code for quality and best practices..."""

# AutoGen subsystem
AUTOGEN_AUDITOR_PROMPT = """Debate project health findings..."""

# Optional: cheap model variants
MASTER_SYSTEM_PROMPT_CHEAP = """..."""  # For non-critical tasks
```
**Usage in Agents:**
**Benefits:**
- Single source of truth for all prompts
- Easy A/B testing (swap prompt, measure results)
- PLC-specific variants (e.g., `CREW_CODER_PROMPT_ST` for Structured Text)
---
### Shutdown Handler & Zombie Killer
**Purpose:** Ensure clean shutdown with no orphaned processes.
**Implementation:** `src/core/shutdown_handler.py` + `main.py` integration
**Responsibilities:**
1. **Cancel active agent run:**
   - Set `state.is_cancelled = True`
   - Propagate cancellation flag to all tools
2. **Shutdown thread pools:**
   - `executor.shutdown(wait=True, cancel_futures=True)`
3. **Kill child PIDs:**
   - Track subprocesses spawned by `run_terminal_cmd`
   - Terminate on app close
4. **Close database connections:**
   - SQLite, Chroma handles
**Trigger:**
**Critical for:** Preventing zombie CrewAI/AutoGen processes after user closes IDE.
---
### Safety Requirements
#### Project-Root Boundary Enforcement
- **All file operations** validated against `state.project_root`
- Attempts to access parent directories (`../`) rejected
- Symlinks resolved and checked
#### Denylist Patterns
- **Automatically deny** operations on:
  - `.env`, `credentials.json`, `.aws/`, `.ssh/`
  - `.git/` (read-only allowed, writes denied)
  - Binary files (unless explicitly allowed)
  - System directories (`/etc/`, `C:\Windows\`)
- **User override:** Explicitly allowed patterns in Settings (advanced users only)
#### Terminal Command Risk Labels
- **LOW:** Read-only commands (`ls`, `cat`, `git status`)
- **MEDIUM:** Install/build commands (`pip install`, `npm run build`)
- **HIGH:** Destructive commands (`rm -rf`, `git reset --hard`, `DROP TABLE`)
- **Approval modal color-coded** by risk level
#### Tool Output Size Caps
- **Terminal output:** Max 10,000 characters (truncate with "... output truncated")
- **Log files:** Bounded rotation (max 10 files, 1MB each)
- **CrewAI/AutoGen transcripts:** Discarded (never stored)
---
### Settings Management (platformdirs)
**Purpose:** Store global settings in OS-standard location, managed via Settings UI.
**Implementation:** `src/core/config.py` + `src/ui/settings_modal.py`
**Storage Location (via platformdirs):**
- **Windows:** `%APPDATA%\Pulse\config.json`
- **Linux:** `~/.config/pulse/config.json`
- **macOS:** `~/Library/Application Support/Pulse/config.json`
**Settings Structure:**
```json
{"api_keys":{"openai":"sk-...","anthropic":""},"models":{"master_agent":"gpt-4o","crew_coder":"gpt-4o","autogen_auditor":"gpt-4o-mini"},"preferences":{"theme":"dark","enable_autogen":true}}
```
**Settings UX Flow:**
1. User opens Settings (Menu Bar → Settings → API Keys)
2. **Settings Modal** appears with input fields
3. User pastes API key, selects model from dropdown
4. Clicks "Save"
5. Pulse saves to platformdirs path (user never navigates manually)
6. **Warning displayed:** "Keys are stored securely in your user profile"
**Security:**
- **Never** save keys in workspace (`.env` files)
- **Never** commit keys to git
- Dev mode fallback: Read from `.env` with console warning
---
### Workspace Initialization & Dynamic Discovery
**On workspace open:**
1. Create `.pulse/` directory if not exists
2. Initialize SQLite schema: `.pulse/history.sqlite`
3. Initialize Chroma: `.pulse/chroma_db/`
4. Add `.pulse/` to `.gitignore` (if git repo)
5. **NO static workspace classification** - Master Agent discovers project structure dynamically via tools
**Dynamic Workspace Understanding (Claude Code Approach):**
- **No pre-classification** - No workspace_type detection upfront
- **Tool-based discovery** - Master Agent uses `search_workspace` and `manage_file_ops` to understand project on-demand
- **PLC detection** - When Master Agent sees `.st` files during tool usage, it dynamically enhances prompts with PLC expertise
- **Multi-language support** - Workspace can contain Python + PLC + JavaScript; Master discovers each as needed
- **Flexible and accurate** - No assumptions, everything discovered through actual file exploration
**`.pulse/` Structure:**
## VS CODE-STYLE EDITOR (Critical Feature)
### Features
**Tabbed Interface:** Tab 0 "Pulse Chat" (permanent), dynamic file tabs `[filename ×]`, click to switch/close
**File Operations:** Click sidebar to open/focus, × to close, agent-modified files auto-open
**Editor:** Monospace font, line numbers, basic syntax highlighting, Ctrl+S save, immediate persist
**Agent-Aware:** Agent uses same File Manager, writes trigger tab refresh, manual edits are ground truth
**Safety:** Workspace-constrained, atomic writes
### Integrated Terminal
**Appearance:** Bottom panel, black (#1E1E1E), monospace, `Pulse> ` prompt
**Features:** Command history (↑/↓), stdout/stderr display, workspace-rooted execution
**Use Cases:** Build scripts, compiler commands, file status, git ops
### Resizable Panels
**Implementation:** `ft.GestureDetector` splitters - vertical (sidebar/main), horizontal (editor/terminal)
**UX:** Hover for resize cursor, drag to resize, sizes persist (SQLite)
---
## V1.0 IMPLEMENTATION PLAN (5 Phases)
**Current Status:** Phase 0 Complete (UI + basic agent skeleton)
**Objective:** Reach production-ready v1.0 through 5 focused implementation phases.
### Phase 1: LLM Integration (CRITICAL)
**Goal:** Replace stub LLM with real OpenAI + Anthropic integration
**Key Deliverables:**
- `src/core/llm_client.py` - LLMClient class with OpenAI + Anthropic support
- Function calling implementation for both providers
- Mode-based system prompts (Agent/Ask/Plan) in `src/core/prompts.py`
- Replace `call_llm_stub()` in `master_graph.py` with real LLM calls
- Tool schema definitions for all tools
**Success Criteria:**
- Master Agent can call GPT-5.2, Claude Opus 4.5, etc.
- Function calling works (Master can invoke tools)
- Mode switching changes system prompt dynamically
- No stub code remaining
**Documentation:** See `docs/PHASE_1_PROMPT.md` for detailed implementation guide
---
### Phase 2: Architecture Cleanup
**Goal:** Delete static context_manager, implement dynamic workspace understanding
**Key Deliverables:**
- **DELETE** `src/core/context_manager.py` completely
- Remove `detect_workspace_type()` calls from `runtime.py`
- Remove `workspace_type` from `MasterState` schema
- Dynamic PLC detection when Master Agent sees `.st` files during tool usage
- Workspace understanding via `search_workspace` and `manage_file_ops` only
**Success Criteria:**
- No context_manager.py file exists
- No workspace_type in state
- Hybrid projects (Python + PLC + JS) handled correctly
- Master Agent discovers project structure dynamically
- Pure Claude Code architecture achieved
**Documentation:** See `docs/PHASE_2_PROMPT.md` for detailed implementation guide
---
### Phase 3: Web Search Tool
**Goal:** Add web search capability for documentation research
**Key Deliverables:**
- `src/tools/web_search.py` - DuckDuckGo integration
- Register `web_search` in Tool Registry (Tier 3)
- Update Agent/Ask mode prompts to mention web search capability
- Error handling for offline/rate limits
**Success Criteria:**
- Master Agent can search web via function calling
- Documentation questions answered with source links
- PLC documentation searchable (Siemens, Beckhoff, etc.)
- Graceful degradation when offline
**Documentation:** See `docs/PHASE_3_PROMPT.md` for detailed implementation guide
---
### Phase 4: UI Fixes & Polish
**Goal:** Fix UI bugs and update to production quality
**Key Deliverables:**
- Fix sidebar scrolling (add `expand=True`)
- Fix menu bar visibility (Flet MenuBar rendering)
- Implement VS Code-style file tree with `ExpansionTile`
- Update model dropdown to 13 supported models
- Move feedback to Help → Report Issue
- Verify all Flet attributes against official docs (no made-up attributes)
**Success Criteria:**
- Sidebar scrolls smoothly
- Menu bar fully visible with File/View/Settings/Help
- File tree expands/collapses like VS Code
- Model dropdown shows all 13 models
- Feedback accessible via Help menu
**Documentation:** See `docs/PHASE_4_PROMPT.md` for detailed implementation guide
---
### Phase 5: Testing & Production Release
**Goal:** Comprehensive testing and v1.0 release
**Key Deliverables:**
- End-to-end test suite (LLM integration, mode switching, PLC generation)
- Approval gates tested (patch preview, terminal approval)
- Performance benchmarks (response times < 5 seconds)
- Production readiness checklist
- CI/CD workflow for Windows .exe builds
- GitHub release preparation
**Success Criteria:**
- All core workflows tested
- No critical bugs
- Error handling graceful
- Performance acceptable
- Ready for public release
**Documentation:** See `docs/PHASE_5_PROMPT.md` for detailed implementation guide
---
**After Phase 5:** Pulse v1.0 matches Claude Code capabilities with PLC specialization and better UI.
**Phase Prompts Location:** All detailed phase prompts are in `docs/` directory for easy handoff to new Claude Code sessions.
---
### KEEP SIMPLE (Scope Constraints):
- **No cloud backend** (local-first only)
- **No multi-project management** (single workspace at a time)
- **No direct PLC hardware connection** (code generation only)
- **PLC v1 scope:** Text generation for `.st`/`.scl`/`.mat` (no vendor compiler integration)
- **Single active run only** (no concurrency, no parallel agents)
## OPERATIONAL EXCELLENCE
### CI/CD Pipeline (GitHub Actions)
**Triggers:**
- **On every push/PR to main:** Run linting and unit tests
- **On tag (e.g., v0.1.0):** Run tests, Build .exe, Attach to GitHub Release
**Jobs:**
1. **lint_and_test (Ubuntu):** Static analysis (ruff), Unit tests (pytest)
2. **build_windows (Windows):** Build .exe via PyInstaller or flet pack
3. **release (Ubuntu):** Create GitHub Release with attached Windows artifact
## SUCCESS CRITERIA
A reviewer can:
1. Install Pulse from GitHub Release .exe
2. **Experience a fully functional IDE:**
   - Open workspace and browse files in sidebar
   - Select mode from mode selector
   - Open multiple files in tabs
   - Close tabs with × button
   - Resize sidebar and terminal by dragging splitters
   - Use integrated terminal for commands
   - Switch between Pulse Chat and file tabs
3. Complete one end-to-end flow in each mode:
   - **Agent Mode:** requirement in Pulse Chat → code change → new file tab opens → feedback
   - **Plan Mode:** requirement → plan review in Agent Panel → approve → code change
   - **Ask Mode:** ask question in Pulse Chat → receive explanation with file references
4. **Perception:** "This is a real, professional IDE with AI agents, not a prototype"
## DEVELOPMENT PRINCIPLES
1. **Professional UI, MVP Agents:** Invest in IDE UX, use simple GPT-4o agents
2. **Local-First:** All data stays on user's machine
3. **Safety:** Atomic writes, workspace constraints, no destructive operations
4. **Modularity:**
   - LangGraph for workflow orchestration
   - CrewAI/Autogen for node implementation details
   - Clean separation of UI, agents, core
5. **VS Code Philosophy:** Familiar, professional, keyboard-friendly
## REFERENCE DOCUMENTS
- Full PRD: `Pulse_Agentic_AI_IDE_PRD.MD`
- This file (`CLAUDE.md`) is the **source of truth** for all v2.6 implementation decisions
## CRITICAL IMPLEMENTATION RULES
### Architecture Decisions (Non-Negotiable)
**1. NO context_manager.py**
- **FORBIDDEN:** Static workspace classification (workspace_type detection)
- **REQUIRED:** Dynamic workspace understanding via tools (Claude Code approach)
- **Rationale:** Master Agent discovers project structure on-demand using `search_workspace` and `manage_file_ops`
**2. Single Master Agent (Hub-and-Spoke)**
- **FORBIDDEN:** Multi-agent systems (separate Planner Agent, Coder Agent, etc.)
- **REQUIRED:** One Master Agent + Tool Belt (3 tiers)
- **Rationale:** Proven by Claude Code/Cursor; simpler, more maintainable
**3. 3 Modes Only (Mode-Based Prompting)**
- **FORBIDDEN:** Separate agents for each mode
- **REQUIRED:** Same Master Agent with different system prompts per mode (Agent/Ask/Plan)
- **Rationale:** Tool access restrictions + prompt changes = different behavior
**4. Dynamic PLC Detection**
- **FORBIDDEN:** Upfront PLC project classification
- **REQUIRED:** Detect `.st` files during tool usage → enhance prompt dynamically
- **Rationale:** Supports hybrid projects (Python + PLC + JS) without assumptions
**5. Web Search in Tier 3**
- **FORBIDDEN:** Expecting Master to know all documentation from training data
- **REQUIRED:** `web_search` tool for documentation research (DuckDuckGo)
- **Rationale:** Current information (2025 docs) not in training data
---
### Code Reuse Policy
- **READ FIRST:** Always read existing codebase before proposing changes
- **DELETE WITH PROOF:** Only delete files after proving they are unused AND not aligned with v2.6 architecture
- **REFACTOR OVER REWRITE:** Prefer updating existing code to match v2.6 requirements
### v2.6 Migration Checklist
Before marking any file as DELETE, verify:
1. File is not referenced in v2.6 architecture (check directory structure above)
2. File functionality is not needed (check Tool Belt tiers, System Requirements)
3. File is not indirectly used (check imports across codebase)
**Example:**
- **WRONG:** "Delete `router_node.py` because we're using Master Agent now"
- **RIGHT:** "Refactor `router_node.py` → `master_agent.py`; keep workspace analysis logic"
### asyncio.to_thread Requirements
ALL blocking CrewAI/AutoGen calls MUST be wrapped:
```python
# WRONG - Blocks UI thread
result = crew.kickoff()

# CORRECT - Offloads to thread
result = await asyncio.to_thread(crew.kickoff)
```
### Prompt Registry Requirements
ALL prompts MUST be in `src/core/prompts.py`:
```python
# WRONG - Hardcoded in agent
prompt = "You are a PLC coder..."

# CORRECT - Reference registry
from src.core.prompts import CREW_CODER_PROMPT
prompt = CREW_CODER_PROMPT
```
