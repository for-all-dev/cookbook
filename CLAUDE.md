# CLAUDE.md

Project instructions for the Formal Verification Agent Recipes cookbook.

## Overview

Educational cookbook bridging formal verification (Dafny, Lean) and agentic AI systems.

**Workspace**: Python 3.13 + UV, three members: `book/` (Jupyter Book), `evals/` (agent harnesses, see `evals/CLAUDE.md`), `scripts/` (utilities)

**Live site**: recipes.for-all.dev

## Version Control

Uses both `.git/` and `.jj/` (Jujutsu v0.34.0). **Jujutsu rules**: Always use `-m` flag inline (e.g., `jj new -m "msg"`), never use interactive editor commands.

## Development

**Prerequisites**: Dafny, Elan (Lean toolchain), UV, `ANTHROPIC_API_KEY` environment variable. Or use `nix develop` for everything.

**Workspace**: Three UV members (`book/`, `evals/`, `scripts/`) sharing `.venv/` at root.

**Dependency management**:
```bash
uv add <package> --package <member>  # Add dependency
uv sync                               # Sync all dependencies
```

**Build book**:
```bash
cd book && uv run jupyter book start  # Access at localhost:3000
```

Book config: `book/myst.yml`, static assets: `book/static/img/`

## Common Tasks

**Add book chapter**: Create `book/0X-chapter-name/`, add markdown, update `book/myst.yml`, test locally

**Implement eval**: See `evals/CLAUDE.md`

**Generate figures**: `uv run scripts/<name>.py`, save to `book/static/img/`

**Update dependencies**: `uv add <package> --package <member>; uv sync`

## Key Concepts

- **Verification agents**: LLM generates code/proofs → verifier feedback → iterate
- **Perfect Grader Thesis**: Formal verifiers enable evals without LLM-as-judge
- **Benchmarks → Evals → RL**: Ground truth becomes a process; deterministic feedback enables RL

## Philosophy

Not a math book. Defensive acceleration. Practical tooling (typer, pydantic). Modern Python (UV). ~6-month shelf life.

## Deployment

**Target**: recipes.for-all.dev | **CI/CD**: GitHub Actions → SSH deploy on push to `master` | **Configs**: `operations/`

## Troubleshooting

- **Dafny/Lean not found**: Install from releases or use `nix develop`
- **API key errors**: Set `ANTHROPIC_API_KEY`
- **Book build fails**: Check `book/myst.yml` syntax
- **Evals issues**: See `evals/CLAUDE.md`

## Resources

- UV: https://docs.astral.sh/uv/
- Jupyter Book: https://jupyterbook.org/
- Dafny: https://dafny.org/ | Lean: https://lean-lang.org/
- Evals frameworks: See `evals/CLAUDE.md`
