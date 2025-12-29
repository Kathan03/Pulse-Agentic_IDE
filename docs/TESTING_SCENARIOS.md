# Pulse IDE v2.6 - Testing Scenarios

Manual verification guide for Pulse IDE functionality.

---

## Pre-requisites

1. Python 3.10+ installed
2. Virtual environment activated
3. Dependencies installed: `pip install -r requirements.txt`
4. OpenAI API key configured (via Settings UI or platformdirs config)

---

## Scenario 1: The Happy Path (Simple Question)

**Goal:** Verify basic Q&A functionality works without tool calls.

### Steps

1. Launch app: `python main.py`
2. In Pulse Chat tab, type: `"What is structured text?"`
3. Press Enter or click Send

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Input received | `src/ui/app.py` → `_handle_agent_query()` |
| Single-run lock | `is_running = True`, input disabled |
| Vibe status | "Pulse is Wondering..." appears | `src/ui/components/vibe_loader.py` |
| Graph starts | `src/agents/runtime.py` → `run_agent()` |
| Master agent | `src/agents/master_graph.py` → `master_agent_node()` |
| LLM call | Direct answer (no tool needed) | `call_llm_stub()` |
| Response | Answer appears in chat | `src/ui/log_panel.py` |
| Cleanup | `is_running = False`, input enabled |

### Verification Checklist

- [ ] No approval modal appeared (no tools needing approval)
- [ ] Response is displayed in chat
- [ ] UI did not freeze during processing
- [ ] Vibe loader appeared and disappeared

---

## Scenario 2: The Dangerous Path (Terminal Command Approval)

**Goal:** Verify terminal command approval flow blocks dangerous commands.

### Steps

1. Launch app: `python main.py`
2. In Pulse Chat tab, type: `"Run the command: rm -rf /tmp/test"`
3. Press Enter

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Input received | `src/ui/app.py` → `_handle_agent_query()` |
| Master decides | Tool call: `plan_terminal_cmd` | `master_agent_node()` |
| Tool planning | Creates CommandPlan with risk_label: **HIGH** | `src/tools/terminal.py` |
| Approval request | `emit_approval_requested("terminal", ...)` | `src/core/events.py` |
| Graph pauses | `interrupt()` called | `tool_execution_node()` |
| Modal appears | TerminalApprovalModal shows | `src/ui/components/approval.py` |
| User sees | Red "HIGH" risk badge, command preview |
| User denies | Click [Deny] |
| Graph resumes | `user_decision = {"approved": False}` |
| Response | "Action cancelled: User denied approval" |

### Verification Checklist

- [ ] Terminal approval modal appeared
- [ ] Risk label shows **HIGH** (red badge)
- [ ] Command is displayed: `rm -rf /tmp/test`
- [ ] Clicking [Deny] closes modal and shows denial message
- [ ] Command was NOT executed

### Variant: Approve Safe Command

1. Type: `"Run git status"`
2. Modal shows risk_label: **LOW** (green)
3. Click [Execute]
4. Command executes, output shown

---

## Scenario 3: The Heavy Lift (Patch Approval)

**Goal:** Verify code generation triggers patch approval flow.

### Steps

1. Launch app: `python main.py`
2. Create a test file in workspace: `test.st`
3. In Pulse Chat, type: `"Add a timer variable to test.st"`
4. Press Enter

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Input received | `src/ui/app.py` → `_handle_agent_query()` |
| Master decides | Tool call: `apply_patch` | `master_agent_node()` |
| Patch preview | Creates PatchPlan with diff | `src/tools/patching.py` |
| Approval request | `emit_approval_requested("patch", ...)` | `src/core/events.py` |
| Graph pauses | `interrupt()` called | `tool_execution_node()` |
| Modal appears | PatchApprovalModal shows | `src/ui/components/approval.py` |
| User sees | Diff preview with +/- lines (green/red) |
| User approves | Click [Approve] |
| Patch executed | `execute_patch()` writes file | `src/tools/patching.py` |
| File updated | `files_touched` includes `test.st` |
| Editor refreshes | Tab reloads with new content |

### Verification Checklist

- [ ] Patch approval modal appeared
- [ ] Diff shows green (+) lines for additions
- [ ] Diff shows red (-) lines for deletions (if any)
- [ ] Clicking [Approve] closes modal
- [ ] File was actually modified on disk
- [ ] Editor tab refreshed with new content

---

## Scenario 4: The CrewAI Feature (Tier 3 Tool)

**Goal:** Verify CrewAI integration for complex features.

### Pre-requisite

- Settings → Agent Toggles → "Enable CrewAI Builder" = ON
- OpenAI API key configured

### Steps

1. Launch app: `python main.py`
2. In Pulse Chat, type: `"Generate a snake game in Python"`
3. Press Enter

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Input received | `src/ui/app.py` → `_handle_agent_query()` |
| Master decides | Tool call: `implement_feature` | `master_agent_node()` |
| CrewAI starts | `asyncio.to_thread(crew.kickoff)` | `src/tools/builder_crew.py` |
| Vibe status | "Pulse is Preparing..." (long duration) |
| Crew workflow | Planner → Coder → Reviewer agents run |
| Returns patches | `FeatureResult` with `patch_plans` list |
| Each patch | Triggers approval flow (see Scenario 3) |
| Completion | Summary displayed in chat |

### Verification Checklist

- [ ] UI remained responsive during CrewAI execution
- [ ] Vibe status showed throughout
- [ ] Multiple patch approvals may appear (one per file)
- [ ] Final summary mentions files created/modified
- [ ] **IMPORTANT:** CrewAI transcript NOT visible (context containment)

### Toggle OFF Test

1. Settings → Agent Toggles → "Enable CrewAI Builder" = OFF
2. Repeat the request
3. Should return: "CrewAI is disabled in settings"

---

## Scenario 5: The AutoGen Audit (Tier 3 Tool)

**Goal:** Verify AutoGen diagnostics integration.

### Pre-requisite

- Settings → Agent Toggles → "Enable AutoGen Auditor" = ON
- OpenAI API key configured

### Steps

1. Launch app: `python main.py`
2. In Pulse Chat, type: `"Check my project for security issues"`
3. Press Enter

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Input received | `src/ui/app.py` → `_handle_agent_query()` |
| Master decides | Tool call: `diagnose_project` | `master_agent_node()` |
| Stage A | Deterministic checks (file structure, syntax) | `src/tools/auditor_swarm.py` |
| Stage B (if ON) | AutoGen debate (optional) |
| Returns JSON | `DiagnosisResult` with findings |
| Response | Formatted findings in chat |

### Expected Output Structure

```json
{
  "risk_level": "MEDIUM",
  "findings": [
    {"severity": "WARNING", "file": "main.st", "line": 42, "message": "..."}
  ],
  "prioritized_fixes": [
    {"priority": 1, "action": "...", "rationale": "..."}
  ],
  "verification_steps": ["1. Run tests", "2. Check build"]
}
```

### Verification Checklist

- [ ] Findings displayed in chat
- [ ] Risk level badge visible (LOW/MEDIUM/HIGH)
- [ ] Each finding shows file, line, severity
- [ ] Prioritized fixes listed
- [ ] **IMPORTANT:** AutoGen debate transcript NOT visible (context containment)

### Toggle OFF Test

1. Settings → Agent Toggles → "Enable AutoGen Auditor" = OFF
2. Repeat the request
3. Should return Stage A results only (deterministic checks, no LLM spend)

---

## Scenario 6: Settings Persistence

**Goal:** Verify settings save to platformdirs and persist across sessions.

### Steps

1. Launch app: `python main.py`
2. Menu → Settings → API Keys
3. Enter a test API key: `sk-test-123`
4. Click [Save]
5. Close the app
6. Re-launch app
7. Menu → Settings → API Keys
8. Verify key is still there

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Open settings | `SettingsModal.open()` | `src/ui/components/settings_modal.py` |
| Load settings | `SettingsManager.load_settings()` | `src/core/settings.py` |
| Save settings | `SettingsManager.save_settings()` |
| File written | `%APPDATA%\Pulse\config.json` (Windows) |
| Re-launch | Settings loaded from config file |

### Verification Checklist

- [ ] Settings modal opens via Menu → Settings
- [ ] API key field is password-masked
- [ ] "Reveal" button shows actual key
- [ ] Save shows "Settings saved successfully!"
- [ ] Settings persist after app restart
- [ ] Config file exists at platformdirs path

---

## Scenario 7: Shutdown Cleanup

**Goal:** Verify background processes are killed on app close.

### Steps

1. Launch app: `python main.py`
2. Start a long-running request (e.g., "Generate a complex feature")
3. While agent is running (vibe loader visible), close the window
4. Check for zombie processes

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| Close window | `page.on_close` triggered | `src/ui/app.py` |
| Cleanup called | `_cleanup()` method |
| Cancel run | `current_run_task.cancel()` |
| Terminal cleanup | `terminal.cleanup()` |
| Process cleanup | `cleanup_processes()` | `src/core/processes.py` |
| App exits | Clean shutdown |

### Verification Checklist

- [ ] No console errors on close
- [ ] Check Task Manager: No orphan Python processes
- [ ] No zombie CrewAI/AutoGen processes
- [ ] Shutdown message: "[SHUTDOWN] Cleanup complete"

---

## Scenario 8: Single-Run Lock

**Goal:** Verify only one agent run can be active at a time.

### Steps

1. Launch app: `python main.py`
2. Type a request and press Enter
3. While agent is running, type another request and press Enter

### Expected Behavior

| Step | What Happens | Files Activated |
|------|--------------|-----------------|
| First request | `is_running = True` | `src/ui/app.py` |
| Second request | Check `is_running` |
| Blocked | Input queued, message shown |
| Message | "A run is already in progress. Your input has been queued." |
| First completes | `is_running = False` |
| Queue processed | Queued input automatically runs |

### Verification Checklist

- [ ] Second request shows queue message
- [ ] First request completes normally
- [ ] Queued request runs automatically after
- [ ] No concurrent graph executions

---

## Running Automated Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_tier3_toggles.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

*Last updated: December 2024*
*Pulse IDE v2.6 - Manual Testing Guide*
