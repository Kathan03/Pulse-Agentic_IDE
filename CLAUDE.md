# Pulse - Agentic AI IDE for PLC Coding

## CORE CONSTRAINTS (Strict Adherence Required)

1. **Platform:** Windows Desktop Application (Local-first).
2. **UI Framework:** Python + Flet (No web frameworks like React/Vue).
3. **Orchestration:** LangGraph (for multi-agent orchestration).
4. **Persistence:** SQLite (State) + Local File System (Workspace).
5. **No Cloud:** All processing and storage are local (except LLM API calls).
6. **Timeline:** 2.5 days (~50-60 hours) to ship MVP.

## PROJECT SCOPE

We are building a desktop app where an Automation Engineer can:
- Open a local folder (Workspace).
- View/Edit .st (Structured Text) files in a Flet-based embedded code editor.
- Input natural language tasks (e.g., "Add a motor toggle routine").
- Watch agents (Planner → Coder → Tester → QA → Customizer) generate/edit code in that folder.
- Ask questions about existing code (Q&A mode).
- Approve plans before execution (Plan mode) or run fully autonomous (Agent mode).

## ARCHITECTURE

### Complete Directory Structure (Source of Truth)

```
Pulse/
│
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore patterns
├── README.md                        # Project documentation
│
├── src/                             # Source code root
│   ├── __init__.py
│   │
│   ├── ui/                          # Flet UI Components (Presentation Layer)
│   │   ├── __init__.py
│   │   ├── app.py                   # Main Flet application controller
│   │   ├── sidebar.py               # Mode selector + workspace file tree
│   │   ├── editor.py                # Embedded code editor component
│   │   ├── log_panel.py             # Agent activity log display
│   │   ├── test_panel.py            # Validation results display
│   │   ├── feedback_prompt.py       # Rating and feedback collection UI
│   │   └── components/              # Reusable UI widgets
│   │       ├── __init__.py
│   │       ├── file_tree.py         # Workspace folder tree widget
│   │       └── plan_view.py         # Plan steps display widget
│   │
│   ├── agents/                      # LangGraph Agent Nodes (Orchestration Layer)
│   │   ├── __init__.py
│   │   ├── graph.py                 # LangGraph orchestration setup
│   │   ├── planner.py               # Planner Agent node
│   │   ├── coder.py                 # Coder Agent node
│   │   ├── tester.py                # Tester Agent node
│   │   ├── qa.py                    # QA Agent node (RAG-powered)
│   │   └── customizer.py            # Customizer Agent node (feedback)
│   │
│   ├── core/                        # Core Business Logic & Infrastructure
│   │   ├── __init__.py
│   │   ├── state.py                 # LangGraph state schema (Pydantic models)
│   │   ├── config.py                # Application configuration
│   │   ├── file_manager.py          # Workspace file I/O with atomic writes
│   │   ├── db.py                    # SQLite session persistence manager
│   │   ├── rag.py                   # Chroma vector store & RAG logic
│   │   └── llm_client.py            # LLM provider abstraction (OpenAI/Anthropic)
│   │
│   └── tools/                       # Utility Functions & Helper Tools
│       ├── __init__.py
│       ├── logger.py                # Structured logging utility
│       ├── validation.py            # Input validation helpers
│       └── atomic_writer.py         # Safe file write operations
│
├── data/                            # Local Persistence (gitignored)
│   ├── pulse.db                     # SQLite database for sessions/state
│   ├── chroma/                      # Chroma vector store directory
│   └── feedback/                    # JSONL feedback logs
│       └── feedback.jsonl           # Append-only feedback log
│
├── workspace/                       # User workspace (example/default)
│   └── .keep                        # Placeholder to preserve directory
│
├── tests/                           # Test Suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_agents/                 # Agent orchestration tests
│   │   ├── __init__.py
│   │   ├── test_planner.py
│   │   ├── test_coder.py
│   │   └── test_tester.py
│   ├── test_core/                   # Core functionality tests
│   │   ├── __init__.py
│   │   ├── test_file_manager.py
│   │   ├── test_db.py
│   │   └── test_rag.py
│   └── test_ui/                     # UI component tests (optional for MVP)
│       └── __init__.py
│
└── .github/                         # CI/CD Pipeline
    └── workflows/
        └── ci-cd.yml                # GitHub Actions workflow
```

### Directory Responsibilities

**Root Level:**
- `main.py` - Flet app entry point; initializes UI and engine
- `requirements.txt` - All Python dependencies
- `.env.example` - Template for API keys (OPENAI_API_KEY, etc.)

**`/src/ui` - Presentation Layer (Flet):**
- Clean separation from business logic
- All Flet components and views
- Responsible for rendering state, not managing it

**`/src/agents` - Orchestration Layer (LangGraph):**
- Each agent is a LangGraph node
- `graph.py` defines the multi-agent workflow (Agent/Plan/Ask modes)
- Agents call tools from `/src/core` and `/src/tools`

**`/src/core` - Business Logic & Infrastructure:**
- `state.py` - Single source of truth for LangGraph state schema
- `file_manager.py` - All workspace file operations (atomic writes)
- `db.py` - SQLite persistence for sessions
- `rag.py` - Chroma vector store + RAG query logic
- `llm_client.py` - Abstraction over LLM providers

**`/src/tools` - Utilities:**
- Shared helper functions
- Logging, validation, atomic writes

**`/data` - Local Persistence (gitignored):**
- `pulse.db` - SQLite database
- `chroma/` - Vector store for RAG
- `feedback/feedback.jsonl` - User feedback logs

**`/workspace` - User's PLC Code:**
- Default workspace folder (user can select any folder)
- Contains `.st` files (Structured Text PLC code)

**`/tests` - Test Suite:**
- Unit tests for agents, core, and tools
- Pytest framework
- Critical for CI/CD pipeline

### Technology Stack
- **Language:** Python 3.x
- **UI:** Flet (Python-driven desktop UI)
- **Editor:** Flet-based embedded code editor component
- **Orchestration:** LangGraph (multi-agent graph and state management)
- **LLM:** Pluggable client (OpenAI/Anthropic/etc.)
- **Persistence:**
  - SQLite for sessions and state
  - Chroma (local vector store) for RAG
  - JSONL files for feedback logs
- **Packaging:** PyInstaller or flet pack for Windows .exe
- **CI/CD:** GitHub Actions

## AGENT DESCRIPTIONS

### 1. Planner Agent (High-Context Task Planner)
**Purpose:** Turn user's request into concrete, step-by-step implementation plan.

**Inputs:**
- User request (natural language)
- Snapshot of relevant project files

**Outputs:**
- Ordered list of Plan Steps (e.g., Analyze code, Add routine, Wire logic, Document)

**Responsibilities:**
- Make assumptions explicit (e.g., timer resolution, input/output names)
- Surface potential risks ("This change may affect cycle time")

**UX:** Plan steps displayed in UI sidebar. In Plan Mode, steps require user approval.

### 2. Coder Agent (File I/O + Code Generation)
**Purpose:** Translate plan steps into PLC-style code and actual file changes.

**Inputs:**
- Approved Plan Steps
- Current workspace state

**Outputs:**
- Concrete file operations (Create/Modify files)

**Responsibilities:**
- Use simplified Structured Text dialect for MVP
- Ensure code is idempotent (re-runnable without corruption)
- Adhere to simple coding style

**Safety:** Atomic writes constrained to workspace.

**Integration:** Files created/modified are immediately visible in embedded editor.

### 3. Tester Agent (Validation)
**Purpose:** Validate generated/modified code against stated requirements.

**Inputs:**
- User requirement
- Updated files

**Outputs:**
- Test summary (Basic static checks, Suggested test cases)

**MVP Behavior:** Focus on static analysis and requirement coverage mapping. Optionally generate pseudo-tests.

**UX:** Results displayed in Test panel (e.g., "3 checks: 2 pass, 1 warning").

### 4. QA Agent (Context-Aware Q&A via RAG)
**Purpose:** Answer user questions about the codebase and changes.

**Inputs:**
- User question
- Vector search over project files

**Outputs:**
- Explanations referencing specific files/lines

**Responsibilities:**
- Summarize logic in human-friendly language
- Highlight impact of recent changes

### 5. Customizer Agent (Feedback Loop & Telemetry)
**Purpose:** Capture structured feedback and logs for future model improvement.

**Inputs:**
- Session metadata
- User rating (1-5 stars)
- Optional free-text feedback

**Outputs:**
- Append-only JSONL logs stored locally

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
```

**UX:** Lightweight feedback prompt after each completed run.

**Value:** Built-in fine-tuning data loop without cloud backend.

## INTERACTION MODES

### 1. Agent Mode (Fully Autonomous)
**Flow:** Planner → Coder → Tester → QA → Customizer

**User Experience:**
- User enters requirement and clicks "Run"
- Pulse generates plan (shown for transparency)
- Edits files automatically
- Runs validation
- Summarizes what changed
- Prompts for feedback
- Updated files open/refresh in embedded editor

**Use Case:** Quick iteration when user trusts the system.

### 2. Plan Mode (Human-in-the-Loop)
**Flow:** Planner → **(User Approves Plan)** → Coder → Tester → QA → Customizer

**User Experience:**
- User enters requirement and selects Plan Mode
- Planner presents step-by-step plan
- User can approve entire plan or adjust descriptions
- Only then does Coder modify files

**Use Case:** Higher-stakes changes requiring explicit review.

### 3. Ask Mode (Q&A Only)
**Flow:** QA → Customizer

**User Experience:**
- User asks questions about existing code or behavior
- No file changes performed

**Use Case:** Code comprehension, impact analysis, debugging support.

## EMBEDDED CODE EDITOR (Critical Feature)

**Purpose:** Make Pulse a usable day-to-day IDE, not just an AI command console.

**Features:**
- Central panel shows currently selected file from workspace
- Supports viewing and editing PLC-style (Structured Text) code
- Basic affordances: monospaced font, line numbers, simple keyboard shortcuts
- Changes saved to disk and become part of context for all agents

**File Tree / Workspace Panel:**
- Left-hand panel shows workspace folder structure
- Selecting a file opens it in editor
- New files created by Coder Agent appear automatically

**Agent-Aware Editing:**
- Coder Agent reads files via same abstraction editor uses
- Writes changes that editor immediately reflects
- Manual user edits are first-class: subsequent agent runs take updated file contents as ground truth

**Safety:**
- All edits (human or agent) constrained to configured workspace
- Atomic writes when saving from agents to avoid partial-file corruption

## MVP PRIORITIES

**MUST HAVE:**
1. Embedded code editor with file tree
2. All 5 agents working in orchestrated flow
3. All 3 interaction modes (Agent, Plan, Ask)
4. Local persistence (SQLite + filesystem)
5. RAG over workspace files (Chroma)
6. Feedback collection system
7. GitHub Actions CI/CD pipeline
8. Windows .exe build

**KEEP SIMPLE:**
- No cloud backend
- No multi-project management
- No direct PLC hardware connection
- Basic UI (functional over beautiful)
- Single PLC dialect (Structured Text-like)

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
2. Open workspace folder and view/edit code in embedded editor
3. Complete one end-to-end flow in each mode:
   - **Agent Mode:** requirement → code change → test summary → feedback
   - **Plan Mode:** requirement → plan review → approved code change
   - **Ask Mode:** ask question → receive explanation referencing code
4. Perceive it as "a real IDE, not a demo script"

## DEVELOPMENT PRINCIPLES

1. **MVP-First:** No over-engineering. Ship functional, not perfect.
2. **Local-First:** All data stays on user's machine.
3. **Safety:** Atomic writes, workspace constraints, no destructive operations.
4. **Speed:** Prioritize functional stability over aesthetics.
5. **Modularity:** Agents are pluggable LangGraph nodes.

## REFERENCE DOCUMENTS

- Full PRD: `Pulse_Agentic_AI_IDE_PRD.MD`
- This file (`CLAUDE.md`) is the **source of truth** for all implementation decisions.