# Pulse – Agentic AI IDE for PLC Coding

**Document Type:** Product Requirements Document (PRD)
**Version:** 2.6 - Unified Master Loop / Hub-and-Spoke Architecture
**Platform:** Windows Desktop Application
**Scope:** Professional IDE (UI) + Unified Master Agent + Tool Belt (v2.6)

---

## 1. Problem Statement

Programming PLCs (Programmable Logic Controllers) today is:

* **Manual:** Engineers hand-write ladder logic or structured text in vendor-specific IDEs.
* **Error-prone:** Small mistakes in timing, interlocks, or I/O mapping can lead to production downtime or safety incidents.
* **Slow to iterate:** Each change requires mentally simulating logic, redeploying, and often involving on-site testing.
* **Tooling-fragmented:** IDEs do not provide modern AI assistance (planning, refactoring, context-aware Q&A).

Automation engineers are under pressure to ship changes quickly while maintaining reliability. They lack an “AI pair programmer” tailored to PLC workflows.

---

## 2. Proposed Solution – Pulse ("Cursor for PLC")

Pulse is an Agentic AI IDE for PLC-style code, delivered as a local Windows desktop app. It acts as a PLC-focused "Cursor/Copilot," helping engineers:

* Turn natural language requirements into actionable code changes.
* Preview and approve all code patches before they are applied.
* Preview and approve all terminal commands before they execute.
* Search and understand existing codebases via local RAG.
* Generate PLC-style code safely in a workspace on their machine.

**Key design principles (v2.6):**
* **Local-first:** All files, state, and settings stay on the user's machine.
* **Hub-and-Spoke:** Single Unified Master Agent orchestrates work through a Tool Belt.
* **Human-in-the-Loop:** Mandatory approval gates for patches and terminal commands.
* **Context Containment:** CrewAI/AutoGen transcripts never enter Master context (summaries only).
* **Operational Excellence:** Automated CI/CD builds Windows .exe on release tags.

---

## 3. User Persona

**Primary Persona – Automation Engineer**

* **Role:** Automation / Controls Engineer (in manufacturing, logistics, or process industry).
* **Goals:**
    * Implement PLC logic changes faster with fewer defects.
    * Understand and safely modify existing PLC programs.
    * Experiment with “what-if” logic changes before deploying to the PLC.
* **Pain Points:**
    * Vendor IDEs lack high-level guidance and explanation.
    * Debugging timing or state issues is tedious.
    * Little reuse or codification of tribal knowledge.
* **Environment:**
    * Windows laptop/desktop on or near the shop floor.
    * Mix of online/offline connectivity.
    * Often restricted from uploading code to external cloud services.

*For the MVP, we assume a technically comfortable engineer who is open to using an AI assistant, but still wants control over code and changes.*

---

## 4. Scope – Professional IDE with v2.6 Architecture

### Philosophy
* **UI & IDE Experience:** Production-quality, VS Code-level user experience
* **Agent Architecture:** Unified Master Loop (The Brain) + Tool Belt (The Hands)
* **Safety First:** Human approval gates for all code changes and terminal commands

### In Scope (v2.6)
**Windows desktop application built with:**
* **UI:** Python + Flet (VS Code-style layout with menu bar)
* **Orchestration:** LangGraph Unified Master Loop (single agent, no router)
* **Subsystems:** CrewAI/Autogen (wrapped as agentic tools, context-contained)
* **Storage:** Local workspace with `.pulse/` state directory
* **Persistence:** SQLite (`.pulse/history.sqlite`) + Chroma (`.pulse/chroma_db/`)
* **Settings:** platformdirs (OS-standard path for API keys and preferences)

**PLC v1 Scope:**
* **Text generation only** for `.st` (Structured Text), `.scl`, `.mat` files
* **No vendor compiler integration** (plugin seam reserved for future)
* **No live PLC connection** (local code editing and generation only)

**Tool Belt (3 Tiers):**
* **Tier 1 (Atomic):** `manage_file_ops`, `apply_patch`, `search_workspace`
* **Tier 2 (Permissioned):** `run_terminal_cmd`, `dependency_manager`
* **Tier 3 (Agentic):** `implement_feature` (CrewAI), `diagnose_project` (AutoGen)

**Approval Gates (CRITICAL):**
* **Patch Preview Modal:** Display unified diff → user approves/rejects → apply
* **Terminal Approval Modal:** Display CommandPlan + risk label → user approves/rejects → execute

**VS Code-style IDE features:**
* **Menu Bar:**
  * File: Open Workspace, Save All, Exit
  * View: Toggle Terminal, Toggle Sidebar
  * Settings: API Keys, Models, Agent Toggles
  * Help: About Pulse, Documentation
* **Tabbed Editor:**
  * Multiple file tabs with close buttons (×)
  * Permanent "Pulse Chat" tab (Tab 0) for agent interactions
  * Click files in sidebar to open in new tabs
  * Syntax highlighting, line numbers, monospace font
* **Integrated Terminal:**
  * Bottom panel with terminal interface
  * Black background, monospace font
  * Command history support
* **Resizable Panels:**
  * Draggable vertical splitter (sidebar ↔ main content)
  * Draggable horizontal splitter (editor ↔ terminal)
* **Workspace File Tree:**
  * Left sidebar showing folder structure
  * Files open in editor on click
* **Vibe Status:**
  * Subtle status words during agent work (Wondering, Preparing, Rejoicing)
  * Rate-limited updates (2-3 seconds)

**CI/CD (GitHub Actions workflow):**
* Run tests and linting on every push/PR
* Build Windows .exe on release tags (e.g., `v0.1.0`)
* Attach binary to GitHub Release

### Out of Scope
* Direct connection to live PLC hardware (PLC v1: code generation only)
* Vendor compiler integration (reserved for future plugin)
* Multi-project management (single workspace at a time)
* Cloud backend, user accounts, or centralized logging
* Concurrent agent runs (single active run only)
* Advanced editor features (IntelliSense, debugger, extensions)

---

## 5. Solution Overview (v2.6)

At a high level:

1. **User opens Pulse** and selects a workspace folder containing PLC-style code (or starting empty).
2. **Workspace initialization:** Pulse creates `.pulse/` directory with SQLite DB and Chroma vector store.
3. **User configures API keys** via Settings modal (Menu Bar → Settings → API Keys) stored in platformdirs.
4. **User enters task** in Pulse Chat, e.g., *"Add a timer to the conveyor logic"*.
5. **Unified Master Agent analyzes** request and decides which tools to use:
   - For **simple questions:** Uses `search_workspace` (RAG) → displays answer in chat
   - For **code changes:** Uses `implement_feature` (CrewAI subsystem) → generates PatchPlan
   - For **terminal commands:** Uses `run_terminal_cmd` → generates CommandPlan
6. **Human approval gates:**
   - **Patch preview modal** shows unified diff → user approves/rejects
   - **Terminal approval modal** shows command + risk label → user approves/rejects
7. **Execution:**
   - Approved patches applied atomically to workspace
   - Modified files automatically open in editor tabs
   - Approved commands execute in terminal
8. **Master summarizes** actions and results in Pulse Chat.
9. **All state persists** locally in `.pulse/` directory; global settings in platformdirs.

---

## 6. User Personas & Key Use Cases

### Primary Use Cases

**Generate new PLC logic from a requirement**
* User describes behavior in plain language.
* Pulse produces a plan, code files, and a brief explanation.
* Generated code is opened in the embedded editor for inspection and further manual edits.

**Modify existing PLC logic**
* User opens an existing project folder and selects files from the workspace tree.
* They review and optionally hand-edit the code in the integrated editor.
* User describes a desired change in natural language.
* Pulse:
    * Analyzes the current code.
    * Proposes a plan (in Plan Mode) or directly edits files (in Agent Mode).
    * Updates the same files the user can continue editing manually in the editor.

**Understand and explain existing code**
* User asks *“What does this timer do?”* or *“How is Motor_1 interlocked?”*
* Pulse reads the codebase and provides a structured explanation, referencing specific files opened in the editor.

**Collect feedback on code quality**
* After each run, the user rates the outcome and optionally adds comments.
* Pulse logs these for future improvement/fine-tuning (locally).

---

## 7. Key Features – Tool Belt & IDE (v2.6)

### 7.0 Unified Master Agent (The Brain)

**Purpose:** Single decision-making agent that orchestrates all work through the Tool Belt.

**Responsibilities:**
- Analyze user requests and determine appropriate tool sequence
- Call tools from 3-tier Tool Belt based on task requirements
- Handle interrupts (approval gates) deterministically
- Summarize actions and results for user

**Implementation:**
- LangGraph node with access to full Tool Belt
- References centralized prompts (`src/core/prompts.py`)
- Single active run (global lock enforced)
- Cancellable from UI (propagates to all tools)

**No Router:** Master Agent directly decides which tools to use (no classification step).

---

### 7.1 Tool Belt (The Hands)

**Architecture:** 3-tier system providing capabilities to Master Agent.

#### Tier 1: Atomic Tools
- **`manage_file_ops`:** CRUD operations (project-root restricted, denylist enforced)
- **`apply_patch`:** Unified diff generation → preview → approval → atomic write
- **`search_workspace`:** RAG queries over workspace (Chroma vector store)

#### Tier 2: Permissioned Tools
- **`run_terminal_cmd`:** CommandPlan → approval modal → execute (with risk labels)
- **`dependency_manager`:** Detect tooling → propose safe commands → route to `run_terminal_cmd`

#### Tier 3: Agentic Tools (Subsystems)
- **`implement_feature`:** CrewAI (Planner → Coder → Reviewer) → returns PatchPlans + summary
- **`diagnose_project`:** AutoGen (deterministic checks + debate) → returns JSON findings

**Context Containment:** CrewAI/AutoGen transcripts discarded; only structured outputs return.

**UI Responsiveness:** Tier 3 tools offloaded via `await asyncio.to_thread(...)`.

---

### 7.2 VS Code-Style IDE Experience
*Purpose: Deliver a production-quality IDE that engineers will want to use daily.*

**Layout (VS Code-inspired):**
```
┌─────────────────────────────────────────────────────────────┐
│                    Pulse - Agentic AI IDE                    │
├──────────┬──────────────────────────────────────────────────┤
│          │  [Pulse Chat] [main.st ×] [motor_ctrl.st ×]     │
│ Sidebar  │  ┌─────────────────────────────────────────────┐ │
│          │  │                                             │ │
│ • Files  │  │                                             │ │
│ • Agent  │  │         EDITOR CONTENT AREA                 │ │
│          │  │         (Tabbed Files)                      │ │
│          │  │                                             │ │
│          │  └─────────────────────────────────────────────┘ │
│  <=>     │  ═════════════════════════════════════════════   │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │ Pulse> _                                    │ │
│          │  │ TERMINAL OUTPUT                             │ │
│          │  └─────────────────────────────────────────────┘ │
└──────────┴──────────────────────────────────────────────────┘
```

* **Tabbed Editor:**
    * **Tab 0 (Permanent): "Pulse Chat"**
      * Non-closable tab for agent interactions
      * Mode selector (Agent/Plan/Ask)
      * Chat interface for natural language requests
      * Displays agent responses, plans, and validation results
    * **Dynamic File Tabs (Tab 1+):**
      * Each opened file gets its own tab with close button (×)
      * Tab header shows filename
      * Click file in sidebar → opens in new tab (or focuses if already open)
      * Supports viewing and editing PLC-style (Structured Text) code
      * Monospaced font, line numbers, syntax highlighting
      * Changes saved to disk and become context for agents

* **Workspace File Tree (Sidebar):**
    * Left panel showing workspace folder structure
    * Click file → opens in editor tab
    * New files created by Coder Agent appear automatically
    * Visual indicators for modified files

* **Integrated Terminal (Bottom Panel):**
    * Black background, monospace font
    * Terminal prompt (`Pulse> `)
    * Command history (up/down arrows)
    * Can run workspace scripts, view logs, etc.

* **Resizable Panels:**
    * **Vertical splitter:** Drag to resize sidebar ↔ main content area
    * **Horizontal splitter:** Drag to resize editor ↔ terminal
    * Splitters have visual affordance (handle/gripper)

* **Agent Panel (Sidebar):**
    * Mode selector buttons (Agent/Plan/Ask)
    * Customizer feedback section (star rating + comments)
    * Plan view for approval workflow

* **Agent-Aware Editing:**
    * Master Agent reads files via same file manager
    * Writes changes that editor immediately reflects in tabs
    * Manual user edits are first-class: subsequent agent runs use updated file contents as ground truth

* **Safety:**
    * All edits (human or agent) constrained to project root
    * Atomic writes when applying patches (temp file + rename)
    * Denylist patterns prevent editing sensitive files (.env, credentials, etc.)

---

### 7.3 Approval Gates (Human-in-the-Loop)

**Purpose:** Ensure user control over all code changes and terminal commands.

#### Patch Preview Modal
* **Trigger:** Master Agent or `implement_feature` generates PatchPlan
* **Display:**
  * Unified diff with syntax highlighting
  * Rationale explaining why this change is needed
  * Affected file paths
  * Approve / Reject buttons
* **Flow:**
  1. Graph pauses execution
  2. User reviews diff in modal
  3. User clicks Approve → patch applied atomically
  4. User clicks Reject → patch discarded, Master continues
  5. Modified files automatically open in editor tabs

#### Terminal Approval Modal
* **Trigger:** Master Agent or tool generates CommandPlan
* **Display:**
  * Full command to be executed
  * Rationale explaining purpose
  * Risk label (LOW / MEDIUM / HIGH) with color coding
  * Approve / Reject buttons
* **Flow:**
  1. Graph pauses execution
  2. User reviews command and risk level
  3. User clicks Approve → command executes in terminal
  4. User clicks Reject → command discarded
  5. Terminal output displayed in integrated terminal panel

**Risk Label Examples:**
- **LOW:** `git status`, `ls -la`, `cat main.st`
- **MEDIUM:** `pip install pytest`, `npm run build`
- **HIGH:** `rm -rf`, `git reset --hard`, `DROP TABLE`

---

## 8. Unified Interaction Model (v2.6)

**Philosophy:** Replace mode-based routing with a single adaptive flow.

### Single Flow (No Mode Selector)

**User Experience:**
1. User enters request in **Pulse Chat** tab
2. **Master Agent analyzes** request
3. Master decides which tools to use based on request type
4. For **code changes:**
   - Generates or delegates to `implement_feature`
   - Presents patch preview modal
   - User approves → patch applied → files open in tabs
5. For **terminal commands:**
   - Generates CommandPlan
   - Presents terminal approval modal
   - User approves → command executes → output in terminal
6. For **questions:**
   - Uses `search_workspace` (RAG) or direct LLM
   - Displays answer in Pulse Chat with file references
7. Master summarizes actions and results

**No Mode Selector:** Behavior adapts to request (no manual mode selection).

**Always Human-in-the-Loop:**
- ALL code changes require patch approval
- ALL terminal commands require approval with risk labels

---

### Example User Flows

#### Flow 1: Code Change Request
**Request:** *"Add a 5-second timer to the conveyor start sequence"*

1. Master analyzes → determines code change needed
2. Master calls `implement_feature` (CrewAI subsystem)
3. CrewAI (Planner → Coder → Reviewer) generates PatchPlan
4. **Patch preview modal** appears:
   - Shows unified diff of changes
   - Rationale: "Add timer logic to conveyor start sequence as requested"
5. User reviews diff, clicks **Approve**
6. Patch applied atomically to `conveyor.st`
7. File `conveyor.st` opens in new editor tab
8. Master summarizes: "Added 5-second timer to conveyor start sequence in conveyor.st"

#### Flow 2: Terminal Command Request
**Request:** *"Install pytest for testing"*

1. Master analyzes → determines terminal command needed
2. Master generates CommandPlan:
   - Command: `pip install pytest`
   - Rationale: "Install pytest testing framework"
   - Risk: **MEDIUM**
3. **Terminal approval modal** appears (yellow warning color)
4. User reviews command and rationale, clicks **Approve**
5. Command executes in integrated terminal
6. Terminal output displayed in terminal panel
7. Master summarizes: "Installed pytest successfully"

#### Flow 3: Question Request
**Request:** *"What does the StartMotor function do?"*

1. Master analyzes → determines Q&A request
2. Master calls `search_workspace` (RAG query over Chroma)
3. Chroma returns relevant file excerpts
4. Master displays answer in Pulse Chat:
   - "The StartMotor function is defined in motor_ctrl.st:42..."
   - Clickable file reference: `motor_ctrl.st:42`
5. User clicks reference → file opens in tab at line 42

---

## 9. Architecture & Stack (v2.6)

### 9.1 Technical Stack
* **Language:** Python 3.x
* **UI:** Flet (Python-driven, modern desktop UI with VS Code-style layout + menu bar)
* **Editor:** Flet-based tabbed code editor component
  * Tab 0: Permanent "Pulse Chat" tab
  * Tabs 1+: Dynamic file tabs with close buttons
  * Monospaced font, line numbers, syntax highlighting
* **Terminal:** Flet-based integrated terminal panel
* **Menu Bar:** VS Code-style (File, View, Settings, Help)
* **Orchestration:**
  * **LangGraph:** Unified Master Loop (hub-and-spoke, single active run)
  * **CrewAI/Autogen:** Specialized subsystems wrapped as Tier 3 tools
  * **Pattern:** Master Agent orchestrates Tool Belt; subsystems offloaded via `asyncio.to_thread`
* **LLM Integration:**
  * Primary: OpenAI GPT-4o (for Master Agent and subsystems)
  * Pluggable LLM client (future support for Anthropic, local models)
  * Prompts centralized in `src/core/prompts.py`
* **Persistence:**
  * SQLite for sessions and state (`.pulse/history.sqlite` in workspace)
  * Chroma (local vector store) for RAG (`.pulse/chroma_db/` in workspace)
  * platformdirs for global settings (API keys, preferences)
* **Packaging:** PyInstaller or flet pack for Windows .exe
* **CI/CD:** GitHub Actions (lint/test on every push, build .exe on release tags)

### 9.2 High-Level Flow (v2.6)
1. **User interaction in "Pulse Chat" tab (Tab 0):**
   * User enters natural language request in Pulse Chat tab
   * User clicks "Run" or presses Enter
   * (No mode selector - Master Agent decides behavior)

2. **UI → Master Agent:**
   * UI invokes LangGraph Master Loop with user request
   * Global run lock enforced (only one active run)

3. **Master Agent orchestration:**
   * Master analyzes request
   * Decides which tools to call from Tool Belt (3 tiers)
   * For Tier 3 tools: offloads to thread via `await asyncio.to_thread(...)`
   * CrewAI/AutoGen transcripts discarded; only structured outputs return

4. **Approval Gates (Interrupts):**
   * For patches: Graph pauses → Patch preview modal → User approves/rejects → Graph resumes
   * For terminal commands: Graph pauses → Terminal approval modal → User approves/rejects → Graph resumes

5. **Master Agent → UI (State updates):**
   * Master returns updated `PulseState` (patches applied, commands executed, answers provided)

6. **UI rendering updates:**
   * **Pulse Chat tab:** Display Master's summary and results
   * **File tree:** Refresh with new/modified files
   * **File tabs:** Open modified files in new tabs
   * **Terminal:** Show command output
   * **Vibe status:** Display contextual status word (Wondering, Preparing, Rejoicing)

7. **User review and iteration:**
   * User reviews changes in file tabs
   * User can manually edit code in tabs
   * User can ask follow-up questions in Pulse Chat tab
   * User can cancel active run via UI button

---

## 10. Operational Excellence – Deployment & CI/CD

### 10.1 Objectives
Ensure every change is:
* Tested before being packaged.
* Packaged automatically into a Windows .exe.
* Published in a repeatable, observable way.

### 10.2 CI/CD Pipeline (GitHub Actions)
**Triggers:**
* **On every push / PR to main:** Run linting and unit tests.
* **On tag (e.g., v0.1.0):** Run tests, Build .exe for Windows, Attach binary to a GitHub Release.

**Jobs:**
1. **lint_and_test (Ubuntu)**
    * Install Python, dependencies.
    * Run:
        * Static analysis (e.g., ruff).
        * Unit tests (pytest) for: Engine logic, Filesystem tools, Persistence & logging.
2. **build_windows (Windows)**
    * Install Python, dependencies.
    * Build desktop executable: `pyinstaller` or `flet pack` on `main.py`.
    * Upload artifact.
3. **release (Ubuntu)**
    * For tagged versions: Create GitHub Release.
    * Attach the Windows artifact.

**Value for Stakeholder:**
* Clear “green pipeline” as a visible signal of quality.
* Reproducible builds—no manual packaging.
* Easy distribution: link to GitHub Release with a downloadable installer.

---

## 11. Non-Functional Requirements

### 11.1 Privacy & Security
* All project files stay on user’s local machine by default.
* No automatic upload of code, logs, or PLC projects to external services.
* **LLM calls:**
    * Configurable using API keys.
    * Clear documentation of what is sent to LLM providers (e.g., truncated context).

### 11.2 Performance & Latency
* **App startup:** < 5 seconds on a typical engineering laptop.
* **Core interactions:**
    * Simple Q&A responses: target < 5 seconds (excluding LLM latency).
    * Full agent run (Planner → Coder → Tester) for small projects: < 20–30 seconds.
* The UI must remain responsive during long agent runs (non-blocking).

### 11.3 Reliability
* No destructive file operations outside the configured workspace.
* Atomic writes when modifying files (write to temp + rename).
* **Recoverable state:**
    * Most recent session can be reloaded on app restart.
    * Graceful handling of: LLM failures (timeouts, quota), Corrupted or missing files.

### 11.4 Usability
* Clear visual distinction between: Plan steps, File changes, Test results.
* Persistent mode selector (Agent / Plan / Ask).
* Basic error messaging (“LLM request failed, please retry.”).
* Embedded editor that makes Pulse feel like a familiar IDE: Readable font, line numbers, clear active file highlighting.

### 11.5 Extensibility
* Agent graph and tools are modular.
* New agents (e.g., “Refactor Agent”) can be added without UI redesign.
* Additional PLC dialects can be supported behind a configuration flag in future versions.

---

## 12. Success Metrics (v2.6)

### 12.1 Delivery & Execution
* **CI pipeline health:** ≥ 90% of pushes to main have all checks green
* **Automated test coverage:** Unit tests covering:
  * Master Agent orchestration (LangGraph Unified Master Loop)
  * Tool Belt (3 tiers: Atomic, Permissioned, Agentic)
  * File operations (project-root enforcement, denylist, atomic writes)
  * Approval gates (patch and terminal approval flows)
  * Shutdown handler (graceful cleanup, zombie process killer)
  * Persistence & logging (SQLite, Chroma, platformdirs)
  * UI components (tab management, file tree, terminal, modals)

### 12.2 Product Experience (Qualitative)
A reviewer (e.g., hiring manager) can:

1. **Install and launch:**
   * Download and run Pulse .exe from GitHub Release
   * App launches in < 5 seconds
   * No console warnings about missing dependencies

2. **Experience VS Code-style IDE:**
   * Open workspace folder → `.pulse/` directory auto-created
   * Navigate file tree in left sidebar
   * Click file → opens in new tab with close button (×)
   * See permanent "Pulse Chat" tab (Tab 0)
   * Access menu bar (File, View, Settings, Help)
   * Open Settings modal → paste API key → select model → save
   * Verify settings saved to platformdirs (not workspace)
   * Resize panels by dragging splitters (sidebar, terminal)
   * View/edit code with syntax highlighting and line numbers
   * Use integrated terminal at bottom

3. **Complete end-to-end unified flows:**
   * **Code Change Flow:**
     * Enter request: "Add a timer to the conveyor logic"
     * Master Agent calls `implement_feature` (CrewAI)
     * **Patch preview modal** appears with diff and rationale
     * Review diff, click **Approve**
     * File automatically opens in tab with changes applied
     * Master summarizes action in Pulse Chat
   * **Terminal Command Flow:**
     * Enter request: "Install pytest"
     * Master Agent generates CommandPlan
     * **Terminal approval modal** appears with command, rationale, risk label (MEDIUM)
     * Click **Approve**
     * Command executes in terminal, output displayed
   * **Q&A Flow:**
     * Ask: "What does StartMotor do?"
     * Master uses `search_workspace` (RAG)
     * Answer appears in Pulse Chat with clickable file reference
     * Click reference → file opens in tab

4. **Safety verification:**
   * Attempt code change → Verify patch preview required (no auto-apply)
   * Attempt terminal command → Verify approval required
   * Verify files outside project root are rejected
   * Verify `.env` file edits are denied (denylist)

5. **System stability:**
   * Close app during active run → Verify no zombie processes
   * Reopen workspace → Verify state persists (tabs, history)
   * View vibe status during agent work (e.g., "Preparing...")

**Perception benchmarks:**
* "This is a production-quality IDE I would actually use daily"
* "The approval gates give me confidence in what the AI is doing"
* "The patch preview is clear and professional - better than some commercial tools"
* "Settings management via the UI is intuitive - I never had to find config files"

### 12.3 Operational Excellence
* **Build success rate:** ≥ 95% of tagged releases result in a successful .exe build and attached artifact
* **Mean Time to Fix (MTTF):** Broken main-branch builds corrected within one working session
* **Zero zombie processes:** App shutdown leaves no orphaned CrewAI/AutoGen processes

---

## 13. Risks & Assumptions (v2.6)

**Assumptions**
* OpenAI GPT-4o API is available and stable
* User has valid OpenAI API key (configured via Settings UI)
* User has permission to run local executables and modify files in their workspace
* Target PLC use-case can be represented in a simplified Structured Text-like dialect
* Flet framework supports required UI features (tabs, terminal, splitters, modals)
* platformdirs works reliably across Windows (primary), Linux, macOS (future)
* `asyncio.to_thread` provides sufficient UI responsiveness for blocking CrewAI/AutoGen work

**Risks (v2.6)**
* **Approval gate UX friction:**
  * Users may find constant approval modals annoying for trivial changes
  * *Mitigation:* Clear, informative modals with rationale; future: user-configurable trust levels

* **LLM variability:**
  * GPT-4o may produce inconsistent code quality or incorrect patches
  * *Mitigation:* Patch preview (user can reject); CrewAI Reviewer agent; centralized prompts for tuning

* **Context containment complexity:**
  * Ensuring CrewAI/AutoGen transcripts never leak into Master context requires discipline
  * *Mitigation:* Strict typing (PatchPlan, DiagnosisResult Pydantic models); code review checklist

* **Subsystem responsiveness:**
  * `asyncio.to_thread` may not be sufficient for very long CrewAI/AutoGen runs
  * *Mitigation:* Vibe status words for progress feedback; future: ProcessPoolExecutor upgrade

* **Shutdown race conditions:**
  * Zombie process killer may fail if processes spawn rapidly or fork
  * *Mitigation:* Track all subprocess PIDs; test on clean Windows VM; add timeout to kills

* **Packaging friction:**
  * PyInstaller/flet pack may struggle with LangGraph, CrewAI, Chroma dependencies
  * *Mitigation:* Test packaging early in CI; use flet pack (Flet-optimized); bundle all dependencies

* **User trust:**
  * Engineers may be cautious about approving AI-generated patches without full understanding
  * *Mitigation:* Clear diffs with rationale; risk labels on terminal commands; atomic writes (undo-safe)

* **PLC v1 scope limits:**
  * Text generation only (no compiler integration) may feel incomplete to advanced users
  * *Mitigation:* Document plugin seam for future vendor integrations; focus on code quality