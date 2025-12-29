r"""
Global Settings Management for Pulse IDE v2.6.

Uses platformdirs to store user settings in OS-standard locations.
Manages API keys, model preferences, and agent toggles.

Storage Locations (via platformdirs):
- Windows: %APPDATA%\Pulse\config.json
- Linux: ~/.config/pulse/config.json
- macOS: ~/Library/Application Support/Pulse/config.json
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from platformdirs import user_config_dir

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages global user settings in OS-standard config directory.

    Settings are stored as JSON and include:
    - API keys (OpenAI, Anthropic)
    - Model selections (master_agent, crew_coder, autogen_auditor)
    - Preferences (theme, enable_autogen, enable_crew)
    """

    APP_NAME = "Pulse"
    APP_AUTHOR = "PulseIDE"
    CONFIG_FILE_NAME = "config.json"

    # Default settings structure
    DEFAULT_SETTINGS = {
        "api_keys": {
            "openai": "",
            "anthropic": ""
        },
        "models": {
            "master_agent": "gpt-5-mini",
            "crew_coder": "gpt-5-nano",
            "autogen_auditor": "gpt-5-nano"
        },
        "preferences": {
            "theme": "dark",
            "enable_autogen": True,
            "enable_crew": True
        }
    }

    def __init__(self):
        """
        Initialize SettingsManager with platformdirs config directory.

        Creates config directory if not exists.
        """
        # Get OS-standard config directory
        self.config_dir = Path(user_config_dir(self.APP_NAME, self.APP_AUTHOR))
        self.config_file = self.config_dir / self.CONFIG_FILE_NAME

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Settings config directory: {self.config_dir}")

    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from config file.

        Returns:
            Dict with settings (uses defaults if file doesn't exist).
        """
        if not self.config_file.exists():
            logger.info("Config file not found, using defaults")
            return self.DEFAULT_SETTINGS.copy()

        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                settings = json.load(f)

            # Merge with defaults to handle missing keys
            merged_settings = self._merge_with_defaults(settings)

            logger.info("Settings loaded successfully")
            return merged_settings

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config file: {e}")
            logger.warning("Using default settings")
            return self.DEFAULT_SETTINGS.copy()

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to config file.

        Args:
            settings: Settings dict to save.

        Returns:
            True if save succeeded, False otherwise.
        """
        try:
            # Validate structure before saving
            validated_settings = self._merge_with_defaults(settings)

            # Write to temp file first (atomic write)
            temp_file = self.config_file.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(validated_settings, f, indent=2)

            # Atomic rename
            temp_file.replace(self.config_file)

            logger.info("Settings saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.

        Args:
            provider: Provider name ("openai" or "anthropic").

        Returns:
            API key string or None if not configured.
        """
        settings = self.load_settings()
        api_key = settings.get("api_keys", {}).get(provider, "")
        return api_key if api_key else None

    def set_api_key(self, provider: str, api_key: str) -> bool:
        """
        Set API key for a specific provider.

        Args:
            provider: Provider name ("openai" or "anthropic").
            api_key: API key string.

        Returns:
            True if save succeeded.
        """
        settings = self.load_settings()
        if "api_keys" not in settings:
            settings["api_keys"] = {}

        settings["api_keys"][provider] = api_key
        return self.save_settings(settings)

    def get_model(self, component: str) -> str:
        """
        Get configured model for a specific component.

        Args:
            component: Component name ("master_agent", "crew_coder", "autogen_auditor").

        Returns:
            Model name (defaults from DEFAULT_SETTINGS if not configured).
        """
        settings = self.load_settings()
        return settings.get("models", {}).get(
            component,
            self.DEFAULT_SETTINGS["models"][component]
        )

    def set_model(self, component: str, model_name: str) -> bool:
        """
        Set model for a specific component.

        Args:
            component: Component name ("master_agent", "crew_coder", "autogen_auditor").
            model_name: Model identifier (e.g., "gpt-4o", "gpt-4o-mini").

        Returns:
            True if save succeeded.
        """
        settings = self.load_settings()
        if "models" not in settings:
            settings["models"] = {}

        settings["models"][component] = model_name
        return self.save_settings(settings)

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get user preference value.

        Args:
            key: Preference key (e.g., "theme", "enable_autogen").
            default: Default value if key not found.

        Returns:
            Preference value or default.
        """
        settings = self.load_settings()
        return settings.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any) -> bool:
        """
        Set user preference value.

        Args:
            key: Preference key.
            value: Preference value.

        Returns:
            True if save succeeded.
        """
        settings = self.load_settings()
        if "preferences" not in settings:
            settings["preferences"] = {}

        settings["preferences"][key] = value
        return self.save_settings(settings)

    def _merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user settings with defaults to handle missing keys.

        Args:
            settings: User settings dict (potentially incomplete).

        Returns:
            Complete settings dict with defaults filled in.
        """
        merged = self.DEFAULT_SETTINGS.copy()

        for section in ["api_keys", "models", "preferences"]:
            if section in settings:
                merged[section].update(settings[section])

        return merged

    def reset_to_defaults(self) -> bool:
        """
        Reset all settings to defaults.

        Returns:
            True if reset succeeded.
        """
        logger.warning("Resetting settings to defaults")
        return self.save_settings(self.DEFAULT_SETTINGS.copy())

    def get_config_file_path(self) -> Path:
        """
        Get absolute path to config file for debugging.

        Returns:
            Path to config.json file.
        """
        return self.config_file


# Singleton instance for global access
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """
    Get singleton SettingsManager instance.

    Returns:
        Global SettingsManager instance.
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


__all__ = ["SettingsManager", "get_settings_manager"]
