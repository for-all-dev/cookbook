"""Manual tool-calling loop for rawdog DafnyBench implementation.

This module demonstrates what inspect-ai's generate() abstracts away by
implementing the tool-calling loop manually with the Anthropic SDK.
"""

import logging

import anthropic
from evals.dafnybench.inspect_ai.prompt import DAFNY_SYSTEM_PROMPT
from evals.dafnybench.inspect_ai.utils import categorize_error
from evals.dafnybench.rawdog.tools import verify_dafny
from evals.dafnybench.rawdog.types import AgentResult, EvalSample, save_artifact


def run_agent(sample: EvalSample, model: str, max_iterations: int = 20) -> AgentResult:
    """Run agent on a single sample with manual tool-calling loop.

    This function implements the core tool-calling loop that inspect-ai's
    generate() handles automatically. It demonstrates:
    - Manual message history management
    - Anthropic API integration with tools
    - Tool execution and result handling
    - Iteration control and stopping conditions

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

    # Initialize message history
    messages = [{"role": "user", "content": sample.input}]

    # Track metrics
    attempts = 0
    success = False
    final_code = None
    error_type = None
    last_code = None  # Track last code passed to tool

    # Setup logging for this sample
    logger = logging.getLogger(__name__)
    logger.info(f"Starting evaluation for sample {sample.test_id}")

    # Tool definition (Anthropic API format)
    tools = [
        {
            "name": "verify_dafny",
            "description": "Verify Dafny code and return verification results. "
            "Pass your complete Dafny program to check if verification succeeds. "
            "If verification fails, detailed error messages are returned for analysis and retry.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Complete Dafny program with verification hints added",
                    }
                },
                "required": ["code"],
            },
        }
    ]

    # Manual iteration loop - this is what generate() does automatically!
    for iteration in range(max_iterations):
        logger.debug(f"Iteration {iteration + 1}/{max_iterations}")

        try:
            # Call Anthropic API
            response = client.messages.create(
                model=model,
                max_tokens=8192,  # Increased to handle longer responses
                system=DAFNY_SYSTEM_PROMPT,
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
            # Use last_code if we have it
            if last_code:
                final_code = last_code
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

                if tool_name == "verify_dafny":
                    attempts += 1
                    code = tool_input["code"]
                    last_code = code  # Track for final extraction

                    # Log and save artifact
                    logger.info(
                        f"Attempt {attempts}: Verifying code ({len(code)} chars)"
                    )
                    save_artifact(sample.test_id, attempts, code)

                    # Execute tool
                    result = verify_dafny(code)

                    if result["success"]:
                        # Verification succeeded!
                        success = True
                        final_code = code
                        logger.info(f"Success after {attempts} attempts")

                        # Add tool result to message history
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result["message"],
                            }
                        )

                    else:
                        # Verification failed - return error for agent to retry
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
                    max_tokens=8192,  # Increased to handle longer responses
                    system=DAFNY_SYSTEM_PROMPT,
                    messages=messages,
                    tools=tools,
                )
            except anthropic.APIError as e:
                logger.error(f"API error on final call: {e}")
            break

    # Use last_code if we didn't get final_code from success
    if not success and last_code:
        final_code = last_code
        # Run one final verification to get error details
        result = verify_dafny(final_code)
        error_type = categorize_error(result.get("stderr", ""))
        logger.warning(f"Failed after {attempts} attempts: {error_type}")

    return AgentResult(
        sample_id=sample.test_id,
        success=success,
        attempts=attempts,
        final_code=final_code,
        error_type=error_type if not success else None,
    )
