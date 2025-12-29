"""
Code Preview Panel for Pulse IDE.

Displays generated code diffs with approval/rejection controls.
Shows side-by-side comparison of original vs. generated code.
"""

import flet as ft
from typing import List, Dict, Any, Callable
from difflib import unified_diff


class CodePreviewPanel:
    """
    Code Preview Panel with diff view and approval controls.

    Features:
    - Side-by-side diff view (original vs. generated)
    - Multiple file support with tabs
    - Action indicators (CREATE/MODIFY)
    - Explanation text for each change
    - Approve/Reject buttons
    - Feedback text area (shown on reject)
    """

    def __init__(
        self,
        code_preview: List[Dict[str, Any]],
        on_approve: Callable[[], None],
        on_reject: Callable[[str], None]
    ):
        """
        Initialize Code Preview Panel.

        Args:
            code_preview: List of code preview items from coder_node
                [{
                    "file": "main.st",
                    "action": "create" | "modify",
                    "original": "...",
                    "generated": "...",
                    "explanation": "..."
                }, ...]
            on_approve: Callback when user approves all changes
            on_reject: Callback when user rejects with feedback (str)
        """
        self.code_preview = code_preview
        self.on_approve = on_approve
        self.on_reject = on_reject
        self.current_file_index = 0
        self.feedback_text = ft.TextField(
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="Describe what you'd like me to change...",
            visible=False,
            border_color=ft.Colors.ORANGE_400
        )
        self.control = self._build_ui()

    def _build_ui(self) -> ft.Container:
        """Build the code preview UI."""
        if not self.code_preview:
            return ft.Container(
                content=ft.Text("No code preview available."),
                padding=20
            )

        # File tabs (if multiple files)
        file_tabs = []
        if len(self.code_preview) > 1:
            for idx, preview_item in enumerate(self.code_preview):
                file_name = preview_item.get("file", f"File {idx+1}")
                action = preview_item.get("action", "modify").upper()

                file_tabs.append(
                    ft.Tab(
                        text=f"{file_name} [{action}]",
                        content=self._build_file_preview(idx)
                    )
                )

        # Main content area
        if len(self.code_preview) > 1:
            content_area = ft.Tabs(
                tabs=file_tabs,
                selected_index=0,
                animation_duration=300
            )
        else:
            content_area = self._build_file_preview(0)

        # Approval buttons
        approve_button = ft.ElevatedButton(
            text="✓ Approve All Changes",
            icon=ft.Icons.CHECK_CIRCLE,
            on_click=self._handle_approve,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE
        )

        reject_button = ft.OutlinedButton(
            text="✗ Reject & Provide Feedback",
            icon=ft.Icons.CANCEL,
            on_click=self._handle_reject_toggle,
            color=ft.Colors.ORANGE_400
        )

        submit_feedback_button = ft.ElevatedButton(
            text="Submit Feedback",
            icon=ft.Icons.SEND,
            on_click=self._handle_submit_feedback,
            bgcolor=ft.Colors.ORANGE_700,
            color=ft.Colors.WHITE,
            visible=False
        )

        button_row = ft.Row(
            controls=[
                approve_button,
                reject_button,
                submit_feedback_button
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER
        )

        # Store references for toggling visibility
        self.approve_button = approve_button
        self.reject_button = reject_button
        self.submit_feedback_button = submit_feedback_button

        # Main container
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(
                            "📝 Code Preview - Review changes before applying",
                            size=18,
                            weight=ft.FontWeight.BOLD
                        ),
                        padding=ft.padding.only(bottom=10)
                    ),
                    ft.Divider(),
                    content_area,
                    ft.Divider(),
                    self.feedback_text,
                    button_row
                ],
                spacing=10,
                expand=True,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            border_radius=10
        )

    def _build_file_preview(self, index: int) -> ft.Container:
        """Build preview for a single file."""
        if index >= len(self.code_preview):
            return ft.Container(
                content=ft.Text("Invalid file index"),
                padding=10
            )

        preview_item = self.code_preview[index]
        file_name = preview_item.get("file", "Unknown File")
        action = preview_item.get("action", "modify")
        original = preview_item.get("original", "")
        generated = preview_item.get("generated", "")
        explanation = preview_item.get("explanation", "")

        # Header with file info
        action_color = ft.Colors.GREEN_400 if action == "create" else ft.Colors.BLUE_400
        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.ADD_CIRCLE if action == "create" else ft.Icons.EDIT,
                        color=action_color
                    ),
                    ft.Text(
                        f"{action.upper()}: {file_name}",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=action_color
                    )
                ],
                spacing=10
            ),
            padding=ft.padding.only(bottom=10)
        )

        # Explanation
        explanation_box = ft.Container(
            content=ft.Text(
                explanation,
                size=14,
                italic=True
            ),
            padding=10,
            bgcolor=ft.Colors.BLUE_GREY_900,
            border_radius=5,
            margin=ft.margin.only(bottom=10)
        )

        # Diff view (side-by-side or unified)
        if action == "create":
            # For new files, just show generated content
            diff_view = self._build_generated_view(generated)
        else:
            # For modifications, show diff
            diff_view = self._build_diff_view(original, generated, file_name)

        return ft.Container(
            content=ft.Column(
                controls=[
                    header,
                    explanation_box,
                    diff_view
                ],
                spacing=10,
                expand=True,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=10
        )

    def _build_generated_view(self, generated: str) -> ft.Container:
        """Build view for newly created files (no diff needed)."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Generated Code:", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                    ft.Container(
                        content=ft.Text(
                            generated,
                            selectable=True,
                            font_family="Courier New"
                        ),
                        padding=10,
                        bgcolor=ft.Colors.BLACK,
                        border=ft.border.all(2, ft.Colors.GREEN_400),
                        border_radius=5
                    )
                ],
                spacing=5
            ),
            expand=True
        )

    def _build_diff_view(self, original: str, generated: str, file_name: str) -> ft.Container:
        """Build unified diff view for modified files."""
        # Generate unified diff
        original_lines = original.splitlines(keepends=True)
        generated_lines = generated.splitlines(keepends=True)

        diff = unified_diff(
            original_lines,
            generated_lines,
            fromfile=f"{file_name} (Original)",
            tofile=f"{file_name} (Generated)",
            lineterm=""
        )

        # Build diff display with color coding
        diff_lines = []
        for line in diff:
            if line.startswith('+++') or line.startswith('---'):
                # File headers
                diff_lines.append(
                    ft.Text(
                        line,
                        color=ft.Colors.CYAN_400,
                        weight=ft.FontWeight.BOLD,
                        font_family="Courier New"
                    )
                )
            elif line.startswith('@@'):
                # Hunk headers
                diff_lines.append(
                    ft.Text(
                        line,
                        color=ft.Colors.PURPLE_400,
                        weight=ft.FontWeight.BOLD,
                        font_family="Courier New"
                    )
                )
            elif line.startswith('+'):
                # Additions
                diff_lines.append(
                    ft.Container(
                        content=ft.Text(
                            line,
                            color=ft.Colors.GREEN_400,
                            font_family="Courier New"
                        ),
                        bgcolor=ft.Colors.GREEN_900
                    )
                )
            elif line.startswith('-'):
                # Deletions
                diff_lines.append(
                    ft.Container(
                        content=ft.Text(
                            line,
                            color=ft.Colors.RED_400,
                            font_family="Courier New"
                        ),
                        bgcolor=ft.Colors.RED_900
                    )
                )
            else:
                # Context lines
                diff_lines.append(
                    ft.Text(
                        line,
                        color=ft.Colors.WHITE70,
                        font_family="Courier New"
                    )
                )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Diff:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                    ft.Container(
                        content=ft.Column(
                            controls=diff_lines,
                            spacing=0,
                            scroll=ft.ScrollMode.AUTO
                        ),
                        padding=10,
                        bgcolor=ft.Colors.BLACK,
                        border=ft.border.all(2, ft.Colors.BLUE_400),
                        border_radius=5,
                        height=400
                    )
                ],
                spacing=5
            ),
            expand=True
        )

    def _handle_approve(self, e):
        """Handle approve button click."""
        print("[CODE_PREVIEW] User approved all changes")
        self.on_approve()

    def _handle_reject_toggle(self, e):
        """Handle reject button click (show feedback field)."""
        print("[CODE_PREVIEW] User clicked reject, showing feedback field")
        # Show feedback field and submit button
        self.feedback_text.visible = True
        self.submit_feedback_button.visible = True
        # Hide approve and reject buttons
        self.approve_button.visible = False
        self.reject_button.visible = False
        # Update UI
        if e.page:
            e.page.update()

    def _handle_submit_feedback(self, e):
        """Handle feedback submission."""
        feedback = self.feedback_text.value or ""
        if not feedback.strip():
            # Show error if feedback is empty
            self.feedback_text.error_text = "Please provide feedback describing what to change"
            if e.page:
                e.page.update()
            return

        print(f"[CODE_PREVIEW] User rejected with feedback: {feedback[:100]}...")
        self.on_reject(feedback)

    def get_control(self) -> ft.Container:
        """Get the Flet control for this component."""
        return self.control


# Module exports
__all__ = ["CodePreviewPanel"]
