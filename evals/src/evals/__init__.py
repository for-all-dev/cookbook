"""
Evals CLI for formal verification benchmarks.
"""

import typer
from typing_extensions import Annotated

from evals.dafnybench.inspect_ai import run_dafnybench_eval


app = typer.Typer(help="Evaluation tools for formal verification benchmarks")


@app.command()
def solve(
    benchmark: Annotated[
        str,
        typer.Argument(help="Benchmark name (e.g., 'dafnybench')"),
    ],
    framework: Annotated[
        str,
        typer.Option(
            "--framework",
            "-f",
            help="Framework to use: 'inspect' or 'rawdog'",
        ),
    ] = "inspect",
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Model to evaluate (e.g., 'anthropic/claude-3-5-sonnet-20241022')",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Limit number of samples to evaluate (default: 10, use -1 for all 782 samples)",
        ),
    ] = 10,
) -> None:
    """
    Run evaluation on a formal verification benchmark.

    Examples:

        # Run DafnyBench with Inspect AI (default: 10 samples, natural tool-based iteration)
        uv run solve dafnybench --framework inspect

        # Run with all 782 samples
        uv run solve dafnybench --framework inspect --limit -1

        # Run with specific model
        uv run solve dafnybench -f inspect -m anthropic/claude-3-5-sonnet-20241022

        # Test with just 5 samples
        uv run solve dafnybench -f inspect --limit 5
    """
    if benchmark.lower() == "dafnybench":
        if framework.lower().startswith("inspect"):
            # Convert limit=-1 to None (all samples)
            eval_limit = None if limit == -1 else limit

            typer.echo(
                f"Running DafnyBench with Inspect AI (tool-based agent, limit={limit if limit != -1 else 'all'})..."
            )
            run_dafnybench_eval(
                model=model,
                limit=eval_limit,
            )
        elif framework.lower() == "rawdog":
            typer.echo("rawdog framework not yet implemented", err=True)
            raise typer.Exit(code=1)
        else:
            typer.echo(f"Unknown framework: {framework}", err=True)
            typer.echo("Available frameworks: inspect, rawdog", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Unknown benchmark: {benchmark}", err=True)
        typer.echo("Available benchmarks: dafnybench", err=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the CLI."""
    app()
