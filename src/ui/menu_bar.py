"""
VS Code-Style Menu Bar for Pulse IDE v2.6 (Phase 7).

Provides top-level menu structure:
- File: Open Workspace, Save All, Exit
- View: Toggle Terminal, Toggle Sidebar
- Settings: API Keys, Models, Agent Toggle
- Help: About Pulse, Documentation
"""

import flet as ft
from typing import Callable, Optional
from src.ui.theme import VSCodeColors, Fonts, Spacing


class MenuBar:
    """
    VS Code-style menu bar component.

    Provides application-level menu items with keyboard shortcuts.
    """

    def __init__(
        self,
        on_open_workspace: Optional[Callable] = None,
        on_save_all: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
        on_toggle_terminal: Optional[Callable] = None,
        on_toggle_sidebar: Optional[Callable] = None,
        on_open_settings: Optional[Callable] = None,
        on_about: Optional[Callable] = None,
        on_documentation: Optional[Callable] = None,
    ):
        """
        Initialize MenuBar.

        Args:
            on_open_workspace: Callback for File > Open Workspace
            on_save_all: Callback for File > Save All
            on_exit: Callback for File > Exit
            on_toggle_terminal: Callback for View > Toggle Terminal
            on_toggle_sidebar: Callback for View > Toggle Sidebar
            on_open_settings: Callback for Settings menu
            on_about: Callback for Help > About
            on_documentation: Callback for Help > Documentation
        """
        self._on_open_workspace = on_open_workspace
        self._on_save_all = on_save_all
        self._on_exit = on_exit
        self._on_toggle_terminal = on_toggle_terminal
        self._on_toggle_sidebar = on_toggle_sidebar
        self._on_open_settings = on_open_settings
        self._on_about = on_about
        self._on_documentation = on_documentation

        self._container = self._build()

    def _build(self) -> ft.Container:
        """Build the menu bar UI with enhanced visibility using Row + PopupMenuButton."""
        # Use Row with PopupMenuButton for better visibility
        # File menu - with theme colors
        file_menu = ft.PopupMenuButton(
            content=ft.Text(
                "File",
                size=Fonts.FONT_SIZE_NORMAL,
                color=VSCodeColors.MENU_FOREGROUND,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=VSCodeColors.MENU_BACKGROUND,  # Popup background
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OPEN, size=16, color=VSCodeColors.MENU_FOREGROUND),
                            ft.Text("Open Workspace...", color=VSCodeColors.MENU_FOREGROUND),
                        ],
                        spacing=8
                    ),
                    on_click=self._handle_open_workspace,
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SAVE, size=16, color=VSCodeColors.MENU_FOREGROUND),
                            ft.Text("Save All  (Ctrl+Shift+S)", color=VSCodeColors.MENU_FOREGROUND),
                        ],
                        spacing=8
                    ),
                    on_click=self._handle_save_all,
                ),
                ft.PopupMenuItem(),  # Divider
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.EXIT_TO_APP, size=16, color=VSCodeColors.MENU_FOREGROUND),
                            ft.Text("Exit", color=VSCodeColors.MENU_FOREGROUND),
                        ],
                        spacing=8
                    ),
                    on_click=self._handle_exit,
                ),
            ],
        )

        # View menu - with theme colors
        view_menu = ft.PopupMenuButton(
            content=ft.Text(
                "View",
                size=Fonts.FONT_SIZE_NORMAL,
                color=VSCodeColors.MENU_FOREGROUND,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=VSCodeColors.MENU_BACKGROUND,  # Popup background
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.TERMINAL, size=16, color=VSCodeColors.MENU_FOREGROUND),
                            ft.Text("Toggle Terminal  (Ctrl+`)", color=VSCodeColors.MENU_FOREGROUND),
                        ],
                        spacing=8
                    ),
                    on_click=self._handle_toggle_terminal,
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.VERTICAL_SPLIT, size=16, color=VSCodeColors.MENU_FOREGROUND),
                            ft.Text("Toggle Sidebar  (Ctrl+B)", color=VSCodeColors.MENU_FOREGROUND),
                        ],
                        spacing=8
                    ),
                    on_click=self._handle_toggle_sidebar,
                ),
            ],
        )

        # Settings button (opens settings page in editor)
        settings_menu = ft.TextButton(
            content=ft.Text(
                "Settings",
                size=Fonts.FONT_SIZE_NORMAL,
                color=VSCodeColors.MENU_FOREGROUND,
                weight=ft.FontWeight.W_500,
            ),
            on_click=lambda e: self._handle_open_settings("all"),
        )

        # Help menu - Under Construction - with theme colors
        help_menu = ft.PopupMenuButton(
            content=ft.Text(
                "Help",
                size=Fonts.FONT_SIZE_NORMAL,
                color=VSCodeColors.MENU_FOREGROUND,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=VSCodeColors.MENU_BACKGROUND,  # Popup background
            items=[
                ft.PopupMenuItem(
                    content=ft.Text("🚧 Under Construction", color=VSCodeColors.DESCRIPTION_FOREGROUND),
                    disabled=True,
                ),
            ],
        )

        # Logo and title for leftmost section
        from src.ui.theme import create_logo_image
        logo_section = ft.Row(
            controls=[
                create_logo_image(width=24, height=24),
                ft.Text(
                    "Pulse",
                    size=Fonts.FONT_SIZE_NORMAL,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.TITLE_BAR_FOREGROUND,
                ),
            ],
            spacing=8,
        )

        # Window control buttons (right side of title bar)
        window_controls = ft.Row(
            controls=[
                # Minimize button
                ft.IconButton(
                    icon=ft.Icons.MINIMIZE,
                    icon_size=16,
                    icon_color=VSCodeColors.MENU_FOREGROUND,
                    on_click=self._handle_minimize,
                    tooltip="Minimize",
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(4),
                    ),
                ),
                # Maximize/Restore button
                ft.IconButton(
                    icon=ft.Icons.CROP_SQUARE,
                    icon_size=14,
                    icon_color=VSCodeColors.MENU_FOREGROUND,
                    on_click=self._handle_maximize,
                    tooltip="Maximize",
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(4),
                    ),
                ),
                # Close button
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=16,
                    icon_color=VSCodeColors.MENU_FOREGROUND,
                    on_click=self._handle_close,
                    tooltip="Close",
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(4),
                    ),
                    hover_color="#E81123",  # Red on hover like Windows
                ),
            ],
            spacing=0,
        )

        # Create menu bar using Row with PERFECTLY EVEN spacing
        # Match the good spacing between View-Settings-Help
        menu_row = ft.Row(
            controls=[
                ft.Container(content=logo_section, padding=ft.padding.only(right=16)),  # Logo has more right space
                ft.Container(content=file_menu, padding=ft.padding.symmetric(horizontal=8)),  # Equal spacing
                ft.Container(content=view_menu, padding=ft.padding.symmetric(horizontal=8)),  # Equal spacing
                ft.Container(content=settings_menu, padding=ft.padding.symmetric(horizontal=8)),  # Equal spacing
                ft.Container(content=help_menu, padding=ft.padding.symmetric(horizontal=8)),  # Equal spacing
                ft.Container(expand=True),  # Spacer to push window controls to the right
                window_controls,
            ],
            spacing=0,  # No spacing since containers have padding
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Wrap in container with title bar styling
        menu_container = ft.Container(
            content=menu_row,
            bgcolor=VSCodeColors.TITLE_BAR_BACKGROUND,
            height=35,
            padding=ft.padding.symmetric(horizontal=12, vertical=0),
            border=ft.border.only(bottom=ft.BorderSide(1, VSCodeColors.PANEL_BORDER)),
        )

        # Make menu bar draggable (acts as window title bar)
        return ft.WindowDragArea(
            content=menu_container,
            maximizable=True,
        )

    def get_control(self):
        """Get the menu bar control."""
        return self._container

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def _handle_open_workspace(self, e):
        """Handle Open Workspace click."""
        if self._on_open_workspace:
            self._on_open_workspace()

    def _handle_save_all(self, e):
        """Handle Save All click."""
        if self._on_save_all:
            self._on_save_all()

    def _handle_exit(self, e):
        """Handle Exit click."""
        if self._on_exit:
            self._on_exit()
        else:
            # Default: close window
            if e.control.page:
                e.control.page.window.close()

    def _handle_toggle_terminal(self, e):
        """Handle Toggle Terminal click."""
        if self._on_toggle_terminal:
            self._on_toggle_terminal()

    def _handle_toggle_sidebar(self, e):
        """Handle Toggle Sidebar click."""
        if self._on_toggle_sidebar:
            self._on_toggle_sidebar()

    def _handle_open_settings(self, section: str = "all"):
        """Handle Settings button click - opens settings page in editor."""
        print(f"[DEBUG] MenuBar._handle_open_settings called with section: {section}")
        if self._on_open_settings:
            print(f"[DEBUG] Calling on_open_settings callback")
            self._on_open_settings(section)
        else:
            print(f"[WARNING] No on_open_settings callback registered")

    def _handle_about(self, e):
        """Handle About click."""
        if self._on_about:
            self._on_about()

    def _handle_documentation(self, e):
        """Handle Documentation click."""
        if self._on_documentation:
            self._on_documentation()

    def _handle_report_issue(self, e):
        """Handle Report Issue click."""
        # Open GitHub issues page in browser
        import webbrowser
        webbrowser.open("https://github.com/kathanshah/pulse-ide/issues/new")

    def _handle_minimize(self, e):
        """Handle window minimize button click."""
        if e.control.page:
            e.control.page.window.minimized = True
            e.control.page.update()

    def _handle_maximize(self, e):
        """Handle window maximize/restore button click."""
        if e.control.page:
            # Toggle between maximized and normal
            if e.control.page.window.maximized:
                e.control.page.window.maximized = False
            else:
                e.control.page.window.maximized = True
            e.control.page.update()

    def _handle_close(self, e):
        """Handle window close button click."""
        if e.control.page:
            e.control.page.window.close()


def create_about_dialog(page: ft.Page) -> ft.AlertDialog:
    """
    Create About Pulse dialog.

    Args:
        page: Flet Page for dialog display.

    Returns:
        AlertDialog with about information.
    """
    return ft.AlertDialog(
        modal=True,
        title=ft.Text("About Pulse IDE"),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Image(
                        src="/icons/pulse_logo.png",
                        width=64,
                        height=64,
                        fit=ft.ImageFit.CONTAIN,
                        error_content=ft.Icon(
                            ft.Icons.SMART_TOY,
                            size=64,
                            color=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER
                        )
                    ),
                    ft.Text(
                        "Pulse IDE",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=VSCodeColors.EDITOR_FOREGROUND
                    ),
                    ft.Text(
                        "Version 2.6 - Unified Master Loop",
                        size=12,
                        color=VSCodeColors.DESCRIPTION_FOREGROUND
                    ),
                    ft.Divider(height=16),
                    ft.Text(
                        "Agentic AI IDE for PLC Coding",
                        size=14,
                        color=VSCodeColors.EDITOR_FOREGROUND
                    ),
                    ft.Text(
                        "Built with LangGraph + Flet",
                        size=12,
                        color=VSCodeColors.DESCRIPTION_FOREGROUND
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            width=300,
            padding=20,
        ),
        actions=[
            ft.TextButton(
                "Close",
                on_click=lambda e: setattr(e.control.page.dialog, 'open', False) or e.control.page.update()
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )


__all__ = [
    "MenuBar",
    "create_about_dialog",
]
