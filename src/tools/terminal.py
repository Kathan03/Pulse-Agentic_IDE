"""
Terminal Tool for Pulse IDE v2.6 (Phase 5 - Tier 2 Permissioned).

Implements safe command execution with human-in-the-loop approval:
- plan_terminal_cmd(): Generate CommandPlan with risk assessment (no execution)
- run_terminal_cmd(): Execute approved CommandPlan with timeout and output capture

Architecture:
- Strict separation: LLM requests via plan function, execution only after approval
- PID tracking: All subprocesses registered for shutdown handler cleanup
- Risk classification: LOW/MEDIUM/HIGH based on command patterns
- Output bounded: stdout/stderr capped at 10k chars to prevent context overflow

Safety:
- All commands run with cwd=project_root (workspace boundary enforcement)
- Timeout enforcement with graceful terminate → force kill fallback
- Subprocess PID tracking via processes.py registry
- Structured output (exit_code, stdout, stderr, timed_out, pid)
"""

import subprocess
import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from src.agents.state import CommandPlan
from src.core.processes import register_process

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Output size cap (prevent unbounded context growth)
MAX_OUTPUT_SIZE = 10000  # chars

# Default timeout for commands (2 minutes)
DEFAULT_TIMEOUT = 120  # seconds


# ============================================================================
# RISK CLASSIFICATION
# ============================================================================

def analyze_risk(command: str) -> Dict[str, str]:
    """
    Classify command risk level based on patterns.

    Args:
        command: Shell command string to analyze

    Returns:
        Dict with keys: {"level": "LOW"|"MEDIUM"|"HIGH", "reason": str}

    Risk Heuristics:
        - HIGH: Destructive file ops, privilege escalation, permission changes,
                disk writes to devices, network fetches, database ops
        - MEDIUM: Installs, file moves/renames, git pushes
        - LOW: Read-only commands (ls, cat, echo, git status, etc.)

    Examples:
        >>> analyze_risk("rm -rf /")
        {'level': 'HIGH', 'reason': 'Destructive file operation'}

        >>> analyze_risk("pip install pytest")
        {'level': 'MEDIUM', 'reason': 'Package installation'}

        >>> analyze_risk("ls -la")
        {'level': 'LOW', 'reason': 'Read-only command'}
    """
    command_lower = command.lower()

    # ========================================================================
    # HIGH RISK PATTERNS
    # ========================================================================

    high_risk_patterns = [
        # Destructive file operations
        ("rm -rf", "Destructive file operation"),
        ("rm -r", "Recursive delete operation"),
        ("del /s", "Recursive delete (Windows)"),
        ("rmdir /s", "Recursive directory delete (Windows)"),
        ("format ", "Disk format command"),
        ("mkfs", "Filesystem creation"),

        # Privilege escalation
        ("sudo ", "Privilege escalation"),
        ("su ", "User switch"),
        ("runas ", "Run as admin (Windows)"),

        # Permission changes
        ("chmod ", "Permission modification"),
        ("chown ", "Ownership change"),
        ("icacls ", "ACL modification (Windows)"),

        # Disk/device writes
        ("dd ", "Direct disk write"),
        ("/dev/", "Device file access"),

        # Network operations
        ("curl ", "Network fetch (arbitrary execution risk)"),
        ("wget ", "Network download"),
        ("nc ", "Netcat (network tool)"),

        # Database operations
        ("drop table", "Database table deletion"),
        ("drop database", "Database deletion"),
    ]

    for pattern, reason in high_risk_patterns:
        if pattern in command_lower:
            return {"level": "HIGH", "reason": reason}

    # ========================================================================
    # MEDIUM RISK PATTERNS
    # ========================================================================

    medium_risk_patterns = [
        # Package installs
        ("pip install", "Python package installation"),
        ("npm install", "Node package installation"),
        ("yarn add", "Yarn package installation"),
        ("apt-get install", "System package installation"),
        ("brew install", "Homebrew package installation"),

        # File moves/renames
        ("mv ", "File move/rename"),
        ("move ", "File move (Windows)"),
        ("ren ", "File rename (Windows)"),

        # Git operations
        ("git push", "Git push to remote"),
        ("git commit", "Git commit"),
        ("git reset --hard", "Destructive git reset"),

        # Build operations
        ("make clean", "Build cleanup"),
        ("npm run build", "NPM build script"),
    ]

    for pattern, reason in medium_risk_patterns:
        if pattern in command_lower:
            return {"level": "MEDIUM", "reason": reason}

    # ========================================================================
    # LOW RISK PATTERNS (Read-only)
    # ========================================================================

    low_risk_patterns = [
        # Directory listings
        "ls ", "dir ", "tree ",

        # File viewing
        "cat ", "head ", "tail ", "type ", "more ", "less ",

        # Search/grep
        "grep ", "find ", "where ",

        # Status/info commands
        "git status", "git log", "git diff", "git show",
        "python --version", "node --version", "npm --version",
        "pip list", "pip show", "npm ls",
        "pwd", "cd ", "echo ",
        "which ", "where ",
    ]

    for pattern in low_risk_patterns:
        if pattern in command_lower:
            return {"level": "LOW", "reason": "Read-only command"}

    # ========================================================================
    # DEFAULT: MEDIUM RISK (Unknown command)
    # ========================================================================

    return {"level": "MEDIUM", "reason": "Unknown command (default to MEDIUM risk)"}


# ============================================================================
# PLAN FUNCTION (Pre-approval)
# ============================================================================

def plan_terminal_cmd(
    command: str,
    rationale: str,
    project_root: Path,
    working_dir: Optional[Path] = None
) -> CommandPlan:
    """
    Create a CommandPlan for terminal execution (no execution, just planning).

    This is the function exposed to the Master Agent LLM. It generates a
    structured plan that requires user approval before execution.

    Args:
        command: Shell command to execute
        rationale: Explanation of why this command is needed
        project_root: Project root directory (enforces workspace boundary)
        working_dir: Optional working directory (defaults to project_root)

    Returns:
        CommandPlan model with risk assessment

    Example:
        >>> plan = plan_terminal_cmd(
        ...     command="pip install pytest",
        ...     rationale="Install testing framework",
        ...     project_root=Path("/workspace")
        ... )
        >>> plan.risk_label
        'MEDIUM'
    """
    # Default working_dir to project_root
    if working_dir is None:
        working_dir = project_root

    # Validate working_dir is within project_root
    try:
        working_dir = Path(working_dir).resolve()
        project_root = Path(project_root).resolve()

        # Check if working_dir is a child of project_root
        working_dir.relative_to(project_root)
    except ValueError:
        # working_dir is outside project_root - reset to project_root
        logger.warning(
            f"Working directory {working_dir} outside project root {project_root}. "
            f"Resetting to project root."
        )
        working_dir = project_root

    # Analyze risk
    risk_info = analyze_risk(command)

    # Create CommandPlan
    plan = CommandPlan(
        command=command,
        rationale=rationale,
        risk_label=risk_info["level"],  # type: ignore (Literal type checking)
        working_dir=str(working_dir),
    )

    logger.info(f"Created CommandPlan: {command} (risk={risk_info['level']})")
    return plan


# ============================================================================
# EXECUTE FUNCTION (Post-approval)
# ============================================================================

def run_terminal_cmd(
    plan: CommandPlan,
    project_root: Path,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute an approved CommandPlan with timeout and output capture.

    This function should ONLY be called after user approval. It:
    1. Spawns subprocess with cwd=plan.working_dir (or project_root)
    2. Registers PID in process registry (for shutdown cleanup)
    3. Captures stdout/stderr with size caps
    4. Enforces timeout with graceful terminate → force kill
    5. Returns structured output

    Args:
        plan: Approved CommandPlan from plan_terminal_cmd()
        project_root: Project root directory (workspace boundary enforcement)
        timeout: Timeout in seconds (defaults to DEFAULT_TIMEOUT)

    Returns:
        Dict with keys:
        {
            "exit_code": int,
            "stdout": str (bounded to MAX_OUTPUT_SIZE),
            "stderr": str (bounded to MAX_OUTPUT_SIZE),
            "timed_out": bool,
            "pid": int,
            "command": str,
        }

    Example:
        >>> plan = plan_terminal_cmd(...)
        >>> # User approves
        >>> result = run_terminal_cmd(plan, project_root=Path("/workspace"))
        >>> result["exit_code"]
        0
        >>> result["stdout"]
        'pytest installed successfully'
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    # Determine working directory
    working_dir = Path(plan.working_dir) if plan.working_dir else project_root
    working_dir = working_dir.resolve()

    logger.info(f"Executing command: {plan.command} (cwd={working_dir}, timeout={timeout}s)")

    # Initialize result structure
    result = {
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "pid": -1,
        "command": plan.command,
    }

    try:
        # ====================================================================
        # SUBPROCESS EXECUTION
        # ====================================================================

        # Determine shell based on platform
        if sys.platform == "win32":
            # Windows: use PowerShell or cmd
            shell = True
            shell_cmd = plan.command
        else:
            # Unix: use sh
            shell = True
            shell_cmd = plan.command

        # Spawn subprocess
        proc = subprocess.Popen(
            shell_cmd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(working_dir),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        result["pid"] = proc.pid if proc.pid else -1

        # Register in process registry for shutdown cleanup
        if proc.pid:
            register_process(proc, plan.command, cwd=working_dir)

        logger.info(f"Subprocess spawned: PID={proc.pid}")

        # ====================================================================
        # WAIT WITH TIMEOUT
        # ====================================================================

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            result["exit_code"] = proc.returncode

            # Truncate output if too large
            result["stdout"] = _truncate_output(stdout, MAX_OUTPUT_SIZE)
            result["stderr"] = _truncate_output(stderr, MAX_OUTPUT_SIZE)

            logger.info(
                f"Command completed: PID={proc.pid}, exit_code={proc.returncode}, "
                f"stdout={len(stdout)} chars, stderr={len(stderr)} chars"
            )

        except subprocess.TimeoutExpired:
            # Timeout - kill process
            logger.warning(f"Command timed out after {timeout}s: {plan.command}")
            result["timed_out"] = True

            # Graceful terminate
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill
                logger.warning(f"Force killing timed-out process PID={proc.pid}")
                proc.kill()
                proc.wait()

            # Capture partial output
            try:
                stdout, stderr = proc.communicate(timeout=1)
                result["stdout"] = _truncate_output(stdout, MAX_OUTPUT_SIZE)
                result["stderr"] = _truncate_output(stderr, MAX_OUTPUT_SIZE)
            except:
                result["stderr"] = f"[Timeout after {timeout}s - process killed]"

            result["exit_code"] = proc.returncode if proc.returncode else -1

        # Unregister from process registry (successfully completed)
        from src.core.processes import unregister_process
        if proc.pid:
            unregister_process(proc.pid)

        return result

    except Exception as e:
        # Execution error
        logger.error(f"Command execution failed: {e}", exc_info=True)
        result["stderr"] = f"Execution error: {str(e)}"
        result["exit_code"] = -1
        return result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _truncate_output(text: str, max_size: int) -> str:
    """
    Truncate output to max_size characters with truncation notice.

    Args:
        text: Output string to truncate
        max_size: Maximum size in characters

    Returns:
        Truncated string (or original if under limit)
    """
    if len(text) <= max_size:
        return text

    truncated = text[:max_size]
    notice = f"\n\n[... output truncated - {len(text)} total chars, showing first {max_size}]"
    return truncated + notice


__all__ = [
    "analyze_risk",
    "plan_terminal_cmd",
    "run_terminal_cmd",
]
