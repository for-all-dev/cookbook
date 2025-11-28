"""Result aggregation and metrics for rawdog DafnyBench implementation."""

from evals.dafnybench.rawdog.types import AgentResult, EvalMetrics


def aggregate_results(results: list[AgentResult]) -> EvalMetrics:
    """Aggregate individual sample results into overall metrics.

    Args:
        results: List of agent results for each sample

    Returns:
        EvalMetrics with aggregated statistics including accuracy,
        average attempts, and error distribution
    """
    total_samples = len(results)
    successful = sum(1 for r in results if r.success)

    # Calculate accuracy
    accuracy = successful / total_samples if total_samples > 0 else 0.0

    # Calculate average attempts (only for samples that attempted)
    total_attempts = sum(r.attempts for r in results)
    average_attempts = total_attempts / total_samples if total_samples > 0 else 0.0

    # Build error distribution (only for failed samples)
    error_distribution: dict[str, int] = {}
    for result in results:
        if not result.success and result.error_type:
            error_distribution[result.error_type] = (
                error_distribution.get(result.error_type, 0) + 1
            )

    return EvalMetrics(
        total_samples=total_samples,
        successful=successful,
        accuracy=accuracy,
        average_attempts=average_attempts,
        error_distribution=error_distribution,
    )
