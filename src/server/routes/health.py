"""
Health Check Endpoints for Pulse IDE Server.

Provides HTTP endpoints for monitoring server health
and getting server status information.

Endpoints:
- GET /api/health - Basic health check
- GET /api/status - Detailed server status
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.server.session import get_session_manager

router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str
    timestamp: str
    version: str


class StatusResponse(BaseModel):
    """Response model for /status endpoint with more details."""

    status: str
    timestamp: str
    version: str
    active_sessions: int
    active_runs: int
    uptime_seconds: Optional[float] = None


# ============================================================================
# SERVER STATE
# ============================================================================

# Track server start time for uptime calculation
_server_start_time: Optional[datetime] = None


def set_server_start_time() -> None:
    """Set the server start time (called on startup)."""
    global _server_start_time
    _server_start_time = datetime.now()


def get_uptime_seconds() -> Optional[float]:
    """Get server uptime in seconds."""
    if _server_start_time is None:
        return None
    return (datetime.now() - _server_start_time).total_seconds()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse with status, timestamp, and version.

    Example:
        GET /api/health
        {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00",
            "version": "2.6.0"
        }
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.6.0"
    )


@router.get("/status", response_model=StatusResponse)
async def server_status() -> StatusResponse:
    """
    Detailed server status endpoint.

    Returns:
        StatusResponse with connection counts and uptime.

    Example:
        GET /api/status
        {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00",
            "version": "2.6.0",
            "active_sessions": 2,
            "active_runs": 1,
            "uptime_seconds": 3600.5
        }
    """
    session_manager = get_session_manager()

    return StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.6.0",
        active_sessions=await session_manager.get_session_count(),
        active_runs=await session_manager.get_active_run_count(),
        uptime_seconds=get_uptime_seconds()
    )


__all__ = ["router", "set_server_start_time"]
