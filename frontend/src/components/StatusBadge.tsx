export function StatusBadge({ status }: { status: string }) {
  const cls = status === "ok" || status === "passed" ? "badge-ok" : status === "error" || status === "failed" ? "badge-error" : "badge-warn";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function BoolBadge({ value, trueLabel = "pass", falseLabel = "fail" }: { value: boolean | null; trueLabel?: string; falseLabel?: string }) {
  if (value === null) return <span className="badge badge-neutral">n/a</span>;
  return <span className={`badge ${value ? "badge-ok" : "badge-error"}`}>{value ? trueLabel : falseLabel}</span>;
}
