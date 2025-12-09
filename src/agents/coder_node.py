"""
Coder Agent Node for Pulse IDE.

Implements file I/O and code generation. Translates plan steps into
actual PLC code and writes changes to disk. Uses CrewAI for iterative
code refinement.
"""

from typing import Dict, Any
import re

from src.core.state import AgentState
from src.core.crew_factory import CrewFactory
from src.core.file_manager import FileManager
from src.core.config import Config


def coder_node(state: AgentState) -> Dict[str, Any]:
    """
    Coder Agent Node for generating and writing PLC code.

    This node:
    1. Initializes FileManager and CrewFactory
    2. Iterates through each step in the plan
    3. Gets file context (from state or reads from disk)
    4. Executes CrewAI coder crew to generate code
    5. Writes generated code to disk (atomic writes)
    6. Tracks all modified files in files_touched

    Args:
        state: Current agent state containing plan and file_context.

    Returns:
        Dict with "files_touched" and "code_changes" keys.

    Example:
        >>> state = {
        ...     "plan": ["Add motor control to main.st"],
        ...     "workspace_path": "./workspace",
        ...     ...
        ... }
        >>> result = coder_node(state)
        >>> print(result["files_touched"])
        ['main.st']
    """
    # Extract necessary state
    plan = state.get("plan", [])
    workspace_path = state.get("workspace_path", ".")
    file_context = state.get("file_context", "")

    # Validate plan
    if not plan:
        return {
            "files_touched": [],
            "code_changes": "Error: No plan provided to Coder Agent"
        }

    # Step 1: Initialize FileManager and CrewFactory
    try:
        file_manager = FileManager(workspace_path)
        factory = CrewFactory()
    except Exception as e:
        return {
            "files_touched": [],
            "code_changes": f"Error initializing Coder Agent: {str(e)}"
        }

    # Step 2: Initialize tracking
    files_touched = []
    changes_log = []

    # Step 3: Iterate through each step in the plan
    for step_idx, step in enumerate(plan, start=1):
        try:
            # Step 4: Get context for this step
            # Check if file_context contains a file path or actual content
            context = ""

            # Try to extract filename from the step (e.g., "Add function to main.st")
            filename_match = re.search(r'(\w+\.st)', step)
            target_file = filename_match.group(1) if filename_match else "main.st"

            # Try to read existing file content if it exists
            if file_manager.file_exists(target_file):
                try:
                    context = file_manager.read_file(target_file)
                except Exception:
                    context = "# New file - no existing content"
            else:
                context = "# New file - no existing content"

            # If file_context is provided and looks like content (not a path), use it
            if file_context and not file_context.endswith('.st'):
                context = file_context

            # Step 5: Execute the crew
            crew = factory.create_coder_crew(step, context)
            result = crew.kickoff()

            # Step 6: Parse the result
            # The crew is configured with output_pydantic=CodeOutput
            code = ""
            explanation = ""

            if hasattr(result, 'pydantic') and result.pydantic:
                code_output = result.pydantic
                code = code_output.code if hasattr(code_output, 'code') else str(code_output)
                explanation = code_output.explanation if hasattr(code_output, 'explanation') else ""
            elif hasattr(result, 'raw'):
                code = result.raw
                explanation = f"Step {step_idx}: {step}"
            else:
                code = str(result)
                explanation = f"Step {step_idx}: {step}"

            # Clean up code (remove markdown formatting if present)
            code = _clean_code(code)

            # Step 7: Write to disk
            file_manager.write_file(target_file, code)

            # Step 8: Track the file
            if target_file not in files_touched:
                files_touched.append(target_file)

            # Log the change
            changes_log.append(
                f"Step {step_idx}: {step}\n"
                f"  File: {target_file}\n"
                f"  {explanation}"
            )

        except Exception as e:
            changes_log.append(
                f"Step {step_idx}: {step}\n"
                f"  ERROR: {str(e)}"
            )

    # Step 9: Return updated state
    code_changes = "\n\n".join(changes_log)

    return {
        "files_touched": files_touched,
        "code_changes": code_changes
    }


def _clean_code(code: str) -> str:
    """
    Remove markdown formatting from generated code.

    Args:
        code: Raw code string that may contain markdown

    Returns:
        Clean code without markdown formatting
    """
    # Remove markdown code blocks (```...```)
    code = re.sub(r'^```[\w]*\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^```[\w]*', '', code, flags=re.MULTILINE)
    code = re.sub(r'```$', '', code, flags=re.MULTILINE)

    # Remove any leading/trailing whitespace
    code = code.strip()

    return code
