"""Utility functions for DafnyBench evaluation."""

import re
from typing import Union

from inspect_ai.solver import TaskState


def extract_code_v1(completion: str) -> str:
    """Extract Dafny code from model completion (v1 - buggy version).

    This version extracts from the final completion text, taking the last code block.
    Problem: If the model celebrates after success ("Perfect! It worked!"), this may
    extract the wrong code or fail to find any code.

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


def extract_code_v2(state: TaskState) -> str:
    """Extract Dafny code from task state (v2 - fixed version with backtracking).

    This version walks backwards through the message history. If the current message
    has no Dafny code (e.g., celebratory message), it backtracks to find the most
    recent message that does contain code.

    Args:
        state: Task state containing message history.

    Returns:
        Cleaned Dafny code.
    """
    code_block_pattern = r"```(?:dafny)?\s*\n(.*?)```"

    # Walk backwards through assistant messages
    for message in reversed(state.messages):
        # Only look at assistant messages
        if message.role != "assistant":
            continue

        # Get the text content
        content = message.text if hasattr(message, "text") else str(message.content)

        # Try to extract code from this message
        matches = re.findall(code_block_pattern, content, re.DOTALL)

        if matches:
            # Found code! Return the last code block from this message
            return matches[-1].strip()

    # Fallback: use v1 extraction on the final completion
    return extract_code_v1(state.output.completion)


def extract_code(
    completion_or_state: Union[str, TaskState], strategy: str = "v1"
) -> str:
    """Extract Dafny code using the specified strategy.

    Args:
        completion_or_state: Either a completion string (for v1) or TaskState (for v2).
        strategy: Extraction strategy - "v1" (buggy) or "v2" (fixed with backtracking).

    Returns:
        Cleaned Dafny code.
    """
    if strategy == "v1":
        # v1 requires a string
        if isinstance(completion_or_state, str):
            return extract_code_v1(completion_or_state)
        else:
            # If given TaskState, extract completion
            return extract_code_v1(completion_or_state.output.completion)
    elif strategy == "v2":
        # v2 requires TaskState for message history
        if isinstance(completion_or_state, TaskState):
            return extract_code_v2(completion_or_state)
        else:
            # If given string, fall back to v1
            return extract_code_v1(completion_or_state)
    else:
        raise ValueError(f"Unknown extraction strategy: {strategy}")


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
