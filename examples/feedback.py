"""Emit a trace, remember its ID, then attach feedback.

Feedback is how you label traces as "good" / "bad" / "neutral" — either
from end users (thumbs-up buttons, corrections) or from offline
reviewers. In TruLayer, feedback is a separate write path that
references a trace by ID, so it can arrive minutes or days after the
trace itself.

This demo runs an LLM call, flushes the trace, then POSTs a "good"
label against it.
"""
from __future__ import annotations

from examples._config import build_openai_client, init_client


def main() -> tuple[str, str]:
    client = init_client()
    openai_client = build_openai_client()

    question = "In one sentence, what is the Louvre?"

    with client.trace(name="feedback-demo", tags=["demo", "feedback"]) as t:
        t.set_input(question)
        with t.span("openai.chat", span_type="llm") as s:
            s.set_model("gpt-4o-mini")
            s.set_input(question)
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": question}],
                temperature=0,
            )
            answer = (resp.choices[0].message.content or "").strip()
            s.set_output(answer)
            if resp.usage is not None:
                s.set_tokens(
                    prompt=resp.usage.prompt_tokens,
                    completion=resp.usage.completion_tokens,
                )
        t.set_output(answer)
        trace_id = t._data.id

    # Make sure the trace is ingested before feedback references it.
    client.shutdown(timeout=2.0)

    client.feedback(
        trace_id=trace_id,
        label="good",
        score=1.0,
        comment="Accurate and concise.",
        metadata={"source": "demo", "reviewer": "auto"},
    )
    return trace_id, "good"


if __name__ == "__main__":
    trace_id, label = main()
    print(f"feedback: trace={trace_id} label={label}")
