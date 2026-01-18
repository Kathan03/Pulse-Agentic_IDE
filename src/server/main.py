"""
Pulse IDE WebSocket Server Entry Point.

FastAPI application with WebSocket endpoint for remote client communication.
This server enables Electron/web frontends to interact with the Pulse agent
backend.

Usage:
    # Run the server
    python -m src.server.main

    # Or with custom host/port
    python -m src.server.main --host 0.0.0.0 --port 8080

    # For development with auto-reload
    uvicorn src.server.main:app --reload --host 127.0.0.1 --port 8765
"""

import argparse
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.server.routes.websocket import router as ws_router
from src.server.routes.health import router as health_router, set_server_start_time
from src.server.routes.settings import router as settings_router
from src.server.routes.conversations import router as conversations_router
from src.server.routes.workspace import router as workspace_router
from src.server.session import get_session_manager
from src.core.events import get_event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup/shutdown.

    Initializes global singletons on startup and cleans up
    resources on shutdown.
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("=" * 60)
    logger.info("Pulse IDE Server starting...")
    logger.info("=" * 60)

    # Record start time for uptime tracking
    set_server_start_time()

    # Initialize global singletons
    _ = get_event_bus()
    _ = get_session_manager()

    logger.info("Global singletons initialized")
    logger.info("Pulse IDE Server started successfully")
    logger.info("-" * 60)

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("-" * 60)
    logger.info("Pulse IDE Server shutting down...")

    # Cleanup event bus
    try:
        event_bus = get_event_bus()
        await event_bus.shutdown()
        logger.info("EventBus shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down EventBus: {e}")

    # Cleanup sessions (will disconnect all WebSockets)
    try:
        session_manager = get_session_manager()
        sessions = await session_manager.get_all_sessions()
        for connection_id in list(sessions.keys()):
            await session_manager.remove_session(connection_id)
        logger.info(f"Cleaned up {len(sessions)} sessions")
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")

    logger.info("Pulse IDE Server shutdown complete")
    logger.info("=" * 60)


# ============================================================================
# CREATE APPLICATION
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="Pulse IDE Server",
        description="WebSocket server for Pulse IDE agent backend. "
                    "Enables remote clients to interact with the AI agent.",
        version="2.6.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ========================================================================
    # CORS MIDDLEWARE
    # ========================================================================
    # Allow all origins for development. Restrict in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restrict to Electron app origin in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ========================================================================
    # INCLUDE ROUTERS
    # ========================================================================
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(settings_router, prefix="/api", tags=["settings"])
    app.include_router(conversations_router, tags=["conversations"])
    app.include_router(workspace_router, tags=["workspace"])
    app.include_router(ws_router, tags=["websocket"])

    # ========================================================================
    # ROOT ENDPOINT
    # ========================================================================
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with server info."""
        return {
            "name": "Pulse IDE Server",
            "version": "2.6.0",
            "status": "running",
            "websocket_url": "/ws",
            "docs_url": "/docs",
        }

    return app


# Create the app instance
app = create_app()


# ============================================================================
# SERVER RUNNER
# ============================================================================

def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    reload: bool = False,
    log_level: str = "info"
) -> None:
    """
    Run the Pulse IDE server with uvicorn.

    Args:
        host: Host address to bind to (default: 127.0.0.1).
        port: Port number to listen on (default: 8765, use 0 for dynamic allocation).
        reload: Enable auto-reload for development (default: False).
        log_level: Logging level (default: info).
    """
    import os

    # Check if running in Electron mode (production bundled)
    is_electron_mode = os.environ.get("PULSE_ELECTRON_MODE") == "true"

    if port == 0 or is_electron_mode:
        # Dynamic port allocation - use Server class for port detection
        _run_server_with_port_detection(host, port, log_level)
    else:
        # Standard mode with fixed port
        logger.info(f"Starting server on {host}:{port}")
        uvicorn.run(
            "src.server.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True,
        )


def _run_server_with_port_detection(
    host: str,
    port: int,
    log_level: str
) -> None:
    """
    Run server with dynamic port allocation and announce the port.

    Used when running in Electron production mode. Prints the allocated
    port in a special format that Electron can parse from stdout.
    """
    import socket

    # If port is 0, let the OS allocate a free port
    if port == 0:
        # Find a free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = s.getsockname()[1]

    logger.info(f"Starting server on {host}:{port}")

    # Print port announcement for Electron to parse
    # IMPORTANT: This exact format is parsed by Electron main.ts
    print(f"PULSE_PORT:{port}", flush=True)
    sys.stdout.flush()

    # Run uvicorn with the allocated port
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
    )
    server = uvicorn.Server(config)

    # Run the server
    asyncio.run(server.serve())


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Pulse IDE WebSocket Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port number to listen on"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level"
    )
    return parser.parse_args()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    args = parse_args()
    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )
