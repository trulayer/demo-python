"""End-to-end RAG pipeline traced with TruLayer.

Pipeline stages (each becomes a span):

  1. embed-query       (span_type="default")  — OpenAI text-embedding-3-small
  2. retrieve-docs     (span_type="retrieval") — cosine similarity in-memory
  3. generate-answer   (span_type="llm")       — OpenAI chat.completions

The corpus is tiny and in-memory — the goal is to show the *shape* of a
RAG trace, not to be a real search system. Swap `_CORPUS` and `_retrieve`
for your own store and the tracing code stays the same.
"""
from __future__ import annotations

import math

from examples._config import build_openai_client, init_client


_CORPUS: dict[str, str] = {
    "paris": "The Eiffel Tower is a wrought-iron lattice tower in Paris, France.",
    "rome": "The Colosseum is a large amphitheatre in the centre of Rome, Italy.",
    "berlin": "The Brandenburg Gate is an 18th-century neoclassical monument in Berlin, Germany.",
    "tokyo": "Tokyo Tower is a communications and observation tower in Shiba-koen, Tokyo.",
}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _embed(openai_client, text: str) -> list[float]:
    resp = openai_client.embeddings.create(model="text-embedding-3-small", input=text)
    return list(resp.data[0].embedding)


def main() -> str:
    client = init_client()
    openai_client = build_openai_client()

    question = "Which city is the Eiffel Tower in?"

    with client.trace(name="rag-query", tags=["demo", "rag"]) as t:
        t.set_input(question)

        # ---- 1. embed the query ------------------------------------------
        with t.span("embed-query", span_type="default") as s:
            s.set_model("text-embedding-3-small")
            s.set_input(question)
            q_vec = _embed(openai_client, question)
            s.set_output(f"vector[{len(q_vec)}]")

        # ---- 2. retrieve top-k documents by cosine similarity ------------
        with t.span("retrieve-docs", span_type="retrieval") as s:
            s.set_input(question)
            # Embed each corpus document (in a real system these live in a
            # vector DB and are pre-computed).
            scored: list[tuple[str, float]] = []
            for doc_id, doc in _CORPUS.items():
                d_vec = _embed(openai_client, doc)
                scored.append((doc_id, _cosine(q_vec, d_vec)))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_k = scored[:2]
            retrieved = [_CORPUS[doc_id] for doc_id, _ in top_k]
            s.set_output("\n---\n".join(retrieved))
            s.set_metadata(
                top_k=[{"doc": d, "score": round(sc, 4)} for d, sc in top_k],
                corpus_size=len(_CORPUS),
            )

        # ---- 3. generate the answer --------------------------------------
        context_block = "\n".join(f"- {d}" for d in retrieved)
        prompt = (
            f"Answer the user's question using only the context.\n\n"
            f"Context:\n{context_block}\n\n"
            f"Question: {question}"
        )
        with t.span("generate-answer", span_type="llm") as s:
            s.set_model("gpt-4o-mini")
            s.set_input(prompt)
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Answer strictly from the given context."},
                    {"role": "user", "content": prompt},
                ],
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

    client.shutdown(timeout=2.0)
    return trace_id


if __name__ == "__main__":
    trace_id = main()
    print(f"rag_pipeline: emitted trace {trace_id}")
