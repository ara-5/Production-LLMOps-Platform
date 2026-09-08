"""LLM-as-judge scoring for hallucination, faithfulness, and relevance.

Uses structured JSON output (`output_config.format`) on the Anthropic
Messages API so scores parse reliably with no assistant-prefill trick.
Each judge call is itself run through TraceClient.llm_call (span_kind="judge")
inside its own trace, so judge latency/tokens/cost are tracked exactly like
any other LLM call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from llmops_sdk import TraceClient

JUDGE_SCHEMA_COMMON = {
    "verdict": {"type": "string"},
    "score": {"type": "number"},
    "reasoning": {"type": "string"},
}

HALLUCINATION_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["hallucinated", "not_hallucinated", "partial"]},
            "score": {"type": "number", "description": "0.0 = fully hallucinated, 1.0 = fully grounded in context"},
            "reasoning": {"type": "string"},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["verdict", "score", "reasoning", "unsupported_claims"],
        "additionalProperties": False,
    },
}

FAITHFULNESS_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["faithful", "unfaithful", "partial"]},
            "score": {"type": "number", "description": "0.0-1.0 fraction of answer claims supported by context"},
            "reasoning": {"type": "string"},
        },
        "required": ["verdict", "score", "reasoning"],
        "additionalProperties": False,
    },
}

RELEVANCE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["relevant", "irrelevant", "partial"]},
            "score": {"type": "number", "description": "0.0-1.0 how well the answer addresses the question"},
            "reasoning": {"type": "string"},
        },
        "required": ["verdict", "score", "reasoning"],
        "additionalProperties": False,
    },
}

_HALLUCINATION_PROMPT = """You are an expert factuality grader for a RAG system. Given the retrieved \
CONTEXT and the ANSWER produced by the system, determine whether the answer contains claims that are \
NOT supported by the context (hallucinations).

CONTEXT:
{context}

ANSWER:
{answer}

Grade strictly: only treat a claim as supported if it is directly stated or clearly implied by the context. \
Respond with the required JSON only."""

_FAITHFULNESS_PROMPT = """You are grading the faithfulness (groundedness) of an ANSWER against the retrieved \
CONTEXT it was generated from. Faithfulness measures what fraction of the answer's claims are directly \
traceable to the context, independent of whether the answer is a good response to any question.

CONTEXT:
{context}

ANSWER:
{answer}

Respond with the required JSON only."""

_RELEVANCE_PROMPT = """You are grading answer relevance: does the ANSWER actually address the QUESTION that \
was asked, regardless of factual correctness?

QUESTION:
{question}

ANSWER:
{answer}

Respond with the required JSON only."""


@dataclass
class JudgeResult:
    score: float
    passed: bool | None
    reasoning: str
    raw: dict
    judge_trace_id: str
    judge_model: str


def _run_judge(
    trace_client: TraceClient,
    *,
    trace_name: str,
    prompt: str,
    schema: dict,
    judge_model: str,
    pass_threshold: float = 0.7,
) -> JudgeResult:
    with trace_client.trace(trace_name, tags={"role": "judge"}) as trace:
        result = trace.llm_call(
            model=judge_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            output_config={"format": schema},
            span_kind="judge",
            span_name=trace_name,
        )
    data = json.loads(result.text)
    score = float(data["score"])
    return JudgeResult(
        score=score,
        passed=score >= pass_threshold,
        reasoning=data.get("reasoning", ""),
        raw=data,
        judge_trace_id=trace.trace_id,
        judge_model=judge_model,
    )


def score_hallucination(
    answer: str, context: list[str], trace_client: TraceClient, judge_model: str = "claude-opus-5"
) -> JudgeResult:
    prompt = _HALLUCINATION_PROMPT.format(context="\n\n".join(context), answer=answer)
    result = _run_judge(
        trace_client,
        trace_name="eval.hallucination",
        prompt=prompt,
        schema=HALLUCINATION_SCHEMA,
        judge_model=judge_model,
    )
    # For hallucination, "score" is groundedness (higher = better = less hallucinated).
    return result


def score_faithfulness(
    answer: str, context: list[str], trace_client: TraceClient, judge_model: str = "claude-opus-5"
) -> JudgeResult:
    prompt = _FAITHFULNESS_PROMPT.format(context="\n\n".join(context), answer=answer)
    return _run_judge(
        trace_client,
        trace_name="eval.faithfulness",
        prompt=prompt,
        schema=FAITHFULNESS_SCHEMA,
        judge_model=judge_model,
    )


def score_relevance(
    question: str, answer: str, trace_client: TraceClient, judge_model: str = "claude-opus-5"
) -> JudgeResult:
    prompt = _RELEVANCE_PROMPT.format(question=question, answer=answer)
    return _run_judge(
        trace_client,
        trace_name="eval.relevance",
        prompt=prompt,
        schema=RELEVANCE_SCHEMA,
        judge_model=judge_model,
    )
