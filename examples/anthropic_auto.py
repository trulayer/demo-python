"""Anthropic auto-instrumentation — zero per-call span code.

Same pattern as `openai_auto.py` but for the Anthropic Messages API:
`instrument_anthropic(client)` patches `anthropic.messages.create` so
every call inside an active trace records an `anthropic.messages` span.

Run it with:

    uv run python -m examples.anthropic_auto
"""
from __future__ import annotations

from trulayer import instrument_anthropic

from examples._config import build_anthropic_client, init_client


def main() -> str:
    client = init_client()
    instrument_anthropic(client)
    anthropic_client = build_anthropic_client()

    question = "In one short sentence, why is the Eiffel Tower famous?"

    with client.trace(name="landmark-qa", tags=["demo", "anthropic-auto"]) as t:
        t.set_input(question)
        resp = anthropic_client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=128,
            messages=[{"role": "user", "content": question}],
        )
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        t.set_output(text.strip())
        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    print(f"anthropic_auto: emitted trace {trace_id}")
