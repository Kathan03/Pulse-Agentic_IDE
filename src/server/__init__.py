"""
Pulse IDE WebSocket Server Package.

Provides a FastAPI + WebSocket server layer for the Pulse IDE agent backend.
This enables remote clients (Electron frontend) to interact with the agent
while maintaining compatibility with the existing Flet UI.

Usage:
    # Start server
    python -m src.server.main

    # Or programmatically
    from src.server.main import run_server
    run_server(host="127.0.0.1", port=8765)
"""

from src.server.models import (
    MessageType,
    WSMessage,
    AgentRequestPayload,
    ApprovalResponsePayload,
    CancelRequestPayload,
    EventPayload,
    ApprovalRequiredPayload,
    RunResultPayload,
    ErrorPayload,
)
from src.server.session import (
    Session,
    SessionManager,
    get_session_manager,
)
from src.server.networked_bridge import NetworkedBridge
from src.server.serializers import serialize_event_data

__all__ = [
    # Models
    "MessageType",
    "WSMessage",
    "AgentRequestPayload",
    "ApprovalResponsePayload",
    "CancelRequestPayload",
    "EventPayload",
    "ApprovalRequiredPayload",
    "RunResultPayload",
    "ErrorPayload",
    # Session
    "Session",
    "SessionManager",
    "get_session_manager",
    # Bridge
    "NetworkedBridge",
    # Serializers
    "serialize_event_data",
]
