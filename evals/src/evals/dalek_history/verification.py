"""Lake build verification for Lean files."""

import logging
import subprocess
from pathlib import Path

from evals.dalek_history.structures import VerificationResult

logger = logging.getLogger(__name__)


def run_lake_build(
    repo_path: Path, target_file: Path | None = None, timeout: int = 300
) -> VerificationResult:
    """Run Lake build and capture results.

    Args:
        repo_path: Path to repository root.
        target_file: Specific file to build (None = build all).
        timeout: Timeout in seconds.

    Returns:
        VerificationResult with build outcome.
    """
    # Construct command
    cmd = ["lake", "build"]
    if target_file:
        # Convert .lean file path to module name (replace / with ., remove .lean)
        module_name = str(target_file).replace("/", ".").replace(".lean", "")
        cmd.append(module_name)

    logger.info(f"Running: {' '.join(cmd)} (timeout: {timeout}s)")

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        success = result.returncode == 0
        error_message = parse_lean_error(result.stderr) if not success else None

        return VerificationResult(
            success=success,
            stdout=result.stdout,
            stderr=result.stderr,
            error_message=error_message,
            timeout=False,
        )

    except subprocess.TimeoutExpired as e:
        logger.warning(f"Lake build timed out after {timeout}s")
        return VerificationResult(
            success=False,
            stdout=e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
            stderr=e.stderr.decode("utf-8", errors="replace") if e.stderr else "",
            error_message="Build timed out",
            timeout=True,
        )

    except Exception as e:
        logger.error(f"Lake build failed with exception: {e}")
        return VerificationResult(
            success=False,
            stdout="",
            stderr=str(e),
            error_message=f"Exception: {e}",
            timeout=False,
        )


def parse_lean_error(stderr: str) -> str:
    """Extract meaningful error message from Lake stderr.

    Lean errors typically have format:
    file.lean:line:col: error: message

    Args:
        stderr: Full stderr output from Lake.

    Returns:
        Key error line, or first 200 chars if no error line found.
    """
    lines = stderr.split("\n")

    # Look for lines with ": error:" pattern
    error_lines = [line for line in lines if ": error:" in line]

    if error_lines:
        return error_lines[0]

    # Fallback: return first non-empty line or truncated stderr
    non_empty_lines = [line for line in lines if line.strip()]
    if non_empty_lines:
        return non_empty_lines[0][:200]

    return stderr[:200] if stderr else "Unknown error"


def is_verification_error(stderr: str) -> bool:
    """Check if error is a verification error (not syntax/import error).

    Verification errors typically indicate proof failures, type mismatches,
    or incomplete proofs. Syntax and import errors are build failures but
    not interesting for proof repair challenges.

    Args:
        stderr: Stderr output from Lake build.

    Returns:
        True if this appears to be a verification error.
    """
    # Common verification error patterns
    verification_patterns = [
        "type mismatch",
        "failed to synthesize",
        "unsolved goals",
        "tactic",
        "unknown identifier",
        "application type mismatch",
        "invalid",
    ]

    # Common non-verification error patterns (exclude these)
    exclude_patterns = [
        "error: import",
        "error: unknown package",
        "error: file not found",
        "syntax error",
    ]

    stderr_lower = stderr.lower()

    # Exclude syntax/import errors
    if any(pattern in stderr_lower for pattern in exclude_patterns):
        return False

    # Check for verification error patterns
    return any(pattern in stderr_lower for pattern in verification_patterns)
