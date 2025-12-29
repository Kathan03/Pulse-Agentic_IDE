"""
Vibe Status Loader for Pulse IDE v2.6 (Phase 7).

Displays contextual status words during agent execution:
- Thinking: Wondering, Stewing, Cogitating, Hoping, Exploring, Preparing
- Context: Mustering, Coalescing, Ideating
- Action: Completing, Messaging, Uploading, Connecting, Affirming, Rejoicing, Celebrating

Features:
- Subtle fade animation on status change
- Rate-limited updates (2-3 seconds)
- Lifecycle-aware word selection
"""

import flet as ft
from typing import Optional
from src.ui.theme import VSCodeColors, Fonts, Spacing
from src.ui.bridge import VibeCategory, VIBE_WORDS, get_vibe_category


class VibeLoader:
    """
    Vibe status display component.

    Shows current agent status with subtle animation.
    Positioned near the input field in the chat panel.
    """

    def __init__(self):
        """Initialize VibeLoader."""
        self._current_vibe: str = ""
        self._visible: bool = False

        # Status text with fade effect
        self._status_text = ft.Text(
            "",
            size=Fonts.FONT_SIZE_SMALL,
            color=VSCodeColors.INFO_FOREGROUND,
            italic=True,
            animate_opacity=300,  # 300ms fade
            opacity=0.0
        )

        # Status icon (thinking indicator)
        self._status_icon = ft.ProgressRing(
            width=14,
            height=14,
            stroke_width=2,
            color=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER,
            visible=False
        )

        # Container with subtle styling
        self._container = ft.Container(
            content=ft.Row(
                controls=[
                    self._status_icon,
                    self._status_text
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=Spacing.BORDER_RADIUS_SMALL,
            visible=False,
            animate_opacity=300
        )

    def get_control(self) -> ft.Container:
        """Get the vibe loader control."""
        return self._container

    def show(self, vibe: str) -> None:
        """
        Show vibe status with fade-in effect.

        Args:
            vibe: Vibe status word (e.g., "Wondering", "Preparing").
        """
        self._current_vibe = vibe
        self._visible = True

        # Update text
        self._status_text.value = f"Pulse is {vibe}..."
        self._status_text.opacity = 1.0

        # Show progress ring
        self._status_icon.visible = True

        # Update color based on category
        category = get_vibe_category(vibe)
        if category == VibeCategory.THINKING:
            self._status_text.color = VSCodeColors.INFO_FOREGROUND
            self._status_icon.color = VSCodeColors.INFO_FOREGROUND
        elif category == VibeCategory.CONTEXT:
            self._status_text.color = VSCodeColors.WARNING_FOREGROUND
            self._status_icon.color = VSCodeColors.WARNING_FOREGROUND
        elif category == VibeCategory.ACTION:
            self._status_text.color = VSCodeColors.SUCCESS_FOREGROUND
            self._status_icon.color = VSCodeColors.SUCCESS_FOREGROUND
        else:
            # Default
            self._status_text.color = VSCodeColors.INFO_FOREGROUND
            self._status_icon.color = VSCodeColors.INFO_FOREGROUND

        # Show container
        self._container.visible = True

        # Update UI if mounted
        if self._container.page:
            self._container.update()

    def hide(self) -> None:
        """Hide vibe status with fade-out effect."""
        self._visible = False
        self._current_vibe = ""

        # Fade out
        self._status_text.opacity = 0.0
        self._status_icon.visible = False

        # Hide container after fade
        self._container.visible = False

        # Update UI if mounted
        if self._container.page:
            self._container.update()

    def update_vibe(self, vibe: str) -> None:
        """
        Update vibe status.

        Shows the loader if not visible, updates text if already visible.

        Args:
            vibe: Vibe status word.
        """
        if vibe:
            self.show(vibe)
        else:
            self.hide()

    @property
    def current_vibe(self) -> str:
        """Get current vibe status."""
        return self._current_vibe

    @property
    def is_visible(self) -> bool:
        """Check if vibe loader is visible."""
        return self._visible


class VibeStatusBar:
    """
    Vibe status bar for sidebar display.

    More prominent display for sidebar, shows full category context.
    """

    def __init__(self):
        """Initialize VibeStatusBar."""
        self._current_vibe: str = ""

        # Category indicator
        self._category_chip = ft.Container(
            content=ft.Text(
                "",
                size=Fonts.FONT_SIZE_SMALL - 1,
                color=ft.Colors.WHITE,
                weight=ft.FontWeight.BOLD
            ),
            bgcolor=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            border_radius=4,
            visible=False
        )

        # Status text
        self._status_text = ft.Text(
            "",
            size=Fonts.FONT_SIZE_SMALL,
            color=VSCodeColors.SIDEBAR_FOREGROUND,
            italic=True
        )

        # Progress indicator
        self._progress = ft.ProgressRing(
            width=12,
            height=12,
            stroke_width=2,
            color=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER,
            visible=False
        )

        # Main container
        self._container = ft.Container(
            content=ft.Row(
                controls=[
                    self._progress,
                    self._category_chip,
                    self._status_text
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.symmetric(horizontal=Spacing.PADDING_SMALL, vertical=4),
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
            border_radius=Spacing.BORDER_RADIUS_SMALL,
            border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
            visible=False
        )

    def get_control(self) -> ft.Container:
        """Get the status bar control."""
        return self._container

    def show(self, vibe: str) -> None:
        """Show status with vibe word."""
        self._current_vibe = vibe

        # Get category
        category = get_vibe_category(vibe)

        # Update category chip
        if category:
            category_text = self._category_chip.content
            if category == VibeCategory.THINKING:
                category_text.value = "THINK"
                self._category_chip.bgcolor = VSCodeColors.INFO_FOREGROUND
            elif category == VibeCategory.CONTEXT:
                category_text.value = "CTX"
                self._category_chip.bgcolor = VSCodeColors.WARNING_FOREGROUND
            elif category == VibeCategory.ACTION:
                category_text.value = "ACT"
                self._category_chip.bgcolor = VSCodeColors.SUCCESS_FOREGROUND
            self._category_chip.visible = True
        else:
            self._category_chip.visible = False

        # Update status text
        self._status_text.value = vibe

        # Show progress and container
        self._progress.visible = True
        self._container.visible = True

        # Update UI if mounted
        if self._container.page:
            self._container.update()

    def hide(self) -> None:
        """Hide status bar."""
        self._current_vibe = ""
        self._container.visible = False
        self._progress.visible = False
        self._category_chip.visible = False
        self._status_text.value = ""

        if self._container.page:
            self._container.update()

    def update_vibe(self, vibe: str) -> None:
        """Update vibe status."""
        if vibe:
            self.show(vibe)
        else:
            self.hide()


__all__ = [
    "VibeLoader",
    "VibeStatusBar",
]
