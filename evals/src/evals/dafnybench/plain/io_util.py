"""I/O utilities for plain DafnyBench implementation."""

import json
import logging
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


def save_conversation_history(
    test_id: str,
    timestamp: str,
    messages: list[dict],
    system_prompt: str | None = None,
) -> None:
    """Save full conversation history to logs/plain_<timestamp>_<sample_id>.json.

    Args:
        test_id: Test identifier from dataset
        timestamp: Timestamp string (YYYYMMDD_HHMMSS format)
        messages: Full message history array from Anthropic API
        system_prompt: Optional system prompt to include in the conversation log

    Creates logs directory in workspace root if it doesn't exist.
    Sanitizes test_id for use in filename.
    """
    workspace_root = get_workspace_root()
    logs_dir = workspace_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Sanitize test_id for filename
    safe_id = test_id.replace("/", "_").replace("\\", "_")

    log_path = logs_dir / f"plain_{timestamp}_{safe_id}.json"

    # Build conversation object with system prompt and messages
    conversation = {
        "test_id": test_id,
        "timestamp": timestamp,
        "system_prompt": system_prompt,
        "messages": messages,
    }

    log_path.write_text(json.dumps(conversation, indent=2, default=str))
