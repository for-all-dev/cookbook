"""Pure Anthropic SDK implementation of DafnyBench evaluation.

This module implements the DafnyBench evaluation using only the Anthropic SDK,
demonstrating what inspect-ai abstracts away with its generate() function.

The "rawdog" approach shows the manual tool-calling loop, message management,
and iteration control that frameworks handle automatically.
"""

import logging

from evals.dafnybench.inspect_ai.dataset import load_dafnybench_dataset
from evals.dafnybench.rawdog.agent import run_agent
from evals.dafnybench.rawdog.metrics import aggregate_results
from evals.dafnybench.rawdog.types import EvalSample, setup_logging


def run_dafnybench_rawdog(model: str, limit: int | None) -> None:
    """Run DafnyBench evaluation with pure Anthropic SDK.

    This function demonstrates the complete evaluation flow without using
    inspect-ai framework abstractions. It:
    1. Sets up logging and loads the dataset
    2. Runs the agent on each sample with manual tool-calling loop
    3. Aggregates results and prints summary statistics

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5")
        limit: Max samples to evaluate (None = all 782 samples)
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Load dataset
    dataset = load_dafnybench_dataset()
    if limit:
        dataset = dataset[:limit]

    print(f"Evaluating {len(dataset)} samples with {model}...")
    logger.info(f"Starting evaluation: {len(dataset)} samples, model={model}")

    # Convert to EvalSample format
    samples = [
        EvalSample(
            test_id=s.metadata["test_id"],
            input=s.input,
            hints_removed=s.metadata["hints_removed"],
            ground_truth=s.metadata["ground_truth"],
        )
        for s in dataset
    ]

    # Run evaluation
    results = []
    for i, sample in enumerate(samples, 1):
        print(f"[{i}/{len(samples)}] Evaluating {sample.test_id}...")

        result = run_agent(sample, model=model)
        results.append(result)

        status = "✓" if result.success else "✗"
        print(f"  {status} {result.attempts} attempts")

    # Aggregate metrics
    metrics = aggregate_results(results)
    logger.info(f"Evaluation complete: {metrics.accuracy:.1%} accuracy")

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total samples:     {metrics.total_samples}")
    print(f"Successful:        {metrics.successful}")
    print(f"Accuracy:          {metrics.accuracy:.1%}")
    print(f"Average attempts:  {metrics.average_attempts:.2f}")

    if metrics.error_distribution:
        print("\nError distribution:")
        for error_type, count in sorted(metrics.error_distribution.items()):
            print(f"  {error_type}: {count}")
