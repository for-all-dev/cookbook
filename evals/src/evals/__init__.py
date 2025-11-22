"""Evals CLI for formal verification benchmarks."""

from typing import Annotated

import typer

from evals.dafnybench.inspect_ai import run_dafnybench_eval

app = typer.Typer(help="Evaluation tools for formal verification benchmarks")


@app.command()
def agent(
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
        str,
        typer.Option(
            "--model",
            "-m",
            help="Model to evaluate (default: anthropic/claude-sonnet-4-5)",
        ),
    ] = "anthropic/claude-sonnet-4-5",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Limit number of samples to evaluate (default: 10, use -1 for all 782 samples)",
        ),
    ] = 10,
) -> None:
    """Run evaluation on a formal verification benchmark.

    Examples:
        # Run DafnyBench with Inspect AI (default: Claude Sonnet 4.5, 10 samples)
        uv run agent dafnybench

        # Run with all 782 samples
        uv run agent dafnybench --limit -1

        # Test with just 5 samples
        uv run agent dafnybench --limit 5

        # Use different model
        uv run agent dafnybench -m anthropic/claude-opus-4
    """
    if benchmark.lower().startswith("dafny"):
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
