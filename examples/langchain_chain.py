"""LangChain retrieval-augmented chain with TruLayer auto-instrumentation.

Demonstrates `instrument_langchain(client)` which returns a
`BaseCallbackHandler` that you attach to any LangChain runnable. Every
chain step (retriever, LLM call, output parse) emits a span into the
current TruLayer trace -- no per-call span code in your pipeline.

Pipeline:

    FakeRetriever  -->  prompt_template  -->  ChatOpenAI  -->  StrOutputParser

The retriever returns hardcoded documents (no vector DB needed). The
callback handler sits on the full chain; `client.trace(...)` defines the
outer trace boundary.

Run it with:

    uv run python -m examples.langchain_chain

Set `OPENAI_API_KEY` + `TRULAYER_*` in `.env` for real runs, or
`TRULAYER_DEMO_MOCK=1` for an offline run.
"""
from __future__ import annotations

import os
from typing import Any

from trulayer import instrument_langchain

from examples._config import init_client, is_mock_mode, openai_mock_httpx_client


class _FakeRetriever:
    """Minimal retriever that returns hardcoded documents.

    Implements the LangChain Runnable protocol (`.invoke()`) so it can
    sit in a LCEL pipe without pulling in a full vector store.
    """

    _docs = [
        "The Eiffel Tower is a wrought-iron lattice tower in Paris, built in 1889.",
        "It stands 330 metres tall and is the most-visited paid monument in the world.",
    ]

    def invoke(self, query: str, config: dict[str, Any] | None = None) -> str:
        """Return fake retrieved documents as a single string."""
        return "\n".join(self._docs)

    def batch(self, inputs: list[str], **kwargs: Any) -> list[str]:
        return [self.invoke(q) for q in inputs]


def _build_chain() -> tuple[object, object]:
    """Build a retrieval-augmented chain and return (chain, retriever)."""
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_openai import ChatOpenAI

    retriever = _FakeRetriever()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the question using only the provided context.\n\nContext:\n{context}"),
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

    # LCEL chain: retrieve context in parallel with passing the question
    # through, then format into the prompt, call LLM, parse output.
    chain = (
        {"context": retriever.invoke, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever


def main() -> str:
    client = init_client()
    handler = instrument_langchain(client)
    chain, _ = _build_chain()

    question = "What is one must-see landmark in Paris?"

    with client.trace(
        name="langchain-rag",
        tags=["demo", "langchain"],
        metadata={"example": "langchain_chain.py"},
    ) as t:
        t.set_input(question)
        # `callbacks` is threaded through LangChain's runnable config;
        # every LLM call in the chain invokes the handler automatically.
        answer = chain.invoke(question, config={"callbacks": [handler]})
        t.set_output(str(answer).strip())
        trace_id = t._data.id

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    print(f"langchain_chain: emitted trace {trace_id}")
