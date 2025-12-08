"""Pydantic-AI agent for FVAPPS evaluation."""

import logging

from evals.fvapps.pydantic_ai.prompt import LEAN_FVAPPS_SYSTEM_PROMPT
from evals.fvapps.pydantic_ai.tools import verify_lean
from evals.fvapps.pydantic_ai.types import AgentResult, FVAPPSSample
from evals.fvapps.pydantic_ai.utils import categorize_error, extract_code

from pydantic_ai import Agent, RunContext


class AgentDeps:
    """Dependencies for agent tools."""

    def __init__(self, sample: FVAPPSSample):
        self.sample = sample
        self.attempts = 0


def create_fvapps_agent(model: str) -> Agent[AgentDeps, str]:
    """Create pydantic-ai agent with verify_lean tool.

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5")

    Returns:
        Agent configured for FVAPPS task
    """
    # Strip "anthropic/" prefix if present (inspect-ai format compatibility)
    if model.startswith("anthropic/"):
        model = model.replace("anthropic/", "")

    agent = Agent(
        model,
        deps_type=AgentDeps,
        system_prompt=LEAN_FVAPPS_SYSTEM_PROMPT,
    )

    @agent.tool
    async def verify_lean_tool(ctx: RunContext[AgentDeps], code: str) -> str:
        """Verify Lean code with lake build.

        Args:
            code: Complete Lean program with sorry replaced

        Returns:
            Success message or error details
        """
        ctx.deps.attempts += 1

        logger = logging.getLogger(__name__)
        logger.info(f"Attempt {ctx.deps.attempts}: Verifying code ({len(code)} chars)")

        # Run verification
        result = verify_lean(code, ctx.deps.sample.units)

        # Return message (pydantic-ai pattern: return string, not raise error)
        return result["message"]

    return agent


def run_agent_on_sample(
    sample: FVAPPSSample,
    model: str,
) -> AgentResult:
    """Run pydantic-ai agent on single FVAPPS sample.

    Args:
        sample: FVAPPS sample with Lean code and tests
        model: Model identifier

    Returns:
        AgentResult with success status, attempts, code, and error
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting evaluation for sample {sample.apps_id}")

    # Create agent
    agent = create_fvapps_agent(model)

    # Create dependencies
    deps = AgentDeps(sample=sample)

    # Construct user prompt
    user_prompt = f"""Problem: {sample.apps_question}

Specification (replace all sorry placeholders):
```lean
{sample.spec}
```

Unit tests (must pass):
```lean
{sample.units}
```

Write the complete implementation and proofs, then call verify_lean tool to check your work.
"""

    try:
        # Run agent (pydantic-ai handles tool iteration automatically in run_sync)
        result = agent.run_sync(user_prompt, deps=deps)

        # Extract code from result (pydantic-ai uses .data attribute on RunResult)
        # Get the output text from the result
        output_text = str(result.data) if hasattr(result, "data") else str(result)
        final_code = extract_code(output_text)

        # Check if verification succeeded (based on success message in output)
        success = "✓ Verification succeeded" in output_text

        if success:
            logger.info(f"Success after {deps.attempts} attempts")
            error_type = None
        else:
            # Run final verification to get error details
            verify_result = verify_lean(final_code, sample.units)
            error_type = categorize_error(verify_result["stderr"])
            logger.warning(f"Failed after {deps.attempts} attempts: {error_type}")

        return AgentResult(
            sample_id=sample.apps_id,
            success=success,
            attempts=deps.attempts,
            final_code=final_code,
            error_type=error_type,
        )

    except Exception as e:
        logger.error(f"Error running agent: {e}")
        return AgentResult(
            sample_id=sample.apps_id,
            success=False,
            attempts=deps.attempts,
            final_code=None,
            error_type="agent_error",
        )
