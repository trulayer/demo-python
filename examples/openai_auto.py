"""OpenAI auto-instrumentation — zero per-call span code.

`instrument_openai(client)` monkey-patches the OpenAI SDK so every
`chat.completions.create` call inside an active trace automatically
produces an `openai.chat` span with model, tokens, input, and output.

Use this when you want tracing without threading spans through your
application code. You still own the *trace* boundary (one per request,
per job, etc.); TruLayer fills in the provider-call spans for you.

Run it with:

    uv run python -m examples.openai_auto
"""
from __future__ import annotations

from trulayer import instrument_openai

from examples._config import build_openai_client, init_client


SYSTEM_PROMPT = (
    "You are a helpful travel assistant. Answer in one sentence. "
    "Be specific but brief."
)

USER_QUESTIONS = [
    "Name one must-see landmark in Paris.",
    "Name one must-see landmark in Rome.",
    "Name one must-see landmark in Tokyo.",
]


def main() -> list[str]:
    client = init_client()
    instrument_openai(client)  # patches openai.chat.completions.create
    openai_client = build_openai_client()

    trace_ids: list[str] = []
    for question in USER_QUESTIONS:
        # One trace per user request — the auto-instrumented OpenAI call
        # emits its own LLM span inside.
        with client.trace(name="travel-qa", tags=["demo", "openai-auto"]) as t:
            t.set_input(question)
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                temperature=0,
            )
            t.set_output((resp.choices[0].message.content or "").strip())
            trace_ids.append(t._data.id)

    client.shutdown(timeout=2.0)
    return trace_ids


if __name__ == "__main__":
    ids = main()
    print(f"openai_auto: emitted {len(ids)} traces -> {ids}")
