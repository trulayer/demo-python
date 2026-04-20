"""Manual trace + span creation around a real OpenAI chat call.

This is the "hello world" of the TruLayer SDK. It shows the three things
every tracing integration needs:

  1. Open a trace that represents one user-facing operation.
  2. Wrap each logical step (retrieval, prompt construction, LLM call)
     in its own span so you can see latency and I/O per step.
  3. Attach the trace's top-level input/output so dashboards show the
     user's question and your final answer without drilling into spans.

Run it with:

    uv run python -m examples.basic_trace

Set `OPENAI_API_KEY` and `TRULAYER_*` in `.env` to hit real services,
or set `TRULAYER_DEMO_MOCK=1` for a fully offline run.
"""
from __future__ import annotations

import time

from examples._config import build_openai_client, init_client


def main() -> str:
    client = init_client()
    openai_client = build_openai_client()

    question = "What is the capital of France? Answer in one short sentence."

    with client.trace(
        name="basic-qa",
        external_id="basic-qa-demo",
        tags=["demo", "basic-trace"],
        metadata={"example": "basic_trace.py"},
    ) as t:
        t.set_input(question)
        t.set_model("gpt-4o-mini")

        # Step 1 — pretend we looked up some context. In a real app this
        # might be a vector-store query or a DB read.
        with t.span("retrieve-context", span_type="retrieval") as s:
            s.set_input(question)
            context = "France is a country in Western Europe; its capital is Paris."
            s.set_output(context)
            s.set_metadata(source="static-fixture")

        # Step 2 — call OpenAI and record the call as its own LLM span.
        prompt = f"Use this context:\n{context}\n\nQuestion: {question}"
        with t.span("openai.chat", span_type="llm") as s:
            s.set_model("gpt-4o-mini")
            s.set_input(prompt)

            start = time.monotonic()
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a concise assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            answer = (resp.choices[0].message.content or "").strip()
            s.set_output(answer)
            if resp.usage is not None:
                s.set_tokens(
                    prompt=resp.usage.prompt_tokens,
                    completion=resp.usage.completion_tokens,
                )
            s.set_metadata(provider_latency_ms=elapsed_ms)

        t.set_output(answer)
        if resp.usage is not None:
            # Rough cost estimate so the trace dashboard has a non-null value.
            t.set_cost(
                resp.usage.prompt_tokens * 0.00000015
                + resp.usage.completion_tokens * 0.0000006
            )
        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    print(f"basic_trace: emitted trace {trace_id}")
