"""JSONL output generation for proof repair challenges."""

import json
import logging
from pathlib import Path

from evals.dalek_history.structures import Challenge

logger = logging.getLogger(__name__)


def format_challenge_jsonl(challenge: Challenge) -> dict:
    """Convert Challenge to JSONL schema.

    Output schema matches the specification in CLAUDE.md:
    {
      "task_id": "commit_hash_file_name",
      "metadata": {
        "original_commit": "hash",
        "commit_message": "...",
        "author": "...",
        "date": "...",
        "author_fix_diff": "git_diff_string",
        "error_message": "stderr_from_lake_build",
        "definition_files": [...],
        "proof_file": "..."
      },
      "setup": {
        "instructions": "The definitions in [File X] have changed...",
        "codebase_state": {...}
      },
      "verification": {
        "command": "lake build [TargetFile]",
        "expected_output": "Success",
        "timeout_seconds": 300
      }
    }

    Args:
        challenge: Challenge object to convert.

    Returns:
        Dictionary in JSONL format.
    """
    # Generate instruction text
    def_files_str = ", ".join(str(f) for f in challenge.definition_files)
    instructions = (
        f"The definitions in {def_files_str} have changed, "
        f"breaking the proof in {challenge.proof_file}. "
        "Update the proof to restore verification."
    )

    return {
        "task_id": challenge.task_id,
        "metadata": {
            "original_commit": challenge.commit_hash,
            "author_fix_diff": challenge.author_fix_diff,
            "error_message": challenge.error_message,
            "definition_files": [str(f) for f in challenge.definition_files],
            "proof_file": str(challenge.proof_file),
        },
        "setup": {
            "instructions": instructions,
            "codebase_state": challenge.codebase_snapshot,
        },
        "verification": {
            "command": challenge.verification_command,
            "expected_output": "Success",
            "timeout_seconds": 300,
        },
    }


def write_challenges(challenges: list[Challenge], output_path: Path) -> None:
    """Write challenges to JSONL file.

    Each challenge is written as one line of JSON.

    Args:
        challenges: List of challenges to write.
        output_path: Path to output JSONL file.
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Writing {len(challenges)} challenges to {output_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        for challenge in challenges:
            jsonl_obj = format_challenge_jsonl(challenge)
            json_line = json.dumps(jsonl_obj, ensure_ascii=False)
            f.write(json_line + "\n")

    logger.info(f"Successfully wrote {len(challenges)} challenges")


def read_challenges(input_path: Path) -> list[dict]:
    """Read challenges from JSONL file.

    Args:
        input_path: Path to JSONL file.

    Returns:
        List of challenge dictionaries.
    """
    challenges = []

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                challenges.append(json.loads(line))

    return challenges
