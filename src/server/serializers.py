"""
Event Serialization Utilities for Pulse IDE Server.

Provides functions to convert Python objects (Pydantic models, datetime,
Path objects, etc.) into JSON-safe dictionaries for WebSocket transport.

Handles:
- Pydantic BaseModel instances (PatchPlan, CommandPlan, ToolOutput)
- datetime objects -> ISO 8601 strings
- Path objects -> string paths
- Nested dicts and lists
- Primitive types (str, int, float, bool, None)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def serialize_event_data(data: Any) -> Dict[str, Any]:
    """
    Serialize event data to a JSON-safe dictionary.

    Recursively converts Python objects to JSON-serializable types.

    Args:
        data: Any Python object to serialize.

    Returns:
        JSON-safe dictionary representation.

    Examples:
        >>> from src.agents.state import PatchPlan
        >>> plan = PatchPlan(file_path="test.st", diff="+code", rationale="Add code")
        >>> serialize_event_data(plan)
        {'file_path': 'test.st', 'diff': '+code', 'rationale': 'Add code', 'action': 'modify'}
    """
    if data is None:
        return {}

    if isinstance(data, BaseModel):
        return data.model_dump()

    if isinstance(data, dict):
        return {k: _serialize_value(v) for k, v in data.items()}

    if isinstance(data, (list, tuple)):
        return [_serialize_value(v) for v in data]

    return {"value": _serialize_value(data)}


def _serialize_value(value: Any) -> Any:
    """
    Serialize a single value to a JSON-safe type.

    Args:
        value: Any Python value.

    Returns:
        JSON-serializable representation.
    """
    if value is None:
        return None

    # Pydantic models
    if isinstance(value, BaseModel):
        return value.model_dump()

    # datetime objects
    if isinstance(value, datetime):
        return value.isoformat()

    # Path-like objects
    if isinstance(value, Path) or hasattr(value, "__fspath__"):
        return str(value)

    # Enums
    if hasattr(value, "value"):
        return value.value

    # Collections
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]

    if isinstance(value, set):
        return [_serialize_value(v) for v in value]

    # Primitives
    if isinstance(value, (str, int, float, bool)):
        return value

    # Bytes
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()

    # Fallback: convert to string
    try:
        return str(value)
    except Exception as e:
        logger.warning(f"Failed to serialize value {type(value)}: {e}")
        return f"<unserializable: {type(value).__name__}>"


def serialize_patch_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a PatchPlan dict for WebSocket transport.

    Ensures all fields are present and properly formatted.

    Args:
        data: PatchPlan as dict.

    Returns:
        Serialized PatchPlan dict.
    """
    return {
        "file_path": str(data.get("file_path", "")),
        "diff": str(data.get("diff", "")),
        "rationale": str(data.get("rationale", "")),
        "action": str(data.get("action", "modify")),
    }


def serialize_command_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a CommandPlan dict for WebSocket transport.

    Ensures all fields are present and properly formatted.

    Args:
        data: CommandPlan as dict.

    Returns:
        Serialized CommandPlan dict.
    """
    return {
        "command": str(data.get("command", "")),
        "rationale": str(data.get("rationale", "")),
        "risk_label": str(data.get("risk_label", "MEDIUM")),
        "working_dir": data.get("working_dir"),
    }


def serialize_tool_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a ToolOutput dict for WebSocket transport.

    Ensures all fields are present and properly formatted.

    Args:
        data: ToolOutput as dict.

    Returns:
        Serialized ToolOutput dict.
    """
    return {
        "tool_name": str(data.get("tool_name", "")),
        "success": bool(data.get("success", False)),
        "result": _serialize_value(data.get("result")),
        "error": data.get("error"),
        "timestamp": str(data.get("timestamp", datetime.now().isoformat())),
        "summary": str(data.get("summary", "")),
        "next_steps": list(data.get("next_steps", [])),
    }


def serialize_approval_data(
    approval_type: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Serialize approval data based on type.

    Args:
        approval_type: "patch" or "terminal".
        data: The approval data dict.

    Returns:
        Serialized approval data.
    """
    if approval_type == "patch":
        return serialize_patch_plan(data)
    elif approval_type == "terminal":
        return serialize_command_plan(data)
    else:
        return serialize_event_data(data)


def deserialize_agent_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize an agent request payload.

    Validates and normalizes the request fields.

    Args:
        payload: Raw request payload from client.

    Returns:
        Normalized request dict.

    Raises:
        ValueError: If required fields are missing.
    """
    user_input = payload.get("user_input")
    if not user_input or not isinstance(user_input, str):
        raise ValueError("user_input is required and must be a string")

    project_root = payload.get("project_root")
    if not project_root or not isinstance(project_root, str):
        raise ValueError("project_root is required and must be a string")

    return {
        "user_input": user_input.strip(),
        "project_root": project_root,
        "conversation_id": payload.get("conversation_id"),
        "mode": payload.get("mode", "agent"),
        "max_iterations": min(max(int(payload.get("max_iterations", 10)), 1), 50),
    }


def deserialize_approval_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize an approval response payload.

    Validates and normalizes the response fields.

    Args:
        payload: Raw response payload from client.

    Returns:
        Normalized response dict.

    Raises:
        ValueError: If required fields are missing.
    """
    run_id = payload.get("run_id")
    if not run_id or not isinstance(run_id, str):
        raise ValueError("run_id is required and must be a string")

    approved = payload.get("approved")
    if not isinstance(approved, bool):
        raise ValueError("approved is required and must be a boolean")

    return {
        "run_id": run_id,
        "approved": approved,
        "feedback": str(payload.get("feedback", "")),
    }


__all__ = [
    "serialize_event_data",
    "serialize_patch_plan",
    "serialize_command_plan",
    "serialize_tool_output",
    "serialize_approval_data",
    "deserialize_agent_request",
    "deserialize_approval_response",
]
