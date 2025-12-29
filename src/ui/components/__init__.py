"""
Pulse IDE UI Components (Phase 7).

Reusable UI widgets and modals.
"""

from src.ui.components.resizable_splitter import VerticalSplitter, HorizontalSplitter
from src.ui.components.vibe_loader import VibeLoader, VibeStatusBar
from src.ui.components.settings_modal import SettingsModal, open_settings_modal
from src.ui.components.approval import (
    PatchApprovalModal,
    TerminalApprovalModal,
    show_patch_approval,
    show_terminal_approval,
)

__all__ = [
    # Splitters
    "VerticalSplitter",
    "HorizontalSplitter",
    # Vibe loaders
    "VibeLoader",
    "VibeStatusBar",
    # Settings
    "SettingsModal",
    "open_settings_modal",
    # Approval modals
    "PatchApprovalModal",
    "TerminalApprovalModal",
    "show_patch_approval",
    "show_terminal_approval",
]
