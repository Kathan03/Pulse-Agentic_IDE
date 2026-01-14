"""
WebSocket Protocol Models for Pulse IDE Server.

Defines Pydantic models for all WebSocket message types used in
client-server communication. All messages use a consistent envelope
format with type, id, timestamp, and payload.

Protocol Overview:
- Client -> Server: agent_request, approval_response, cancel_request, ping
- Server -> Client: event, approval_required, run_result, error, pong
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Literal

from pydantic import BaseModel, Field


# ============================================================================
# MESSAGE TYPES
# ============================================================================

class MessageType(str, Enum):
    """WebSocket message types for Pulse IDE protocol."""

    # Client -> Server
    AGENT_REQUEST = "agent_request"
    APPROVAL_RESPONSE = "approval_response"
    CANCEL_REQUEST = "cancel_request"
    PING = "ping"

    # Server -> Client
    EVENT = "event"
    APPROVAL_REQUIRED = "approval_required"
    RUN_RESULT = "run_result"
    ERROR = "error"
    PONG = "pong"


# ============================================================================
# BASE MESSAGE ENVELOPE
# ============================================================================

class WSMessage(BaseModel):
    """
    Base WebSocket message envelope.

    All messages exchanged between client and server use this format.
    The payload field contains message-type-specific data.

    Attributes:
        type: Message type (from MessageType enum).
        id: Unique message ID for correlation/tracking.
        timestamp: ISO 8601 timestamp of message creation.
        payload: Message-type-specific payload data.
    """

    type: MessageType
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# ============================================================================
# CLIENT -> SERVER PAYLOADS
# ============================================================================

class AgentRequestPayload(BaseModel):
    """
    Payload for AGENT_REQUEST message.

    Sent by client to start a new agent run.

    Attributes:
        user_input: The user's query or instruction.
        project_root: Absolute path to the workspace root directory.
        conversation_id: Optional ID to resume an existing conversation.
        mode: Agent mode ("agent", "ask", or "plan").
        max_iterations: Maximum graph iterations (default: 10).
    """

    user_input: str = Field(..., description="User's query or instruction")
    project_root: str = Field(..., description="Absolute path to workspace root")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID to resume"
    )
    mode: Literal["agent", "ask", "plan"] = Field(
        default="agent", description="Agent mode"
    )
    max_iterations: int = Field(
        default=10, ge=1, le=50, description="Maximum graph iterations"
    )


class ApprovalResponsePayload(BaseModel):
    """
    Payload for APPROVAL_RESPONSE message.

    Sent by client in response to APPROVAL_REQUIRED.

    Attributes:
        run_id: The run ID that requires approval.
        approved: Whether the user approved the action.
        feedback: Optional feedback text (especially for denials).
    """

    run_id: str = Field(..., description="Run ID requiring approval")
    approved: bool = Field(..., description="Whether user approved the action")
    feedback: str = Field(default="", description="Optional feedback text")


class CancelRequestPayload(BaseModel):
    """
    Payload for CANCEL_REQUEST message.

    Sent by client to cancel an active run.

    Attributes:
        run_id: The run ID to cancel.
    """

    run_id: str = Field(..., description="Run ID to cancel")


# ============================================================================
# SERVER -> CLIENT PAYLOADS
# ============================================================================

class EventPayload(BaseModel):
    """
    Payload for EVENT message.

    Forwards EventBus events to the client.

    Attributes:
        event_type: The event type (from EventType enum value).
        data: Event-specific data dict.
    """

    event_type: str = Field(..., description="Event type string")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")


class ApprovalRequiredPayload(BaseModel):
    """
    Payload for APPROVAL_REQUIRED message.

    Sent when the agent needs user approval for an action.

    Attributes:
        run_id: The run ID that requires approval.
        approval_type: Type of approval ("patch" or "terminal").
        description: Human-readable description of the action.
        data: Approval-specific data (PatchPlan or CommandPlan as dict).
    """

    run_id: str = Field(..., description="Run ID requiring approval")
    approval_type: Literal["patch", "terminal"] = Field(
        ..., description="Type of approval needed"
    )
    description: str = Field(
        default="", description="Human-readable description of the action"
    )
    data: Dict[str, Any] = Field(..., description="PatchPlan or CommandPlan data")


class RunResultPayload(BaseModel):
    """
    Payload for RUN_RESULT message.

    Sent when an agent run completes (success or failure).

    Attributes:
        run_id: The completed run's ID.
        conversation_id: The conversation ID for history.
        success: Whether the run completed successfully.
        response: The agent's final response text.
        files_touched: List of files modified during the run.
        execution_log: List of execution log entries.
        cancelled: Whether the run was cancelled.
        error: Error message if the run failed.
    """

    run_id: str = Field(..., description="Completed run ID")
    conversation_id: str = Field(..., description="Conversation ID")
    success: bool = Field(..., description="Whether run succeeded")
    response: str = Field(default="", description="Agent's final response")
    files_touched: List[str] = Field(
        default_factory=list, description="Files modified"
    )
    execution_log: List[str] = Field(
        default_factory=list, description="Execution log entries"
    )
    cancelled: bool = Field(default=False, description="Whether run was cancelled")
    error: Optional[str] = Field(None, description="Error message if failed")


class ErrorPayload(BaseModel):
    """
    Payload for ERROR message.

    Sent when an error occurs during message processing.

    Attributes:
        code: Error code string (e.g., "invalid_message", "run_failed").
        message: Human-readable error message.
        details: Optional additional error details.
    """

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_event_message(event_type: str, data: Dict[str, Any]) -> WSMessage:
    """Create an EVENT message with the given type and data."""
    return WSMessage(
        type=MessageType.EVENT,
        payload=EventPayload(event_type=event_type, data=data).model_dump()
    )


def create_approval_required_message(
    run_id: str,
    approval_type: Literal["patch", "terminal"],
    data: Dict[str, Any],
    description: str = ""
) -> WSMessage:
    """Create an APPROVAL_REQUIRED message."""
    return WSMessage(
        type=MessageType.APPROVAL_REQUIRED,
        payload=ApprovalRequiredPayload(
            run_id=run_id,
            approval_type=approval_type,
            description=description,
            data=data
        ).model_dump()
    )


def create_run_result_message(
    run_id: str,
    conversation_id: str,
    success: bool,
    response: str = "",
    files_touched: Optional[List[str]] = None,
    execution_log: Optional[List[str]] = None,
    cancelled: bool = False,
    error: Optional[str] = None
) -> WSMessage:
    """Create a RUN_RESULT message."""
    return WSMessage(
        type=MessageType.RUN_RESULT,
        payload=RunResultPayload(
            run_id=run_id,
            conversation_id=conversation_id,
            success=success,
            response=response,
            files_touched=files_touched or [],
            execution_log=execution_log or [],
            cancelled=cancelled,
            error=error
        ).model_dump()
    )


def create_error_message(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> WSMessage:
    """Create an ERROR message."""
    return WSMessage(
        type=MessageType.ERROR,
        payload=ErrorPayload(code=code, message=message, details=details).model_dump()
    )


def create_pong_message(timestamp: Optional[str] = None) -> WSMessage:
    """Create a PONG message in response to PING."""
    return WSMessage(
        type=MessageType.PONG,
        payload={"timestamp": timestamp or datetime.now().isoformat()}
    )


__all__ = [
    # Enums
    "MessageType",
    # Models
    "WSMessage",
    "AgentRequestPayload",
    "ApprovalResponsePayload",
    "CancelRequestPayload",
    "EventPayload",
    "ApprovalRequiredPayload",
    "RunResultPayload",
    "ErrorPayload",
    # Helper functions
    "create_event_message",
    "create_approval_required_message",
    "create_run_result_message",
    "create_error_message",
    "create_pong_message",
]
