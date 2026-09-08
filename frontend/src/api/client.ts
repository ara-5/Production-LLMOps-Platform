import type {
  AnnotationOut,
  AskResponse,
  CostBreakdownRow,
  DatasetItemOut,
  DatasetOut,
  DatasetVersionOut,
  DatasetWithVersions,
  ErrorRow,
  EvalSummaryResponse,
  OverviewMetrics,
  PromptDiffOut,
  PromptOut,
  PromptVersionOut,
  PromptWithVersions,
  RegressionRunOut,
  TimeseriesPoint,
  TraceDetail,
  TraceListResponse,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const usable = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (usable.length === 0) return "";
  return "?" + new URLSearchParams(usable.map(([k, v]) => [k, String(v)])).toString();
}

export const api = {
  // Traces
  listTraces: (params: { status?: string; model_id?: string; is_synthetic?: boolean; limit?: number; offset?: number } = {}) =>
    request<TraceListResponse>(`/api/traces${qs(params)}`),
  getTrace: (traceId: string) => request<TraceDetail>(`/api/traces/${traceId}`),

  // Metrics
  overview: (since?: string) => request<OverviewMetrics>(`/api/metrics/overview${qs({ since })}`),
  latencyTimeseries: (bucket = "1 hour") => request<TimeseriesPoint[]>(`/api/metrics/latency-timeseries${qs({ bucket })}`),
  costTimeseries: (bucket = "1 day") => request<TimeseriesPoint[]>(`/api/metrics/cost-timeseries${qs({ bucket })}`),
  costBreakdown: (group_by: "model_id" | "prompt_version_id" = "model_id") =>
    request<CostBreakdownRow[]>(`/api/metrics/cost-breakdown${qs({ group_by })}`),
  errors: (limit = 50) => request<ErrorRow[]>(`/api/metrics/errors${qs({ limit })}`),

  // Prompts
  listPrompts: () => request<PromptOut[]>("/api/prompts"),
  getPrompt: (id: number) => request<PromptWithVersions>(`/api/prompts/${id}`),
  createPrompt: (name: string) => request<PromptOut>("/api/prompts", { method: "POST", body: JSON.stringify({ name }) }),
  createPromptVersion: (promptId: number, body: { template: string; commit_message?: string }) =>
    request<PromptVersionOut>(`/api/prompts/${promptId}/versions`, { method: "POST", body: JSON.stringify(body) }),
  diffPromptVersions: (promptId: number, fromVersion: number, toVersion: number) =>
    request<PromptDiffOut>(`/api/prompts/${promptId}/diff${qs({ from_version: fromVersion, to_version: toVersion })}`),
  rollbackPrompt: (promptId: number, toVersion: number) =>
    request<PromptVersionOut>(`/api/prompts/${promptId}/rollback`, { method: "POST", body: JSON.stringify({ to_version: toVersion }) }),

  // Datasets
  listDatasets: () => request<DatasetOut[]>("/api/datasets"),
  getDataset: (id: number) => request<DatasetWithVersions>(`/api/datasets/${id}`),
  listDatasetVersions: (id: number) => request<DatasetVersionOut[]>(`/api/datasets/${id}/versions`),
  getDatasetVersionItems: (id: number, version: number) => request<DatasetItemOut[]>(`/api/datasets/${id}/versions/${version}/items`),

  // Evals
  evalSummary: () => request<EvalSummaryResponse>("/api/evals/summary"),
  scoreTrace: (traceId: string, metrics?: string[]) =>
    request(`/api/evals/score-trace/${traceId}`, { method: "POST", body: JSON.stringify({ metrics: metrics ?? ["hallucination", "faithfulness", "relevance"] }) }),

  // Regression
  listRegressionRuns: () => request<RegressionRunOut[]>("/api/regression/runs"),
  getRegressionRun: (id: number) => request<RegressionRunOut>(`/api/regression/runs/${id}`),
  createRegressionRun: (body: {
    name: string;
    dataset_version_id: number;
    prompt_version_id: number;
    model_id: string;
    baseline_run_id?: number;
    limit?: number;
  }) => request<RegressionRunOut>("/api/regression/runs", { method: "POST", body: JSON.stringify(body) }),
  setBaseline: (id: number) => request<RegressionRunOut>(`/api/regression/runs/${id}/set-baseline`, { method: "POST" }),

  // Annotations
  annotationQueue: (status = "pending") => request<AnnotationOut[]>(`/api/annotations/queue${qs({ status })}`),
  createAnnotation: (body: { trace_id: string; label?: string; score?: number; comment?: string; status?: string }) =>
    request<AnnotationOut>("/api/annotations", { method: "POST", body: JSON.stringify(body) }),

  // Demo app
  ask: (question: string, prompt_version_id?: number, model_id?: string) =>
    request<AskResponse>("/demo/ask", { method: "POST", body: JSON.stringify({ question, prompt_version_id, model_id }) }),
};
