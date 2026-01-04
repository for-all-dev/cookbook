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
            apps_id=row["apps_id"],  # type: ignore
            apps_question=row["apps_question"],  # type: ignore
            spec=row["spec"],  # type: ignore
            units=row["units"],  # type: ignore
            sorries=row["sorries"],  # type: ignore
            apps_difficulty=row.get("apps_difficulty"),  # type: ignore
            assurance_level=row.get("assurance_level"),  # type: ignore
        )
        for row in hf_dataset  # type: ignore
    ]
