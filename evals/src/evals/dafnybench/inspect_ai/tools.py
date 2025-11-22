"""Tools for DafnyBench evaluation."""

from inspect_ai.tool import ToolError, tool
from inspect_ai.util import sandbox


@tool
def verify_dafny():
    """Tool that verifies Dafny code and returns verification results.

    The agent calls this tool with generated code to check if verification succeeds.
    If verification fails, detailed error messages are returned for the agent to
    analyze and retry with improved hints.
    """

    async def execute(code: str) -> str:
        """Verify Dafny code and return verification results.

        Args:
            code: Complete Dafny program with verification hints added.

        Returns:
            Success message if verification passes, or raises ToolError with diagnostics.
        """
        # Check for verification bypass attempts (following DafnyBench methodology)
        if "{:verify false}" in code.lower():
            raise ToolError(
                "Invalid code: contains {:verify false} which bypasses verification. "
                "You must properly verify the code with correct annotations."
            )

        # Write code to temporary file
        temp_file = "/tmp/dafny_verify.dfy"
        await sandbox().write_file(temp_file, code)

        try:
            # Run Dafny verification
            result = await sandbox().exec(
                ["dafny", "verify", temp_file],
                timeout=30,
            )

            # Check for successful verification
            if result.returncode == 0 and "0 errors" in result.stdout:
                return "✓ Verification succeeded! All checks passed."

            # Return detailed error information for the agent to learn from
            error_output = result.stderr if result.stderr else result.stdout
            raise ToolError(f"Verification failed:\n\n{error_output}")

        except TimeoutError:
            raise ToolError(
                "Verification timed out after 30 seconds. The program may be too complex or contain infinite loops."
            )

    return execute
