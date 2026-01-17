# Phase C: CI/CD Pipeline & Deployment - Prompt for New Chat

Copy and paste this entire prompt into a new chat session to implement Phase C.

---

## Context: What is Pulse?

**Pulse** is an Agentic AI IDE specifically designed for PLC (Programmable Logic Controller) coding, but also supports general programming tasks. It combines the power of large language models with a modern Electron-based UI to provide an intelligent coding assistant that can:

- **Understand natural language requests** and translate them into code changes
- **Execute terminal commands** with user approval
- **Create, read, update, and delete files** with diff previews
- **Use multi-agent systems** (CrewAI for code generation, AutoGen for code review debates)
- **Support multiple LLM providers** (OpenAI, Anthropic, Google Gemini)
- **Maintain conversation history** for context-aware assistance

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pulse IDE Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Electron + React + TypeScript)                        │
│  ├── Monaco Editor with diff preview                            │
│  ├── Chat panel with streaming responses                        │
│  ├── Terminal approval UI                                        │
│  └── File explorer with workspace management                    │
├─────────────────────────────────────────────────────────────────┤
│  Backend (Python + FastAPI + LangGraph)                          │
│  ├── WebSocket server for real-time communication               │
│  ├── Master Agent (LangGraph state machine)                     │
│  ├── Tool Registry (file ops, terminal, search, etc.)           │
│  ├── CrewAI/AutoGen integration for sub-agents                  │
│  └── LLM Client (OpenAI, Anthropic, Google)                     │
└─────────────────────────────────────────────────────────────────┘
```

## What Has Been Achieved (Phases A & B)

### Phase A: Core Functionality
- ✅ LangGraph-based Master Agent with state machine architecture
- ✅ Tool registry with 15+ tools (file ops, terminal, codebase search, etc.)
- ✅ WebSocket communication between Electron frontend and Python backend
- ✅ Approval flow for dangerous operations (terminal commands, file writes)
- ✅ Conversation history persistence with SQLite
- ✅ Multi-provider LLM support (OpenAI, Anthropic, Google Gemini)
- ✅ Settings UI for API key configuration

### Phase B: UI & UX
- ✅ Electron-based UI with Monaco editor
- ✅ Diff preview for file changes
- ✅ Terminal approval modal with risk levels
- ✅ Chat interface with streaming responses
- ✅ File explorer with workspace management
- ✅ Dark theme with modern aesthetics

## Why We Need Phase C: CI/CD Pipeline

Currently, to use Pulse, developers must:
1. Clone the repository
2. Install Python dependencies (`pip install -r requirements.txt`)
3. Install Node.js dependencies (`npm install`)
4. Run the backend (`python -m src.server.main`)
5. Run the frontend (`npm run dev`)

**This is a barrier to adoption.** We need a simple `Pulse.exe` that users can download and run.

### Why GitHub Actions?

GitHub Actions provides:
- **Free CI/CD** for open source projects
- **Cross-platform builds** (Windows, macOS, Linux)
- **Automatic releases** triggered by git tags
- **Artifact hosting** for downloadable executables
- **Community familiarity** - most developers know GitHub

### Goals for Phase C

1. **Automated Builds**: When code is pushed, automatically build and test
2. **Automated Releases**: When a version tag (e.g., `v0.1.0`) is pushed, create a GitHub Release
3. **NSIS Installer**: Provide `Pulse-Setup-0.1.0.exe` - a Windows installer
4. **Bundled Backend**: Package Python backend with the Electron app
5. **No Setup Required**: Run installer → Double-click `Pulse.exe` → Pulse starts

### Installer Specifications

The release should produce an **NSIS installer** (`Pulse-Setup-0.1.0.exe`) that:

- Shows a setup wizard (Next → Install → Finish)
- Installs Pulse to `C:\Program Files\Pulse`
- Creates Start Menu shortcuts
- Adds entry to "Add/Remove Programs" (clean uninstall)
- Optionally creates desktop shortcuts
- The installed application should be named **`Pulse.exe`**
- Uses icon: `assets/pulse_icon_bg_020321.ico`

### Installer UI Design

The NSIS installer should have the following screens:

**Screen 1: Welcome**
```
┌────────────────────────────────────────────────┐
│  [Pulse Icon]                                  │
│                                                │
│  Welcome to Pulse Setup                        │
│                                                │
│  Setup will guide you through the             │
│  installation of Pulse.                        │
│                                                │
│  Click Next to continue.                       │
│                                                │
│                    [Next >]  [Cancel]          │
└────────────────────────────────────────────────┘
```

**Screen 2: Choose Install Location**
```
┌────────────────────────────────────────────────┐
│  Choose Install Location                       │
│                                                │
│  Destination Folder:                           │
│  ┌──────────────────────────────┐ [Browse...] │
│  │ C:\Program Files\Pulse       │              │
│  └──────────────────────────────┘              │
│                                                │
│  Space required: ~250 MB                       │
│  Space available: 120 GB                       │
│                                                │
│       [< Back]  [Install]  [Cancel]            │
└────────────────────────────────────────────────┘
```

**Screen 3: Installing (Progress)**
```
┌────────────────────────────────────────────────┐
│  Installing                                    │
│                                                │
│  Please wait while Pulse is being installed.  │
│                                                │
│  ████████████████░░░░░░░░░░░░  62%            │
│                                                │
│  Extracting: pulse-backend.exe                 │
│                                                │
│                              [Cancel]          │
└────────────────────────────────────────────────┘
```

**Screen 4: Finish**
```
┌────────────────────────────────────────────────┐
│  Completing Pulse Setup                        │
│                                                │
│  Setup has finished installing Pulse on       │
│  your computer.                                │
│                                                │
│  ☑ Create Desktop Shortcut                    │
│  ☑ Launch Pulse                               │
│                                                │
│                    [Finish]                    │
└────────────────────────────────────────────────┘
```

**Customization Options (Optional):**
- Custom header banner image (150x57 pixels)
- Custom sidebar/wizard image (164x314 pixels)
- License agreement page (if needed)
- Custom installer icon (use `pulse_icon_bg_020321.ico`)

---

## Phase C Implementation Task

### Objective

Set up a complete CI/CD pipeline using GitHub Actions for Pulse IDE v0.1 that:

1. **Builds the application** on push to main branch
2. **Runs tests** (Python backend + TypeScript frontend)
3. **Creates releases** when version tags are pushed
4. **Produces downloadable executables** for Windows (required), macOS (optional), Linux (optional)

### Technical Requirements

#### 1. GitHub Actions Workflows

Create the following workflow files in `.github/workflows/`:

**a. `ci.yml` - Continuous Integration**
- Trigger: Push to `main`, Pull Requests
- Jobs:
  - Lint Python code (flake8/ruff)
  - Lint TypeScript code (eslint)
  - Run Python tests (pytest)
  - Run TypeScript tests (if any exist)
  - Build Electron app (no packaging, just verify build works)

**b. `release.yml` - Release Pipeline**
- Trigger: Push of tags matching `v*` (e.g., `v0.1.0`)
- Jobs:
  - Build Windows executable using electron-builder
  - Bundle Python backend with PyInstaller
  - Create GitHub Release with changelog
  - Upload artifacts (exe, zip, checksums)

#### 2. Backend Bundling

The Python backend needs to be bundled with the Electron app:

**Option A: PyInstaller Bundle**
- Use PyInstaller to create `pulse-backend.exe`
- Electron spawns this on startup
- Pros: Single file, fast startup
- Cons: Large file size (~100MB+)


#### 3. Electron Builder Configuration

Update `pulse-electron/package.json` with electron-builder config:

```json
{
  "build": {
    "appId": "com.pulse.ide",
    "productName": "Pulse",
    "win": {
      "target": "nsis",
      "icon": "../assets/pulse_icon_bg_020321.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "Pulse",
      "installerIcon": "../assets/pulse_icon_bg_020321.ico",
      "uninstallerIcon": "../assets/pulse_icon_bg_020321.ico"
    },
    "extraResources": [
      {
        "from": "../dist-backend/pulse-backend.exe",
        "to": "backend/pulse-backend.exe"
      }
    ]
  }
}
```

Key requirements:
- **App name**: `Pulse` (produces `Pulse.exe`)
- **Icon**: `assets/pulse_icon_bg_020321.ico`
- **Installer name**: `Pulse-Setup-${version}.exe`
- **Install location**: `C:\Program Files\Pulse`
- Include backend executable as extra resource

#### 4. Version Management

- Use npm version + git tags for releases
- Sync version between package.json and Python's version
- Generate changelog from commits (optional: use conventional commits)

### File Structure

```
.github/
└── workflows/
    ├── ci.yml              # CI pipeline
    └── release.yml         # Release pipeline

pulse-electron/
├── package.json            # Add electron-builder config
├── electron-builder.yml    # Electron builder config (optional)
└── scripts/
    └── build-backend.js    # Script to build Python backend

src/
├── __version__.py          # Python version file
└── ...
```

### Deliverables

1. `.github/workflows/ci.yml` - CI workflow
2. `.github/workflows/release.yml` - Release workflow
3. Updated `pulse-electron/package.json` with electron-builder config
4. `pyinstaller.spec` or build script for backend bundling
5. Documentation on how to create a release
6. (Optional) Auto-update configuration

### Success Criteria

- [ ] CI runs on every push and PR
- [ ] Release workflow creates GitHub Release on tag push
- [ ] `Pulse-Setup-0.1.0.exe` installer is downloadable from releases
- [ ] Installer creates `Pulse.exe` in `C:\Program Files\Pulse`
- [ ] Start Menu and optional Desktop shortcuts are created
- [ ] Executable runs without requiring Python/Node installation
- [ ] Backend starts automatically when `Pulse.exe` launches
- [ ] Icon displays correctly (`assets/pulse_icon_bg_020321.ico`)

---

## Repository Information

- **Repository**: `c:\Users\katha\OneDrive - The Pennsylvania State University\Documents\Projects\Pulse`
- **Frontend**: `pulse-electron/` (Electron + React + TypeScript + Vite)
- **Backend**: `src/` (Python + FastAPI + LangGraph)
- **Version**: 0.1.0 (first public release)

## Key Files to Reference

- `pulse-electron/package.json` - Frontend dependencies and scripts
- `requirements.txt` - Python dependencies
- `src/server/main.py` - Backend entry point
- `pulse-electron/electron/main.ts` - Electron main process

---

## Notes

- This is Pulse v0.1 - the first public release
- Focus on Windows first; macOS/Linux can be added later
- Keep the CI/CD simple and maintainable
- Document the release process clearly
- Test the executable on a clean Windows machine before release

---

*End of Phase C Prompt*
