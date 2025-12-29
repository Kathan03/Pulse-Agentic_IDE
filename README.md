
  You are a senior AI engineer implementing real LLM integration for Pulse IDE. The stub LLM (call_llm_stub) blocks all agent functionality - replace it with OpenAI + Anthropic clients supporting function calling. Follow docs/PHASE_1_PROMPT.md for requirements; CLAUDE.md has architecture context.

  ---
  Phase 2: Architecture Cleanup

  You are a software architect refactoring Pulse to match Claude Code's proven architecture. DELETE src/core/context_manager.py entirely - it causes static classification that breaks hybrid projects (Python+PLC+JS). Follow docs/PHASE_2_PROMPT.md to implement dynamic workspace discovery via tools instead.

  ---
  Phase 3: Web Search Tool

  You are a backend engineer adding web search to Pulse's Tool Belt. Master Agent currently can't answer documentation questions - add DuckDuckGo integration (Tier 3) so it can research Flet docs, PLC manuals, Stack Overflow. Follow docs/PHASE_3_PROMPT.md for implementation.

  ---
  Phase 4: UI Fixes & Polish

  You are a UI/UX engineer fixing critical bugs in Pulse's Flet interface. Sidebar doesn't scroll, menu bar invisible, file tree is flat, model dropdown outdated - fix these to match VS Code quality. Follow docs/PHASE_4_PROMPT.md; verify all Flet attributes against official docs.

  ---
  Phase 5: Testing & Production Release

  You are a QA engineer validating Pulse v1.0 for production. Execute comprehensive end-to-end tests: LLM integration, mode switching (Agent/Ask/Plan), PLC code generation, approval gates. Follow docs/PHASE_5_PROMPT.md test suite; all criteria must pass before v1.0 release.

  #Issue
  1. Prompt changes needs to be done. The agent response are too inconsistent. And something completely different to the expected response. It is too focused towards PLC coding so its not doing any normal task
  2. Check if the master agent can really access all the tools.
  3. Check if agent ask for permission before editing anything. How is the UI to check the code changes? 
  4. UI issues
  5. Push on github
  6. Github actions CI/CD

