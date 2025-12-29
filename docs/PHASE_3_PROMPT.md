# Pulse IDE - Phase 3: Web Search Tool

## Context
Pulse is a desktop IDE for PLC coding with AI assistance. **Read CLAUDE.md for full architecture and requirements.**

**Current Problem:** Master Agent cannot answer documentation questions. If user asks "How do I use Flet's ExpansionTile?" or "Show me Siemens TIA Portal timer examples", Master has no way to research current information.

**Why This Matters:** LLM training data is outdated (cutoff Jan 2025). Current library docs, PLC manuals, and Stack Overflow solutions are not in training data. Without web search, Master says "I don't know" for documentation questions.

---

## What to Do

### 1. Implement web_search Tool
**File:** `src/tools/web_search.py` (NEW FILE)

**Requirements:**
- Search the web using DuckDuckGo (free, no API key needed)
- Return list of results with title, URL, snippet
- Limit results to 5-10 (configurable)
- Truncate snippets to reasonable length (500 chars max)
- Handle errors gracefully (network failures, rate limits)

**Why:** DuckDuckGo is free and doesn't require API keys. Good enough for v1.0. Can upgrade to Tavily or Brave later.

**How (Brief):** Use `duckduckgo-search` Python library. Create async function `web_search(query, num_results=5)`. Return list of dicts with title/url/snippet. Add error handling for offline/rate limits.

**Reference:** Search online for "duckduckgo-search Python library usage" - DO NOT make up method names.

---

### 2. Register web_search in Tool Registry
**File:** `src/tools/registry.py`

**Requirements:**
- Add `web_search` to Tier 3 tools
- Define tool schema (name, description, parameters)
- Schema should specify `query` (string, required) and `num_results` (integer, optional)
- Description should explain when to use: "Search the web for documentation, Stack Overflow answers, or technical information"

**Why:** Master Agent needs to know this tool exists and how to use it via function calling.

**How (Brief):** Add web_search to tool schemas list. Import and register in ToolRegistry. Set `requires_approval=False` (web search is safe).

---

### 3. Update Mode-Based Prompts
**File:** `src/core/prompts.py`

**Requirements:**
- Update `AGENT_MODE_PROMPT` to mention web search capability
- Update `ASK_MODE_PROMPT` to mention web search capability
- Do NOT add to `PLAN_MODE_PROMPT` (planning should use existing knowledge, not web)

**Why:** Master Agent needs to know it can search web for documentation questions.

**How (Brief):** Add 1-2 sentences to Agent and Ask prompts: "You can search the web using web_search tool when workspace search returns no results or when user asks about external libraries/frameworks."

---

### 4. Configure Tool Access by Mode
**File:** `src/tools/registry.py` or `src/agents/master_graph.py`

**Requirements:**
- **Agent Mode:** Has access to web_search ✅
- **Ask Mode:** Has access to web_search ✅
- **Plan Mode:** NO access to web_search ❌

**Why:** Agent and Ask modes need current information. Plan mode should plan using existing knowledge without external lookups.

**How (Brief):** In `get_tools_for_mode()` function, include web_search for "agent" and "ask", exclude for "plan".

---

### 5. Test Web Search Integration
**Test Cases:**

**Test 1: Documentation Question (Ask Mode)**
```
Mode: Ask
User: "How do I use Flet's ExpansionTile widget?"

Expected:
- Master calls web_search("Flet ExpansionTile documentation")
- Receives results from flet.dev
- Responds with usage explanation + source links
```

**Test 2: PLC Documentation**
```
Mode: Agent
User: "Show me Siemens TIA Portal timer examples"

Expected:
- Master calls web_search("Siemens TIA Portal TON timer IEC 61131-3 example")
- Finds Siemens docs/tutorials
- Responds with timer syntax + examples + source URLs
```

**Test 3: Offline Graceful Degradation**
```
Setup: Disconnect internet
User: "How do I use pandas DataFrame?"

Expected:
- Master attempts web_search
- Receives network error
- Falls back to training data knowledge
- Responds: "I couldn't reach the internet. Based on my training, here's how pandas DataFrames work..."
```

---

## Success Criteria

- [ ] `src/tools/web_search.py` implemented with DuckDuckGo
- [ ] web_search registered in ToolRegistry (Tier 3)
- [ ] Tool schema defined for web_search
- [ ] Agent/Ask mode prompts mention web search capability
- [ ] web_search available in Agent and Ask modes, NOT in Plan mode
- [ ] Documentation questions answered with source links
- [ ] Graceful error handling when offline
- [ ] No regression from Phase 1 & 2

---

## Critical Warnings

⚠️ **Do NOT make up duckduckgo-search attributes:** Search the official library docs online before using. Verify method names and parameters.

⚠️ **Install dependency:** Add `duckduckgo-search` to `requirements.txt`.

⚠️ **Rate limiting:** DuckDuckGo is IP-based rate limited. If search fails with rate limit error, return graceful message to user.

⚠️ **Source attribution:** Always include URLs in results so user can verify information.

---

## Resources

- **Architecture Reference:** Read CLAUDE.md → Tool Belt Tier 3, Mode-Based Behavior
- **Library Docs:** Search online for "duckduckgo-search Python library GitHub"
- **Existing Tools:** Review `src/tools/rag.py` (search_workspace) for similar search pattern
- **Tool Registry:** Check `src/tools/registry.py` for tool registration pattern

---

**Implementation Approach:**
1. Install `duckduckgo-search` library
2. Create `web_search.py` with basic search function
3. Test search function in isolation (run manually)
4. Register in ToolRegistry with schema
5. Update prompts
6. Test end-to-end (user question → web search → answer with links)
