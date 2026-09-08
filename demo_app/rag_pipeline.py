"""The instrumented demo RAG application: retrieves context from the fixed
Northwind Cloud corpus, then asks Claude to answer using that context. Every
call goes through TraceClient so the resulting trace/spans are exactly what
feeds the observability dashboard, the eval engine, and regression tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from llmops_sdk import TraceClient
from llmops_sdk import otel_attrs as attrs

from demo_app.retriever import RetrievedChunk, get_retriever


@dataclass
class RagAnswer:
    answer: str
    retrieved_doc_ids: list[str]
    sources: list[dict]
    trace_id: str
    cost_usd: float
    latency_ms: int


def render_template(template: str, question: str, context_chunks: list[RetrievedChunk]) -> str:
    context_block = "\n\n".join(f"[{c.doc_id}] {c.title}\n{c.text}" for c in context_chunks)
    return template.format(question=question, context=context_block)


def answer_question(
    *,
    question: str,
    prompt_version: Any,
    model_id: str,
    trace_client: TraceClient,
    k: int = 5,
    dataset_item_id: int | None = None,
    on_complete: Callable[[dict], None] | None = None,
) -> RagAnswer:
    retriever = get_retriever()
    with trace_client.trace(
        "rag.answer_question",
        prompt_version_id=getattr(prompt_version, "id", None),
        dataset_item_id=dataset_item_id,
        on_complete=on_complete,
    ) as trace:
        with trace.span("retrieve", kind="retrieval") as span:
            chunks = retriever.retrieve(question, k=k)
            span.set_attributes(**{
                attrs.LLMOPS_RETRIEVAL_DOC_IDS: [c.doc_id for c in chunks],
                attrs.LLMOPS_RETRIEVAL_SCORES: [c.score for c in chunks],
                attrs.LLMOPS_RETRIEVAL_CONTEXT: [c.text for c in chunks],
            })

        prompt = render_template(prompt_version.template, question, chunks)
        result = trace.llm_call(model=model_id, messages=[{"role": "user", "content": prompt}], max_tokens=1024)

        # Stash question/answer on the llm span so evaluate_trace() can later
        # re-score this trace without re-running the pipeline.
        trace.spans[-1].attributes[attrs.LLMOPS_QUESTION] = question
        trace.spans[-1].attributes[attrs.LLMOPS_ANSWER] = result.text

    return RagAnswer(
        answer=result.text,
        retrieved_doc_ids=[c.doc_id for c in chunks],
        sources=[{"doc_id": c.doc_id, "title": c.title, "score": c.score} for c in chunks],
        trace_id=trace.trace_id,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )
