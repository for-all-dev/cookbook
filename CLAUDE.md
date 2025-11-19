# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a formal verification cookbook that bridges formal verification and agentic language systems. It contains:

- **book**: Jupyter Book documentation about formal verification agents (Dafny, Lean, RL)
- **evals**: Evaluation code to be imported/viewed in the ebook but also, given an API key, work e2e.

The project uses a uv workspace with two members (book, evals).

## Version Control

This repository uses both `.git` and `.jj` directories - check for jujutsu (jj) commands when the user references version control.

## Development Commands

### Building the Book

```bash
# Navigate to book directory
cd book

# Start development server
uv run jupyter book start
# Access at http://localhost:3000
```

The book uses MyST markdown and is configured via `book/myst.yml`. Book structure follows numbered directories (01-introduction, 02-dafny, 03-lean, 04-rl, 05-outlook).

### Running Tests (evals)

```bash
# Run tests for evals package
cd evals
uv run pytest

# Run with ruff linting
uv run ruff check
```

The evals package has a dev dependency group including pytest, hypothesis, ruff, and ty.

### Working with Dependencies

```bash
# Add dependency to specific workspace member
uv add <package> --package <book|evals>

# Sync all workspace dependencies
uv sync
```

## Architecture

### Workspace Structure

- Root `pyproject.toml` defines the workspace with two members
- Each member (book, evals) has its own `pyproject.toml`
- Python 3.13 is required for both book and evals
- Shared virtual environment at `.venv/`

### Evals Package

- in `evals.dafnybench`, we're working with `wendy-sun/DafnyBench` on huggingface.
  - `evals.dafnybench.inspect_ai` will do it with the `inspect_ai` framework
  - `evals.dafnybench.rawdog` will do it with pure python and the anthropic SDK.
- in `evals.fvapps`, we're working with `quinn-dougherty/fvapps` on huggingface, which we'll do with `pydantic_ai`

### Book Architecture

- MyST Markdown format with Jupyter Book
- Table of contents defined in `book/myst.yml`
- Organized into chapters by topic (introduction, dafny, lean, rl, outlook)
- Uses book-theme template with folder organization
