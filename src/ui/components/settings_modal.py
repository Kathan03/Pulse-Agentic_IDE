"""
Settings Modal for Pulse IDE v2.6 (Phase 7).

VS Code-style settings dialog with tabs for:
- API Keys (secure input fields)
- Models (dropdown selections)
- Agent Toggles (CrewAI Builder, AutoGen Auditor)

Settings are persisted via platformdirs (OS-standard path).
"""

import flet as ft
from typing import Optional, Callable, Dict, Any
from src.ui.theme import VSCodeColors, Fonts, Spacing
from src.core.settings import get_settings_manager, SettingsManager


class SettingsModal:
    """
    Settings modal dialog.

    Reads/writes settings using SettingsManager (platformdirs).
    """

    # Available models for dropdowns (13 models from CLAUDE.md)
    AVAILABLE_MODELS = [
        # OpenAI GPT-5.x Series
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5.1-codex",
        "gpt-5.2-pro",
        # OpenAI GPT-4.1.x Series
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        # Anthropic Claude 4.5 Series
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
    ]

    def __init__(self, page: ft.Page, on_save: Optional[Callable[[], None]] = None):
        """
        Initialize SettingsModal.

        Args:
            page: Flet Page for dialog display.
            on_save: Optional callback after settings are saved.
        """
        self.page = page
        self.on_save = on_save
        self.settings_manager: SettingsManager = get_settings_manager()

        # Current settings snapshot
        self._settings: Dict[str, Any] = {}

        # UI controls (initialized in _build)
        self._openai_key_field: Optional[ft.TextField] = None
        self._anthropic_key_field: Optional[ft.TextField] = None
        self._master_model_dropdown: Optional[ft.Dropdown] = None
        self._crew_model_dropdown: Optional[ft.Dropdown] = None
        self._autogen_model_dropdown: Optional[ft.Dropdown] = None
        self._enable_crew_switch: Optional[ft.Switch] = None
        self._enable_autogen_switch: Optional[ft.Switch] = None
        self._config_path_text: Optional[ft.Text] = None
        self._status_text: Optional[ft.Text] = None

        self._dialog: Optional[ft.AlertDialog] = None

    def _build(self) -> ft.AlertDialog:
        """Build the settings dialog UI."""
        # Load current settings
        self._settings = self.settings_manager.load_settings()

        # ====================================================================
        # API KEYS TAB
        # ====================================================================

        self._openai_key_field = ft.TextField(
            label="OpenAI API Key",
            hint_text="sk-...",
            value=self._settings.get("api_keys", {}).get("openai", ""),
            password=True,
            can_reveal_password=True,
            width=400,
            text_size=Fonts.FONT_SIZE_NORMAL,
            border_color=VSCodeColors.INPUT_BORDER,
            focused_border_color=VSCodeColors.INPUT_ACTIVE_BORDER,
        )

        self._anthropic_key_field = ft.TextField(
            label="Anthropic API Key",
            hint_text="sk-ant-...",
            value=self._settings.get("api_keys", {}).get("anthropic", ""),
            password=True,
            can_reveal_password=True,
            width=400,
            text_size=Fonts.FONT_SIZE_NORMAL,
            border_color=VSCodeColors.INPUT_BORDER,
            focused_border_color=VSCodeColors.INPUT_ACTIVE_BORDER,
        )

        api_keys_content = ft.Column(
            controls=[
                ft.Text(
                    "API Keys are stored securely in your user profile directory.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                    italic=True,
                ),
                ft.Container(height=8),
                self._openai_key_field,
                ft.Container(height=12),
                self._anthropic_key_field,
                ft.Container(height=12),
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.SECURITY,
                            size=16,
                            color=VSCodeColors.INFO_FOREGROUND
                        ),
                        ft.Text(
                            "Keys are never stored in your workspace or committed to git.",
                            size=Fonts.FONT_SIZE_SMALL - 1,
                            color=VSCodeColors.INFO_FOREGROUND,
                        ),
                    ],
                    spacing=6,
                ),
            ],
            spacing=4,
        )

        # ====================================================================
        # MODELS TAB
        # ====================================================================

        models = self._settings.get("models", {})

        self._master_model_dropdown = ft.Dropdown(
            label="Master Agent Model",
            hint_text="Primary LLM for decision making",
            value=models.get("master_agent", "gpt-5-mini"),
            options=[ft.dropdown.Option(m) for m in self.AVAILABLE_MODELS],
            width=300,
            text_size=Fonts.FONT_SIZE_NORMAL,
        )

        self._crew_model_dropdown = ft.Dropdown(
            label="CrewAI Coder Model",
            hint_text="LLM for code generation",
            value=models.get("crew_coder", "gpt-5-nano"),
            options=[ft.dropdown.Option(m) for m in self.AVAILABLE_MODELS],
            width=300,
            text_size=Fonts.FONT_SIZE_NORMAL,
        )

        self._autogen_model_dropdown = ft.Dropdown(
            label="AutoGen Auditor Model",
            hint_text="LLM for project diagnostics (can use cheaper model)",
            value=models.get("autogen_auditor", "gpt-5-nano"),
            options=[ft.dropdown.Option(m) for m in self.AVAILABLE_MODELS],
            width=300,
            text_size=Fonts.FONT_SIZE_NORMAL,
        )

        models_content = ft.Column(
            controls=[
                ft.Text(
                    "Configure which models are used for different agent components.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                    italic=True,
                ),
                ft.Container(height=8),
                self._master_model_dropdown,
                ft.Container(height=12),
                self._crew_model_dropdown,
                ft.Container(height=12),
                self._autogen_model_dropdown,
            ],
            spacing=4,
        )

        # ====================================================================
        # AGENT TOGGLES TAB
        # ====================================================================

        preferences = self._settings.get("preferences", {})

        self._enable_crew_switch = ft.Switch(
            label="Enable CrewAI Builder",
            value=preferences.get("enable_crew", True),
            active_color=VSCodeColors.BUTTON_BACKGROUND,
        )

        self._enable_autogen_switch = ft.Switch(
            label="Enable AutoGen Auditor",
            value=preferences.get("enable_autogen", True),
            active_color=VSCodeColors.BUTTON_BACKGROUND,
        )

        toggles_content = ft.Column(
            controls=[
                ft.Text(
                    "Enable or disable specialized agent subsystems.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                    italic=True,
                ),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._enable_crew_switch,
                            ft.Text(
                                "CrewAI Builder handles complex feature implementations "
                                "using a Planner -> Coder -> Reviewer workflow.",
                                size=Fonts.FONT_SIZE_SMALL - 1,
                                color=VSCodeColors.DESCRIPTION_FOREGROUND,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=12,
                    bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                    border_radius=Spacing.BORDER_RADIUS_SMALL,
                    border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
                ),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._enable_autogen_switch,
                            ft.Text(
                                "AutoGen Auditor provides project health diagnostics "
                                "through multi-agent debate.",
                                size=Fonts.FONT_SIZE_SMALL - 1,
                                color=VSCodeColors.DESCRIPTION_FOREGROUND,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=12,
                    bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                    border_radius=Spacing.BORDER_RADIUS_SMALL,
                    border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
                ),
            ],
            spacing=4,
        )

        # ====================================================================
        # INFO TAB (Config Path)
        # ====================================================================

        config_path = str(self.settings_manager.get_config_file_path())
        self._config_path_text = ft.Text(
            config_path,
            size=Fonts.FONT_SIZE_SMALL,
            color=VSCodeColors.LINK_FOREGROUND,
            selectable=True,
        )

        info_content = ft.Column(
            controls=[
                ft.Text(
                    "Configuration File Location",
                    size=Fonts.FONT_SIZE_NORMAL,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=4),
                ft.Container(
                    content=self._config_path_text,
                    padding=12,
                    bgcolor=VSCodeColors.EDITOR_BACKGROUND,
                    border_radius=Spacing.BORDER_RADIUS_SMALL,
                    border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
                ),
                ft.Container(height=12),
                ft.Text(
                    "Settings are stored in your OS-standard config directory "
                    "(via platformdirs). They persist across workspaces.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=16),
                ft.ElevatedButton(
                    text="Reset to Defaults",
                    icon=ft.Icons.RESTORE,
                    on_click=self._handle_reset,
                    style=ft.ButtonStyle(
                        bgcolor=VSCodeColors.BUTTON_SECONDARY_BACKGROUND,
                        color=VSCodeColors.BUTTON_SECONDARY_FOREGROUND,
                    ),
                ),
            ],
            spacing=4,
        )

        # ====================================================================
        # TABS
        # ====================================================================

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=150,
            tabs=[
                ft.Tab(
                    text="API Keys",
                    icon=ft.Icons.KEY,
                    content=ft.Container(
                        content=api_keys_content,
                        padding=16,
                    ),
                ),
                ft.Tab(
                    text="Models",
                    icon=ft.Icons.PSYCHOLOGY,
                    content=ft.Container(
                        content=models_content,
                        padding=16,
                    ),
                ),
                ft.Tab(
                    text="Toggles",
                    icon=ft.Icons.TUNE,
                    content=ft.Container(
                        content=toggles_content,
                        padding=16,
                    ),
                ),
                ft.Tab(
                    text="Info",
                    icon=ft.Icons.INFO,
                    content=ft.Container(
                        content=info_content,
                        padding=16,
                    ),
                ),
            ],
            expand=True,
        )

        # ====================================================================
        # STATUS BAR
        # ====================================================================

        self._status_text = ft.Text(
            "",
            size=Fonts.FONT_SIZE_SMALL,
            color=VSCodeColors.SUCCESS_FOREGROUND,
            visible=False,
        )

        # ====================================================================
        # DIALOG
        # ====================================================================

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SETTINGS, color=VSCodeColors.ACTIVITY_BAR_ACTIVE_BORDER),
                    ft.Text("Settings", size=18, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        tabs,
                        self._status_text,
                    ],
                    expand=True,
                ),
                width=500,
                height=400,
            ),
            actions=[
                ft.TextButton(
                    "Cancel",
                    on_click=self._handle_cancel,
                ),
                ft.ElevatedButton(
                    "Save",
                    icon=ft.Icons.SAVE,
                    on_click=self._handle_save,
                    style=ft.ButtonStyle(
                        bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                        color=VSCodeColors.BUTTON_FOREGROUND,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        return self._dialog

    def open(self, section: str = "all") -> None:
        """
        Open the settings modal.

        Args:
            section: Which tab to show ("api_keys", "models", "toggles", "all").
        """
        # Build dialog if not already built
        if self._dialog is None:
            self._dialog = self._build()

        # Set initial tab based on section
        tab_index = {
            "api_keys": 0,
            "models": 1,
            "toggles": 2,
            "info": 3,
            "all": 0,
        }.get(section, 0)

        # Find tabs control and set selected index
        if self._dialog.content:
            content_col = self._dialog.content.content
            if content_col and content_col.controls:
                tabs = content_col.controls[0]
                if isinstance(tabs, ft.Tabs):
                    tabs.selected_index = tab_index

        # Show dialog
        self.page.dialog = self._dialog
        self._dialog.open = True
        self.page.update()

    def close(self) -> None:
        """Close the settings modal."""
        if self._dialog:
            self._dialog.open = False
            self.page.update()

    def _handle_save(self, e) -> None:
        """Handle Save button click."""
        try:
            # Collect values from UI
            new_settings = {
                "api_keys": {
                    "openai": self._openai_key_field.value or "",
                    "anthropic": self._anthropic_key_field.value or "",
                },
                "models": {
                    "master_agent": self._master_model_dropdown.value or "gpt-5-mini",
                    "crew_coder": self._crew_model_dropdown.value or "gpt-5-nano",
                    "autogen_auditor": self._autogen_model_dropdown.value or "gpt-5-nano",
                },
                "preferences": {
                    "theme": self._settings.get("preferences", {}).get("theme", "dark"),
                    "enable_crew": self._enable_crew_switch.value,
                    "enable_autogen": self._enable_autogen_switch.value,
                },
            }

            # Save settings
            success = self.settings_manager.save_settings(new_settings)

            if success:
                self._show_status("Settings saved successfully!", "success")
                # Call callback
                if self.on_save:
                    self.on_save()
                # Close dialog after short delay
                import asyncio
                async def close_after_delay():
                    await asyncio.sleep(0.5)
                    self.close()
                self.page.run_task(close_after_delay)
            else:
                self._show_status("Failed to save settings.", "error")

        except Exception as ex:
            self._show_status(f"Error: {str(ex)}", "error")

    def _handle_cancel(self, e) -> None:
        """Handle Cancel button click."""
        self.close()

    def _handle_reset(self, e) -> None:
        """Handle Reset to Defaults button click."""
        try:
            success = self.settings_manager.reset_to_defaults()
            if success:
                # Reload UI with defaults
                self._settings = self.settings_manager.load_settings()
                self._update_ui_from_settings()
                self._show_status("Settings reset to defaults.", "success")
            else:
                self._show_status("Failed to reset settings.", "error")
        except Exception as ex:
            self._show_status(f"Error: {str(ex)}", "error")

    def _update_ui_from_settings(self) -> None:
        """Update UI controls with current settings."""
        api_keys = self._settings.get("api_keys", {})
        models = self._settings.get("models", {})
        preferences = self._settings.get("preferences", {})

        self._openai_key_field.value = api_keys.get("openai", "")
        self._anthropic_key_field.value = api_keys.get("anthropic", "")
        self._master_model_dropdown.value = models.get("master_agent", "gpt-5-mini")
        self._crew_model_dropdown.value = models.get("crew_coder", "gpt-5-nano")
        self._autogen_model_dropdown.value = models.get("autogen_auditor", "gpt-5-nano")
        self._enable_crew_switch.value = preferences.get("enable_crew", True)
        self._enable_autogen_switch.value = preferences.get("enable_autogen", True)

        self.page.update()

    def _show_status(self, message: str, status_type: str = "info") -> None:
        """Show status message."""
        if self._status_text:
            self._status_text.value = message
            self._status_text.visible = True

            if status_type == "success":
                self._status_text.color = VSCodeColors.SUCCESS_FOREGROUND
            elif status_type == "error":
                self._status_text.color = VSCodeColors.ERROR_FOREGROUND
            else:
                self._status_text.color = VSCodeColors.INFO_FOREGROUND

            self.page.update()


def open_settings_modal(page: ft.Page, section: str = "all") -> None:
    """
    Helper function to open settings modal.

    Args:
        page: Flet Page.
        section: Which tab to show.
    """
    modal = SettingsModal(page)
    modal.open(section)


__all__ = [
    "SettingsModal",
    "open_settings_modal",
]
