export interface TraceListItem {
  trace_id: string;
  name: string;
  started_at: string;
  latency_ms: number | null;
  ttft_ms: number | null;
  status: string;
  error_type: string | null;
  model_id: string | null;
  prompt_version_id: number | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  is_synthetic: boolean;
  tags: Record<string, unknown>;
}

export interface SpanOut {
  id: number;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  span_kind: string;
  started_at: string;
  ended_at: string | null;
  latency_ms: number | null;
  status: string;
  status_message: string | null;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  cost_usd: number;
  attributes: Record<string, unknown>;
}

export interface EvalScoreOut {
  id: number;
  metric_name: string;
  score: number;
  passed: boolean | null;
  reasoning: string | null;
  judge_model: string | null;
  judge_trace_id: string | null;
  created_at: string;
}

export interface TraceDetail extends TraceListItem {
  ended_at: string | null;
  tokens_per_sec: number | null;
  retry_count: number;
  dataset_item_id: number | null;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  tags: Record<string, unknown>;
  attributes: Record<string, unknown>;
  spans: SpanOut[];
  eval_scores: EvalScoreOut[];
}

export interface TraceListResponse {
  items: TraceListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface OverviewMetrics {
  since: string;
  until: string;
  request_count: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  avg_ttft_ms: number;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_read_tokens: number;
}

export interface TimeseriesPoint {
  bucket: string;
  [key: string]: unknown;
}

export interface CostBreakdownRow {
  group_key: string | number | null;
  cost_usd: number;
  cache_read_tokens: number;
  input_tokens: number;
  request_count: number;
}

export interface ErrorRow {
  trace_id: string;
  name: string;
  started_at: string;
  error_type: string | null;
  model_id: string | null;
  retry_count: number;
}

export interface PromptOut {
  id: number;
  name: string;
  created_at: string;
}

export interface PromptVersionOut {
  id: number;
  prompt_id: number;
  version: number;
  template: string;
  variables: Record<string, unknown>;
  commit_message: string | null;
  created_by: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PromptWithVersions extends PromptOut {
  versions: PromptVersionOut[];
}

export interface PromptDiffOut {
  prompt_id: number;
  from_version: number;
  to_version: number;
  diff: string;
}

export interface DatasetOut {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface DatasetVersionOut {
  id: number;
  dataset_id: number;
  version: number;
  commit_message: string | null;
  created_at: string;
  item_count: number;
}

export interface DatasetWithVersions extends DatasetOut {
  versions: DatasetVersionOut[];
}

export interface DatasetItemOut {
  id: number;
  external_id: string | null;
  question: string;
  expected_answer: string | null;
  expected_retrieval_doc_ids: string[];
  relevance_grades: Record<string, number>;
  item_metadata: Record<string, unknown>;
}

export interface MetricSummary {
  metric_name: string;
  count: number;
  mean: number;
  p50: number;
  p95: number;
  pass_rate: number | null;
}

export interface EvalSummaryResponse {
  metrics: MetricSummary[];
}

export interface MetricComparison {
  metric_name: string;
  baseline: number;
  current: number;
  delta: number;
  threshold: number;
  passed: boolean;
}

export interface RegressionRunOut {
  id: number;
  name: string;
  dataset_version_id: number;
  prompt_version_id: number;
  model_id: string;
  baseline_run_id: number | null;
  is_baseline: boolean;
  status: string;
  summary: {
    item_count?: number;
    metrics?: Record<string, { count: number; mean: number; p50: number; p95: number }>;
    latency_ms?: { count: number; mean: number; p50: number; p95: number };
    cost_usd?: { count: number; mean: number; p50: number; p95: number };
    comparison?: { passed: boolean; comparisons: MetricComparison[] };
    note?: string;
  };
  started_at: string;
  ended_at: string | null;
}

export interface AnnotationOut {
  id: number;
  trace_id: string;
  annotator_email: string | null;
  label: string | null;
  score: number | null;
  comment: string | null;
  status: string;
  created_at: string;
}

export interface AskResponse {
  answer: string;
  sources: { doc_id: string; title: string; score: number }[];
  trace_id: string;
  latency_ms: number;
  cost_usd: number;
}
