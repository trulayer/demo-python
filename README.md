# TruLayer AI — Python Demos

Runnable, end-to-end Python examples that show how to trace AI
applications with the [`trulayer`](https://pypi.org/project/trulayer/) SDK. Every example
emits real traces and spans; the final `feedback.py` demo also posts
user feedback against a trace.

## Quick start

```bash
# From this directory:
cp .env.example .env      # then fill in your keys
uv sync                   # installs trulayer + openai + anthropic
uv run python -m examples.basic_trace
```

Set in `.env` at minimum:

```
TRULAYER_API_KEY=tl_...
TRULAYER_PROJECT_NAME=my-project
TRULAYER_ENDPOINT=https://api.trulayer.ai
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Offline / CI mode

Set `TRULAYER_DEMO_MOCK=1` and every OpenAI / Anthropic call is routed
through an `httpx.MockTransport`. No real keys required, no network
touched. Used by `run_all.py` and the test suite.

```bash
TRULAYER_DEMO_MOCK=1 uv run python -m examples.run_all
```

This spins up a local HTTP server that mimics the TruLayer ingestion
endpoints, runs every example against it, and prints a summary of the
batches and feedback it received — an end-to-end data-flow check.

## Examples

| File                    | Shows                                                                      |
|-------------------------|----------------------------------------------------------------------------|
| `basic_trace.py`        | Manual `trace()` + `span()` with a real OpenAI call                         |
| `openai_auto.py`        | `instrument_openai()` — zero per-call span code                            |
| `anthropic_auto.py`     | `instrument_anthropic()` — same pattern, Claude Messages API                |
| `langchain_chain.py`    | `instrument_langchain()` callback on a prompt-\|-LLM-\|-parser chain         |
| `rag_pipeline.py`       | Embed → retrieve → generate, three span types in one trace                  |
| `agent.py`              | Tool-calling agent loop, one span per tool + one per LLM turn               |
| `streaming.py`          | Streaming chat responses auto-captured by the OpenAI patch                  |
| `feedback.py`           | Trace an answer and attach a thumbs-up feedback record                      |
| `run_all.py`            | Orchestrates every example against the local mock ingestion server         |
| `mock_server.py`        | Tiny HTTP server that captures `/v1/ingest/batch` and `/v1/feedback`        |

Each file can be run standalone:

```bash
uv run python -m examples.openai_auto
uv run python -m examples.rag_pipeline
uv run python -m examples.agent
```

## Tests

```bash
uv run pytest
```

The test suite runs in mock mode, starts the mock ingestion server
per-test, and asserts that each example's payload actually arrived —
including trace tags, span types, and feedback linkage.

## Project layout

```
demo-python/
├── .env.example
├── pyproject.toml
├── examples/
│   ├── _config.py          # .env loader + TruLayer / OpenAI / Anthropic clients
│   ├── mock_server.py      # local HTTP stand-in for the ingestion API
│   ├── basic_trace.py
│   ├── openai_auto.py
│   ├── anthropic_auto.py
│   ├── langchain_chain.py
│   ├── rag_pipeline.py
│   ├── agent.py
│   ├── streaming.py
│   ├── feedback.py
│   └── run_all.py
└── tests/
    └── test_examples.py    # end-to-end smoke tests
```

