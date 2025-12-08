"""Manual tool-calling loop for plain DafnyBench implementation.

This module demonstrates what inspect-ai's generate() abstracts away by
implementing the tool-calling loop manually with the Anthropic SDK.

This version uses specialized insertion tools instead of having the agent
regenerate complete files.
"""

import logging
from datetime import datetime

import anthropic
from evals.dafnybench.inspect_ai.utils import categorize_error
from evals.dafnybench.plain.config import get_config
from evals.dafnybench.plain.io_util import save_artifact, save_conversation_history
from evals.dafnybench.plain.structures import AgentResult, EvalSample
from evals.dafnybench.plain.tools import (
    TOOLS,
    get_code_state,
    insert_assertion,
    insert_invariant,
    insert_measure,
    insert_postcondition,
    insert_precondition,
    update_code_state,
    verify_dafny,
)


def run_agent(
    sample: EvalSample, model: str, max_iterations: int | None = None
) -> AgentResult:
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
        max_iterations: Maximum number of tool-calling iterations (None = use config)

    Returns:
        AgentResult with success status, attempts, final code, and error type
    """
    # Load configuration
    config = get_config()

    # Use config defaults if not specified
    if max_iterations is None:
        max_iterations = config.evaluation.max_iterations

    # Generate timestamp for logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize Anthropic client
    client = anthropic.Anthropic()

    # Strip "anthropic/" prefix from model name if present (inspect-ai format)
    if model.startswith("anthropic/"):
        model = model.replace("anthropic/", "")

    # Initialize message history with code state (using template from config)
    initial_state = config.prompt.initial_state_template.format(
        code=sample.hints_removed
    )

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

    # Manual iteration loop - this is what generate() does automatically!
    for iteration in range(max_iterations):
        logger.debug(f"Iteration {iteration + 1}/{max_iterations}")

        try:
            # Call Anthropic API
            response = client.messages.create(
                model=model,
                max_tokens=config.evaluation.max_tokens,
                system=config.prompt.system_prompt,
                messages=messages,
                tools=TOOLS,
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
        latest_code = None  # Track latest code state from insertions

        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                tool_use_id = content_block.id

                # Route to appropriate tool using pattern matching
                match tool_name:
                    case "insert_invariant":
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
                        # Track latest code for cumulative updates
                        if result["success"] and result.get("code"):
                            latest_code = result["code"]

                    case "insert_assertion":
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
                        if result["success"] and result.get("code"):
                            latest_code = result["code"]

                    case "insert_precondition":
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
                        if result["success"] and result.get("code"):
                            latest_code = result["code"]

                    case "insert_postcondition":
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
                        if result["success"] and result.get("code"):
                            latest_code = result["code"]

                    case "insert_measure":
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
                        if result["success"] and result.get("code"):
                            latest_code = result["code"]

                    case "verify_dafny":
                        attempts += 1
                        result = verify_dafny(messages)

                        logger.info(
                            f"Attempt {attempts}: Verification {'succeeded' if result['success'] else 'failed'}"
                        )

                        # Save artifact with current code
                        if result.get("code"):
                            save_artifact(
                                sample.test_id,
                                attempts,
                                result["code"],
                                is_final=result["success"],
                            )

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

        # Add tool results as user message (BEFORE state update to maintain pairing)
        messages.append({"role": "user", "content": tool_results})

        # Update code state AFTER tool_results to maintain proper Anthropic message pairing
        # Note: This means multiple insertions in one turn are NOT cumulative - agent must
        # call verify_dafny or make multiple turns to see cumulative effects
        if latest_code is not None:
            update_code_state(messages, latest_code)

        # If verification succeeded, make one more API call to let model respond
        if success:
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=config.evaluation.max_tokens,
                    system=config.prompt.system_prompt,
                    messages=messages,
                    tools=TOOLS,
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

    # Save full conversation history to JSON
    save_conversation_history(
        test_id=sample.test_id,
        timestamp=timestamp,
        messages=messages,
        system_prompt=config.prompt.system_prompt,
    )

    return AgentResult(
        sample_id=sample.test_id,
        success=success,
        attempts=attempts,
        final_code=final_code,
        error_type=error_type if not success else None,
    )
