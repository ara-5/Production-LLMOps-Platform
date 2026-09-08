import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";
import { EvalMetricsChart } from "../components/charts/EvalMetricsChart";

const METRIC_LABELS: Record<string, string> = {
  hallucination: "Hallucination (groundedness)",
  faithfulness: "Faithfulness",
  relevance: "Relevance",
  precision_at_k: "Retrieval precision@k",
  recall_at_k: "Retrieval recall@k",
  mrr: "Retrieval MRR",
  ndcg: "Retrieval NDCG",
};

export default function Evaluations() {
  const { data, isLoading, isError, error } = useQuery({ queryKey: ["evals", "summary"], queryFn: () => api.evalSummary() });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Evaluations</h1>
          <p>LLM-as-judge quality scores and retrieval-quality metrics across all scored traces</p>
        </div>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState error={error} />}
      {data && data.metrics.length === 0 && <EmptyState label="No traces have been scored yet. Open a trace and click 'Run Eval'." />}

      {data && data.metrics.length > 0 && (
        <>
          <div className="card">
            <h2>Mean score by metric</h2>
            <EvalMetricsChart data={data.metrics} />
          </div>

          <div className="card">
            <h2>Metric detail</h2>
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Scored</th>
                  <th>Mean</th>
                  <th>p50</th>
                  <th>p95</th>
                  <th>Pass rate</th>
                </tr>
              </thead>
              <tbody>
                {data.metrics.map((m) => (
                  <tr key={m.metric_name}>
                    <td>{METRIC_LABELS[m.metric_name] ?? m.metric_name}</td>
                    <td>{m.count.toLocaleString()}</td>
                    <td className="mono">{m.mean.toFixed(3)}</td>
                    <td className="mono">{m.p50.toFixed(3)}</td>
                    <td className="mono">{m.p95.toFixed(3)}</td>
                    <td>{m.pass_rate !== null ? `${(m.pass_rate * 100).toFixed(1)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
