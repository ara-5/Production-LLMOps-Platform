import uuid
from datetime import UTC, datetime

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _ingest_payload(trace_id: str) -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "trace": {
            "trace_id": trace_id,
            "name": "test.trace",
            "started_at": now,
            "ended_at": now,
            "latency_ms": 123,
            "ttft_ms": 45,
            "tokens_per_sec": 12.5,
            "status": "ok",
            "model_id": "claude-sonnet-5",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost_usd": 0.0007,
            "is_synthetic": True,
        },
        "spans": [
            {
                "span_id": str(uuid.uuid4()),
                "name": "llm.generate",
                "span_kind": "llm",
                "started_at": now,
                "ended_at": now,
                "latency_ms": 123,
                "status": "ok",
                "input_tokens": 100,
                "output_tokens": 50,
                "cost_usd": 0.0007,
                "attributes": {"gen_ai.request.model": "claude-sonnet-5"},
            }
        ],
    }


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ingest_and_get_trace_round_trip():
    trace_id = str(uuid.uuid4())
    ingest_resp = client.post("/api/traces/ingest", json=_ingest_payload(trace_id))
    assert ingest_resp.status_code == 201
    assert ingest_resp.json()["status"] == "ingested"

    get_resp = client.get(f"/api/traces/{trace_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["trace_id"] == trace_id
    assert body["model_id"] == "claude-sonnet-5"
    assert body["input_tokens"] == 100
    assert len(body["spans"]) == 1


def test_ingest_is_idempotent():
    trace_id = str(uuid.uuid4())
    payload = _ingest_payload(trace_id)
    first = client.post("/api/traces/ingest", json=payload)
    second = client.post("/api/traces/ingest", json=payload)
    assert first.json()["status"] == "ingested"
    assert second.json()["status"] == "already_ingested"


def test_get_missing_trace_404():
    resp = client.get(f"/api/traces/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_list_traces_filters_by_status():
    resp = client.get("/api/traces", params={"status": "ok", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "total" in body
