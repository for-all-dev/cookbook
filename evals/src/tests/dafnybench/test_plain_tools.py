"""Tests for plain tool-based hint insertion."""

from evals.dafnybench.plain.tools import (
    find_insertion_point,
    format_hint_line,
    get_code_state,
    get_indentation,
    insert_invariant,
    update_code_state,
)


def test_get_indentation():
    """Test extraction of leading whitespace."""
    assert get_indentation("    while (i < n)") == "    "
    assert get_indentation("while (i < n)") == ""
    assert get_indentation("\t\tassert x > 0") == "\t\t"
    assert get_indentation("") == ""


def test_format_hint_line():
    """Test formatting of hint lines with proper syntax."""
    line = format_hint_line("invariant", "0 <= i <= n", "  ")
    assert line == "  invariant 0 <= i <= n"

    line = format_hint_line("requires", "n >= 0", "")
    assert line == "requires n >= 0"

    line = format_hint_line("ensures", "r > 0", "    ")
    assert line == "    ensures r > 0"


def test_find_insertion_point_by_line():
    """Test finding insertion point by line number."""
    code_lines = ["method Test()", "{", "  var x := 0;", "}"]

    # Valid line number (line 3 = index 2)
    idx, indent = find_insertion_point(code_lines, line_number=3)
    assert idx == 2
    # Previous line is "{" which has no indentation
    assert indent == ""

    # Beginning of file
    idx, indent = find_insertion_point(code_lines, line_number=1)
    assert idx == 0

    # End of file
    idx, indent = find_insertion_point(code_lines, line_number=5)
    assert idx == 4

    # Out of range
    result = find_insertion_point(code_lines, line_number=10)
    assert result[0] is None
    assert "out of range" in result[1]


def test_find_insertion_point_by_context():
    """Test finding insertion point by context matching."""
    code_lines = [
        "method Sum(n: nat)",
        "{",
        "  var i := 0;",
        "  while (i < n)",
        "  {",
        "    i := i + 1;",
        "  }",
        "}",
    ]

    # Find by context_before
    idx, indent = find_insertion_point(code_lines, context_before="while (i < n)")
    assert idx == 4  # After "while" line, before opening brace
    assert indent == "  "

    # Find with context_after for disambiguation
    idx, indent = find_insertion_point(
        code_lines, context_before="while (i < n)", context_after="{"
    )
    assert idx == 4

    # Ambiguous context
    code_with_duplicates = ["var x := 0;", "var y := 0;", "var x := 0;"]
    result = find_insertion_point(code_with_duplicates, context_before="var x := 0;")
    assert result[0] is None
    assert "Ambiguous" in result[1]

    # Context not found
    result = find_insertion_point(code_lines, context_before="nonexistent")
    assert result[0] is None
    assert "not found" in result[1]


def test_state_management():
    """Test code state storage and retrieval from message history."""
    messages = []

    # Initially no state
    assert get_code_state(messages) is None

    # Add state
    code1 = "method Test() {}"
    update_code_state(messages, code1)
    assert get_code_state(messages) == code1
    assert len(messages) == 1
    assert messages[0]["role"] == "user"

    # Update state
    code2 = "method Test() {\n  var x := 0;\n}"
    update_code_state(messages, code2)
    assert get_code_state(messages) == code2

    # Most recent state is returned
    assert len(messages) == 2


def test_insert_invariant_by_line():
    """Test inserting invariant by line number."""
    messages = []
    initial_code = "method Test() {\n  while (i < n) {\n  }\n}"
    update_code_state(messages, initial_code)

    result = insert_invariant(messages, invariant="0 <= i <= n", line_number=2)

    assert result["success"]
    assert "inserted" in result["message"].lower()  # type: ignore
    assert "line 2" in result["message"]  # type: ignore

    # Check the returned code (insertion tools no longer update state internally)
    assert "invariant 0 <= i <= n" in result["code"]  # type: ignore


def test_insert_invariant_by_context():
    """Test inserting invariant by context matching."""
    messages = []
    initial_code = "method Test() {\n  while (i < n) {\n  }\n}"
    update_code_state(messages, initial_code)

    result = insert_invariant(
        messages, invariant="0 <= i <= n", context_before="while (i < n)"
    )

    assert result["success"]
    # Check the returned code
    assert "invariant 0 <= i <= n" in result["code"]  # type: ignore


def test_insertion_error_handling():
    """Test error handling for invalid insertion parameters."""
    messages = []
    initial_code = "method Test() {}"
    update_code_state(messages, initial_code)

    # Invalid line number
    result = insert_invariant(messages, invariant="true", line_number=100)
    assert not result["success"]
    assert "out of range" in result["message"]  # type: ignore

    # Context not found
    result = insert_invariant(messages, invariant="true", context_before="nonexistent")
    assert not result["success"]
    assert "not found" in result["message"]  # type: ignore


def test_multiple_insertions():
    """Test multiple sequential hint insertions with manual state updates."""
    messages = []
    initial_code = "method Sum(n: nat) returns (sum: nat)\n{\n  sum := 0;\n}"
    update_code_state(messages, initial_code)

    # Insert precondition
    result1 = insert_invariant(
        messages, invariant="n >= 0", context_before="method Sum"
    )
    assert result1["success"]
    assert "n >= 0" in result1["code"]  # type: ignore

    # Manually update state (simulating what agent does)
    update_code_state(messages, result1["code"])  # type: ignore

    # Insert another hint
    result2 = insert_invariant(messages, invariant="sum >= 0", line_number=4)
    assert result2["success"]

    # Check both hints are in second result
    assert "n >= 0" in result2["code"]  # type: ignore
    assert "sum >= 0" in result2["code"]  # type: ignore


def test_state_in_tool_results():
    """Test that state updates work when manually applied (agent pattern)."""
    messages = []
    initial_code = "method Test() {}"
    update_code_state(messages, initial_code)

    # Add a hint and manually update state (agent pattern)
    result = insert_invariant(messages, invariant="true", line_number=1)
    assert result["success"]
    update_code_state(messages, result["code"])  # type: ignore

    # Check that we have 2 state updates now
    user_messages = [m for m in messages if m["role"] == "user"]
    assert len(user_messages) == 2

    # Both should contain the state marker
    for msg in user_messages:
        assert "=== CURRENT_CODE_STATE ===" in msg["content"]


def test_insertion_preserves_indentation():
    """Test that insertions preserve proper indentation."""
    messages = []
    initial_code = """method Test()
{
  var x := 0;
  while (x < 10)
  {
    x := x + 1;
  }
}"""
    update_code_state(messages, initial_code)

    # Insert invariant with context
    result = insert_invariant(
        messages, invariant="0 <= x <= 10", context_before="while (x < 10)"
    )
    assert result["success"]

    # Check that invariant has same indentation as while statement in returned code
    assert "  invariant 0 <= x <= 10" in result["code"]  # type: ignore
