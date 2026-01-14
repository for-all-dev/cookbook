"""Git operations using GitPython for mining the repository history."""

import logging
from collections.abc import Iterator
from pathlib import Path

from git import Commit, Repo
from git.exc import GitCommandError

logger = logging.getLogger(__name__)


def get_commit_iterator(repo_path: Path, start_ref: str = "master") -> Iterator[Commit]:
    """Iterate backwards through git history.

    Args:
        repo_path: Path to repository root.
        start_ref: Starting reference (branch/commit), defaults to "master".

    Yields:
        Commit objects in reverse chronological order.
    """
    repo = Repo(repo_path)
    yield from repo.iter_commits(start_ref)


def get_modified_files(commit: Commit) -> tuple[list[Path], list[Path]]:
    """Get files modified in a commit.

    Args:
        commit: The commit to analyze.

    Returns:
        Tuple of (current_files, parent_files) where:
        - current_files: List of modified file paths at commit
        - parent_files: List of file paths at parent (for comparison)
    """
    current_files = []
    parent_files = []

    # Get parent commit (use first parent for merge commits)
    if not commit.parents:
        # Initial commit - all files are "new"
        for item in commit.tree.traverse():
            if item.type == "blob" and item.path.endswith(".lean"):
                current_files.append(Path(item.path))
        return current_files, parent_files

    parent = commit.parents[0]

    # Get diffs between commit and parent
    diffs = parent.diff(commit)

    for diff in diffs:
        # Only consider .lean files
        if diff.a_path and diff.a_path.endswith(".lean"):
            current_files.append(Path(diff.a_path))
            parent_files.append(Path(diff.a_path))
        elif diff.b_path and diff.b_path.endswith(".lean"):
            current_files.append(Path(diff.b_path))
            if diff.a_path:
                parent_files.append(Path(diff.a_path))

    return current_files, parent_files


def safe_checkout(repo: Repo, commit_hash: str) -> bool:
    """Safely checkout a specific commit.

    Args:
        repo: Repository object.
        commit_hash: Commit hash to checkout.

    Returns:
        True if checkout successful, False otherwise.
    """
    try:
        repo.git.checkout(commit_hash, force=True)
        return True
    except GitCommandError as e:
        logger.error(f"Failed to checkout {commit_hash}: {e}")
        return False


def get_file_diff(repo: Repo, commit: Commit, file_path: Path) -> str:
    """Get git diff for a specific file between commit and parent.

    Args:
        repo: Repository object.
        commit: The commit to get diff for.
        file_path: Path to file (relative to repo root).

    Returns:
        Diff string, or empty string if no diff available.
    """
    if not commit.parents:
        # Initial commit - return full file content as "diff"
        try:
            blob = commit.tree / str(file_path)
            return blob.data_stream.read().decode("utf-8", errors="replace")
        except Exception:
            return ""

    parent = commit.parents[0]

    try:
        diff = repo.git.diff(parent.hexsha, commit.hexsha, "--", str(file_path))
        return diff
    except GitCommandError:
        return ""


def get_file_content_at_commit(
    repo: Repo, commit: Commit, file_path: Path
) -> str | None:
    """Get file content at a specific commit.

    Args:
        repo: Repository object.
        commit: The commit to get file from.
        file_path: Path to file (relative to repo root).

    Returns:
        File content as string, or None if file doesn't exist at that commit.
    """
    try:
        blob = commit.tree / str(file_path)
        return blob.data_stream.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def restore_file_from_parent(repo: Repo, commit: Commit, file_path: Path) -> bool:
    """Restore a file to its state at the parent commit.

    This checks out the file from the parent commit while keeping
    the rest of the working tree at the current commit.

    Args:
        repo: Repository object.
        commit: Current commit (file will be restored from its parent).
        file_path: Path to file (relative to repo root).

    Returns:
        True if restoration successful, False otherwise.
    """
    if not commit.parents:
        logger.warning(f"Cannot restore {file_path} - no parent commit")
        return False

    parent = commit.parents[0]

    try:
        repo.git.checkout(parent.hexsha, "--", str(file_path))
        return True
    except GitCommandError as e:
        logger.error(f"Failed to restore {file_path} from parent: {e}")
        return False
