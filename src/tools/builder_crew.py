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
from typing import Dict, Any, List, Optional

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

    try:
        if provider == "openai":
            if not LANGCHAIN_OPENAI_AVAILABLE:
                logger.error("langchain_openai not installed. Run: pip install langchain-openai")
                return None

            api_key = api_keys.get("openai", "")
            if not api_key:
                logger.error("OpenAI API key not configured in Settings → API Keys")
                return None

            logger.info(f"Creating OpenAI LLM: {model}")
            return ChatOpenAI(model=model, api_key=api_key)

        elif provider == "anthropic":
            if not LANGCHAIN_ANTHROPIC_AVAILABLE:
                logger.error("langchain_anthropic not installed. Run: pip install langchain-anthropic")
                return None

            api_key = api_keys.get("anthropic", "")
            if not api_key:
                logger.error("Anthropic API key not configured in Settings → API Keys")
                return None

            logger.info(f"Creating Anthropic LLM: {model}")
            return ChatAnthropic(model=model, api_key=api_key)

        elif provider == "google":
            if not LANGCHAIN_GOOGLE_AVAILABLE:
                logger.error("langchain_google_genai not installed. Run: pip install langchain-google-genai")
                return None

            api_key = api_keys.get("google", "")
            if not api_key:
                logger.error("Google API key not configured in Settings → API Keys")
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
            description="""Implement the plan step-by-step.

For each file that needs to be created or modified, output the COMPLETE file content in this EXACT format:

### FILE: path/to/filename.py
```python
# Complete file content here
# Include ALL code, not just changes
...
```

For example, if creating a snake game:
### FILE: snake.py
```python
import pygame
# ... complete implementation ...
```

IMPORTANT:
- Always include the ### FILE: header with the EXACT filename from the plan
- Output the FULL file content, NOT a diff
- Use the correct file extension (.py, .js, .ts, .st, etc.)
- Include clear variable names and comments
- Consider edge cases (startup, shutdown, faults)
- Implement safety interlocks where applicable for PLC code
""",
            agent=coder,
            expected_output="Complete file contents for all affected files with ### FILE: headers",
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
        parts.append("\nActive Files:\n" + "\n".join(f"- {f}" for f in active_files))

    if recent_changes := context.get("recent_changes"):
        parts.append("\nRecent Changes:\n" + "\n".join(f"- {c}" for c in recent_changes))

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

    # Parse diff blocks (with fallback to code blocks)
    patch_plans = _extract_patches_from_text(result_text, original_request=request)

    # Extract verification steps (look for numbered list after "Verification:" or "Test:")
    verification_steps = _extract_verification_steps(result_text)

    # Build summary - warn if no patches extracted
    if patch_plans:
        summary = f"Implemented feature: {request[:80]}... ({len(patch_plans)} files affected)"
    else:
        # FALLBACK: Try to extract ANY code block as a last resort
        import re
        any_code_pattern = r"```\w*\s*\n(.*?)```"
        all_code_blocks = re.findall(any_code_pattern, result_text, re.DOTALL)

        if all_code_blocks:
            # Use the longest code block as the main output
            longest_code = max(all_code_blocks, key=len).strip()

            if longest_code:
                # Extract filename from request
                file_path = _extract_filename_from_request(request)

                patch_plans.append({
                    "file_path": file_path,
                    "content": longest_code,
                    "diff": None,
                    "rationale": f"Generated code for: {request[:50]}...",
                    "action": "create"
                })
                summary = f"Implemented feature: {request[:80]}... (1 file from fallback extraction)"
                logger.info(f"Fallback extraction: found code block, using filename: {file_path}")
            else:
                summary = f"Feature implementation completed but no code patches were extracted. Review the output manually."
                logger.warning(f"CrewAI completed but extracted 0 patches. Result text length: {len(result_text)}")
        else:
            summary = f"Feature implementation completed but no code patches were extracted. Review the output manually."
            logger.warning(f"CrewAI completed but extracted 0 patches. Result text length: {len(result_text)}")

    return {
        "patch_plans": patch_plans,
        "summary": summary,
        "verification_steps": verification_steps,
        "metadata": {
            "crew_enabled": True,
            "budget_mode": "bounded",
            "max_iterations": MAX_CREW_ITERATIONS,
            "patches_generated": len(patch_plans),
            "extraction_method": "diff_blocks" if any(p.get("diff") for p in patch_plans) else "code_blocks"
        }
    }


def _extract_patches_from_text(text: str, original_request: str = "") -> List[Dict[str, Any]]:
    """
    Extract unified diff patches OR code blocks from crew output text.

    PERMANENT FIX: Attempts to extract in order:
    0. ### FILE: headers with code blocks (new preferred format)
    1. Proper unified diff blocks (```diff)
    2. Code blocks with file path hints (```python # filename.py)
    3. Code blocks after file path mentions

    Args:
        text: Raw crew output text.
        original_request: Original user request (to extract filename hints).

    Returns:
        List of PatchPlan-compatible dicts.
    """
    import re

    patches = []

    # =================================================================
    # Strategy 0 (NEW): Look for ### FILE: headers with code blocks
    # This is the preferred format from the updated Coder instructions
    # =================================================================
    file_header_pattern = r"###\s*FILE:\s*([\w\./_-]+)\s*\n```\w*\s*\n(.*?)```"
    file_blocks = re.findall(file_header_pattern, text, re.DOTALL | re.IGNORECASE)

    for file_path, code in file_blocks:
        if code.strip():
            patches.append({
                "file_path": file_path.strip(),
                "content": code.strip(),
                "diff": None,
                "rationale": f"Create {file_path.strip()} with generated code",
                "action": "create"
            })

    if patches:
        logger.info(f"[FIX] Extracted {len(patches)} patches from ### FILE: headers")
        return patches

    # =================================================================
    # Strategy 1: Find proper diff blocks (```diff ... ```)
    # =================================================================
    diff_pattern = r"```diff\s*\n(.*?)```"
    diff_blocks = re.findall(diff_pattern, text, re.DOTALL)

    for diff in diff_blocks:
        # Extract file path from --- a/path/to/file
        file_match = re.search(r"---\s+a/([\w\./_-]+)", diff)
        if not file_match:
            # Try alternative format: --- path/to/file
            file_match = re.search(r"---\s+([\w\./_-]+)", diff)
        if not file_match:
            logger.warning(f"Could not extract file path from diff: {diff[:50]}...")
            continue

        file_path = file_match.group(1)

        # Determine action (heuristic)
        action = "modify"
        if "new file mode" in diff or "--- /dev/null" in diff:
            action = "create"
        elif "+++ /dev/null" in diff:
            action = "delete"

        patches.append({
            "file_path": file_path,
            "diff": diff,
            "rationale": f"Implement changes for {file_path}",
            "action": action
        })

    # If we found proper diffs, return them
    if patches:
        logger.info(f"Extracted {len(patches)} patches from diff blocks")
        return patches

    # Strategy 2: Look for code blocks with language hints and file path comments
    # Pattern: ```python\n# filename.py or ```python\n# File: filename.py
    code_pattern = r"```(\w+)\s*\n(?:#\s*(?:File:\s*)?([\w\./_-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))\s*\n)?(.*?)```"
    code_blocks = re.findall(code_pattern, text, re.DOTALL | re.IGNORECASE)

    for lang, file_hint, code in code_blocks:
        if not code.strip():
            continue

        # Try to determine filename
        file_path = None

        # Use file hint from comment if present
        if file_hint:
            file_path = file_hint.strip()
        else:
            # IMPROVED: Try multiple patterns to extract filename from original request
            # Patterns ordered from most specific to least specific
            filename_patterns = [
                # "called snake.py", "named snake.py"
                r"(?:called|named)\s+['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
                # "create snake.py", "make snake.py", "write snake.py"
                r"(?:create|make|write|build)\s+['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
                # "in snake.py", "to snake.py", "file snake.py"
                r"(?:in|to|file)\s+['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
                # "snake.py" anywhere in the request (last resort)
                r"['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
            ]

            for pattern in filename_patterns:
                filename_match = re.search(pattern, original_request, re.IGNORECASE)
                if filename_match:
                    file_path = filename_match.group(1)
                    break

            if not file_path:
                # Look for filename mention near this code block in the text
                # Search backwards from code block position for filename
                code_pos = text.find(code[:50]) if len(code) >= 50 else text.find(code)
                if code_pos > 0:
                    nearby_text = text[max(0, code_pos-500):code_pos]
                    nearby_match = re.search(r"['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?", nearby_text)
                    if nearby_match:
                        file_path = nearby_match.group(1)

        if not file_path:
            # Default filename based on language
            ext_map = {"python": "py", "javascript": "js", "typescript": "ts", "java": "java", "go": "go", "rust": "rs"}
            ext = ext_map.get(lang.lower(), lang.lower())
            file_path = f"generated_code.{ext}"
            logger.warning(f"Could not determine filename, using default: {file_path}")

        # Create a "full file content" patch (for new file creation)
        patches.append({
            "file_path": file_path,
            "content": code.strip(),  # Full content for direct write
            "diff": None,  # No diff, use direct write
            "rationale": f"Create {file_path} with generated code",
            "action": "create"
        })

    logger.info(f"Extracted {len(patches)} patches from code blocks (fallback)")
    return patches


def _extract_filename_from_request(request: str) -> str:
    """
    Extract target filename from user request.

    PERMANENT FIX: More aggressive filename extraction with additional patterns.

    Args:
        request: Original user request text.

    Returns:
        Extracted filename or default "generated_code.py"
    """
    import re

    # PERMANENT FIX: Extended patterns to catch more filename variations
    # Ordered from most specific to least specific
    patterns = [
        # "called snake_6.py", "named game.py"
        r"(?:called|named)\s+['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
        # "create snake.py", "make game.py", "write app.py", "build main.py"
        r"(?:create|make|write|build|generate)\s+(?:a\s+)?(?:\w+\s+)*?['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
        # "script called snake.py"
        r"script\s+(?:called|named)\s+['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
        # "file snake.py", "in snake.py", "to snake.py"
        r"(?:file|in|to)\s+['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
        # Any filename with extension at the end of request
        r"([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))\s*$",
        # Any filename with extension anywhere (last resort)
        r"['\"]?([\w\._-]+\.(?:py|js|ts|tsx|jsx|st|scl|java|go|rs|rb|c|cpp|h))['\"]?",
    ]

    for pattern in patterns:
        match = re.search(pattern, request, re.IGNORECASE)
        if match:
            filename = match.group(1)
            logger.info(f"[FIX] Extracted filename '{filename}' from request using pattern")
            return filename

    # Default based on common keywords in request
    if any(kw in request.lower() for kw in ['python', 'py', 'snake', 'game']):
        default = "generated_code.py"
    elif any(kw in request.lower() for kw in ['javascript', 'js', 'node']):
        default = "generated_code.js"
    elif any(kw in request.lower() for kw in ['typescript', 'ts', 'angular', 'react']):
        default = "generated_code.ts"
    elif any(kw in request.lower() for kw in ['structured text', 'plc', 'st']):
        default = "generated_code.st"
    else:
        default = "generated_code.py"

    logger.warning(f"[FIX] Could not extract filename from request, using default: {default}")
    return default


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
