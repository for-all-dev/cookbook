"""Dataset loading for DafnyBench."""

from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class DafnyBenchSample:
    """Single sample from DafnyBench dataset.

    This is a framework-agnostic representation that can be converted
    to inspect_ai.Sample, rawdog EvalSample, or other formats.
    """

    test_id: str
    test_file: str
    hints_removed: str
    ground_truth: str


def load_dafnybench_dataset() -> list[DafnyBenchSample]:
    """Load the DafnyBench dataset from Hugging Face.

    Returns framework-agnostic DafnyBenchSample objects that can be
    converted to framework-specific formats (inspect_ai.Sample, etc).

    Returns:
        List of DafnyBenchSample objects with raw dataset fields.
    """
    hf_dataset = load_dataset("wendy-sun/DafnyBench", split="test")

    samples = [
        DafnyBenchSample(
            test_id=row["test_ID"],
            test_file=row["test_file"],
            hints_removed=row["hints_removed"],
            ground_truth=row["ground_truth"],
        )
        for row in hf_dataset
    ]

    return samples
