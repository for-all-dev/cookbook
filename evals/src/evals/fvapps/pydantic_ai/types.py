"""Type definitions and utilities for FVAPPS pydantic-ai implementation."""

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


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

    Creates logs directory if it doesn't exist and configures logging
    to write to both file and console.
    """
    logs_dir = Path("logs")
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
