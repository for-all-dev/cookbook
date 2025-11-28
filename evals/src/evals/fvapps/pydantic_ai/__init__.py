"""Pydantic AI implementation of FVAPPS (Lean) evaluation."""

import logging

from evals.fvapps.pydantic_ai.agent import run_agent_on_sample
from evals.fvapps.pydantic_ai.dataset import load_fvapps_dataset
from evals.fvapps.pydantic_ai.types import AgentResult, EvalMetrics, setup_logging


def aggregate_results(results: list[AgentResult]) -> EvalMetrics:
    """Aggregate results into metrics.

    Args:
        results: List of AgentResult objects

    Returns:
        EvalMetrics with accuracy and error distribution
    """
    total = len(results)
    successful = sum(1 for r in results if r.success)
    accuracy = successful / total if total > 0 else 0.0

    total_attempts = sum(r.attempts for r in results)
    average_attempts = total_attempts / total if total > 0 else 0.0

    # Error distribution (only failed samples)
    error_distribution: dict[str, int] = {}
    for r in results:
        if not r.success and r.error_type:
            error_distribution[r.error_type] = error_distribution.get(r.error_type, 0) + 1

    return EvalMetrics(
        total_samples=total,
        successful=successful,
        accuracy=accuracy,
        average_attempts=average_attempts,
        error_distribution=error_distribution,
    )


def run_fvapps_eval(model: str, limit: int | None) -> None:
    """Run FVAPPS evaluation with Pydantic AI.

    This function:
    1. Sets up logging and loads the dataset
    2. Runs the pydantic-ai agent on each sample
    3. Aggregates results and prints summary statistics

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5")
        limit: Max samples to evaluate (None = all samples)
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Load dataset
    dataset = load_fvapps_dataset()
    if limit:
        dataset = dataset[:limit]

    print(f"Evaluating {len(dataset)} samples with {model}...")
    logger.info(f"Starting evaluation: {len(dataset)} samples, model={model}")

    # Run evaluation
    results = []
    for i, sample in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] Evaluating {sample.apps_id}...")

        result = run_agent_on_sample(sample, model=model)
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
