# Pulse IDE - Phase 2: Architecture Cleanup (Delete context_manager)

## Context
Pulse is a desktop IDE for PLC coding with AI assistance. **Read CLAUDE.md for full architecture and requirements.**

**Current Problem:** `src/core/context_manager.py` pre-classifies workspaces as "PLC_PROJECT" or "GENERIC" on startup. This is wrong - Claude Code uses dynamic discovery via tools instead.

**Why This Matters:** Static classification breaks hybrid projects (Python + PLC + JavaScript). It locks workspace into one type even when it contains multiple languages. Claude Code/Cursor don't do this - they discover structure dynamically.

---

## What to Do

### 1. Delete context_manager.py Entirely
**File:** `src/core/context_manager.py`

**Requirements:**
- DELETE this file completely
- Verify no other files import from it (search codebase for `from src.core.context_manager` or `import context_manager`)
- Expected: Only `runtime.py` imports it

**Why:** This file implements the wrong architectural pattern. We're following Claude Code's proven approach instead.

---

### 2. Update runtime.py
**File:** `src/agents/runtime.py`

**Requirements:**
- Remove `from src.core.context_manager import detect_workspace_type` import
- Remove `workspace_type = detect_workspace_type(project_root)` call
- Remove `workspace_type` parameter from `create_initial_master_state()` call

**Why:** Master Agent will discover workspace structure on-demand using `search_workspace` and `manage_file_ops` tools, not upfront classification.

**How (Brief):** Delete import line, delete function call, remove parameter. Master Agent starts with no assumptions about workspace.

---

### 3. Update State Schema
**File:** `src/agents/state.py`

**Requirements:**
- Remove `workspace_type` field from `MasterState` TypedDict (if it exists)
- Remove `workspace_type` parameter from `create_initial_master_state()` function

**Why:** No more static classification, so no need to store workspace type in state.

**How (Brief):** Remove the field and parameter. Workspace context is discovered dynamically via tool usage.

---

### 4. Implement Dynamic PLC Detection
**Concept:** Master Agent detects PLC files during conversation, not upfront

**How It Works:**
1. User asks: "Add a timer to Motor_1"
2. Master calls `search_workspace("Motor_1")`
3. Master sees results from `motor.st` file (Structured Text)
4. Master thinks: "This is PLC code" → dynamically enhances prompt with PLC expertise
5. Master generates IEC 61131-3 compliant code

**What to Implement:**
- In `master_graph.py` or `prompts.py`, add logic to enhance system prompt when `.st` files detected in tool results
- No upfront classification - enhancement happens during conversation based on actual file discoveries

**Why:** Supports hybrid projects. If workspace has Python + PLC, Master discovers both as needed.

---

### 5. Test Dynamic Discovery
**Test Cases:**

**Test 1: Hybrid Project**
```
Workspace:
- main.py (Python)
- motor.st (PLC)
- server.js (JavaScript)

User: "What languages are in this project?"
Expected: Master uses search_workspace or manage_file_ops, discovers all three, responds: "This project uses Python, PLC Structured Text, and JavaScript"
```

**Test 2: PLC Code Generation**
```
Workspace: motor.st exists

User: "Add emergency stop to Motor_1"
Expected:
- Master calls search_workspace("Motor_1")
- Sees .st file
- Dynamically enhances prompt with PLC expertise
- Generates IEC 61131-3 code
```

**Test 3: No Errors**
```
Expected: No import errors, no missing workspace_type errors, all modes work (Agent/Ask/Plan)
```

---

## Success Criteria

- [ ] `src/core/context_manager.py` file does not exist
- [ ] No imports of `context_manager` in codebase (grep confirms)
- [ ] `runtime.py` does not call `detect_workspace_type()`
- [ ] `workspace_type` removed from state schema
- [ ] Hybrid projects (Python + PLC + JS) handled correctly
- [ ] Master Agent discovers project structure dynamically via tools
- [ ] PLC code generation still works (dynamic detection)
- [ ] All Phase 1 functionality preserved (no regression)

---

## Critical Warnings

⚠️ **Do NOT create a new context_manager:** The whole point is to delete it. Dynamic discovery via tools replaces it.

⚠️ **Do NOT add workspace_type anywhere else:** No static classification. Master Agent figures it out on-demand.

⚠️ **Test hybrid projects:** Ensure Python + PLC + JS workspaces work correctly (no assumptions about "one type").

---

## Resources

- **Architecture Reference:** Read CLAUDE.md → "Dynamic Workspace Understanding" and "Architecture Decisions (Non-Negotiable)"
- **Existing Code:** Review `src/agents/runtime.py` to find where context_manager is called
- **Tool Usage:** Check `src/tools/rag.py` (search_workspace) and `src/tools/file_ops.py` (manage_file_ops) to understand how Master discovers files

---

**Implementation Approach:**
1. Search codebase for all context_manager references
2. Delete file
3. Remove imports and calls
4. Update state schema
5. Test that nothing breaks
6. Test hybrid project discovery
