# Pulse – Agentic AI IDE for PLC Coding

**Document Type:** Product Requirements Document (PRD)
**MVP Timeline:** 2.5 days (~50–60 hours)
**Platform:** Windows Desktop Application

---

## 1. Problem Statement

Programming PLCs (Programmable Logic Controllers) today is:

* **Manual:** Engineers hand-write ladder logic or structured text in vendor-specific IDEs.
* **Error-prone:** Small mistakes in timing, interlocks, or I/O mapping can lead to production downtime or safety incidents.
* **Slow to iterate:** Each change requires mentally simulating logic, redeploying, and often involving on-site testing.
* **Tooling-fragmented:** IDEs do not provide modern AI assistance (planning, refactoring, context-aware Q&A).

Automation engineers are under pressure to ship changes quickly while maintaining reliability. They lack an “AI pair programmer” tailored to PLC workflows.

---

## 2. Proposed Solution – Pulse (“Cursor for PLC”)

Pulse is an Agentic AI IDE for PLC-style code, delivered as a local Windows desktop app. It acts as a PLC-focused “Cursor/Copilot,” helping engineers:

* Turn natural language requirements into structured plans.
* Generate and edit PLC-style code safely in a workspace on their machine.
* Validate logic against requirements and basic checks.
* Capture feedback for continuous improvement.

**Key design principles:**
* **Local-first:** Project files and logs stay on the user’s machine by default.
* **Operational excellence:** Automated CI/CD pipeline builds a signed .exe from GitHub pushes.
* **Agentic workflow:** Planner, Coder, Tester, QA, and Customizer agents collaborate through a structured orchestration layer.

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

## 4. Scope – Desktop App MVP

### In Scope (MVP)
**Windows desktop application built with:**
* **UI:** Python + Flet.
* **Orchestration:** LangGraph for multi-agent orchestration.
* **Storage:** Local file system access to a user-selected workspace folder.
* **Persistence:** SQLite for session/state persistence.
* **RAG:** Local vector store (e.g., Chroma) for context-aware Q&A over project files.

**Agentic core:**
* Planner, Coder, Tester, QA, Customizer agents.

**Interaction modes:**
* Agent Mode (fully autonomous loop).
* Plan Mode (human-in-the-loop).
* Ask Mode (chat/Q&A only).

**Embedded code editor:**
* In-app text editor for viewing and editing PLC-style code (files in the workspace), with basic affordances (monospaced font, line numbers, read/write integration with the Coder Agent).

**CI/CD (GitHub Actions workflow):**
* Run tests and linting.
* Build Windows .exe artifact via PyInstaller or flet pack.
* Attach binary to GitHub Release.

### Out of Scope (MVP)
* Direct connection to live PLC hardware.
* Support for multiple PLC vendor IDEs or proprietary project formats.
* Rich project management (multi-project dashboards, collaboration).
* Cloud backend, user accounts, or centralized logging.

---

## 5. Solution Overview

At a high level:

1.  The user opens Pulse and selects a workspace folder containing PLC-style code (or starting empty).
2.  They view and edit code directly in an embedded text editor, just like a lightweight PLC IDE.
3.  They provide a natural-language task, e.g., *“Create a routine that toggles Motor_1 every 10 seconds with a fault latch.”*
4.  Pulse orchestrates a set of AI agents (Planner → Coder → Tester → QA → Customizer) to:
    * Plan the work.
    * Generate/edit PLC-style code and update files in the workspace.
    * Validate and summarize changes.
    * Ask for and record user feedback.
5.  All code and logs are stored locally in the workspace and in Pulse’s local data directory.

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

## 7. Key Features – Agents & IDE

### 7.0 In-IDE Code Editing & Workspace View
*Purpose: Make Pulse a usable day-to-day IDE, not just an AI command console.*

* **Embedded Code Editor:**
    * Central panel shows the currently selected file from the workspace.
    * Supports viewing and editing PLC-style (Structured Text-like) code.
    * Basic editor affordances (monospaced font, line numbers, simple keyboard shortcuts).
    * Changes are saved to disk and become part of the context for all agents.
* **File Tree / Workspace Panel:**
    * Left-hand panel shows the workspace folder structure.
    * Selecting a file opens it in the editor.
    * New files created by the Coder Agent appear automatically in the tree.
* **Agent-Aware Editing:**
    * The Coder Agent reads files via the same abstraction the editor uses.
    * Writes changes that the editor immediately reflects.
    * Manual user edits are treated as first-class: Subsequent agent runs take the updated file contents as ground truth.
* **Safety:**
    * All edits (human or agent) are constrained to the configured workspace.
    * Pulse uses atomic writes when saving from agents to avoid partial-file corruption.

### 7.1 Planner Agent (High-Context Task Planner)
*Purpose: Turn a user’s request into a concrete, step-by-step implementation plan.*

* **Inputs:** User request (natural language), Snapshot of relevant project files.
* **Outputs:** Ordered list of Plan Steps (e.g., Analyze code, Add routine, Wire logic, Document).
* **Responsibilities:**
    * Make assumptions explicit (e.g., timer resolution, input/output names).
    * Surface potential risks (“This change may affect cycle time.”).
* **UX:** Plan steps are displayed in the UI sidebar. In Plan Mode, steps require user approval.

### 7.2 Coder Agent (File I/O + Code Generation)
*Purpose: Translate plan steps into PLC-style code and actual file changes.*

* **Inputs:** Approved Plan Steps, Current workspace state.
* **Outputs:** Concrete file operations (Create/Modify files).
* **Responsibilities:**
    * Use a single PLC-like dialect (simplified Structured Text) for MVP.
    * Ensure code is idempotent (re-runnable without corruption).
    * Adhere to a simple coding style.
* **Safety:** Atomic writes constrained to the workspace.
* **Integration:** Files created/modified are immediately visible in the embedded editor.

### 7.3 Tester Agent (Validation)
*Purpose: Validate generated/modified code against the stated requirements.*

* **Inputs:** User requirement, Updated files.
* **Outputs:** Test summary (Basic static checks, Suggested test cases).
* **MVP Behavior:** Focus on static analysis and requirement coverage mapping. Optionally generate pseudo-tests.
* **UX:** Results displayed in a Test panel (e.g., “3 checks: 2 pass, 1 warning.”).

### 7.4 QA Agent (Context-Aware Q&A via RAG)
*Purpose: Answer user questions about the codebase and changes.*

* **Inputs:** User question, Vector search over project files.
* **Outputs:** Explanations referencing specific files/lines.
* **Responsibilities:** Summarize logic in human-friendly language; highlight impact of recent changes.

### 7.5 Customizer Agent (Feedback Loop & Telemetry)
*Purpose: Capture structured feedback and logs for future model improvement.*

* **Inputs:** Session metadata, User rating (1–5 stars), Optional free-text feedback.
* **Outputs:** Append-only JSONL logs stored locally.

**Example Log Structure:**
```json
{
  "session_id": "...",
  "user_request": "...",
  "plan": [...],
  "files_touched": ["main.st"],
  "tests_summary": {...},
  "rating": 4,
  "feedback": "Code worked but needed more comments."
}

* **UX:** Lightweight feedback prompt after each completed run.
* **Value:** Demonstrates a built-in fine-tuning data loop without a cloud backend.

---

## 8. Interaction Modes

### 8.1 Agent Mode (Fully Autonomous)
**Flow:** Planner → Coder → Tester → QA → Customizer

* **User experience:**
    * User enters a requirement and clicks “Run”.
    * Pulse:
        * Generates a plan (shown for transparency).
        * Edits files automatically.
        * Runs validation.
        * Summarizes what changed.
        * Prompts for feedback.
    * Updated files open or refresh in the embedded editor for inspection.
* **Use case:** Quick iteration when the user trusts the system.

### 8.2 Plan Mode (Human-in-the-Loop)
**Flow:** Planner → (User Approves Plan) → Coder → Tester → QA → Customizer

* **User experience:**
    * User enters a requirement and selects Plan Mode.
    * Planner presents a step-by-step plan.
    * User can:
        * Approve the entire plan.
        * Adjust descriptions (MVP: text edit).
    * Only then does Coder modify files.
* **Use case:** Higher-stakes changes requiring explicit review.

### 8.3 Ask Mode (Q&A Only)
**Flow:** QA → Customizer

* **User experience:**
    * User asks questions about existing code or behavior.
    * No file changes are performed.
* **Use case:** Code comprehension, impact analysis, debugging support.

---

## 9. Architecture & Stack

### 9.1 Technical Stack
* **Language:** Python 3.x
* **UI:** Flet (Python-driven, modern desktop UI)
* **Editor:** Flet-based embedded code editor component (single-file editing with basic features; no full language server in MVP).
* **Orchestration:** LangGraph (multi-agent graph and state management)
* **LLM Integration:** Pluggable LLM client (e.g., OpenAI/Anthropic); future support for local models.
* **Persistence:**
    * SQLite for sessions and state.
    * Chroma (local vector store) for RAG over project content.
    * JSONL files for feedback logs.
* **Packaging:** PyInstaller or flet pack for Windows .exe.
* **CI/CD:** GitHub Actions (Ubuntu for tests, Windows for build).

### 9.2 High-Level Flow
1. UI receives user input + selected mode.
2. UI calls `PulseEngine.run(mode, request)` (engine layer).
3. Engine uses LangGraph to traverse the appropriate agent graph.
4. Agents call tools (filesystem, RAG, logging) as needed.
5. Engine returns updated state (plan, changes, tests, answers) to UI.
6. UI renders updates:
    * Plan view.
    * File tree.
    * Code editor with updated content.
    * Test panel and feedback prompt.

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

## 12. Success Metrics

### 12.1 Delivery & Execution
* **MVP delivery time:** Functional desktop app and CI/CD pipeline within 2.5 days.
* **CI pipeline health:** ≥ 90% of pushes to main have all checks green.
* **Automated test coverage (MVP):** Unit tests covering:
    * Core agent orchestration.
    * File system operations.
    * Persistence & logging.

### 12.2 Product Experience (Qualitative for MVP)
A reviewer (e.g., hiring manager) can:
1. Install Pulse from a GitHub Release .exe.
2. Open a workspace folder and view/edit code in the embedded editor.
3. Complete at least one end-to-end flow in each mode:
    * **Agent Mode:** requirement → code change → test summary → feedback.
    * **Plan Mode:** requirement → plan review → approved code change.
    * **Ask Mode:** ask a question → receive explanation referencing code opened in the editor.
* **Perception:**
    * “This looks and feels like a real IDE, not a demo script.”
    * “The deployment and build process is clearly thought-through.”

### 12.3 Operational Excellence
* **Build success rate:** ≥ 95% of tagged releases result in a successful .exe build and attached artifact.
* **Mean Time to Fix (MTTF) for broken builds:** Broken main-branch builds are corrected within one working session.

---

## 13. Risks & Assumptions

**Assumptions**
* A cloud LLM (OpenAI/Anthropic, etc.) is available for MVP; local models are a future enhancement.
* User has permission to run local executables and install dependencies.
* Target PLC use-case can be represented in a simplified Structured Text-like dialect.

**Risks (MVP)**
* **LLM variability:** Generated code quality may be inconsistent.
    * *Mitigation:* Keep scope narrow and rely on Tester Agent for basic checks.
* **User trust:** Engineers may be cautious about letting an AI edit code.
    * *Mitigation:* Provide Plan Mode and clear visibility into changes via the embedded editor.
* **Packaging friction:** PyInstaller/flet pack may have edge cases on some Windows setups.
    * *Mitigation:* Test on at least one clean Windows environment before release.