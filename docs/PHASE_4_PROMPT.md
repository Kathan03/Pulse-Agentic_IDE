# Pulse IDE - Phase 4: UI Fixes & Polish

## Context
Pulse is a desktop IDE for PLC coding with AI assistance. **Read CLAUDE.md for full architecture and requirements.**

**Current Problem:** UI has several bugs that hurt professional feel:
1. Sidebar doesn't scroll (file tree cut off)
2. Menu bar invisible (gray bar shows but no text)
3. File tree is flat list (should be VS Code-style tree with folders)
4. Model dropdown outdated (shows old models, missing GPT-5.x and Claude 4.5)
5. Feedback in wrong place (should be Help → Report Issue)

**Why This Matters:** Pulse should feel like VS Code, not a prototype. Users expect professional IDE experience. Current UI bugs break that perception.

---

## What to Do

### 1. Fix Sidebar Scrolling
**File:** `src/ui/sidebar.py`

**Problem:** File tree doesn't scroll when many files present. Likely missing `expand=True` on scrollable container.

**Requirements:**
- File tree should scroll vertically when content exceeds viewport
- Scrollbar should appear when needed
- Scrolling should be smooth (60fps)

**Why:** Users with large projects can't see all files without scrolling.

**How (Brief):** Find the file tree container (likely `ft.Column` or `ft.ListView`). Add `scroll=ft.ScrollMode.AUTO` and `expand=True`. Test with 50+ file project.

**Reference:** Search online for "Flet scrolling ListView" or "Flet Column scroll" - DO NOT make up Flet attributes.

---

### 2. Fix Menu Bar Visibility
**File:** `src/ui/menu_bar.py`

**Problem:** Menu bar shows as gray bar but no menu text (File, View, Settings, Help) visible.

**Requirements:**
- Menu bar should show: File | View | Settings | Help
- Clicking should open dropdown menus
- Text should be visible against background

**Why:** Users can't access Settings or Help without visible menu.

**How (Brief):** Check `ft.MenuBar` or `ft.AppBar` implementation. Likely issue: wrong text color, wrong background color, or missing menu items. Search Flet MenuBar docs online for correct usage.

**Reference:** Search "Flet MenuBar example" online - DO NOT guess Flet attributes.

---

### 3. Implement VS Code-Style File Tree
**File:** `src/ui/sidebar.py` or `src/ui/components/file_tree.py`

**Problem:** File tree is flat list. Should be expandable/collapsible tree with folders.

**Requirements:**
- Folders should have expand/collapse arrows (▶/▼)
- Clicking folder expands/collapses children
- Files nested under parent folders
- Visual hierarchy (indentation)
- Icons for folders vs files (optional but nice)

**Why:** VS Code has hierarchical tree. Flat list doesn't scale for real projects.

**How (Brief):** Use `ft.ExpansionTile` for folders. Recursively build tree structure. Each folder is ExpansionTile, each file is ListTile. Search Flet ExpansionTile docs for proper usage.

**Reference:** Search "Flet ExpansionTile recursive tree" online - DO NOT make up attributes.

---

### 4. Update Model Dropdown to 13 Models
**File:** `src/ui/components/settings_modal.py`

**Problem:** Model dropdown shows old models. Missing GPT-5.x and Claude 4.5 series.

**Requirements:**
- Update dropdown to show all 13 models (see CLAUDE.md → Supported LLM Models):
  - GPT-5.x: gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano, gpt-5.1-codex, gpt-5.2-pro
  - GPT-4.1.x: gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
  - Claude 4.5: claude-opus-4-5, claude-sonnet-4-5, claude-haiku-4-5
- Dropdown should allow user to select model per component (master_agent, crew_coder, autogen_auditor)

**Why:** Users need access to latest models. Old list blocks newer models.

**How (Brief):** Find model dropdown (likely `ft.Dropdown`). Update `options` list to include all 13 model IDs. Verify against CLAUDE.md model list.

---

### 5. Move Feedback to Help Menu
**File:** `src/ui/sidebar.py` and `src/ui/menu_bar.py`

**Problem:** Feedback section is in sidebar. Should be in Help → Report Issue menu item.

**Requirements:**
- Remove feedback section from sidebar
- Add "Report Issue" to Help menu
- Clicking opens GitHub issues page: `https://github.com/YOUR_REPO/pulse/issues/new`

**Why:** Feedback belongs in Help menu, not taking up sidebar space.

**How (Brief):** Delete feedback UI from sidebar. Add menu item to Help menu. Use `ft.Page.launch_url()` to open GitHub issues in browser.

---

### 6. Verify All Flet Attributes Against Official Docs
**Critical:** Before implementing, search Flet documentation online for each control used.

**Controls to Verify:**
- `ft.MenuBar` - Menu bar implementation
- `ft.ExpansionTile` - Folder tree
- `ft.Dropdown` - Model selection
- `ft.ListView` or `ft.Column` with `scroll` - Scrollable containers

**Why:** Previous implementations used made-up attributes that don't exist in Flet, causing errors.

**How:** For each Flet control, search "Flet [ControlName] documentation flet.dev" and verify all parameters/methods exist.

---

## Success Criteria

- [ ] Sidebar scrolls smoothly with large file lists
- [ ] Menu bar fully visible with File/View/Settings/Help menus
- [ ] File tree expands/collapses like VS Code (folders with ▶/▼)
- [ ] Model dropdown shows all 13 supported models
- [ ] Feedback removed from sidebar, accessible via Help → Report Issue
- [ ] All Flet attributes verified against official docs (no made-up attributes)
- [ ] UI feels professional (VS Code-level polish)

---

## Critical Warnings

⚠️ **DO NOT make up Flet attributes:** This has been a recurring issue. Search flet.dev documentation online before using ANY Flet control. Verify every parameter exists.

⚠️ **Test on real project:** Use workspace with 50+ files and nested folders to test scrolling and tree performance.

⚠️ **Responsive UI:** Ensure UI doesn't freeze during file tree rendering (use `ft.ProgressRing` if needed for large directories).

---

## Resources

- **Architecture Reference:** Read CLAUDE.md → UI Architecture (VS Code-Style)
- **Flet Docs:** Search online for:
  - "Flet MenuBar documentation" (flet.dev)
  - "Flet ExpansionTile example" (flet.dev)
  - "Flet Dropdown options" (flet.dev)
  - "Flet Column scroll" (flet.dev)
- **Existing UI Code:** Review `src/ui/editor.py` to see working tabbed interface pattern
- **Model List:** Check CLAUDE.md → Supported LLM Models section for complete list

---

**Implementation Approach:**
1. Start with sidebar scrolling (easiest fix)
2. Fix menu bar visibility (critical for Settings access)
3. Implement file tree with ExpansionTile (most complex)
4. Update model dropdown (simple list update)
5. Move feedback to Help menu (simple refactor)
6. Test all changes with real project (50+ files)
