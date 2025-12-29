"""
Clarification Dialog Component for Pulse IDE (V2.2 - Two-Level Clarification).

Displays a modal dialog to collect user responses to clarification questions
from either the Router (request type ambiguity) or Planner (implementation details).

V2.2 Enhancements:
- Support for clarification_source (router vs. planner)
- Different headers/messages based on source
- Context field display for each question
- Thread-safe dialog management
"""

import flet as ft
from typing import Dict, List, Callable, Any


# ============================================================================
# Clarification Dialog
# ============================================================================

class ClarificationDialog:
    """
    Modal dialog for collecting clarification responses from the user.

    This component dynamically renders input fields based on question types
    and collects structured responses that are merged back into the agent state.

    Supported Question Types:
    - free_text: Text input field
    - multiple_choice: Radio buttons or dropdown
    - yes_no: Yes/No radio buttons

    Thread Safety:
        This dialog is designed to be opened from background agent threads
        using page.call_from_thread(). All UI updates must be thread-safe.
    """

    def __init__(
        self,
        page: ft.Page,
        questions: List[Dict[str, Any]],
        on_submit: Callable[[Dict[str, str]], None],
        clarification_source: str = "planner"
    ):
        """
        Initialize the Clarification Dialog (V2.2 Enhanced).

        Args:
            page: Flet page instance for dialog management.
            questions: List of question dictionaries with structure:
                {
                    "question": str,
                    "type": "free_text" | "multiple_choice" | "yes_no",
                    "options": List[str] (optional, for multiple_choice),
                    "context": str (optional, additional context for the question)
                }
            on_submit: Callback function to invoke with responses dict.
                Signature: on_submit(responses: Dict[str, str]) -> None
            clarification_source: "router" or "planner" (V2.2)
                - "router": Request type is ambiguous
                - "planner": Implementation details are ambiguous
        """
        self.page = page
        self.questions = questions
        self.on_submit_callback = on_submit
        self.clarification_source = clarification_source
        self.responses: Dict[str, str] = {}
        self.input_widgets: Dict[str, Any] = {}

        # Build the dialog
        self.dialog = self._build_dialog()

    def _build_dialog(self) -> ft.AlertDialog:
        """Build the modal dialog with dynamic question inputs (V2.2 Enhanced)."""

        # V2.2: Customize header and message based on clarification source
        if self.clarification_source == "router":
            dialog_title = "🔍 I need to understand your request better"
            dialog_message = "I'm not sure how to classify your request. Please help me understand what you're asking for:"
            title_color = ft.Colors.ORANGE_700
        else:  # planner
            dialog_title = "📋 I need more details to create a plan"
            dialog_message = "Your request is clear, but I need some additional information to generate an accurate plan:"
            title_color = ft.Colors.BLUE_700

        # Create input widgets for each question
        question_widgets = []

        for idx, question_data in enumerate(self.questions):
            question_text = question_data.get("question", "")
            question_type = question_data.get("type", "free_text")
            options = question_data.get("options", [])
            context = question_data.get("context", "")  # V2.2: Context field

            # Question label
            question_label = ft.Text(
                f"{idx + 1}. {question_text}",
                size=14,
                weight=ft.FontWeight.W_500
            )

            # V2.2: Context label (if provided)
            context_label = None
            if context:
                context_label = ft.Container(
                    content=ft.Text(
                        context,
                        size=12,
                        color=ft.Colors.GREY_600,
                        italic=True
                    ),
                    padding=ft.padding.only(left=20, top=5, bottom=5)
                )

            # Input widget based on type
            if question_type == "free_text":
                input_widget = ft.TextField(
                    label="Your answer",
                    multiline=False,
                    border_color=ft.Colors.BLUE_400,
                    focused_border_color=ft.Colors.BLUE_700,
                    on_change=lambda e, q=question_text: self._on_text_change(q, e.control.value)
                )
                self.input_widgets[question_text] = input_widget

            elif question_type == "yes_no":
                radio_group = ft.RadioGroup(
                    content=ft.Row([
                        ft.Radio(value="Yes", label="Yes"),
                        ft.Radio(value="No", label="No")
                    ]),
                    on_change=lambda e, q=question_text: self._on_radio_change(q, e.control.value)
                )
                input_widget = radio_group
                self.input_widgets[question_text] = input_widget

            elif question_type == "multiple_choice":
                if options:
                    radio_buttons = [ft.Radio(value=opt, label=opt) for opt in options]
                    radio_group = ft.RadioGroup(
                        content=ft.Column(radio_buttons, spacing=5),
                        on_change=lambda e, q=question_text: self._on_radio_change(q, e.control.value)
                    )
                    input_widget = radio_group
                    self.input_widgets[question_text] = input_widget
                else:
                    # Fallback to text input if no options provided
                    input_widget = ft.TextField(
                        label="Your answer",
                        on_change=lambda e, q=question_text: self._on_text_change(q, e.control.value)
                    )
                    self.input_widgets[question_text] = input_widget

            else:
                # Unknown type, fallback to text input
                input_widget = ft.TextField(
                    label="Your answer",
                    on_change=lambda e, q=question_text: self._on_text_change(q, e.control.value)
                )
                self.input_widgets[question_text] = input_widget

            # Add question, context, and input to list (V2.2: Include context if present)
            column_controls = [question_label]
            if context_label:
                column_controls.append(context_label)
            column_controls.append(input_widget)

            question_widgets.append(
                ft.Container(
                    content=ft.Column(column_controls, spacing=8),
                    padding=ft.padding.only(bottom=15)
                )
            )

        # Dialog content (V2.2: Use dynamic title and message)
        dialog_content = ft.Column(
            [
                ft.Text(
                    dialog_title,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=title_color
                ),
                ft.Divider(height=1, color=ft.Colors.GREY_400),
                ft.Text(
                    dialog_message,
                    size=13,
                    color=ft.Colors.GREY_700
                ),
                ft.Container(height=10),
                *question_widgets
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )

        # Dialog buttons
        submit_button = ft.ElevatedButton(
            "Submit",
            icon=ft.Icons.CHECK,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            on_click=self._on_submit
        )

        cancel_button = ft.TextButton(
            "Cancel",
            on_click=self._on_cancel
        )

        # Create dialog
        dialog = ft.AlertDialog(
            modal=True,
            title=None,
            content=ft.Container(
                content=dialog_content,
                width=500,
                padding=20
            ),
            actions=[
                cancel_button,
                submit_button
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        return dialog

    def _on_text_change(self, question: str, value: str):
        """Handle text input changes."""
        self.responses[question] = value

    def _on_radio_change(self, question: str, value: str):
        """Handle radio button changes."""
        self.responses[question] = value

    def _on_submit(self, e):
        """Handle submit button click."""
        # Validate that all questions have responses
        missing_responses = []
        for question_data in self.questions:
            question_text = question_data.get("question", "")
            if question_text not in self.responses or not self.responses[question_text]:
                missing_responses.append(question_text)

        if missing_responses:
            # Show error message
            self._show_validation_error(missing_responses)
            return

        # Close dialog
        self.close()

        # Invoke callback with responses
        self.on_submit_callback(self.responses)

    def _on_cancel(self, e):
        """Handle cancel button click."""
        self.close()

    def _show_validation_error(self, missing_questions: List[str]):
        """Show validation error for missing responses."""
        error_text = "Please answer all questions:\n" + "\n".join(
            f"- {q}" for q in missing_questions[:3]
        )

        # Add error banner to dialog
        if hasattr(self.dialog, "content") and hasattr(self.dialog.content, "content"):
            column = self.dialog.content.content
            if isinstance(column, ft.Column):
                # Check if error banner already exists
                if not any(isinstance(child, ft.Banner) for child in column.controls):
                    error_banner = ft.Container(
                        content=ft.Text(
                            error_text,
                            color=ft.Colors.RED_700,
                            size=12
                        ),
                        bgcolor=ft.Colors.RED_100,
                        border=ft.border.all(1, ft.Colors.RED_400),
                        border_radius=5,
                        padding=10
                    )
                    column.controls.insert(0, error_banner)
                    self.page.update()

    def open(self):
        """Open the clarification dialog."""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def close(self):
        """Close the clarification dialog."""
        if self.dialog:
            self.dialog.open = False
            self.page.update()


# ============================================================================
# Thread-Safe Helper Function
# ============================================================================

def show_clarification_dialog(
    page: ft.Page,
    questions: List[Dict[str, Any]],
    on_submit: Callable[[Dict[str, str]], None],
    clarification_source: str = "planner"
) -> None:
    """
    Thread-safe helper to show clarification dialog from background threads (V2.2).

    This function opens the dialog directly since it's already being called
    from within a background thread (via page.run_thread).

    Args:
        page: Flet page instance.
        questions: List of clarification question dictionaries.
        on_submit: Callback function for when user submits responses.
        clarification_source: "router" or "planner" (V2.2)

    Example:
        >>> def handle_responses(responses: Dict[str, str]):
        >>>     print(f"User answered: {responses}")
        >>>
        >>> questions = [
        >>>     {"question": "Where to add timer?", "type": "free_text"},
        >>>     {"question": "Timer duration?", "type": "free_text"}
        >>> ]
        >>>
        >>> # From background thread:
        >>> show_clarification_dialog(page, questions, handle_responses, "planner")
    """
    # V2.2: Fixed - No need for call_from_thread since we're already in a background thread
    dialog = ClarificationDialog(page, questions, on_submit, clarification_source)
    dialog.open()


# ============================================================================
# Module Exports
# ============================================================================

__all__ = ["ClarificationDialog", "show_clarification_dialog"]
