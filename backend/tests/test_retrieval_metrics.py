import pytest

from app.services.eval_engine.retrieval_metrics import mrr, ndcg_at_k, precision_at_k, recall_at_k


def test_precision_at_k_all_relevant():
    assert precision_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == 1.0


def test_precision_at_k_partial():
    # 2 of top 4 are relevant
    assert precision_at_k(["a", "x", "b", "y"], {"a", "b"}, k=4) == pytest.approx(0.5)


def test_precision_at_k_empty_retrieval():
    assert precision_at_k([], {"a"}, k=5) == 0.0


def test_recall_at_k_finds_all():
    assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=3) == 1.0


def test_recall_at_k_partial():
    # only 1 of 2 relevant docs retrieved in top 2
    assert recall_at_k(["a", "x"], {"a", "b"}, k=2) == pytest.approx(0.5)


def test_recall_at_k_no_relevant_docs():
    assert recall_at_k(["a", "b"], set(), k=2) == 0.0


def test_mrr_first_hit():
    assert mrr(["a", "b", "c"], {"a"}) == 1.0


def test_mrr_third_hit():
    assert mrr(["x", "y", "a"], {"a"}) == pytest.approx(1 / 3)


def test_mrr_no_hit():
    assert mrr(["x", "y", "z"], {"a"}) == 0.0


def test_ndcg_perfect_ranking_binary_relevance():
    # both relevant docs retrieved, in the best possible order
    assert ndcg_at_k(["a", "b", "x"], {"a", "b"}, k=3) == pytest.approx(1.0)


def test_ndcg_worse_ranking_scores_lower_than_perfect():
    perfect = ndcg_at_k(["a", "b", "x"], {"a", "b"}, k=3)
    worse = ndcg_at_k(["x", "a", "b"], {"a", "b"}, k=3)
    assert worse < perfect


def test_ndcg_no_relevant_docs_in_corpus():
    assert ndcg_at_k(["a", "b"], set(), k=2) == 0.0


def test_ndcg_graded_relevance():
    grades = {"a": 3, "b": 1}
    # retrieving the higher-graded doc first should score higher than reversed order
    best_order = ndcg_at_k(["a", "b"], {"a", "b"}, k=2, relevance_grades=grades)
    worst_order = ndcg_at_k(["b", "a"], {"a", "b"}, k=2, relevance_grades=grades)
    assert best_order == pytest.approx(1.0)
    assert worst_order < best_order
