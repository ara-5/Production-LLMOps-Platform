import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { CostBreakdownChart } from "../components/charts/CostBreakdownChart";

// Rough cache-savings estimate: cache reads are billed far below full input
// price (see sdk/llmops_sdk/pricing.py). We use the sonnet-5 ratio (0.20 vs
// 2.00 per 1M) as a representative full-input equivalent for the callout.
const CACHE_DISCOUNT_ESTIMATE = 0.9;

export default function Costs() {
  const [groupBy, setGroupBy] = useState<"model_id" | "prompt_version_id">("model_id");
  const breakdown = useQuery({ queryKey: ["cost-breakdown", groupBy], queryFn: () => api.costBreakdown(groupBy) });
  const overview = useQuery({ queryKey: ["metrics", "overview"], queryFn: () => api.overview() });

  const totalCacheRead = breakdown.data?.reduce((sum, r) => sum + r.cache_read_tokens, 0) ?? 0;
  const estimatedSavings = (totalCacheRead / 1_000_000) * 2.0 * CACHE_DISCOUNT_ESTIMATE;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Costs</h1>
          <p>Spend broken down by model and prompt version, with prompt-cache savings</p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Total spend (14d)</div>
          <div className="kpi-value">${overview.data ? overview.data.total_cost_usd.toFixed(4) : "—"}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Cache read tokens</div>
          <div className="kpi-value">{(totalCacheRead / 1000).toFixed(0)}k</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Estimated cache savings</div>
          <div className="kpi-value">${estimatedSavings.toFixed(4)}</div>
          <div className="kpi-sub">vs. paying full input price for those tokens</div>
        </div>
      </div>

      <div className="card">
        <div className="filters-row" style={{ marginBottom: 4 }}>
          <h2 style={{ margin: 0 }}>Spend by</h2>
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as "model_id" | "prompt_version_id")}>
            <option value="model_id">Model</option>
            <option value="prompt_version_id">Prompt version</option>
          </select>
        </div>
        {breakdown.isLoading && <LoadingState />}
        {breakdown.isError && <ErrorState error={breakdown.error} />}
        {breakdown.data && <CostBreakdownChart data={breakdown.data} />}
      </div>

      <div className="card">
        <h2>Detail</h2>
        {breakdown.data && (
          <table>
            <thead>
              <tr>
                <th>{groupBy === "model_id" ? "Model" : "Prompt version"}</th>
                <th>Requests</th>
                <th>Input tokens</th>
                <th>Cache read tokens</th>
                <th>Cost</th>
                <th>Avg cost / request</th>
              </tr>
            </thead>
            <tbody>
              {breakdown.data.map((row) => (
                <tr key={String(row.group_key)}>
                  <td>{groupBy === "prompt_version_id" ? `v${row.group_key}` : row.group_key ?? "unknown"}</td>
                  <td>{row.request_count.toLocaleString()}</td>
                  <td>{row.input_tokens.toLocaleString()}</td>
                  <td>{row.cache_read_tokens.toLocaleString()}</td>
                  <td>${row.cost_usd.toFixed(4)}</td>
                  <td>${(row.cost_usd / Math.max(row.request_count, 1)).toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
