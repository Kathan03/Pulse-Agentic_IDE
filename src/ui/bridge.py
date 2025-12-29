"""
UI Bridge for Pulse IDE v2.6 (Phase 7).

Connects backend events to UI updates without blocking.
Provides async-friendly event transport + buffering for:
- Vibe status updates
- Lifecycle events (node entered/exited, tool requested/executed)
- Approval requests (patch/terminal)
- Final response delivery
- Cancellation/stop events

Thread-safe: Uses asyncio.Queue for communication between
backend threads and Flet's UI thread.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from src.core.events import (
    EventBus,
    Event,
    EventType,
    get_event_bus,
    iter_queue,
)

logger = logging.getLogger(__name__)


# ============================================================================
# VIBE STATUS CATEGORIES (from CLAUDE.md)
# ============================================================================

class VibeCategory(str, Enum):
    """Vibe status word categories."""
    THINKING = "thinking"
    CONTEXT = "context"
    ACTION = "action"


# Vibe words by category (from CLAUDE.md)
VIBE_WORDS = {
    VibeCategory.THINKING: [
        "Wondering", "Stewing", "Cogitating", "Hoping", "Exploring", "Preparing"
    ],
    VibeCategory.CONTEXT: [
        "Mustering", "Coalescing", "Ideating"
    ],
    VibeCategory.ACTION: [
        "Completing", "Messaging", "Uploading", "Connecting",
        "Affirming", "Rejoicing", "Celebrating"
    ],
}


def get_vibe_category(vibe: str) -> Optional[VibeCategory]:
    """Get the category for a vibe word."""
    for category, words in VIBE_WORDS.items():
        if vibe in words:
            return category
    return None


# ============================================================================
# UI STATE DATA CLASSES
# ============================================================================

@dataclass
class UIState:
    """
    UI-level state for single-run lock and lifecycle tracking.

    Thread-safe via atomic flag reads/writes.
    """
    is_running: bool = False
    pending_approval: Optional[Dict[str, Any]] = None
    current_vibe: str = ""
    queued_input: Optional[str] = None
    current_run_id: Optional[str] = None

    def reset(self):
        """Reset state after run completes."""
        self.is_running = False
        self.pending_approval = None
        self.current_vibe = ""
        self.current_run_id = None
        # Note: queued_input preserved for next run


@dataclass
class UIEvent:
    """
    Event container for UI updates.

    Wraps core Event with UI-specific metadata.
    """
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_core_event(cls, event: Event) -> "UIEvent":
        """Convert core Event to UIEvent."""
        return cls(
            type=event.type.value,
            data=event.data,
            timestamp=event.timestamp
        )


# ============================================================================
# UI BRIDGE
# ============================================================================

class UIBridge:
    """
    Bridge between backend events and Flet UI.

    Responsibilities:
    - Subscribe to core EventBus
    - Buffer events in asyncio.Queue
    - Provide methods for UI components to consume events
    - Track UI state (is_running, pending_approval, vibe)
    - Handle approval responses (resume graph)

    Usage:
        bridge = UIBridge()

        # Start consuming events
        async for event in bridge.consume_events():
            if event.type == "status_changed":
                update_vibe_label(event.data["status"])
            elif event.type == "approval_requested":
                show_approval_modal(event.data)
    """

    def __init__(self):
        """Initialize UI Bridge."""
        self.state = UIState()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._event_bus: Optional[EventBus] = None
        self._subscription_queue: Optional[asyncio.Queue] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Callbacks for UI updates (set by UI components)
        self._on_vibe_update: Optional[Callable[[str], None]] = None
        self._on_approval_request: Optional[Callable[[str, Dict], None]] = None
        self._on_run_complete: Optional[Callable[[bool], None]] = None
        self._on_event: Optional[Callable[[UIEvent], None]] = None

        # Approval response future (for blocking on user decision)
        self._approval_future: Optional[asyncio.Future] = None

        logger.debug("UIBridge initialized")

    # ========================================================================
    # EVENT BUS INTEGRATION
    # ========================================================================

    def connect_event_bus(self) -> None:
        """
        Connect to the global EventBus.

        Must be called before starting event consumption.
        """
        self._event_bus = get_event_bus()
        self._subscription_queue = self._event_bus.subscribe()
        logger.info("UIBridge connected to EventBus")

    def disconnect_event_bus(self) -> None:
        """Disconnect from EventBus."""
        if self._event_bus and self._subscription_queue:
            self._event_bus.unsubscribe(self._subscription_queue)
            self._subscription_queue = None
        logger.info("UIBridge disconnected from EventBus")

    async def start_consuming(self) -> None:
        """
        Start consuming events from EventBus.

        Should be called as a background task.
        """
        if not self._subscription_queue:
            self.connect_event_bus()

        self._shutdown = False

        async for event in iter_queue(self._subscription_queue):
            if self._shutdown:
                break

            # Convert to UIEvent and process
            ui_event = UIEvent.from_core_event(event)
            await self._process_event(ui_event)

        logger.info("UIBridge stopped consuming events")

    async def stop_consuming(self) -> None:
        """Stop consuming events."""
        self._shutdown = True
        self.disconnect_event_bus()

    # ========================================================================
    # EVENT PROCESSING
    # ========================================================================

    async def _process_event(self, event: UIEvent) -> None:
        """
        Process a UI event and update state.

        Args:
            event: UIEvent to process.
        """
        event_type = event.type

        # Update state based on event type
        if event_type == EventType.STATUS_CHANGED.value:
            self.state.current_vibe = event.data.get("status", "")
            if self._on_vibe_update:
                self._on_vibe_update(self.state.current_vibe)

        elif event_type == EventType.APPROVAL_REQUESTED.value:
            self.state.pending_approval = event.data
            if self._on_approval_request:
                approval_type = event.data.get("type", "unknown")
                approval_data = event.data.get("data", {})
                self._on_approval_request(approval_type, approval_data)

        elif event_type == EventType.RUN_STARTED.value:
            self.state.is_running = True
            self.state.current_run_id = event.data.get("run_id")

        elif event_type == EventType.RUN_COMPLETED.value:
            success = event.data.get("success", True)
            self.state.reset()
            if self._on_run_complete:
                self._on_run_complete(success)

        elif event_type == EventType.RUN_CANCELLED.value:
            self.state.reset()
            if self._on_run_complete:
                self._on_run_complete(False)

        # Enqueue for external consumers
        await self._event_queue.put(event)

        # Call generic event handler
        if self._on_event:
            self._on_event(event)

    # ========================================================================
    # EVENT CONSUMPTION (for UI components)
    # ========================================================================

    async def consume_events(self):
        """
        Async generator for consuming UI events.

        Yields:
            UIEvent objects as they arrive.

        Example:
            async for event in bridge.consume_events():
                handle_event(event)
        """
        while not self._shutdown:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=0.1
                )
                yield event
            except asyncio.TimeoutError:
                continue

    def get_pending_event(self) -> Optional[UIEvent]:
        """
        Non-blocking check for pending events.

        Returns:
            UIEvent if available, None otherwise.
        """
        try:
            return self._event_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    # ========================================================================
    # CALLBACK REGISTRATION
    # ========================================================================

    def set_vibe_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for vibe status updates."""
        self._on_vibe_update = callback

    def set_approval_callback(self, callback: Callable[[str, Dict], None]) -> None:
        """Set callback for approval requests."""
        self._on_approval_request = callback

    def set_run_complete_callback(self, callback: Callable[[bool], None]) -> None:
        """Set callback for run completion."""
        self._on_run_complete = callback

    def set_event_callback(self, callback: Callable[[UIEvent], None]) -> None:
        """Set callback for all events."""
        self._on_event = callback

    # ========================================================================
    # APPROVAL HANDLING
    # ========================================================================

    async def wait_for_approval(self) -> Dict[str, Any]:
        """
        Wait for user approval decision.

        Called by graph when approval is requested.

        Returns:
            Dict with {"approved": bool, ...} from user.
        """
        self._approval_future = asyncio.get_event_loop().create_future()
        try:
            result = await self._approval_future
            return result
        finally:
            self._approval_future = None

    def submit_approval(self, approved: bool, feedback: str = "") -> None:
        """
        Submit user's approval decision.

        Called by approval modal when user clicks Approve/Deny.

        Args:
            approved: True if user approved, False if denied.
            feedback: Optional feedback text (for rejections).
        """
        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result({
                "approved": approved,
                "feedback": feedback
            })

        # Clear pending approval state
        self.state.pending_approval = None

        logger.info(f"Approval submitted: approved={approved}")

    # ========================================================================
    # EMITTERS (for direct UI → event publishing)
    # ========================================================================

    async def emit_vibe(self, vibe: str) -> None:
        """
        Emit vibe status update.

        Args:
            vibe: Vibe status word.
        """
        event = UIEvent(
            type=EventType.STATUS_CHANGED.value,
            data={"status": vibe}
        )
        await self._process_event(event)

    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit generic event.

        Args:
            event_type: Event type string.
            data: Event data dict.
        """
        event = UIEvent(type=event_type, data=data)
        await self._process_event(event)

    def request_approval(self, approval_type: str, data: Dict[str, Any]) -> None:
        """
        Request approval from UI (synchronous for graph integration).

        Args:
            approval_type: "patch" or "terminal".
            data: Approval data (PatchPlan or CommandPlan as dict).
        """
        self.state.pending_approval = {"type": approval_type, "data": data}

        if self._on_approval_request:
            self._on_approval_request(approval_type, data)

    # ========================================================================
    # RUN LIFECYCLE
    # ========================================================================

    def start_run(self, run_id: str) -> bool:
        """
        Attempt to start a new run.

        Returns:
            True if run started, False if another run is active.
        """
        if self.state.is_running:
            logger.warning("Cannot start run: another run is active")
            return False

        self.state.is_running = True
        self.state.current_run_id = run_id
        logger.info(f"Run started: {run_id}")
        return True

    def end_run(self, success: bool = True) -> None:
        """
        End the current run.

        Args:
            success: Whether run completed successfully.
        """
        run_id = self.state.current_run_id
        self.state.reset()
        logger.info(f"Run ended: {run_id} (success={success})")

    def cancel_run(self) -> None:
        """Cancel the current run."""
        if self.state.is_running:
            self.state.is_running = False
            logger.info(f"Run cancelled: {self.state.current_run_id}")
            # Note: actual cancellation is handled by the graph

    def queue_input(self, text: str) -> None:
        """
        Queue user input while run is active.

        Args:
            text: User input text.
        """
        self.state.queued_input = text
        logger.debug(f"Input queued: {text[:50]}...")

    def get_queued_input(self) -> Optional[str]:
        """
        Get and clear queued input.

        Returns:
            Queued input text or None.
        """
        text = self.state.queued_input
        self.state.queued_input = None
        return text


# ============================================================================
# GLOBAL BRIDGE INSTANCE
# ============================================================================

_global_bridge: Optional[UIBridge] = None


def get_ui_bridge() -> UIBridge:
    """
    Get global UIBridge instance (singleton).

    Returns:
        Global UIBridge instance.
    """
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = UIBridge()
    return _global_bridge


def reset_ui_bridge() -> None:
    """
    Reset global UIBridge instance (for testing).

    WARNING: Only use in tests.
    """
    global _global_bridge
    _global_bridge = None


__all__ = [
    "UIBridge",
    "UIState",
    "UIEvent",
    "VibeCategory",
    "VIBE_WORDS",
    "get_vibe_category",
    "get_ui_bridge",
    "reset_ui_bridge",
]
