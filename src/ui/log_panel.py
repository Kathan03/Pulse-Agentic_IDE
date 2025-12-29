"""
Agent Activity Log Panel Component for Pulse IDE.

Displays agent execution logs and provides user input interface.
Meta-inspired modern design with professional animations.
"""

import flet as ft
from pathlib import Path
from src.ui.theme import VSCodeColors, Fonts, Spacing
from src.ui.components.loading_animation import LoadingAnimation


# Fox pixel art for welcome screen (25x25)
FOX_25 = [
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000001000001000000000",
    "0000000001100011000000000",
    "0000000001111111000000000",
    "0000000011111111100000000",
    "0000000011111111100000000",
    "0000000011211121100000000",
    "0000000001111111000000000",
    "0000000000011100000000000",
    "0000000000001000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
    "0000000000000000000000000",
]
# 0=transparent, 1=body, 2=eye


def fox_svg(body="#FF7A00", eye="#FFFFFF", pixel=10):
    """Generate fox SVG with customizable colors."""
    h = len(FOX_25)
    w = len(FOX_25[0])
    rects = []
    for y, row in enumerate(FOX_25):
        for x, v in enumerate(row):
            if v == "0":
                continue
            fill = eye if v == "2" else body
            rects.append(
                f'<rect x="{x*pixel}" y="{y*pixel}" width="{pixel}" height="{pixel}" fill="{fill}"/>'
            )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w*pixel}" height="{h*pixel}" viewBox="0 0 {w*pixel} {h*pixel}">
  <g shape-rendering="crispEdges">
    {''.join(rects)}
  </g>
</svg>'''


class LogPanel:
    """
    Agent activity log and user input panel with VS Code styling.

    Features:
    - ListView for displaying agent logs
    - TextField for user input at the bottom
    - Auto-scrolling to latest log entries
    - VS Code Dark Modern theme colors
    - Input disable state during agent runs (Phase 7)
    """

    def __init__(self, on_submit=None, on_execute_plan=None, on_cancel_plan=None):
        """
        Initialize LogPanel.

        Args:
            on_submit: Callback function when user submits input (receives text as parameter)
            on_execute_plan: Callback function when user executes plan (V2.1)
            on_cancel_plan: Callback function when user cancels plan (V2.1)
        """
        self.on_submit = on_submit
        self.on_execute_plan = on_execute_plan
        self.on_cancel_plan = on_cancel_plan
        self.log_view = None
        self.input_field = None
        self.plan_view = None
        self.current_view = "log"  # "log" or "plan"

        # V2.3: Per-tab message history for context preservation (Issue A fix)
        # This list stores LangChain Message objects (HumanMessage, AIMessage, etc.)
        # and maintains conversation continuity within THIS specific tab
        self.message_history = []

        # Phase 7: Input disable state during agent runs
        self._input_disabled = False
        self._stop_button = None

        # Meta-inspired loading animation
        self._loading_animation = None
        self._loading_container = None

        # Vibe loader (moved from sidebar to log panel)
        self._vibe_loader = None
        self._vibe_container = None

        # Welcome screen state
        self._welcome_screen = None
        self._log_column = None  # Store reference for visibility toggling
        self._has_messages = False

        self.container = self._build()

    def _build(self):
        """Build the log panel UI component with modern Meta-inspired design."""
        # Log display area
        self.log_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=16,
            auto_scroll=True,
        )

        # Create Claude Code-style welcome screen
        self._welcome_screen = self._build_welcome_screen()

        # Loading animation (Meta-inspired)
        self._loading_animation = LoadingAnimation(message="Pulse is thinking...")
        self._loading_container = ft.Container(
            content=self._loading_animation,
            visible=False,
            padding=ft.padding.only(bottom=12),
        )

        # Vibe loader for status words (Wondering, Brewing, etc.)
        from src.ui.components.vibe_loader import VibeLoader
        self._vibe_loader = VibeLoader()
        self._vibe_container = ft.Container(
            content=self._vibe_loader.get_control(),
            visible=False,
            padding=ft.padding.only(left=16, bottom=8),
        )

        # User input field (modern design) - uses theme colors
        self.input_field = ft.TextField(
            hint_text="Ask Pulse anything...",
            hint_style=ft.TextStyle(
                color=VSCodeColors.DESCRIPTION_FOREGROUND,
                size=Fonts.FONT_SIZE_NORMAL,
                font_family="Inter"
            ),
            multiline=False,
            on_submit=self._handle_submit,
            border=ft.InputBorder.OUTLINE,
            text_size=Fonts.FONT_SIZE_NORMAL,
            bgcolor=VSCodeColors.INPUT_BACKGROUND,
            color=VSCodeColors.INPUT_FOREGROUND,
            border_color=VSCodeColors.INPUT_BORDER,
            focused_border_color=VSCodeColors.INPUT_ACTIVE_BORDER,
            border_radius=8,
            content_padding=14,
        )

        # Send button (modern design with hover effects) - uses theme colors
        send_button = ft.Container(
            content=ft.Icon(
                ft.Icons.SEND_ROUNDED,
                color=VSCodeColors.BUTTON_FOREGROUND,
                size=20,
            ),
            bgcolor=VSCodeColors.BUTTON_BACKGROUND,
            width=44,
            height=44,
            border_radius=8,
            on_click=self._handle_submit,
            ink=True,
            tooltip="Send message",
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color="#00000026",
                offset=ft.Offset(0, 2),
            ),
        )

        # Input row with text field and send button
        input_row = ft.Row(
            controls=[
                ft.Container(
                    content=self.input_field,
                    expand=True,
                ),
                send_button,
            ],
            spacing=10,
        )

        # Store log column reference for visibility toggling
        self._log_column = ft.Column(
            controls=[
                self.log_view,
                self._vibe_container,  # Vibe status words appear here
                self._loading_container,
            ],
            spacing=0,
            expand=True,
            visible=self._has_messages,
        )

        # Main column layout with modern styling
        # Show welcome screen initially, switch to log view after first message
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            # Log view (hidden initially if no messages)
                            self._log_column,
                            # Welcome screen (visible initially)
                            self._welcome_screen,
                        ],
                    ),
                    expand=True,
                    bgcolor=VSCodeColors.EDITOR_BACKGROUND,  # Theme background
                    border=ft.border.all(1, VSCodeColors.PANEL_BORDER),  # Theme border
                    border_radius=10,
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=16,
                        color="#00000033",
                        offset=ft.Offset(0, 4),
                    ),
                ),
                input_row,
            ],
            spacing=12,
            expand=True,
        )

    def _build_welcome_screen(self):
        """Build Claude Code-style welcome screen."""
        # Pulse logo SVG (left of title)
        logo_path = Path.cwd() / "assets" / "pulse_logo_orange_25x25.svg"
        pulse_logo = None
        if logo_path.exists():
            with open(logo_path, "r", encoding="utf-8") as f:
                pulse_logo_svg = f.read()
            pulse_logo = ft.Image(
                src=pulse_logo_svg,
                width=50,
                height=50,
            )
        else:
            # Fallback to icon if SVG not found
            pulse_logo = ft.Icon(
                ft.Icons.AUTO_AWESOME,
                color="#FF7A00",
                size=40,
            )

        # Title row with logo on the left
        title_row = ft.Row(
            controls=[
                pulse_logo,
                ft.Container(width=0),  # Reduced spacing for closer alignment
                ft.Text(
                    "Pulse Code",
                    size=32,
                    weight=ft.FontWeight.W_700,
                    color=VSCodeColors.EDITOR_FOREGROUND,  # Theme-aware text color
                    font_family="Inter",
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Subtitle
        subtitle = ft.Text(
            "Your AI-powered PLC development assistant",
            size=14,
            color=VSCodeColors.DESCRIPTION_FOREGROUND,  # Theme-aware description color
            font_family="Inter",
            text_align=ft.TextAlign.CENTER,
            italic=True,
        )

        # Fox mascot (pixelated)
        fox_image = ft.Image(
            src=fox_svg(body="#FF7A00", eye="#FFFFFF", pixel=8),
            width=200,
            height=200,
        )

        # Welcome container
        return ft.Container(
            content=ft.Column(
                controls=[
                    title_row,
                    ft.Container(height=8),
                    subtitle,
                    ft.Container(height=40),
                    fox_image,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True,
            alignment=ft.alignment.center,
            visible=not self._has_messages,  # Hide when messages exist
        )

    def get_control(self):
        """Get the log panel control for adding to the page."""
        return self.container

    def _handle_submit(self, e):
        """Handle user input submission."""
        print("[DEBUG] _handle_submit called")
        if self.input_field.value and self.input_field.value.strip():
            user_text = self.input_field.value.strip()
            print(f"[DEBUG] User input: {user_text}")

            # Clear input field FIRST to ensure immediate UI feedback
            self.input_field.value = ""
            if self.input_field.page:
                self.input_field.update()
            print("[DEBUG] Input field cleared")

            # Add user message to log panel (centralized message management)
            self.add_log(user_text, "user")

            # Call the callback if provided (pass text only, not manage UI)
            if self.on_submit:
                print(f"[DEBUG] Calling on_submit callback")
                try:
                    self.on_submit(user_text)
                    print(f"[DEBUG] on_submit callback completed")
                except Exception as ex:
                    print(f"[ERROR] Exception in on_submit: {ex}")
                    import traceback
                    traceback.print_exc()
            else:
                print("[DEBUG] No on_submit callback registered")
        else:
            print("[DEBUG] No input or empty input")

    def add_log(self, message: str, log_type: str = "info"):
        """
        Add a log entry to the panel with VS Code color coding.

        Args:
            message: Log message to display
            log_type: Type of log ("info", "success", "warning", "error", "agent", "user")
        """
        # Hide welcome screen on first message
        if not self._has_messages:
            self._has_messages = True
            if self._welcome_screen:
                self._welcome_screen.visible = False
                if self._welcome_screen.page:
                    self._welcome_screen.update()
            if self._log_column:
                self._log_column.visible = True
                if self._log_column.page:
                    self._log_column.update()

        # Color mapping using VS Code theme colors
        color_map = {
            "info": VSCodeColors.INFO_FOREGROUND,
            "success": VSCodeColors.SUCCESS_FOREGROUND,
            "warning": VSCodeColors.WARNING_FOREGROUND,
            "error": VSCodeColors.ERROR_FOREGROUND,
            "agent": VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER,
            "user": "#4EC9B0",  # Teal color for user messages
        }

        # Icon mapping for different log types
        icon_map = {
            "info": ft.Icons.INFO_OUTLINE,
            "success": ft.Icons.CHECK_CIRCLE_OUTLINE,
            "warning": ft.Icons.WARNING_AMBER,
            "error": ft.Icons.ERROR_OUTLINE,
            "agent": ft.Icons.SMART_TOY_OUTLINED,
            "user": ft.Icons.PERSON_OUTLINE,
        }

        # Special formatting for user and agent messages (Meta-inspired design)
        if log_type == "user":
            # User messages - uses theme colors
            log_entry = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(
                                name=ft.Icons.PERSON_ROUNDED,
                                color=VSCodeColors.BUTTON_FOREGROUND,
                                size=16,
                            ),
                            bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                            width=32,
                            height=32,
                            border_radius=16,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "You",
                                    size=12,
                                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                                    weight=ft.FontWeight.W_500,
                                    font_family="Inter",
                                ),
                                ft.Text(
                                    message,
                                    size=14,
                                    color=VSCodeColors.EDITOR_FOREGROUND,
                                    font_family="Inter",
                                    selectable=True,
                                    weight=ft.FontWeight.W_400,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor=VSCodeColors.SIDEBAR_BACKGROUND,
                padding=16,
                border_radius=12,
                border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=8,
                    color="#00000026",
                    offset=ft.Offset(0, 2),
                ),
            )
        elif log_type == "agent":
            # Agent messages with modern Meta-inspired design
            # Load pulse logo SVG
            pulse_logo_path = Path.cwd() / "assets" / "pulse_logo_orange_25x25.svg"
            if pulse_logo_path.exists():
                with open(pulse_logo_path, "r", encoding="utf-8") as f:
                    pulse_logo_svg = f.read()
                agent_icon = ft.Image(
                    src=pulse_logo_svg,
                    width=45,
                    height=45,
                )
            else:
                agent_icon = ft.Icon(
                    name=ft.Icons.AUTO_AWESOME,
                    color="#FFFFFF",
                    size=16,
                )

            log_entry = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=agent_icon,
                            bgcolor=ft.LinearGradient(
                                begin=ft.alignment.top_left,
                                end=ft.alignment.bottom_right,
                                colors=[VSCodeColors.BUTTON_BACKGROUND, VSCodeColors.INFO_FOREGROUND],
                            ),
                            width=32,
                            height=32,
                            border_radius=16,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "Pulse AI",
                                    size=12,
                                    color=VSCodeColors.INFO_FOREGROUND,
                                    weight=ft.FontWeight.W_600,
                                    font_family="Inter",
                                ),
                                ft.Text(
                                    message.replace("", ""),
                                    size=14,
                                    color=VSCodeColors.EDITOR_FOREGROUND,
                                    font_family="Inter",
                                    selectable=True,
                                    weight=ft.FontWeight.W_400,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                padding=16,
                border_radius=12,
                border=ft.border.all(1, VSCodeColors.INFO_FOREGROUND),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=12,
                    color="#1F6FEB33",
                    offset=ft.Offset(0, 2),
                ),
            )
        else:
            # Standard system log entries (info, success, warning, error)
            log_entry = ft.Row(
                controls=[
                    ft.Icon(
                        name=icon_map.get(log_type, ft.Icons.INFO_OUTLINE),
                        color=color_map.get(log_type, VSCodeColors.INFO_FOREGROUND),
                        size=16,
                    ),
                    ft.Text(
                        message,
                        size=Fonts.FONT_SIZE_SMALL,
                        color=color_map.get(log_type, VSCodeColors.INFO_FOREGROUND),
                        font_family=Fonts.SANS_SERIF_PRIMARY,
                        expand=True,
                        selectable=True,
                    ),
                ],
                spacing=Spacing.PADDING_SMALL,
            )

        self.log_view.controls.append(log_entry)
        if self.log_view.page:
            self.log_view.update()

    def clear_logs(self):
        """Clear all log entries."""
        self.log_view.controls.clear()
        if self.log_view.page:
            self.log_view.update()

    def append_log(self, text: str, log_type: str = "info"):
        """
        Thread-safe method to append a log entry to the panel.
        This method ensures UI updates are performed safely from background threads.

        CRITICAL: This method uses page.run_task() (documented Flet API) to ensure
        thread safety when called from LangGraph background threads. Direct UI updates
        from background threads will cause the application to freeze or crash.

        Args:
            text: Log message to display
            log_type: Type of log ("info", "success", "warning", "error", "agent")
        """
        # Check if we have access to the page (required for thread-safe updates)
        if self.log_view.page is None:
            # ERROR: Page reference not set - log to console only
            print(f"[ERROR] LogPanel.append_log: page reference is None (control not mounted)")
            print(f"[ERROR] Message not displayed in UI: [{log_type}] {text}")
            return

        # Thread-safe update using Flet's documented API: page.run_task()
        # This schedules the UI update on the main thread from background threads
        async def update_ui():
            """Internal async helper to update UI on the main thread."""
            self.add_log(text, log_type)  # add_log already calls .update()

        # Execute the UI update on the main thread using documented Flet API
        self.log_view.page.run_task(update_ui)

    # ============================================================================
    # V2.3 Message History Management (Issue A Fix - Per-Tab Context)
    # ============================================================================

    def get_message_history(self):
        """
        Get the current message history for this tab.

        Returns:
            List of LangChain Message objects representing the conversation history.
        """
        return self.message_history

    def update_message_history(self, new_messages):
        """
        Update the message history for this tab with new messages from the graph.

        Args:
            new_messages: List of LangChain Message objects from the graph result.
        """
        self.message_history = new_messages
        print(f"[LOG_PANEL] Updated message history: {len(self.message_history)} messages")

    # ============================================================================
    # V2.1 Plan Mode UI
    # ============================================================================

    def show_plan_view(self, plan_steps: list):
        """
        Display the Plan Mode UI with plan steps as checkboxes.

        This method switches the view from log display to plan review mode,
        showing plan steps in a checkbox list with Execute/Cancel buttons.

        Args:
            plan_steps: List of plan step strings to display.

        Thread Safety:
            Use call_from_thread when calling from background threads.
        """
        print(f"[LOG_PANEL] Showing plan view with {len(plan_steps)} steps")

        # Create checkbox list for plan steps
        step_checkboxes = []
        for idx, step in enumerate(plan_steps):
            checkbox = ft.Checkbox(
                label=step,
                value=False,
                label_style=ft.TextStyle(
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                    font_family=Fonts.SANS_SERIF_PRIMARY
                ),
                fill_color=VSCodeColors.BUTTON_BACKGROUND,
                check_color=VSCodeColors.EDITOR_BACKGROUND
            )
            step_checkboxes.append(checkbox)

        # Create plan header
        plan_header = ft.Container(
            content=ft.Row([
                ft.Icon(
                    name=ft.Icons.CHECKLIST,
                    color=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER,
                    size=24
                ),
                ft.Text(
                    "Implementation Plan",
                    size=Fonts.FONT_SIZE_LARGE,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER
                )
            ], spacing=Spacing.PADDING_SMALL),
            padding=Spacing.PADDING_MEDIUM
        )

        # Plan steps container
        plan_steps_container = ft.Container(
            content=ft.Column(
                controls=step_checkboxes,
                spacing=Spacing.PADDING_SMALL,
                scroll=ft.ScrollMode.AUTO
            ),
            expand=True,
            padding=Spacing.PADDING_MEDIUM,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
            border=ft.border.all(Spacing.BORDER_WIDTH, VSCodeColors.PANEL_BORDER),
            border_radius=Spacing.BORDER_RADIUS_SMALL
        )

        # Action buttons
        execute_button = ft.ElevatedButton(
            "Execute Plan",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=VSCodeColors.BUTTON_BACKGROUND,
            color=VSCodeColors.BUTTON_FOREGROUND,
            on_click=self._handle_execute_plan
        )

        cancel_button = ft.TextButton(
            "Cancel",
            icon=ft.Icons.CANCEL,
            on_click=self._handle_cancel_plan
        )

        button_row = ft.Row(
            controls=[cancel_button, execute_button],
            alignment=ft.MainAxisAlignment.END,
            spacing=Spacing.PADDING_MEDIUM
        )

        # Build plan view
        self.plan_view = ft.Column(
            controls=[
                plan_header,
                ft.Divider(height=1, color=VSCodeColors.PANEL_BORDER),
                ft.Container(
                    content=ft.Text(
                        "Review the implementation steps below. Click 'Execute Plan' when ready.",
                        size=Fonts.FONT_SIZE_SMALL,
                        color=VSCodeColors.INFO_FOREGROUND,
                        italic=True
                    ),
                    padding=ft.padding.only(left=Spacing.PADDING_MEDIUM, right=Spacing.PADDING_MEDIUM)
                ),
                plan_steps_container,
                ft.Container(
                    content=button_row,
                    padding=Spacing.PADDING_MEDIUM
                )
            ],
            spacing=Spacing.PADDING_SMALL,
            expand=True
        )

        # Switch to plan view
        self.current_view = "plan"
        self._update_view()

    def show_log_view(self):
        """
        Switch back to log view from plan view.

        Thread Safety:
            Use call_from_thread when calling from background threads.
        """
        print("[LOG_PANEL] Switching to log view")
        self.current_view = "log"
        self._update_view()

    def _update_view(self):
        """Update the container to show current view (log or plan)."""
        if self.current_view == "plan" and self.plan_view:
            # Replace container content with plan view
            self.container.controls.clear()
            self.container.controls.append(self.plan_view)
        else:
            # Show log view (rebuild the original layout)
            self.container.controls.clear()

            # Log container
            log_container = ft.Container(
                content=self.log_view,
                expand=True,
                bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                border=ft.border.all(Spacing.BORDER_WIDTH, VSCodeColors.PANEL_BORDER),
                border_radius=Spacing.BORDER_RADIUS_SMALL,
            )

            # Input row
            send_button = ft.IconButton(
                icon=ft.Icons.SEND,
                tooltip="Send",
                on_click=self._handle_submit,
                icon_color=VSCodeColors.BUTTON_BACKGROUND,
                bgcolor=VSCodeColors.BUTTON_SECONDARY_BACKGROUND,
                hover_color=VSCodeColors.BUTTON_SECONDARY_HOVER,
            )

            input_row = ft.Row(
                controls=[
                    ft.Container(
                        content=self.input_field,
                        expand=True,
                    ),
                    send_button,
                ],
                spacing=Spacing.PADDING_SMALL,
            )

            self.container.controls.append(log_container)
            self.container.controls.append(input_row)

        if self.container.page:
            self.container.update()

    def _handle_execute_plan(self, e):
        """Handle Execute Plan button click."""
        print("[LOG_PANEL] Execute Plan clicked")
        if self.on_execute_plan:
            self.on_execute_plan()

        # Switch back to log view
        self.show_log_view()

    def _handle_cancel_plan(self, e):
        """Handle Cancel Plan button click."""
        print("[LOG_PANEL] Cancel Plan clicked")
        if self.on_cancel_plan:
            self.on_cancel_plan()

        # Switch back to log view
        self.show_log_view()

    # ============================================================================
    # Phase 7: Input Disable State During Runs
    # ============================================================================

    def disable_input(self, on_stop=None):
        """
        Disable input during agent run with Meta-inspired loading animation.

        Shows a professional loading indicator instead of plain text.

        Args:
            on_stop: Callback when stop button is clicked.
        """
        self._input_disabled = True
        if self.input_field:
            self.input_field.disabled = True
            self.input_field.hint_text = "Pulse is thinking..."
            if self.input_field.page:
                self.input_field.update()

        # Show loading animation
        if self._loading_container:
            self._loading_container.visible = True
            if self._loading_container.page:
                self._loading_container.update()

    def enable_input(self):
        """
        Re-enable input after agent run completes.
        """
        self._input_disabled = False
        if self.input_field:
            self.input_field.disabled = False
            self.input_field.hint_text = "Ask Pulse anything..."
            if self.input_field.page:
                self.input_field.update()

        # Hide loading animation
        if self._loading_container:
            self._loading_container.visible = False
            if self._loading_container.page:
                self._loading_container.update()

        # Hide vibe loader
        if self._vibe_container:
            self._vibe_container.visible = False
            if self._vibe_container.page:
                self._vibe_container.update()

    def update_vibe(self, vibe: str):
        """
        Update vibe status word (Wondering, Brewing, etc.).

        Args:
            vibe: Vibe status word to display.
        """
        if self._vibe_loader and vibe:
            self._vibe_loader.update_vibe(vibe)
            if self._vibe_container:
                self._vibe_container.visible = True
                if self._vibe_container.page:
                    self._vibe_container.update()
        elif self._vibe_container:
            self._vibe_container.visible = False
            if self._vibe_container.page:
                self._vibe_container.update()

    @property
    def is_input_disabled(self) -> bool:
        """Check if input is currently disabled."""
        return self._input_disabled
