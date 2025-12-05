"""
Pulse IDE - Main Flet Application
Entry point for the Flet-based desktop UI
"""
import flet as ft
from src.ui.sidebar import Sidebar


def main(page: ft.Page):
    """
    Main entry point for the Flet application.

    Sets up the initial page configuration and creates the base layout
    with sidebar (left) and main content area (right).

    Args:
        page: The Flet Page object representing the application window
    """
    # Configure page settings
    page.title = "Pulse IDE"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # Create left sidebar with file explorer
    sidebar = Sidebar()

    # Create main content area placeholder (expandable)
    main_content = ft.Container(
        expand=True,
        bgcolor="#1E1E1E",  # Darker gray for main content
        padding=10,
        content=ft.Text(
            "Main Content Area\n(Editor & Panels)",
            size=14,
            color="#CCCCCC"  # Light gray text
        )
    )

    # Create the main layout: sidebar on left, content on right
    layout = ft.Row(
        controls=[sidebar.get_control(), main_content],
        spacing=0,
        expand=True
    )

    # Add layout to page
    page.add(layout)

    # Initialize FilePicker for the sidebar
    sidebar.initialize_file_picker(page)

    # Initialize sidebar with current working directory as workspace root
    sidebar.load_directory(".", set_as_root=True)