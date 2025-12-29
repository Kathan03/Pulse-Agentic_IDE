"""
Dependency Manager for Pulse IDE v2.6 (Phase 5 - Tier 2 Permissioned).

Detects project tooling and proposes safe install commands (never executes directly).
All proposals are routed to run_terminal_cmd for human approval.

Detection:
- Python: venv status, requirements.txt, pyproject.toml
- Node: package.json, package-lock.json, yarn.lock
- Java: pom.xml, build.gradle, build.gradle.kts

Safety:
- Fail fast: If Python deps exist but no venv active, returns warning + no proposal
- Never executes commands: Only generates proposals for terminal tool
- Structured output: detection results + warnings + command proposals

Output Format:
{
    "detected": {"python": bool, "node": bool, "java": bool},
    "safe_to_install": bool,
    "warnings": List[str],
    "proposals": List[
        {"tool": "run_terminal_cmd", "command": str, "rationale": str}
    ]
}
"""

import sys
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# PYTHON DETECTION
# ============================================================================

def detect_python_tooling(project_root: Path) -> Dict[str, Any]:
    """
    Detect Python project tooling and venv status.

    Args:
        project_root: Project root directory

    Returns:
        Dict with keys:
        {
            "has_venv": bool,
            "venv_active": bool,
            "has_requirements_txt": bool,
            "has_pyproject_toml": bool,
            "warnings": List[str],
            "proposals": List[Dict],
        }

    Safety Rule:
        If dependency files exist but venv is not active, fail fast with warning.
    """
    result = {
        "has_venv": False,
        "venv_active": False,
        "has_requirements_txt": False,
        "has_pyproject_toml": False,
        "warnings": [],
        "proposals": [],
    }

    # Check for venv directory
    venv_paths = [
        project_root / ".venv",
        project_root / "venv",
        project_root / "env",
    ]
    result["has_venv"] = any(p.exists() and p.is_dir() for p in venv_paths)

    # Check if venv is active (compare sys.prefix and sys.base_prefix)
    result["venv_active"] = sys.prefix != sys.base_prefix

    # Check for Python dependency files
    result["has_requirements_txt"] = (project_root / "requirements.txt").exists()
    result["has_pyproject_toml"] = (project_root / "pyproject.toml").exists()

    # ========================================================================
    # FAIL FAST: Python deps without active venv
    # ========================================================================

    has_python_deps = result["has_requirements_txt"] or result["has_pyproject_toml"]

    if has_python_deps and not result["venv_active"]:
        result["warnings"].append(
            "Python dependency files detected but no virtual environment is active. "
            "Activate venv first to prevent system-wide installs."
        )
        logger.warning("Python deps detected without active venv - skipping install proposal")
        return result

    # ========================================================================
    # SAFE TO INSTALL: Propose install commands
    # ========================================================================

    if result["has_requirements_txt"] and result["venv_active"]:
        result["proposals"].append({
            "tool": "run_terminal_cmd",
            "command": "pip install -r requirements.txt",
            "rationale": "Install Python dependencies from requirements.txt",
        })

    if result["has_pyproject_toml"] and result["venv_active"]:
        result["proposals"].append({
            "tool": "run_terminal_cmd",
            "command": "pip install -e .",
            "rationale": "Install Python project in editable mode from pyproject.toml",
        })

    return result


# ============================================================================
# NODE DETECTION
# ============================================================================

def detect_node_tooling(project_root: Path) -> Dict[str, Any]:
    """
    Detect Node.js project tooling.

    Args:
        project_root: Project root directory

    Returns:
        Dict with keys:
        {
            "has_package_json": bool,
            "has_package_lock": bool,
            "has_yarn_lock": bool,
            "warnings": List[str],
            "proposals": List[Dict],
        }
    """
    result = {
        "has_package_json": False,
        "has_package_lock": False,
        "has_yarn_lock": False,
        "warnings": [],
        "proposals": [],
    }

    # Check for Node.js files
    result["has_package_json"] = (project_root / "package.json").exists()
    result["has_package_lock"] = (project_root / "package-lock.json").exists()
    result["has_yarn_lock"] = (project_root / "yarn.lock").exists()

    # ========================================================================
    # PROPOSE INSTALL COMMANDS
    # ========================================================================

    if result["has_package_json"]:
        if result["has_yarn_lock"]:
            # Yarn project
            result["proposals"].append({
                "tool": "run_terminal_cmd",
                "command": "yarn install",
                "rationale": "Install Node.js dependencies using Yarn",
            })
        else:
            # NPM project (default or package-lock.json)
            result["proposals"].append({
                "tool": "run_terminal_cmd",
                "command": "npm install",
                "rationale": "Install Node.js dependencies using NPM",
            })

    return result


# ============================================================================
# JAVA DETECTION
# ============================================================================

def detect_java_tooling(project_root: Path) -> Dict[str, Any]:
    """
    Detect Java project tooling.

    Args:
        project_root: Project root directory

    Returns:
        Dict with keys:
        {
            "has_maven": bool,
            "has_gradle": bool,
            "warnings": List[str],
            "proposals": List[Dict],
        }

    Note:
        Currently detection-only. Future phases can add build proposals.
    """
    result = {
        "has_maven": False,
        "has_gradle": False,
        "warnings": [],
        "proposals": [],
    }

    # Check for Java build files
    result["has_maven"] = (project_root / "pom.xml").exists()
    result["has_gradle"] = (
        (project_root / "build.gradle").exists()
        or (project_root / "build.gradle.kts").exists()
    )

    # ========================================================================
    # FUTURE: Propose build commands (Phase 6+)
    # ========================================================================

    # For now, just detect - no install proposals
    # Future: Add Maven/Gradle dependency install commands

    return result


# ============================================================================
# MAIN DEPENDENCY MANAGER
# ============================================================================

def dependency_manager(project_root: Path) -> Dict[str, Any]:
    """
    Detect all project tooling and propose safe install commands.

    Args:
        project_root: Project root directory

    Returns:
        Dict with keys:
        {
            "detected": {"python": bool, "node": bool, "java": bool},
            "safe_to_install": bool,
            "warnings": List[str],
            "proposals": List[
                {"tool": "run_terminal_cmd", "command": str, "rationale": str}
            ]
        }

    Safety:
        - Fail fast if Python deps exist without active venv
        - All proposals routed to run_terminal_cmd (human approval required)

    Example:
        >>> result = dependency_manager(Path("/workspace"))
        >>> result["detected"]
        {'python': True, 'node': False, 'java': False}
        >>> result["safe_to_install"]
        True
        >>> result["proposals"]
        [{'tool': 'run_terminal_cmd', 'command': 'pip install -r requirements.txt', ...}]
    """
    project_root = Path(project_root).resolve()
    logger.info(f"Running dependency detection for: {project_root}")

    # ========================================================================
    # DETECT ALL TOOLING
    # ========================================================================

    python_result = detect_python_tooling(project_root)
    node_result = detect_node_tooling(project_root)
    java_result = detect_java_tooling(project_root)

    # ========================================================================
    # AGGREGATE RESULTS
    # ========================================================================

    detected = {
        "python": (
            python_result["has_requirements_txt"]
            or python_result["has_pyproject_toml"]
        ),
        "node": node_result["has_package_json"],
        "java": java_result["has_maven"] or java_result["has_gradle"],
    }

    warnings = (
        python_result["warnings"]
        + node_result["warnings"]
        + java_result["warnings"]
    )

    proposals = (
        python_result["proposals"]
        + node_result["proposals"]
        + java_result["proposals"]
    )

    # Safe to install if there are proposals (no critical warnings)
    safe_to_install = len(proposals) > 0 and len(warnings) == 0

    result = {
        "detected": detected,
        "safe_to_install": safe_to_install,
        "warnings": warnings,
        "proposals": proposals,
    }

    logger.info(
        f"Dependency detection complete: detected={detected}, "
        f"safe_to_install={safe_to_install}, "
        f"proposals={len(proposals)}, warnings={len(warnings)}"
    )

    return result


__all__ = [
    "dependency_manager",
    "detect_python_tooling",
    "detect_node_tooling",
    "detect_java_tooling",
]
