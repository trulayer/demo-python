"""End-to-end smoke tests: run each example against a mock ingestion
server and assert that traces / spans / feedback actually arrived.

Runs in `TRULAYER_DEMO_MOCK=1` mode so no provider API keys are
required. Tests are deterministic and offline.
"""
from __future__ import annotations

import importlib
import os
from typing import Any

import pytest

from examples import mock_server


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRULAYER_DEMO_MOCK", "1")
    monkeypatch.setenv("TRULAYER_API_KEY", "tl_test")
    monkeypatch.setenv("TRULAYER_PROJECT_NAME", "test-project")


@pytest.fixture
def mock_url() -> Any:
    with mock_server.run_mock_server() as url:
        yield url


def _all_traces(received: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [tr for batch in received["batches"] for tr in batch.get("traces", [])]


def _run(module_name: str) -> Any:
    # Fresh import each time — demos call trulayer.init() which resets the
    # global client, but reloading the module is cheap and keeps state clean.
    mod = importlib.import_module(f"examples.{module_name}")
    importlib.reload(mod)
    return mod.main()


@pytest.mark.parametrize(
    "example,expected_tags",
    [
        ("basic_trace", {"demo", "basic-trace"}),
        ("openai_auto", {"demo", "openai-auto"}),
        ("anthropic_auto", {"demo", "anthropic-auto"}),
        ("rag_pipeline", {"demo", "rag"}),
        ("agent", {"demo", "agent"}),
        ("langchain_chain", {"demo", "langchain"}),
        ("async_example", {"demo", "async"}),
    ],
)
def test_example_emits_trace(
    example: str,
    expected_tags: set[str],
    mock_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRULAYER_ENDPOINT", mock_url)

    _run(example)

    traces = _all_traces(mock_server.get_received())
    assert traces, f"{example}: no traces received"

    # All traces should belong to the demo project and carry the right tags.
    for tr in traces:
        assert tr["project_id"] == "test-project"
        assert expected_tags.issubset(set(tr.get("tags", [])))
        assert tr["input"]
        assert tr["output"]
        assert tr["ended_at"] is not None
        assert tr["spans"], f"{example}: trace {tr['id']} had no spans"


def test_feedback_flow(mock_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRULAYER_ENDPOINT", mock_url)

    trace_id, label = _run("feedback")

    received = mock_server.get_received()
    traces = _all_traces(received)
    assert any(tr["id"] == trace_id for tr in traces), "feedback trace missing in batches"

    feedback = received["feedback"]
    assert feedback, "no feedback received"
    assert feedback[0]["trace_id"] == trace_id
    assert feedback[0]["label"] == label
    assert feedback[0]["score"] == 1.0


def test_agent_emits_tool_spans(mock_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent example should exercise tool spans even in mock mode."""
    monkeypatch.setenv("TRULAYER_ENDPOINT", mock_url)

    _run("agent")
    traces = _all_traces(mock_server.get_received())
    assert traces, "agent emitted no traces"

    span_types = {s["span_type"] for tr in traces for s in tr["spans"]}
    assert "tool" in span_types, f"expected at least one tool span, got {span_types}"
    assert "llm" in span_types


def test_async_example_has_concurrent_spans(
    mock_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The async example should produce two LLM spans from concurrent tasks."""
    monkeypatch.setenv("TRULAYER_ENDPOINT", mock_url)

    _run("async_example")
    traces = _all_traces(mock_server.get_received())
    assert traces, "async_example emitted no traces"

    span_names = [s["name"] for s in traces[0]["spans"]]
    assert "ask-nyc" in span_names, f"missing ask-nyc span, got {span_names}"
    assert "ask-london" in span_names, f"missing ask-london span, got {span_names}"
    assert all(s["span_type"] == "llm" for s in traces[0]["spans"])


def test_rag_pipeline_has_three_stage_shape(
    mock_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRULAYER_ENDPOINT", mock_url)

    _run("rag_pipeline")
    traces = _all_traces(mock_server.get_received())
    assert traces, "rag_pipeline emitted no traces"

    span_names = [s["name"] for s in traces[0]["spans"]]
    assert "embed-query" in span_names
    assert "retrieve-docs" in span_names
    assert "generate-answer" in span_names
