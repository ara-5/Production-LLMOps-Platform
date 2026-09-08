"""Deterministic retrieval-quality metrics: precision@k, recall@k, MRR, NDCG.

No API calls — pure functions of (retrieved_ids, relevant_ids[, relevance_grades]).
"""

from __future__ import annotations

import math


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(top_k)


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def _dcg(gains: list[float]) -> float:
    return sum(gain / math.log2(idx + 2) for idx, gain in enumerate(gains))


def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
    relevance_grades: dict[str, int] | None = None,
) -> float:
    """Binary relevance by default (grade 1 for any id in relevant_ids); pass
    relevance_grades for graded relevance (e.g. {doc_id: 0-3})."""
    top_k = retrieved_ids[:k]
    if not top_k or not relevant_ids:
        return 0.0

    def gain(doc_id: str) -> float:
        if relevance_grades is not None:
            return float(relevance_grades.get(doc_id, 0))
        return 1.0 if doc_id in relevant_ids else 0.0

    actual_gains = [gain(doc_id) for doc_id in top_k]
    dcg = _dcg(actual_gains)

    if relevance_grades is not None:
        ideal_gains = sorted(relevance_grades.values(), reverse=True)[:k]
    else:
        ideal_gains = [1.0] * min(len(relevant_ids), k)
    idcg = _dcg([float(g) for g in ideal_gains])

    return dcg / idcg if idcg > 0 else 0.0
