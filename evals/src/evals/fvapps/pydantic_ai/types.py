"""Type definitions and utilities for FVAPPS pydantic-ai implementation."""

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


def get_workspace_root() -> Path:
    """Find the workspace root by looking for the root pyproject.toml.

    Returns:
        Path to the workspace root directory

    Raises:
        RuntimeError: If workspace root cannot be found
    """
    current = Path(__file__).resolve()

    # Walk up the directory tree looking for workspace root
    for parent in current.parents:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            # Check if this is the root (has [tool.uv.workspace])
            content = pyproject.read_text()
            if "[tool.uv.workspace]" in content:
                return parent

    raise RuntimeError(
        "Could not find workspace root (pyproject.toml with [tool.uv.workspace])"
    )


class FVAPPSSample(BaseModel):
    """Single sample from quinn-dougherty/fvapps dataset."""

    apps_id: str
    apps_question: str  # Natural language description
    spec: str  # Lean code with sorry placeholders
    units: str  # Unit tests (#guard_msgs, #eval)
    sorries: int  # Number of sorry placeholders
    apps_difficulty: str | None = None
    assurance_level: str | None = None


class AgentResult(BaseModel):
    """Result for a single sample evaluation."""

    sample_id: str
    success: bool
    attempts: int  # Number of verify_lean calls
    final_code: str | None
    error_type: str | None  # Only if not success


class EvalMetrics(BaseModel):
    """Aggregated metrics across all samples."""

    total_samples: int
    successful: int
    accuracy: float  # successful / total_samples
    average_attempts: float
    error_distribution: dict[str, int]  # error_type -> count


def setup_logging() -> None:
    """Setup logging to logs/fvapps_pydantic_YYYYMMDD_HHMMSS.log.

    Creates logs directory in workspace root if it doesn't exist and configures
    logging to write to both file and console.
    """
    workspace_root = get_workspace_root()
    logs_dir = workspace_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"fvapps_pydantic_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),  # Also print to console
        ],
    )
