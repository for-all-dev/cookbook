"""Dataset loading for DafnyBench."""

from datasets import load_dataset

from inspect_ai.dataset import Sample


def load_dafnybench_dataset() -> list[Sample]:
    """Load the DafnyBench dataset from Hugging Face.

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
