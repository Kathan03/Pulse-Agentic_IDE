"""
Session Manager for Pulse IDE Server.

Manages WebSocket sessions and their mapping to LangGraph threads.
Provides thread-safe session tracking for concurrent connections.

Key responsibilities:
- Track active WebSocket connections
- Map connection_id to LangGraph thread_id for conversation continuity
- Track run state (current_run_id, pending_approval)
- Support session resumption on reconnect
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


# ============================================================================
# SESSION DATA CLASS
# ============================================================================

@dataclass
class Session:
    """
    Represents an active WebSocket session.

    Tracks connection state, LangGraph thread association,
    and current run state.

    Attributes:
        connection_id: Unique identifier for this connection.
        websocket: The FastAPI WebSocket connection object.
        thread_id: LangGraph thread_id for conversation continuity.
        conversation_id: Current conversation ID.
        project_root: Workspace root path for this session.
        created_at: Session creation timestamp.
        last_activity: Last activity timestamp (for timeout tracking).
        current_run_id: ID of the currently active run (if any).
        pending_approval: Data for pending approval request (if any).
        is_running: Whether a run is currently active.
    """

    connection_id: str
    websocket: WebSocket
    thread_id: Optional[str] = None
    conversation_id: Optional[str] = None
    project_root: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    current_run_id: Optional[str] = None
    pending_approval: Optional[Dict[str, Any]] = None
    is_running: bool = False

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def start_run(self, run_id: str, thread_id: str) -> None:
        """Mark a run as started."""
        self.current_run_id = run_id
        self.thread_id = thread_id
        self.is_running = True
        self.update_activity()

    def end_run(self) -> None:
        """Mark the current run as ended."""
        self.current_run_id = None
        self.pending_approval = None
        self.is_running = False
        self.update_activity()

    def set_pending_approval(self, approval_data: Dict[str, Any]) -> None:
        """Set pending approval data."""
        self.pending_approval = approval_data
        self.update_activity()

    def clear_pending_approval(self) -> None:
        """Clear pending approval data."""
        self.pending_approval = None
        self.update_activity()


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """
    Manages WebSocket sessions and their mapping to LangGraph threads.

    Thread-safe via asyncio.Lock for concurrent access.
    Provides methods for session lifecycle and run tracking.

    Usage:
        manager = get_session_manager()

        # Create session on connect
        session = await manager.create_session(connection_id, websocket)

        # Associate run with session
        await manager.associate_run(connection_id, run_id, thread_id)

        # Get session by run ID (for routing approval responses)
        session = await manager.get_session_by_run(run_id)

        # Remove session on disconnect
        await manager.remove_session(connection_id)
    """

    def __init__(self):
        """Initialize SessionManager."""
        self._sessions: Dict[str, Session] = {}
        self._run_to_session: Dict[str, str] = {}  # run_id -> connection_id
        self._lock = asyncio.Lock()

        logger.debug("SessionManager initialized")

    async def create_session(
        self,
        connection_id: str,
        websocket: WebSocket
    ) -> Session:
        """
        Create a new session for a WebSocket connection.

        Args:
            connection_id: Unique connection identifier.
            websocket: The FastAPI WebSocket connection.

        Returns:
            The created Session object.
        """
        async with self._lock:
            session = Session(connection_id=connection_id, websocket=websocket)
            self._sessions[connection_id] = session
            logger.info(f"Session created: {connection_id}")
            return session

    async def get_session(self, connection_id: str) -> Optional[Session]:
        """
        Get session by connection ID.

        Args:
            connection_id: The connection ID to look up.

        Returns:
            Session if found, None otherwise.
        """
        return self._sessions.get(connection_id)

    async def get_session_by_run(self, run_id: str) -> Optional[Session]:
        """
        Get session by run ID.

        Useful for routing approval responses to the correct session.

        Args:
            run_id: The run ID to look up.

        Returns:
            Session if found, None otherwise.
        """
        connection_id = self._run_to_session.get(run_id)
        if connection_id:
            return self._sessions.get(connection_id)
        return None

    async def associate_run(
        self,
        connection_id: str,
        run_id: str,
        thread_id: str
    ) -> None:
        """
        Associate a run with a session.

        Updates session state and creates run_id -> connection_id mapping.

        Args:
            connection_id: The connection ID.
            run_id: The run ID to associate.
            thread_id: The LangGraph thread ID.
        """
        async with self._lock:
            session = self._sessions.get(connection_id)
            if session:
                session.start_run(run_id, thread_id)
                self._run_to_session[run_id] = connection_id
                logger.info(
                    f"Run {run_id} associated with session {connection_id}"
                )

    async def clear_run(self, run_id: str) -> None:
        """
        Clear run association when run completes.

        Args:
            run_id: The run ID to clear.
        """
        async with self._lock:
            connection_id = self._run_to_session.pop(run_id, None)
            if connection_id and connection_id in self._sessions:
                session = self._sessions[connection_id]
                session.end_run()
                logger.info(f"Run {run_id} cleared from session {connection_id}")

    async def set_pending_approval(
        self,
        run_id: str,
        approval_data: Dict[str, Any]
    ) -> None:
        """
        Set pending approval for a session.

        Args:
            run_id: The run ID that requires approval.
            approval_data: The approval request data.
        """
        session = await self.get_session_by_run(run_id)
        if session:
            session.set_pending_approval(approval_data)
            logger.debug(f"Pending approval set for run {run_id}")

    async def clear_pending_approval(self, run_id: str) -> None:
        """
        Clear pending approval for a session.

        Args:
            run_id: The run ID to clear approval for.
        """
        session = await self.get_session_by_run(run_id)
        if session:
            session.clear_pending_approval()
            logger.debug(f"Pending approval cleared for run {run_id}")

    async def remove_session(self, connection_id: str) -> None:
        """
        Remove a session (on disconnect).

        Cleans up session and any associated run mappings.

        Args:
            connection_id: The connection ID to remove.
        """
        async with self._lock:
            session = self._sessions.pop(connection_id, None)
            if session:
                # Clean up run mapping if run was active
                if session.current_run_id:
                    self._run_to_session.pop(session.current_run_id, None)
                logger.info(f"Session removed: {connection_id}")

    async def get_all_sessions(self) -> Dict[str, Session]:
        """
        Get all active sessions.

        Returns:
            Dict mapping connection_id to Session.
        """
        return dict(self._sessions)

    async def get_active_run_count(self) -> int:
        """
        Get count of currently active runs.

        Returns:
            Number of active runs.
        """
        return len(self._run_to_session)

    async def get_session_count(self) -> int:
        """
        Get count of active sessions.

        Returns:
            Number of active sessions.
        """
        return len(self._sessions)


# ============================================================================
# GLOBAL SINGLETON
# ============================================================================

_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get global SessionManager instance (singleton).

    Returns:
        Global SessionManager instance.
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager() -> None:
    """
    Reset global SessionManager instance.

    WARNING: Only use in tests.
    """
    global _session_manager
    _session_manager = None


__all__ = [
    "Session",
    "SessionManager",
    "get_session_manager",
    "reset_session_manager",
]
