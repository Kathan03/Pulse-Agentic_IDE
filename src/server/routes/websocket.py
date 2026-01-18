"""
WebSocket Endpoint Handler for Pulse IDE Server.

Provides the main WebSocket endpoint for client-server communication.
Handles message routing, agent execution, approval flow, and cleanup.

Protocol:
1. Client connects to /ws
2. Server sends connection confirmation (PONG with connection_id)
3. Client sends AGENT_REQUEST to start a run
4. Server streams EVENTs and may send APPROVAL_REQUIRED
5. Client responds with APPROVAL_RESPONSE if needed
6. Server sends RUN_RESULT when complete
"""

import asyncio
import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.server.models import (
    WSMessage,
    MessageType,
    CancelRequestPayload,
    create_run_result_message,
    create_error_message,
    create_pong_message,
    create_event_message,
)
from src.server.session import Session, get_session_manager
from src.server.networked_bridge import NetworkedBridge
from src.server.serializers import (
    deserialize_agent_request,
    deserialize_approval_response,
)
from src.agents.runtime import (
    run_agent,
    resume_with_approval,
    cancel_current_run,
    is_run_active,
    get_current_run_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Track bridges per connection for cleanup
_connection_bridges: Dict[str, NetworkedBridge] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for Pulse IDE clients.

    Handles:
    - Connection setup and teardown
    - Message routing to appropriate handlers
    - Error handling and cleanup

    Protocol:
    - Client connects and receives connection confirmation
    - Client sends AGENT_REQUEST to start a run
    - Server streams EVENTs during execution
    - Server sends APPROVAL_REQUIRED when approval needed
    - Client responds with APPROVAL_RESPONSE
    - Server sends RUN_RESULT when complete
    """
    # Accept connection
    await websocket.accept()
    connection_id = str(uuid.uuid4())

    # Create session
    session_manager = get_session_manager()
    session = await session_manager.create_session(connection_id, websocket)

    # Create and connect bridge
    bridge = NetworkedBridge(session)
    await bridge.connect()
    _connection_bridges[connection_id] = bridge

    logger.info(f"WebSocket connected: {connection_id}")

    try:
        # Send connection confirmation
        confirmation = create_pong_message()
        confirmation.payload["connection_id"] = connection_id
        confirmation.payload["status"] = "connected"
        await websocket.send_json(confirmation.model_dump())

        # Message handling loop
        while True:
            try:
                data = await websocket.receive_json()

                # Parse message
                try:
                    message = WSMessage(**data)
                except Exception as e:
                    logger.warning(f"Invalid message format: {e}")
                    await send_error(websocket, "invalid_message", f"Invalid message format: {e}")
                    continue

                # Route to handler
                await handle_message(session, bridge, message)

            except ValueError as e:
                # Invalid JSON or message format
                await send_error(websocket, "invalid_message", str(e))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Cleanup
        await bridge.disconnect()
        if connection_id in _connection_bridges:
            del _connection_bridges[connection_id]
        await session_manager.remove_session(connection_id)
        logger.info(f"WebSocket cleanup complete: {connection_id}")


async def handle_message(session: Session, bridge: NetworkedBridge, message: WSMessage):
    """
    Route incoming message to appropriate handler.

    Args:
        session: The Session for this connection.
        bridge: The NetworkedBridge for this connection.
        message: The parsed WSMessage.
    """
    handlers = {
        MessageType.AGENT_REQUEST: handle_agent_request,
        MessageType.APPROVAL_RESPONSE: handle_approval_response,
        MessageType.CANCEL_REQUEST: handle_cancel_request,
        MessageType.PING: handle_ping,
    }

    # Handle string type values
    msg_type = message.type
    if isinstance(msg_type, str):
        try:
            msg_type = MessageType(msg_type)
        except ValueError:
            await send_error(
                session.websocket,
                "unknown_message_type",
                f"Unknown message type: {message.type}"
            )
            return

    handler = handlers.get(msg_type)
    if handler:
        await handler(session, bridge, message)
    else:
        await send_error(
            session.websocket,
            "unknown_message_type",
            f"Unknown message type: {message.type}"
        )


async def handle_agent_request(
    session: Session,
    bridge: NetworkedBridge,
    message: WSMessage
):
    """
    Handle AGENT_REQUEST - start a new agent run.

    Validates the request, associates a run with the session,
    and starts agent execution in a background task.

    Args:
        session: The Session for this connection.
        bridge: The NetworkedBridge for this connection.
        message: The AGENT_REQUEST message.
    """
    try:
        # Parse and validate payload
        try:
            request = deserialize_agent_request(message.payload)
        except ValueError as e:
            await send_error(session.websocket, "invalid_request", str(e))
            return

        # Check if already running
        if session.is_running:
            await send_error(
                session.websocket,
                "run_already_active",
                "A run is already active for this session"
            )
            return

        # Check global run lock (single-run enforcement)
        if is_run_active():
            await send_error(
                session.websocket,
                "server_busy",
                "Another run is active on the server. Please wait."
            )
            return

        # Generate run_id and thread_id
        run_id = str(uuid.uuid4())
        thread_id = session.thread_id or str(uuid.uuid4())

        # Associate run with session
        session_manager = get_session_manager()
        await session_manager.associate_run(session.connection_id, run_id, thread_id)
        session.conversation_id = request.get("conversation_id")
        session.project_root = request["project_root"]

        logger.info(f"Starting agent run {run_id} for session {session.connection_id}")

        # Run agent in background task
        asyncio.create_task(
            execute_agent_run(session, bridge, run_id, request)
        )

    except Exception as e:
        logger.error(f"Error handling agent request: {e}", exc_info=True)
        await send_error(session.websocket, "agent_request_failed", str(e))


async def execute_agent_run(
    session: Session,
    bridge: NetworkedBridge,
    run_id: str,
    request: Dict[str, Any]
):
    """
    Execute agent run and send result to client.

    Runs the agent in the background and sends RUN_RESULT
    when complete.

    Args:
        session: The Session for this connection.
        bridge: The NetworkedBridge for this connection.
        run_id: The unique run ID.
        request: The validated agent request.
    """
    session_manager = get_session_manager()
    waiting_for_approval = False

    try:
        # Run the agent with the same run_id as the session
        result = await run_agent(
            user_input=request["user_input"],
            project_root=request["project_root"],
            max_iterations=request["max_iterations"],
            config={"thread_id": session.thread_id},
            conversation_id=request.get("conversation_id"),
            mode=request.get("mode", "agent"),
            run_id=run_id
        )

        # Check if waiting for approval (don't send run_result yet)
        if result.get("waiting_for_approval"):
            logger.info(f"Agent run {run_id} paused for approval, not sending run_result")
            waiting_for_approval = True
            return

        # Send result
        result_message = create_run_result_message(
            run_id=run_id,
            conversation_id=result.get("conversation_id", ""),
            success=result.get("success", False),
            response=result.get("response", ""),
            files_touched=result.get("files_touched", []),
            execution_log=result.get("execution_log", []),
            cancelled=result.get("cancelled", False),
            error=result.get("error")
        )
        await session.websocket.send_json(result_message.model_dump())

        logger.info(f"Agent run {run_id} completed: success={result.get('success')}")

    except Exception as e:
        logger.error(f"Agent run {run_id} failed: {e}", exc_info=True)
        await send_error(session.websocket, "run_failed", str(e))

    finally:
        # Clear run state ONLY if not waiting for approval
        if not waiting_for_approval:
            await session_manager.clear_run(run_id)
        else:
            logger.info(f"Session run {run_id} kept active for approval")


async def handle_approval_response(
    session: Session,
    bridge: NetworkedBridge,
    message: WSMessage
):
    """
    Handle APPROVAL_RESPONSE - user approved/denied action.

    Validates the response and resumes the paused graph
    with the user's decision.

    Args:
        session: The Session for this connection.
        bridge: The NetworkedBridge for this connection.
        message: The APPROVAL_RESPONSE message.
    """
    try:
        # Parse and validate payload
        try:
            response = deserialize_approval_response(message.payload)
        except ValueError as e:
            await send_error(session.websocket, "invalid_response", str(e))
            return

        run_id = response["run_id"]
        approved = response["approved"]
        feedback = response["feedback"]

        # Verify run_id matches
        if run_id != session.current_run_id:
            await send_error(
                session.websocket,
                "invalid_run_id",
                f"Run ID mismatch: expected {session.current_run_id}, got {run_id}"
            )
            return

        # Check if there's a pending approval
        if not bridge.has_pending_approval():
            await send_error(
                session.websocket,
                "no_pending_approval",
                "No approval is pending for this run"
            )
            return

        logger.info(f"Approval response received for run {run_id}: approved={approved}")

        # Submit approval to bridge (resolves the waiting Future)
        bridge.submit_approval(approved, feedback)

        # Resume the graph
        # Note: Use runtime's run_id (may differ from session's)
        runtime_run_id = get_current_run_id()
        if not runtime_run_id:
            await send_error(session.websocket, "no_active_run", "No active run to resume")
            return
            
        result = await resume_with_approval(
            run_id=runtime_run_id,
            approved=approved,
            project_root=session.project_root,
            config={"thread_id": session.thread_id}
        )

        # Send intermediate event to confirm approval was processed
        await bridge.send_event(
            event_type="approval_processed",
            data={
                "run_id": run_id,
                "approved": approved,
            }
        )

        # Send the final RUN_RESULT with the agent's response
        result_message = create_run_result_message(
            run_id=run_id,  # Use session's run_id for frontend consistency
            conversation_id=result.get("conversation_id", ""),
            success=result.get("success", False),
            response=result.get("response", ""),
            files_touched=result.get("files_touched", []),
            execution_log=result.get("execution_log", []),
            cancelled=result.get("cancelled", False),
            error=result.get("error")
        )
        await session.websocket.send_json(result_message.model_dump())
        
        # Send run_completed event
        await bridge.send_event(
            event_type="run_completed",
            data={"run_id": run_id, "success": result.get("success", False)}
        )
        
        # Clear session run state now that resume is complete
        session_manager = get_session_manager()
        await session_manager.clear_run(run_id)
        
        logger.info(f"Resume result sent for run {run_id}: success={result.get('success')}")

    except Exception as e:
        logger.error(f"Error handling approval response: {e}", exc_info=True)
        await send_error(session.websocket, "approval_failed", str(e))


async def handle_cancel_request(
    session: Session,
    bridge: NetworkedBridge,
    message: WSMessage
):
    """
    Handle CANCEL_REQUEST - cancel active run.

    Validates the request and signals cancellation to the graph.

    Args:
        session: The Session for this connection.
        bridge: The NetworkedBridge for this connection.
        message: The CANCEL_REQUEST message.
    """
    try:
        payload = CancelRequestPayload(**message.payload)

        if payload.run_id != session.current_run_id:
            await send_error(
                session.websocket,
                "invalid_run_id",
                "No matching active run to cancel"
            )
            return

        # Cancel the run
        cancelled = cancel_current_run()

        if cancelled:
            # Send cancellation event
            cancel_event = create_event_message(
                event_type="run_cancelled",
                data={"run_id": payload.run_id}
            )
            await session.websocket.send_json(cancel_event.model_dump())
            logger.info(f"Run {payload.run_id} cancellation requested")
        else:
            await send_error(
                session.websocket,
                "cancel_failed",
                "Failed to cancel run"
            )

    except Exception as e:
        logger.error(f"Error handling cancel request: {e}", exc_info=True)
        await send_error(session.websocket, "cancel_failed", str(e))


async def handle_ping(
    session: Session,
    bridge: NetworkedBridge,
    message: WSMessage
):
    """
    Handle PING - respond with PONG for keep-alive.

    Args:
        session: The Session for this connection.
        bridge: The NetworkedBridge for this connection.
        message: The PING message.
    """
    pong = create_pong_message(message.timestamp)
    await session.websocket.send_json(pong.model_dump())
    session.update_activity()


async def send_error(websocket: WebSocket, code: str, message: str):
    """
    Send an error message to the client.

    Args:
        websocket: The WebSocket to send to.
        code: Error code string.
        message: Human-readable error message.
    """
    error_msg = create_error_message(code=code, message=message)
    await websocket.send_json(error_msg.model_dump())


def get_bridge_for_connection(connection_id: str) -> Optional[NetworkedBridge]:
    """
    Get the NetworkedBridge for a connection.

    Args:
        connection_id: The connection ID.

    Returns:
        NetworkedBridge if found, None otherwise.
    """
    return _connection_bridges.get(connection_id)


__all__ = ["router", "get_bridge_for_connection"]
