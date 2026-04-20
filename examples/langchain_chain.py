"""LangChain chain with TruLayer auto-instrumentation via a callback.

`instrument_langchain(client)` returns a `BaseCallbackHandler` subclass
that you attach to any LangChain runnable. Every LLM / chat call the
chain makes emits a `langchain.llm` span into the current TruLayer
trace — no per-call span code in your pipeline.

Pipeline in this demo:

    prompt_template | ChatOpenAI | StrOutputParser

The handler sits on the chat model; `client.trace(...)` defines the
outer trace boundary.

    uv run python -m examples.langchain_chain

Set `OPENAI_API_KEY` + `TRULAYER_*` in `.env` for real runs, or
`TRULAYER_DEMO_MOCK=1` for an offline run.

If `LANGCHAIN_TRACING_V2=true` is set alongside `LANGCHAIN_API_KEY`,
LangSmith tracing is additionally enabled — TruLayer and LangSmith
record the same run via separate callback paths.
"""
from __future__ import annotations

import os

from trulayer import instrument_langchain

from examples._config import init_client, is_mock_mode, openai_mock_httpx_client


def _build_chain() -> object:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a concise travel guide. One sentence only."),
        ("human", "{question}"),
    ])

    if is_mock_mode():
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key="sk-demo-mock",
            temperature=0,
            http_client=openai_mock_httpx_client(),
        )
    else:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Put it in `.env` or export it, "
                "or set TRULAYER_DEMO_MOCK=1 for offline mode."
            )
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=key, temperature=0)

    return prompt | llm | StrOutputParser()


def main() -> str:
    client = init_client()
    handler = instrument_langchain(client)
    chain = _build_chain()

    question = "What is one must-see landmark in Paris?"

    with client.trace(
        name="langchain-qa",
        tags=["demo", "langchain"],
        metadata={"example": "langchain_chain.py"},
    ) as t:
        t.set_input(question)
        # `callbacks` is threaded through LangChain's runnable config;
        # every LLM call in the chain invokes the handler.
        answer = chain.invoke({"question": question}, config={"callbacks": [handler]})
        t.set_output(str(answer).strip())
        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    print(f"langchain_chain: emitted trace {trace_id}")
