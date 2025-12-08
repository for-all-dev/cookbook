"""Dataset conversion utilities for inspect_ai framework."""

from inspect_ai.dataset import Sample

from evals.dafnybench.common.dataset import DafnyBenchSample


def convert_to_inspect_samples(samples: list[DafnyBenchSample]) -> list[Sample]:
    """Convert DafnyBenchSample objects to inspect_ai Sample objects.

    Args:
        samples: List of framework-agnostic DafnyBenchSample objects

    Returns:
        List of inspect_ai Sample objects with input prompt and metadata
    """
    return [
        Sample(
            input=f"Add verification hints to this Dafny code:\n\n{sample.hints_removed}",
            metadata={
                "test_id": sample.test_id,
                "test_file": sample.test_file,
                "hints_removed": sample.hints_removed,
                "ground_truth": sample.ground_truth,
            },
        )
        for sample in samples
    ]
