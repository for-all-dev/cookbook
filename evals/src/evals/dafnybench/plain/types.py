"""Type definitions and utilities for plain DafnyBench implementation."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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

    raise RuntimeError("Could not find workspace root (pyproject.toml with [tool.uv.workspace])")


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


def setup_logging() -> None:
    """Setup logging to logs/plain_YYYYMMDD_HHMMSS.log.

    Creates logs directory in workspace root if it doesn't exist and configures
    logging to write to both file and console.
    """
    workspace_root = get_workspace_root()
    logs_dir = workspace_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"plain_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),  # Also print to console
        ],
    )


def save_artifact(test_id: str, attempt: int, code: str, is_final: bool = False) -> None:
    """Save Dafny code artifact to artifacts/sample_<id>_attempt_<n>.dfy or _final.dfy.

    Args:
        test_id: Test identifier from dataset
        attempt: Attempt number (1-indexed)
        code: Dafny code to save
        is_final: If True, save as *_final.dfy (for successful verifications)

    Creates artifacts directory in workspace root if it doesn't exist.
    Sanitizes test_id for use in filename.
    """
    workspace_root = get_workspace_root()
    artifacts_dir = workspace_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # Sanitize test_id for filename
    safe_id = test_id.replace("/", "_").replace("\\", "_")

    if is_final:
        artifact_path = artifacts_dir / f"sample_{safe_id}_final.dfy"
    else:
        artifact_path = artifacts_dir / f"sample_{safe_id}_attempt_{attempt}.dfy"

    artifact_path.write_text(code)
