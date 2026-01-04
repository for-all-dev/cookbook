# Evals Package

Agent benchmarks on formal verification tasks.

## Overview

Evaluation harnesses for verification agents using three frameworks:
- **inspect-ai**: High-level, automatic tool-calling loops
- **plain**: Pure Anthropic SDK (shows what's under the hood)
- **pydantic-ai**: Lean FVAPPS tasks

## Running Evaluations

```bash
cd evals
uv run agent dafnybench              # Defaults: Sonnet 4.5, 10 samples
uv run agent dafnybench --limit -1   # All 782 samples
uv run agent dafnybench -m anthropic/claude-opus-4-1
```

## Architecture

```
evals/src/evals/
├── __init__.py                 # CLI entry point
├── dafnybench/
│   ├── common/                 # Shared dataset loader
│   ├── inspect_ai/             # Task, scorer, tools
│   └── plain/                  # Manual tool-calling loop
│       ├── agent.py           # handle_tool(), run_agent()
│       ├── config.toml        # Prompts and settings
│       ├── io_util.py         # Logging, artifacts
│       ├── structures.py      # EvalSample, AgentResult, EvalMetrics
│       └── tools.py           # insert_*, verify_dafny, TOOLS
└── fvapps/pydantic_ai/        # Lean FVAPPS
```

## DafnyBench

**Dataset**: `wendy-sun/DafnyBench` (782 samples) - Add verification hints to Dafny programs

**Frameworks**:
- **inspect-ai**: `generate()` handles loop automatically, free logging/metrics
- **plain**: Manual loop, tool-based insertions (`insert_invariant`, etc.), conversation history to JSON

**Metrics**: Accuracy, avg time, avg attempts, error distribution

## Testing

```bash
cd evals
uv run pytest        # Tests
uv run ruff check --fix   # Lint
uv run ruff format   # Format
uv run ty check      # Type check (don't use pyright)
```

## Implementing a New Eval

1. Create `src/evals/<benchmark_name>/`
2. Choose framework: `inspect_ai/`, `pydantic_ai/`, or `plain/`
3. Implement dataset loader (in `common/` if reused), tools, metrics, agent
4. Add CLI command in `src/evals/__init__.py`
5. Add tests in `tests/`

## Output Artifacts

**Conversation history** (plain only):
```
logs/plain_<timestamp>_<sample_id>.json
{"test_id": "...", "timestamp": "...", "system_prompt": "...", "messages": [...]}
```

**Dafny artifacts**:
```
artifacts/sample_<id>_attempt_<n>.dfy    # Each attempt
artifacts/sample_<id>_final.dfy          # Successful verification
```

## Key Patterns

- **Tool-based agents**: LLM has access to `verify_dafny` tool, iterates naturally
- **Perfect Grader**: Deterministic verifier feedback → no LLM-as-judge needed
- **Dual framework**: Show high-level (inspect-ai) and low-level (plain) approaches

## Troubleshooting

- **Dafny/Lean not found**: Install from releases or `nix develop` at workspace root
- **API key errors**: Set `ANTHROPIC_API_KEY`
- **Tests fail**: Ensure Dafny in PATH
- **Type errors**: Use `uv run ty check`, not pyright

## Dependencies

**Core**: inspect-ai, anthropic, datasets, pydantic, pydantic-ai, typer
**Dev**: pytest, ruff, ty

## Resources

- Inspect AI: https://inspect.ai-safety-institute.org.uk/
- Pydantic AI: https://ai.pydantic.dev/
- Dafny: https://dafny.org/ | Lean: https://lean-lang.org/
