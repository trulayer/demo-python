"""Tool-calling agent traced end-to-end.

Runs a small OpenAI function-calling loop with two tools:
  * `get_weather(city)`  — returns a canned weather string
  * `calculate(expr)`    — evaluates a simple arithmetic expression

Each tool invocation becomes a `span_type="tool"` span, and each LLM
turn becomes a `span_type="llm"` span. The result is a tree you can
inspect in TruLayer showing exactly what the model did and why.
"""
from __future__ import annotations

import ast
import json
import operator
from typing import Any

from examples._config import build_openai_client, init_client


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a simple arithmetic expression (e.g. '7 * 6').",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
]

_WEATHER_TABLE = {
    "paris": {"temp_c": 22, "conditions": "sunny"},
    "rome": {"temp_c": 28, "conditions": "clear"},
    "tokyo": {"temp_c": 18, "conditions": "light rain"},
}

_SAFE_OPS: dict[type[ast.AST], Any] = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(expr: str) -> float:
    """Evaluate arithmetic without `eval` — only numbers and + - * / **."""
    def _walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
            return _SAFE_OPS[type(node.op)](_walk(node.left), _walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
            return _SAFE_OPS[type(node.op)](_walk(node.operand))
        raise ValueError(f"unsupported expression: {ast.dump(node)}")

    return _walk(ast.parse(expr, mode="eval"))


def _call_tool(name: str, args: dict[str, Any]) -> str:
    if name == "get_weather":
        city = str(args.get("city", "")).lower()
        data = _WEATHER_TABLE.get(city, {"temp_c": 20, "conditions": "unknown"})
        return json.dumps({"city": city, **data})
    if name == "calculate":
        return json.dumps({"result": _safe_eval(str(args.get("expression", "0")))})
    raise ValueError(f"unknown tool: {name}")


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You are a helpful assistant. Use the provided tools when needed. "
    "Keep your final answer to one sentence."
)

_MAX_TURNS = 5


def main() -> str:
    client = init_client()
    openai_client = build_openai_client()

    task = (
        "Look up the weather in Paris and Tokyo. "
        "If Paris is warmer than Tokyo, tell me what 7 * 6 is. "
        "Otherwise, tell me what 8 * 9 is."
    )

    with client.trace(name="tool-agent", tags=["demo", "agent"]) as t:
        t.set_input(task)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": task},
        ]

        for turn in range(_MAX_TURNS):
            with t.span(f"agent.turn-{turn}", span_type="llm") as s:
                s.set_model("gpt-4o-mini")
                s.set_input(json.dumps(messages[-1]))
                resp = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=_TOOL_SCHEMAS,
                    tool_choice="auto",
                    temperature=0,
                )
                msg = resp.choices[0].message
                messages.append(msg.model_dump(exclude_none=True))
                s.set_output(msg.content or "<tool call>")
                if resp.usage is not None:
                    s.set_tokens(
                        prompt=resp.usage.prompt_tokens,
                        completion=resp.usage.completion_tokens,
                    )

            # No tool calls -> we have the final answer.
            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                t.set_output((msg.content or "").strip())
                break

            for tc in tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                with t.span(f"tool.{name}", span_type="tool") as s:
                    s.set_input(json.dumps(args))
                    s.set_metadata(tool=name, tool_call_id=tc.id)
                    try:
                        result = _call_tool(name, args)
                        s.set_output(result)
                    except Exception as exc:  # recorded on the span automatically
                        s.set_output(f"error: {exc}")
                        raise
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": result,
                })
        else:
            # Loop exhausted without a tool-free reply.
            t.set_output("<max turns reached>")

        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    print(f"agent: emitted trace {trace_id}")
