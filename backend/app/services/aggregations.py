from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session


def _default_since(since: datetime | None) -> datetime:
    return since or (datetime.now(UTC) - timedelta(days=14))


def overview_metrics(db: Session, since: datetime | None = None, until: datetime | None = None) -> dict:
    since = _default_since(since)
    until = until or datetime.now(UTC)
    row = db.execute(
        text(
            """
            SELECT
                count(*) AS request_count,
                count(*) FILTER (WHERE status = 'error') AS error_count,
                coalesce(avg(latency_ms), 0) AS avg_latency_ms,
                coalesce(percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms), 0) AS p50_latency_ms,
                coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms), 0) AS p95_latency_ms,
                coalesce(percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms), 0) AS p99_latency_ms,
                coalesce(avg(ttft_ms), 0) AS avg_ttft_ms,
                coalesce(sum(cost_usd), 0) AS total_cost_usd,
                coalesce(sum(input_tokens), 0) AS total_input_tokens,
                coalesce(sum(output_tokens), 0) AS total_output_tokens,
                coalesce(sum(cache_read_tokens), 0) AS total_cache_read_tokens
            FROM traces
            WHERE started_at BETWEEN :since AND :until
            """
        ),
        {"since": since, "until": until},
    ).mappings().first()

    request_count = row["request_count"] or 0
    error_count = row["error_count"] or 0
    return {
        "since": since,
        "until": until,
        "request_count": request_count,
        "error_count": error_count,
        "error_rate": (error_count / request_count) if request_count else 0.0,
        "avg_latency_ms": float(row["avg_latency_ms"]),
        "p50_latency_ms": float(row["p50_latency_ms"]),
        "p95_latency_ms": float(row["p95_latency_ms"]),
        "p99_latency_ms": float(row["p99_latency_ms"]),
        "avg_ttft_ms": float(row["avg_ttft_ms"]),
        "total_cost_usd": float(row["total_cost_usd"]),
        "total_input_tokens": int(row["total_input_tokens"]),
        "total_output_tokens": int(row["total_output_tokens"]),
        "total_cache_read_tokens": int(row["total_cache_read_tokens"]),
    }


def latency_timeseries(db: Session, bucket: str = "1 hour", since: datetime | None = None) -> list[dict]:
    since = _default_since(since)
    rows = db.execute(
        text(
            """
            SELECT
                date_trunc(:trunc_unit, started_at) AS bucket,
                coalesce(avg(latency_ms), 0) AS avg_latency_ms,
                coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms), 0) AS p95_latency_ms,
                count(*) AS request_count
            FROM traces
            WHERE started_at >= :since
            GROUP BY bucket
            ORDER BY bucket
            """
        ),
        {"since": since, "trunc_unit": "hour" if bucket == "1 hour" else "day"},
    ).mappings().all()
    return [dict(r) for r in rows]


def cost_timeseries(db: Session, bucket: str = "1 day", since: datetime | None = None) -> list[dict]:
    since = _default_since(since)
    rows = db.execute(
        text(
            """
            SELECT
                date_trunc(:trunc_unit, started_at) AS bucket,
                coalesce(sum(cost_usd), 0) AS cost_usd,
                count(*) AS request_count
            FROM traces
            WHERE started_at >= :since
            GROUP BY bucket
            ORDER BY bucket
            """
        ),
        {"since": since, "trunc_unit": "day" if bucket == "1 day" else "hour"},
    ).mappings().all()
    return [dict(r) for r in rows]


def cost_breakdown(db: Session, group_by: str = "model_id", since: datetime | None = None) -> list[dict]:
    since = _default_since(since)
    column = "model_id" if group_by == "model_id" else "prompt_version_id"
    rows = db.execute(
        text(
            f"""
            SELECT
                {column} AS group_key,
                coalesce(sum(cost_usd), 0) AS cost_usd,
                coalesce(sum(cache_read_tokens), 0) AS cache_read_tokens,
                coalesce(sum(input_tokens), 0) AS input_tokens,
                count(*) AS request_count
            FROM traces
            WHERE started_at >= :since
            GROUP BY {column}
            ORDER BY cost_usd DESC
            """
        ),
        {"since": since},
    ).mappings().all()
    return [dict(r) for r in rows]


def recent_errors(db: Session, since: datetime | None = None, limit: int = 50) -> list[dict]:
    since = _default_since(since)
    rows = db.execute(
        text(
            """
            SELECT trace_id, name, started_at, error_type, model_id, retry_count
            FROM traces
            WHERE status = 'error' AND started_at >= :since
            ORDER BY started_at DESC
            LIMIT :limit
            """
        ),
        {"since": since, "limit": limit},
    ).mappings().all()
    return [dict(r) for r in rows]
