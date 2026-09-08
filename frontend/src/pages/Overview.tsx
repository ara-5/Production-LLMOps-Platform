import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { CostTrendChart } from "../components/charts/CostTrendChart";
import { LatencyChart } from "../components/charts/LatencyChart";

function fmtUsd(n: number): string {
  return `$${n.toFixed(4)}`;
}

function fmtMs(n: number): string {
  return `${Math.round(n).toLocaleString()} ms`;
}

export default function Overview() {
  const overview = useQuery({ queryKey: ["metrics", "overview"], queryFn: () => api.overview() });
  const latency = useQuery({ queryKey: ["metrics", "latency-ts"], queryFn: () => api.latencyTimeseries("1 day") });
  const cost = useQuery({ queryKey: ["metrics", "cost-ts"], queryFn: () => api.costTimeseries("1 day") });
  const errors = useQuery({ queryKey: ["metrics", "errors"], queryFn: () => api.errors(8) });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Overview</h1>
          <p>Last 14 days across the Northwind Cloud support assistant</p>
        </div>
      </div>

      {overview.isLoading && <LoadingState />}
      {overview.isError && <ErrorState error={overview.error} />}
      {overview.data && (
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Requests</div>
            <div className="kpi-value">{overview.data.request_count.toLocaleString()}</div>
            <div className="kpi-sub">{overview.data.error_count} failed</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Error rate</div>
            <div className="kpi-value">{(overview.data.error_rate * 100).toFixed(2)}%</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg latency</div>
            <div className="kpi-value">{fmtMs(overview.data.avg_latency_ms)}</div>
            <div className="kpi-sub">p95 {fmtMs(overview.data.p95_latency_ms)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg TTFT</div>
            <div className="kpi-value">{fmtMs(overview.data.avg_ttft_ms)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Total cost</div>
            <div className="kpi-value">{fmtUsd(overview.data.total_cost_usd)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Tokens (in / out)</div>
            <div className="kpi-value" style={{ fontSize: 16 }}>
              {(overview.data.total_input_tokens / 1000).toFixed(0)}k / {(overview.data.total_output_tokens / 1000).toFixed(0)}k
            </div>
            <div className="kpi-sub">{(overview.data.total_cache_read_tokens / 1000).toFixed(0)}k cache read</div>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <h2>Latency</h2>
          {latency.isLoading && <LoadingState />}
          {latency.data && <LatencyChart data={latency.data} />}
        </div>
        <div className="card">
          <h2>Cost</h2>
          {cost.isLoading && <LoadingState />}
          {cost.data && <CostTrendChart data={cost.data} />}
        </div>
      </div>

      <div className="card">
        <h2>Recent failed requests</h2>
        {errors.isLoading && <LoadingState />}
        {errors.data && errors.data.length === 0 && <div className="empty-state">No errors in range. Nice.</div>}
        {errors.data && errors.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Trace</th>
                <th>Started</th>
                <th>Error type</th>
                <th>Model</th>
                <th>Retries</th>
              </tr>
            </thead>
            <tbody>
              {errors.data.map((e) => (
                <tr key={e.trace_id} className="clickable">
                  <td className="mono">
                    <Link to={`/traces/${e.trace_id}`}>{e.trace_id.slice(0, 8)}</Link>
                  </td>
                  <td>{new Date(e.started_at).toLocaleString()}</td>
                  <td>
                    <span className="badge badge-error">{e.error_type ?? "unknown"}</span>
                  </td>
                  <td>{e.model_id ?? "—"}</td>
                  <td>{e.retry_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
