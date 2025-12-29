"""
Approval Modals for Pulse IDE v2.6 (Phase 7).

Deterministic approval gates for:
- Patch approval: Show unified diff, require Approve/Deny
- Terminal approval: Show command + risk label, require Execute/Deny

These modals are the ONLY path for patch application and terminal execution.
Graph execution pauses until user provides approval decision.
"""

import flet as ft
from typing import Callable, Dict, Any, Optional
from src.ui.theme import VSCodeColors, Fonts, Spacing


class PatchApprovalModal:
    """
    Patch approval modal dialog.

    Shows unified diff preview with syntax highlighting.
    Requires explicit Approve/Deny decision.
    """

    def __init__(
        self,
        page: ft.Page,
        on_approve: Callable[[], None],
        on_deny: Callable[[str], None],
    ):
        """
        Initialize PatchApprovalModal.

        Args:
            page: Flet Page for dialog display.
            on_approve: Callback when user approves.
            on_deny: Callback when user denies (receives feedback text).
        """
        self.page = page
        self.on_approve = on_approve
        self.on_deny = on_deny

        self._dialog: Optional[ft.AlertDialog] = None
        self._diff_text: Optional[ft.Text] = None
        self._feedback_field: Optional[ft.TextField] = None
        self._file_path_text: Optional[ft.Text] = None
        self._rationale_text: Optional[ft.Text] = None

    def show(self, patch_data: Dict[str, Any]) -> None:
        """
        Show the patch approval modal.

        Args:
            patch_data: PatchPlan as dict with keys:
                - file_path: Target file path
                - diff: Unified diff content
                - rationale: Why this patch is being applied
        """
        file_path = patch_data.get("file_path", "unknown")
        diff = patch_data.get("diff", "")
        rationale = patch_data.get("rationale", "No rationale provided")

        # Build diff display with syntax coloring
        diff_lines = []
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                diff_lines.append(
                    ft.Text(
                        line,
                        font_family=Fonts.MONOSPACE_PRIMARY,
                        size=Fonts.FONT_SIZE_SMALL,
                        color="#98C379",  # Green for additions
                        selectable=True,
                    )
                )
            elif line.startswith("-") and not line.startswith("---"):
                diff_lines.append(
                    ft.Text(
                        line,
                        font_family=Fonts.MONOSPACE_PRIMARY,
                        size=Fonts.FONT_SIZE_SMALL,
                        color="#E06C75",  # Red for deletions
                        selectable=True,
                    )
                )
            elif line.startswith("@@"):
                diff_lines.append(
                    ft.Text(
                        line,
                        font_family=Fonts.MONOSPACE_PRIMARY,
                        size=Fonts.FONT_SIZE_SMALL,
                        color="#61AFEF",  # Blue for hunk headers
                        selectable=True,
                    )
                )
            else:
                diff_lines.append(
                    ft.Text(
                        line,
                        font_family=Fonts.MONOSPACE_PRIMARY,
                        size=Fonts.FONT_SIZE_SMALL,
                        color=VSCodeColors.EDITOR_FOREGROUND,
                        selectable=True,
                    )
                )

        # Feedback field for rejection
        self._feedback_field = ft.TextField(
            label="Feedback (optional)",
            hint_text="Explain what's wrong or what you'd like instead...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            visible=False,
            width=500,
            text_size=Fonts.FONT_SIZE_NORMAL,
        )

        # Build dialog
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.DIFFERENCE,
                        color=VSCodeColors.WARNING_FOREGROUND,
                        size=24,
                    ),
                    ft.Text(
                        "Patch Approval Required",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        # File path
                        ft.Row(
                            controls=[
                                ft.Text(
                                    "File:",
                                    weight=ft.FontWeight.BOLD,
                                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                                ),
                                ft.Text(
                                    file_path,
                                    color=VSCodeColors.LINK_FOREGROUND,
                                    selectable=True,
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Container(height=4),
                        # Rationale
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(
                                        "Rationale:",
                                        weight=ft.FontWeight.BOLD,
                                        size=Fonts.FONT_SIZE_SMALL,
                                        color=VSCodeColors.DESCRIPTION_FOREGROUND,
                                    ),
                                    ft.Text(
                                        rationale,
                                        size=Fonts.FONT_SIZE_SMALL,
                                        color=VSCodeColors.EDITOR_FOREGROUND,
                                    ),
                                ],
                                spacing=4,
                            ),
                            padding=8,
                            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                            border_radius=Spacing.BORDER_RADIUS_SMALL,
                        ),
                        ft.Container(height=8),
                        # Diff preview
                        ft.Text(
                            "Changes:",
                            weight=ft.FontWeight.BOLD,
                            size=Fonts.FONT_SIZE_SMALL,
                            color=VSCodeColors.DESCRIPTION_FOREGROUND,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=diff_lines,
                                spacing=0,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            bgcolor="#1E1E2E",
                            padding=12,
                            border_radius=Spacing.BORDER_RADIUS_SMALL,
                            border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
                            height=300,
                        ),
                        ft.Container(height=8),
                        # Feedback field
                        self._feedback_field,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=600,
                height=500,
            ),
            actions=[
                ft.TextButton(
                    "Deny",
                    icon=ft.Icons.CLOSE,
                    on_click=self._handle_deny_click,
                    style=ft.ButtonStyle(
                        color=VSCodeColors.ERROR_FOREGROUND,
                    ),
                ),
                ft.ElevatedButton(
                    "Approve",
                    icon=ft.Icons.CHECK,
                    on_click=self._handle_approve,
                    style=ft.ButtonStyle(
                        bgcolor=VSCodeColors.SUCCESS_FOREGROUND,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Show dialog
        self.page.dialog = self._dialog
        self._dialog.open = True
        self.page.update()

    def _handle_approve(self, e) -> None:
        """Handle Approve button click."""
        self._close_dialog()
        self.on_approve()

    def _handle_deny_click(self, e) -> None:
        """Handle Deny button click - show feedback field or submit."""
        if not self._feedback_field.visible:
            # First click: show feedback field
            self._feedback_field.visible = True
            self.page.update()
        else:
            # Second click: submit denial with feedback
            feedback = self._feedback_field.value or ""
            self._close_dialog()
            self.on_deny(feedback)

    def _close_dialog(self) -> None:
        """Close the dialog."""
        if self._dialog:
            self._dialog.open = False
            self.page.update()


class TerminalApprovalModal:
    """
    Terminal command approval modal dialog.

    Shows command preview with risk label and rationale.
    Requires explicit Execute/Deny decision.
    """

    # Risk level colors
    RISK_COLORS = {
        "LOW": VSCodeColors.SUCCESS_FOREGROUND,
        "MEDIUM": VSCodeColors.WARNING_FOREGROUND,
        "HIGH": VSCodeColors.ERROR_FOREGROUND,
    }

    def __init__(
        self,
        page: ft.Page,
        on_execute: Callable[[], None],
        on_deny: Callable[[str], None],
    ):
        """
        Initialize TerminalApprovalModal.

        Args:
            page: Flet Page for dialog display.
            on_execute: Callback when user approves execution.
            on_deny: Callback when user denies (receives feedback text).
        """
        self.page = page
        self.on_execute = on_execute
        self.on_deny = on_deny

        self._dialog: Optional[ft.AlertDialog] = None
        self._feedback_field: Optional[ft.TextField] = None

    def show(self, command_data: Dict[str, Any]) -> None:
        """
        Show the terminal approval modal.

        Args:
            command_data: CommandPlan as dict with keys:
                - command: Command string to execute
                - rationale: Why this command is being executed
                - risk_label: "LOW", "MEDIUM", or "HIGH"
        """
        command = command_data.get("command", "")
        rationale = command_data.get("rationale", "No rationale provided")
        risk_label = command_data.get("risk_label", "MEDIUM")

        risk_color = self.RISK_COLORS.get(risk_label, VSCodeColors.WARNING_FOREGROUND)

        # Feedback field for rejection
        self._feedback_field = ft.TextField(
            label="Feedback (optional)",
            hint_text="Explain why this command shouldn't run...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            visible=False,
            width=450,
            text_size=Fonts.FONT_SIZE_NORMAL,
        )

        # Build dialog
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.TERMINAL,
                        color=risk_color,
                        size=24,
                    ),
                    ft.Text(
                        "Terminal Command Approval",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        # Risk label badge
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(
                                        f"RISK: {risk_label}",
                                        size=Fonts.FONT_SIZE_SMALL,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE,
                                    ),
                                    bgcolor=risk_color,
                                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                                    border_radius=4,
                                ),
                            ],
                        ),
                        ft.Container(height=12),
                        # Command display
                        ft.Text(
                            "Command:",
                            weight=ft.FontWeight.BOLD,
                            size=Fonts.FONT_SIZE_SMALL,
                            color=VSCodeColors.DESCRIPTION_FOREGROUND,
                        ),
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        "$ ",
                                        font_family=Fonts.MONOSPACE_PRIMARY,
                                        size=Fonts.FONT_SIZE_NORMAL,
                                        color=VSCodeColors.TERMINAL_ANSI_BRIGHT_GREEN,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        command,
                                        font_family=Fonts.MONOSPACE_PRIMARY,
                                        size=Fonts.FONT_SIZE_NORMAL,
                                        color=VSCodeColors.TERMINAL_FOREGROUND,
                                        selectable=True,
                                    ),
                                ],
                                spacing=0,
                            ),
                            bgcolor=VSCodeColors.TERMINAL_BACKGROUND,
                            padding=12,
                            border_radius=Spacing.BORDER_RADIUS_SMALL,
                            border=ft.border.all(1, risk_color),
                        ),
                        ft.Container(height=12),
                        # Rationale
                        ft.Text(
                            "Rationale:",
                            weight=ft.FontWeight.BOLD,
                            size=Fonts.FONT_SIZE_SMALL,
                            color=VSCodeColors.DESCRIPTION_FOREGROUND,
                        ),
                        ft.Container(
                            content=ft.Text(
                                rationale,
                                size=Fonts.FONT_SIZE_SMALL,
                                color=VSCodeColors.EDITOR_FOREGROUND,
                            ),
                            padding=8,
                            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                            border_radius=Spacing.BORDER_RADIUS_SMALL,
                        ),
                        ft.Container(height=12),
                        # Warning for HIGH risk
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.WARNING,
                                        color=VSCodeColors.WARNING_FOREGROUND,
                                        size=16,
                                    ),
                                    ft.Text(
                                        "This command will be executed in your terminal. "
                                        "Review carefully before approving.",
                                        size=Fonts.FONT_SIZE_SMALL - 1,
                                        color=VSCodeColors.WARNING_FOREGROUND,
                                    ),
                                ],
                                spacing=6,
                            ),
                            visible=risk_label in ["MEDIUM", "HIGH"],
                        ),
                        ft.Container(height=8),
                        # Feedback field
                        self._feedback_field,
                    ],
                ),
                width=500,
                padding=8,
            ),
            actions=[
                ft.TextButton(
                    "Deny",
                    icon=ft.Icons.CLOSE,
                    on_click=self._handle_deny_click,
                    style=ft.ButtonStyle(
                        color=VSCodeColors.ERROR_FOREGROUND,
                    ),
                ),
                ft.ElevatedButton(
                    "Execute",
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=self._handle_execute,
                    style=ft.ButtonStyle(
                        bgcolor=risk_color if risk_label != "HIGH" else VSCodeColors.ERROR_FOREGROUND,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Show dialog
        self.page.dialog = self._dialog
        self._dialog.open = True
        self.page.update()

    def _handle_execute(self, e) -> None:
        """Handle Execute button click."""
        self._close_dialog()
        self.on_execute()

    def _handle_deny_click(self, e) -> None:
        """Handle Deny button click - show feedback field or submit."""
        if not self._feedback_field.visible:
            # First click: show feedback field
            self._feedback_field.visible = True
            self.page.update()
        else:
            # Second click: submit denial with feedback
            feedback = self._feedback_field.value or ""
            self._close_dialog()
            self.on_deny(feedback)

    def _close_dialog(self) -> None:
        """Close the dialog."""
        if self._dialog:
            self._dialog.open = False
            self.page.update()


def show_patch_approval(
    page: ft.Page,
    patch_data: Dict[str, Any],
    on_approve: Callable[[], None],
    on_deny: Callable[[str], None],
) -> PatchApprovalModal:
    """
    Helper function to show patch approval modal.

    Args:
        page: Flet Page.
        patch_data: PatchPlan as dict.
        on_approve: Callback for approval.
        on_deny: Callback for denial.

    Returns:
        PatchApprovalModal instance.
    """
    modal = PatchApprovalModal(page, on_approve, on_deny)
    modal.show(patch_data)
    return modal


def show_terminal_approval(
    page: ft.Page,
    command_data: Dict[str, Any],
    on_execute: Callable[[], None],
    on_deny: Callable[[str], None],
) -> TerminalApprovalModal:
    """
    Helper function to show terminal approval modal.

    Args:
        page: Flet Page.
        command_data: CommandPlan as dict.
        on_execute: Callback for execution.
        on_deny: Callback for denial.

    Returns:
        TerminalApprovalModal instance.
    """
    modal = TerminalApprovalModal(page, on_execute, on_deny)
    modal.show(command_data)
    return modal


__all__ = [
    "PatchApprovalModal",
    "TerminalApprovalModal",
    "show_patch_approval",
    "show_terminal_approval",
]
