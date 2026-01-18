# Pulse Agentic IDE <img src="assets/fox_pixel_25x25.svg" alt="Pulse Mascot" width="55" />

<div align="center">
  <img src="assets/pulse_icon_bg_062024_256.png" alt="Pulse Logo" width="200" />
  
  <br />
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![Node.js](https://img.shields.io/badge/Node.js-20+-green.svg)](https://nodejs.org/)
  [![Electron](https://img.shields.io/badge/Electron-28-9FEAF9.svg)](https://www.electronjs.org/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6.svg)](https://www.typescriptlang.org/)
  [![CI](https://github.com/Kathan03/Pulse-Agentic_IDE/actions/workflows/ci.yml/badge.svg)](https://github.com/Kathan03/Pulse-Agentic_IDE/actions)

  <h3>🚀 The First AI IDE Designed for Agent-Human Collaboration</h3>

  <p><i><b>Pulse</b> is not just another autocomplete tool. It's a fully autonomous coding partner powered by <b>LangGraph</b>, <b>CrewAI</b>, and <b>AutoGen</b> — capable of planning, executing, and verifying complex software engineering tasks across your entire codebase.</i></p>
</div>

---

## 🎯 Why Pulse?

### The Problem with Current AI Coding Tools

| Feature | Claude Code / Windsurf / Antigravity | **Pulse** |
|---------|--------------------------------------|-----------|
| **Pricing** | $20/month subscription (or usage limits) | **Pay only for what you use** |
| **Usage Limits** | Time-based limits (e.g., 5 hours of Claude usage) | **No usage limits — API-based access** |
| **Model Lock-in** | Tied to specific providers | **Any model: OpenAI, Anthropic, Google Gemini** |
| **PLC/Industrial Support** | None | **First-class IEC 61131-3 support** |
| **Multi-Agent Architecture** | Single agent | **CrewAI + AutoGen sub-agents** |

### 💰 Cost Savings Example

With subscription-based tools, you pay **$20/month** regardless of usage. With Pulse:
- Light usage month (~$5-10 API costs) → **Save $10-15**
- Variable usage → Pay only for tokens consumed
- No usage → **$0** — No wasted subscription fees

**You bring your own API keys. You control your costs.**

---

## ✨ Key Features

### 🧠 **Multi-Agent Architecture**
Pulse orchestrates multiple AI agents working in concert:
- **Master Agent (LangGraph)**: Stateful reasoning engine with cyclic workflows
- **Builder Crew (CrewAI)**: Role-based agents (Planner, Coder, Reviewer) for complex feature implementation
- **Auditor Swarm (AutoGen)**: Multi-agent debates for code review and security analysis

### 🔌 **Multi-Provider LLM Support**
Use any model from any provider — switch models mid-conversation:

| Provider | Supported Models |
|----------|------------------|
| **OpenAI** | `gpt-5.2`, `gpt-5.1`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5.2-codex`, `gpt-5.1-codex-max`, `gpt-5.1-codex`, `gpt-5.2-pro`, `gpt-5-pro` |
| **Anthropic** | `claude-sonnet-4.5`, `claude-opus-4.5` |
| **Google Gemini** | `gemini-3-pro`, `gemini-3-flash` |

### 🛡️ **Enterprise-Grade Safety**
- **Terminal Guardrails**: Commands analyzed for risk (Low/Medium/High)
- **Diff Previews**: Review every file change before applying
- **Approval Workflows**: Dangerous operations require explicit user consent

### 🏭 **PLC & Industrial Automation**
Specialized capabilities for **Structured Text (IEC 61131-3)** programming:
- First AI IDE tailored for OT/ICS engineers
- Also supports general-purpose programming (Python, TypeScript, etc.)

### 💬 **Conversation History**
Persistent chat history with context-aware assistance across sessions.

---

## 🛠️ Technology Stack

### **AI/ML Frameworks**
- **LangGraph** — Stateful, cyclic agent workflows with tool execution
- **LangChain** — LLM abstraction, tool definitions, prompt management
- **CrewAI** — Role-based multi-agent orchestration
- **PyAutoGen** — Microsoft's multi-agent conversation framework

### **LLM Provider SDKs**
- **OpenAI SDK** — GPT-5.x series
- **Anthropic SDK** — Claude 4.5 series
- **Google Generative AI SDK** — Gemini 3 series

### **Backend (Python)**
- **FastAPI** + **WebSockets** — Real-time bidirectional communication
- **Pydantic** — Data validation and settings management
- **ChromaDB** — Vector database for semantic codebase search
- **PyInstaller** — Backend bundling for distribution

### **Frontend (TypeScript)**
- **Electron** — Desktop application framework
- **React** + **Vite** — Modern UI with fast HMR
- **Monaco Editor** — VS Code's editor engine
- **Xterm.js** — Terminal emulation

### **DevOps & CI/CD**
- **GitHub Actions** — Automated CI/CD pipeline
- **electron-builder** — Windows installer (NSIS)
- **pytest** + **Ruff** — Python testing & linting
- **ESLint** — TypeScript linting

> **Note**: The UI was initially prototyped with Flet (Flutter for Python), then migrated to Electron + React for production-grade UX.

---

## 🏗️ Architecture

Pulse uses a **Hub-and-Spoke** architecture where the Master Agent coordinates all operations:

```mermaid
graph TD
    User["User / Developer"] -->|Chat & Commands| UI["Pulse UI (Electron)"]
    UI -->|Events| Master["Master Agent (LangGraph)"]

    subgraph "Unified Master Loop"
        Master -->|Request Tool| Exec["Tool Execution Node"]
        Exec -->|Tool Result| Master
    end

    subgraph "Tool Registry"
        Exec -->|Invoke| Tools["Standard Tools"]
        Exec -->|Invoke| Crew["CrewAI Sub-agents"]
        Exec -->|Invoke| AutoGen["AutoGen Auditors"]
    end
```

**Key Design Decisions:**
- **LangGraph** provides the core loop with state persistence and cyclic execution
- **CrewAI** and **AutoGen** are invoked as **tools**, not independent workflows
- **WebSocket** enables real-time streaming of agent responses
- **Tool approvals** intercept dangerous operations before execution

---

## 🚀 CI/CD Pipeline

Pulse features a fully automated build and release pipeline using GitHub Actions:

### **Continuous Integration (`ci.yml`)**
Triggered on every push and pull request:
- ✅ Python linting (Ruff)
- ✅ TypeScript linting (ESLint)
- ✅ Python tests (pytest)
- ✅ TypeScript type checking
- ✅ Electron build verification

### **Automated Releases (`release.yml`)**
Triggered on version tags (`v*`):
1. **Build Python backend** → `pulse-server.exe` (PyInstaller)
2. **Build Electron app** → `Pulse-Setup-{version}.exe` (electron-builder + NSIS)
3. **Create GitHub Release** with checksums and changelog

```bash
# To create a release:
git tag v0.1.0
git push origin v0.1.0
# → Automatically builds and publishes installer!
```

---

## 📥 Installation

### Option 1: Download Installer (Recommended)
1. Go to [Releases](https://github.com/Kathan03/Pulse-Agentic_IDE/releases)
2. Download `Pulse-Setup-{version}.exe`
3. Run the installer
4. Configure your API keys in Settings

### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/Kathan03/Pulse-Agentic_IDE.git
cd Pulse-Agentic_IDE

# Backend setup
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend setup
cd pulse-electron
npm install

# Run in development mode
npm run dev  # In one terminal
python -m src.server.main  # In another terminal
```

---

## ⚙️ Configuration

Configure your API keys in the Settings panel (or via `.env` file):

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
```

---

## 📂 Project Structure

```
Pulse/
├── .github/workflows/     # CI/CD pipelines
│   ├── ci.yml             # Continuous integration
│   └── release.yml        # Automated releases
├── pulse-electron/        # Electron + React frontend
│   ├── electron/          # Main process (TypeScript)
│   ├── src/               # React components
│   └── package.json       # Frontend dependencies
├── src/                   # Python backend
│   ├── agents/            # LangGraph, CrewAI, AutoGen
│   ├── server/            # FastAPI WebSocket server
│   ├── tools/             # Tool implementations
│   └── core/llm_client.py # Multi-provider LLM abstraction
├── tests/                 # pytest test suite
└── requirements.txt       # Python dependencies
```

---

## 🔮 Future Roadmap

- [ ] **Git Operations Tool**: Full git support (commit, push, pull, branch, merge)
- [ ] **Model Routing/Fallback**: Automatically route tasks to optimal models
- [ ] **Plugin System**: Third-party plugin support
- [ ] **macOS and Linux Builds**: Cross-platform installers
- [ ] **Local LLM Support**: Ollama, LM Studio integration

See [FUTURE_OPTIMIZATIONS.md](docs/FUTURE_OPTIMIZATIONS.md) for the complete roadmap.

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">
  <p>Built with ❤️ by <b>Kathan</b></p>
  <p><i>Demonstrating expertise in AI/ML Engineering, Full-Stack Development, and DevOps</i></p>
</div>
