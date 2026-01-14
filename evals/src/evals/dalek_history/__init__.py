"""Dalek history proof repair mining pipeline.

This module extracts proof repair challenges from the curve25519-dalek-lean-verify
git history by identifying commits where definition changes broke existing proofs.
"""

import logging
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from evals.dalek_history.config import Config, setup_logging
from evals.dalek_history.file_classifier import classify_file, should_exclude_path
from evals.dalek_history.git_ops import (
    get_commit_iterator,
    get_file_diff,
    get_modified_files,
    restore_file_from_parent,
    safe_checkout,
)
from evals.dalek_history.jsonl_writer import write_challenges
from evals.dalek_history.metrics import (
    format_progress,
    print_candidates,
    print_mining_summary,
)
from evals.dalek_history.snapshot import capture_codebase_snapshot
from evals.dalek_history.structures import Challenge, CommitCandidate, MiningResult
from evals.dalek_history.verification import is_verification_error, run_lake_build

logger = logging.getLogger(__name__)


def identify_candidates(repo: Repo, config: Config) -> list[CommitCandidate]:
    """Phase A: Identify commits that modify both definitions and proofs.

    Args:
        repo: GitPython repository object.
        config: Configuration object.

    Returns:
        List of candidate commits.
    """
    candidates = []
    processed = 0

    logger.info("Phase A: Identifying candidate commits")

    for commit in get_commit_iterator(
        Path(repo.working_dir), config.mining.start_ref
    ):
        processed += 1

        # Check max_commits limit
        if config.mining.max_commits > 0 and processed > config.mining.max_commits:
            logger.info(f"Reached max_commits limit ({config.mining.max_commits})")
            break

        if processed % 10 == 0:
            logger.info(f"Processed {processed} commits, found {len(candidates)} candidates")

        # Get modified files
        current_files, _ = get_modified_files(commit)

        # Filter out excluded paths
        current_files = [
            f
            for f in current_files
            if not should_exclude_path(f, config.filtering.exclude_paths)
        ]

        if not current_files:
            continue

        # Classify files
        definition_files = []
        proof_files = []

        repo_path = Path(repo.working_dir)

        for file_path in current_files:
            full_path = repo_path / file_path
            if not full_path.exists():
                # File might be deleted in this commit
                continue

            classification = classify_file(full_path)

            if classification.is_definition:
                definition_files.append(file_path)

            if classification.is_proof:
                # Check minimum thresholds
                if (
                    classification.theorem_count >= config.filtering.min_theorem_count
                    or classification.lemma_count >= config.filtering.min_theorem_count
                    or classification.tactic_block_count
                    >= config.filtering.min_tactic_blocks
                ):
                    proof_files.append(file_path)

        # Candidate must modify both definitions and proofs
        if definition_files and proof_files:
            candidate = CommitCandidate(
                commit_hash=commit.hexsha,
                commit_message=commit.message.strip(),
                author=str(commit.author),
                date=commit.committed_datetime,
                definition_files=definition_files,
                proof_files=proof_files,
            )
            candidates.append(candidate)
            logger.info(
                f"Found candidate: {commit.hexsha[:8]} - {commit.message.strip()[:50]}"
            )

    logger.info(f"Phase A complete: {len(candidates)} candidates from {processed} commits")
    return candidates


def validate_candidate(
    repo: Repo, candidate: CommitCandidate, config: Config
) -> list[Challenge]:
    """Phase B: Validate a candidate by creating broken state and testing.

    Args:
        repo: GitPython repository object.
        candidate: Candidate commit to validate.
        config: Configuration object.

    Returns:
        List of valid challenges (one per proof file that breaks), or empty list if none.
    """
    challenges = []
    repo_path = Path(repo.working_dir)

    # Checkout the "fixed" state (commit C)
    if not safe_checkout(repo, candidate.commit_hash):
        logger.warning(f"Failed to checkout {candidate.commit_hash}")
        return challenges

    commit = repo.commit(candidate.commit_hash)

    # Try each proof file
    for proof_file in candidate.proof_files:
        logger.debug(f"Testing proof file: {proof_file}")

        # First, verify that the fixed state actually builds successfully
        # (We need this as a baseline to know if reverting breaks it)
        result_fixed = run_lake_build(
            repo_path, proof_file, config.verification.timeout_seconds
        )

        if not result_fixed.success:
            logger.debug(
                f"Proof file {proof_file} doesn't build in fixed state, skipping"
            )
            continue

        # Restore proof file to parent state (create "broken" state)
        if not restore_file_from_parent(repo, commit, proof_file):
            logger.warning(f"Failed to restore {proof_file} from parent")
            continue

        # Run Lake build on broken state
        result_broken = run_lake_build(
            repo_path, proof_file, config.verification.timeout_seconds
        )

        # Check if this is a valid verification error
        if not result_broken.success and is_verification_error(result_broken.stderr):
            logger.info(f"Valid challenge found: {candidate.commit_hash[:8]} - {proof_file}")

            # Get the diff showing the fix
            author_fix_diff = get_file_diff(repo, commit, proof_file)

            # Capture codebase snapshot (all Lean files for MVP)
            codebase_snapshot = capture_codebase_snapshot(repo_path)

            # Create module name for verification command
            module_name = str(proof_file).replace("/", ".").replace(".lean", "")
            verification_command = f"lake build {module_name}"

            # Generate task_id
            file_name = Path(proof_file).stem
            task_id = f"{candidate.commit_hash[:8]}_{file_name}"

            challenge = Challenge(
                task_id=task_id,
                commit_hash=candidate.commit_hash,
                proof_file=proof_file,
                definition_files=candidate.definition_files,
                author_fix_diff=author_fix_diff,
                error_message=result_broken.error_message or "Unknown error",
                codebase_snapshot=codebase_snapshot,
                verification_command=verification_command,
            )

            challenges.append(challenge)

        # Restore proof file back to fixed state for next iteration
        safe_checkout(repo, candidate.commit_hash)

    return challenges


def run_mining(
    repo_path: Path | None = None,
    output_path: Path | None = None,
    limit: int = -1,
    dry_run: bool = False,
) -> MiningResult:
    """Run the proof repair challenge mining pipeline.

    Args:
        repo_path: Path to repository (overrides config).
        output_path: Path to output JSONL (overrides config).
        limit: Max commits to process (overrides config).
        dry_run: If True, only identify candidates without validation.

    Returns:
        MiningResult with statistics.
    """
    # Load configuration
    config = Config.from_file()

    # Override config with CLI arguments
    if repo_path:
        config.mining.repo_path = repo_path
    if output_path:
        config.output.jsonl_path = output_path
    if limit > 0:
        config.mining.max_commits = limit

    # Setup logging
    setup_logging(config)
    logger.info("Starting dalek history mining")
    logger.info(f"Repository: {config.mining.repo_path}")
    logger.info(f"Max commits: {config.mining.max_commits}")
    logger.info(f"Dry run: {dry_run}")

    # Open repository
    try:
        repo = Repo(config.mining.repo_path)
    except GitCommandError as e:
        logger.error(f"Failed to open repository: {e}")
        raise

    # Count total commits for statistics
    total_commits = sum(1 for _ in repo.iter_commits(config.mining.start_ref))
    if config.mining.max_commits > 0:
        total_commits = min(total_commits, config.mining.max_commits)

    logger.info(f"Total commits to analyze: {total_commits}")

    # Phase A: Identify candidates
    candidates = identify_candidates(repo, config)

    if dry_run:
        print_candidates(candidates)
        return MiningResult(
            total_commits=total_commits,
            candidates=len(candidates),
            valid_challenges=0,
            challenges=[],
            skipped_reasons={},
        )

    # Phase B: Validate and package
    logger.info("Phase B: Validating candidates and packaging challenges")

    all_challenges = []
    skipped_reasons: dict[str, int] = {}

    for i, candidate in enumerate(candidates, 1):
        progress_msg = format_progress(
            i,
            len(candidates),
            f"Validating {candidate.commit_hash[:8]} - {candidate.commit_message[:40]}...",
        )
        logger.info(progress_msg)
        print(progress_msg)

        try:
            challenges = validate_candidate(repo, candidate, config)

            if challenges:
                all_challenges.extend(challenges)
                logger.info(f"  ✓ Found {len(challenges)} challenge(s)")
                print(f"  ✓ Found {len(challenges)} challenge(s)")
            else:
                reason = "no_verification_error"
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
                logger.debug(f"  ✗ Skipped: {reason}")

        except Exception as e:
            logger.error(f"  ✗ Exception while validating: {e}")
            reason = "exception"
            skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

    # Write output
    if all_challenges:
        logger.info(
            f"Writing {len(all_challenges)} challenges to {config.output.jsonl_path}"
        )
        write_challenges(all_challenges, config.output.jsonl_path)
        print(f"\nWrote {len(all_challenges)} challenges to {config.output.jsonl_path}")

    # Build result
    result = MiningResult(
        total_commits=total_commits,
        candidates=len(candidates),
        valid_challenges=len(all_challenges),
        challenges=all_challenges,
        skipped_reasons=skipped_reasons,
    )

    # Print summary
    print_mining_summary(result)

    return result


# CLI interface will be added separately
__all__ = [
    "run_mining",
    "identify_candidates",
    "validate_candidate",
]
