"""
Process Registry for Pulse IDE v2.6 (Phase 5).

Tracks all subprocess PIDs spawned by terminal commands and provides
cleanup semantics for orphan prevention (required by shutdown handler in Phase 7).

Architecture:
- Module-level registry stores active processes (PID + Popen handle + metadata)
- register_process() called by run_terminal_cmd after spawning
- cleanup_processes() called by app shutdown handler to kill all tracked processes
- Cross-platform: graceful terminate → force kill fallback

Safety:
- Best-effort cleanup (no exceptions raised on failure)
- Detailed logging for debugging
- Structured reports for shutdown diagnostics
"""

import subprocess
import time
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# MODULE-LEVEL PROCESS REGISTRY
# ============================================================================

_active_processes: Dict[int, Dict] = {}
"""
Global registry of active subprocesses.

Structure:
{
    pid: {
        "proc": subprocess.Popen,
        "command": str,
        "start_time": float (time.time()),
        "cwd": str,
    }
}
"""


# ============================================================================
# REGISTRATION
# ============================================================================

def register_process(proc: subprocess.Popen, command: str, cwd: Optional[Path] = None) -> None:
    """
    Register a subprocess in the global registry.

    Args:
        proc: subprocess.Popen instance
        command: Command string that was executed
        cwd: Working directory where command was executed (optional)

    Example:
        >>> proc = subprocess.Popen(["ls", "-la"], cwd="/workspace")
        >>> register_process(proc, "ls -la", cwd=Path("/workspace"))
    """
    global _active_processes

    if proc.pid is None:
        logger.warning(f"Cannot register process without PID: {command}")
        return

    _active_processes[proc.pid] = {
        "proc": proc,
        "command": command,
        "start_time": time.time(),
        "cwd": str(cwd) if cwd else None,
    }

    logger.info(f"Registered process PID={proc.pid}: {command}")


def unregister_process(pid: int) -> None:
    """
    Unregister a process from the global registry.

    Args:
        pid: Process ID to unregister

    Example:
        >>> unregister_process(12345)
    """
    global _active_processes

    if pid in _active_processes:
        command = _active_processes[pid]["command"]
        del _active_processes[pid]
        logger.info(f"Unregistered process PID={pid}: {command}")
    else:
        logger.debug(f"Process PID={pid} not in registry (already cleaned up?)")


# ============================================================================
# INTROSPECTION
# ============================================================================

def list_processes() -> List[Dict]:
    """
    List all active processes in the registry.

    Returns:
        List of process metadata dicts (without Popen handle).

    Example:
        >>> processes = list_processes()
        >>> processes[0]
        {
            'pid': 12345,
            'command': 'pip install pytest',
            'start_time': 1234567890.123,
            'cwd': '/workspace',
            'running': True
        }
    """
    global _active_processes

    processes = []
    for pid, data in _active_processes.items():
        proc = data["proc"]
        processes.append({
            "pid": pid,
            "command": data["command"],
            "start_time": data["start_time"],
            "cwd": data["cwd"],
            "running": proc.poll() is None,  # Check if still alive
        })

    return processes


# ============================================================================
# CLEANUP (Zombie Killer)
# ============================================================================

def cleanup_processes(timeout_terminate: float = 2.0, timeout_kill: float = 1.0) -> Dict:
    """
    Terminate all active subprocesses tracked in the registry.

    Strategy:
    1. Attempt graceful terminate (SIGTERM on Unix, TerminateProcess on Windows)
    2. Wait up to timeout_terminate seconds
    3. Force kill (SIGKILL on Unix, TerminateProcess on Windows) if still alive
    4. Unregister all processes

    Args:
        timeout_terminate: Seconds to wait for graceful termination (default: 2.0)
        timeout_kill: Seconds to wait after force kill (default: 1.0)

    Returns:
        Dict with cleanup report:
        {
            "total": int,
            "killed": int,
            "failed": List[Dict],  # PIDs that couldn't be killed
            "already_stopped": int,
        }

    Example:
        >>> report = cleanup_processes()
        >>> report
        {'total': 3, 'killed': 2, 'failed': [], 'already_stopped': 1}
    """
    global _active_processes

    logger.info(f"Starting process cleanup: {len(_active_processes)} processes tracked")

    report = {
        "total": len(_active_processes),
        "killed": 0,
        "failed": [],
        "already_stopped": 0,
    }

    # Make a copy of PIDs to iterate (avoid modification during iteration)
    pids = list(_active_processes.keys())

    for pid in pids:
        data = _active_processes[pid]
        proc = data["proc"]
        command = data["command"]

        try:
            # Check if already stopped
            if proc.poll() is not None:
                logger.info(f"Process PID={pid} already stopped: {command}")
                report["already_stopped"] += 1
                unregister_process(pid)
                continue

            # Step 1: Graceful terminate
            logger.info(f"Terminating process PID={pid}: {command}")
            proc.terminate()

            # Wait for graceful shutdown
            try:
                proc.wait(timeout=timeout_terminate)
                logger.info(f"Process PID={pid} terminated gracefully")
                report["killed"] += 1
                unregister_process(pid)
                continue
            except subprocess.TimeoutExpired:
                logger.warning(f"Process PID={pid} did not terminate gracefully, force killing")

            # Step 2: Force kill
            proc.kill()
            try:
                proc.wait(timeout=timeout_kill)
                logger.info(f"Process PID={pid} force killed")
                report["killed"] += 1
                unregister_process(pid)
            except subprocess.TimeoutExpired:
                logger.error(f"Process PID={pid} could not be killed (zombie?)")
                report["failed"].append({
                    "pid": pid,
                    "command": command,
                    "reason": "Timeout after force kill",
                })
                unregister_process(pid)  # Remove from registry anyway

        except Exception as e:
            logger.error(f"Error cleaning up process PID={pid}: {e}", exc_info=True)
            report["failed"].append({
                "pid": pid,
                "command": command,
                "reason": str(e),
            })
            unregister_process(pid)  # Remove from registry anyway

    logger.info(f"Process cleanup complete: {report}")
    return report


__all__ = [
    "register_process",
    "unregister_process",
    "list_processes",
    "cleanup_processes",
]
