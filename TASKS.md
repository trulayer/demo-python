# Python Demos — Implementation Tasks

## Status Legend

- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1: Core Examples (MVP)

- [ ] `pyproject.toml` with `trulayer`, `openai`, `anthropic`, `langchain` deps
- [ ] `examples/basic_trace.py` — manual trace + span with a simple OpenAI call
- [ ] `examples/openai_auto.py` — `instrument_openai()` with zero manual spans
- [ ] `examples/rag_pipeline.py` — embed → retrieve → generate, 3 spans
- [ ] `examples/agent.py` — tool-calling agent with per-tool spans
- [ ] `examples/feedback.py` — trace then submit thumbs-up feedback

## Phase 2: Advanced Examples

- [ ] `examples/langchain_chain.py` — LangChain chain with auto-instrumentation
- [ ] `examples/async_example.py` — `asyncio` concurrent spans
- [ ] `examples/anthropic_auto.py` — Anthropic auto-instrumentation

## Testing

- [ ] `tests/test_examples.py` — smoke test runner for all examples (dry-run mode)
- [ ] CI job: run smoke tests on every push
