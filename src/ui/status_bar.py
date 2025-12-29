"""
Status Bar Component for Pulse IDE.

Simplified status bar showing "Powered by AI" text.
"""

import flet as ft
from src.ui.theme import VSCodeColors, Fonts, Spacing


class StatusBar:
    """
    Simplified status bar component showing "Powered by AI".
    """

    def __init__(self):
        """Initialize StatusBar."""
        self.container = self._build()

    def _build(self):
        """Build the status bar UI component with theme-aware styling."""
        return ft.Container(
            bgcolor=VSCodeColors.STATUS_BAR_BACKGROUND,  # Theme background
            padding=ft.padding.symmetric(horizontal=Spacing.PADDING_MEDIUM, vertical=8),
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.AUTO_AWESOME,
                        size=16,
                        color=VSCodeColors.STATUS_BAR_FOREGROUND,  # Theme foreground
                    ),
                    ft.Text(
                        "Powered by AI",
                        size=Fonts.FONT_SIZE_SMALL,
                        color=VSCodeColors.STATUS_BAR_FOREGROUND,  # Theme foreground
                        italic=True,
                    ),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

    def get_control(self):
        """Get the status bar control for adding to the page."""
        return self.container
