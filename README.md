# TruLayer AI — Python Demos

End-to-end Python examples demonstrating TruLayer AI SDK integration across common AI use cases.

## Prerequisites

```bash
pip install trulayer openai anthropic langchain
# or
uv sync
```

Set your API keys:

```bash
export TRULAYER_API_KEY=tl_...
export OPENAI_API_KEY=sk-...
```

## Examples

### Basic Tracing

```bash
python examples/basic_trace.py
```

Demonstrates manual trace and span creation with a simple OpenAI call.

### OpenAI Auto-Instrumentation

```bash
python examples/openai_auto.py
```

Shows zero-code instrumentation of the OpenAI client.

### RAG Pipeline

```bash
python examples/rag_pipeline.py
```

Multi-span trace for a retrieval-augmented generation pipeline with embedding + generation spans.

### Multi-Step Agent

```bash
python examples/agent.py
```

Traces a tool-calling agent across multiple reasoning steps and tool invocations.

### LangChain Integration

```bash
python examples/langchain_chain.py
```

Auto-instrumentation for LangChain chains and agents.

### Async Application

```bash
python examples/async_example.py
```

Async trace context with `asyncio` and concurrent span tracking.

### Feedback Submission

```bash
python examples/feedback.py
```

Attaches user feedback (thumbs up/down, corrections) to completed traces.

## Project Structure

```text
demo-python/
├── examples/
│   ├── basic_trace.py
│   ├── openai_auto.py
│   ├── rag_pipeline.py
│   ├── agent.py
│   ├── langchain_chain.py
│   ├── async_example.py
│   └── feedback.py
├── pyproject.toml
└── uv.lock
```

## Engineering Standards

- Every example must run end-to-end without errors
- Examples are integration-tested in CI using a test TruLayer project
- Each example has a clear docstring explaining what it demonstrates
- Keep examples minimal — demonstrate one concept per file
