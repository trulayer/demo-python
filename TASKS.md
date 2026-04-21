# Python Demos — Implementation Tasks

## Status Legend

- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1: Core Examples (MVP)

- [x] `pyproject.toml` with `trulayer`, `openai`, `anthropic`, `langchain` deps
- [x] `examples/basic_trace.py` — manual trace + span with a simple OpenAI call
- [x] `examples/openai_auto.py` — `instrument_openai()` with zero manual spans
- [x] `examples/rag_pipeline.py` — embed → retrieve → generate, 3 spans
- [x] `examples/agent.py` — tool-calling agent with per-tool spans
- [x] `examples/feedback.py` — trace then submit thumbs-up feedback

## Phase 2: Advanced Examples

- [x] `examples/langchain_chain.py` — LangChain chain with auto-instrumentation
- [x] `examples/async_example.py` — `asyncio` concurrent spans
- [x] `examples/anthropic_auto.py` — Anthropic auto-instrumentation

## Testing

- [x] `tests/test_examples.py` — smoke test runner for all examples (dry-run mode)
- [x] CI job: run smoke tests on every push
