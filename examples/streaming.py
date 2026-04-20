"""Streaming OpenAI responses with auto-instrumentation.

`instrument_openai` handles streaming transparently: the span is opened
when the request fires and closed after the stream is fully consumed,
with the accumulated output recorded on the span.

Run it with:

    uv run python -m examples.streaming
"""
from __future__ import annotations

from trulayer import instrument_openai

from examples._config import build_openai_client, init_client, is_mock_mode


def main() -> str | None:
    # The mock transport used in TRULAYER_DEMO_MOCK=1 mode does not emulate
    # the SSE streaming protocol — skip this example offline.
    if is_mock_mode():
        print("streaming: skipped in TRULAYER_DEMO_MOCK mode (SSE not mocked).")
        return None

    client = init_client()
    instrument_openai(client)
    openai_client = build_openai_client()

    question = "List three famous landmarks in Paris, one per line."

    with client.trace(name="streaming-qa", tags=["demo", "streaming"]) as t:
        t.set_input(question)

        chunks: list[str] = []
        stream = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
            stream=True,
            stream_options={"include_usage": True},
        )
        for event in stream:
            if event.choices and event.choices[0].delta.content:
                chunks.append(event.choices[0].delta.content)

        answer = "".join(chunks).strip()
        t.set_output(answer)
        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    if trace_id is not None:
        print(f"streaming: emitted trace {trace_id}")
