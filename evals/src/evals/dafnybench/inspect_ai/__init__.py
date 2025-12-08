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

import tempfile

from evals.dafnybench.common.dataset import load_dafnybench_dataset
from evals.dafnybench.inspect_ai.dataset import convert_to_inspect_samples
from evals.dafnybench.inspect_ai.prompt import DAFNY_SYSTEM_PROMPT
from evals.dafnybench.inspect_ai.tools import verify_dafny
from evals.dafnybench.inspect_ai.utils import (
    ExtractionStrategy,
    categorize_error,
    extract_code,
)

from inspect_ai import Task, eval, task
from inspect_ai.model import Model
from inspect_ai.scorer import Score, Scorer, accuracy, scorer, stderr
from inspect_ai.solver import TaskState, generate, system_message, use_tools
from inspect_ai.util import sandbox


@scorer(metrics=[accuracy(), stderr()])
def dafny_verifier() -> Scorer:
    """Score by running Dafny verification on the reconstructed program.

    Executes Dafny locally and scores based on verification success.
    """

    async def score(state: TaskState) -> Score:
        """Score the completion by verifying with Dafny."""
        # Get extraction strategy from metadata (default: v1)
        strategy = state.metadata.get("extraction_strategy", "v1")

        # Extract code using the specified strategy
        code = extract_code(state, strategy=strategy)

        # Use context manager for automatic cleanup
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dfy", delete=True) as tmp:
            temp_path = tmp.name

            try:
                # Write code to temporary file
                await sandbox().write_file(temp_path, code)

                # Run Dafny verification
                result = await sandbox().exec(
                    ["dafny", "verify", temp_path],
                    timeout=30,
                )

                # Check for successful verification
                success = result.returncode == 0 and "0 errors" in result.stdout

                # Prepare explanation
                if success:
                    explanation = "Verification succeeded"
                else:
                    error_output = result.stderr if result.stderr else result.stdout
                    error_type = categorize_error(error_output)
                    explanation = (
                        f"Verification failed ({error_type}):\n{error_output[:500]}"
                    )

                return Score(
                    value="C" if success else "I",
                    answer=code,
                    explanation=explanation,
                )

            except TimeoutError:
                return Score(
                    value="I",
                    answer=code,
                    explanation="Verification timed out after 30 seconds",
                )
            except Exception as e:
                return Score(
                    value="I",
                    answer=code,
                    explanation=f"Error during verification: {str(e)}",
                )

    return score  # type: ignore


@task
def dafnybench(
    model: str | Model | None = None,
    sandbox: str = "local",
    limit: int | None = None,
    extraction_strategy: ExtractionStrategy = ExtractionStrategy.V1,
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
        extraction_strategy: Code extraction strategy - ExtractionStrategy.V1 (buggy) or V2 (fixed).

    Returns:
        Task configured for DafnyBench evaluation.

    Example:
        # Evaluate with natural tool-based iteration (default)
        inspect eval evals/dafnybench/inspect_ai.py

        # Evaluate specific model
        inspect eval evals/dafnybench/inspect_ai.py -M anthropic/claude-3-5-sonnet-20241022
    """
    # Load framework-agnostic dataset and convert to inspect_ai format
    common_dataset = load_dafnybench_dataset()
    if limit is not None:
        common_dataset = common_dataset[:limit]

    dataset = convert_to_inspect_samples(common_dataset)

    # Add extraction strategy to each sample's metadata (store the value string)
    for sample in dataset:
        if sample.metadata is None:
            sample.metadata = {}
        sample.metadata["extraction_strategy"] = extraction_strategy.value

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
    extraction_strategy: ExtractionStrategy = ExtractionStrategy.V1,
) -> None:
    """Run DafnyBench evaluation programmatically.

    This function is called by the CLI and runs the evaluation using Inspect AI's eval() function.
    The agent naturally handles iteration using the verify_dafny tool.

    Args:
        model: Model to evaluate (uses INSPECT_EVAL_MODEL env var if None).
        limit: Limit number of samples to evaluate (None = all samples).
        extraction_strategy: Code extraction strategy - ExtractionStrategy.V1 (buggy) or V2 (fixed).
    """
    task_obj = dafnybench(
        model=model,
        limit=limit,
        extraction_strategy=extraction_strategy,
    )

    # Run the evaluation
    eval(
        tasks=task_obj,
        model=model,
    )
