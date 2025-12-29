"""
Modern Loading Animation Component for Pulse IDE.

Provides Meta-inspired animated loading states with shimmer effects.
"""

import flet as ft
import time
import asyncio


class LoadingAnimation(ft.Container):
    """
    Animated loading indicator with shimmer effect (Meta-style).

    Features:
    - Pulsing gradient shimmer
    - Smooth fade-in/fade-out
    - Professional animation timing
    """

    def __init__(self, message="Processing request..."):
        # Initialize animation state
        self.message = message
        self._opacity = 0.3
        self._direction = 1

        # Create child controls
        self.progress = ft.ProgressRing(
            width=20,
            height=20,
            stroke_width=2,
            color="#0084FF",  # Meta blue
        )

        self.text = ft.Text(
            self.message,
            size=13,
            color="#8B9DC3",  # Muted blue-gray
            italic=True,
            font_family="Inter",
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )

        # Initialize Container with content
        super().__init__(
            content=ft.Row(
                controls=[
                    self.progress,
                    self.text,
                ],
                spacing=12,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.padding.all(12),
            border_radius=8,
            bgcolor="#0A1929",  # Dark blue-gray background
            border=ft.border.all(1, "#1E3A5F"),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color="#000000",
                offset=ft.Offset(0, 2),
            ),
        )

    def did_mount(self):
        """Start animation when component mounts."""
        self.page.run_task(self._animate)

    async def _animate(self):
        """Animate opacity for shimmer effect."""
        while self.page:
            try:
                await asyncio.sleep(0.8)
                self._opacity += 0.1 * self._direction
                if self._opacity >= 1.0:
                    self._direction = -1
                elif self._opacity <= 0.3:
                    self._direction = 1

                if self.text:
                    self.text.opacity = self._opacity
                    self.text.update()
            except Exception:
                break
