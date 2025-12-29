"""
Pulse IDE - Sidebar Component
File explorer and workspace navigation
"""
import os
import json
from pathlib import Path
import flet as ft
from src.ui.theme import VSCodeColors, Fonts, Spacing, create_logo_image


class Sidebar:
    """
    Sidebar component for Pulse IDE.

    Displays a file explorer showing the workspace directory structure.
    Allows users to navigate and select files for editing.
    """

    # Configuration file path for storing recent workspaces
    CONFIG_FILE = Path("data") / "workspace_config.json"

    def __init__(self, editor_manager=None, file_manager=None):
        """
        Initialize the Sidebar component.

        Args:
            editor_manager: Reference to EditorManager for opening files in tabs
            file_manager: Reference to FileManager for secure file operations
        """
        self.editor_manager = editor_manager
        self.file_manager = file_manager
        self.current_path = None
        self.workspace_root = None  # Store the workspace root directory
        self.recent_workspaces = []  # List of recently opened workspace paths
        self.file_picker = None  # Will be initialized when page is available
        self.current_mode = "Agent Mode"  # Default mode
        self.file_controls = {}  # Dictionary to track file TextButton controls by path

        # Load recent workspaces from config file
        self._load_workspaces_from_config()

        # File list column
        self.file_list_column = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=2,
            expand=True
        )

        # Current workspace folder name display (uppercase, professional styling)
        self.path_text = ft.Text(
            "",
            size=Fonts.FONT_SIZE_SMALL - 1,  # Smaller, more subtle (10px)
            color=VSCodeColors.ACTIVITY_BAR_INACTIVE_FOREGROUND,  # Muted color
            weight=ft.FontWeight.W_500,  # Medium weight
            font_family=Fonts.SANS_SERIF_PRIMARY,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )


        # Mode selector dropdown - More compact
        self.mode_selector = ft.Dropdown(
            label="Mode",
            value="Agent Mode",
            options=[
                ft.dropdown.Option("Agent Mode"),
                ft.dropdown.Option("Plan Mode"),
                ft.dropdown.Option("Ask Mode"),
            ],
            width=160,
            on_change=self._on_mode_changed,
            text_size=Fonts.FONT_SIZE_SMALL,
            dense=True,
            bgcolor=VSCodeColors.DROPDOWN_BACKGROUND,
            border_color=VSCodeColors.DROPDOWN_BORDER,
            color=VSCodeColors.DROPDOWN_FOREGROUND,
        )

        # Create Pulse logo image for button
        pulse_logo = create_logo_image(width=40, height=40)

        # Open Agent button - Compact logo button
        self.open_agent_button = ft.Container(
            content=pulse_logo,
            bgcolor=VSCodeColors.BUTTON_SECONDARY_BACKGROUND,
            padding=ft.padding.all(Spacing.PADDING_SMALL),
            border_radius=Spacing.BORDER_RADIUS_SMALL,
            border=ft.border.all(1, VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER),
            ink=True,
            on_click=self._on_open_agent_click,
            on_hover=lambda e: self._on_button_hover(e),
            tooltip="Open Pulse Agent Chat",
            width=38,
            height=38,
        )

        # Build the main container with two sections (PULSE AGENT + File Tree only)
        self.container = ft.Container(
            width=250,
            bgcolor=VSCodeColors.SIDEBAR_BACKGROUND,
            padding=Spacing.PADDING_MEDIUM,
            content=ft.Column(
                controls=[
                    # ===== SECTION 1: PULSE AGENT =====
                    ft.Container(
                        content=ft.Text(
                            "PULSE AGENT",
                            size=Fonts.FONT_SIZE_SMALL,
                            weight=ft.FontWeight.BOLD,
                            color=VSCodeColors.ACTIVITY_BAR_INACTIVE_FOREGROUND
                        ),
                        padding=ft.padding.only(bottom=Spacing.PADDING_SMALL),  # Add vertical space below
                    ),
                    # Mode selector and Open Agent button in horizontal row
                    ft.Row(
                        controls=[
                            self.mode_selector,
                            self.open_agent_button,
                        ],
                        spacing=Spacing.PADDING_SMALL,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Container(
                        content=ft.Divider(height=2, thickness=2, color=VSCodeColors.SIDEBAR_BORDER),
                        padding=ft.padding.symmetric(vertical=Spacing.PADDING_SMALL),  # Add vertical space around divider
                    ),

                    # ===== SECTION 2: PROJECT STRUCTURE =====
                    # Current workspace folder name (compact)
                    ft.Container(
                        content=self.path_text,
                        padding=ft.padding.only(top=4, bottom=4),  # Increased from 2 to 4
                    ),
                    # File tree container
                    ft.Container(
                        content=self.file_list_column,
                        expand=True
                    )
                ],
                spacing=2,  # Reduced even more for tighter layout
                expand=True
            )
        )


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

    def _build_file_tree_node(self, item_path: Path, depth: int = 0) -> ft.Control:
        """
        Build a file tree node (folder with ExpansionTile or file with TextButton).

        Args:
            item_path: Path to the file or directory
            depth: Current depth in the tree (for indentation)

        Returns:
            ft.Control for the tree node
        """
        try:
            # Skip hidden files and ignored directories
            if item_path.name.startswith('.') or item_path.name in ['__pycache__', 'node_modules', 'venv']:
                return None

            if item_path.is_dir():
                # Build folder with ExpansionTile
                # Get children
                try:
                    children = sorted(item_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                except PermissionError:
                    return None

                # Build child controls recursively
                child_controls = []
                for child in children:
                    child_node = self._build_file_tree_node(child, depth + 1)
                    if child_node:
                        child_controls.append(child_node)

                # Create ExpansionTile for folder - ABSOLUTE MINIMAL SPACING
                # Remove leading icon to save space, use icon in title instead
                folder_title = ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.FOLDER, color="#7FBFFF", size=10),
                        ft.Text(
                            item_path.name,
                            size=10,  # Tiny font
                            color="#7FBFFF",
                            weight=ft.FontWeight.W_400,
                        ),
                    ],
                    spacing=4,
                    tight=True,  # Remove extra space
                )

                return ft.ExpansionTile(
                    title=folder_title,
                    initially_expanded=depth == 0,
                    controls=child_controls,
                    controls_padding=ft.padding.all(0),  # ZERO
                    tile_padding=ft.padding.only(left=depth * 8, top=0, bottom=0, right=0),  # ZERO vertical
                    min_tile_height=16,  # ABSOLUTE MINIMUM (18px -> 16px)
                    dense=True,
                    visual_density=ft.VisualDensity.COMPACT,  # Extra compact
                    collapsed_bgcolor=VSCodeColors.SIDEBAR_BACKGROUND,
                    bgcolor=VSCodeColors.SIDEBAR_BACKGROUND,
                    icon_color="#7FBFFF",
                    collapsed_icon_color="#7FBFFF",
                    maintain_state=True,
                )
            else:
                # Build file with TextButton
                # Determine icon and color based on file type
                if item_path.suffix == '.st':
                    icon = ft.Icons.CODE
                    color = "#98C379"  # Green for PLC files
                elif item_path.suffix == '.py':
                    icon = ft.Icons.CODE
                    color = "#FFD700"  # Gold for Python
                elif item_path.suffix in ['.md', '.txt']:
                    icon = ft.Icons.DESCRIPTION
                    color = "#AAAAAA"
                else:
                    icon = ft.Icons.INSERT_DRIVE_FILE
                    color = "#CCCCCC"

                # Create file button - ABSOLUTE MINIMAL spacing, LEFT aligned
                file_button = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, color=color, size=10),
                            ft.Text(
                                item_path.name,
                                size=10,  # Tiny font to match folders
                                color=color,
                                weight=ft.FontWeight.W_400,
                            ),
                        ],
                        spacing=4,
                        tight=True,  # Remove extra space
                        alignment=ft.MainAxisAlignment.START,  # LEFT align file names
                    ),
                    padding=ft.padding.only(left=depth * 8 + 16, top=0, bottom=0, right=0),  # ZERO vertical
                    ink=True,
                    on_click=lambda e, path=item_path: self.on_item_click(path),
                    border_radius=Spacing.BORDER_RADIUS_SMALL,
                    on_hover=lambda e: self._on_file_hover(e),
                    height=16,  # Match ExpansionTile min_tile_height
                    alignment=ft.alignment.center_left,  # LEFT align container content
                )

                # Store reference for dirty state tracking
                self.file_controls[str(item_path.resolve())] = file_button

                return file_button

        except (PermissionError, OSError):
            return None

    def _on_file_hover(self, e):
        """Handle file item hover effect."""
        if e.data == "true":  # Mouse enter
            e.control.bgcolor = VSCodeColors.LIST_HOVER_BACKGROUND
        else:  # Mouse leave
            e.control.bgcolor = None
        e.control.update()

    def load_directory(self, path: str, set_as_root: bool = False):
        """
        Load and display files from the specified directory with VS Code-style tree.

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

            # Update path display - show only folder name in UPPERCASE (VS Code style)
            self.path_text.value = directory.name.upper()


            # Clear existing file list and file controls dictionary
            self.file_list_column.controls.clear()
            self.file_controls.clear()

            # Build the tree structure
            tree_node = self._build_file_tree_node(directory, depth=0)
            if tree_node and isinstance(tree_node, ft.ExpansionTile):
                # Add children of the root directory directly (don't nest root in itself)
                for child_control in tree_node.controls:
                    if child_control:
                        self.file_list_column.controls.append(child_control)
            elif not tree_node:
                # Empty directory
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
        Handle click events on files (directories don't navigate anymore).

        Args:
            path: Path object of the clicked item
        """
        # Only handle file clicks - directories are expanded via ExpansionTile
        if path.is_file():
            # Open file in the editor manager
            if self.editor_manager:
                self.editor_manager.open_file(str(path))
            else:
                print(f"Selected file: {path} (No editor manager connected)")

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

        # Save to config file
        self._save_workspaces_to_config()

    def _on_mode_changed(self, e):
        """
        Handle mode selection change.

        Args:
            e: Event object from dropdown
        """
        self.current_mode = e.control.value
        print(f"Mode changed to: {self.current_mode}")
        # TODO: Wire this to agent orchestration engine to switch modes

    def _on_button_hover(self, e):
        """Handle hover effect on Open Agent button."""
        if e.data == "true":  # Mouse enter
            e.control.bgcolor = VSCodeColors.BUTTON_SECONDARY_HOVER
        else:  # Mouse leave
            e.control.bgcolor = VSCodeColors.BUTTON_SECONDARY_BACKGROUND
        e.control.update()

    def _on_open_agent_click(self, e):
        """
        Handle Open Agent button click.
        Opens the Pulse Agent tab in the editor with the currently selected mode.

        Args:
            e: Event object from button click
        """
        if self.editor_manager:
            self.editor_manager.open_agent(mode=self.current_mode)
        else:
            print("No editor manager connected")

    def get_current_mode(self):
        """
        Get the currently selected mode.

        Returns:
            Current mode string ("Agent Mode", "Plan Mode", or "Ask Mode")
        """
        return self.current_mode

    def get_selected_mode(self):
        """
        Get the currently selected mode.
        Alias for get_current_mode() for API consistency.

        Returns:
            Current mode string ("Agent Mode", "Plan Mode", or "Ask Mode")
            Defaults to "Ask Mode" if not set.
        """
        return self.current_mode if self.current_mode else "Ask Mode"

    def _load_workspaces_from_config(self):
        """
        Load recent workspaces from the JSON config file.

        If the config file doesn't exist or is invalid, starts with an empty list.
        """
        try:
            if self.CONFIG_FILE.exists():
                # Note: Config file is in data/ directory, which may be outside workspace
                # Use standard file operations for config file (not FileManager)
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

            # Note: Config file is in data/ directory, which may be outside workspace
            # Use standard file operations for config file (not FileManager)
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

    def set_file_dirty(self, file_path: str, is_dirty: bool):
        """
        Mark a file as dirty (unsaved changes) or clean in the sidebar.

        Args:
            file_path: Absolute path to the file
            is_dirty: True to mark as dirty (append *), False to mark as clean (remove *)
        """
        # Normalize the file path
        normalized_path = str(Path(file_path).resolve())

        # Find the control for this file
        if normalized_path in self.file_controls:
            file_container = self.file_controls[normalized_path]

            # The container has a Row with an Icon and Text
            if isinstance(file_container, ft.Container) and isinstance(file_container.content, ft.Row):
                row = file_container.content
                if len(row.controls) >= 2 and isinstance(row.controls[1], ft.Text):
                    text_control = row.controls[1]
                    filename = text_control.value.replace(" *", "").strip()

                    # Update the text based on dirty state
                    if is_dirty:
                        text_control.value = f"{filename} *"
                    else:
                        text_control.value = filename

                    # Update UI if page is available
                    if text_control.page:
                        text_control.update()
