"""Tools for FVAPPS evaluation - Lean verification."""

import subprocess
import tempfile
from pathlib import Path


def verify_lean(code: str, units: str, timeout: int = 60) -> dict[str, str | bool]:
    """Verify Lean code using lake build.

    Creates a temporary Lean project, writes code + units, runs lake build.

    Args:
        code: Lean code with sorry replaced
        units: Unit test code (#guard_msgs, #eval)
        timeout: Timeout in seconds (default: 60)

    Returns:
        dict with keys:
        - success: bool
        - message: str (for agent feedback)
        - stdout: str
        - stderr: str
    """
    # Check for verification bypass attempts
    if "axiom" in code.lower() and "sorry" not in code.lower():
        return {
            "success": False,
            "message": "Invalid code: contains axiom declarations which bypass verification.",
            "stdout": "",
            "stderr": "axiom declarations not allowed",
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "fvapps_verify"
        project_dir.mkdir()

        # Create minimal lakefile.lean
        lakefile_content = """import Lake
open Lake DSL

package fvapps_verify

@[default_target]
lean_lib FVAPPSVerify
"""
        (project_dir / "lakefile.lean").write_text(lakefile_content.strip())

        # Create FVAPPSVerify directory
        lib_dir = project_dir / "FVAPPSVerify"
        lib_dir.mkdir()

        # Write code + unit tests
        full_code = f"{code}\n\n{units}"
        (lib_dir / "Main.lean").write_text(full_code)

        try:
            # Run lake build with timeout
            result = subprocess.run(
                ["lake", "build"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Check for success (returncode 0 and no "error:" in stderr)
            success = result.returncode == 0 and "error:" not in result.stderr.lower()

            if success:
                message = "✓ Verification succeeded! All checks passed."
            else:
                message = f"Verification failed:\n\n{result.stderr}"

            return {
                "success": success,
                "message": message,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"Verification timed out after {timeout} seconds. The program may be too complex or non-terminating.",
                "stdout": "",
                "stderr": "timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during verification: {str(e)}",
                "stdout": "",
                "stderr": str(e),
            }
