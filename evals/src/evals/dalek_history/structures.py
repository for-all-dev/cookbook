"""Data structures for the dalek history mining pipeline."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CommitCandidate:
    """A commit that modifies both definition and proof files."""

    commit_hash: str
    commit_message: str
    author: str
    date: datetime
    definition_files: list[Path]
    proof_files: list[Path]


@dataclass
class VerificationResult:
    """Result from a Lake build attempt."""

    success: bool
    stdout: str
    stderr: str
    error_message: str | None
    timeout: bool


@dataclass
class Challenge:
    """A valid proof repair challenge extracted from git history."""

    task_id: str  # Format: "{commit_hash}_{file_name}"
    commit_hash: str
    proof_file: Path
    definition_files: list[Path]
    author_fix_diff: str
    error_message: str
    codebase_snapshot: dict[str, str]  # file_path -> content
    verification_command: str


@dataclass
class MiningResult:
    """Overall statistics from the mining process."""

    total_commits: int
    candidates: int
    valid_challenges: int
    challenges: list[Challenge]
    skipped_reasons: dict[str, int]  # reason -> count
