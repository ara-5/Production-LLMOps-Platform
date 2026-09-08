// Validated dark-mode categorical palette (see dataviz skill — worst adjacent
// CVD ΔE 8.4, worst adjacent normal-vision ΔE 19.3, all >=3:1 on #1a1a19).
// Fixed order — assign by entity identity, never cycled/reassigned on filter.
export const SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];

export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
};

export const CHART_SURFACE = "#1a1a19";
export const GRIDLINE = "#2c2c2a";
export const AXIS = "#383835";
export const MUTED_INK = "#898781";
export const PRIMARY_INK = "#ffffff";

const MODEL_COLOR_ORDER: Record<string, string> = {
  "claude-opus-5": SERIES[0],
  "claude-sonnet-5": SERIES[1],
  "claude-haiku-4-5": SERIES[2],
};

export function colorForModel(modelId: string | null | undefined, fallbackIndex = 3): string {
  if (modelId && MODEL_COLOR_ORDER[modelId]) return MODEL_COLOR_ORDER[modelId];
  return SERIES[fallbackIndex % SERIES.length];
}

const METRIC_COLOR_ORDER: Record<string, string> = {
  hallucination: SERIES[0],
  faithfulness: SERIES[1],
  relevance: SERIES[2],
  precision_at_k: SERIES[3],
  recall_at_k: SERIES[4],
  mrr: SERIES[5],
  ndcg: SERIES[6],
};

export function colorForMetric(metric: string): string {
  return METRIC_COLOR_ORDER[metric] ?? SERIES[7];
}
