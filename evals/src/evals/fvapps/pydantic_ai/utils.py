"""Utility functions for FVAPPS evaluation."""

import re


def extract_code(output: str) -> str:
    """Extract Lean code from agent output.

    Looks for ```lean or ``` code blocks and returns the content.
    Returns last code block if multiple exist.

    Args:
        output: Agent output text

    Returns:
        Extracted Lean code
    """
    # Find all code blocks (``` or ```lean)
    pattern = r"```(?:lean)?\n(.*?)```"
    matches = re.findall(pattern, output, re.DOTALL)

    if matches:
        return matches[-1].strip()

    # Fallback: return entire output if no code blocks
    return output.strip()


def categorize_error(stderr: str) -> str:
    """Categorize Lean error types from stderr output.

    Args:
        stderr: Error output from Lean compiler

    Returns:
        One of: type_error, name_error, tactic_failure, termination_failure,
        incomplete_proof, syntax_error, unit_test_failure, unknown_error
    """
    stderr_lower = stderr.lower()

    if "type mismatch" in stderr_lower or "expected type" in stderr_lower:
        return "type_error"
    elif "unknown identifier" in stderr_lower or "unknown constant" in stderr_lower:
        return "name_error"
    elif "tactic" in stderr_lower and "failed" in stderr_lower:
        return "tactic_failure"
    elif "termination" in stderr_lower or "structural recursion" in stderr_lower:
        return "termination_failure"
    elif "unsolved goals" in stderr_lower or "don't know how to synthesize" in stderr_lower:
        return "incomplete_proof"
    elif "unexpected" in stderr_lower or "expected" in stderr_lower:
        return "syntax_error"
    elif "guard" in stderr_lower or "failed" in stderr_lower:
        return "unit_test_failure"
    else:
        return "unknown_error"
