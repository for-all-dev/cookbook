"""Data structures for plain DafnyBench implementation."""

from dataclasses import dataclass


@dataclass
class EvalSample:
    """Single evaluation sample from DafnyBench dataset."""

    test_id: str
    input: str  # Task prompt with code
    hints_removed: str  # Code with hints removed
    ground_truth: str  # Expected correct code


@dataclass
class AgentResult:
    """Result for a single sample evaluation."""

    sample_id: str
    success: bool
    attempts: int  # Number of verify_dafny calls
    final_code: str | None
    error_type: str | None  # Only if not success


@dataclass
class EvalMetrics:
    """Aggregated metrics across all samples."""

    total_samples: int
    successful: int
    accuracy: float  # successful / total_samples
    average_attempts: float
    error_distribution: dict[str, int]  # error_type -> count
