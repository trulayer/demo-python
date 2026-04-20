"""Run every example against a local mock ingestion server.

Forces `TRULAYER_DEMO_MOCK=1` so no real provider keys are required,
then spins up `mock_server.run_mock_server`, points `TRULAYER_ENDPOINT`
at it, runs each example in sequence, and prints a summary of the
payloads the server received. This is the canonical end-to-end check.

    uv run python -m examples.run_all
"""
from __future__ import annotations

import importlib
import os

from examples import mock_server


# Ordered so the stdout log reads top-down, simple -> complex.
EXAMPLES = [
    "basic_trace",
    "openai_auto",
    "anthropic_auto",
    "langchain_chain",
    "rag_pipeline",
    "agent",
    "streaming",
    "feedback",
]


def main() -> None:
    os.environ["TRULAYER_DEMO_MOCK"] = "1"
    os.environ.setdefault("TRULAYER_API_KEY", "tl_demo")
    os.environ.setdefault("TRULAYER_PROJECT_NAME", "demo")

    with mock_server.run_mock_server() as url:
        os.environ["TRULAYER_ENDPOINT"] = url
        print(f"mock ingestion server: {url}\n")

        for name in EXAMPLES:
            mod = importlib.import_module(f"examples.{name}")
            try:
                result = mod.main()
            except Exception as exc:
                print(f"  {name:<18} FAILED: {exc}")
                continue
            print(f"  {name:<18} -> {result}")

        received = mock_server.get_received()
        traces = [tr for b in received["batches"] for tr in b.get("traces", [])]
        span_count = sum(len(tr.get("spans", [])) for tr in traces)
        print(
            f"\nserver received: {len(received['batches'])} batches, "
            f"{len(traces)} traces, {span_count} spans, "
            f"{len(received['feedback'])} feedback"
        )


if __name__ == "__main__":
    main()
