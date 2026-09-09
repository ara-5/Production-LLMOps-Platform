import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";
import { StatusBadge } from "../components/StatusBadge";

const PAGE_SIZE = 25;

export default function Traces() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<string>("");
  const [modelId, setModelId] = useState<string>("");
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["traces", status, modelId, page],
    queryFn: () =>
      api.listTraces({
        status: status || undefined,
        model_id: modelId || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Traces</h1>
          <p>Every request through the Northwind Cloud support assistant</p>
        </div>
      </div>

      <div className="filters-row">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All statuses</option>
          <option value="ok">ok</option>
          <option value="error">error</option>
        </select>
        <select
          value={modelId}
          onChange={(e) => {
            setModelId(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All models</option>
          <option value="claude-opus-5">claude-opus-5</option>
          <option value="claude-sonnet-5">claude-sonnet-5</option>
          <option value="claude-haiku-4-5">claude-haiku-4-5</option>
        </select>
      </div>

      <div className="card">
        {isLoading && <LoadingState />}
        {isError && <ErrorState error={error} />}
        {data && data.items.length === 0 && <EmptyState label="No traces match these filters." />}
        {data && data.items.length > 0 && (
          <>
            <table>
              <thead>
                <tr>
                  <th>Trace</th>
                  <th>Started</th>
                  <th>Status</th>
                  <th>Model</th>
                  <th>Latency</th>
                  <th>TTFT</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((t) => (
                  <tr key={t.trace_id} className="clickable" onClick={() => navigate(`/traces/${t.trace_id}`)}>
                    <td className="mono">{t.trace_id.slice(0, 8)}</td>
                    <td>{new Date(t.started_at).toLocaleString()}</td>
                    <td>
                      <StatusBadge status={t.status} />
                    </td>
                    <td>{t.model_id ?? "—"}</td>
                    <td>{t.latency_ms ?? "—"} ms</td>
                    <td>{t.ttft_ms ?? "—"} ms</td>
                    <td>
                      {t.input_tokens} / {t.output_tokens}
                    </td>
                    <td>${t.cost_usd.toFixed(5)}</td>
                    <td>
                      <span className="badge badge-neutral">{t.is_synthetic ? "synthetic" : "live"}</span>
                      {t.tags?.fallback_used === true && (
                        <span className="badge badge-warn" style={{ marginLeft: 6 }} title="Primary provider failed; recovered via local Ollama fallback">
                          fallback
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="filters-row" style={{ marginTop: 14, marginBottom: 0, justifyContent: "space-between" }}>
              <span className="text-muted">
                {data.total.toLocaleString()} traces — page {page + 1} of {totalPages}
              </span>
              <div className="pill-row">
                <button className="btn btn-secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </button>
                <button className="btn btn-secondary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
