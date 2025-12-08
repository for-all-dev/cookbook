"""Evals CLI for formal verification benchmarks."""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from evals.dafnybench.inspect_ai import run_dafnybench_eval
from evals.dafnybench.inspect_ai.utils import ExtractionStrategy
from evals.dafnybench.plain import run_dafnybench_plain
from evals.dafnybench.plain.config import get_config

# Load environment variables from .env file
# Check both project root and evals/ directory
DOTENV = Path(".env")
for env_path in [DOTENV, Path("evals") / DOTENV, Path("../") / DOTENV]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Default configuration - load from config
config = get_config()
DEFAULT_MODEL = f"anthropic/{config.evaluation.default_model}"
DEFAULT_LIMIT = 10

# Model shortcuts (for backwards compatibility)
SONNET = "anthropic/claude-sonnet-4-5"
HAIKU = "anthropic/claude-haiku-4-5"

app = typer.Typer(help="Evaluation tools for formal verification benchmarks")

# Create subcommand groups
dafnybench_app = typer.Typer(help="DafnyBench evaluation tasks")
fvapps_app = typer.Typer(help="FVAPPS (Lean) evaluation tasks")

app.add_typer(dafnybench_app, name="dafnybench")
app.add_typer(fvapps_app, name="fvapps")


@dafnybench_app.command("inspect")
def dafnybench_inspect(
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help=f"Model to evaluate (default: {HAIKU})",
        ),
    ] = HAIKU,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help=f"Limit number of samples to evaluate (default: {DEFAULT_LIMIT}, use -1 for all 782 samples)",
        ),
    ] = DEFAULT_LIMIT,
    extraction_strategy: Annotated[
        str,
        typer.Option(
            "--extraction-strategy",
            help="Code extraction strategy: 'v1' (buggy - extracts from final completion) or 'v2' (fixed - backtracks through message history)",
        ),
    ] = "v1",
) -> None:
    """Run DafnyBench evaluation using Inspect AI framework.

    Examples:
        # Run with defaults (Claude Haiku 4.5, 10 samples, v1 extraction)
        uv run agent dafnybench inspect

        # Run with v2 extraction strategy (fixed)
        uv run agent dafnybench inspect --extraction-strategy v2

        # Run with all 782 samples
        uv run agent dafnybench inspect --limit -1

        # Test with just 5 samples
        uv run agent dafnybench inspect --limit 5

        # Use different model
        uv run agent dafnybench inspect -m anthropic/claude-opus-4
    """
    # Validate and convert extraction strategy
    if extraction_strategy not in ["v1", "v2"]:
        typer.echo(
            f"Error: extraction-strategy must be 'v1' or 'v2', got '{extraction_strategy}'",
            err=True,
        )
        raise typer.Exit(code=1)

    strategy = ExtractionStrategy(extraction_strategy)

    # Convert limit=-1 to None (all samples)
    eval_limit = None if limit == -1 else limit

    typer.echo(
        f"Running DafnyBench with Inspect AI (limit={limit if limit != -1 else 'all'}, strategy={extraction_strategy})..."
    )
    run_dafnybench_eval(
        model=model,
        limit=eval_limit,
        extraction_strategy=strategy,
    )


@dafnybench_app.command("plain")
def dafnybench_plain(
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help=f"Model to evaluate (default: {DEFAULT_MODEL})",
        ),
    ] = DEFAULT_MODEL,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help=f"Limit number of samples to evaluate (default: {DEFAULT_LIMIT}, use -1 for all 782 samples)",
        ),
    ] = DEFAULT_LIMIT,
) -> None:
    """Run DafnyBench evaluation using plain Anthropic SDK (no framework).

    This implementation shows what Inspect AI abstracts away by implementing
    the evaluation loop manually with just the Anthropic SDK.

    Examples:
        # Run with defaults
        uv run agent dafnybench plain

        # Run with all samples
        uv run agent dafnybench plain --limit -1
    """
    # Convert limit=-1 to None (all samples)
    eval_limit = None if limit == -1 else limit

    typer.echo(
        f"Running DafnyBench plain (limit={limit if limit != -1 else 'all'})..."
    )
    run_dafnybench_plain(model=model, limit=eval_limit)


@fvapps_app.command("pydanticai")
def fvapps_pydanticai(
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help=f"Model to evaluate (default: {DEFAULT_MODEL})",
        ),
    ] = DEFAULT_MODEL,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help=f"Limit number of samples to evaluate (default: {DEFAULT_LIMIT}, use -1 for all samples)",
        ),
    ] = DEFAULT_LIMIT,
) -> None:
    """Run FVAPPS (Lean) evaluation using Pydantic AI framework.

    FVAPPS is a Lean theorem proving benchmark where agents write terminating
    functional programs that satisfy specifications and pass unit tests.

    Examples:
        # Run with defaults (Claude Sonnet 4.5, 10 samples)
        uv run agent fvapps pydantic

        # Test with just 1 sample
        uv run agent fvapps pydantic --limit 1

        # Use different model
        uv run agent fvapps pydantic -m anthropic/claude-haiku-4-5
    """
    from evals.fvapps.pydantic_ai import run_fvapps_eval

    # Convert limit=-1 to None (all samples)
    eval_limit = None if limit == -1 else limit

    typer.echo(
        f"Running FVAPPS with Pydantic AI (limit={limit if limit != -1 else 'all'})..."
    )
    run_fvapps_eval(model=model, limit=eval_limit)


def main() -> None:
    """Entry point for the CLI."""
    app()
