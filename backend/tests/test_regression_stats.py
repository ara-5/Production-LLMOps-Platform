import pytest
from app.services.regression.stats import compare_to_baseline


def test_no_regression_when_scores_improve():
    current = {"faithfulness": 0.92, "latency_p95_ms": 900, "cost_usd_mean": 0.01}
    baseline = {"faithfulness": 0.88, "latency_p95_ms": 850, "cost_usd_mean": 0.01}
    result = compare_to_baseline(current, baseline)
    assert result.passed is True


def test_quality_regression_fails():
    current = {"faithfulness": 0.70}
    baseline = {"faithfulness": 0.90}
    result = compare_to_baseline(current, baseline)
    assert result.passed is False
    faithfulness = next(c for c in result.comparisons if c.metric_name == "faithfulness")
    assert faithfulness.passed is False
    assert faithfulness.delta == pytest.approx(-0.20)


def test_small_quality_dip_within_threshold_passes():
    # default threshold for faithfulness is -0.05
    current = {"faithfulness": 0.87}
    baseline = {"faithfulness": 0.90}
    result = compare_to_baseline(current, baseline)
    assert result.passed is True


def test_latency_regression_fails():
    current = {"latency_p95_ms": 2000}
    baseline = {"latency_p95_ms": 1000}
    result = compare_to_baseline(current, baseline)
    assert result.passed is False


def test_cost_regression_fails_when_over_threshold():
    current = {"cost_usd_mean": 0.02}
    baseline = {"cost_usd_mean": 0.01}  # +100% > 25% threshold
    result = compare_to_baseline(current, baseline)
    assert result.passed is False


def test_missing_metrics_are_skipped_not_failed():
    result = compare_to_baseline({"faithfulness": 0.9}, {})
    assert result.comparisons == []
    assert result.passed is True
