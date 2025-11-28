"""Manual tool-calling loop for rawdog DafnyBench implementation.

This module demonstrates what inspect-ai's generate() abstracts away by
implementing the tool-calling loop manually with the Anthropic SDK.

This version uses specialized insertion tools instead of having the agent
regenerate complete files.
"""

import logging

import anthropic
from evals.dafnybench.inspect_ai.utils import categorize_error
from evals.dafnybench.rawdog.prompt import RAWDOG_SYSTEM_PROMPT
from evals.dafnybench.rawdog.tools import (
    get_code_state,
    insert_assertion,
    insert_invariant,
    insert_measure,
    insert_postcondition,
    insert_precondition,
    verify_dafny,
)
from evals.dafnybench.rawdog.types import AgentResult, EvalSample, save_artifact


def run_agent(sample: EvalSample, model: str, max_iterations: int = 20) -> AgentResult:
    """Run agent on a single sample with manual tool-calling loop.

    This function implements the core tool-calling loop that inspect-ai's
    generate() handles automatically. It demonstrates:
    - Manual message history management
    - Anthropic API integration with tools
    - Tool execution and result handling
    - Iteration control and stopping conditions

    This version uses specialized insertion tools for targeted hint placement
    instead of having the agent regenerate complete Dafny files.

    Args:
        sample: Evaluation sample with code to verify
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5")
        max_iterations: Maximum number of tool-calling iterations

    Returns:
        AgentResult with success status, attempts, final code, and error type
    """
    # Initialize Anthropic client
    client = anthropic.Anthropic()

    # Strip "anthropic/" prefix from model name if present (inspect-ai format)
    if model.startswith("anthropic/"):
        model = model.replace("anthropic/", "")

    # Initialize message history with code state
    initial_state = f"""=== CURRENT_CODE_STATE ===

```dafny
{sample.hints_removed}
```

Above is the initial unhinted code. Use insertion tools to add verification hints."""

    messages = [
        {"role": "user", "content": sample.input},
        {"role": "user", "content": initial_state},
    ]

    # Track metrics
    attempts = 0
    success = False
    final_code = None
    error_type = None

    # Setup logging for this sample
    logger = logging.getLogger(__name__)
    logger.info(f"Starting evaluation for sample {sample.test_id}")

    # Tool definitions (Anthropic API format)
    tools = [
        {
            "name": "insert_invariant",
            "description": "Insert a loop invariant at specified location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "invariant": {
                        "type": "string",
                        "description": "Invariant expression",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number (1-indexed, optional)",
                    },
                    "context_before": {
                        "type": "string",
                        "description": "Line before insertion point (optional)",
                    },
                    "context_after": {
                        "type": "string",
                        "description": "Line after insertion point (optional)",
                    },
                },
                "required": ["invariant"],
            },
        },
        {
            "name": "insert_assertion",
            "description": "Insert an assertion at specified location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "assertion": {
                        "type": "string",
                        "description": "Assertion expression",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number (1-indexed, optional)",
                    },
                    "context_before": {
                        "type": "string",
                        "description": "Line before insertion point (optional)",
                    },
                    "context_after": {
                        "type": "string",
                        "description": "Line after insertion point (optional)",
                    },
                },
                "required": ["assertion"],
            },
        },
        {
            "name": "insert_precondition",
            "description": "Insert a function precondition (requires clause) at specified location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "precondition": {
                        "type": "string",
                        "description": "Precondition expression",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number (1-indexed, optional)",
                    },
                    "context_before": {
                        "type": "string",
                        "description": "Line before insertion point (optional)",
                    },
                    "context_after": {
                        "type": "string",
                        "description": "Line after insertion point (optional)",
                    },
                },
                "required": ["precondition"],
            },
        },
        {
            "name": "insert_postcondition",
            "description": "Insert a function postcondition (ensures clause) at specified location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "postcondition": {
                        "type": "string",
                        "description": "Postcondition expression",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number (1-indexed, optional)",
                    },
                    "context_before": {
                        "type": "string",
                        "description": "Line before insertion point (optional)",
                    },
                    "context_after": {
                        "type": "string",
                        "description": "Line after insertion point (optional)",
                    },
                },
                "required": ["postcondition"],
            },
        },
        {
            "name": "insert_measure",
            "description": "Insert a termination measure (decreases clause) at specified location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "measure": {"type": "string", "description": "Decreases expression"},
                    "line_number": {
                        "type": "integer",
                        "description": "Line number (1-indexed, optional)",
                    },
                    "context_before": {
                        "type": "string",
                        "description": "Line before insertion point (optional)",
                    },
                    "context_after": {
                        "type": "string",
                        "description": "Line after insertion point (optional)",
                    },
                },
                "required": ["measure"],
            },
        },
        {
            "name": "verify_dafny",
            "description": "Verify the current code state with all hints inserted so far. "
            "Returns verification results and full rendered code.",
            "input_schema": {
                "type": "object",
                "properties": {},  # No parameters - reads from state
            },
        },
    ]

    # Manual iteration loop - this is what generate() does automatically!
    for iteration in range(max_iterations):
        logger.debug(f"Iteration {iteration + 1}/{max_iterations}")

        try:
            # Call Anthropic API
            response = client.messages.create(
                model=model,
                max_tokens=8192,  # Increased to handle longer responses
                system=RAWDOG_SYSTEM_PROMPT,
                messages=messages,
                tools=tools,
            )
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            break

        # Add assistant response to message history
        assistant_message = {"role": "assistant", "content": response.content}
        messages.append(assistant_message)

        # Check stop reason
        if response.stop_reason == "end_turn":
            # No tool use - agent finished without calling tool
            logger.info("Agent ended turn without tool use")
            break

        if response.stop_reason != "tool_use":
            # Unexpected stop reason
            logger.warning(f"Unexpected stop reason: {response.stop_reason}")
            break

        # Process tool uses
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                tool_use_id = content_block.id

                # Route to appropriate tool
                if tool_name == "insert_invariant":
                    result = insert_invariant(
                        messages,
                        invariant=tool_input["invariant"],
                        line_number=tool_input.get("line_number"),
                        context_before=tool_input.get("context_before"),
                        context_after=tool_input.get("context_after"),
                    )
                    logger.info(f"Insert invariant: {result['message']}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result["message"],
                            "is_error": not result["success"],
                        }
                    )

                elif tool_name == "insert_assertion":
                    result = insert_assertion(
                        messages,
                        assertion=tool_input["assertion"],
                        line_number=tool_input.get("line_number"),
                        context_before=tool_input.get("context_before"),
                        context_after=tool_input.get("context_after"),
                    )
                    logger.info(f"Insert assertion: {result['message']}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result["message"],
                            "is_error": not result["success"],
                        }
                    )

                elif tool_name == "insert_precondition":
                    result = insert_precondition(
                        messages,
                        precondition=tool_input["precondition"],
                        line_number=tool_input.get("line_number"),
                        context_before=tool_input.get("context_before"),
                        context_after=tool_input.get("context_after"),
                    )
                    logger.info(f"Insert precondition: {result['message']}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result["message"],
                            "is_error": not result["success"],
                        }
                    )

                elif tool_name == "insert_postcondition":
                    result = insert_postcondition(
                        messages,
                        postcondition=tool_input["postcondition"],
                        line_number=tool_input.get("line_number"),
                        context_before=tool_input.get("context_before"),
                        context_after=tool_input.get("context_after"),
                    )
                    logger.info(f"Insert postcondition: {result['message']}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result["message"],
                            "is_error": not result["success"],
                        }
                    )

                elif tool_name == "insert_measure":
                    result = insert_measure(
                        messages,
                        measure=tool_input["measure"],
                        line_number=tool_input.get("line_number"),
                        context_before=tool_input.get("context_before"),
                        context_after=tool_input.get("context_after"),
                    )
                    logger.info(f"Insert measure: {result['message']}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result["message"],
                            "is_error": not result["success"],
                        }
                    )

                elif tool_name == "verify_dafny":
                    attempts += 1
                    result = verify_dafny(messages)

                    logger.info(
                        f"Attempt {attempts}: Verification {'succeeded' if result['success'] else 'failed'}"
                    )

                    # Save artifact with current code
                    if result.get("code"):
                        save_artifact(sample.test_id, attempts, result["code"])

                    if result["success"]:
                        # Verification succeeded!
                        success = True
                        final_code = result.get("code")
                        logger.info(f"Success after {attempts} attempts")

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result["message"],
                            }
                        )
                    else:
                        # Verification failed
                        logger.debug(
                            f"Verification failed: {result['message'][:100]}..."
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result["message"],
                                "is_error": True,
                            }
                        )

        # Add tool results as user message
        messages.append({"role": "user", "content": tool_results})

        # If verification succeeded, make one more API call to let model respond
        if success:
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=8192,
                    system=RAWDOG_SYSTEM_PROMPT,
                    messages=messages,
                    tools=tools,
                )
            except anthropic.APIError as e:
                logger.error(f"API error on final call: {e}")
            break

    # Get final code from state if we didn't get it from success
    if not success:
        final_code = get_code_state(messages)
        if final_code:
            # Run one final verification to get error details
            result = verify_dafny(messages)
            error_type = categorize_error(result.get("stderr", ""))
            logger.warning(f"Failed after {attempts} attempts: {error_type}")

    return AgentResult(
        sample_id=sample.test_id,
        success=success,
        attempts=attempts,
        final_code=final_code,
        error_type=error_type if not success else None,
    )
