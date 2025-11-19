"""Custom metrics for DafnyBench evaluation."""

from inspect_ai.scorer import Score, Metric, metric


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
            s.metadata.get("attempts", 0) for s in scores if "attempts" in s.metadata
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
