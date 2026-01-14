"""Metrics and reporting for mining results."""

import logging

from evals.dalek_history.structures import CommitCandidate, MiningResult

logger = logging.getLogger(__name__)


def print_candidates(candidates: list[CommitCandidate]) -> None:
    """Print summary of candidate commits (for dry-run mode).

    Args:
        candidates: List of candidate commits found.
    """
    print("\n" + "=" * 70)
    print("CANDIDATE COMMITS")
    print("=" * 70)

    for i, candidate in enumerate(candidates, 1):
        print(f"\n[{i}] {candidate.commit_hash[:8]} - {candidate.commit_message[:60]}")
        print(f"    Author: {candidate.author}")
        print(f"    Date: {candidate.date}")
        print(f"    Definition files ({len(candidate.definition_files)}):")
        for df in candidate.definition_files[:3]:  # Show first 3
            print(f"      - {df}")
        if len(candidate.definition_files) > 3:
            print(f"      ... and {len(candidate.definition_files) - 3} more")
        print(f"    Proof files ({len(candidate.proof_files)}):")
        for pf in candidate.proof_files[:3]:  # Show first 3
            print(f"      - {pf}")
        if len(candidate.proof_files) > 3:
            print(f"      ... and {len(candidate.proof_files) - 3} more")

    print("\n" + "=" * 70)
    print(f"Total candidates: {len(candidates)}")
    print("=" * 70)


def print_mining_summary(result: MiningResult) -> None:
    """Print summary of mining results.

    Args:
        result: Mining result with statistics.
    """
    print("\n" + "=" * 70)
    print("MINING SUMMARY")
    print("=" * 70)

    print(f"Commits analyzed:     {result.total_commits}")
    print(f"Candidates found:     {result.candidates}")
    print(f"Valid challenges:     {result.valid_challenges}")

    if result.candidates > 0:
        success_rate = (result.valid_challenges / result.candidates) * 100
        print(f"Success rate:         {success_rate:.1f}%")

    if result.skipped_reasons:
        print("\nSkipped reasons:")
        for reason, count in sorted(
            result.skipped_reasons.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {reason:25s} {count:4d}")

    print("=" * 70)

    # Log detailed statistics
    logger.info(f"Mining completed: {result.valid_challenges} challenges extracted")
    logger.info(f"Total commits: {result.total_commits}")
    logger.info(f"Candidates: {result.candidates}")
    logger.info(f"Skipped reasons: {result.skipped_reasons}")


def format_progress(current: int, total: int, message: str) -> str:
    """Format a progress message.

    Args:
        current: Current item number.
        total: Total items.
        message: Progress message.

    Returns:
        Formatted string like "[5/100] Processing commit abc123..."
    """
    return f"[{current}/{total}] {message}"
