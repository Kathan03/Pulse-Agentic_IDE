"""
Cursor-style Settings Page for Pulse IDE

A dedicated settings page that opens as a tab in the editor with:
- Left sidebar with sections: API Keys, Models, Code Intelligence, Theme
- Right content area with settings for each section
- Default welcome/readme page
"""

import flet as ft
from typing import Optional, Callable
from src.ui.theme import VSCodeColors, Fonts, Spacing
from src.core.settings import get_settings_manager


class SettingsPage:
    """
    Cursor-style settings page with sidebar navigation.

    Layout:
    ┌──────────────────────────────────┐
    │ ┌─────────┬──────────────────┐   │
    │ │ Sidebar │   Content Area   │   │
    │ │         │                  │   │
    │ │ API Keys│  Welcome/Readme  │   │
    │ │ Models  │  or              │   │
    │ │ Code AI │  Section Details │   │
    │ │ Theme   │                  │   │
    │ └─────────┴──────────────────┘   │
    └──────────────────────────────────┘
    """

    def __init__(self, on_close: Optional[Callable] = None, on_theme_change: Optional[Callable] = None):
        """
        Initialize SettingsPage.

        Args:
            on_close: Callback when settings page is closed
            on_theme_change: Callback when theme changes for instant UI update
        """
        self.on_close = on_close
        self.on_theme_change = on_theme_change
        self.settings_manager = get_settings_manager()
        self._current_section = "welcome"

        # Content containers for each section
        self._content_area = None
        self._sidebar_buttons = {}

        self.container = self._build()

    def _build(self) -> ft.Container:
        """Build the settings page layout."""
        # Sidebar navigation
        sidebar = self._build_sidebar()

        # Content area (initially shows welcome)
        self._content_area = ft.Container(
            content=self._build_welcome_content(),
            expand=True,
            padding=20,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
        )

        # Main layout: sidebar + content
        main_layout = ft.Row(
            controls=[
                sidebar,
                ft.VerticalDivider(width=1, color=VSCodeColors.PANEL_BORDER),
                self._content_area,
            ],
            spacing=0,
            expand=True,
        )

        return ft.Container(
            content=main_layout,
            expand=True,
            bgcolor=VSCodeColors.EDITOR_BACKGROUND,
        )

    def _build_sidebar(self) -> ft.Container:
        """Build the left sidebar with navigation buttons."""
        # Create navigation buttons
        api_keys_btn = self._create_sidebar_button("API Keys", "api_keys", ft.Icons.KEY)
        models_btn = self._create_sidebar_button("Models", "models", ft.Icons.PSYCHOLOGY)
        code_ai_btn = self._create_sidebar_button("Code Intelligence", "code_intelligence", ft.Icons.LIGHTBULB)
        theme_btn = self._create_sidebar_button("Theme", "theme", ft.Icons.PALETTE)

        # Store references
        self._sidebar_buttons = {
            "api_keys": api_keys_btn,
            "models": models_btn,
            "code_intelligence": code_ai_btn,
            "theme": theme_btn,
        }

        return ft.Container(
            width=200,
            bgcolor=VSCodeColors.SIDEBAR_BACKGROUND,
            padding=10,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Settings",
                        size=Fonts.FONT_SIZE_LARGE,
                        weight=ft.FontWeight.BOLD,
                        color=VSCodeColors.SIDEBAR_FOREGROUND,
                    ),
                    ft.Divider(height=1, color=VSCodeColors.SIDEBAR_BORDER),
                    api_keys_btn,
                    models_btn,
                    code_ai_btn,
                    theme_btn,
                ],
                spacing=4,
            ),
        )

    def _create_sidebar_button(self, label: str, section: str, icon: str) -> ft.Container:
        """Create a sidebar navigation button."""
        button = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=16, color=VSCodeColors.SIDEBAR_FOREGROUND),
                    ft.Text(
                        label,
                        size=Fonts.FONT_SIZE_SMALL,
                        color=VSCodeColors.SIDEBAR_FOREGROUND,
                    ),
                ],
                spacing=8,
            ),
            padding=8,
            border_radius=Spacing.BORDER_RADIUS_SMALL,
            ink=True,
            on_click=lambda e, s=section: self._navigate_to_section(s),
            on_hover=lambda e: self._on_sidebar_hover(e),
            data=section,  # Store section name
        )
        return button

    def _on_sidebar_hover(self, e):
        """Handle sidebar button hover."""
        if e.data == "true":  # Mouse enter
            e.control.bgcolor = VSCodeColors.LIST_HOVER_BACKGROUND
        else:  # Mouse leave
            if e.control.data != self._current_section:
                e.control.bgcolor = None
        e.control.update()

    def _navigate_to_section(self, section: str):
        """Navigate to a specific settings section."""
        self._current_section = section

        # Update sidebar button states
        for sect_name, btn in self._sidebar_buttons.items():
            if sect_name == section:
                btn.bgcolor = VSCodeColors.LIST_ACTIVE_SELECTION_BACKGROUND
            else:
                btn.bgcolor = None
            btn.update()

        # Update content area
        if section == "api_keys":
            self._content_area.content = self._build_api_keys_content()
        elif section == "models":
            self._content_area.content = self._build_models_content()
        elif section == "code_intelligence":
            self._content_area.content = self._build_code_intelligence_content()
        elif section == "theme":
            self._content_area.content = self._build_theme_content()

        self._content_area.update()

    def _build_welcome_content(self) -> ft.Column:
        """Build the welcome/readme content."""
        return ft.Column(
            controls=[
                ft.Text(
                    "⚙️ Pulse Settings",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=20),
                ft.Text(
                    "Configure your Pulse IDE experience",
                    size=Fonts.FONT_SIZE_NORMAL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=30),
                ft.Text(
                    "📌 Quick Links:",
                    size=Fonts.FONT_SIZE_MEDIUM,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=10),
                self._create_quick_link("🔑 API Keys", "Configure OpenAI and Anthropic API keys", "api_keys"),
                self._create_quick_link("🤖 Models", "Select AI models for different agents", "models"),
                self._create_quick_link("💡 Code Intelligence", "Enable/disable agent toggles", "code_intelligence"),
                self._create_quick_link("🎨 Theme", "Choose your IDE theme", "theme"),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=4,
        )

    def _create_quick_link(self, title: str, description: str, section: str) -> ft.Container:
        """Create a clickable quick link card."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=Fonts.FONT_SIZE_NORMAL, weight=ft.FontWeight.W_500, color=VSCodeColors.LINK_FOREGROUND),
                    ft.Text(description, size=Fonts.FONT_SIZE_SMALL, color=VSCodeColors.DESCRIPTION_FOREGROUND),
                ],
                spacing=2,
            ),
            padding=12,
            border_radius=Spacing.BORDER_RADIUS_SMALL,
            border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
            ink=True,
            on_click=lambda e, s=section: self._navigate_to_section(s),
            on_hover=lambda e: self._on_card_hover(e),
        )

    def _on_card_hover(self, e):
        """Handle quick link card hover."""
        if e.data == "true":
            e.control.bgcolor = VSCodeColors.LIST_HOVER_BACKGROUND
        else:
            e.control.bgcolor = None
        e.control.update()

    def _build_api_keys_content(self) -> ft.Column:
        """Build API Keys settings content."""
        settings = self.settings_manager.load_settings()
        api_keys = settings.get("api_keys", {})

        # OpenAI API Key
        openai_field = ft.TextField(
            label="OpenAI API Key",
            hint_text="sk-...",
            value=api_keys.get("openai", ""),
            password=True,
            can_reveal_password=True,
            width=500,
            text_size=Fonts.FONT_SIZE_NORMAL,
            border_color=VSCodeColors.INPUT_BORDER,
            focused_border_color=VSCodeColors.INPUT_ACTIVE_BORDER,
        )

        openai_status = ft.Text("", size=Fonts.FONT_SIZE_SMALL, visible=False)

        def save_openai_key(e):
            settings = self.settings_manager.load_settings()
            settings["api_keys"]["openai"] = openai_field.value
            self.settings_manager.save_settings(settings)
            openai_status.value = "✓ Saved"
            openai_status.color = VSCodeColors.SUCCESS_FOREGROUND
            openai_status.visible = True
            openai_status.update()

        # Anthropic API Key
        anthropic_field = ft.TextField(
            label="Anthropic API Key",
            hint_text="sk-ant-...",
            value=api_keys.get("anthropic", ""),
            password=True,
            can_reveal_password=True,
            width=500,
            text_size=Fonts.FONT_SIZE_NORMAL,
            border_color=VSCodeColors.INPUT_BORDER,
            focused_border_color=VSCodeColors.INPUT_ACTIVE_BORDER,
        )

        anthropic_status = ft.Text("", size=Fonts.FONT_SIZE_SMALL, visible=False)

        def save_anthropic_key(e):
            settings = self.settings_manager.load_settings()
            settings["api_keys"]["anthropic"] = anthropic_field.value
            self.settings_manager.save_settings(settings)
            anthropic_status.value = "✓ Saved"
            anthropic_status.color = VSCodeColors.SUCCESS_FOREGROUND
            anthropic_status.visible = True
            anthropic_status.update()

        return ft.Column(
            controls=[
                ft.Text(
                    "🔑 API Keys",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Configure your API keys for AI providers. Keys are stored securely in your system config.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=20),

                # OpenAI Section
                ft.Text(
                    "OpenAI",
                    size=Fonts.FONT_SIZE_MEDIUM,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                openai_field,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save OpenAI Key",
                            icon=ft.Icons.SAVE,
                            on_click=save_openai_key,
                            style=ft.ButtonStyle(
                                bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                                color=VSCodeColors.BUTTON_FOREGROUND,
                            ),
                        ),
                        openai_status,
                    ],
                    spacing=10,
                ),
                ft.Container(height=30),

                # Anthropic Section
                ft.Text(
                    "Anthropic",
                    size=Fonts.FONT_SIZE_MEDIUM,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                anthropic_field,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save Anthropic Key",
                            icon=ft.Icons.SAVE,
                            on_click=save_anthropic_key,
                            style=ft.ButtonStyle(
                                bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                                color=VSCodeColors.BUTTON_FOREGROUND,
                            ),
                        ),
                        anthropic_status,
                    ],
                    spacing=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )

    def _build_models_content(self) -> ft.Column:
        """Build Models settings content."""
        settings = self.settings_manager.load_settings()
        models = settings.get("models", {})

        # Available models (13 models from CLAUDE.md)
        available_models = [
            "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
            "gpt-5.1-codex", "gpt-5.2-pro",
            "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
            "claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5",
        ]

        # Model dropdowns
        master_dropdown = ft.Dropdown(
            label="Master Agent Model",
            value=models.get("master_agent", "gpt-5-mini"),
            options=[ft.dropdown.Option(m) for m in available_models],
            width=300,
        )

        crew_dropdown = ft.Dropdown(
            label="CrewAI Coder Model",
            value=models.get("crew_coder", "gpt-5-nano"),
            options=[ft.dropdown.Option(m) for m in available_models],
            width=300,
        )

        autogen_dropdown = ft.Dropdown(
            label="AutoGen Auditor Model",
            value=models.get("autogen_auditor", "gpt-5-nano"),
            options=[ft.dropdown.Option(m) for m in available_models],
            width=300,
        )

        status_text = ft.Text("", size=Fonts.FONT_SIZE_SMALL, visible=False)

        def save_models(e):
            settings = self.settings_manager.load_settings()
            settings["models"]["master_agent"] = master_dropdown.value
            settings["models"]["crew_coder"] = crew_dropdown.value
            settings["models"]["autogen_auditor"] = autogen_dropdown.value
            self.settings_manager.save_settings(settings)
            status_text.value = "✓ Models saved"
            status_text.color = VSCodeColors.SUCCESS_FOREGROUND
            status_text.visible = True
            status_text.update()

        return ft.Column(
            controls=[
                ft.Text(
                    "🤖 AI Models",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Select which AI models to use for different agent components.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=20),
                master_dropdown,
                ft.Container(height=12),
                crew_dropdown,
                ft.Container(height=12),
                autogen_dropdown,
                ft.Container(height=20),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save Models",
                            icon=ft.Icons.SAVE,
                            on_click=save_models,
                            style=ft.ButtonStyle(
                                bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                                color=VSCodeColors.BUTTON_FOREGROUND,
                            ),
                        ),
                        status_text,
                    ],
                    spacing=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )

    def _build_code_intelligence_content(self) -> ft.Column:
        """Build Code Intelligence settings content."""
        settings = self.settings_manager.load_settings()
        preferences = settings.get("preferences", {})

        crew_switch = ft.Switch(
            label="Enable CrewAI Builder",
            value=preferences.get("enable_crew", True),
            active_color=VSCodeColors.BUTTON_BACKGROUND,
        )

        autogen_switch = ft.Switch(
            label="Enable AutoGen Auditor",
            value=preferences.get("enable_autogen", True),
            active_color=VSCodeColors.BUTTON_BACKGROUND,
        )

        status_text = ft.Text("", size=Fonts.FONT_SIZE_SMALL, visible=False)

        def save_toggles(e):
            settings = self.settings_manager.load_settings()
            settings["preferences"]["enable_crew"] = crew_switch.value
            settings["preferences"]["enable_autogen"] = autogen_switch.value
            self.settings_manager.save_settings(settings)
            status_text.value = "✓ Settings saved"
            status_text.color = VSCodeColors.SUCCESS_FOREGROUND
            status_text.visible = True
            status_text.update()

        return ft.Column(
            controls=[
                ft.Text(
                    "💡 Code Intelligence",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Enable or disable specialized agent subsystems.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=20),
                crew_switch,
                ft.Text(
                    "CrewAI Builder handles complex feature implementations using Planner → Coder → Reviewer workflow.",
                    size=Fonts.FONT_SIZE_SMALL - 1,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=16),
                autogen_switch,
                ft.Text(
                    "AutoGen Auditor provides project health diagnostics through multi-agent debate.",
                    size=Fonts.FONT_SIZE_SMALL - 1,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=20),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save Settings",
                            icon=ft.Icons.SAVE,
                            on_click=save_toggles,
                            style=ft.ButtonStyle(
                                bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                                color=VSCodeColors.BUTTON_FOREGROUND,
                            ),
                        ),
                        status_text,
                    ],
                    spacing=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )

    def _build_theme_content(self) -> ft.Column:
        """Build Theme settings content."""
        settings = self.settings_manager.load_settings()
        current_theme = settings.get("preferences", {}).get("theme", "dark")

        theme_dropdown = ft.Dropdown(
            label="Select Theme",
            value=current_theme,
            options=[
                ft.dropdown.Option("light", "Light"),
                ft.dropdown.Option("dark", "Dark"),
                ft.dropdown.Option("midnight", "Midnight"),
            ],
            width=300,
        )

        status_text = ft.Text("", size=Fonts.FONT_SIZE_SMALL, visible=False)

        def save_theme(e):
            settings = self.settings_manager.load_settings()
            settings["preferences"]["theme"] = theme_dropdown.value
            self.settings_manager.save_settings(settings)

            # Apply theme immediately
            from src.ui.theme import reload_theme
            success = reload_theme()

            if success:
                # Trigger theme change callback to update UI
                if self.on_theme_change:
                    try:
                        self.on_theme_change(theme_dropdown.value)
                        status_text.value = "✓ Theme applied successfully! Restart for full effect."
                        status_text.color = VSCodeColors.SUCCESS_FOREGROUND
                    except Exception as ex:
                        print(f"[ERROR] Theme callback failed: {ex}")
                        status_text.value = "✓ Theme saved. Restart for full effect."
                        status_text.color = VSCodeColors.WARNING_FOREGROUND
                else:
                    status_text.value = "✓ Theme saved. Restart for full effect."
                    status_text.color = VSCodeColors.WARNING_FOREGROUND
            else:
                status_text.value = "⚠ Theme saved but could not apply. Please restart the application."
                status_text.color = VSCodeColors.WARNING_FOREGROUND

            status_text.visible = True
            status_text.update()

            print(f"[INFO] Theme changed to {theme_dropdown.value}")

        return ft.Column(
            controls=[
                ft.Text(
                    "🎨 Theme",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Choose your IDE color theme.",
                    size=Fonts.FONT_SIZE_SMALL,
                    color=VSCodeColors.DESCRIPTION_FOREGROUND,
                ),
                ft.Container(height=20),
                theme_dropdown,
                ft.Container(height=20),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Apply Theme",
                            icon=ft.Icons.BRUSH,
                            on_click=save_theme,
                            style=ft.ButtonStyle(
                                bgcolor=VSCodeColors.BUTTON_BACKGROUND,
                                color=VSCodeColors.BUTTON_FOREGROUND,
                            ),
                        ),
                        status_text,
                    ],
                    spacing=10,
                ),
                ft.Container(height=20),
                ft.Text(
                    "Available Themes:",
                    size=Fonts.FONT_SIZE_MEDIUM,
                    weight=ft.FontWeight.BOLD,
                    color=VSCodeColors.EDITOR_FOREGROUND,
                ),
                ft.Container(height=10),
                self._create_theme_preview("Light", "Clean and bright interface"),
                self._create_theme_preview("Dark", "VS Code Dark Modern theme"),
                self._create_theme_preview("Midnight", "Deep blue interface"),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )

    def _create_theme_preview(self, name: str, description: str) -> ft.Container:
        """Create a theme preview card."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(name, size=Fonts.FONT_SIZE_NORMAL, weight=ft.FontWeight.W_500, color=VSCodeColors.EDITOR_FOREGROUND),
                    ft.Text(description, size=Fonts.FONT_SIZE_SMALL, color=VSCodeColors.DESCRIPTION_FOREGROUND),
                ],
                spacing=2,
            ),
            padding=10,
            border_radius=Spacing.BORDER_RADIUS_SMALL,
            border=ft.border.all(1, VSCodeColors.PANEL_BORDER),
        )

    def get_control(self) -> ft.Container:
        """Get the settings page control."""
        return self.container


__all__ = ["SettingsPage"]
