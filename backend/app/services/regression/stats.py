"""Baseline-vs-current comparison for regression test runs."""

from __future__ import annotations

from dataclasses import dataclass

# Default per-metric thresholds. Positive threshold = "current must not drop
# by more than this much"; latency/cost use a different sign convention
# (current must not *rise* by more than the threshold) — handled explicitly.
DEFAULT_QUALITY_THRESHOLDS = {
    "hallucination": -0.05,
    "faithfulness": -0.05,
    "relevance": -0.05,
    "precision_at_k": -0.10,
    "recall_at_k": -0.10,
    "mrr": -0.10,
    "ndcg": -0.10,
}
LATENCY_P95_REGRESSION_MS = 500
COST_REGRESSION_RATIO = 0.25  # current cost must not exceed baseline by more than 25%


@dataclass
class MetricComparison:
    metric_name: str
    baseline: float
    current: float
    delta: float
    threshold: float
    passed: bool


@dataclass
class RegressionResult:
    passed: bool
    comparisons: list[MetricComparison]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "comparisons": [c.__dict__ for c in self.comparisons],
        }


def compare_to_baseline(
    current: dict[str, float],
    baseline: dict[str, float],
    thresholds: dict[str, float] | None = None,
) -> RegressionResult:
    thresholds = thresholds or DEFAULT_QUALITY_THRESHOLDS
    comparisons: list[MetricComparison] = []

    for metric_name, threshold in thresholds.items():
        if metric_name not in current or metric_name not in baseline:
            continue
        delta = current[metric_name] - baseline[metric_name]
        passed = delta >= threshold
        comparisons.append(
            MetricComparison(metric_name, baseline[metric_name], current[metric_name], delta, threshold, passed)
        )

    if "latency_p95_ms" in current and "latency_p95_ms" in baseline:
        delta = current["latency_p95_ms"] - baseline["latency_p95_ms"]
        passed = delta <= LATENCY_P95_REGRESSION_MS
        comparisons.append(
            MetricComparison("latency_p95_ms", baseline["latency_p95_ms"], current["latency_p95_ms"], delta, LATENCY_P95_REGRESSION_MS, passed)
        )

    if "cost_usd_mean" in current and "cost_usd_mean" in baseline and baseline["cost_usd_mean"] > 0:
        ratio = (current["cost_usd_mean"] - baseline["cost_usd_mean"]) / baseline["cost_usd_mean"]
        passed = ratio <= COST_REGRESSION_RATIO
        comparisons.append(
            MetricComparison("cost_usd_mean", baseline["cost_usd_mean"], current["cost_usd_mean"], ratio, COST_REGRESSION_RATIO, passed)
        )

    overall_passed = all(c.passed for c in comparisons) if comparisons else True
    return RegressionResult(passed=overall_passed, comparisons=comparisons)
