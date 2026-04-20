"""Shared configuration for the demos.

Responsibilities:
  * Load environment variables from `.env` at the repo root.
  * Initialize the global TruLayer client.
  * Build OpenAI / Anthropic clients — either real (with your API key)
    or mock-transport clients (when `TRULAYER_DEMO_MOCK=1`), so the same
    example code runs in development and in CI.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

import trulayer


# ---------------------------------------------------------------------------
# .env loading (no external dependency — keeps the demo repo tiny)
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    here = Path(__file__).resolve().parent.parent
    for candidate in (Path.cwd() / ".env", here / ".env"):
        if not candidate.is_file():
            continue
        for raw in candidate.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def is_mock_mode() -> bool:
    return os.environ.get("TRULAYER_DEMO_MOCK", "").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# TruLayer client
# ---------------------------------------------------------------------------

def _project_name() -> str:
    # TRULAYER_PROJECT_ID is the deprecated alias from before we standardized
    # on names — keep it working so existing .env files don't break.
    return (
        os.environ.get("TRULAYER_PROJECT_NAME")
        or os.environ.get("TRULAYER_PROJECT_ID")
        or "demo"
    )


def init_client() -> trulayer.TruLayerClient:
    _load_dotenv()
    client = trulayer.init(
        api_key=os.environ.get("TRULAYER_API_KEY", "tl_demo"),
        project_name=_project_name(),
        endpoint=os.environ.get("TRULAYER_ENDPOINT", "http://127.0.0.1:8080"),
        flush_interval=0.2,
    )
    # The batch sender starts its event loop on a background thread. Wait
    # briefly for the loop to come up so that a shutdown() immediately
    # after a short example still drains the queue.
    deadline = time.monotonic() + 1.0
    while client._batch._loop is None and time.monotonic() < deadline:
        time.sleep(0.001)
    return client


# ---------------------------------------------------------------------------
# Provider clients: real or mock-transport
# ---------------------------------------------------------------------------

def _openai_mock_handler(request: httpx.Request) -> httpx.Response:
    import json as _json

    path = request.url.path
    if path.endswith("/chat/completions"):
        body = _json.loads(request.content.decode("utf-8") or "{}")
        has_tools = bool(body.get("tools"))
        has_tool_result = any(m.get("role") == "tool" for m in body.get("messages", []))
        # If the caller is running the agent example (tools were offered) and
        # hasn't fed a tool result back yet, return a canned tool_call so the
        # mock still exercises the tool-span path.
        if has_tools and not has_tool_result:
            return httpx.Response(200, json={
                "id": "chatcmpl-mock-tool",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4o-mini",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call_mock_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": _json.dumps({"city": "Paris"}),
                            },
                        }],
                    },
                    "finish_reason": "tool_calls",
                }],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            })
        return httpx.Response(200, json={
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o-mini",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Paris is the capital of France."},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        })
    if path.endswith("/embeddings"):
        return httpx.Response(200, json={
            "object": "list",
            "model": "text-embedding-3-small",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}],
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        })
    return httpx.Response(404, json={"error": {"message": f"unhandled path: {path}"}})


def _anthropic_mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/messages"):
        return httpx.Response(200, json={
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Paris is the capital of France."}],
            "model": "claude-3-5-sonnet-latest",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 8},
        })
    return httpx.Response(404, json={"error": {"message": "unhandled"}})


def build_openai_client() -> Any:
    """Return an `openai.OpenAI` instance — real or mock-transport.

    Raises RuntimeError with a friendly message if the user is in
    real mode but `OPENAI_API_KEY` is missing.
    """
    import openai  # imported here so the module imports even without the extra

    if is_mock_mode():
        return openai.OpenAI(
            api_key="sk-demo-mock",
            http_client=httpx.Client(transport=httpx.MockTransport(_openai_mock_handler)),
        )

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Put it in `.env` or export it, "
            "or set TRULAYER_DEMO_MOCK=1 for offline mode."
        )
    return openai.OpenAI(api_key=key)


def openai_mock_httpx_client() -> httpx.Client:
    """Return an httpx.Client whose transport mocks the OpenAI HTTP API.

    Useful for libraries (e.g. langchain_openai.ChatOpenAI) that accept
    a pre-built httpx client but not a raw handler.
    """
    return httpx.Client(transport=httpx.MockTransport(_openai_mock_handler))


def build_anthropic_client() -> Any:
    import anthropic

    if is_mock_mode():
        return anthropic.Anthropic(
            api_key="sk-ant-demo-mock",
            http_client=httpx.Client(transport=httpx.MockTransport(_anthropic_mock_handler)),
        )

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Put it in `.env` or export it, "
            "or set TRULAYER_DEMO_MOCK=1 for offline mode."
        )
    return anthropic.Anthropic(api_key=key)
