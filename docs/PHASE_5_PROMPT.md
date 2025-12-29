# Pulse IDE - Phase 5: Testing & Production Release

## Context
Pulse is a desktop IDE for PLC coding with AI assistance. **Read CLAUDE.md for full architecture and requirements.**

**Current Status:** All features implemented (Phases 1-4 complete). Now validating production readiness through comprehensive testing.

**Why This Matters:** v1.0 must be bug-free and professional. Users expect Claude Code-level quality. Testing proves Pulse is ready for real-world use.

---

## What to Do

### 1. Test LLM Integration
**Goal:** Verify Master Agent can call LLMs and use tools via function calling

**Test Cases:**

**Test 1.1: OpenAI GPT-5.2**
- Settings → Select gpt-5.2
- Pulse Chat: "Write a hello world function in Python"
- Expected: GPT calls apply_patch → patch preview → approve → file created
- Success: Code generated, file created, no errors

**Test 1.2: Anthropic Claude Opus 4.5**
- Settings → Select claude-opus-4-5
- Pulse Chat: "Explain how binary search works"
- Expected: Claude responds with explanation (no tool calls)
- Success: Accurate answer, response time < 3 seconds

**Test 1.3: Invalid API Key Error Handling**
- Settings → Enter invalid key
- Pulse Chat: "Hello"
- Expected: Error message "Invalid API key. Please configure in Settings."
- Success: Clear error, no crash, can recover by fixing key

**Why:** Proves LLM integration works for both providers with graceful error handling.

---

### 2. Test Mode Switching
**Goal:** Verify 3 modes behave differently with correct tool access

**Test 2.1: Agent Mode**
- Mode: Agent
- Request: "Add a README.md file"
- Expected: Master uses apply_patch, creates file, requires approval
- Success: All tools available, can modify files

**Test 2.2: Ask Mode**
- Mode: Ask
- Request: "What files are in this project?"
- Expected: Master uses search_workspace, lists files, no modification offered
- Success: Read-only tools only, cannot modify files

**Test 2.3: Plan Mode**
- Mode: Plan
- Request: "How would you implement user authentication?"
- Expected: Master creates structured plan, no execution
- Success: Detailed plan, no tool calls, no web search

**Why:** Proves mode-based prompting works correctly with proper tool restrictions.

---

### 3. Test PLC Code Generation
**Goal:** Verify PLC-specific code generation with IEC 61131-3 compliance

**Test 3.1: Emergency Stop Logic**
- Workspace: motor.st file exists
- Request: "Add emergency stop logic to Motor_1"
- Expected:
  - Master calls search_workspace("Motor_1")
  - Detects .st file (Structured Text)
  - Generates IEC 61131-3 code with safety logic
  - Code includes: IF EmergencyStop THEN Motor_1 := FALSE; END_IF
- Success: Valid Structured Text, safety-first approach, proper variable naming

**Test 3.2: Timer Implementation**
- Request: "Create a 5-second timer for conveyor startup"
- Expected: TON timer with correct syntax (PT := T#5s)
- Success: IEC 61131-3 compliant, proper time format

**Why:** Proves PLC specialization works with dynamic detection (no upfront classification).

---

### 4. Test Multi-Language Projects
**Goal:** Verify hybrid projects (Python + PLC + JS) handled correctly

**Test Setup:**
```
workspace/
├── main.py (Python)
├── plc_controller.st (PLC)
└── dashboard.js (JavaScript)
```

**Test 4.1: Language Detection**
- Request: "What languages are used in this project?"
- Expected: "Python, PLC Structured Text, and JavaScript"
- Success: All three detected, no confusion

**Test 4.2: Language-Specific Code Generation**
- Request 1: "Add error handling to the Python backend"
- Expected: Python code generated (not PLC or JS)
- Request 2: "Add a safety interlock to the PLC"
- Expected: IEC 61131-3 code generated (not Python or JS)
- Success: Correct language detected for each request

**Why:** Proves dynamic workspace understanding works for hybrid projects.

---

### 5. Test Web Search Integration
**Goal:** Verify web_search tool works for documentation questions

**Test 5.1: Documentation Research**
- Mode: Ask
- Request: "How do I use Flet's ExpansionTile?"
- Expected:
  - Master calls web_search("Flet ExpansionTile documentation")
  - Returns results from flet.dev
  - Responds with usage + source links
- Success: Accurate answer with source attribution

**Test 5.2: Offline Graceful Degradation**
- Disconnect internet
- Request: "How do I use pandas DataFrame?"
- Expected:
  - web_search fails with network error
  - Falls back to training data
  - Responds with disclaimer: "I couldn't reach the internet..."
- Success: No crash, fallback works

**Why:** Proves web search enhances documentation Q&A without breaking offline.

---

### 6. Test Approval Gates
**Goal:** Verify human-in-the-loop approvals work for patches and commands

**Test 6.1: Patch Approval**
- Request: "Create a logging utility in utils.py"
- Expected: Patch preview modal appears with diff
- Action: Click Deny
- Expected: Patch NOT applied, utils.py NOT created
- Success: User can reject changes

**Test 6.2: Terminal Command Approval**
- Request: "Install pytest"
- Expected: Terminal approval modal shows "pip install pytest" with MEDIUM risk
- Action: Click Execute
- Expected: Command runs in terminal, output shown
- Success: User approves before execution

**Why:** Proves safety gates prevent unauthorized file/command changes.

---

### 7. Test UI Polish
**Goal:** Verify all UI fixes from Phase 4 work

**Test 7.1: Sidebar Scrolling**
- Open workspace with 50+ files
- Expected: Sidebar scrolls smoothly, no cut-off files
- Success: Scrollbar appears, scrolling works

**Test 7.2: Menu Bar**
- Expected: File | View | Settings | Help visible and clickable
- Success: Menus open, Settings accessible

**Test 7.3: File Tree**
- Workspace with nested folders
- Expected: Folders expand/collapse with ▶/▼ arrows
- Success: VS Code-style tree, hierarchical

**Test 7.4: Model Dropdown**
- Open Settings → Models
- Expected: Shows all 13 models (GPT-5.x, GPT-4.1.x, Claude 4.5)
- Success: All models listed

**Why:** Proves UI feels professional (VS Code-level).

---

### 8. Test Performance
**Goal:** Verify response times acceptable

**Benchmarks:**
- Simple question ("What is 2+2?") → < 2 seconds
- Code generation ("Write hello world") → < 5 seconds
- Web search ("How to use X?") → < 7 seconds
- Complex request ("Implement authentication") → < 10 seconds

**Why:** Proves Pulse is responsive enough for real-world use.

---

## Success Criteria (Production Readiness Checklist)

### Functionality
- [ ] LLM integration works (OpenAI + Anthropic)
- [ ] All 3 modes work (Agent/Ask/Plan)
- [ ] PLC code generation works (IEC 61131-3)
- [ ] Web search works
- [ ] Approval gates work (patch + terminal)
- [ ] Multi-language projects work

### UI/UX
- [ ] Sidebar scrolls
- [ ] Menu bar visible
- [ ] File tree expand/collapse works
- [ ] Model dropdown shows correct models
- [ ] Vibe loader shows status

### Stability
- [ ] No crashes with invalid API keys
- [ ] No crashes offline
- [ ] No crashes with large workspaces
- [ ] Error messages clear
- [ ] Can recover from all errors

### Performance
- [ ] Simple queries < 2 seconds
- [ ] Code generation < 5 seconds
- [ ] Web search < 7 seconds
- [ ] UI responsive (no freezing)

### Security
- [ ] API keys stored in platformdirs (not workspace)
- [ ] File operations restricted to workspace
- [ ] Denylist patterns enforced (.env, credentials)
- [ ] Terminal commands require approval
- [ ] HIGH risk commands clearly labeled

---

## Critical Warnings

⚠️ **ALL tests must pass:** Do not mark v1.0 as ready if any critical test fails. Fix bugs first.

⚠️ **No regressions:** Previous phases' functionality must still work. Test end-to-end flows.

⚠️ **Real-world testing:** Use actual PLC projects and Python projects, not toy examples.

---

## Resources

- **Architecture Reference:** Read CLAUDE.md for complete requirements
- **Test Scenarios:** See `docs/TESTING_SCENARIOS.md` for additional test cases (if exists)
- **Existing Tests:** Check `tests/` directory for any existing unit/integration tests

---

## If All Tests Pass

**v1.0 is PRODUCTION-READY! 🎉**

**Next Steps:**
1. Update version to v1.0.0 in relevant files
2. Create CHANGELOG.md documenting all features
3. Update README.md with setup instructions
4. Tag release: `git tag v1.0.0`
5. Push to GitHub: `git push origin v1.0.0`
6. Create GitHub Release with Windows .exe (if CI/CD ready)
7. Announce Pulse v1.0 is live!

**Congratulations:** You've built a production-grade AI coding assistant for PLC programming.
