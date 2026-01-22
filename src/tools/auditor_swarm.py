"""
Tier 3 Tool: AutoGen Auditor (diagnose_project).

Performs project health diagnostics via:
- Stage A: Deterministic checks (always runs, fast)
- Stage B: Optional AutoGen debate (bounded, gated by toggle)

Output: Strict JSON with risk_level, findings, prioritized_fixes, verification_steps.

Context Containment:
- AutoGen debate transcripts are NEVER returned to Master
- Only final JSON output is returned

UI Responsiveness:
- Blocking AutoGen execution is offloaded via asyncio.to_thread

Multi-Provider Support:
- Supports OpenAI, Anthropic Claude, and Google Gemini models
- Provider is auto-detected from model name
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# AutoGen imports - PERMANENT FIX: Prioritize pyautogen 0.2.x (pinned version)
# We pin to pyautogen==0.2.35 in requirements.txt for stable GroupChat API
AUTOGEN_AVAILABLE = False
AUTOGEN_PACKAGE_INFO = "not_installed"
_import_errors = []

# Strategy 1 (PREFERRED): pyautogen direct (pyautogen 0.2.x - our pinned version)
try:
    from pyautogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    AUTOGEN_AVAILABLE = True
    AUTOGEN_PACKAGE_INFO = "pyautogen==0.2.x"
    logging.getLogger(__name__).info("AutoGen loaded via 'pyautogen' (0.2.x - pinned)")
except ImportError as e1:
    _import_errors.append(f"pyautogen: {e1}")

    # Strategy 2: pyautogen.agentchat (alternative import path for some 0.2.x versions)
    try:
        from pyautogen.agentchat import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
        AUTOGEN_AVAILABLE = True
        AUTOGEN_PACKAGE_INFO = "pyautogen.agentchat"
        logging.getLogger(__name__).info("AutoGen loaded via 'pyautogen.agentchat'")
    except ImportError as e2:
        _import_errors.append(f"pyautogen.agentchat: {e2}")

        # Strategy 3: autogen direct (Microsoft autogen package - fallback)
        try:
            from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
            AUTOGEN_AVAILABLE = True
            AUTOGEN_PACKAGE_INFO = "autogen"
            logging.getLogger(__name__).info("AutoGen loaded via 'autogen'")
        except ImportError as e3:
            _import_errors.append(f"autogen: {e3}")
            logging.getLogger(__name__).warning(
                f"AutoGen not available. Tried imports:\n  " + "\n  ".join(_import_errors) +
                f"\n\nFix: pip uninstall autogen autogen-agentchat pyautogen -y && pip install pyautogen==0.2.35"
            )

from src.core.settings import get_settings_manager
from src.core.prompts import AUTOGEN_AUDITOR_PROMPT

logger = logging.getLogger(__name__)


# ============================================================================
# MULTI-PROVIDER LLM CONFIG FACTORY
# ============================================================================

def _get_provider(model: str) -> str:
    """
    Determine LLM provider from model name.
    
    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4.5", "gemini-3-pro")
    
    Returns:
        Provider name: "openai", "anthropic", or "google"
    """
    model_lower = model.lower()
    
    if model_lower.startswith("gpt") or model_lower.startswith("o1") or model_lower.startswith("o3"):
        return "openai"
    elif model_lower.startswith("claude"):
        return "anthropic"
    elif model_lower.startswith("gemini"):
        return "google"
    else:
        # Default to OpenAI for unknown models
        logger.warning(f"Unknown model '{model}', defaulting to OpenAI provider")
        return "openai"


def _create_llm_config(model: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create AutoGen-compatible LLM config for the specified model.
    
    AutoGen uses a config_list format for multi-provider support.
    
    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4.5", "gemini-3-pro")
        settings: Settings dict containing API keys
    
    Returns:
        AutoGen LLM config dict, or None if initialization fails
    """
    provider = _get_provider(model)
    api_keys = settings.get("api_keys", {})

    try:
        if provider == "openai":
            api_key = api_keys.get("openai", "")
            if not api_key:
                logger.error("OpenAI API key not configured in Settings → API Keys")
                return None

            logger.info(f"Creating OpenAI LLM config for AutoGen: {model}")
            return {
                "config_list": [{
                    "model": model,
                    "api_key": api_key,
                }],
                "temperature": 0.4,
            }

        elif provider == "anthropic":
            api_key = api_keys.get("anthropic", "")
            if not api_key:
                logger.error("Anthropic API key not configured in Settings → API Keys")
                return None

            logger.info(f"Creating Anthropic LLM config for AutoGen: {model}")
            return {
                "config_list": [{
                    "model": model,
                    "api_key": api_key,
                    "api_type": "anthropic",
                }],
                "temperature": 0.4,
            }

        elif provider == "google":
            api_key = api_keys.get("google", "")
            if not api_key:
                logger.error("Google API key not configured in Settings → API Keys")
                return None

            logger.info(f"Creating Google LLM config for AutoGen: {model}")
            return {
                "config_list": [{
                    "model": model,
                    "api_key": api_key,
                    "api_type": "google",
                }],
                "temperature": 0.4,
            }
        
        else:
            logger.error(f"Unknown provider: {provider}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create LLM config for {model}: {e}", exc_info=True)
        return None


# ============================================================================
# BUDGET CONTROLS
# ============================================================================

# Safe defaults for bounded execution
MAX_AUTOGEN_ROUNDS = 5  # Maximum rounds for AutoGen debate
MAX_TOKENS_PER_MESSAGE = 2000  # Token limit per agent message


# ============================================================================
# ASYNC WRAPPER (UI Responsiveness)
# ============================================================================

async def diagnose_project(
    focus_area: Optional[str] = None,
    project_root: Optional[Path] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Diagnose project health via deterministic checks + optional AutoGen debate.

    This is the main entry point called by the Master Agent.
    Offloads blocking AutoGen work to a background thread.

    Args:
        focus_area: Optional focus area (e.g., "safety logic", "file structure").
        project_root: Project root directory (for file scanning).
        context: Optional context dict (workspace_summary, active_files, etc.).

    Returns:
        Dict with keys (strict JSON format):
            - risk_level: str ("HIGH" | "MEDIUM" | "LOW")
            - findings: List[Dict] (severity, file, line, message)
            - prioritized_fixes: List[Dict] (priority, action, rationale)
            - verification_steps: List[str]
            - metadata: Dict (autogen enabled, rounds, budget mode)

    Example:
        >>> result = await diagnose_project(
        ...     focus_area="safety logic",
        ...     project_root=Path("/workspace")
        ... )
        >>> result["risk_level"]
        "MEDIUM"
        >>> len(result["findings"])
        3
    """
    logger.info(f"diagnose_project called: focus_area={focus_area}")

    # Load settings
    settings_manager = get_settings_manager()
    settings = settings_manager.load_settings()

    # Always run Stage A (deterministic checks)
    logger.info("Running Stage A: Deterministic checks")
    stage_a_result = _run_deterministic_checks(project_root, context or {}, focus_area)

    # Toggle gate: If AutoGen disabled, return Stage A only
    enable_autogen = settings.get("preferences", {}).get("enable_autogen", True)
    if not enable_autogen:
        logger.info("AutoGen disabled by toggle, returning Stage A results only")
        stage_a_result["metadata"]["autogen_enabled"] = False
        stage_a_result["metadata"]["budget_mode"] = "disabled"
        return stage_a_result

    # Offload Stage B (AutoGen debate) to background thread
    logger.info("Offloading AutoGen debate (Stage B) to background thread")
    result = await asyncio.to_thread(
        _run_autogen_sync,
        stage_a_result=stage_a_result,
        project_root=project_root,
        context=context or {},
        settings=settings,
        focus_area=focus_area
    )

    logger.info(f"Diagnosis complete: risk_level={result['risk_level']}, findings={len(result['findings'])}")
    return result


# ============================================================================
# STAGE A: DETERMINISTIC CHECKS (always runs)
# ============================================================================

def _run_deterministic_checks(
    project_root: Optional[Path],
    context: Dict[str, Any],
    focus_area: Optional[str]
) -> Dict[str, Any]:
    """
    Run fast deterministic checks on project structure and code.

    Args:
        project_root: Project root directory.
        context: Workspace context dict.
        focus_area: Optional focus area.

    Returns:
        Dict with risk_level, findings, prioritized_fixes, verification_steps, metadata.
    """
    logger.info("Running deterministic checks...")

    findings = []
    prioritized_fixes = []

    # Check 1: Workspace exists and is not empty
    if not project_root or not project_root.exists():
        findings.append({
            "severity": "ERROR",
            "file": "N/A",
            "line": 0,
            "message": "Project root directory does not exist or is inaccessible"
        })
        prioritized_fixes.append({
            "priority": 1,
            "action": "Open a valid workspace directory",
            "rationale": "Cannot perform diagnostics without a valid project root"
        })

        return {
            "risk_level": "HIGH",
            "findings": findings,
            "prioritized_fixes": prioritized_fixes,
            "verification_steps": ["Open a valid workspace directory and re-run diagnostics"],
            "metadata": {
                "autogen_enabled": False,
                "stage": "A_only",
                "deterministic_checks": True
            }
        }

    # Check 2: Look for common source file extensions
    # Support multiple languages: PLC (.st, .scl), Python (.py), JavaScript/TypeScript (.js, .ts, .tsx), etc.
    source_extensions = [
        "**/*.st", "**/*.scl",  # PLC/IEC 61131-3
        "**/*.py",              # Python
        "**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx",  # JavaScript/TypeScript
        "**/*.java",            # Java
        "**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp",    # C/C++
        "**/*.go",              # Go
        "**/*.rs",              # Rust
        "**/*.rb",              # Ruby
        "**/*.php",             # PHP
        "**/*.cs",              # C#
    ]

    source_files = []
    for ext in source_extensions:
        source_files.extend(project_root.glob(ext))

    # Deduplicate and exclude common non-source directories
    source_files = [
        f for f in source_files
        if not any(excluded in f.parts for excluded in [
            'node_modules', '__pycache__', '.git', 'venv', '.venv',
            'dist', 'build', '.next', 'target', 'bin', 'obj'
        ])
    ]

    if not source_files:
        findings.append({
            "severity": "WARNING",
            "file": "N/A",
            "line": 0,
            "message": "No source files found in workspace"
        })

    logger.info(f"Found {len(source_files)} source files for analysis")

    # Check 3: Basic syntax validation (look for common patterns)
    for source_file in source_files[:20]:  # Limit to first 20 files for performance
        try:
            content = source_file.read_text(encoding="utf-8", errors="ignore")
            file_ext = source_file.suffix.lower()

            # PLC-specific checks (.st, .scl)
            if file_ext in ['.st', '.scl']:
                var_count = content.count("VAR")
                end_var_count = content.count("END_VAR")
                if var_count != end_var_count:
                    findings.append({
                        "severity": "ERROR",
                        "file": str(source_file.relative_to(project_root)),
                        "line": 0,
                        "message": f"Unbalanced VAR blocks ({var_count} VAR, {end_var_count} END_VAR)"
                    })
                    prioritized_fixes.append({
                        "priority": 2,
                        "action": f"Fix VAR/END_VAR balance in {source_file.name}",
                        "rationale": "Unbalanced variable blocks will cause compilation errors"
                    })

            # Python-specific checks (.py)
            elif file_ext == '.py':
                # Check for common security issues
                if 'eval(' in content or 'exec(' in content:
                    findings.append({
                        "severity": "WARNING",
                        "file": str(source_file.relative_to(project_root)),
                        "line": 0,
                        "message": "Uses eval() or exec() - potential code injection risk"
                    })
                if 'subprocess.shell=True' in content or 'shell=True' in content:
                    findings.append({
                        "severity": "WARNING",
                        "file": str(source_file.relative_to(project_root)),
                        "line": 0,
                        "message": "Uses shell=True in subprocess - potential command injection risk"
                    })

            # JavaScript/TypeScript checks
            elif file_ext in ['.js', '.ts', '.tsx', '.jsx']:
                if 'eval(' in content:
                    findings.append({
                        "severity": "WARNING",
                        "file": str(source_file.relative_to(project_root)),
                        "line": 0,
                        "message": "Uses eval() - potential code injection risk"
                    })
                if 'innerHTML' in content and 'dangerouslySetInnerHTML' not in content:
                    findings.append({
                        "severity": "INFO",
                        "file": str(source_file.relative_to(project_root)),
                        "line": 0,
                        "message": "Uses innerHTML - verify input is sanitized to prevent XSS"
                    })

        except Exception as e:
            logger.warning(f"Failed to read {source_file}: {e}")
            findings.append({
                "severity": "WARNING",
                "file": str(source_file.relative_to(project_root)),
                "line": 0,
                "message": f"Failed to read file: {str(e)}"
            })

    # Determine risk level based on findings
    error_count = sum(1 for f in findings if f["severity"] == "ERROR")
    warning_count = sum(1 for f in findings if f["severity"] == "WARNING")

    if error_count > 0:
        risk_level = "HIGH"
    elif warning_count > 2:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Build verification steps
    verification_steps = [
        "Review all ERROR-level findings and fix critical issues",
        "Address WARNING-level findings to improve code quality",
        "Re-run diagnostics after fixes to verify improvements"
    ]

    if not findings:
        verification_steps = ["No issues found. Project structure looks good!"]

    return {
        "risk_level": risk_level,
        "findings": findings,
        "prioritized_fixes": prioritized_fixes,
        "verification_steps": verification_steps,
        "metadata": {
            "autogen_enabled": False,
            "stage": "A_only",
            "deterministic_checks": True,
            "files_scanned": len(source_files)
        }
    }


# ============================================================================
# STAGE B: AUTOGEN DEBATE (runs in thread pool, optional)
# ============================================================================

def _run_autogen_sync(
    stage_a_result: Dict[str, Any],
    project_root: Optional[Path],
    context: Dict[str, Any],
    settings: Dict[str, Any],
    focus_area: Optional[str]
) -> Dict[str, Any]:
    """
    Synchronous AutoGen debate execution (runs in background thread).

    Roles:
    - Auditor: Reviews Stage A findings and proposes additional checks
    - Hacker: Looks for security vulnerabilities and edge cases
    - Defender: Proposes fixes and mitigation strategies
    - Moderator: Synthesizes debate into final JSON output

    Args:
        stage_a_result: Results from deterministic Stage A.
        project_root: Project root directory.
        context: Workspace context dict.
        settings: User settings snapshot.
        focus_area: Optional focus area for debate.

    Returns:
        Dict with risk_level, findings, prioritized_fixes, verification_steps, metadata.
    """
    logger.info("Starting AutoGen debate (Stage B)")

    try:
        # Check if AutoGen is available
        if not AUTOGEN_AVAILABLE:
            logger.error(
                f"AutoGen not available (package_info={AUTOGEN_PACKAGE_INFO}). "
                f"Install with: pip install pyautogen"
            )
            stage_a_result["metadata"]["autogen_enabled"] = False
            stage_a_result["metadata"]["error"] = "autogen_not_installed"
            stage_a_result["metadata"]["autogen_package_info"] = AUTOGEN_PACKAGE_INFO
            return stage_a_result

        logger.info(f"AutoGen available via '{AUTOGEN_PACKAGE_INFO}' package")
        
        # Extract model settings
        model_name = settings.get("models", {}).get("autogen_auditor", "gpt-4o-mini")
        
        # Create provider-agnostic LLM config
        llm_config = _create_llm_config(model_name, settings)
        
        if llm_config is None:
            logger.error("Failed to create LLM config, falling back to Stage A only")
            stage_a_result["metadata"]["autogen_enabled"] = False
            stage_a_result["metadata"]["error"] = "llm_config_failed"
            return stage_a_result

        # Create agents
        auditor = AssistantAgent(
            name="Auditor",
            system_message=AUTOGEN_AUDITOR_PROMPT + "\n\nYou are the Auditor. Review the deterministic findings and propose additional checks.",
            llm_config=llm_config
        )

        hacker = AssistantAgent(
            name="Hacker",
            system_message="You are the Hacker. Find security vulnerabilities, edge cases, and subtle bugs that deterministic checks might miss.",
            llm_config=llm_config
        )

        defender = AssistantAgent(
            name="Defender",
            system_message="You are the Defender. Propose fixes and mitigation strategies for identified issues. Prioritize by severity and impact.",
            llm_config=llm_config
        )

        moderator = UserProxyAgent(
            name="Moderator",
            system_message="""You are the Moderator. Synthesize the debate into a final JSON output.

REQUIRED OUTPUT FORMAT (strict JSON):
{
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "findings": [
    {"severity": "ERROR" | "WARNING" | "INFO", "file": "path/to/file", "line": 42, "message": "Description"}
  ],
  "prioritized_fixes": [
    {"priority": 1, "action": "What to do", "rationale": "Why it matters"}
  ],
  "verification_steps": ["1. Step one", "2. Step two"]
}

Do NOT include any text outside the JSON block. Output ONLY valid JSON.""",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False
        )

        # Create group chat
        groupchat = GroupChat(
            agents=[auditor, hacker, defender, moderator],
            messages=[],
            max_round=MAX_AUTOGEN_ROUNDS
        )

        manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

        # Build initial message with Stage A results
        initial_message = f"""Project Diagnosis Debate:

FOCUS AREA: {focus_area or "General project health"}

STAGE A (Deterministic) RESULTS:
Risk Level: {stage_a_result['risk_level']}
Findings: {len(stage_a_result['findings'])} issues found

DETAILS:
{json.dumps(stage_a_result, indent=2)}

INSTRUCTIONS:
1. Auditor: Review these findings and propose additional checks
2. Hacker: Look for security vulnerabilities and edge cases
3. Defender: Propose fixes for all identified issues
4. Moderator: Synthesize into final JSON (use the required format above)

Begin the debate. Moderator will produce final JSON after {MAX_AUTOGEN_ROUNDS} rounds.
"""

        # Execute group chat (blocking)
        logger.info(f"Executing AutoGen group chat (max {MAX_AUTOGEN_ROUNDS} rounds)")
        moderator.initiate_chat(
            manager,
            message=initial_message
        )

        # Extract final JSON from chat history
        final_json = _extract_json_from_chat(groupchat.messages)

        if final_json:
            # Merge with Stage A results (AutoGen findings supplement deterministic findings)
            final_json["metadata"] = {
                "autogen_enabled": True,
                "stage": "A_and_B",
                "budget_mode": "bounded",
                "max_rounds": MAX_AUTOGEN_ROUNDS,
                "rounds_used": len(groupchat.messages),
                "deterministic_checks": True
            }
            logger.info(f"AutoGen debate complete: {final_json['risk_level']}")
            return final_json
        else:
            logger.warning("Failed to extract JSON from AutoGen debate, falling back to Stage A")
            stage_a_result["metadata"]["autogen_enabled"] = True
            stage_a_result["metadata"]["error"] = "json_extraction_failed"
            return stage_a_result

    except Exception as e:
        logger.error(f"AutoGen debate failed: {e}", exc_info=True)
        stage_a_result["metadata"]["autogen_enabled"] = True
        stage_a_result["metadata"]["error"] = str(e)
        return stage_a_result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _extract_json_from_chat(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Extract final JSON output from AutoGen chat messages.

    Looks for the last message containing valid JSON with required keys.

    Args:
        messages: List of chat messages from GroupChat.

    Returns:
        Parsed JSON dict or None if extraction failed.
    """
    required_keys = {"risk_level", "findings", "prioritized_fixes", "verification_steps"}

    # Search messages in reverse order (last message is most likely to have final JSON)
    for message in reversed(messages):
        content = message.get("content", "")

        # Try to extract JSON block
        import re
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))

                # Validate required keys
                if required_keys.issubset(parsed.keys()):
                    logger.info("Successfully extracted JSON from AutoGen debate")
                    return parsed

            except json.JSONDecodeError:
                continue

    logger.warning("Could not extract valid JSON from AutoGen chat")
    return None


__all__ = ["diagnose_project"]
