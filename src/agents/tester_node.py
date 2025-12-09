"""
Tester Agent Node for Pulse IDE.

Validates generated/modified code against requirements. Performs static
analysis checks including variable declaration validation and logic pattern
detection.
"""

from typing import Dict, Any
import re

from src.core.state import AgentState
from src.core.file_manager import FileManager


def tester_node(state: AgentState) -> Dict[str, Any]:
    """
    Tester Agent Node for validating PLC code.

    This node:
    1. Initializes FileManager
    2. Iterates through all files in files_touched
    3. Performs static analysis:
       - Check 1 (Safety): Validates VAR/END_VAR matching
       - Check 2 (Logic): Detects empty IF blocks
    4. Constructs test report
    5. Returns report in messages

    Args:
        state: Current agent state containing files_touched and workspace_path.

    Returns:
        Dict with "messages" containing test report.

    Example:
        >>> state = {
        ...     "files_touched": ["main.st"],
        ...     "workspace_path": "./workspace",
        ...     ...
        ... }
        >>> result = tester_node(state)
        >>> print(result["messages"][0].content)
        Test Report:
        ...
    """
    # Extract necessary state
    files_touched = state.get("files_touched", [])
    workspace_path = state.get("workspace_path", ".")

    # Validate input
    if not files_touched:
        return {
            "test_results": {"status": "skipped", "message": "No files to test"}
        }

    # Step 1: Initialize FileManager
    try:
        file_manager = FileManager(workspace_path)
    except Exception as e:
        return {
            "test_results": {
                "status": "error",
                "message": f"Error initializing FileManager: {str(e)}"
            }
        }

    # Step 2: Initialize report
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("TESTER AGENT - VALIDATION REPORT")
    report_lines.append("=" * 60)
    report_lines.append("")

    all_checks_passed = True

    # Step 3: Iterate through files_touched
    for file_path in files_touched:
        report_lines.append(f"File: {file_path}")
        report_lines.append("-" * 60)

        try:
            # Read file content
            content = file_manager.read_file(file_path)

            # Step 4: Static Analysis
            file_errors = []
            file_warnings = []

            # CHECK 1: VAR/END_VAR matching (Safety)
            # Use regex to match whole words only
            var_count = len(re.findall(r'\bVAR\b', content))
            end_var_count = len(re.findall(r'\bEND_VAR\b', content))

            if var_count != end_var_count:
                file_errors.append(
                    f"CRITICAL ERROR: Mismatched VAR/END_VAR declarations "
                    f"(VAR: {var_count}, END_VAR: {end_var_count})"
                )
                all_checks_passed = False

            # CHECK 2: Empty IF blocks (Logic)
            # Pattern: IF...THEN immediately followed by END_IF (with optional whitespace)
            empty_if_pattern = r'IF\s+.*?\s+THEN\s*END_IF'
            empty_if_matches = re.findall(empty_if_pattern, content, re.IGNORECASE | re.DOTALL)

            if empty_if_matches:
                file_warnings.append(
                    f"WARNING: Empty IF block detected ({len(empty_if_matches)} occurrence(s))"
                )
                for match in empty_if_matches[:3]:  # Show first 3 matches
                    # Clean up whitespace for display
                    clean_match = ' '.join(match.split())
                    file_warnings.append(f"  - {clean_match}")

            # CHECK 3: Missing semicolons (common syntax error)
            # Look for lines that should end with semicolon but don't
            lines = content.split('\n')
            missing_semicolons = []
            for i, line in enumerate(lines, start=1):
                stripped = line.strip()
                # Skip empty lines, comments, and structural keywords
                if not stripped or stripped.startswith('//') or stripped.startswith('(*'):
                    continue
                # Check if line needs semicolon (assignments, calls, etc.)
                if ((':=' in stripped or 'RETURN' in stripped.upper())
                    and not stripped.endswith(';')
                    and not stripped.endswith('THEN')
                    and not stripped.endswith('DO')):
                    missing_semicolons.append((i, stripped[:50]))  # First 50 chars

            if missing_semicolons:
                file_warnings.append(
                    f"WARNING: Possible missing semicolons ({len(missing_semicolons)} line(s))"
                )
                for line_num, line_text in missing_semicolons[:3]:  # Show first 3
                    file_warnings.append(f"  Line {line_num}: {line_text}...")

            # Report results for this file
            if file_errors:
                report_lines.append("ERRORS:")
                report_lines.extend(f"  {error}" for error in file_errors)
                report_lines.append("")

            if file_warnings:
                report_lines.append("WARNINGS:")
                report_lines.extend(f"  {warning}" for warning in file_warnings)
                report_lines.append("")

            if not file_errors and not file_warnings:
                report_lines.append("✓ All checks passed")
                report_lines.append("")

        except FileNotFoundError:
            report_lines.append(f"ERROR: File not found: {file_path}")
            report_lines.append("")
            all_checks_passed = False
        except Exception as e:
            report_lines.append(f"ERROR: Failed to analyze file: {str(e)}")
            report_lines.append("")
            all_checks_passed = False

    # Step 5: Final summary
    report_lines.append("=" * 60)
    if all_checks_passed:
        report_lines.append("SUMMARY: All critical checks passed ✓")
    else:
        report_lines.append("SUMMARY: Critical errors detected - review required ✗")
    report_lines.append("=" * 60)

    # Step 6: Construct final report message
    final_report = "\n".join(report_lines)

    # Store test results in structured format
    test_results = {
        "status": "passed" if all_checks_passed else "failed",
        "files_tested": len(files_touched),
        "report": final_report
    }

    # Step 7: Return updated state
    # Import AIMessage here to avoid circular imports
    from langchain_core.messages import AIMessage

    return {
        "messages": [AIMessage(content=final_report)],
        "test_results": test_results
    }
