"""DafnyBench evaluation using Inspect AI framework.

This module implements an evaluation task for the DafnyBench dataset
(wendy-sun/DafnyBench on Hugging Face), which tests language models'
ability to add verification hints to Dafny programs.

Task: Given Dafny code with verification hints removed, generate the
missing hints (assertions, loop invariants, pre/postconditions, etc.)
such that the program can be successfully verified by the Dafny compiler.

Usage:
    uv run solve dafnybench --framework inspect

Requirements:
    - Dafny compiler must be installed and available as `dafny` command
    - Install via: https://github.com/dafny-lang/dafny/releases
"""

import time

from evals.dafnybench.inspect_ai.dataset import load_dafnybench_dataset
from evals.dafnybench.inspect_ai.metrics import (
    avg_attempts,
    error_type_distribution,
    verification_time,
)
from evals.dafnybench.inspect_ai.prompt import DAFNY_SYSTEM_PROMPT
from evals.dafnybench.inspect_ai.tools import verify_dafny
from evals.dafnybench.inspect_ai.utils import categorize_error, extract_code

from inspect_ai import Task, eval, task
from inspect_ai.model import Model
from inspect_ai.scorer import Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState, generate, system_message, use_tools
from inspect_ai.util import sandbox


@scorer(
    metrics=[
        accuracy(),
        stderr(),
        verification_time(),
        avg_attempts(),
        error_type_distribution(),
    ]
)
def dafny_verifier() -> Scorer:
    """Score by running Dafny verification on the reconstructed program.

    Executes Dafny locally and scores based on verification success.
    Tracks comprehensive metrics including time, attempts, and error types.
    """

    async def score(state: TaskState, target: Target) -> Score:
        """Score the completion by verifying with Dafny."""
        start_time = time.time()

        # Extract code from completion
        code = extract_code(state.output.completion)

        # Get test ID for unique file naming
        test_id = state.metadata.get("test_id", "unknown")
        test_file = f"/tmp/dafny_eval_{test_id}.dfy"

        try:
            # Write code to temporary file
            await sandbox().write_file(test_file, code)

            # Run Dafny verification
            result = await sandbox().exec(
                ["dafny", "verify", test_file],
                timeout=30,
            )

            verification_time_sec = time.time() - start_time

            # Check for successful verification
            success = result.returncode == 0 and "0 errors" in result.stdout

            # Determine error type if failed
            error_type = (
                "success"
                if success
                else categorize_error(result.stderr if result.stderr else result.stdout)
            )

            # Prepare explanation
            if success:
                explanation = f"Verification succeeded in {verification_time_sec:.2f}s"
            else:
                error_output = result.stderr if result.stderr else result.stdout
                explanation = (
                    f"Verification failed ({error_type}):\n{error_output[:500]}"
                )

            return Score(
                value="C" if success else "I",
                answer=code,
                explanation=explanation,
                metadata={
                    "verification_time": verification_time_sec,
                    "error_type": error_type,
                    "attempts": state.metadata.get("attempts", 1),
                    "success_on_attempt": state.metadata.get("success_on_attempt"),
                    "test_id": test_id,
                    "test_file": state.metadata.get("test_file", ""),
                    "dafny_stdout": result.stdout[:1000] if not success else "",
                    "dafny_stderr": result.stderr[:1000] if not success else "",
                },
            )

        except TimeoutError:
            return Score(
                value="I",
                answer=code,
                explanation="Verification timed out after 30 seconds",
                metadata={
                    "verification_time": 30.0,
                    "error_type": "timeout",
                    "attempts": state.metadata.get("attempts", 1),
                    "test_id": test_id,
                },
            )
        except Exception as e:
            return Score(
                value="I",
                answer=code,
                explanation=f"Error during verification: {str(e)}",
                metadata={
                    "verification_time": time.time() - start_time,
                    "error_type": "execution_error",
                    "attempts": state.metadata.get("attempts", 1),
                    "test_id": test_id,
                    "error_message": str(e),
                },
            )

    return score


@task
def dafnybench(
    model: str | Model | None = None,
    sandbox: str = "local",
    limit: int | None = None,
) -> Task:
    """DafnyBench evaluation task.

    Evaluates language models on their ability to add verification hints
    to Dafny programs from the wendy-sun/DafnyBench dataset.

    The task uses a tool-based approach where the agent has access to a verify_dafny
    tool. The agent naturally iterates by calling the tool, receiving feedback, and
    refining its approach until verification succeeds.

    Args:
        model: Model to evaluate (default: from INSPECT_EVAL_MODEL env var).
        sandbox: Sandbox type - use "local" if Dafny is installed locally (default: "local").
        limit: Limit number of samples to evaluate (default: all 782 samples).

    Returns:
        Task configured for DafnyBench evaluation.

    Example:
        # Evaluate with natural tool-based iteration (default)
        inspect eval evals/dafnybench/inspect_ai.py

        # Evaluate specific model
        inspect eval evals/dafnybench/inspect_ai.py -M anthropic/claude-3-5-sonnet-20241022
    """
    dataset = load_dafnybench_dataset()
    if limit is not None:
        dataset = dataset[:limit]

    return Task(
        dataset=dataset,
        solver=[
            system_message(DAFNY_SYSTEM_PROMPT),
            use_tools(verify_dafny()),
            generate(),  # Handles tool loop automatically
        ],
        scorer=dafny_verifier(),
        sandbox=sandbox,
    )


def run_dafnybench_eval(
    model: str | None = None,
    limit: int | None = None,
) -> None:
    """Run DafnyBench evaluation programmatically.

    This function is called by the CLI and runs the evaluation using Inspect AI's eval() function.
    The agent naturally handles iteration using the verify_dafny tool.

    Args:
        model: Model to evaluate (uses INSPECT_EVAL_MODEL env var if None).
        limit: Limit number of samples to evaluate (None = all samples).
    """
    task_obj = dafnybench(
        model=model,
        limit=limit,
    )

    # Run the evaluation
    eval(
        tasks=task_obj,
        model=model,
    )
