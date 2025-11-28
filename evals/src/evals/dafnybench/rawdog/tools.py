"""Tool execution for rawdog DafnyBench implementation with hint insertion tools."""

import subprocess
import tempfile
from pathlib import Path


# ===== Phase 1: State Management =====

def get_code_state(messages: list[dict]) -> str | None:
    """Extract current code state from message history.

    Searches backwards through messages for most recent code state marker.
    Returns None if no state found (initialization case).

    Args:
        messages: Message history containing code states

    Returns:
        Current code string or None if no state found
    """
    for msg in reversed(messages):
        if msg["role"] == "user":
            # Check for list of tool_result blocks
            if isinstance(msg["content"], list):
                for block in msg["content"]:
                    if block.get("type") == "tool_result":
                        content = block.get("content", "")
                        if "=== CURRENT_CODE_STATE ===" in content:
                            # Extract code between markers
                            start = content.find("```dafny\n")
                            end = content.find("\n```", start)
                            if start != -1 and end != -1:
                                return content[start + 9 : end]
            # Check for string content with state marker
            elif isinstance(msg["content"], str):
                if "=== CURRENT_CODE_STATE ===" in msg["content"]:
                    start = msg["content"].find("```dafny\n")
                    end = msg["content"].find("\n```", start)
                    if start != -1 and end != -1:
                        return msg["content"][start + 9 : end]
    return None


def update_code_state(messages: list[dict], new_code: str) -> None:
    """Update message history with new code state.

    Appends user message containing state marker and code.
    This is called after each insertion to update the tracked state.

    Args:
        messages: Message history to update (modified in place)
        new_code: New code state to store
    """
    state_message = f"""=== CURRENT_CODE_STATE ===

```dafny
{new_code}
```

State updated after hint insertion."""

    messages.append({"role": "user", "content": state_message})


# ===== Phase 2: Insertion Utilities =====

def get_indentation(line: str) -> str:
    """Extract leading whitespace from a line.

    Args:
        line: Line of code

    Returns:
        Leading whitespace string
    """
    return line[: len(line) - len(line.lstrip())]


def find_insertion_point(
    code_lines: list[str],
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> tuple[int, str] | tuple[None, str]:
    """Find where to insert hint using line number or context matching.

    Returns:
        (line_index, indentation) on success
        (None, error_message) on failure

    Priority:
        1. If line_number provided, use it (0-indexed internally)
        2. If context_before/after provided, search for match
        3. If both provided, try line_number first, fall back to context

    Args:
        code_lines: Lines of code
        line_number: 1-indexed line number (optional)
        context_before: Line before insertion point (optional)
        context_after: Line after insertion point for disambiguation (optional)

    Returns:
        Either (index, indentation) or (None, error_message)
    """
    if line_number is not None:
        # Line-based insertion (convert to 0-indexed)
        idx = line_number - 1
        if 0 <= idx <= len(code_lines):
            # Get indentation from previous line or next line
            if idx > 0:
                indent = get_indentation(code_lines[idx - 1])
            elif idx < len(code_lines):
                indent = get_indentation(code_lines[idx])
            else:
                indent = ""
            return idx, indent
        else:
            return (
                None,
                f"Line number {line_number} out of range (1-{len(code_lines)})",
            )

    if context_before is not None:
        # Context-based search
        matches = []
        for i, line in enumerate(code_lines):
            if context_before.strip() in line:
                # Check context_after if provided
                if context_after is not None:
                    if (
                        i + 1 < len(code_lines)
                        and context_after.strip() in code_lines[i + 1]
                    ):
                        matches.append(i + 1)
                else:
                    matches.append(i + 1)

        if len(matches) == 0:
            return None, f"Context not found: '{context_before}'"
        elif len(matches) > 1:
            return (
                None,
                f"Ambiguous context: '{context_before}' matches {len(matches)} locations. "
                f"Use context_after or line_number to disambiguate.",
            )
        else:
            idx = matches[0]
            indent = get_indentation(code_lines[idx - 1]) if idx > 0 else ""
            return idx, indent

    return None, "Must provide either line_number or context_before"


def format_hint_line(hint_type: str, hint_content: str, indentation: str) -> str:
    """Format a hint with proper indentation and syntax.

    Args:
        hint_type: "invariant", "assert", "requires", "ensures", "decreases"
        hint_content: The actual hint expression
        indentation: Leading whitespace

    Returns:
        Formatted hint line (no trailing newline)
    """
    return f"{indentation}{hint_type} {hint_content}"


# ===== Phase 3: Specialized Insertion Tools =====

def insert_hint(
    messages: list[dict],
    hint_type: str,
    hint_content: str,
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> dict[str, str | bool]:
    """Generic hint insertion function.

    Returns:
        dict with keys:
            - success (bool): True if insertion succeeded
            - message (str): Success/error message
            - code (str): Full code after insertion (on success)

    Args:
        messages: Message history containing code state
        hint_type: Type of hint to insert
        hint_content: Content of the hint
        line_number: Optional line number (1-indexed)
        context_before: Optional context before insertion point
        context_after: Optional context after insertion point
    """
    # Get current code state
    current_code = get_code_state(messages)
    if current_code is None:
        return {
            "success": False,
            "message": "Error: No code state found. This is a system error.",
            "code": "",
        }

    # Parse into lines
    code_lines = current_code.split("\n")

    # Find insertion point
    result = find_insertion_point(code_lines, line_number, context_before, context_after)
    if result[0] is None:
        return {
            "success": False,
            "message": result[1],
            "code": current_code,
        }

    idx, indent = result

    # Format hint
    hint_line = format_hint_line(hint_type, hint_content, indent)

    # Insert at position
    code_lines.insert(idx, hint_line)

    # Reconstruct code
    new_code = "\n".join(code_lines)

    # DON'T update state here - let the agent do it after collecting all tool results
    # This prevents breaking tool_use/tool_result pairing in message history

    return {
        "success": True,
        "message": f"✓ {hint_type.capitalize()} inserted at line {idx + 1}",
        "code": new_code,
    }


def insert_invariant(
    messages: list[dict],
    invariant: str,
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> dict[str, str | bool]:
    """Insert loop invariant hint.

    Args:
        messages: Message history
        invariant: Invariant expression
        line_number: Optional line number (1-indexed)
        context_before: Optional context before insertion
        context_after: Optional context after insertion

    Returns:
        Result dict with success, message, and code
    """
    return insert_hint(
        messages, "invariant", invariant, line_number, context_before, context_after
    )


def insert_assertion(
    messages: list[dict],
    assertion: str,
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> dict[str, str | bool]:
    """Insert assertion hint.

    Args:
        messages: Message history
        assertion: Assertion expression
        line_number: Optional line number (1-indexed)
        context_before: Optional context before insertion
        context_after: Optional context after insertion

    Returns:
        Result dict with success, message, and code
    """
    return insert_hint(
        messages, "assert", assertion, line_number, context_before, context_after
    )


def insert_precondition(
    messages: list[dict],
    precondition: str,
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> dict[str, str | bool]:
    """Insert function precondition (requires).

    Args:
        messages: Message history
        precondition: Precondition expression
        line_number: Optional line number (1-indexed)
        context_before: Optional context before insertion
        context_after: Optional context after insertion

    Returns:
        Result dict with success, message, and code
    """
    return insert_hint(
        messages, "requires", precondition, line_number, context_before, context_after
    )


def insert_postcondition(
    messages: list[dict],
    postcondition: str,
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> dict[str, str | bool]:
    """Insert function postcondition (ensures).

    Args:
        messages: Message history
        postcondition: Postcondition expression
        line_number: Optional line number (1-indexed)
        context_before: Optional context before insertion
        context_after: Optional context after insertion

    Returns:
        Result dict with success, message, and code
    """
    return insert_hint(
        messages, "ensures", postcondition, line_number, context_before, context_after
    )


def insert_measure(
    messages: list[dict],
    measure: str,
    line_number: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> dict[str, str | bool]:
    """Insert termination measure (decreases).

    Args:
        messages: Message history
        measure: Decreases expression
        line_number: Optional line number (1-indexed)
        context_before: Optional context before insertion
        context_after: Optional context after insertion

    Returns:
        Result dict with success, message, and code
    """
    return insert_hint(
        messages, "decreases", measure, line_number, context_before, context_after
    )


# ===== Phase 4: Updated verify_dafny =====

def verify_dafny(messages: list[dict]) -> dict[str, str | bool]:
    """Verify current code state using Dafny compiler.

    Reads code from message history state, runs verification, returns
    results including full rendered code.

    Args:
        messages: Message history containing code state

    Returns:
        dict with keys:
            - success (bool): True if verification succeeded
            - message (str): Success/failure message
            - code (str): Full current code with all hints
            - stdout (str): Standard output from Dafny
            - stderr (str): Standard error from Dafny
    """
    # Get current code state
    code = get_code_state(messages)
    if code is None:
        return {
            "success": False,
            "message": "Error: No code state found. Insert hints first.",
            "code": "",
            "stdout": "",
            "stderr": "",
        }

    # Check for verification bypass attempts (following DafnyBench methodology)
    if "{:verify false}" in code.lower():
        return {
            "success": False,
            "message": "Invalid code: contains {:verify false} which bypasses verification. "
            "You must properly verify the code with correct annotations.",
            "code": code,
            "stdout": "",
            "stderr": "Bypass attempt detected",
        }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dfy", delete=False) as tmp:
        tmp.write(code)
        temp_path = tmp.name

    try:
        # Run Dafny verification with timeout
        result = subprocess.run(
            ["dafny", "verify", temp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check for successful verification
        success = result.returncode == 0 and "0 errors" in result.stdout

        if success:
            message = "✓ Verification succeeded! All checks passed."
        else:
            error_output = result.stderr if result.stderr else result.stdout
            message = f"Verification failed:\n\n{error_output}"

        return {
            "success": success,
            "message": message,
            "code": code,  # Return full code
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Verification timed out after 30 seconds. "
            "The program may be too complex or contain infinite loops.",
            "code": code,
            "stdout": "",
            "stderr": "Timeout",
        }
    finally:
        # Cleanup temporary file
        Path(temp_path).unlink(missing_ok=True)
