"""Dataset loading for FVAPPS."""

from datasets import load_dataset

from evals.fvapps.pydantic_ai.types import FVAPPSSample


def load_fvapps_dataset(split: str = "train") -> list[FVAPPSSample]:
    """Load FVAPPS dataset from quinn-dougherty/fvapps.

    Returns:
        List of FVAPPSSample objects with Lean code and unit tests.
    """
    hf_dataset = load_dataset("quinn-dougherty/fvapps", split=split)

    return [
        FVAPPSSample(
            apps_id=row["apps_id"],
            apps_question=row["apps_question"],
            spec=row["spec"],
            units=row["units"],
            sorries=row["sorries"],
            apps_difficulty=row.get("apps_difficulty"),
            assurance_level=row.get("assurance_level"),
        )
        for row in hf_dataset
    ]
