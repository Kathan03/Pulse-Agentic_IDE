"""
Comprehensive Theme System for Pulse IDE

Supports 3 themes: Light, Dark, Midnight
Each theme provides complete color palettes for all UI components.
"""
import flet as ft
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ThemeColors:
    """Complete color palette for a theme."""

    # Editor Colors
    EDITOR_BACKGROUND: str
    EDITOR_FOREGROUND: str
    EDITOR_LINE_NUMBER: str
    EDITOR_SELECTION_BACKGROUND: str
    EDITOR_CURSOR: str

    # Sidebar Colors
    SIDEBAR_BACKGROUND: str
    SIDEBAR_FOREGROUND: str
    SIDEBAR_BORDER: str
    SIDEBAR_TITLE_FOREGROUND: str

    # Activity Bar Colors
    ACTIVITY_BAR_BACKGROUND: str
    ACTIVITY_BAR_FOREGROUND: str
    ACTIVITY_BAR_INACTIVE_FOREGROUND: str
    ACTIVITY_BAR_BORDER: str
    ACTIVITY_BAR_ACTIVE_BORDER: str

    # Panel Colors (Terminal, Output, etc.)
    PANEL_BACKGROUND: str
    PANEL_BORDER: str
    PANEL_TITLE_ACTIVE_FOREGROUND: str
    PANEL_TITLE_INACTIVE_FOREGROUND: str

    # Terminal Colors
    TERMINAL_BACKGROUND: str
    TERMINAL_FOREGROUND: str
    TERMINAL_CURSOR: str
    TERMINAL_SELECTION: str

    # Button Colors
    BUTTON_BACKGROUND: str
    BUTTON_FOREGROUND: str
    BUTTON_HOVER_BACKGROUND: str
    BUTTON_BORDER: str
    BUTTON_SECONDARY_BACKGROUND: str
    BUTTON_SECONDARY_FOREGROUND: str
    BUTTON_SECONDARY_HOVER: str

    # Input Colors
    INPUT_BACKGROUND: str
    INPUT_FOREGROUND: str
    INPUT_BORDER: str
    INPUT_PLACEHOLDER_FOREGROUND: str
    INPUT_ACTIVE_BORDER: str

    # Dropdown Colors
    DROPDOWN_BACKGROUND: str
    DROPDOWN_FOREGROUND: str
    DROPDOWN_BORDER: str
    DROPDOWN_LIST_BACKGROUND: str

    # Tab Colors
    TAB_ACTIVE_BACKGROUND: str
    TAB_INACTIVE_BACKGROUND: str
    TAB_ACTIVE_FOREGROUND: str
    TAB_INACTIVE_FOREGROUND: str
    TAB_BORDER: str
    TAB_ACTIVE_BORDER: str
    TAB_HOVER_BACKGROUND: str

    # Status Bar Colors
    STATUS_BAR_BACKGROUND: str
    STATUS_BAR_FOREGROUND: str

    # List Colors
    LIST_ACTIVE_SELECTION_BACKGROUND: str
    LIST_ACTIVE_SELECTION_FOREGROUND: str
    LIST_HOVER_BACKGROUND: str
    LIST_HOVER_FOREGROUND: str

    # Notification Colors
    NOTIFICATION_INFO_BACKGROUND: str
    NOTIFICATION_WARNING_BACKGROUND: str
    NOTIFICATION_ERROR_BACKGROUND: str
    NOTIFICATION_SUCCESS_BACKGROUND: str

    # Splitter/Divider Colors
    SPLITTER_BACKGROUND: str
    SPLITTER_BORDER: str
    DIVIDER: str

    # Focus Border
    FOCUS_BORDER: str

    # Menu Colors
    MENU_BACKGROUND: str
    MENU_FOREGROUND: str
    MENU_SELECTION_BACKGROUND: str
    MENU_SEPARATOR: str

    # Title Bar Colors
    TITLE_BAR_BACKGROUND: str
    TITLE_BAR_FOREGROUND: str

    # Link Colors
    LINK_FOREGROUND: str

    # Description Colors
    DESCRIPTION_FOREGROUND: str

    # Error/Warning/Info Colors
    ERROR_FOREGROUND: str
    WARNING_FOREGROUND: str
    INFO_FOREGROUND: str
    SUCCESS_FOREGROUND: str

    # Logo/SVG Colors
    LOGO_PRIMARY: str
    LOGO_SECONDARY: str
    LOGO_ACCENT: str


# ============================================================================
# DARK THEME (VS Code Dark Modern)
# ============================================================================

DARK_THEME = ThemeColors(
    # Editor
    EDITOR_BACKGROUND="#1E1E1E",
    EDITOR_FOREGROUND="#CCCCCC",
    EDITOR_LINE_NUMBER="#858585",
    EDITOR_SELECTION_BACKGROUND="#264F78",
    EDITOR_CURSOR="#AEAFAD",

    # Sidebar
    SIDEBAR_BACKGROUND="#252526",
    SIDEBAR_FOREGROUND="#CCCCCC",
    SIDEBAR_BORDER="#2B2B2B",
    SIDEBAR_TITLE_FOREGROUND="#CCCCCC",

    # Activity Bar
    ACTIVITY_BAR_BACKGROUND="#181818",
    ACTIVITY_BAR_FOREGROUND="#D7D7D7",
    ACTIVITY_BAR_INACTIVE_FOREGROUND="#868686",
    ACTIVITY_BAR_BORDER="#2B2B2B",
    ACTIVITY_BAR_ACTIVE_BORDER="#0078D4",

    # Panel
    PANEL_BACKGROUND="#181818",
    PANEL_BORDER="#2B2B2B",
    PANEL_TITLE_ACTIVE_FOREGROUND="#E7E7E7",
    PANEL_TITLE_INACTIVE_FOREGROUND="#9D9D9D",

    # Terminal
    TERMINAL_BACKGROUND="#0C0C0C",
    TERMINAL_FOREGROUND="#CCCCCC",
    TERMINAL_CURSOR="#FFFFFF",
    TERMINAL_SELECTION="#264F78",

    # Buttons
    BUTTON_BACKGROUND="#0078D4",
    BUTTON_FOREGROUND="#FFFFFF",
    BUTTON_HOVER_BACKGROUND="#026EC1",
    BUTTON_BORDER="#FFFFFF12",
    BUTTON_SECONDARY_BACKGROUND="#313131",
    BUTTON_SECONDARY_FOREGROUND="#CCCCCC",
    BUTTON_SECONDARY_HOVER="#3C3C3C",

    # Input
    INPUT_BACKGROUND="#313131",
    INPUT_FOREGROUND="#CCCCCC",
    INPUT_BORDER="#3C3C3C",
    INPUT_PLACEHOLDER_FOREGROUND="#999999",
    INPUT_ACTIVE_BORDER="#0078D4",

    # Dropdown
    DROPDOWN_BACKGROUND="#313131",
    DROPDOWN_FOREGROUND="#CCCCCC",
    DROPDOWN_BORDER="#3C3C3C",
    DROPDOWN_LIST_BACKGROUND="#252526",

    # Tabs
    TAB_ACTIVE_BACKGROUND="#1E1E1E",
    TAB_INACTIVE_BACKGROUND="#2D2D2D",
    TAB_ACTIVE_FOREGROUND="#FFFFFF",
    TAB_INACTIVE_FOREGROUND="#969696",
    TAB_BORDER="#252526",
    TAB_ACTIVE_BORDER="#0078D4",
    TAB_HOVER_BACKGROUND="#2A2D2E",

    # Status Bar
    STATUS_BAR_BACKGROUND="#0078D4",
    STATUS_BAR_FOREGROUND="#FFFFFF",

    # List
    LIST_ACTIVE_SELECTION_BACKGROUND="#04395E",
    LIST_ACTIVE_SELECTION_FOREGROUND="#FFFFFF",
    LIST_HOVER_BACKGROUND="#2A2D2E",
    LIST_HOVER_FOREGROUND="#CCCCCC",

    # Notifications
    NOTIFICATION_INFO_BACKGROUND="#0078D4",
    NOTIFICATION_WARNING_BACKGROUND="#CD9731",
    NOTIFICATION_ERROR_BACKGROUND="#F48771",
    NOTIFICATION_SUCCESS_BACKGROUND="#13A10E",

    # Splitter/Divider
    SPLITTER_BACKGROUND="#404040",
    SPLITTER_BORDER="#505050",
    DIVIDER="#2B2B2B",

    # Focus
    FOCUS_BORDER="#0078D4",

    # Menu
    MENU_BACKGROUND="#252526",
    MENU_FOREGROUND="#CCCCCC",
    MENU_SELECTION_BACKGROUND="#04395E",
    MENU_SEPARATOR="#454545",

    # Title Bar
    TITLE_BAR_BACKGROUND="#181818",
    TITLE_BAR_FOREGROUND="#CCCCCC",

    # Link
    LINK_FOREGROUND="#3794FF",

    # Description
    DESCRIPTION_FOREGROUND="#9D9D9D",

    # Status
    ERROR_FOREGROUND="#F48771",
    WARNING_FOREGROUND="#CCA700",
    INFO_FOREGROUND="#3794FF",
    SUCCESS_FOREGROUND="#89D185",

    # Logo/SVG
    LOGO_PRIMARY="#FF7A00",  # Orange
    LOGO_SECONDARY="#FFFFFF",  # White
    LOGO_ACCENT="#0078D4",  # Blue
)


# ============================================================================
# LIGHT THEME
# ============================================================================

LIGHT_THEME = ThemeColors(
    # Editor
    EDITOR_BACKGROUND="#FFFFFF",
    EDITOR_FOREGROUND="#000000",
    EDITOR_LINE_NUMBER="#237893",
    EDITOR_SELECTION_BACKGROUND="#ADD6FF",
    EDITOR_CURSOR="#000000",

    # Sidebar
    SIDEBAR_BACKGROUND="#F3F3F3",
    SIDEBAR_FOREGROUND="#383838",
    SIDEBAR_BORDER="#E5E5E5",
    SIDEBAR_TITLE_FOREGROUND="#383838",

    # Activity Bar
    ACTIVITY_BAR_BACKGROUND="#2C2C2C",
    ACTIVITY_BAR_FOREGROUND="#FFFFFF",
    ACTIVITY_BAR_INACTIVE_FOREGROUND="#CCCCCC",
    ACTIVITY_BAR_BORDER="#6B6B6B",
    ACTIVITY_BAR_ACTIVE_BORDER="#007ACC",

    # Panel
    PANEL_BACKGROUND="#F3F3F3",
    PANEL_BORDER="#E5E5E5",
    PANEL_TITLE_ACTIVE_FOREGROUND="#383838",
    PANEL_TITLE_INACTIVE_FOREGROUND="#717171",

    # Terminal
    TERMINAL_BACKGROUND="#FFFFFF",
    TERMINAL_FOREGROUND="#000000",
    TERMINAL_CURSOR="#000000",
    TERMINAL_SELECTION="#ADD6FF",

    # Buttons
    BUTTON_BACKGROUND="#007ACC",
    BUTTON_FOREGROUND="#FFFFFF",
    BUTTON_HOVER_BACKGROUND="#005A9E",
    BUTTON_BORDER="#00000014",
    BUTTON_SECONDARY_BACKGROUND="#E5E5E5",
    BUTTON_SECONDARY_FOREGROUND="#000000",
    BUTTON_SECONDARY_HOVER="#D3D3D3",

    # Input
    INPUT_BACKGROUND="#FFFFFF",
    INPUT_FOREGROUND="#000000",
    INPUT_BORDER="#CECECE",
    INPUT_PLACEHOLDER_FOREGROUND="#767676",
    INPUT_ACTIVE_BORDER="#007ACC",

    # Dropdown
    DROPDOWN_BACKGROUND="#FFFFFF",
    DROPDOWN_FOREGROUND="#000000",
    DROPDOWN_BORDER="#CECECE",
    DROPDOWN_LIST_BACKGROUND="#FFFFFF",

    # Tabs
    TAB_ACTIVE_BACKGROUND="#FFFFFF",
    TAB_INACTIVE_BACKGROUND="#ECECEC",
    TAB_ACTIVE_FOREGROUND="#333333",
    TAB_INACTIVE_FOREGROUND="#717171",
    TAB_BORDER="#F3F3F3",
    TAB_ACTIVE_BORDER="#007ACC",
    TAB_HOVER_BACKGROUND="#ECECEC",

    # Status Bar
    STATUS_BAR_BACKGROUND="#007ACC",
    STATUS_BAR_FOREGROUND="#FFFFFF",

    # List
    LIST_ACTIVE_SELECTION_BACKGROUND="#0060C0",
    LIST_ACTIVE_SELECTION_FOREGROUND="#FFFFFF",
    LIST_HOVER_BACKGROUND="#E8E8E8",
    LIST_HOVER_FOREGROUND="#000000",

    # Notifications
    NOTIFICATION_INFO_BACKGROUND="#007ACC",
    NOTIFICATION_WARNING_BACKGROUND="#FF8C00",
    NOTIFICATION_ERROR_BACKGROUND="#E51400",
    NOTIFICATION_SUCCESS_BACKGROUND="#107C10",

    # Splitter/Divider
    SPLITTER_BACKGROUND="#D0D0D0",
    SPLITTER_BORDER="#CECECE",
    DIVIDER="#E5E5E5",

    # Focus
    FOCUS_BORDER="#007ACC",

    # Menu
    MENU_BACKGROUND="#F3F3F3",
    MENU_FOREGROUND="#383838",
    MENU_SELECTION_BACKGROUND="#0060C0",
    MENU_SEPARATOR="#E5E5E5",

    # Title Bar
    TITLE_BAR_BACKGROUND="#F3F3F3",  # Light background matching sidebar
    TITLE_BAR_FOREGROUND="#383838",  # Dark text for good contrast

    # Link
    LINK_FOREGROUND="#007ACC",

    # Description
    DESCRIPTION_FOREGROUND="#717171",

    # Status
    ERROR_FOREGROUND="#E51400",
    WARNING_FOREGROUND="#BF8803",
    INFO_FOREGROUND="#007ACC",
    SUCCESS_FOREGROUND="#107C10",

    # Logo/SVG
    LOGO_PRIMARY="#FF7A00",  # Orange
    LOGO_SECONDARY="#2C2C2C",  # Dark Gray
    LOGO_ACCENT="#007ACC",  # Blue
)


# ============================================================================
# MIDNIGHT THEME (Deep Blue - Log Panel Inspired)
# ============================================================================

MIDNIGHT_THEME = ThemeColors(
    # Editor
    EDITOR_BACKGROUND="#0D1117",
    EDITOR_FOREGROUND="#E6EDF3",
    EDITOR_LINE_NUMBER="#6E7681",
    EDITOR_SELECTION_BACKGROUND="#1F3A5F",
    EDITOR_CURSOR="#C9D1D9",

    # Sidebar
    SIDEBAR_BACKGROUND="#161B22",
    SIDEBAR_FOREGROUND="#E6EDF3",
    SIDEBAR_BORDER="#21262D",
    SIDEBAR_TITLE_FOREGROUND="#E6EDF3",

    # Activity Bar
    ACTIVITY_BAR_BACKGROUND="#010409",
    ACTIVITY_BAR_FOREGROUND="#E6EDF3",
    ACTIVITY_BAR_INACTIVE_FOREGROUND="#8B9DC3",
    ACTIVITY_BAR_BORDER="#21262D",
    ACTIVITY_BAR_ACTIVE_BORDER="#0084FF",

    # Panel
    PANEL_BACKGROUND="#161B22",
    PANEL_BORDER="#21262D",
    PANEL_TITLE_ACTIVE_FOREGROUND="#E6EDF3",
    PANEL_TITLE_INACTIVE_FOREGROUND="#8B9DC3",

    # Terminal
    TERMINAL_BACKGROUND="#010409",
    TERMINAL_FOREGROUND="#E6EDF3",
    TERMINAL_CURSOR="#58A6FF",
    TERMINAL_SELECTION="#1F3A5F",

    # Buttons
    BUTTON_BACKGROUND="#0084FF",
    BUTTON_FOREGROUND="#FFFFFF",
    BUTTON_HOVER_BACKGROUND="#0070E0",
    BUTTON_BORDER="#30363D",
    BUTTON_SECONDARY_BACKGROUND="#21262D",
    BUTTON_SECONDARY_FOREGROUND="#E6EDF3",
    BUTTON_SECONDARY_HOVER="#30363D",

    # Input
    INPUT_BACKGROUND="#0D1117",
    INPUT_FOREGROUND="#E6EDF3",
    INPUT_BORDER="#30363D",
    INPUT_PLACEHOLDER_FOREGROUND="#8B9DC3",
    INPUT_ACTIVE_BORDER="#0084FF",

    # Dropdown
    DROPDOWN_BACKGROUND="#0D1117",
    DROPDOWN_FOREGROUND="#E6EDF3",
    DROPDOWN_BORDER="#30363D",
    DROPDOWN_LIST_BACKGROUND="#161B22",

    # Tabs
    TAB_ACTIVE_BACKGROUND="#0D1117",
    TAB_INACTIVE_BACKGROUND="#21262D",
    TAB_ACTIVE_FOREGROUND="#FFFFFF",
    TAB_INACTIVE_FOREGROUND="#8B9DC3",
    TAB_BORDER="#21262D",
    TAB_ACTIVE_BORDER="#0084FF",
    TAB_HOVER_BACKGROUND="#161B22",

    # Status Bar
    STATUS_BAR_BACKGROUND="#0084FF",
    STATUS_BAR_FOREGROUND="#FFFFFF",

    # List
    LIST_ACTIVE_SELECTION_BACKGROUND="#1F3A5F",
    LIST_ACTIVE_SELECTION_FOREGROUND="#FFFFFF",
    LIST_HOVER_BACKGROUND="#161B22",
    LIST_HOVER_FOREGROUND="#E6EDF3",

    # Notifications
    NOTIFICATION_INFO_BACKGROUND="#0084FF",
    NOTIFICATION_WARNING_BACKGROUND="#FF9500",
    NOTIFICATION_ERROR_BACKGROUND="#FF375F",
    NOTIFICATION_SUCCESS_BACKGROUND="#26A641",

    # Splitter/Divider
    SPLITTER_BACKGROUND="#30363D",
    SPLITTER_BORDER="#484F58",
    DIVIDER="#21262D",

    # Focus
    FOCUS_BORDER="#0084FF",

    # Menu
    MENU_BACKGROUND="#161B22",
    MENU_FOREGROUND="#E6EDF3",
    MENU_SELECTION_BACKGROUND="#1F3A5F",
    MENU_SEPARATOR="#30363D",

    # Title Bar
    TITLE_BAR_BACKGROUND="#010409",
    TITLE_BAR_FOREGROUND="#E6EDF3",

    # Link
    LINK_FOREGROUND="#58A6FF",

    # Description
    DESCRIPTION_FOREGROUND="#8B9DC3",

    # Status
    ERROR_FOREGROUND="#FF7B72",
    WARNING_FOREGROUND="#FFA657",
    INFO_FOREGROUND="#58A6FF",
    SUCCESS_FOREGROUND="#56D364",

    # Logo/SVG
    LOGO_PRIMARY="#0084FF",  # Bright Blue
    LOGO_SECONDARY="#E6EDF3",  # Light Gray
    LOGO_ACCENT="#58A6FF",  # Medium Blue
)


# ============================================================================
# THEME MANAGER
# ============================================================================

class ThemeManager:
    """Manages theme switching across the application."""

    THEMES = {
        "light": LIGHT_THEME,
        "dark": DARK_THEME,
        "midnight": MIDNIGHT_THEME,
    }

    def __init__(self, initial_theme: str = "dark"):
        """
        Initialize ThemeManager.

        Args:
            initial_theme: Initial theme name ("light", "dark", or "midnight")
        """
        self._current_theme_name = initial_theme
        self._current_theme = self.THEMES[initial_theme]
        self._callbacks = []

    def get_current_theme(self) -> ThemeColors:
        """Get the current theme colors."""
        return self._current_theme

    def get_current_theme_name(self) -> str:
        """Get the current theme name."""
        return self._current_theme_name

    def set_theme(self, theme_name: str) -> None:
        """
        Set the active theme.

        Args:
            theme_name: Theme name ("light", "dark", or "midnight")
        """
        if theme_name not in self.THEMES:
            raise ValueError(f"Unknown theme: {theme_name}")

        self._current_theme_name = theme_name
        self._current_theme = self.THEMES[theme_name]

        # Notify all registered callbacks
        for callback in self._callbacks:
            callback(self._current_theme)

    def register_callback(self, callback):
        """Register a callback to be called when theme changes."""
        self._callbacks.append(callback)

    def get_flet_theme_mode(self) -> ft.ThemeMode:
        """Get Flet theme mode for current theme."""
        if self._current_theme_name == "light":
            return ft.ThemeMode.LIGHT
        else:
            return ft.ThemeMode.DARK


# Global theme manager instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def get_current_theme() -> ThemeColors:
    """Get current theme colors."""
    return get_theme_manager().get_current_theme()
