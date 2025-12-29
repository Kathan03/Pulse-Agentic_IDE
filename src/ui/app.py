"""
Pulse IDE - Main Flet Application (Phase 7: UI Heartbeat)

Entry point for the Flet-based desktop UI with:
- VS Code-style layout with menu bar
- Single-run lock (no concurrent agent runs)
- Async event streaming via UIBridge
- Approval modals for patches and terminal commands
- Settings UX via platformdirs
- Shutdown handler integration
"""

import flet as ft
import asyncio
import uuid
import atexit
from typing import Dict, Any, Optional
from pathlib import Path

# UI Components
from src.ui.sidebar import Sidebar
from src.ui.editor import EditorManager
from src.ui.log_panel import LogPanel
from src.ui.terminal import TerminalPanel
from src.ui.status_bar import StatusBar
from src.ui.menu_bar import MenuBar, create_about_dialog
from src.ui.components.resizable_splitter import VerticalSplitter, HorizontalSplitter
from src.ui.components.vibe_loader import VibeLoader, VibeStatusBar
from src.ui.components.settings_modal import SettingsModal
from src.ui.components.approval import show_patch_approval, show_terminal_approval
from src.ui.bridge import UIBridge, get_ui_bridge, UIEvent

# Theme
from src.ui.theme import VSCodeColors, Spacing

# Core
from src.core.file_manager import FileManager
from src.core.processes import cleanup_processes
from src.core.events import EventType

# Import Master Graph (Phase 3)
print("[DEBUG] Importing master graph...")
try:
    from src.agents.master_graph import create_master_graph
    from src.agents.state import create_initial_master_state
    from src.core.settings import get_settings_manager
    print("[DEBUG] Master graph imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import master graph: {e}")
    import traceback
    traceback.print_exc()
    create_master_graph = None


class PulseApp:
    """
    Main Pulse IDE Application Controller.

    Manages:
    - UI layout and components
    - Single-run lock enforcement
    - Event bridge for async streaming
    - Approval modal flow
    - Shutdown cleanup
    """

    def __init__(self, page: ft.Page):
        """Initialize Pulse IDE application."""
        self.page = page
        self.workspace_path = str(Path.cwd())

        # Single-run lock state
        self.is_running = False
        self.pending_approval: Optional[Dict[str, Any]] = None
        self.current_run_task: Optional[asyncio.Task] = None
        self.active_log_panel: Optional[LogPanel] = None  # Track currently running panel

        # UI Bridge for async events
        self.bridge = get_ui_bridge()

        # Master Graph (initialized lazily)
        self._master_graph = None

        # UI Components (initialized in _build_ui)
        self.menu_bar: Optional[MenuBar] = None
        self.sidebar: Optional[Sidebar] = None
        self.editor_manager: Optional[EditorManager] = None
        self.terminal: Optional[TerminalPanel] = None
        self.status_bar: Optional[StatusBar] = None
        self.vibe_loader: Optional[VibeLoader] = None
        self.vibe_status_bar: Optional[VibeStatusBar] = None
        self.settings_modal: Optional[SettingsModal] = None

        # File Manager
        try:
            self.file_manager = FileManager(base_path=self.workspace_path)
        except ValueError as e:
            print(f"[ERROR] FileManager init failed: {e}")
            self.file_manager = FileManager(base_path=".")

        # Terminal visibility state
        self._terminal_visible = True
        self._sidebar_visible = True

        # Container references for toggle visibility
        self._terminal_container: Optional[ft.Container] = None
        self._sidebar_container: Optional[ft.Container] = None

        # Build UI
        self._setup_page()
        self._build_ui()
        self._setup_bridge_callbacks()
        self._setup_shutdown_handler()

    def _setup_page(self):
        """Configure page settings."""
        self.page.title = "Pulse"  # Short title
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.bgcolor = VSCodeColors.EDITOR_BACKGROUND

        # Hide default title bar to use custom menu bar as title bar (VS Code style)
        self.page.window.title_bar_hidden = True
        self.page.window.title_bar_buttons_hidden = False  # Keep window controls

        # Set window icon to Pulse logo
        # CRITICAL: Windows requires .ICO format for window icons
        try:
            # Try ICO file first (required for Windows)
            icon_candidates = [
                Path("assets/pulse_icon_bg_062024.ico"),  # MUST be ICO for Windows
                Path("assets/pulse_icon_bg_062024_256.png"),
                Path("assets/pulse_icon_bg_223A47.ico"),
            ]
            icon_set = False
            for icon_path in icon_candidates:
                print(f"[DEBUG] Trying icon path: {icon_path} (exists: {icon_path.exists()})")
                if icon_path.exists():
                    self.page.window.icon = str(icon_path.absolute())
                    print(f"[INFO] Window icon set to: {icon_path.absolute()}")
                    icon_set = True
                    break
            if not icon_set:
                print("[WARNING] No suitable icon file found")
        except Exception as e:
            print(f"[WARNING] Could not set window icon: {e}")
            import traceback
            traceback.print_exc()

        # Keyboard shortcuts
        self.page.on_keyboard_event = self._on_keyboard_event

    def _build_ui(self):
        """Build the complete UI layout."""
        # Status bar
        self.status_bar = StatusBar()

        # Vibe loaders
        self.vibe_loader = VibeLoader()
        self.vibe_status_bar = VibeStatusBar()

        # Sidebar
        self.sidebar = Sidebar(editor_manager=None, file_manager=self.file_manager)

        # Editor manager reference holder
        editor_manager_ref = [None]

        # Query handler for agent interaction
        def handle_query(user_input: str, target_log_panel):
            """Handle user query - starts agent run with single-run lock."""
            self._handle_agent_query(user_input, target_log_panel)

        # Log panel template
        log_panel = LogPanel(on_submit=lambda text: print("[DEBUG] Template submit"))

        # Dirty state callback
        def handle_file_dirty_state(file_path: str, is_dirty: bool):
            self.sidebar.set_file_dirty(file_path, is_dirty)

        # Editor manager
        self.editor_manager = EditorManager(
            log_panel=log_panel,
            file_manager=self.file_manager,
            dirty_callback=handle_file_dirty_state,
            query_handler=handle_query
        )
        editor_manager_ref[0] = self.editor_manager
        self.sidebar.editor_manager = self.editor_manager

        # Mode change handler
        original_on_mode_changed = self.sidebar._on_mode_changed
        def on_mode_changed_with_updates(e):
            original_on_mode_changed(e)
        self.sidebar._on_mode_changed = on_mode_changed_with_updates

        # Terminal
        self.terminal = TerminalPanel(
            on_command=lambda cmd: None,
            workspace_path=self.workspace_path
        )

        # Menu bar
        self.menu_bar = MenuBar(
            on_open_workspace=self._handle_open_workspace,
            on_save_all=self._handle_save_all,
            on_exit=self._handle_exit,
            on_toggle_terminal=self._handle_toggle_terminal,
            on_toggle_sidebar=self._handle_toggle_sidebar,
            on_open_settings=self._handle_open_settings,
            on_about=self._handle_about,
            on_documentation=self._handle_documentation,
        )

        # Settings modal
        self.settings_modal = SettingsModal(self.page)

        # Create containers
        self._sidebar_container = ft.Container(
            width=250,
            bgcolor=VSCodeColors.SIDEBAR_BACKGROUND,
            content=self.sidebar.get_control(),
            visible=self._sidebar_visible,
        )

        self._terminal_container = ft.Container(
            height=200,
            bgcolor=VSCodeColors.PANEL_BACKGROUND,
            content=self.terminal.get_control(),
            visible=self._terminal_visible,
        )

        editor_container = ft.Container(
            expand=True,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
            content=self.editor_manager.get_control(),
        )

        # Splitters
        vertical_splitter = VerticalSplitter(
            left_container=self._sidebar_container,
            right_container=None,
            initial_left_width=250,
            min_width=150,
            max_width=500
        )

        horizontal_splitter = HorizontalSplitter(
            top_container=editor_container,
            bottom_container=self._terminal_container,
            initial_bottom_height=200,
            min_height=100,
            max_height=400
        )

        # Right column (editor + terminal)
        right_column = ft.Column(
            controls=[
                editor_container,
                horizontal_splitter.get_control(),
                self._terminal_container,
            ],
            spacing=0,
            expand=True,
        )

        # Main content row
        main_content = ft.Row(
            controls=[
                self._sidebar_container,
                vertical_splitter.get_control(),
                right_column,
            ],
            spacing=0,
            expand=True,
        )

        # Complete layout with menu bar
        complete_layout = ft.Column(
            controls=[
                self.menu_bar.get_control(),
                main_content,
                self.status_bar.get_control(),
            ],
            spacing=0,
            expand=True,
        )

        # Add to page
        self.page.add(complete_layout)

        # Initialize file picker for sidebar
        self.sidebar.initialize_file_picker(self.page)

        # Load current directory
        self.sidebar.load_directory(".", set_as_root=True)

    def _setup_bridge_callbacks(self):
        """Setup UIBridge callbacks for event handling."""
        self.bridge.set_vibe_callback(self._on_vibe_update)
        self.bridge.set_approval_callback(self._on_approval_request)
        self.bridge.set_run_complete_callback(self._on_run_complete)

    def _setup_shutdown_handler(self):
        """Setup shutdown handler for cleanup."""
        # Register cleanup on app exit
        atexit.register(self._cleanup)

        # Page close handler
        def on_page_close(e):
            self._cleanup()

        self.page.on_close = on_page_close

    def _cleanup(self):
        """Cleanup on app close."""
        print("[SHUTDOWN] Starting cleanup...")

        # Cancel active run
        if self.current_run_task and not self.current_run_task.done():
            print("[SHUTDOWN] Cancelling active run...")
            self.current_run_task.cancel()

        # Cleanup terminal processes
        if self.terminal:
            self.terminal.cleanup()

        # Cleanup registered processes
        try:
            report = cleanup_processes()
            print(f"[SHUTDOWN] Process cleanup: {report}")
        except Exception as e:
            print(f"[SHUTDOWN] Process cleanup error: {e}")

        print("[SHUTDOWN] Cleanup complete")

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def _on_keyboard_event(self, e: ft.KeyboardEvent):
        """Handle keyboard shortcuts."""
        key_lower = e.key.lower() if e.key else ""

        # Ctrl+S: Save current file
        if key_lower == "s" and (e.ctrl or e.meta):
            print("[KEYBOARD] Ctrl+S: Save file")
            self.editor_manager.save_current_file()
            self.page.update()

        # Ctrl+`: Toggle terminal
        elif key_lower == "`" and e.ctrl:
            print("[KEYBOARD] Ctrl+`: Toggle terminal")
            self._handle_toggle_terminal()

        # Ctrl+B: Toggle sidebar
        elif key_lower == "b" and e.ctrl:
            print("[KEYBOARD] Ctrl+B: Toggle sidebar")
            self._handle_toggle_sidebar()

        # Ctrl+,: Open settings
        elif key_lower == "," and e.ctrl:
            print("[KEYBOARD] Ctrl+,: Open settings")
            self._handle_open_settings("all")

    def _on_vibe_update(self, vibe: str):
        """Handle vibe status update from bridge."""
        # Update vibe in the currently running log panel
        if self.active_log_panel:
            self.active_log_panel.update_vibe(vibe)

    def _on_approval_request(self, approval_type: str, data: Dict[str, Any]):
        """Handle approval request from bridge."""
        self.pending_approval = {"type": approval_type, "data": data}

        if approval_type == "patch":
            show_patch_approval(
                self.page,
                data,
                on_approve=self._handle_patch_approve,
                on_deny=self._handle_patch_deny,
            )
        elif approval_type == "terminal":
            show_terminal_approval(
                self.page,
                data,
                on_execute=self._handle_terminal_approve,
                on_deny=self._handle_terminal_deny,
            )

    def _on_run_complete(self, success: bool):
        """Handle run completion from bridge."""
        self.is_running = False
        self.pending_approval = None
        if self.vibe_loader:
            self.vibe_loader.hide()
        if self.vibe_status_bar:
            self.vibe_status_bar.hide()

    # ========================================================================
    # APPROVAL HANDLERS
    # ========================================================================

    def _handle_patch_approve(self):
        """Handle patch approval."""
        self.bridge.submit_approval(approved=True)
        self.pending_approval = None

    def _handle_patch_deny(self, feedback: str):
        """Handle patch denial."""
        self.bridge.submit_approval(approved=False, feedback=feedback)
        self.pending_approval = None

    def _handle_terminal_approve(self):
        """Handle terminal command approval."""
        self.bridge.submit_approval(approved=True)
        self.pending_approval = None

    def _handle_terminal_deny(self, feedback: str):
        """Handle terminal command denial."""
        self.bridge.submit_approval(approved=False, feedback=feedback)
        self.pending_approval = None

    # ========================================================================
    # MENU HANDLERS
    # ========================================================================

    def _handle_open_workspace(self):
        """Handle File > Open Workspace."""
        self.sidebar.open_folder_dialog(None)

    def _handle_save_all(self):
        """Handle File > Save All."""
        # TODO: Implement save all open files
        print("[MENU] Save All triggered")

    def _handle_exit(self):
        """Handle File > Exit."""
        self._cleanup()
        self.page.window.close()

    def _handle_toggle_terminal(self):
        """Handle View > Toggle Terminal."""
        self._terminal_visible = not self._terminal_visible
        if self._terminal_container:
            self._terminal_container.visible = self._terminal_visible
            self.page.update()

    def _handle_toggle_sidebar(self):
        """Handle View > Toggle Sidebar."""
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_container:
            self._sidebar_container.visible = self._sidebar_visible
            self.page.update()

    def _handle_open_settings(self, section: str = "all"):
        """Handle Settings menu - opens settings page as a tab."""
        print(f"[DEBUG] App._handle_open_settings called with section: {section}")
        if self.editor_manager:
            print(f"[DEBUG] Editor manager exists, calling open_settings_page()")
            self.editor_manager.open_settings_page()
        else:
            print(f"[WARNING] Editor manager not initialized")

    def _handle_about(self):
        """Handle Help > About."""
        dialog = create_about_dialog(self.page)
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _handle_documentation(self):
        """Handle Help > Documentation."""
        # Open documentation URL in browser
        import webbrowser
        webbrowser.open("https://github.com/anthropics/pulse-ide")

    # ========================================================================
    # AGENT QUERY HANDLING
    # ========================================================================

    def _handle_agent_query(self, user_input: str, target_log_panel: LogPanel):
        """
        Handle agent query with single-run lock.

        Args:
            user_input: User's input text.
            target_log_panel: LogPanel for this tab.
        """
        # Single-run lock check
        if self.is_running:
            # Queue input or show message
            self.bridge.queue_input(user_input)
            target_log_panel.append_log(
                "A run is already in progress. Your input has been queued.",
                "warning"
            )
            return

        # Start run
        self.is_running = True
        self.active_log_panel = target_log_panel
        run_id = str(uuid.uuid4())[:8]

        # Show vibe indicator in the log panel
        if target_log_panel:
            target_log_panel.update_vibe("Wondering")

        # Run in background task to keep UI responsive
        async def run_agent_in_background():
            """Background async task for agent execution."""
            try:
                # Get or create master graph
                if self._master_graph is None:
                    if create_master_graph is None:
                        raise RuntimeError("Master graph not available")
                    self._master_graph = create_master_graph(Path(self.workspace_path))

                # Get mode
                mode = self.sidebar.get_selected_mode()
                mode_key = mode.replace(" Mode", "").lower()

                # Get message history from log panel
                existing_history = target_log_panel.get_message_history()

                # Get settings snapshot
                settings_manager = get_settings_manager()
                settings_snapshot = {
                    "provider": "openai",  # TODO: Get from settings
                    "model": settings_manager.get_model("master_agent"),
                    "enable_crew": settings_manager.get_preference("enable_crew", True),
                    "enable_autogen": settings_manager.get_preference("enable_autogen", True),
                }

                # Create properly initialized state using helper function
                inputs = create_initial_master_state(
                    user_input=user_input,
                    project_root=self.workspace_path,
                    settings_snapshot=settings_snapshot,
                )

                # Merge existing message history if available
                if existing_history:
                    inputs["messages"] = existing_history + [{"role": "user", "content": user_input}]

                # Stream graph execution with thread_id config (required for checkpointer)
                import uuid
                config = {"configurable": {"thread_id": str(uuid.uuid4())}}

                # Use astream() for async nodes (master_agent_node is async def)
                async for event in self._master_graph.astream(inputs, config):
                    for node_name, result in event.items():
                        if result:
                            # Handle agent response
                            if result.get("agent_response"):
                                target_log_panel.append_log(
                                    f"{result['agent_response']}",
                                    "agent"
                                )

                            # Handle files modified
                            if result.get("files_modified"):
                                self.editor_manager.reload_tabs()

            except Exception as e:
                import traceback
                error_msg = f"Error: {str(e)}"
                target_log_panel.append_log(error_msg, "error")
                print(f"[ERROR] {traceback.format_exc()}")

            finally:
                # Reset state
                self.is_running = False
                self.active_log_panel = None

                # Hide vibe in log panel
                if target_log_panel:
                    target_log_panel.update_vibe("")

                # Check for queued input
                queued = self.bridge.get_queued_input()
                if queued:
                    # Process queued input after short delay
                    await asyncio.sleep(0.5)
                    self._handle_agent_query(queued, target_log_panel)

        # Start background async task (not thread)
        self.page.run_task(run_agent_in_background)


def main(page: ft.Page):
    """Main entry point for the Flet application."""
    app = PulseApp(page)


# Export for Flet
if __name__ == "__main__":
    ft.app(target=main)
