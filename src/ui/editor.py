"""
Tabbed Editor Manager Component for Pulse IDE.

Provides a VS Code-like tabbed interface for editing multiple files and the agent chat.
"""

import flet as ft
from pathlib import Path
from src.ui.theme import VSCodeColors, Fonts, Spacing, create_logo_image
from src.ui.log_panel import LogPanel
from src.ui.components.settings_page import SettingsPage


class EditorManager:
    """
    Tabbed editor manager component.

    Features:
    - Tabbed interface for multiple files
    - Dynamic Pulse Agent tab (opened on demand)
    - File tabs with close buttons
    - Welcome screen when no tabs are open
    """

    def __init__(self, log_panel=None, file_manager=None, dirty_callback=None, query_handler=None):
        """
        Initialize the EditorManager.

        Args:
            log_panel: Reference to the LogPanel template for creating Pulse Agent tabs
            file_manager: Reference to FileManager for secure file operations
            dirty_callback: Callback function (file_path, is_dirty) to notify sidebar of dirty state
            query_handler: Callback function (user_input) to handle agent queries
        """
        self.log_panel_template = log_panel  # Template for creating new log panels
        self.file_manager = file_manager
        self.query_handler = query_handler  # Handler for agent queries
        self.tabs_control = None
        self.welcome_screen = None
        self.open_files = {}  # Map of file_path -> tab_index
        self.tab_editors = {}  # Map of tab_index -> editor TextField
        self.agent_tabs = {}  # Map of tab_index -> log_panel instance
        self.agent_session_counter = 0  # Counter for agent session numbering
        self.current_mode = "Agent Mode"  # Track current agent mode
        self.dirty_files = set()  # Set of file paths with unsaved changes
        self.dirty_callback = dirty_callback  # Callback to notify sidebar of dirty state
        self.original_contents = {}  # Map of file_path -> original content for dirty tracking
        self.container = self._build()

    def _build(self):
        """Build the tabbed editor UI component with VS Code styling."""
        # Create welcome screen
        self.welcome_screen = self._create_welcome_screen()

        # Create the tabs control (empty initially)
        self.tabs_control = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[],
            expand=True,
            on_change=self._on_tab_changed,
            indicator_color=VSCodeColors.TAB_ACTIVE_BORDER,
            label_color=VSCodeColors.TAB_ACTIVE_FOREGROUND,
            unselected_label_color=VSCodeColors.TAB_INACTIVE_FOREGROUND,
            visible=False,  # Hidden when no tabs
        )

        # Container that shows either welcome screen or tabs
        return ft.Container(
            content=ft.Stack(
                controls=[
                    self.welcome_screen,
                    self.tabs_control,
                ],
            ),
            expand=True,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
        )

    def _create_welcome_screen(self):
        """Create the welcome screen shown when no files are open."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.DESCRIPTION_OUTLINED,
                        size=64,
                        color=VSCodeColors.EDITOR_LINE_NUMBER,
                    ),
                    ft.Text(
                        "Please select a file to view",
                        size=Fonts.FONT_SIZE_LARGE,
                        color=VSCodeColors.EDITOR_FOREGROUND,
                        weight=ft.FontWeight.W_300,
                    ),
                    ft.Container(height=20),
                    ft.Text(
                        "Open a file from the workspace or start a Pulse Agent session",
                        size=Fonts.FONT_SIZE_SMALL,
                        color=VSCodeColors.EDITOR_LINE_NUMBER,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
        )

    def _update_visibility(self):
        """Update visibility of welcome screen vs tabs."""
        has_tabs = len(self.tabs_control.tabs) > 0
        self.welcome_screen.visible = not has_tabs
        self.tabs_control.visible = has_tabs

        if self.container.page:
            self.welcome_screen.update()
            self.tabs_control.update()

    def get_control(self):
        """Get the editor manager control for adding to the page."""
        return self.container

    def _handle_theme_change(self, theme_name: str):
        """Handle instant theme change by reloading the page."""
        print(f"[INFO] Theme changed to {theme_name}, triggering page reload...")
        if self.container.page:
            # Force page update to apply new theme colors
            self.container.page.update()
            print("[INFO] Page updated with new theme")

    def open_settings_page(self):
        """Open the Pulse Settings page as a new tab."""
        print("[DEBUG] EditorManager.open_settings_page() called")

        # Check if settings tab already exists
        for idx, tab in enumerate(self.tabs_control.tabs):
            # Check both old text format and new tab_content format
            is_settings = False
            if hasattr(tab, 'text') and tab.text and "Pulse Settings" in str(tab.text):
                is_settings = True
            elif hasattr(tab, 'tab_content') and tab.tab_content:
                # Check if any control in tab_content contains "Pulse Settings"
                if hasattr(tab.tab_content, 'controls'):
                    is_settings = any(
                        isinstance(c, ft.Text) and "Pulse Settings" in c.value
                        for c in tab.tab_content.controls
                    )

            if is_settings:
                # Settings tab already exists, switch to it
                print(f"[DEBUG] Settings tab already exists at index {idx}, switching to it")
                self.tabs_control.selected_index = idx

                # Show tabs control and hide welcome screen
                self.tabs_control.visible = True
                if self.welcome_screen:
                    self.welcome_screen.visible = False

                # Update the entire container to ensure visibility
                if self.tabs_control.page:
                    self.container.update()
                    print("[DEBUG] Container updated, settings tab should now be visible")
                return

        print("[DEBUG] Creating new settings page")
        # Create new settings page
        try:
            # Pass theme change callback to enable instant theme updates
            settings_page = SettingsPage(on_theme_change=self._handle_theme_change)
            print("[DEBUG] SettingsPage created successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create SettingsPage: {e}")
            import traceback
            traceback.print_exc()
            return

        # Create close button for settings tab
        def close_settings_tab(e):
            # Find and close settings tab
            for idx, tab in enumerate(self.tabs_control.tabs):
                if hasattr(tab, 'tab_content') and any(
                    isinstance(c, ft.Text) and "Pulse Settings" in c.value
                    for c in (tab.tab_content.controls if hasattr(tab.tab_content, 'controls') else [])
                ):
                    self.tabs_control.tabs.pop(idx)
                    # Switch to previous tab or Pulse Chat
                    if self.tabs_control.tabs:
                        self.tabs_control.selected_index = max(0, idx - 1)
                    if self.tabs_control.page:
                        self.container.update()
                    return

        close_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=14,
            tooltip="Close settings",
            on_click=close_settings_tab,
            icon_color=VSCodeColors.TAB_INACTIVE_FOREGROUND,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.HOVERED: VSCodeColors.BUTTON_SECONDARY_HOVER,
                    ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                },
                overlay_color=VSCodeColors.ERROR_FOREGROUND,
                padding=ft.padding.all(2),
            ),
        )

        # Create tab label with close button
        tab_label = ft.Row(
            controls=[
                ft.Icon(ft.Icons.SETTINGS, size=16),
                ft.Text("Pulse Settings", size=13),
                close_button,
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        )

        # Create tab with custom label and close button
        new_tab = ft.Tab(
            tab_content=tab_label,  # Custom label with close button
            content=settings_page.get_control(),
        )

        # Add tab
        self.tabs_control.tabs.append(new_tab)
        self.tabs_control.selected_index = len(self.tabs_control.tabs) - 1
        print(f"[DEBUG] Settings tab added at index {self.tabs_control.selected_index}")

        # Show tabs control and hide welcome screen
        self.tabs_control.visible = True
        if self.welcome_screen:
            self.welcome_screen.visible = False

        # Update UI
        if self.tabs_control.page:
            self.container.update()
            print("[DEBUG] UI updated successfully")
        else:
            print("[WARNING] tabs_control.page is None, cannot update")

    def open_agent(self, mode="Agent Mode"):
        """
        Open a new Pulse Agent tab (supports multiple sessions).

        Args:
            mode: The agent mode (Agent Mode, Plan Mode, or Ask Mode)
        """
        self.current_mode = mode
        self.agent_session_counter += 1

        # Create a new log panel instance for this session
        def handle_user_input(text: str):
            """Handle user input from this agent session."""
            print(f"[DEBUG] Agent tab handler called with: {text}")
            # Call the actual query handler from app.py, passing the mounted LogPanel
            # (LogPanel already added user message in _handle_submit)
            if self.query_handler:
                print(f"[DEBUG] Calling query_handler from agent tab with new_log_panel")
                self.query_handler(text, new_log_panel)  # ✅ Pass the mounted tab's LogPanel
            else:
                print(f"[ERROR] No query_handler registered in EditorManager")
                new_log_panel.add_log("❌ Query handler not configured", "error")

        new_log_panel = LogPanel(on_submit=handle_user_input)

        # Create new agent tab with session number
        session_label = f" (Session {self.agent_session_counter})" if self.agent_session_counter > 1 else ""
        tab_title = f"Pulse Agent - {mode}{session_label}"

        # Create logo image for tab icon
        tab_logo = create_logo_image(width=42, height=42)

        # Create close button for this tab
        # Store log panel reference to find the tab index dynamically
        def close_this_agent_tab(e):
            # Find the current index of this agent tab by searching for the log panel
            for idx, panel in self.agent_tabs.items():
                if panel == new_log_panel:
                    self.close_tab_by_index(idx)
                    break

        close_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=14,
            tooltip="Close tab",
            on_click=close_this_agent_tab,
            icon_color=VSCodeColors.TAB_INACTIVE_FOREGROUND,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.HOVERED: VSCodeColors.BUTTON_SECONDARY_HOVER,
                    ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                },
                overlay_color=VSCodeColors.ERROR_FOREGROUND,
                padding=ft.padding.all(2),
            ),
        )

        # Create custom tab label with title and close button next to it
        tab_label = ft.Row(
            controls=[
                ft.Icon(name=tab_logo, size=16),
                ft.Text(tab_title, size=13),
                close_button,
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        )

        # Create tab content without close button (it's now in the tab label)
        tab_content = ft.Container(
            content=new_log_panel.get_control(),
            expand=True,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
            padding=Spacing.PADDING_MEDIUM,
        )

        agent_tab = ft.Tab(
            tab_content=tab_label,  # Custom label with close button
            content=tab_content,
        )

        # Add tab at the beginning
        self.tabs_control.tabs.insert(0, agent_tab)
        new_tab_index = 0

        # Update all file tab indices (shift them by 1)
        files_to_update = list(self.open_files.items())
        for file_path, old_index in files_to_update:
            self.open_files[file_path] = old_index + 1

        # Update tab_editors indices
        editors_to_update = list(self.tab_editors.items())
        self.tab_editors = {}
        for old_index, editor in editors_to_update:
            self.tab_editors[old_index + 1] = editor

        # Update agent_tabs indices (shift all existing agent tabs by 1)
        agent_tabs_to_update = list(self.agent_tabs.items())
        self.agent_tabs = {}
        for old_index, log_panel in agent_tabs_to_update:
            self.agent_tabs[old_index + 1] = log_panel
        self.agent_tabs[new_tab_index] = new_log_panel  # Add the new one at index 0

        # Switch to new agent tab
        self.tabs_control.selected_index = 0
        self._update_visibility()

        if self.tabs_control.page:
            self.tabs_control.update()

    def open_file(self, file_path: str):
        """
        Open a file in a new tab or switch to existing tab.

        Args:
            file_path: Path to the file to open
        """
        # Check if file is already open
        if file_path in self.open_files:
            # Switch to existing tab
            tab_index = self.open_files[file_path]
            self.tabs_control.selected_index = tab_index
            self.tabs_control.update()
            return

        # Read file content using FileManager
        try:
            path = Path(file_path)
            if self.file_manager:
                # Use FileManager for secure, validated file reads
                content = self.file_manager.read_file(str(path))
            else:
                # Fallback to direct file I/O if FileManager not available
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            content = f"Error loading file: {str(e)}"

        # Store original content for dirty state tracking
        normalized_path = str(path.resolve())
        self.original_contents[normalized_path] = content

        # Create onChange handler for dirty state tracking
        def on_text_changed(e):
            """Handle text changes in the editor to track dirty state."""
            current_content = e.control.value
            # Mark as dirty if content has changed from original
            if current_content != self.original_contents.get(normalized_path, ""):
                self._mark_file_dirty(file_path, True)
            else:
                self._mark_file_dirty(file_path, False)

        # Create editor for this file with VS Code styling
        editor = ft.TextField(
            value=content,
            multiline=True,
            min_lines=20,
            text_style=ft.TextStyle(font_family=Fonts.MONOSPACE_PRIMARY),
            expand=True,
            border=ft.InputBorder.NONE,
            text_size=Fonts.FONT_SIZE_NORMAL,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
            color=VSCodeColors.EDITOR_FOREGROUND,
            cursor_color=VSCodeColors.EDITOR_CURSOR,
            selection_color=VSCodeColors.EDITOR_SELECTION_BACKGROUND,
            on_change=on_text_changed,
            on_submit=lambda _: None,  # Handle Enter key (no-op for multiline)
        )

        # Get filename for tab title
        filename = path.name

        # Determine file icon based on extension
        icon = self._get_file_icon(path.suffix)

        # Create close button for this file tab
        # Use the file_path to find and close the tab dynamically
        def close_this_file_tab(e):
            # Close by file path ensures we close the correct tab
            if e.control.page:
                e.control.page.overlay.clear()  # Clear any overlays
            self.close_file(file_path)
            if e.control.page:
                e.control.page.update()

        close_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=14,
            tooltip="Close file",
            on_click=close_this_file_tab,
            icon_color=VSCodeColors.TAB_INACTIVE_FOREGROUND,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.HOVERED: VSCodeColors.BUTTON_SECONDARY_HOVER,
                    ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                },
                overlay_color=VSCodeColors.ERROR_FOREGROUND,
                padding=ft.padding.all(2),
            ),
        )

        # Create custom tab label with filename and close button next to it
        tab_label = ft.Row(
            controls=[
                ft.Icon(name=icon, size=16),
                ft.Text(filename, size=13),
                close_button,
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        )

        # Create tab content without close button (it's now in the tab label)
        tab_content = ft.Container(
            content=editor,
            expand=True,
            padding=Spacing.PADDING_MEDIUM,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
        )

        # Create the tab with custom label
        new_tab = ft.Tab(
            tab_content=tab_label,  # Custom label with close button
            content=tab_content,
        )

        # Add tab to tabs control
        self.tabs_control.tabs.append(new_tab)
        tab_index = len(self.tabs_control.tabs) - 1

        # Track the file and editor
        self.open_files[file_path] = tab_index
        self.tab_editors[tab_index] = editor

        # Switch to the new tab
        self.tabs_control.selected_index = tab_index

        # Update visibility
        self._update_visibility()

        # Update UI
        if self.tabs_control.page:
            self.tabs_control.update()

    def _close_file_click(self, e, file_path):
        """Handle close button click on file tab."""
        e.control.page.overlay.append(
            ft.SnackBar(
                content=ft.Text(f"Tab close functionality: Use Ctrl+W or right-click menu"),
                action="OK",
            )
        )
        # For now, just close the file
        self.close_file(file_path)

    def close_file(self, file_path: str):
        """
        Close a file tab.

        Args:
            file_path: Path to the file to close
        """
        if file_path not in self.open_files:
            return

        # Check if file is dirty (has unsaved changes)
        normalized_path = str(Path(file_path).resolve())
        if normalized_path in self.dirty_files:
            # Show confirmation dialog
            filename = Path(file_path).name
            self._show_unsaved_changes_dialog(file_path, filename)
            return

        # Proceed with closing
        self._perform_close(file_path)

    def _perform_close(self, file_path: str):
        """
        Actually perform the file close operation.

        Args:
            file_path: Path to the file to close
        """
        if file_path not in self.open_files:
            return

        tab_index = self.open_files[file_path]

        # Clear dirty state
        normalized_path = str(Path(file_path).resolve())
        self.dirty_files.discard(normalized_path)
        if normalized_path in self.original_contents:
            del self.original_contents[normalized_path]

        # Notify sidebar to clear dirty indicator
        if self.dirty_callback:
            self.dirty_callback(normalized_path, False)

        # Remove the tab
        del self.tabs_control.tabs[tab_index]

        # Remove from tracking
        del self.open_files[file_path]
        if tab_index in self.tab_editors:
            del self.tab_editors[tab_index]

        # Update indices for files that were after this one
        files_to_update = [(fp, idx) for fp, idx in self.open_files.items() if idx > tab_index]
        for fp, idx in files_to_update:
            self.open_files[fp] = idx - 1

        # Update tab_editors indices
        editors_to_update = [(idx, editor) for idx, editor in self.tab_editors.items() if idx > tab_index]
        for idx, editor in editors_to_update:
            del self.tab_editors[idx]
            self.tab_editors[idx - 1] = editor

        # Update agent_tabs indices
        agent_tabs_to_update = [(idx, log_panel) for idx, log_panel in self.agent_tabs.items() if idx > tab_index]
        for idx, log_panel in agent_tabs_to_update:
            del self.agent_tabs[idx]
            self.agent_tabs[idx - 1] = log_panel

        # Switch to previous tab or first tab
        if self.tabs_control.selected_index >= len(self.tabs_control.tabs):
            self.tabs_control.selected_index = max(0, len(self.tabs_control.tabs) - 1)

        # Update visibility
        self._update_visibility()

        # Update UI
        if self.tabs_control.page:
            self.tabs_control.update()

    def _show_unsaved_changes_dialog(self, file_path: str, filename: str):
        """
        Show a confirmation dialog for unsaved changes.

        Args:
            file_path: Path to the file
            filename: Name of the file to display
        """
        def handle_save(e):
            # Save the file
            self.save_current_file()
            # Close the dialog
            dialog.open = False
            dialog.page.update()
            # Close the file
            self._perform_close(file_path)

        def handle_dont_save(e):
            # Close the dialog
            dialog.open = False
            dialog.page.update()
            # Close the file without saving
            self._perform_close(file_path)

        def handle_cancel(e):
            # Just close the dialog
            dialog.open = False
            dialog.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Unsaved Changes"),
            content=ft.Text(f"Do you want to save the changes to '{filename}'?"),
            actions=[
                ft.TextButton("Save", on_click=handle_save),
                ft.TextButton("Don't Save", on_click=handle_dont_save),
                ft.TextButton("Cancel", on_click=handle_cancel),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Add dialog to page overlay and show it
        if self.container.page:
            self.container.page.overlay.append(dialog)
            dialog.open = True
            self.container.page.update()

    def close_tab_by_index(self, tab_index: int):
        """
        Close a tab by its index (works for both file tabs and agent tabs).

        Args:
            tab_index: Index of the tab to close
        """
        # Validate tab index
        if tab_index < 0 or tab_index >= len(self.tabs_control.tabs):
            print(f"[WARNING] Invalid tab index: {tab_index}")
            return

        # Check if this is an agent tab
        if tab_index in self.agent_tabs:
            print(f"[DEBUG] Closing agent tab at index {tab_index}")

            # Step 1: Remove the tab from UI
            del self.tabs_control.tabs[tab_index]

            # Step 2: Create new dictionaries with updated indices
            # This prevents issues with concurrent modifications
            new_agent_tabs = {}
            new_tab_editors = {}
            new_open_files = {}

            # Update agent_tabs: remove current, shift down indices after it
            for idx, log_panel in self.agent_tabs.items():
                if idx < tab_index:
                    new_agent_tabs[idx] = log_panel
                elif idx > tab_index:
                    new_agent_tabs[idx - 1] = log_panel
                # Skip idx == tab_index (it's being deleted)

            # Update tab_editors: shift down indices after deleted tab
            for idx, editor in self.tab_editors.items():
                if idx < tab_index:
                    new_tab_editors[idx] = editor
                elif idx > tab_index:
                    new_tab_editors[idx - 1] = editor

            # Update open_files: shift down indices after deleted tab
            for fp, idx in self.open_files.items():
                if idx < tab_index:
                    new_open_files[fp] = idx
                elif idx > tab_index:
                    new_open_files[fp] = idx - 1
                # Skip idx == tab_index if it exists

            # Replace the dictionaries
            self.agent_tabs = new_agent_tabs
            self.tab_editors = new_tab_editors
            self.open_files = new_open_files

            # Update selected index if needed
            if self.tabs_control.selected_index >= len(self.tabs_control.tabs):
                self.tabs_control.selected_index = max(0, len(self.tabs_control.tabs) - 1)

            # Update visibility and UI
            self._update_visibility()
            if self.tabs_control.page:
                self.tabs_control.update()

            print(f"[DEBUG] Agent tab closed. Remaining tabs: {len(self.tabs_control.tabs)}")
            return

        # Find the file path for this tab index
        file_path = None
        for fp, idx in self.open_files.items():
            if idx == tab_index:
                file_path = fp
                break

        if file_path:
            self.close_file(file_path)

    def _on_tab_changed(self, e):
        """Handle tab change event."""
        # Optional: Add logic when switching tabs
        pass

    def get_current_file_content(self):
        """
        Get the content of the currently active file.

        Returns:
            Content of the current file, or None if on Pulse Agent tab or no tab
        """
        current_index = self.tabs_control.selected_index

        # Skip if this is an agent tab
        if current_index in self.agent_tabs:
            return None

        if current_index in self.tab_editors:
            return self.tab_editors[current_index].value

        return None

    def save_current_file(self):
        """Save the currently active file."""
        current_index = self.tabs_control.selected_index

        # Skip if this is an agent tab
        if current_index in self.agent_tabs:
            return

        # Find the file path for this tab
        file_path = None
        for fp, idx in self.open_files.items():
            if idx == current_index:
                file_path = fp
                break

        if not file_path or current_index not in self.tab_editors:
            return

        # Get content and save using FileManager
        content = self.tab_editors[current_index].value

        try:
            if self.file_manager:
                # Use FileManager for atomic, secure writes
                self.file_manager.write_file(file_path, content)
            else:
                # Fallback to direct file I/O if FileManager not available
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            print(f"Saved: {file_path}")

            # Update the original content to the newly saved content
            normalized_path = str(Path(file_path).resolve())
            self.original_contents[normalized_path] = content

            # Mark file as clean after successful save
            self._mark_file_dirty(file_path, False)
        except Exception as e:
            print(f"Error saving file {file_path}: {e}")

    def _mark_file_dirty(self, file_path: str, is_dirty: bool):
        """
        Mark a file as dirty (unsaved changes) or clean.

        Args:
            file_path: Path to the file
            is_dirty: True to mark as dirty, False to mark as clean
        """
        # Normalize the file path
        normalized_path = str(Path(file_path).resolve())

        # Update dirty_files set
        if is_dirty:
            self.dirty_files.add(normalized_path)
        else:
            self.dirty_files.discard(normalized_path)

        # Update tab title
        self._update_tab_title(normalized_path, is_dirty)

        # Notify sidebar via callback
        if self.dirty_callback:
            self.dirty_callback(normalized_path, is_dirty)

    def _update_tab_title(self, file_path: str, is_dirty: bool):
        """
        Update the tab title to show dirty state (with asterisk).

        Args:
            file_path: Path to the file
            is_dirty: True to add asterisk, False to remove it
        """
        # Find the tab index for this file
        if file_path not in self.open_files:
            return

        tab_index = self.open_files[file_path]
        if tab_index >= len(self.tabs_control.tabs):
            return

        # Get the tab
        tab = self.tabs_control.tabs[tab_index]

        # Get the filename from the path
        filename = Path(file_path).name

        # Update the tab text
        if is_dirty:
            tab.text = f"{filename} *"
        else:
            tab.text = filename

        # Update UI if page is available
        if self.tabs_control.page:
            self.tabs_control.update()

    def _get_file_icon(self, extension: str):
        """
        Get appropriate icon for file type.

        Args:
            extension: File extension (e.g., '.py', '.st')

        Returns:
            Flet icon constant
        """
        icon_map = {
            '.st': ft.Icons.CODE,           # PLC Structured Text
            '.py': ft.Icons.CODE,           # Python
            '.md': ft.Icons.DESCRIPTION,    # Markdown
            '.txt': ft.Icons.TEXT_SNIPPET,  # Text
            '.json': ft.Icons.DATA_OBJECT,  # JSON
        }

        return icon_map.get(extension.lower(), ft.Icons.INSERT_DRIVE_FILE)

    def update_chat_log(self, message: str, log_type: str = "agent"):
        """
        Update the chat log in the currently active agent tab.
        Used by background threads to stream agent responses to the UI.

        Args:
            message: Message to display in the chat
            log_type: Type of log entry ("info", "success", "warning", "error", "agent")
        """
        current_index = self.tabs_control.selected_index

        # Check if current tab is an agent tab
        if current_index in self.agent_tabs:
            agent_log_panel = self.agent_tabs[current_index]
            agent_log_panel.add_log(message, log_type)
        else:
            # If not on an agent tab, try to find the most recent agent tab
            if self.agent_tabs:
                most_recent_agent_index = min(self.agent_tabs.keys())
                agent_log_panel = self.agent_tabs[most_recent_agent_index]
                agent_log_panel.add_log(message, log_type)

    def update_chat_stream(self, message: str):
        """
        Stream a message to the chat interface.
        Alias for update_chat_log with default "agent" type.

        Args:
            message: Message to stream to the chat
        """
        self.update_chat_log(message, "agent")

    def reload_tabs(self):
        """
        Reload all open file tabs from disk.
        Used after agents modify files to show the updated content.
        Preserves dirty state for files with unsaved user changes.
        """
        for file_path, tab_index in list(self.open_files.items()):
            # Skip if tab doesn't have an editor (shouldn't happen, but defensive)
            if tab_index not in self.tab_editors:
                continue

            editor = self.tab_editors[tab_index]
            normalized_path = str(Path(file_path).resolve())

            try:
                # Re-read file content from disk
                if self.file_manager:
                    new_content = self.file_manager.read_file(file_path)
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        new_content = f.read()

                # Check if file has unsaved user changes
                if normalized_path in self.dirty_files:
                    # File has unsaved changes - ask user if they want to reload
                    # For now, skip reloading files with unsaved changes
                    print(f"Skipping reload of {file_path} - has unsaved changes")
                    continue

                # Update editor content
                editor.value = new_content

                # Update original content for dirty tracking
                self.original_contents[normalized_path] = new_content

                # Update UI if page is available
                if editor.page:
                    editor.update()

                print(f"Reloaded: {file_path}")

            except Exception as e:
                print(f"Error reloading file {file_path}: {e}")
