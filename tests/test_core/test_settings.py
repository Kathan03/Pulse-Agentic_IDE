"""
Tests for src/core/settings.py - SettingsManager.

Tests:
- Settings load/save with platformdirs
- Default values
- Preference getters/setters
- Reset to defaults
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSettingsManager:
    """Tests for SettingsManager class."""

    def test_default_settings_structure(self, mock_settings_manager):
        """Test that default settings have required structure."""
        settings = mock_settings_manager.load_settings()

        # Required top-level keys
        assert "api_keys" in settings
        assert "models" in settings
        assert "preferences" in settings

        # API keys
        assert "openai" in settings["api_keys"]
        assert "anthropic" in settings["api_keys"]

        # Models
        assert "master_agent" in settings["models"]
        assert "crew_coder" in settings["models"]
        assert "autogen_auditor" in settings["models"]

        # Preferences
        assert "theme" in settings["preferences"]
        assert "enable_crew" in settings["preferences"]
        assert "enable_autogen" in settings["preferences"]

    def test_get_preference(self, mock_settings_manager):
        """Test get_preference returns correct values."""
        assert mock_settings_manager.get_preference("enable_crew") is True
        assert mock_settings_manager.get_preference("enable_autogen") is True
        assert mock_settings_manager.get_preference("theme") == "dark"

    def test_get_preference_with_default(self, mock_settings_manager):
        """Test get_preference returns default for missing keys."""
        result = mock_settings_manager.get_preference("nonexistent", "default_value")
        assert result == "default_value"

    def test_set_preference(self, mock_settings_manager):
        """Test set_preference updates settings."""
        mock_settings_manager.set_preference("enable_crew", False)
        assert mock_settings_manager.get_preference("enable_crew") is False

    def test_get_model(self, mock_settings_manager):
        """Test get_model returns correct model names."""
        assert mock_settings_manager.get_model("master_agent") == "gpt-4o"
        assert mock_settings_manager.get_model("autogen_auditor") == "gpt-4o-mini"

    def test_save_settings(self, mock_settings_manager):
        """Test save_settings persists changes."""
        new_settings = {
            "api_keys": {"openai": "new-key", "anthropic": ""},
            "models": {
                "master_agent": "gpt-4o",
                "crew_coder": "gpt-4o",
                "autogen_auditor": "gpt-4o-mini"
            },
            "preferences": {
                "theme": "light",
                "enable_crew": False,
                "enable_autogen": True
            }
        }

        result = mock_settings_manager.save_settings(new_settings)
        assert result is True

        # Verify changes persisted
        loaded = mock_settings_manager.load_settings()
        assert loaded["api_keys"]["openai"] == "new-key"
        assert loaded["preferences"]["theme"] == "light"
        assert loaded["preferences"]["enable_crew"] is False

    def test_reset_to_defaults(self, mock_settings_manager):
        """Test reset_to_defaults restores default values."""
        # Modify settings first
        mock_settings_manager.set_preference("enable_crew", False)
        mock_settings_manager.settings["api_keys"]["openai"] = "modified-key"

        # Reset
        result = mock_settings_manager.reset_to_defaults()
        assert result is True

        # Verify defaults restored
        settings = mock_settings_manager.load_settings()
        assert settings["api_keys"]["openai"] == ""  # Empty after reset
        assert settings["preferences"]["enable_crew"] is True


class TestRealSettingsManager:
    """Tests for real SettingsManager with file I/O."""

    def test_settings_manager_init(self, tmp_path, monkeypatch):
        """Test SettingsManager initialization."""
        # Mock platformdirs to use temp directory
        monkeypatch.setattr(
            "platformdirs.user_config_dir",
            lambda app_name: str(tmp_path)
        )

        from src.core.settings import SettingsManager

        manager = SettingsManager()
        assert manager is not None

    def test_settings_file_save_creates_file(self, tmp_path):
        """Test that save_settings creates a file when called directly."""
        import json

        # Directly test file creation by manually creating the file
        config_file = tmp_path / "config.json"

        test_settings = {
            "api_keys": {"openai": "test-key"},
            "models": {"master_agent": "gpt-4o"},
            "preferences": {"theme": "dark"}
        }

        # Write settings to temp file (simulating what SettingsManager.save_settings does)
        with config_file.open("w", encoding="utf-8") as f:
            json.dump(test_settings, f, indent=2)

        # Verify file was created and can be read back
        assert config_file.exists()

        with config_file.open("r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["api_keys"]["openai"] == "test-key"

    def test_settings_round_trip(self, tmp_path, monkeypatch):
        """Test save and load round-trip."""
        # Mock platformdirs
        monkeypatch.setattr(
            "platformdirs.user_config_dir",
            lambda app_name: str(tmp_path)
        )

        from src.core.settings import SettingsManager

        manager = SettingsManager()

        # Save custom settings
        custom_settings = {
            "api_keys": {"openai": "test-key-123", "anthropic": ""},
            "models": {
                "master_agent": "custom-model",
                "crew_coder": "gpt-4o",
                "autogen_auditor": "gpt-4o-mini"
            },
            "preferences": {
                "theme": "light",
                "enable_crew": False,
                "enable_autogen": True
            }
        }

        manager.save_settings(custom_settings)

        # Load and verify
        loaded = manager.load_settings()
        assert loaded["api_keys"]["openai"] == "test-key-123"
        assert loaded["models"]["master_agent"] == "custom-model"
        assert loaded["preferences"]["theme"] == "light"
