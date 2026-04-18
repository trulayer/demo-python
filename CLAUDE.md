# CLAUDE.md — Python Demos (demo-python)

## Project Purpose

End-to-end runnable Python examples demonstrating TruLayer AI SDK integration. Used for developer onboarding, documentation, and SDK integration testing in CI.

## Tech Stack

- Python 3.11+
- `uv` — package management
- `trulayer` — the TruLayer Python SDK (from `client-python`)
- `openai`, `anthropic`, `langchain` — AI providers

## Key Commands

```bash
uv sync                           # Install all deps
uv run python examples/basic_trace.py
uv run pytest tests/              # Run integration smoke tests
```

## Project Layout

```text
examples/
  basic_trace.py        → manual trace + span creation
  openai_auto.py        → OpenAI auto-instrumentation
  rag_pipeline.py       → multi-span RAG pipeline
  agent.py              → tool-calling agent tracing
  langchain_chain.py    → LangChain auto-instrumentation
  async_example.py      → async trace context
  feedback.py           → submitting feedback on traces
tests/
  test_examples.py      → CI smoke test: run each example, verify no errors
pyproject.toml
```

## Example Standards

- Every example runs end-to-end with `uv run python examples/<name>.py`
- Each file has a module-level docstring: one sentence explaining what it demonstrates
- No business logic — pure demonstration of one SDK concept per file
- Use real API calls in integration CI; use mock mode (set `TRULAYER_DRY_RUN=true`) for offline runs

## CI Smoke Tests

`tests/test_examples.py` imports and runs `main()` from each example with:
- `TRULAYER_DRY_RUN=true` (no network calls)
- Mocked OpenAI/Anthropic responses

All examples must pass without errors.
