"""Async trace with concurrent spans via asyncio.gather.

Shows that the TruLayer SDK's async context managers work correctly with
asyncio concurrency. Two LLM calls run concurrently inside a single
trace, each wrapped in its own span. Both spans land in the same trace
payload because the trace's async context manager keeps them correlated.

Run it with:

    uv run python -m examples.async_example

Set `OPENAI_API_KEY` + `TRULAYER_*` in `.env` for real runs, or
`TRULAYER_DEMO_MOCK=1` for an offline run.
"""
from __future__ import annotations

import asyncio

from examples._config import build_async_openai_client, init_client


async def _ask(
    openai_client: object,
    trace_ctx: object,
    question: str,
    span_name: str,
) -> str:
    """Run a single OpenAI chat call inside its own span."""
    async with trace_ctx.span(span_name, span_type="llm") as s:  # type: ignore[union-attr]
        s.set_model("gpt-4o-mini")
        s.set_input(question)
        resp = await openai_client.chat.completions.create(  # type: ignore[union-attr]
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Answer in one sentence."},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        answer = (resp.choices[0].message.content or "").strip()
        s.set_output(answer)
        if resp.usage is not None:
            s.set_tokens(prompt=resp.usage.prompt_tokens, completion=resp.usage.completion_tokens)
    return answer


async def _run() -> str:
    client = init_client()
    openai_client = build_async_openai_client()

    questions = [
        ("What is the tallest building in New York?", "ask-nyc"),
        ("What is the tallest building in London?", "ask-london"),
    ]

    async with client.trace(
        name="concurrent-qa",
        tags=["demo", "async"],
        metadata={"example": "async_example.py"},
    ) as t:
        t.set_input(" | ".join(q for q, _ in questions))

        # Fire both LLM calls concurrently -- each gets its own span.
        answers = await asyncio.gather(
            *[_ask(openai_client, t, q, name) for q, name in questions]
        )

        t.set_output(" | ".join(answers))
        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


def main() -> str:
    return asyncio.run(_run())


if __name__ == "__main__":
    trace_id = main()
    print(f"async_example: emitted trace {trace_id}")
