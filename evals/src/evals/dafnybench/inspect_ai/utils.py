"""Utility functions for DafnyBench evaluation."""

import re


def extract_code(completion: str) -> str:
    """Extract Dafny code from model completion, removing markdown formatting.

    Args:
        completion: Raw model output potentially with markdown, explanations, etc.

    Returns:
        Cleaned Dafny code.
    """
    # Remove markdown code blocks
    code_block_pattern = r"```(?:dafny)?\s*\n(.*?)```"
    matches = re.findall(code_block_pattern, completion, re.DOTALL)

    if matches:
        # Use the last code block (model might explain then provide code)
        return matches[-1].strip()

    # If no markdown blocks, return the whole completion
    return completion.strip()


def categorize_error(stderr: str) -> str:
    """Categorize Dafny verification errors into types.

    Args:
        stderr: Dafny error output.

    Returns:
        Error category string.
    """
    stderr_lower = stderr.lower()

    # Check for specific error patterns
    if "invariant" in stderr_lower:
        return "invariant_violation"
    elif "assertion" in stderr_lower or "assert" in stderr_lower:
        return "assertion_failure"
    elif "postcondition" in stderr_lower or "ensures" in stderr_lower:
        return "postcondition_violation"
    elif "precondition" in stderr_lower or "requires" in stderr_lower:
        return "precondition_violation"
    elif "decreases" in stderr_lower or "termination" in stderr_lower:
        return "termination_failure"
    elif "syntax error" in stderr_lower or "parse error" in stderr_lower:
        return "syntax_error"
    elif "resolution error" in stderr_lower or "type error" in stderr_lower:
        return "type_error"
    else:
        return "other_error"
