"""CLI interface for dalek history mining.

Entry point: uv run mine generate
"""

from pathlib import Path
from typing import Annotated

import typer

from evals.dalek_history import run_mining

app = typer.Typer(
    help="Dalek history proof repair mining tools",
    no_args_is_help=True,  # Force showing help if no command given
)


@app.command()
def generate(
    repo: Annotated[
        str | None,
        typer.Option(
            "--repo",
            "-r",
            help="Path to curve25519-dalek-lean-verify repo (default: from config)",
        ),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output JSONL path (default: from config)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-l", help="Max commits to process (default: -1 = all)"
        ),
    ] = -1,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Only identify candidates, don't validate"),
    ] = False,
) -> None:
    """Generate proof repair challenges from dalek git history.

    Examples:
        # Mine all commits (use config defaults)
        uv run mine generate

        # Mine last 50 commits only
        uv run mine generate --limit 50

        # Dry run to see candidates
        uv run mine generate --dry-run --limit 10

        # Custom output path
        uv run mine generate -o ./my_challenges.jsonl
    """
    repo_path = Path(repo) if repo else None
    output_path = Path(output) if output else None

    run_mining(
        repo_path=repo_path,
        output_path=output_path,
        limit=limit,
        dry_run=dry_run,
    )


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
