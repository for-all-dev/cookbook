# CLAUDE.md

Project instructions for Claude Code when working with the Formal Verification Agent Recipes cookbook.

## Project Overview

**Formal Verification Agent Recipes** is an educational cookbook bridging formal verification (Dafny, Lean) and agentic AI systems. It contains:

- **book/**: Jupyter Book documentation with 6 chapters covering verification agents
- **evals/**: Python package implementing agent evaluations on verification tasks
- **scripts/**: Utility scripts for figures and one-off tasks
- **operations/**: Server deployment configuration (nginx, systemd)

**Target audience**: Formal verification experts entering AI/evals space, proof engineers building agents.

**Tech stack**: Python 3.13, UV workspace, Jupyter Book, inspect-ai, pydantic-ai, Anthropic SDK.

**Live site**: recipes.for-all.dev

## Version Control

This repository uses **both** `.git/` and `.jj/` (Jujutsu v0.34.0). Check which exists before suggesting version control commands.

### Jujutsu Command Rules
- **NEVER** use jj commands that open an editor interactively
- Always use non-interactive flags:
  - `jj describe -m "message"` NOT `jj describe`
  - `jj new -m "message"` NOT `jj new`
  - `jj squash -m "message"` NOT `jj squash`
  - For commands that would open an editor, use `-m` flag inline

## Development Environment

### Prerequisites

Install these system dependencies:

```bash
# Dafny compiler (required for DafnyBench evals)
# Download from: https://github.com/dafny-lang/dafny/releases

# Elan (Lean toolchain manager, required for FVAPPS work)
# Install from: https://github.com/leanprover/elan

# UV (Python package manager)
# Install from: https://docs.astral.sh/uv/

# Set API key for running evals
export ANTHROPIC_API_KEY="your-key-here"
```

Alternatively, use the Nix development environment:

```bash
nix develop  # Provides dafny, elan, uv, nodejs, and all tools
```

### Workspace Structure

UV workspace with **three members**:

```
pyproject.toml           # Root workspace config
├── book/                # Member 1: Jupyter Book
│   └── pyproject.toml
├── evals/               # Member 2: Evaluation package
│   └── pyproject.toml
└── scripts/             # Member 3: Utility scripts
    └── pyproject.toml
```

All members require Python 3.13 and share a virtual environment at `.venv/`.

### Dependency Management

```bash
# Add dependency to specific workspace member
uv add <package> --package <book|evals|scripts>

# Add dev dependency
uv add --dev <package> --package evals

# Sync all workspace dependencies
uv sync

# Run commands in workspace context
uv run <command>
```

## Building the Book

The book uses **Jupyter Book** (≥2.0.2) with MyST markdown and the book-theme template.

```bash
# Start development server
cd book
uv run jupyter book start
# Access at http://localhost:3000
```

### Book Structure

1. **01-introduction/** - Target audience, installation, key concepts (evals vs benchmarks, RL)
2. **02-dafny-and-inspect/** - DafnyBench solver with inspect-ai framework
3. **03-dafny-and-rawdog/** - Pure Python + Anthropic SDK implementation
4. **04-lean-and-pydanticai/** - FVAPPS with pydantic-ai framework
5. **05-rl/** - From evals to RL environments, SFT bootstrapping
6. **06-outlook/** - Future directions, measuring verification burden

### Book Configuration

- **Config file**: `book/myst.yml`
- **Static assets**: `book/static/img/` (icons, logos, diagrams)
- **Format**: MyST markdown with Jupyter Book syntax

## Running Evaluations

The `evals` package implements agent benchmarks on formal verification tasks.

### CLI Usage

```bash
cd evals

# Run with defaults (Claude Sonnet 4.5, 10 samples)
uv run agent dafnybench

# Run all 782 samples
uv run agent dafnybench --limit -1

# Test with 5 samples
uv run agent dafnybench --limit 5

# Use different model
uv run agent dafnybench -m anthropic/claude-opus-4-1
```

### Evals Architecture

```
evals/src/evals/
├── __init__.py                    # Typer CLI entry point
├── dafnybench/
│   ├── inspect_ai/                # Complete: inspect-ai implementation
│   │   ├── __init__.py           # Task, scorer (320 lines)
│   │   ├── dataset.py            # HuggingFace loader (32 lines)
│   │   ├── metrics.py            # Custom metrics (46 lines)
│   │   └── tools.py              # verify_dafny tool (59 lines)
│   └── rawdog/                    # TODO: Pure Anthropic SDK implementation
└── fvapps/
    └── pydantic_ai/               # TODO: Lean FVAPPS with pydantic-ai
```

### DafnyBench Implementation

**Dataset**: `wendy-sun/DafnyBench` (782 samples) - Add verification hints to Dafny programs

**Agent architecture**:
1. System prompt explains Dafny verification
2. `verify_dafny` tool runs Dafny compiler
3. Agent iterates naturally via tool calls
4. `generate()` handles tool-calling loop automatically

**Metrics tracked**:
- Accuracy (verification success rate)
- Average verification time
- Average number of attempts
- Error type distribution

**Dependencies**: inspect-ai, anthropic, datasets, pydantic, typer

### Testing

```bash
cd evals

# Run pytest
uv run pytest

# Lint with ruff
uv run ruff check

# Type check
uv run ty
```

## Scripts Directory

One-off utility scripts, not part of main workspace packages.

```bash
# Run scripts via uv
uv run scripts/<script_name>.py
```

**Example**: `lean_agent_helix.py` - Generates visualization of LLM (◉) ↔ verifier (∀) interaction loop.

## Deployment

**Target**: recipes.for-all.dev

**CI/CD**: GitHub Actions (`.github/workflows/deploy.yml`)
- Triggers on push to `master` branch
- SSH deploys to server
- Pulls latest, syncs dependencies, restarts nginx

**Server configs** in `operations/`:
- `cookbook.service` - systemd service
- `nginx-cookbook.conf` - nginx configuration

## Architecture Patterns

### Tool-Based Agent Pattern (Inspect AI)

Agents have access to verification tools (e.g., `verify_dafny`). They iterate naturally via tool calls with no manual loop limits. The framework handles iteration automatically.

### Perfect Grader Thesis

Formal verifiers provide deterministic feedback (binary: verified or not). This enables:
- Evals without LLM-as-judge or human evaluation
- Natural progression from evals to RL environments
- Clear reward signals for reinforcement learning

### Dual Framework Approach

Show both abstraction layers:
- **High-level**: `inspect-ai` (batteries included, free logging/dashboards)
- **Low-level**: "rawdog" with pure Anthropic SDK (shows what's under the hood)

## Development Philosophy

1. **Not a math book** - Works with Lean but avoids pure mathematics
2. **Defensive acceleration** - Ensure correctness keeps pace with capability
3. **Practical tooling** - `typer` for CLIs, `pydantic` types everywhere
4. **Modern Python** - UV, not pip/poetry/requirements.txt
5. **Temporary relevance** - Expects ~6-month shelf life (targets late 2025)

## Key Concepts

**Benchmarks → Evals**: Ground truth becomes a process (run verifier, iterate)

**Evals → RL**: When grader is perfect (formal verification), evals naturally become RL environments

**Verification agents**: LLM generates code/proofs, verifier provides feedback, agent iterates

## Common Tasks

### Add a new chapter to the book

1. Create directory: `book/0X-chapter-name/`
2. Add markdown files with MyST syntax
3. Update `book/myst.yml` table of contents
4. Test locally: `cd book && uv run jupyter book start`

### Implement a new eval

1. Create package under `evals/src/evals/<benchmark_name>/`
2. Choose framework: `inspect_ai/` or `pydantic_ai/` or `rawdog/`
3. Implement dataset loader, tools, metrics, task
4. Add CLI command in `evals/src/evals/__init__.py`
5. Test: `cd evals && uv run pytest`

### Update dependencies

```bash
# Add new dependency
uv add <package> --package <member>

# Update specific package
uv add <package>@latest --package <member>

# Sync lockfile
uv sync
```

### Generate figures

```bash
# Run script with uv
uv run scripts/<script_name>.py

# Save to book/static/img/
# Reference in markdown: ![Alt text](static/img/figure.png)
```

## Troubleshooting

### Dafny not found
Install from https://github.com/dafny-lang/dafny/releases or use `nix develop`

### Lean not found
Install elan from https://github.com/leanprover/elan or use `nix develop`

### API key errors
Set `ANTHROPIC_API_KEY` environment variable

### Book build fails
Check `book/myst.yml` syntax and ensure all referenced files exist

### Tests fail in evals
Ensure Dafny compiler is installed and accessible in PATH

## File Organization

- **Root**: Workspace config (`pyproject.toml`, `uv.lock`), environment (`flake.nix`)
- **book/**: Documentation source, static assets, config (`myst.yml`)
- **evals/**: Package source under `src/evals/`, tests under `tests/`
- **scripts/**: Utility scripts with dependencies in frontmatter
- **operations/**: Server configs (not needed for local development)
- **.github/**: CI/CD workflows

## Additional Resources

- **Inspect AI docs**: https://inspect.ai-safety-institute.org.uk/
- **Pydantic AI docs**: https://ai.pydantic.dev/
- **Dafny docs**: https://dafny.org/
- **Lean docs**: https://lean-lang.org/
- **UV docs**: https://docs.astral.sh/uv/
