"""
Pulse IDE UI Package (Phase 7).

VS Code-style Flet UI components for Pulse IDE.
"""

from src.ui.app import main, PulseApp
from src.ui.bridge import UIBridge, get_ui_bridge, UIState, UIEvent
from src.ui.menu_bar import MenuBar, create_about_dialog
from src.ui.theme import VSCodeColors, Fonts, Spacing

__all__ = [
    # Main app
    "main",
    "PulseApp",
    # Bridge
    "UIBridge",
    "get_ui_bridge",
    "UIState",
    "UIEvent",
    # Menu
    "MenuBar",
    "create_about_dialog",
    # Theme
    "VSCodeColors",
    "Fonts",
    "Spacing",
]
