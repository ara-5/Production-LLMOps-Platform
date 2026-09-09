from __future__ import annotations

from llmops_sdk import TraceClient
from llmops_sdk import otel_attrs as attrs
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.datasets import DatasetItem
from app.models.evals import EvalScore
from app.models.prompts import PromptVersion
from app.models.traces import Trace
from app.services.eval_engine import retrieval_metrics
from app.services.eval_engine.judges import (
    JudgeResult,
    score_faithfulness,
    score_hallucination,
    score_relevance,
)

DEFAULT_LLM_METRICS = ["hallucination", "faithfulness", "relevance"]
RETRIEVAL_METRICS = ["precision_at_k", "recall_at_k", "mrr", "ndcg"]


def _extract_qca(trace: Trace) -> tuple[str | None, str | None, list[str]]:
    """Pull question/answer/context back out of a persisted trace's spans."""
    question = None
    answer = None
    context: list[str] = []
    for span in trace.spans:
        if span.span_kind == "retrieval" and attrs.LLMOPS_RETRIEVAL_CONTEXT in span.attributes:
            context = span.attributes[attrs.LLMOPS_RETRIEVAL_CONTEXT]
        if span.span_kind == "llm":
            if attrs.LLMOPS_QUESTION in span.attributes:
                question = span.attributes[attrs.LLMOPS_QUESTION]
            if attrs.LLMOPS_ANSWER in span.attributes:
                answer = span.attributes[attrs.LLMOPS_ANSWER]
    return question, answer, context


def _save_score(db: Session, trace_id: str, metric_name: str, result: JudgeResult) -> EvalScore:
    row = EvalScore(
        trace_id=trace_id,
        metric_name=metric_name,
        score=result.score,
        passed=result.passed,
        reasoning=result.reasoning,
        judge_model=result.judge_model,
        judge_trace_id=result.judge_trace_id,
    )
    db.add(row)
    return row


def evaluate_trace(
    trace_id: str,
    db: Session,
    trace_client: TraceClient,
    judge_model: str,
    metrics: list[str] | None = None,
) -> list[EvalScore]:
    metrics = metrics or DEFAULT_LLM_METRICS
    trace = db.execute(select(Trace).where(Trace.trace_id == trace_id)).scalar_one()
    question, answer, context = _extract_qca(trace)
    if answer is None:
        raise ValueError(f"trace {trace_id} has no recorded answer to evaluate")

    saved: list[EvalScore] = []
    if "hallucination" in metrics:
        result = score_hallucination(answer, context, trace_client, judge_model)
        saved.append(_save_score(db, trace_id, "hallucination", result))
    if "faithfulness" in metrics:
        result = score_faithfulness(answer, context, trace_client, judge_model)
        saved.append(_save_score(db, trace_id, "faithfulness", result))
    if "relevance" in metrics and question is not None:
        result = score_relevance(question, answer, trace_client, judge_model)
        saved.append(_save_score(db, trace_id, "relevance", result))

    if trace.dataset_item_id is not None and any(m in metrics for m in RETRIEVAL_METRICS):
        item = db.get(DatasetItem, trace.dataset_item_id)
        if item and item.expected_retrieval_doc_ids:
            retrieved_ids = []
            for span in trace.spans:
                if span.span_kind == "retrieval" and attrs.LLMOPS_RETRIEVAL_DOC_IDS in span.attributes:
                    retrieved_ids = span.attributes[attrs.LLMOPS_RETRIEVAL_DOC_IDS]
            relevant_ids = set(item.expected_retrieval_doc_ids)
            grades = item.relevance_grades or None
            k = len(retrieved_ids) or 5
            score_map = {
                "precision_at_k": retrieval_metrics.precision_at_k(retrieved_ids, relevant_ids, k),
                "recall_at_k": retrieval_metrics.recall_at_k(retrieved_ids, relevant_ids, k),
                "mrr": retrieval_metrics.mrr(retrieved_ids, relevant_ids),
                "ndcg": retrieval_metrics.ndcg_at_k(retrieved_ids, relevant_ids, k, grades),
            }
            for name, value in score_map.items():
                if name in metrics:
                    row = EvalScore(trace_id=trace_id, metric_name=name, score=value, passed=value >= 0.5)
                    db.add(row)
                    saved.append(row)

    db.commit()
    for row in saved:
        db.refresh(row)
    return saved


def evaluate_dataset_item(
    item: DatasetItem,
    prompt_version: PromptVersion,
    model_id: str,
    trace_client: TraceClient,
    db: Session,
    judge_model: str,
    k: int = 5,
) -> tuple[str, list[EvalScore]]:
    """Run the demo RAG pipeline for one golden dataset item, persist the
    resulting trace, then score it. Returns (trace_id, eval_scores)."""
    from demo_app.rag_pipeline import (
        answer_question,  # local import avoids a circular dependency at module load
    )

    rag_answer = answer_question(
        question=item.question,
        prompt_version=prompt_version,
        model_id=model_id,
        trace_client=trace_client,
        k=k,
        dataset_item_id=item.id,
    )
    # The pipeline ships its own trace synchronously; re-read it back so we
    # can score against the persisted spans (same contract evaluate_trace uses).
    scores = evaluate_trace(rag_answer.trace_id, db, trace_client, judge_model)
    return rag_answer.trace_id, scores
