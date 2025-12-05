"""
Pulse IDE - Sidebar Component
File explorer and workspace navigation
"""
import os
import json
from pathlib import Path
import flet as ft


class Sidebar:
    """
    Sidebar component for Pulse IDE.

    Displays a file explorer showing the workspace directory structure.
    Allows users to navigate and select files for editing.
    """

    # Configuration file path for storing recent workspaces
    CONFIG_FILE = Path("data") / "workspace_config.json"

    def __init__(self):
        """Initialize the Sidebar component."""
        self.current_path = None
        self.workspace_root = None  # Store the workspace root directory
        self.recent_workspaces = []  # List of recently opened workspace paths
        self.file_picker = None  # Will be initialized when page is available

        # Load recent workspaces from config file
        self._load_workspaces_from_config()

        # File list column
        self.file_list_column = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=2,
            expand=True
        )

        # Current path display
        self.path_text = ft.Text(
            "",
            size=10,
            color="#888888",
            italic=True,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS
        )

        # Workspace switcher dropdown
        self.workspace_dropdown = ft.Dropdown(
            label="Recent Workspaces",
            hint_text="Select a recent workspace",
            options=[],
            width=230,
            on_change=lambda e: self.switch_workspace(e.control.value),
            text_size=11,
            dense=True,
            bgcolor="#3C3C3C",
            border_color="#505050"
        )

        # Navigation buttons
        self.back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_size=16,
            tooltip="Go to parent directory",
            on_click=lambda _: self.go_back(),
            disabled=True,
            icon_color="#E0E0E0"
        )

        self.home_button = ft.IconButton(
            icon=ft.Icons.HOME,
            icon_size=16,
            tooltip="Go to workspace root",
            on_click=lambda _: self.go_to_root(),
            disabled=True,
            icon_color="#E0E0E0"
        )

        # Open folder button
        self.open_folder_button = ft.ElevatedButton(
            text="Open Folder",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self.open_folder_dialog,
            style=ft.ButtonStyle(
                bgcolor="#3C3C3C",
                color="#E0E0E0",
                padding=ft.padding.symmetric(horizontal=10, vertical=5)
            ),
            height=32
        )

        # Build the main container
        self.container = ft.Container(
            width=250,
            bgcolor="#2C2C2C",
            padding=10,
            content=ft.Column(
                controls=[
                    # Header with workspace label
                    ft.Row(
                        controls=[
                            ft.Text(
                                "WORKSPACE",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color="#E0E0E0"
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START
                    ),
                    # Open folder button
                    self.open_folder_button,
                    # Recent workspaces dropdown
                    self.workspace_dropdown,
                    ft.Divider(height=1, color="#404040"),
                    # Navigation bar
                    ft.Row(
                        controls=[
                            self.back_button,
                            self.home_button,
                            ft.Container(
                                content=self.path_text,
                                expand=True
                            )
                        ],
                        spacing=5,
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Divider(height=1, color="#404040"),
                    # File list container
                    ft.Container(
                        content=self.file_list_column,
                        expand=True
                    )
                ],
                spacing=5,
                expand=True
            )
        )

        # Populate dropdown with loaded workspaces
        if self.recent_workspaces:
            self._update_workspace_dropdown()

    def get_control(self):
        """
        Get the sidebar control for adding to the page.

        Returns:
            ft.Container: The sidebar container
        """
        return self.container

    def initialize_file_picker(self, page: ft.Page):
        """
        Initialize the FilePicker and add it to the page services.

        Args:
            page: The Flet Page object
        """
        self.file_picker = ft.FilePicker(on_result=self._on_folder_selected)
        page.overlay.append(self.file_picker)
        page.update()

    def load_directory(self, path: str, set_as_root: bool = False):
        """
        Load and display files from the specified directory.

        Args:
            path: Path to the directory to load
            set_as_root: If True, sets this directory as the workspace root
        """
        try:
            # Convert to Path object for easier manipulation
            directory = Path(path).resolve()
            self.current_path = directory

            # Set workspace root if specified or if not set yet
            if set_as_root or self.workspace_root is None:
                self.workspace_root = directory
                # Add to recent workspaces
                self._add_to_recent_workspaces(str(directory))

            # Update path display
            self.path_text.value = str(directory)

            # Update navigation button states
            # Back button is enabled if we have a parent directory
            self.back_button.disabled = (directory.parent == directory)
            # Home button is enabled if we're not at workspace root
            self.home_button.disabled = (directory == self.workspace_root)

            # Clear existing file list
            self.file_list_column.controls.clear()

            # Get all files and directories
            items = []
            try:
                items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                self.file_list_column.controls.append(
                    ft.Text(
                        "⚠️ Permission denied",
                        size=11,
                        color="#FF5555"
                    )
                )
                if self.container.page:
                    self.container.update()
                return

            # Display directories first, then files
            for item in items:
                try:
                    # Skip hidden files and common ignored directories
                    if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules', 'venv']:
                        continue

                    # Determine icon and color based on type
                    if item.is_dir():
                        icon = "📁"
                        color = "#7FBFFF"
                    else:
                        # Different icons for different file types
                        if item.suffix == '.st':
                            icon = "📄"
                            color = "#98C379"  # Green for PLC files
                        elif item.suffix == '.py':
                            icon = "🐍"
                            color = "#FFD700"  # Gold for Python
                        elif item.suffix in ['.md', '.txt']:
                            icon = "📝"
                            color = "#AAAAAA"
                        else:
                            icon = "📄"
                            color = "#CCCCCC"

                    # Create clickable file/directory button
                    file_button = ft.TextButton(
                        text=f"{icon} {item.name}",
                        style=ft.ButtonStyle(
                            color=color,
                            padding=ft.padding.symmetric(horizontal=5, vertical=5),
                            alignment=ft.alignment.center_left
                        ),
                        on_click=lambda e, path=item: self.on_item_click(path)
                    )

                    self.file_list_column.controls.append(file_button)

                except (PermissionError, OSError) as e:
                    # Skip items we can't access
                    continue

            # If no items were added (empty directory)
            if len(self.file_list_column.controls) == 1:  # Only the header
                self.file_list_column.controls.append(
                    ft.Text(
                        "📭 Empty directory",
                        size=11,
                        color="#888888",
                        italic=True
                    )
                )

            # Update the UI
            if self.container.page:
                self.container.update()

        except Exception as e:
            # Handle any unexpected errors
            self.file_list_column.controls.clear()
            self.file_list_column.controls.append(
                ft.Text(
                    f"❌ Error loading directory:\n{str(e)}",
                    size=11,
                    color="#FF5555"
                )
            )
            if self.container.page:
                self.container.update()

    def on_item_click(self, path: Path):
        """
        Handle click events on files/directories.

        Args:
            path: Path object of the clicked item
        """
        if path.is_dir():
            # Navigate into directory
            self.load_directory(str(path))
        else:
            # For MVP, just print the file path
            # In future iterations, this will open the file in the editor
            print(f"Selected file: {path}")

    def go_back(self):
        """Navigate to the parent directory."""
        if self.current_path and self.current_path.parent != self.current_path:
            self.load_directory(str(self.current_path.parent))

    def go_to_root(self):
        """Navigate to the workspace root directory."""
        if self.workspace_root:
            self.load_directory(str(self.workspace_root))

    def open_folder_dialog(self, e):
        """
        Open a native folder picker dialog to select a new workspace folder.
        Uses Flet's FilePicker for native OS folder selection.

        Args:
            e: The event object from the button click
        """
        if not self.file_picker:
            print("FilePicker not initialized. Call initialize_file_picker() first.")
            return

        try:
            # Open native folder picker dialog
            # The result will be handled by the _on_folder_selected callback
            self.file_picker.get_directory_path(
                dialog_title="Select Workspace Folder"
            )
        except Exception as ex:
            print(f"Error opening folder dialog: {ex}")

    def _on_folder_selected(self, e: ft.FilePickerResultEvent):
        """
        Callback handler for when a folder is selected from the FilePicker.

        Args:
            e: FilePickerResultEvent containing the selected path
        """
        try:
            # e.path contains the selected directory path (or None if cancelled)
            if e.path:
                # Load the new workspace folder
                self.load_directory(e.path, set_as_root=True)
        except Exception as ex:
            print(f"Error handling folder selection: {ex}")

    def _add_to_recent_workspaces(self, workspace_path: str):
        """
        Add a workspace to the recent workspaces list and update the dropdown.

        Args:
            workspace_path: Path to the workspace directory
        """
        # Remove if already exists (to move it to top)
        if workspace_path in self.recent_workspaces:
            self.recent_workspaces.remove(workspace_path)

        # Add to beginning of list
        self.recent_workspaces.insert(0, workspace_path)

        # Keep only last 10 workspaces
        self.recent_workspaces = self.recent_workspaces[:10]

        # Update dropdown options
        self._update_workspace_dropdown()

        # Save to config file
        self._save_workspaces_to_config()

    def _update_workspace_dropdown(self):
        """Update the workspace dropdown with recent workspaces."""
        self.workspace_dropdown.options = [
            ft.dropdown.Option(
                key=path,
                text=Path(path).name + f" ({path})"[:50] + "..."
                if len(path) > 50
                else Path(path).name
            )
            for path in self.recent_workspaces
        ]

        # Update the UI if page is available
        if self.container.page:
            self.workspace_dropdown.update()

    def switch_workspace(self, workspace_path: str):
        """
        Switch to a different workspace from the recent workspaces list.

        Args:
            workspace_path: Path to the workspace to switch to
        """
        if workspace_path and Path(workspace_path).is_dir():
            self.load_directory(workspace_path, set_as_root=True)

    def _load_workspaces_from_config(self):
        """
        Load recent workspaces from the JSON config file.

        If the config file doesn't exist or is invalid, starts with an empty list.
        """
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recent_workspaces = data.get('recent_workspaces', [])
                    # Filter out non-existent directories
                    self.recent_workspaces = [
                        path for path in self.recent_workspaces
                        if Path(path).is_dir()
                    ]
        except Exception as e:
            print(f"Error loading workspace config: {e}")
            self.recent_workspaces = []

    def _save_workspaces_to_config(self):
        """
        Save recent workspaces to the JSON config file.

        Creates the data directory if it doesn't exist.
        """
        try:
            # Ensure the data directory exists
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Save to JSON file
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        'recent_workspaces': self.recent_workspaces
                    },
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            print(f"Error saving workspace config: {e}")
