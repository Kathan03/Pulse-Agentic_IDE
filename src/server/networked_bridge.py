"""
Networked Bridge for Pulse IDE Server.

Bridges the EventBus to WebSocket transport, replacing UIBridge
for remote client communication. Subscribes to EventBus events
and forwards them to WebSocket clients as JSON messages.

Key responsibilities:
1. Subscribe to global EventBus
2. Forward events to WebSocket client as JSON
3. Handle APPROVAL_REQUESTED events (send APPROVAL_REQUIRED message)
4. Provide wait_for_approval() / submit_approval() for graph integration
5. Mirror UIBridge interface for compatibility
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from src.core.events import (
    EventBus,
    Event,
    EventType,
    get_event_bus,
    iter_queue,
)
from src.server.models import (
    WSMessage,
    MessageType,
    create_event_message,
    create_approval_required_message,
)
from src.server.session import Session, get_session_manager
from src.server.serializers import serialize_event_data, serialize_approval_data

logger = logging.getLogger(__name__)


class NetworkedBridge:
    """
    Bridge between EventBus and WebSocket transport.

    Similar interface to UIBridge but sends events over WebSocket
    instead of invoking local callbacks. Each NetworkedBridge instance
    is associated with a specific WebSocket session.

    Usage:
        # Create bridge for a session
        bridge = NetworkedBridge(session)

        # Connect to EventBus and start forwarding
        await bridge.connect()

        # Wait for approval (called by graph during interrupt)
        decision = await bridge.wait_for_approval()

        # Submit approval (called when client sends APPROVAL_RESPONSE)
        bridge.submit_approval(approved=True, feedback="")

        # Disconnect on session end
        await bridge.disconnect()
    """

    def __init__(self, session: Session):
        """
        Initialize NetworkedBridge for a specific WebSocket session.

        Args:
            session: The Session object for this connection.
        """
        self.session = session
        self._event_bus: Optional[EventBus] = None
        self._subscription_queue: Optional[asyncio.Queue] = None
        self._shutdown = False
        self._consumer_task: Optional[asyncio.Task] = None

        # Approval response handling (mirrors UIBridge pattern)
        self._approval_future: Optional[asyncio.Future] = None

        logger.info(f"NetworkedBridge created for session {session.connection_id}")

    # ========================================================================
    # CONNECTION LIFECYCLE
    # ========================================================================

    async def connect(self) -> None:
        """
        Connect to EventBus and start forwarding events.

        Subscribes to the global EventBus and starts a background
        task to consume and forward events to the WebSocket client.
        """
        self._event_bus = get_event_bus()
        self._subscription_queue = self._event_bus.subscribe()
        self._shutdown = False

        # Start consumer in background
        self._consumer_task = asyncio.create_task(self._consume_events())
        logger.info(f"NetworkedBridge connected for session {self.session.connection_id}")

    async def disconnect(self) -> None:
        """
        Disconnect from EventBus and cleanup resources.

        Stops the event consumer, unsubscribes from EventBus,
        and cancels any pending approval futures.
        """
        self._shutdown = True

        # Unsubscribe from EventBus
        if self._event_bus and self._subscription_queue:
            self._event_bus.unsubscribe(self._subscription_queue)
            self._subscription_queue = None

        # Cancel consumer task
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None

        # Cancel any pending approval
        if self._approval_future and not self._approval_future.done():
            self._approval_future.cancel()
            self._approval_future = None

        logger.info(f"NetworkedBridge disconnected for session {self.session.connection_id}")

    # ========================================================================
    # EVENT CONSUMPTION
    # ========================================================================

    async def _consume_events(self) -> None:
        """
        Consume events from EventBus and forward to WebSocket.

        Runs as a background task, continuously polling for events
        and forwarding them to the WebSocket client.
        """
        try:
            async for event in iter_queue(self._subscription_queue):
                if self._shutdown:
                    break

                # Only forward events for this session's run
                # (In single-run mode, all events go to the active session)
                await self._process_event(event)

        except asyncio.CancelledError:
            logger.debug(f"Event consumer cancelled for session {self.session.connection_id}")
        except Exception as e:
            logger.error(f"Event consumer error: {e}", exc_info=True)

    async def _process_event(self, event: Event) -> None:
        """
        Process and forward an event to the WebSocket client.

        Special handling for APPROVAL_REQUESTED events, which
        are converted to APPROVAL_REQUIRED messages.

        Args:
            event: The Event to process and forward.
        """
        try:
            event_type = event.type

            # Special handling for approval requests
            if event_type == EventType.APPROVAL_REQUESTED:
                await self._handle_approval_requested(event)
                return

            # Forward other events as generic EVENT messages
            serialized_data = serialize_event_data(event.data)

            ws_message = create_event_message(
                event_type=event_type.value,
                data=serialized_data
            )

            await self._send_message(ws_message)

        except Exception as e:
            logger.error(f"Error processing event {event.type}: {e}", exc_info=True)

    async def _handle_approval_requested(self, event: Event) -> None:
        """
        Handle APPROVAL_REQUESTED event.

        Sends APPROVAL_REQUIRED message to client and updates
        session state with pending approval data.

        Args:
            event: The APPROVAL_REQUESTED event.
        """
        approval_type = event.data.get("type", "unknown")
        raw_data = event.data.get("data", {})

        # Serialize the approval data
        serialized_data = serialize_approval_data(approval_type, raw_data)

        # Generate human-readable description
        description = self._generate_approval_description(approval_type, serialized_data)

        # Update session state
        self.session.set_pending_approval({
            "type": approval_type,
            "data": serialized_data
        })

        # Store in session manager for routing
        session_manager = get_session_manager()
        if self.session.current_run_id:
            await session_manager.set_pending_approval(
                self.session.current_run_id,
                self.session.pending_approval
            )

        # Send APPROVAL_REQUIRED message
        ws_message = create_approval_required_message(
            run_id=self.session.current_run_id or "",
            approval_type=approval_type,
            data=serialized_data,
            description=description
        )

        await self._send_message(ws_message)
        logger.info(f"Sent approval request to client: {approval_type}")

    def _generate_approval_description(
        self,
        approval_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable description for approval request.

        Args:
            approval_type: Type of approval ("patch" or "terminal").
            data: Serialized approval data.

        Returns:
            Human-readable description string.
        """
        if approval_type == "patch":
            file_path = data.get("file_path", "unknown file")
            summary = data.get("patch_summary", "modify file")
            return f"Apply patch to {file_path}: {summary}"
        elif approval_type == "terminal":
            command = data.get("command", "unknown command")
            risk = data.get("risk_level", "medium")
            return f"Run command ({risk} risk): {command}"
        else:
            return f"Approval required for {approval_type}"

    # ========================================================================
    # APPROVAL HANDLING
    # ========================================================================

    async def wait_for_approval(self) -> Dict[str, Any]:
        """
        Wait for user approval decision over WebSocket.

        Called when the graph needs to wait for user approval.
        Blocks until the client sends an APPROVAL_RESPONSE.

        Returns:
            Dict with {"approved": bool, "feedback": str}.
        """
        loop = asyncio.get_event_loop()
        self._approval_future = loop.create_future()
        try:
            result = await self._approval_future
            return result
        finally:
            self._approval_future = None

    def submit_approval(self, approved: bool, feedback: str = "") -> None:
        """
        Submit user's approval decision.

        Called when the client sends an APPROVAL_RESPONSE message.
        Resolves the approval future to unblock the waiting code.

        Args:
            approved: Whether user approved the action.
            feedback: Optional feedback text.
        """
        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result({
                "approved": approved,
                "feedback": feedback
            })

        # Clear pending approval state
        self.session.clear_pending_approval()
        logger.info(f"Approval submitted: approved={approved}")

    def has_pending_approval(self) -> bool:
        """Check if there's a pending approval waiting."""
        return self._approval_future is not None and not self._approval_future.done()

    # ========================================================================
    # MESSAGE SENDING
    # ========================================================================

    async def _send_message(self, message: WSMessage) -> None:
        """
        Send a message over WebSocket.

        Args:
            message: The WSMessage to send.

        Raises:
            Exception: If sending fails.
        """
        try:
            # Check if WebSocket is still connected
            if self.session.websocket.client_state != WebSocketState.CONNECTED:
                logger.warning(f"WebSocket not connected, dropping message: {message.type}")
                return

            await self.session.websocket.send_json(message.model_dump())
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise

    async def send_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Send a custom event to the WebSocket client.

        Args:
            event_type: Event type string.
            data: Event data dict.
        """
        ws_message = create_event_message(event_type=event_type, data=data)
        await self._send_message(ws_message)

    # ========================================================================
    # UIBridge-COMPATIBLE INTERFACE
    # ========================================================================

    @property
    def is_running(self) -> bool:
        """Check if a run is active (UIBridge compatibility)."""
        return self.session.is_running

    @property
    def pending_approval(self) -> Optional[Dict[str, Any]]:
        """Get pending approval data (UIBridge compatibility)."""
        return self.session.pending_approval

    @property
    def current_vibe(self) -> str:
        """Get current vibe status (UIBridge compatibility)."""
        # We don't track vibe locally; it's forwarded to client
        return ""


__all__ = ["NetworkedBridge"]
