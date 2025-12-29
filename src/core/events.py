"""
Async Event Bus for Pulse IDE v2.6 (Phase 3).

Provides minimal async event streaming for:
- Vibe status updates ("Wondering", "Preparing", etc.)
- Lifecycle events (node entered, tool requested, approval requested, etc.)
- UI heartbeat during long operations

Phase 3 scope: Simple asyncio.Queue-based implementation.
Phase 7 will integrate with Flet UI for real-time updates.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# EVENT TYPES
# ============================================================================

class EventType(str, Enum):
    """Event types for the event bus."""

    # Status events
    STATUS_CHANGED = "status_changed"

    # Lifecycle events
    NODE_ENTERED = "node_entered"
    NODE_EXITED = "node_exited"
    TOOL_REQUESTED = "tool_requested"
    TOOL_EXECUTED = "tool_executed"

    # Approval events
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"

    # Cancellation events
    RUN_CANCELLED = "run_cancelled"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"


# ============================================================================
# EVENT MODEL
# ============================================================================

class Event:
    """
    Generic event container.

    Attributes:
        type: Event type (from EventType enum).
        data: Event payload (dict with event-specific data).
        timestamp: ISO timestamp of event creation.
    """

    def __init__(self, event_type: EventType, data: Optional[Dict[str, Any]] = None):
        self.type = event_type
        self.data = data or {}
        self.timestamp = datetime.now().isoformat()

    def __repr__(self) -> str:
        return f"Event(type={self.type}, data={self.data}, timestamp={self.timestamp})"


# ============================================================================
# EVENT BUS
# ============================================================================

class EventBus:
    """
    Simple async event bus using asyncio.Queue.

    Supports:
    - Publishing events to all subscribers
    - Rate-limited status updates (prevents spam)
    - Multiple concurrent subscribers
    - Clean shutdown

    Phase 3 scope: Single global event bus instance.
    """

    def __init__(self, status_rate_limit_seconds: float = 2.0):
        """
        Initialize event bus.

        Args:
            status_rate_limit_seconds: Minimum time between status updates (default: 2.0s).
        """
        self._queues: list[asyncio.Queue] = []
        self._status_rate_limit = status_rate_limit_seconds
        self._last_status_time: float = 0.0
        self._shutdown = False

        logger.debug("EventBus initialized")

    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to event stream.

        Returns:
            asyncio.Queue that will receive events.

        Example:
            >>> event_queue = event_bus.subscribe()
            >>> async for event in iter_queue(event_queue):
            ...     print(f"Received: {event.type}")
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.append(queue)
        logger.debug(f"New subscriber (total: {len(self._queues)})")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from event stream.

        Args:
            queue: The queue to remove.
        """
        if queue in self._queues:
            self._queues.remove(queue)
            logger.debug(f"Subscriber removed (total: {len(self._queues)})")

    async def publish(self, event: Event) -> None:
        """
        Publish event to all subscribers.

        Args:
            event: Event to publish.

        Note:
            Status events are rate-limited to prevent UI spam.
        """
        if self._shutdown:
            logger.warning("EventBus is shutdown, ignoring event")
            return

        # Rate-limit status events
        if event.type == EventType.STATUS_CHANGED:
            now = time.time()
            if now - self._last_status_time < self._status_rate_limit:
                logger.debug(f"Status update rate-limited: {event.data.get('status')}")
                return
            self._last_status_time = now

        # Publish to all subscribers
        for queue in self._queues:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to publish event to subscriber: {e}")

        logger.debug(f"Published event: {event.type} to {len(self._queues)} subscribers")

    async def shutdown(self) -> None:
        """
        Shutdown event bus and clear all queues.

        Sends None sentinel to all queues to signal shutdown.
        """
        self._shutdown = True
        logger.info("EventBus shutting down")

        # Send shutdown sentinel to all queues
        for queue in self._queues:
            try:
                await queue.put(None)  # Sentinel value
            except Exception as e:
                logger.error(f"Failed to send shutdown sentinel: {e}")

        self._queues.clear()
        logger.info("EventBus shutdown complete")


# ============================================================================
# GLOBAL EVENT BUS INSTANCE
# ============================================================================

_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get global EventBus instance (singleton).

    Returns:
        Global EventBus instance.
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """
    Reset global EventBus instance (for testing).

    WARNING: Only use in tests. Production code should never call this.
    """
    global _global_event_bus
    _global_event_bus = None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def emit_status(status: str) -> None:
    """
    Emit status update event.

    Args:
        status: Vibe status word (e.g., "Wondering", "Preparing").

    Example:
        >>> await emit_status("Exploring")
    """
    event = Event(EventType.STATUS_CHANGED, {"status": status})
    await get_event_bus().publish(event)


async def emit_node_entered(node_name: str) -> None:
    """
    Emit node entered event.

    Args:
        node_name: Name of the node being entered.
    """
    event = Event(EventType.NODE_ENTERED, {"node": node_name})
    await get_event_bus().publish(event)


async def emit_node_exited(node_name: str) -> None:
    """
    Emit node exited event.

    Args:
        node_name: Name of the node being exited.
    """
    event = Event(EventType.NODE_EXITED, {"node": node_name})
    await get_event_bus().publish(event)


async def emit_tool_requested(tool_name: str, args: Optional[Dict[str, Any]] = None) -> None:
    """
    Emit tool requested event.

    Args:
        tool_name: Name of the tool being requested.
        args: Tool arguments (optional).
    """
    event = Event(EventType.TOOL_REQUESTED, {"tool": tool_name, "args": args or {}})
    await get_event_bus().publish(event)


async def emit_tool_executed(tool_name: str, success: bool, result: Any = None) -> None:
    """
    Emit tool executed event.

    Args:
        tool_name: Name of the tool that was executed.
        success: Whether tool execution succeeded.
        result: Tool result (optional).
    """
    event = Event(EventType.TOOL_EXECUTED, {"tool": tool_name, "success": success, "result": result})
    await get_event_bus().publish(event)


async def emit_approval_requested(approval_type: Literal["patch", "terminal"], data: Dict[str, Any]) -> None:
    """
    Emit approval requested event.

    Args:
        approval_type: Type of approval ("patch" or "terminal").
        data: Approval data (PatchPlan or CommandPlan as dict).
    """
    event = Event(EventType.APPROVAL_REQUESTED, {"type": approval_type, "data": data})
    await get_event_bus().publish(event)


async def emit_approval_granted(approval_type: Literal["patch", "terminal"]) -> None:
    """
    Emit approval granted event.

    Args:
        approval_type: Type of approval that was granted.
    """
    event = Event(EventType.APPROVAL_GRANTED, {"type": approval_type})
    await get_event_bus().publish(event)


async def emit_approval_denied(approval_type: Literal["patch", "terminal"]) -> None:
    """
    Emit approval denied event.

    Args:
        approval_type: Type of approval that was denied.
    """
    event = Event(EventType.APPROVAL_DENIED, {"type": approval_type})
    await get_event_bus().publish(event)


async def emit_run_started(run_id: str) -> None:
    """
    Emit run started event.

    Args:
        run_id: Unique run identifier.
    """
    event = Event(EventType.RUN_STARTED, {"run_id": run_id})
    await get_event_bus().publish(event)


async def emit_run_completed(run_id: str, success: bool) -> None:
    """
    Emit run completed event.

    Args:
        run_id: Unique run identifier.
        success: Whether run completed successfully.
    """
    event = Event(EventType.RUN_COMPLETED, {"run_id": run_id, "success": success})
    await get_event_bus().publish(event)


async def emit_run_cancelled(run_id: str) -> None:
    """
    Emit run cancelled event.

    Args:
        run_id: Unique run identifier.
    """
    event = Event(EventType.RUN_CANCELLED, {"run_id": run_id})
    await get_event_bus().publish(event)


# ============================================================================
# ASYNC QUEUE ITERATOR HELPER
# ============================================================================

async def iter_queue(queue: asyncio.Queue):
    """
    Async iterator for asyncio.Queue.

    Yields items from queue until None sentinel is received.

    Args:
        queue: asyncio.Queue to iterate over.

    Yields:
        Items from queue until None is received.

    Example:
        >>> queue = event_bus.subscribe()
        >>> async for event in iter_queue(queue):
        ...     print(event.type)
    """
    while True:
        item = await queue.get()
        if item is None:  # Shutdown sentinel
            break
        yield item


__all__ = [
    "EventType",
    "Event",
    "EventBus",
    "get_event_bus",
    "reset_event_bus",
    "emit_status",
    "emit_node_entered",
    "emit_node_exited",
    "emit_tool_requested",
    "emit_tool_executed",
    "emit_approval_requested",
    "emit_approval_granted",
    "emit_approval_denied",
    "emit_run_started",
    "emit_run_completed",
    "emit_run_cancelled",
    "iter_queue",
]
