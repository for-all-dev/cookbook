"""Evals CLI for formal verification benchmarks."""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from evals.dafnybench.inspect_ai import run_dafnybench_eval

# Load environment variables from .env file
# Check both project root and evals/ directory
for env_path in [Path(".env"), Path("evals/.env")]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Default configuration
DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"
DEFAULT_LIMIT = 10

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
    """Run DafnyBench evaluation using Inspect AI framework.

    Examples:
        # Run with defaults (Claude Sonnet 4.5, 10 samples)
        uv run agent dafnybench inspect

        # Run with all 782 samples
        uv run agent dafnybench inspect --limit -1

        # Test with just 5 samples
        uv run agent dafnybench inspect --limit 5

        # Use different model
        uv run agent dafnybench inspect -m anthropic/claude-opus-4
    """
    # Convert limit=-1 to None (all samples)
    eval_limit = None if limit == -1 else limit

    typer.echo(
        f"Running DafnyBench with Inspect AI (limit={limit if limit != -1 else 'all'})..."
    )
    run_dafnybench_eval(
        model=model,
        limit=eval_limit,
    )


@dafnybench_app.command("raw")
def dafnybench_raw(
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
    """Run DafnyBench evaluation using raw Anthropic SDK (no framework).

    This implementation shows what Inspect AI abstracts away by implementing
    the evaluation loop manually with just the Anthropic SDK.

    Examples:
        # Run with defaults
        uv run agent dafnybench raw

        # Run with all samples
        uv run agent dafnybench raw --limit -1
    """
    typer.echo("DafnyBench raw implementation not yet available", err=True)
    typer.echo("This will be implemented in chapter 3 of the book.", err=True)
    raise typer.Exit(code=1)


@fvapps_app.command("pydantic")
def fvapps_pydantic(
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
            help=f"Limit number of samples to evaluate (default: {DEFAULT_LIMIT})",
        ),
    ] = DEFAULT_LIMIT,
) -> None:
    """Run FVAPPS (Lean) evaluation using Pydantic AI framework.

    FVAPPS is a Lean theorem proving benchmark. This implementation uses
    the Pydantic AI framework for structured agent workflows.

    Examples:
        # Run with defaults
        uv run agent fvapps pydantic

        # Use different model
        uv run agent fvapps pydantic -m anthropic/claude-opus-4
    """
    typer.echo("FVAPPS pydantic implementation not yet available", err=True)
    typer.echo("This will be implemented in chapter 4 of the book.", err=True)
    raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the CLI."""
    app()
