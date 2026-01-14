"""
Pulse IDE Server Routes Package.

Contains FastAPI route handlers for:
- WebSocket endpoint (/ws)
- Health check endpoints (/api/health)
"""

from src.server.routes.websocket import router as ws_router
from src.server.routes.health import router as health_router

__all__ = ["ws_router", "health_router"]
