"""
Settings API Routes for Pulse IDE Server.

Provides REST endpoints for reading and updating user settings,
including API keys, model preferences, and other configurations.

Settings are stored securely using platformdirs in the OS-standard
config location (%APPDATA%/Pulse/config.json on Windows).
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from src.core.settings import get_settings_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class APIKeyUpdate(BaseModel):
    """Request model for updating an API key."""
    provider: str = Field(..., description="Provider name: 'openai' or 'anthropic'")
    api_key: str = Field(..., description="The API key value")


class ModelUpdate(BaseModel):
    """Request model for updating model selection."""
    component: str = Field(..., description="Component: 'master_agent', 'crew_coder', or 'autogen_auditor'")
    model_name: str = Field(..., description="Model identifier (e.g., 'gpt-4o')")


class PreferenceUpdate(BaseModel):
    """Request model for updating a preference."""
    key: str = Field(..., description="Preference key")
    value: Any = Field(..., description="Preference value")


class SettingsResponse(BaseModel):
    """Response model for full settings."""
    api_keys: Dict[str, str]
    models: Dict[str, str]
    preferences: Dict[str, Any]


class APIKeyStatusResponse(BaseModel):
    """Response model for API key status (without revealing the key)."""
    openai_configured: bool
    anthropic_configured: bool


# ============================================================================
# Routes
# ============================================================================

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """
    Get all user settings.

    Note: API keys are masked for security.
    """
    try:
        manager = get_settings_manager()
        settings = manager.load_settings()

        # Mask API keys for security
        masked_settings = settings.copy()
        api_keys = masked_settings.get("api_keys", {})
        masked_settings["api_keys"] = {
            "openai": _mask_key(api_keys.get("openai", "")),
            "anthropic": _mask_key(api_keys.get("anthropic", "")),
        }

        return masked_settings
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/api-keys/status", response_model=APIKeyStatusResponse)
async def get_api_key_status():
    """
    Check if API keys are configured (without revealing them).
    """
    try:
        manager = get_settings_manager()
        openai_key = manager.get_api_key("openai")
        anthropic_key = manager.get_api_key("anthropic")

        return APIKeyStatusResponse(
            openai_configured=bool(openai_key),
            anthropic_configured=bool(anthropic_key),
        )
    except Exception as e:
        logger.error(f"Failed to get API key status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/api-keys")
async def update_api_key(update: APIKeyUpdate):
    """
    Update an API key.
    """
    if update.provider not in ["openai", "anthropic"]:
        raise HTTPException(status_code=400, detail="Invalid provider. Must be 'openai' or 'anthropic'")

    try:
        manager = get_settings_manager()
        success = manager.set_api_key(update.provider, update.api_key)

        if success:
            logger.info(f"API key updated for provider: {update.provider}")
            return {"success": True, "message": f"{update.provider} API key updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save API key")
    except Exception as e:
        logger.error(f"Failed to update API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/models")
async def update_model(update: ModelUpdate):
    """
    Update model selection for a component.
    """
    valid_components = ["master_agent", "crew_coder", "autogen_auditor"]
    if update.component not in valid_components:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid component. Must be one of: {valid_components}"
        )

    try:
        manager = get_settings_manager()
        success = manager.set_model(update.component, update.model_name)

        if success:
            logger.info(f"Model updated for {update.component}: {update.model_name}")
            return {"success": True, "message": f"Model updated for {update.component}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save model selection")
    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/preferences")
async def update_preference(update: PreferenceUpdate):
    """
    Update a user preference.
    """
    try:
        manager = get_settings_manager()
        success = manager.set_preference(update.key, update.value)

        if success:
            logger.info(f"Preference updated: {update.key} = {update.value}")
            return {"success": True, "message": f"Preference '{update.key}' updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save preference")
    except Exception as e:
        logger.error(f"Failed to update preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/config-path")
async def get_config_path():
    """
    Get the path to the config file (for debugging).
    """
    try:
        manager = get_settings_manager()
        path = manager.get_config_file_path()
        return {"config_path": str(path)}
    except Exception as e:
        logger.error(f"Failed to get config path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/reset")
async def reset_settings():
    """
    Reset all settings to defaults.
    """
    try:
        manager = get_settings_manager()
        success = manager.reset_to_defaults()

        if success:
            logger.warning("Settings reset to defaults")
            return {"success": True, "message": "Settings reset to defaults"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset settings")
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helpers
# ============================================================================

def _mask_key(key: str) -> str:
    """Mask an API key for display, showing only first and last 4 characters."""
    if not key or len(key) < 12:
        return "••••••••" if key else ""
    return f"{key[:4]}••••••••{key[-4:]}"
