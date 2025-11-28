"""Tool execution for rawdog DafnyBench implementation."""

import subprocess
import tempfile
from pathlib import Path


def verify_dafny(code: str) -> dict[str, str | bool]:
    """Verify Dafny code synchronously using subprocess.

    Args:
        code: Complete Dafny program with verification hints

    Returns:
        dict with keys:
            - success (bool): True if verification succeeded
            - message (str): Success/failure message
            - stdout (str): Standard output from Dafny
            - stderr (str): Standard error from Dafny

    The function checks for bypass attempts ({:verify false}), runs the
    Dafny compiler with a 30-second timeout, and returns structured results.
    """
    # Check for verification bypass attempts (following DafnyBench methodology)
    if "{:verify false}" in code.lower():
        return {
            "success": False,
            "message": "Invalid code: contains {:verify false} which bypasses verification. "
            "You must properly verify the code with correct annotations.",
            "stdout": "",
            "stderr": "Bypass attempt detected",
        }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dfy", delete=False) as tmp:
        tmp.write(code)
        temp_path = tmp.name

    try:
        # Run Dafny verification with timeout
        result = subprocess.run(
            ["dafny", "verify", temp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check for successful verification
        success = result.returncode == 0 and "0 errors" in result.stdout

        if success:
            message = "✓ Verification succeeded! All checks passed."
        else:
            error_output = result.stderr if result.stderr else result.stdout
            message = f"Verification failed:\n\n{error_output}"

        return {
            "success": success,
            "message": message,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Verification timed out after 30 seconds. "
            "The program may be too complex or contain infinite loops.",
            "stdout": "",
            "stderr": "Timeout",
        }
    finally:
        # Cleanup temporary file
        Path(temp_path).unlink(missing_ok=True)
