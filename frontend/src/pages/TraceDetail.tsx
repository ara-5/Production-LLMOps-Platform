import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { BoolBadge, StatusBadge } from "../components/StatusBadge";
import type { SpanOut } from "../types/api";

function SpanWaterfall({ spans, traceLatency }: { spans: SpanOut[]; traceLatency: number }) {
  if (spans.length === 0) return <div className="empty-state">No spans recorded.</div>;
  const t0 = new Date(spans[0].started_at).getTime();
  const total = Math.max(traceLatency, 1);

  return (
    <div>
      <div className="legend-row">
        <span>
          <span className="legend-dot" style={{ background: "var(--accent)" }} /> llm
        </span>
        <span>
          <span className="legend-dot" style={{ background: "var(--series-3)" }} /> retrieval
        </span>
        <span>
          <span className="legend-dot" style={{ background: "var(--series-4)" }} /> judge
        </span>
        <span>
          <span className="legend-dot" style={{ background: "var(--series-7)" }} /> tool
        </span>
      </div>
      {spans.map((s) => {
        const offset = (new Date(s.started_at).getTime() - t0) / total;
        const width = Math.max((s.latency_ms ?? 0) / total, 0.01);
        return (
          <div className="span-row" key={s.id}>
            <div style={{ width: 150, flexShrink: 0, fontSize: 12 }}>{s.name}</div>
            <div className="span-bar-track">
              <div
                className={`span-bar-fill ${s.span_kind}`}
                style={{ left: `${offset * 100}%`, width: `${Math.min(width, 1 - offset) * 100}%` }}
              />
            </div>
            <div style={{ width: 70, textAlign: "right", fontSize: 12 }} className="mono">
              {s.latency_ms ?? "—"} ms
            </div>
            <div style={{ width: 90, textAlign: "right", fontSize: 12 }} className="mono">
              ${s.cost_usd.toFixed(5)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function TraceDetail() {
  const { traceId } = useParams<{ traceId: string }>();
  const queryClient = useQueryClient();
  const [selectedSpanId, setSelectedSpanId] = useState<number | null>(null);

  const { data: trace, isLoading, isError, error } = useQuery({
    queryKey: ["trace", traceId],
    queryFn: () => api.getTrace(traceId!),
    enabled: !!traceId,
  });

  const runEval = useMutation({
    mutationFn: () => api.scoreTrace(traceId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trace", traceId] }),
  });

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState error={error} />;
  if (!trace) return null;

  const selectedSpan = trace.spans.find((s) => s.id === selectedSpanId) ?? null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>
            Trace <span className="mono">{trace.trace_id}</span>
          </h1>
          <p>
            <Link to="/traces">← Back to traces</Link>
          </p>
        </div>
        <button className="btn" onClick={() => runEval.mutate()} disabled={runEval.isPending}>
          {runEval.isPending ? "Scoring..." : "Run Eval"}
        </button>
      </div>

      {runEval.isError && <div className="empty-state">Eval failed: {(runEval.error as Error).message}</div>}

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Status</div>
          <div className="kpi-value">
            <StatusBadge status={trace.status} />
          </div>
          {trace.error_type && <div className="kpi-sub">{trace.error_type}</div>}
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Latency / TTFT</div>
          <div className="kpi-value" style={{ fontSize: 17 }}>
            {trace.latency_ms} ms / {trace.ttft_ms ?? "—"} ms
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Model</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>
            {trace.model_id ?? "—"}
          </div>
          {trace.prompt_version_id && <div className="kpi-sub">prompt v{trace.prompt_version_id}</div>}
          {trace.tags?.fallback_used === true && (
            <div className="kpi-sub">
              <span className="badge badge-warn">fallback</span> from {String(trace.tags.fallback_from_model ?? "primary provider")}
            </div>
          )}
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Tokens</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>
            {trace.input_tokens} in / {trace.output_tokens} out
          </div>
          <div className="kpi-sub">{trace.cache_read_tokens} cache read</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Cost</div>
          <div className="kpi-value">${trace.cost_usd.toFixed(5)}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Span waterfall</h2>
          <SpanWaterfall spans={trace.spans} traceLatency={trace.latency_ms ?? 1} />
        </div>
        <div className="card">
          <h2>Evaluation scores</h2>
          {trace.eval_scores.length === 0 && <div className="empty-state">Not scored yet. Click "Run Eval".</div>}
          {trace.eval_scores.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Score</th>
                  <th>Passed</th>
                  <th>Judge</th>
                </tr>
              </thead>
              <tbody>
                {trace.eval_scores.map((s) => (
                  <tr key={s.id}>
                    <td>{s.metric_name}</td>
                    <td className="mono">{Number(s.score).toFixed(3)}</td>
                    <td>
                      <BoolBadge value={s.passed} />
                    </td>
                    <td className="text-muted">{s.judge_model ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card">
        <h2>Spans (click for detail)</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Kind</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Tokens</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {trace.spans.map((s) => (
              <tr key={s.id} className="clickable" onClick={() => setSelectedSpanId(s.id === selectedSpanId ? null : s.id)}>
                <td>{s.name}</td>
                <td>
                  <span className="badge badge-neutral">{s.span_kind}</span>
                </td>
                <td>
                  <StatusBadge status={s.status} />
                </td>
                <td>{s.latency_ms ?? "—"} ms</td>
                <td>
                  {s.input_tokens} / {s.output_tokens}
                </td>
                <td>${s.cost_usd.toFixed(5)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {selectedSpan && (
          <div className="diff-view" style={{ marginTop: 14 }}>
            {JSON.stringify(selectedSpan.attributes, null, 2)}
          </div>
        )}
      </div>
    </>
  );
}
