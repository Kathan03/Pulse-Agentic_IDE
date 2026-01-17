"""
Tier 3 Tool: CrewAI Builder (implement_feature).

Implements complex features via CrewAI mini-crew:
- Planner: Analyze request and generate implementation plan
- Coder: Write code based on plan
- Reviewer: Review code for quality and safety

Context Containment:
- Crew transcripts are NEVER returned to Master
- Only structured outputs (PatchPlan, summary, verification) are returned

UI Responsiveness:
- Blocking CrewAI execution is offloaded via asyncio.to_thread

Multi-Provider Support:
- Supports OpenAI, Anthropic Claude, and Google Gemini models
- Provider is auto-detected from model name
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from crewai import Agent, Task, Crew, Process

# LangChain LLM imports - lazy loaded to avoid import errors if not installed
try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_OPENAI_AVAILABLE = False

try:
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_ANTHROPIC_AVAILABLE = True
except ImportError:
    LANGCHAIN_ANTHROPIC_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_GOOGLE_AVAILABLE = True
except ImportError:
    LANGCHAIN_GOOGLE_AVAILABLE = False

from src.core.settings import get_settings_manager
from src.core.prompts import CREW_PLANNER_PROMPT, CREW_CODER_PROMPT, CREW_REVIEWER_PROMPT
from src.agents.state import PatchPlan

logger = logging.getLogger(__name__)


# ============================================================================
# MULTI-PROVIDER LLM FACTORY
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


def _create_llm(model: str, settings: Dict[str, Any]) -> Optional[Any]:
    """
    Create a LangChain LLM instance for the specified model.
    
    Automatically selects the correct provider (OpenAI, Anthropic, Google)
    based on the model name and configures it with the appropriate API key.
    
    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4.5", "gemini-3-pro")
        settings: Settings dict containing API keys
    
    Returns:
        LangChain LLM instance, or None if initialization fails
    """
    provider = _get_provider(model)
    api_keys = settings.get("api_keys", {})
    
    # Check for DEV_MODE (use .env instead of settings)
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
    try:
        if provider == "openai":
            if not LANGCHAIN_OPENAI_AVAILABLE:
                logger.error("langchain_openai not installed. Run: pip install langchain-openai")
                return None
            
            api_key = os.getenv("OPENAI_API_KEY") if dev_mode else api_keys.get("openai", "")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY", "")  # Fallback to env
            
            if not api_key:
                logger.error("OpenAI API key not configured")
                return None
            
            logger.info(f"Creating OpenAI LLM: {model}")
            # Note: Don't pass max_tokens - let the model use its defaults
            # Different OpenAI models have different parameter requirements
            return ChatOpenAI(model=model, api_key=api_key)
        
        elif provider == "anthropic":
            if not LANGCHAIN_ANTHROPIC_AVAILABLE:
                logger.error("langchain_anthropic not installed. Run: pip install langchain-anthropic")
                return None
            
            api_key = os.getenv("ANTHROPIC_API_KEY") if dev_mode else api_keys.get("anthropic", "")
            if not api_key:
                api_key = os.getenv("ANTHROPIC_API_KEY", "")  # Fallback to env
            
            if not api_key:
                logger.error("Anthropic API key not configured")
                return None
            
            logger.info(f"Creating Anthropic LLM: {model}")
            return ChatAnthropic(model=model, api_key=api_key)
        
        elif provider == "google":
            if not LANGCHAIN_GOOGLE_AVAILABLE:
                logger.error("langchain_google_genai not installed. Run: pip install langchain-google-genai")
                return None
            
            api_key = os.getenv("GOOGLE_API_KEY") if dev_mode else api_keys.get("google", "")
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY", "")  # Fallback to env
            
            if not api_key:
                logger.error("Google API key not configured")
                return None
            
            logger.info(f"Creating Google Gemini LLM: {model}")
            return ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
        
        else:
            logger.error(f"Unknown provider: {provider}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create LLM for {model}: {e}", exc_info=True)
        return None


# ============================================================================
# BUDGET CONTROLS
# ============================================================================

# Safe defaults for bounded execution
MAX_CREW_ITERATIONS = 3  # Maximum rounds for crew execution
MAX_TOKENS_PER_AGENT = 4000  # Token limit per agent response (not currently used)


# ============================================================================
# ASYNC WRAPPER (UI Responsiveness)
# ============================================================================

async def implement_feature(
    request: str,
    project_root: Path,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Implement a complex feature via CrewAI (Planner → Coder → Reviewer).

    This is the main entry point called by the Master Agent.
    Offloads blocking CrewAI work to a background thread.

    Args:
        request: User's feature request.
        project_root: Project root directory (for file operations).
        context: Optional context dict (workspace_summary, active_files, etc.).

    Returns:
        Dict with keys:
            - patch_plans: List[Dict] (PatchPlan-compatible dicts)
            - summary: str (concise feature summary)
            - verification_steps: List[str]
            - metadata: Dict (model used, toggle enabled, budget mode)

    Example:
        >>> result = await implement_feature(
        ...     request="Add 5-second delay timer to conveyor start",
        ...     project_root=Path("/workspace")
        ... )
        >>> result["patch_plans"]
        [{"file_path": "conveyor.st", "diff": "...", "rationale": "...", "action": "modify"}]
    """
    logger.info(f"implement_feature called: {request[:50]}...")

    # Load settings
    settings_manager = get_settings_manager()
    settings = settings_manager.load_settings()

    # Toggle gate: If CrewAI disabled, return immediately
    enable_crew = settings.get("preferences", {}).get("enable_crew", True)
    if not enable_crew:
        logger.info("CrewAI disabled by toggle, returning no-op response")
        return {
            "patch_plans": [],
            "summary": "CrewAI builder is disabled in settings. Enable it to use autonomous feature implementation.",
            "verification_steps": [],
            "metadata": {
                "crew_enabled": False,
                "budget_mode": "disabled"
            }
        }

    # Offload to background thread to prevent UI freeze
    logger.info("Offloading CrewAI execution to background thread")
    result = await asyncio.to_thread(
        _run_crew_sync,
        request=request,
        project_root=project_root,
        context=context or {},
        settings=settings
    )

    logger.info(f"CrewAI execution complete: {len(result['patch_plans'])} patches generated")
    return result


# ============================================================================
# SYNC CREW EXECUTION (runs in thread pool)
# ============================================================================

def _run_crew_sync(
    request: str,
    project_root: Path,
    context: Dict[str, Any],
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Synchronous CrewAI execution (runs in background thread).

    Args:
        request: User's feature request.
        project_root: Project root directory.
        context: Workspace context dict.
        settings: User settings snapshot.

    Returns:
        Dict with patch_plans, summary, verification_steps, metadata.
    """
    logger.info("Starting synchronous CrewAI execution")

    try:
        # Extract model settings
        cheap_model = settings.get("models", {}).get("autogen_auditor", "gpt-4o-mini")
        master_model = settings.get("models", {}).get("crew_coder", "gpt-4o")
        
        # Initialize LLMs using provider-agnostic factory
        # This supports OpenAI, Anthropic Claude, and Google Gemini models
        cheap_llm = _create_llm(cheap_model, settings)
        master_llm = _create_llm(master_model, settings)
        
        if cheap_llm is None or master_llm is None:
            return {
                "patch_plans": [],
                "summary": "Error: Failed to initialize LLM. Check API key configuration in settings.",
                "verification_steps": [],
                "metadata": {"error": "llm_init_failed"}
            }

        # Build context string for agents
        context_str = _build_context_string(project_root, context)

        # Create agents
        planner = Agent(
            role="Software Planning Agent",
            goal="Analyze user requirements and generate a clear implementation plan",
            backstory=CREW_PLANNER_PROMPT,
            llm=cheap_llm,
            verbose=True,
            allow_delegation=False
        )

        coder = Agent(
            role="PLC Code Generation Agent",
            goal="Implement the plan step-by-step with production-quality code",
            backstory=CREW_CODER_PROMPT,
            llm=master_llm,
            verbose=True,
            allow_delegation=False
        )

        reviewer = Agent(
            role="Code Review Agent",
            goal="Review generated code for quality, safety, and best practices",
            backstory=CREW_REVIEWER_PROMPT,
            llm=master_llm,
            verbose=True,
            allow_delegation=False
        )

        # Create tasks
        plan_task = Task(
            description=f"""Analyze this feature request and generate an implementation plan:

REQUEST: {request}

WORKSPACE CONTEXT:
{context_str}

Generate a structured plan with:
1. Goal (one-sentence summary)
2. Files Affected (list of files to create/modify)
3. Implementation Steps (3-7 steps max)
4. Verification (how to test)
5. Dependencies (any external requirements)
""",
            agent=planner,
            expected_output="Structured implementation plan with goal, files, steps, verification, and dependencies"
        )

        code_task = Task(
            description=f"""Implement the plan step-by-step.

For each file that needs changes, generate a unified diff patch in this exact format:

```diff
--- a/path/to/file.st
+++ b/path/to/file.st
@@ -line,count +line,count @@
-old content
+new content
```

IMPORTANT:
- Use valid IEC 61131-3 Structured Text syntax
- Include clear variable names and comments
- Consider edge cases (startup, shutdown, faults)
- Implement safety interlocks where applicable
""",
            agent=coder,
            expected_output="Unified diff patches for all affected files with clear rationale",
            context=[plan_task]
        )

        review_task = Task(
            description="""Review the generated code for:
1. Correctness (matches plan?)
2. Safety (interlocks, fault handling?)
3. Syntax (valid IEC 61131-3?)
4. Clarity (names, comments?)
5. Edge cases (startup, shutdown, errors?)

Output format:
- Approval: YES/NO
- Issues Found: [list]
- Suggestions: [list]
- Risk Level: LOW/MEDIUM/HIGH
""",
            agent=reviewer,
            expected_output="Code review with approval status, issues, suggestions, and risk level",
            context=[code_task]
        )

        # Create crew with budget controls
        crew = Crew(
            agents=[planner, coder, reviewer],
            tasks=[plan_task, code_task, review_task],
            process=Process.sequential,
            verbose=True,
            max_rpm=10,  # Rate limit to 10 requests per minute
        )

        # Execute crew (blocking)
        logger.info("Executing CrewAI crew...")
        crew_result = crew.kickoff()

        # Parse crew output into structured format
        parsed_result = _parse_crew_output(crew_result, request)

        logger.info(f"CrewAI execution successful: {parsed_result['summary']}")
        return parsed_result

    except Exception as e:
        logger.error(f"CrewAI execution failed: {e}", exc_info=True)
        return {
            "patch_plans": [],
            "summary": f"Error during feature implementation: {str(e)}",
            "verification_steps": [],
            "metadata": {
                "error": str(e),
                "crew_enabled": True
            }
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_context_string(project_root: Path, context: Dict[str, Any]) -> str:
    """
    Build context string from workspace context dict.

    Args:
        project_root: Project root directory.
        context: Context dict with workspace_summary, active_files, etc.
                 May also be a string if LLM passes raw context.

    Returns:
        Formatted context string for agent prompts.
    """
    parts = [f"Project Root: {project_root}"]

    # Handle case where context is passed as a string instead of dict
    if isinstance(context, str):
        # LLM might pass a raw string as context - just append it
        if context.strip():
            parts.append(f"\nContext:\n{context}")
        return "\n".join(parts)
    
    # Handle None case
    if not context:
        return "\n".join(parts)

    if workspace_summary := context.get("workspace_summary"):
        parts.append(f"\nWorkspace Summary:\n{workspace_summary}")

    if active_files := context.get("active_files"):
        parts.append(f"\nActive Files:\n" + "\n".join(f"- {f}" for f in active_files))

    if recent_changes := context.get("recent_changes"):
        parts.append(f"\nRecent Changes:\n" + "\n".join(f"- {c}" for c in recent_changes))

    return "\n".join(parts)


def _parse_crew_output(crew_result: Any, request: str) -> Dict[str, Any]:
    """
    Parse CrewAI output into structured format.

    Extracts unified diffs from the coder's output and builds PatchPlan dicts.

    Args:
        crew_result: Raw CrewAI result object.
        request: Original user request (for summary).

    Returns:
        Dict with patch_plans, summary, verification_steps, metadata.
    """
    # Extract result text
    if hasattr(crew_result, 'raw'):
        result_text = str(crew_result.raw)
    else:
        result_text = str(crew_result)

    logger.debug(f"Parsing crew result: {result_text[:200]}...")

    # Parse diff blocks (simple regex-based extraction)
    patch_plans = _extract_patches_from_text(result_text)

    # Extract verification steps (look for numbered list after "Verification:" or "Test:")
    verification_steps = _extract_verification_steps(result_text)

    # Build summary
    summary = f"Implemented feature: {request[:80]}... ({len(patch_plans)} files affected)"

    return {
        "patch_plans": patch_plans,
        "summary": summary,
        "verification_steps": verification_steps,
        "metadata": {
            "crew_enabled": True,
            "budget_mode": "bounded",
            "max_iterations": MAX_CREW_ITERATIONS,
            "patches_generated": len(patch_plans)
        }
    }


def _extract_patches_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract unified diff patches from crew output text.

    Args:
        text: Raw crew output text.

    Returns:
        List of PatchPlan-compatible dicts.
    """
    import re

    patches = []

    # Find all diff blocks (```diff ... ```)
    diff_pattern = r"```diff\s*\n(.*?)```"
    diff_blocks = re.findall(diff_pattern, text, re.DOTALL)

    for diff in diff_blocks:
        # Extract file path from --- a/path/to/file
        file_match = re.search(r"---\s+a/([\w\./]+)", diff)
        if not file_match:
            logger.warning(f"Could not extract file path from diff: {diff[:50]}...")
            continue

        file_path = file_match.group(1)

        # Determine action (heuristic: if diff starts with new file, it's create)
        action = "modify"
        if "new file mode" in diff or "+++ /dev/null" in diff:
            action = "create"
        elif "--- /dev/null" in diff:
            action = "create"
        elif "deleted file mode" in diff:
            action = "delete"

        patches.append({
            "file_path": file_path,
            "diff": diff,
            "rationale": f"Implement changes for {file_path}",
            "action": action
        })

    logger.info(f"Extracted {len(patches)} patches from crew output")
    return patches


def _extract_verification_steps(text: str) -> List[str]:
    """
    Extract verification steps from crew output.

    Args:
        text: Raw crew output text.

    Returns:
        List of verification step strings.
    """
    import re

    # Look for numbered lists after "Verification:" or "Test:"
    verification_pattern = r"(?:Verification|Test|Testing):?\s*\n((?:\d+\.\s+.+\n?)+)"
    match = re.search(verification_pattern, text, re.IGNORECASE)

    if match:
        steps_text = match.group(1)
        steps = re.findall(r"\d+\.\s+(.+)", steps_text)
        return [step.strip() for step in steps if step.strip()]

    # Fallback: generic verification steps
    return [
        "Review generated code for correctness",
        "Test implementation in target environment",
        "Verify safety interlocks and fault handling"
    ]


__all__ = ["implement_feature"]
