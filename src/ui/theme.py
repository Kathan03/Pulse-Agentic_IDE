"""
VS Code Dark Modern Theme Colors

Official VS Code Dark Modern theme color palette for Pulse IDE.
Based on: https://github.com/microsoft/vscode/blob/main/extensions/theme-defaults/themes/dark_modern.json

This file now integrates with the ThemeManager to support multiple themes.
"""

# Import theme system
try:
    from src.ui.themes import ThemeManager, DARK_THEME
    from src.core.settings import get_settings_manager

    # Initialize theme manager with user's saved theme preference
    _settings = get_settings_manager().load_settings()
    _saved_theme = _settings.get("preferences", {}).get("theme", "dark")
    _theme_manager = ThemeManager(initial_theme=_saved_theme)
    _current_theme = _theme_manager.get_current_theme()
except Exception as e:
    print(f"[WARNING] Could not load theme system, using fallback dark theme: {e}")
    _current_theme = None


class VSCodeColors:
    """VS Code Dark Modern theme color constants."""

    # Editor Colors
    EDITOR_BACKGROUND = "#1E1E1E"
    EDITOR_FOREGROUND = "#CCCCCC"
    EDITOR_LINE_NUMBER = "#858585"
    EDITOR_SELECTION_BACKGROUND = "#264F78"
    EDITOR_CURSOR = "#AEAFAD"

    # Sidebar Colors
    SIDEBAR_BACKGROUND = "#252526"
    SIDEBAR_FOREGROUND = "#CCCCCC"
    SIDEBAR_BORDER = "#2B2B2B"
    SIDEBAR_TITLE_FOREGROUND = "#CCCCCC"

    # Activity Bar Colors
    ACTIVITY_BAR_BACKGROUND = "#181818"
    ACTIVITY_BAR_FOREGROUND = "#D7D7D7"
    ACTIVITY_BAR_INACTIVE_FOREGROUND = "#868686"
    ACTIVITY_BAR_BORDER = "#2B2B2B"
    ACTIVITY_BAR_ACTIVE_BORDER = "#0078D4"

    # Panel Colors (Terminal, Output, etc.)
    PANEL_BACKGROUND = "#181818"
    PANEL_BORDER = "#2B2B2B"
    PANEL_TITLE_ACTIVE_FOREGROUND = "#E7E7E7"
    PANEL_TITLE_INACTIVE_FOREGROUND = "#9D9D9D"

    # Terminal Colors
    TERMINAL_BACKGROUND = "#0C0C0C"
    TERMINAL_FOREGROUND = "#CCCCCC"
    TERMINAL_CURSOR = "#FFFFFF"
    TERMINAL_SELECTION = "#264F78"

    # ANSI Colors for Terminal
    TERMINAL_ANSI_BLACK = "#0C0C0C"
    TERMINAL_ANSI_RED = "#C50F1F"
    TERMINAL_ANSI_GREEN = "#13A10E"
    TERMINAL_ANSI_YELLOW = "#C19C00"
    TERMINAL_ANSI_BLUE = "#0037DA"
    TERMINAL_ANSI_MAGENTA = "#881798"
    TERMINAL_ANSI_CYAN = "#3A96DD"
    TERMINAL_ANSI_WHITE = "#CCCCCC"
    TERMINAL_ANSI_BRIGHT_BLACK = "#767676"
    TERMINAL_ANSI_BRIGHT_RED = "#E74856"
    TERMINAL_ANSI_BRIGHT_GREEN = "#16C60C"
    TERMINAL_ANSI_BRIGHT_YELLOW = "#F9F1A5"
    TERMINAL_ANSI_BRIGHT_BLUE = "#3B78FF"
    TERMINAL_ANSI_BRIGHT_MAGENTA = "#B4009E"
    TERMINAL_ANSI_BRIGHT_CYAN = "#61D6D6"
    TERMINAL_ANSI_BRIGHT_WHITE = "#F2F2F2"

    # Button Colors
    BUTTON_BACKGROUND = "#0078D4"
    BUTTON_FOREGROUND = "#FFFFFF"
    BUTTON_HOVER_BACKGROUND = "#026EC1"
    BUTTON_BORDER = "#FFFFFF12"
    BUTTON_SECONDARY_BACKGROUND = "#313131"
    BUTTON_SECONDARY_FOREGROUND = "#CCCCCC"
    BUTTON_SECONDARY_HOVER = "#3C3C3C"

    # Input Colors
    INPUT_BACKGROUND = "#313131"
    INPUT_FOREGROUND = "#CCCCCC"
    INPUT_BORDER = "#3C3C3C"
    INPUT_PLACEHOLDER_FOREGROUND = "#999999"
    INPUT_ACTIVE_BORDER = "#0078D4"

    # Dropdown Colors
    DROPDOWN_BACKGROUND = "#313131"
    DROPDOWN_FOREGROUND = "#CCCCCC"
    DROPDOWN_BORDER = "#3C3C3C"
    DROPDOWN_LIST_BACKGROUND = "#252526"

    # Badge Colors
    BADGE_BACKGROUND = "#616161"
    BADGE_FOREGROUND = "#F8F8F8"

    # Tab Colors
    TAB_ACTIVE_BACKGROUND = "#1E1E1E"
    TAB_INACTIVE_BACKGROUND = "#2D2D2D"
    TAB_ACTIVE_FOREGROUND = "#FFFFFF"
    TAB_INACTIVE_FOREGROUND = "#969696"
    TAB_BORDER = "#252526"
    TAB_ACTIVE_BORDER = "#0078D4"
    TAB_ACTIVE_BORDER_TOP = "#0078D4"
    TAB_HOVER_BACKGROUND = "#2A2D2E"

    # Scrollbar Colors
    SCROLLBAR_SHADOW = "#00000033"
    SCROLLBAR_SLIDER_BACKGROUND = "#79797966"
    SCROLLBAR_SLIDER_HOVER = "#646464B3"
    SCROLLBAR_SLIDER_ACTIVE = "#BFBFBFB3"

    # Status Bar Colors
    STATUS_BAR_BACKGROUND = "#0078D4"
    STATUS_BAR_FOREGROUND = "#FFFFFF"
    STATUS_BAR_NO_FOLDER_BACKGROUND = "#68217A"
    STATUS_BAR_DEBUG_BACKGROUND = "#CC6633"

    # List Colors
    LIST_ACTIVE_SELECTION_BACKGROUND = "#04395E"
    LIST_ACTIVE_SELECTION_FOREGROUND = "#FFFFFF"
    LIST_HOVER_BACKGROUND = "#2A2D2E"
    LIST_HOVER_FOREGROUND = "#CCCCCC"
    LIST_INACTIVE_SELECTION_BACKGROUND = "#37373D"

    # Notification Colors
    NOTIFICATION_INFO_BACKGROUND = "#0078D4"
    NOTIFICATION_WARNING_BACKGROUND = "#CD9731"
    NOTIFICATION_ERROR_BACKGROUND = "#F48771"
    NOTIFICATION_SUCCESS_BACKGROUND = "#13A10E"

    # Splitter/Divider Colors
    SPLITTER_BACKGROUND = "#404040"
    SPLITTER_BORDER = "#505050"
    DIVIDER = "#2B2B2B"

    # Focus Border
    FOCUS_BORDER = "#0078D4"

    # Contrast Border
    CONTRAST_ACTIVE_BORDER = "#F38518"
    CONTRAST_BORDER = "#6FC3DF"

    # Widget Colors
    WIDGET_SHADOW = "#00000033"
    WIDGET_BORDER = "#313131"

    # Menu Colors
    MENU_BACKGROUND = "#252526"
    MENU_FOREGROUND = "#CCCCCC"
    MENU_SELECTION_BACKGROUND = "#04395E"
    MENU_SEPARATOR = "#454545"

    # Title Bar Colors
    TITLE_BAR_BACKGROUND = "#181818"
    TITLE_BAR_FOREGROUND = "#CCCCCC"

    # Link Colors
    LINK_FOREGROUND = "#3794FF"
    LINK_ACTIVE_FOREGROUND = "#3794FF"

    # Description Colors
    DESCRIPTION_FOREGROUND = "#9D9D9D"

    # Selection Colors
    SELECTION_BACKGROUND = "#264F78"
    SELECTION_FOREGROUND = "#FFFFFF"

    # Error/Warning/Info Colors
    ERROR_FOREGROUND = "#F48771"
    WARNING_FOREGROUND = "#CCA700"
    INFO_FOREGROUND = "#3794FF"
    SUCCESS_FOREGROUND = "#89D185"

    # Git Colors
    GIT_MODIFIED = "#E2C08D"
    GIT_ADDED = "#73C991"
    GIT_DELETED = "#C74E39"
    GIT_UNTRACKED = "#73C991"
    GIT_IGNORED = "#8C8C8C"


class Fonts:
    """Font family constants."""

    MONOSPACE = "Consolas, 'Courier New', monospace"
    MONOSPACE_PRIMARY = "Consolas"
    MONOSPACE_FALLBACK = "Courier New"

    SANS_SERIF = "Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    SANS_SERIF_PRIMARY = "Segoe UI"

    # Font Sizes
    FONT_SIZE_SMALL = 11
    FONT_SIZE_NORMAL = 13
    FONT_SIZE_MEDIUM = 14
    FONT_SIZE_LARGE = 16
    FONT_SIZE_TITLE = 18


class Spacing:
    """Spacing and padding constants."""

    PADDING_NONE = 0
    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 15
    PADDING_XLARGE = 20

    BORDER_RADIUS_NONE = 0
    BORDER_RADIUS_SMALL = 3
    BORDER_RADIUS_MEDIUM = 5
    BORDER_RADIUS_LARGE = 8

    BORDER_WIDTH = 1
    BORDER_WIDTH_THICK = 2


def load_logo_base64():
    """Load the logo image and return it as base64 string."""
    import base64
    from pathlib import Path

    try:
        logo_path = Path("assets/pulse_logo_orange_25x25.svg")
        if logo_path.exists():
            with open(logo_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"Error loading logo: {e}")
    return None


def create_logo_image(width=16, height=16, fit=None):
    """
    Create a Flet Image widget with the Pulse logo.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        fit: ImageFit option (default: CONTAIN)

    Returns:
        ft.Image widget or None if logo not found
    """
    import flet as ft

    logo_base64 = load_logo_base64()
    if logo_base64:
        return ft.Image(
            src_base64=logo_base64,
            width=width,
            height=height,
            fit=fit or ft.ImageFit.CONTAIN,
        )
    return None


def create_pulse_logo_canvas(width=230, height=140, stroke_color="#0078D4", stroke_width=3):
    """
    Create a custom Pulse logo using Flet canvas.

    The logo features:
    - ECG waveform (heartbeat line)
    - Circuit/agentic branches with nodes

    Args:
        width: Canvas width (default 230)
        height: Canvas height (default 140)
        stroke_color: Color of the logo lines (default VS Code blue)
        stroke_width: Width of the lines (default 3)

    Returns:
        ft.canvas.Canvas widget
    """
    import flet as ft
    import flet.canvas as cv

    # Stroke paint for all shapes
    stroke_paint = ft.Paint(
        stroke_width=stroke_width,
        style=ft.PaintingStyle.STROKE,
        color=stroke_color,
    )

    fill_paint = ft.Paint(
        style=ft.PaintingStyle.FILL,
        color=stroke_color,
    )

    # ECG waveform path (heartbeat line)
    ecg_path = cv.Path(
        [
            cv.Path.MoveTo(20, 80),   # baseline left
            cv.Path.LineTo(70, 80),   # flat
            cv.Path.LineTo(85, 50),   # sharp up
            cv.Path.LineTo(105, 110), # sharp down
            cv.Path.LineTo(125, 65),  # back up
            cv.Path.LineTo(150, 80),  # return to baseline
        ],
        paint=stroke_paint,
    )

    # Circuit / agentic branches (representing AI nodes)
    circuit_shapes = [
        # Main branch to first node
        cv.Line(150, 65, 200, 65, paint=stroke_paint),
        cv.Circle(210, 65, 6, paint=fill_paint),

        # Upper branch
        cv.Line(210, 65, 210, 40, paint=stroke_paint),
        cv.Circle(210, 35, 5, paint=fill_paint),

        # Lower branch
        cv.Line(210, 65, 210, 90, paint=stroke_paint),
        cv.Circle(210, 95, 5, paint=fill_paint),

        # Right extension
        cv.Line(210, 65, 230, 65, paint=stroke_paint),
    ]

    # Create canvas with all shapes
    logo_canvas = cv.Canvas(
        shapes=[ecg_path, *circuit_shapes],
        width=width,
        height=height,
    )

    return logo_canvas


# ============================================================================
# THEME SYSTEM INTEGRATION
# ============================================================================

# Override VSCodeColors with current theme if theme system is available
if _current_theme is not None:
    print(f"[INFO] Applying theme: {_saved_theme}")
    for attr_name in dir(_current_theme):
        if not attr_name.startswith('_'):
            setattr(VSCodeColors, attr_name, getattr(_current_theme, attr_name))


def get_theme_manager():
    """Get the global theme manager instance."""
    return _theme_manager


def reload_theme():
    """
    Reload theme from settings and update VSCodeColors.
    Call this after changing theme in settings to apply immediately.
    """
    global _theme_manager, _current_theme
    try:
        settings = get_settings_manager().load_settings()
        theme_name = settings.get("preferences", {}).get("theme", "dark")
        print(f"[INFO] Reloading theme: {theme_name}")

        _theme_manager.set_theme(theme_name)
        _current_theme = _theme_manager.get_current_theme()

        # Update VSCodeColors class with new theme
        for attr_name in dir(_current_theme):
            if not attr_name.startswith('_'):
                setattr(VSCodeColors, attr_name, getattr(_current_theme, attr_name))

        print(f"[INFO] Theme applied: {theme_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to reload theme: {e}")
        import traceback
        traceback.print_exc()
        return False