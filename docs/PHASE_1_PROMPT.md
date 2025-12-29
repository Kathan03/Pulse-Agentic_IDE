# Pulse IDE - Phase 1: LLM Integration

## Context
Pulse is a desktop IDE for PLC coding with AI assistance. **Read CLAUDE.md for full architecture and requirements.**

**Current Problem:** `call_llm_stub()` in `src/agents/master_graph.py` uses keyword matching instead of real LLMs. This blocks all agent functionality.

**Why This Matters:** Without real LLM integration, Master Agent cannot understand requests, call tools via function calling, or generate code. Pulse is currently a shell with no brain.

---

## What to Do

### 1. Create LLM Client Abstraction
**File:** `src/core/llm_client.py`

**Requirements:**
- Support OpenAI (GPT-5.x, GPT-4.1.x) and Anthropic (Claude 4.5 series)
- Implement function calling for both providers
- Load API keys from platformdirs config (see `src/core/settings.py`)
- Handle errors gracefully (invalid keys, network failures, timeouts)
- Return structured responses with tool calls

**Why:** Master Agent needs a unified interface to call different LLM providers without knowing provider-specific details.

**How (Brief):** Create `LLMClient` class with `generate()` method. Use `openai` and `anthropic` Python SDKs. Map tool schemas to provider-specific formats.

**Reference:** You can search OpenAI and Anthropic API docs online for function calling examples.

---

### 2. Create Mode-Based System Prompts
**File:** `src/core/prompts.py`

**Requirements:**
- `AGENT_MODE_PROMPT` - Full tool access, can modify files and run commands
- `ASK_MODE_PROMPT` - Read-only, uses search_workspace and web_search
- `PLAN_MODE_PROMPT` - Planning only, no execution

**Why:** Same Master Agent behaves differently based on mode. Tool access + prompt changes = different behavior.

**How (Brief):** Define string constants. Agent mode mentions all tools. Ask mode restricts to search only. Plan mode focuses on creating implementation plans.

**PLC Enhancement:** Add `PLC_ENHANCEMENT` prompt snippet that gets appended when Master Agent detects `.st` files during tool usage (dynamic detection, not upfront).

---

### 3. Define Tool Schemas
**File:** `src/tools/registry.py` or new `src/tools/schemas.py`

**Requirements:**
- JSON schemas for all tools: `manage_file_ops`, `apply_patch`, `search_workspace`, `run_terminal_cmd`, `web_search`
- Follow OpenAI function calling format (name, description, parameters)
- Clear parameter descriptions so LLM knows how to use each tool

**Why:** LLM needs structured schemas to know what tools exist and how to call them via function calling.

**How (Brief):** Create list of tool schema dicts. Each has `name`, `description`, `parameters` (with `type`, `properties`, `required`).

---

### 4. Replace Stub with Real LLM
**File:** `src/agents/master_graph.py`

**Requirements:**
- Delete `call_llm_stub()` function entirely
- Import `LLMClient` from `src/core/llm_client.py`
- Load model name from state's settings snapshot
- Pass mode-based system prompt from `src/core/prompts.py`
- Pass tool schemas to LLM
- Parse LLM response for tool calls
- Execute tools and loop back to LLM with results

**Why:** This is the critical connection - Master Agent can now use real intelligence to decide which tools to call.

**How (Brief):** In `master_agent_node()`, instantiate LLMClient, call `generate()` with system prompt + tool schemas, parse response for `tool_calls`, invoke tools via ToolRegistry, append results to conversation, loop until LLM returns final answer.

---

### 5. Test End-to-End Flow
**Requirements:**
- Launch Pulse IDE
- Enter test request: "Create a hello world Python function"
- Verify Master Agent calls LLM (GPT or Claude based on settings)
- Verify LLM uses `apply_patch` tool via function calling
- Verify patch preview appears
- Approve patch
- Verify file created successfully

**Why:** Proves LLM integration works end-to-end.

---

## Success Criteria

- [ ] LLMClient supports OpenAI + Anthropic with function calling
- [ ] Mode-based prompts defined (Agent/Ask/Plan)
- [ ] Tool schemas defined for all tools
- [ ] `call_llm_stub()` deleted, replaced with real LLM calls
- [ ] Master Agent can call tools via function calling
- [ ] End-to-end test passes (user request → LLM → tool → result)
- [ ] No stub code remaining in master_graph.py

---

## Critical Warnings

⚠️ **Do NOT make up framework attributes:** When using `openai` or `anthropic` SDKs, search their official documentation online. Do not guess method names or parameters.

⚠️ **Error Handling:** Invalid API keys should show clear error to user ("Invalid API key. Please configure in Settings."), not crash.

⚠️ **Default Models:** Do NOT change defaults in `src/core/settings.py`. Keep `gpt-5-mini`, `gpt-5-nano` as-is.

---

## Resources

- **Architecture Reference:** Read CLAUDE.md for hub-and-spoke pattern, tool belt structure
- **Online Docs:** Search for "OpenAI function calling API 2025" and "Anthropic Claude tool use 2025"
- **Existing Code:** Review `src/agents/runtime.py` to see how Master Agent is invoked
- **Tool Registry:** Check `src/tools/registry.py` for existing tool registration pattern

---

**Implementation Approach:** Start with LLMClient (easiest to test in isolation), then prompts, then schemas, finally integrate into master_graph.py. Test incrementally.
