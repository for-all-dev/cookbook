"""
DafnyBench evaluation using Inspect AI framework.

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

import re
import time
from typing import Any

from datasets import load_dataset
from inspect_ai import Task, task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ChatMessageUser, Model
from inspect_ai.scorer import Score, Target, accuracy, metric, scorer, stderr, Metric, Scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver, system_message
from inspect_ai.util import sandbox


# System prompt explaining Dafny verification
DAFNY_SYSTEM_PROMPT = """You are an expert in formal verification using Dafny.

Your task is to add verification hints to Dafny programs so they can be verified by the Dafny compiler.

## Verification Hints You Need to Add

1. **Loop Invariants** (`invariant`): Properties that hold before and after each loop iteration
2. **Assertions** (`assert`): Claims about the program state at specific points
3. **Preconditions** (`requires`): Conditions that must hold when a function is called
4. **Postconditions** (`ensures`): Conditions guaranteed to hold when a function returns
5. **Termination Measures** (`decreases`): Expressions that decrease on each recursive call or loop iteration

## Guidelines

- Loop invariants are critical for verifying loops - they must be:
  - True before the loop starts
  - Preserved by each iteration
  - Strong enough to prove the desired property after the loop

- Assertions can help break down complex proofs into smaller steps

- Preconditions and postconditions form the contract for functions

- Decreases clauses prove termination of loops and recursion

## Your Response

Provide the complete Dafny program with all necessary verification hints added.
Return ONLY the code, without markdown formatting or explanations.
"""


def load_dafnybench_dataset() -> list[Sample]:
    """
    Load the DafnyBench dataset from Hugging Face.

    Returns:
        List of Sample objects with input (hints_removed code) and target (ground_truth code).
    """
    hf_dataset = load_dataset("wendy-sun/DafnyBench", split="test")

    samples = []
    for row in hf_dataset:
        samples.append(
            Sample(
                input=f"Add verification hints to this Dafny code:\n\n{row['hints_removed']}",
                target=row["ground_truth"],
                metadata={
                    "test_id": row["test_ID"],
                    "test_file": row["test_file"],
                    "hints_removed": row["hints_removed"],
                    "ground_truth": row["ground_truth"],
                },
            )
        )

    return samples


def extract_code(completion: str) -> str:
    """
    Extract Dafny code from model completion, removing markdown formatting.

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
    """
    Categorize Dafny verification errors into types.

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


@solver
def dafny_solver(max_attempts: int | None = None) -> Solver:
    """
    Iterative repair solver that generates hints and retries with error feedback.

    Args:
        max_attempts: Maximum number of verification attempts (None = let Inspect AI decide naturally).

    Returns:
        Solver that implements iterative repair with error feedback.
    """
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        """
        Solve the task by iteratively generating hints and verifying.
        """
        # If max_attempts is None, just do a single generate and let Inspect handle iterations
        if max_attempts is None:
            state = await generate(state)
            state.metadata["attempts"] = 1
            return state

        attempts = 0

        for attempt in range(1, max_attempts + 1):
            attempts = attempt

            # Generate hints
            state = await generate(state)

            # Extract code from completion
            code = extract_code(state.output.completion)

            # Try verification (dry run - actual scoring happens in scorer)
            # We do this to provide error feedback for next attempt
            try:
                temp_file = f"/tmp/dafny_attempt_{state.metadata['test_id']}_{attempt}.dfy"
                await sandbox().write_file(temp_file, code)

                result = await sandbox().exec(
                    ["dafny", "verify", temp_file],
                    timeout=30,
                )

                # If verification succeeds, stop
                if result.returncode == 0 and "0 errors" in result.stdout:
                    state.metadata["attempts"] = attempts
                    state.metadata["success_on_attempt"] = attempt
                    break

                # If this isn't the last attempt, add error feedback
                if attempt < max_attempts:
                    error_output = result.stderr if result.stderr else result.stdout
                    state.messages.append(
                        ChatMessageUser(
                            content=f"Verification failed with the following error:\n\n{error_output}\n\n"
                                   f"Please fix the verification hints and try again. "
                                   f"Focus on the error message and adjust your invariants, assertions, "
                                   f"or other hints accordingly."
                        )
                    )
            except Exception as e:
                # If we can't verify (e.g., Dafny not installed), continue
                state.metadata["verification_error"] = str(e)
                break

        # Store final attempt count
        state.metadata["attempts"] = attempts

        return state

    return solve


@metric
def verification_time() -> Metric:
    """Metric to track average verification time per sample."""
    def metric_fn(scores: list[Score]) -> float:
        times = [
            s.metadata.get("verification_time", 0)
            for s in scores
            if "verification_time" in s.metadata
        ]
        return sum(times) / len(times) if times else 0.0

    return metric_fn


@metric
def avg_attempts() -> Metric:
    """Metric to track average number of attempts per sample."""
    def metric_fn(scores: list[Score]) -> float:
        attempts = [
            s.metadata.get("attempts", 0)
            for s in scores
            if "attempts" in s.metadata
        ]
        return sum(attempts) / len(attempts) if attempts else 0.0

    return metric_fn


@metric
def error_type_distribution() -> Metric:
    """Metric to show distribution of error types."""
    def metric_fn(scores: list[Score]) -> dict[str, int]:
        error_counts: dict[str, int] = {}
        for s in scores:
            error_type = s.metadata.get("error_type", "unknown")
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts

    return metric_fn


@scorer(metrics=[accuracy(), stderr(), verification_time(), avg_attempts(), error_type_distribution()])
def dafny_verifier() -> Scorer:
    """
    Score by running Dafny verification on the reconstructed program.

    Executes Dafny locally and scores based on verification success.
    Tracks comprehensive metrics including time, attempts, and error types.
    """
    async def score(state: TaskState, target: Target) -> Score:
        """
        Score the completion by verifying with Dafny.
        """
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
            error_type = "success" if success else categorize_error(
                result.stderr if result.stderr else result.stdout
            )

            # Prepare explanation
            if success:
                explanation = f"Verification succeeded in {verification_time_sec:.2f}s"
            else:
                error_output = result.stderr if result.stderr else result.stdout
                explanation = f"Verification failed ({error_type}):\n{error_output[:500]}"

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
    max_attempts: int | None = None,
    model: str | Model | None = None,
    sandbox: str = "local",
    limit: int | None = None,
) -> Task:
    """
    DafnyBench evaluation task.

    Evaluates language models on their ability to add verification hints
    to Dafny programs from the wendy-sun/DafnyBench dataset.

    Args:
        max_attempts: Maximum verification attempts with error feedback (None = natural iteration).
        model: Model to evaluate (default: from INSPECT_EVAL_MODEL env var).
        sandbox: Sandbox type - use "local" if Dafny is installed locally (default: "local").
        limit: Limit number of samples to evaluate (default: all 782 samples).

    Returns:
        Task configured for DafnyBench evaluation.

    Example:
        # Evaluate with natural iteration (default)
        inspect eval evals/dafnybench/inspect_ai.py

        # Evaluate with explicit max attempts
        inspect eval evals/dafnybench/inspect_ai.py -T max_attempts=3

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
            dafny_solver(max_attempts=max_attempts),
        ],
        scorer=dafny_verifier(),
        sandbox=sandbox,
    )


def run_dafnybench_eval(
    max_attempts: int | None = None,
    model: str | None = None,
    limit: int | None = None,
) -> None:
    """
    Run DafnyBench evaluation programmatically.

    This function is called by the CLI and runs the evaluation using Inspect AI's eval() function.

    Args:
        max_attempts: Maximum verification attempts with error feedback (None = natural iteration).
        model: Model to evaluate (uses INSPECT_EVAL_MODEL env var if None).
        limit: Limit number of samples to evaluate (None = all samples).
    """
    task_obj = dafnybench(
        max_attempts=max_attempts,
        model=model,
        limit=limit,
    )

    # Run the evaluation
    eval(
        tasks=task_obj,
        model=model,
    )
