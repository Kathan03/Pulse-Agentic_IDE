# Pulse IDE v2.6 — Updated Implementation Plan (Unified Master Loop / Hub-and-Spoke)

## Non-Negotiables (Locked)
- **Single active agent run only** (no concurrency).
- **Human confirmation required** for:
  - **Applying patches** (`apply_patch` → preview → approve → apply)
  - **Running terminal commands** (`run_terminal_cmd` → preview → approve → execute)
- **Local-first** workspace state; users bring their own API keys.
- **Context containment**: CrewAI/AutoGen transcripts never enter Master context (only structured summaries/artifacts).
- **Reuse-first**: read existing codebase first; delete only after proving “unused” and not aligned with the new PRD/architecture.

---

## Cross-Cutting Enhancements (Apply Throughout All Phases)
### A) Professional Storage, Easy Access (platformdirs)
- Use **platformdirs** to store Pulse user settings in the OS standard location (not `~/.pulse/`).
- The user never needs to locate the file; **Settings UI reads/writes automatically**.
- Storage target (examples):
  - Windows: `C:\Users\<Name>\AppData\Roaming\<Pulse>\settings.json`
  - Linux: `~/.config/<pulse>/settings.json`
  - macOS: `~/Library/Application Support/<Pulse>/settings.json`
- Workspace-local storage remains in `project_root/.pulse/` (hidden folder inside project).

### B) Sub-Agent Threading Model (No UI Freeze)
- CrewAI and AutoGen calls are treated as **blocking**.
- Any expensive/CPU-bound agentic work must be offloaded using:
  - `await asyncio.to_thread(...)` (default)
  - OR a `ProcessPoolExecutor` if CPU-heavy workloads justify it (optional upgrade)
- This is mandatory to keep:
  - “Vibe” status updates flowing
  - UI responsive during long “thinking” steps

### C) Prompt Management (Central Registry)
- Externalize prompts into a centralized registry:
  - `src/core/prompts.yaml` (recommended) OR `src/core/prompts.py` (dataclass-based)
- Must include:
  - `MASTER_SYSTEM_PROMPT`
  - `CREW_CODER_PROMPT`
  - `AUTOGEN_AUDITOR_PROMPT`
  - (optional) PLC/ST variants and “cheap model” variants
- Agent logic must reference prompt keys, not hardcoded strings.

### D) Zombie Process Killer (Shutdown Handler)
- Implement shutdown handling to prevent orphaned processes/threads.
- On app close (`page.on_close` / app exit hook):
  - cancel active agent run
  - shutdown thread/process pools
  - kill child PIDs spawned by terminal commands
  - ensure terminal subprocesses are terminated
- Add “Run cancellation” semantics in the agent runtime.

### E) VS Code-Style Menu Bar (Native-feeling UX)
- Add a top navigation bar using Flet **MenuBar/AppBar** (preferred for familiarity).
- Menu structure:
  - **File**: Open Workspace, Save All, Exit
  - **View**: Toggle Terminal, Toggle Sidebar
  - **Settings**: API Keys, Models, Agent Toggles (opens Settings modal/page)
  - **Help**: About Pulse, Documentation

---

## Phase 1 — Documentation + Product Alignment (Do This First)
### Goal
Give Claude-code an unambiguous target: updated PRD + architecture + operational constraints.

### Actions
1) Update `claude.md` to reflect:
   - Unified Master Loop (LangGraph) architecture
   - Tool Belt tiers (Atomic / Permissioned / Agentic)
   - Single-run lock and run cancellation expectations
   - Patch + terminal approvals (mandatory)
   - Context/token controls (summaries only from CrewAI/AutoGen)
   - Workspace initialization rules (`project_root/.pulse/` + SQLite + Chroma)
   - Global settings in OS-standard path (**platformdirs**)
   - Prompt registry requirement (`prompts.yaml` / `prompts.py`)
   - Thread/process offloading requirement for CrewAI/AutoGen
   - Shutdown handler requirement (zombie killer)
   - Strict “no random files” and “delete only with proof” policies

2) Update `Pulse_Agentic_AI_IDE_PRD.MD` to reflect:
   - Pulse as local-first Agentic IDE for PLC + general coding
   - PLC v1 scope: **text generation only** (.st/.scl/.mat); no vendor compiler integration (plugin seam reserved)
   - Settings UX flow:
     - user pastes key, selects model, saves
     - Pulse stores securely in OS standard path; user never navigates it
   - UX:
     - vibe loader words
     - streaming lifecycle events
     - patch preview + terminal approval modals
     - VS Code-style menu bar
   - Safety:
     - project-root file boundary enforcement
     - denylist patterns unless explicitly allowed
     - terminal approvals + risk labels
     - shutdown kills background work
   - Distribution:
     - GitHub releases + CI builds via GitHub Actions

### Acceptance Criteria
- Docs fully specify architecture + constraints so Claude-code can classify/reuse/delete correctly.

---

## Phase 2 — Combined Discovery + Clean Slate Refactor (Merged Old Phase -1 and 0)
### Goal
Read the repo, map it to the new architecture, reuse what fits, and safely delete/retire what doesn’t.

### Actions (Strict Order)
1) **Read-only inventory & dependency mapping**
   - Walk key directories and entrypoints.
   - Identify:
     - UI boot sequence
     - legacy Router/Planner/Coder flow
     - existing state/memory modules
     - existing settings/storage if any
     - experimental scripts and duplicates

2) **Architecture fit classification** (based on updated PRD + claude.md)
   - For each file/module classify:
     - ✅ KEEP
     - ♻️ REFACTOR/REHOME
     - 🗑️ DELETE
   - For deletions:
     - provide proof via grep/import references
     - categorize: “safe now” vs “safe after refactor”
   - Confirm unauthorized files are not referenced:
     - `main_simple.py`, `smart_agent_node.py`, `conversation_node.py`

3) **Execute deletions + cleanup**
   - Delete only “safe now” items.
   - Remove dead imports; update references.
   - Ensure a single canonical entrypoint remains.

4) **Storage foundations**
   - Workspace-local: on workspace open, ensure:
     - `project_root/.pulse/history.sqlite` (schema + migrations)
     - `project_root/.pulse/chroma_db/`
     - optional bounded logs folder
   - Global user settings:
     - implement settings storage using **platformdirs**
     - secrets stored in OS keychain (fallback encrypted local)

5) **Prompt registry creation**
   - Add `src/core/prompts.yaml` or `src/core/prompts.py`
   - Populate initial prompt set (Master, Crew, AutoGen)

6) **Guardrails**
   - project-root boundary enforcement
   - denylist patterns for sensitive files
   - tool output size caps and log bounds

### Acceptance Criteria
- Repo is clean and aligned with new architecture.
- Workspace open initializes `.pulse/` reliably.
- Settings persist in OS standard path.
- Prompt registry exists and is used going forward.

---

## Phase 3 — Core Runtime: Master Agent (LangGraph) + State + Interrupts
### Goal
Build the “Hub”: one LangGraph master loop that thinks, chooses tools, pauses for approvals, resumes, streams status.

### Actions
1) Implement `src/agents/master_graph.py` with nodes:
   - `master_agent_node`
   - `tool_execution_node`
   - `interrupt_wait_node` (await user approval payload)
2) Define `MasterState`:
   - bounded `messages` + `rolling_summary`
   - `current_status` (vibe)
   - `pending_interrupt` (patch approval / terminal approval)
   - `tool_result` (structured)
   - `settings_snapshot` (provider/model/toggles/budget)
   - `workspace_context` (project root, stack detection)
3) Memory policy:
   - last N turns verbatim
   - rolling summary for older turns
   - full transcripts in SQLite (not in LLM context)
4) Status emitter:
   - vibe words, rate-limited, state-aware
5) Cancellation hooks:
   - master run cancellable from UI
   - cancellation propagates to tools

### Acceptance Criteria
- Master can:
  - answer directly
  - call tool
  - pause for approvals and resume deterministically
  - cancel cleanly

---

## Phase 4 — Tool Belt Tier 1: File Ops + Patch Workflow + Local RAG
### Goal
Safe edits and local semantic search with freshness guarantees.

### Tools
- `manage_file_ops` (project-root restricted)
- `apply_patch` (unified diff) **requires approval**
- `search_workspace` (local RAG)

### Requirements
- `apply_patch` returns PatchPlan → **interrupt_wait_node** → UI approval → apply/deny.
- RAG:
  - sentence-transformers (CPU)
  - Chroma persistent in `.pulse/chroma_db`
  - stale index prevention via incremental embedding updates (tracked in SQLite)

### Acceptance Criteria
- Patch preview/approve/apply works end-to-end.
- RAG updates immediately after patch apply.

---

## Phase 5 — Tool Belt Tier 2: Permissioned Terminal + Dependency Manager
### Goal
Safe command execution and environment-aware installs.

### Tools
- `run_terminal_cmd` **requires approval**
- `dependency_manager`

### Requirements
- `run_terminal_cmd` produces CommandPlan (command + rationale + risk label) → approval → execute.
- Track PIDs for all subprocesses so shutdown handler can kill them.
- `dependency_manager`:
  - detects venv/node/java tooling
  - fails fast if unsafe (no venv)
  - proposes commands routed to `run_terminal_cmd`

### Acceptance Criteria
- Commands never execute without approval.
- Subprocesses are tracked and killable.

---

## Phase 6 — Tier 3: CrewAI Builder + AutoGen Auditor + Budget Controls (Thread/Process Offload Mandatory)
### Goal
Robust autonomous handling with optional advanced agents and cost governance—without freezing UI.

### Settings Controls (must exist before Tier 3)
- Provider + API key (secure)
- Master model + cheap model
- Toggles:
  - Enable CrewAI Builder
  - Enable AutoGen Auditor
- Budget thresholds/warnings and fallback behavior

### Tools
1) `implement_feature` (CrewAI wrapper)
- Planner → Coder → Reviewer
- Returns:
  - PatchPlan(s)
  - concise summary
  - verification steps
- **Offload requirement** (mandatory):
  - `await asyncio.to_thread(crew.kickoff, inputs=inputs)`
  - (optional upgrade) ProcessPool for CPU-heavy usage
- No transcripts returned to master.

2) `diagnose_project` (Deterministic Gate + AutoGen Auditor)
- Stage A: deterministic checks and structured parsing.
- Stage B: AutoGen debate (optional, bounded) roles:
  - Auditor / Hacker / Defender / Moderator
- Strict JSON output: risk_level, findings, prioritized fixes, verification steps
- **Offload requirement** (mandatory):
  - AutoGen group chat runs via `asyncio.to_thread(...)` or executor.

### Acceptance Criteria
- With toggles OFF: cheap mode works.
- With toggles ON: robust mode works without context explosion.
- UI remains responsive during CrewAI/AutoGen runs.

---

## Phase 7 — UI Heartbeat: Async Streaming + Approval Modals + VS Code Menu Bar + Settings UX
### Goal
No UI freezing and native-feeling navigation.

### Actions
1) **Single-run lock**
   - one run at a time
   - queue or prompt stop/queue if user inputs during run
2) **Async event bus**
   - agent/tool events stream to UI via Queue/EventEmitter
3) **Approval modals**
   - Patch approval (diff preview + approve/deny)
   - Terminal approval (command preview + approve/deny)
4) **Settings UX**
   - accessible from Menu → Settings
   - reads/writes from OS standard settings path (platformdirs)
   - key stored securely
5) **VS Code-style menu bar**
   - File: Open Workspace, Save All, Exit
   - View: Toggle Terminal, Toggle Sidebar
   - Settings: API Keys, Models, Agent Toggles
   - Help: About Pulse, Documentation
6) **Vibe status UI**
   - subtle fade label near input
   - dictionary categories:
     - Thinking/Processing: Wondering, Stewing, Cogitating, Hoping, Exploring, Preparing
     - Context: Mustering, Coalescing, Ideating
     - Action/Completion: Completing, Messaging, Uploading, Connecting, Affirming, Rejoicing, Celebrating
7) **Shutdown handler integration**
   - on app close: cancel active run, shutdown pools, kill subprocesses

### Acceptance Criteria
- UI remains responsive during long tasks.
- Approvals are required and deterministic.
- Settings are discoverable via menu bar and saved to OS standard path.
- Closing app kills background work.

---

## Phase 8 — Packaging, Releases, and CI/CD (GitHub Actions)
### Goal
Users can download Pulse from GitHub releases; builds are reproducible and automated.

### Actions
1) Choose packaging approach (Python desktop):
   - build OS-specific binaries (e.g., PyInstaller) and publish artifacts
2) GitHub Actions workflows:
   - PR workflow: lint + basic tests
   - Release workflow (tags):
     - build Windows/macOS/Linux artifacts
     - upload to GitHub Releases
3) Add versioning + changelog strategy
4) Smoke tests:
   - launch app
   - open workspace
   - initialize `.pulse/` successfully

### Acceptance Criteria
- Tagging a release produces downloadable artifacts for major OSes.
- Users can run without setting up a dev environment.

---

## Phase 9 — Hardening & Polishing (Post-v1)
### Goal
Production stability across diverse machines/projects.

### Actions
- log rotation + size caps
- bounded retries for self-correction
- improved RAG indexing performance and status UX
- safer defaults for file boundaries and command risk classification
- stronger cancellation semantics for long tool runs

### Acceptance Criteria
- Stable multi-session usage without slowdown or drift.
- No runaway loops, no orphaned processes, no unbounded context.

---
## Summary: Key Production-Grade Guardrails
- One run at a time (global lock) + cancellation.
- Patch and terminal actions always require human approval.
- CrewAI/AutoGen executed via thread/process offload to keep UI alive.
- Prompts centralized in registry for easy iteration.
- Global settings stored via platformdirs (clean OS paths, clean UX).
- Workspace state isolated per project in `.pulse/`.
- Shutdown handler kills zombie processes and pools.
