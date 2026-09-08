import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";

const LABELS = ["good", "needs_review", "bad"];

function AnnotateForm({ traceId, onDone }: { traceId: string; onDone: () => void }) {
  const [label, setLabel] = useState(LABELS[0]);
  const [comment, setComment] = useState("");
  const create = useMutation({
    mutationFn: () => api.createAnnotation({ trace_id: traceId, label, comment: comment || undefined, status: "completed" }),
    onSuccess: onDone,
  });

  return (
    <div className="filters-row" style={{ marginTop: 6 }}>
      <select value={label} onChange={(e) => setLabel(e.target.value)}>
        {LABELS.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </select>
      <input placeholder="comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
      <button className="btn" disabled={create.isPending} onClick={() => create.mutate()}>
        {create.isPending ? "Saving..." : "Submit"}
      </button>
    </div>
  );
}

export default function Annotations() {
  const queryClient = useQueryClient();
  const [openTraceId, setOpenTraceId] = useState<string | null>(null);

  const recentTraces = useQuery({ queryKey: ["traces", "recent-for-annotation"], queryFn: () => api.listTraces({ status: "ok", limit: 20 }) });
  const completed = useQuery({ queryKey: ["annotations", "completed"], queryFn: () => api.annotationQueue("completed") });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Annotations</h1>
          <p>Human review queue — label recent traces to build ground truth for future eval datasets</p>
        </div>
      </div>

      <div className="card">
        <h2>Recent traces</h2>
        {recentTraces.isLoading && <LoadingState />}
        {recentTraces.isError && <ErrorState error={recentTraces.error} />}
        {recentTraces.data && recentTraces.data.items.length === 0 && <EmptyState />}
        {recentTraces.data && (
          <table>
            <thead>
              <tr>
                <th>Trace</th>
                <th>Started</th>
                <th>Model</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {recentTraces.data.items.map((t) => (
                <tr key={t.trace_id}>
                  <td className="mono">
                    <Link to={`/traces/${t.trace_id}`}>{t.trace_id.slice(0, 8)}</Link>
                  </td>
                  <td>{new Date(t.started_at).toLocaleString()}</td>
                  <td>{t.model_id ?? "—"}</td>
                  <td>
                    <button className="btn btn-secondary" onClick={() => setOpenTraceId(openTraceId === t.trace_id ? null : t.trace_id)}>
                      {openTraceId === t.trace_id ? "Cancel" : "Annotate"}
                    </button>
                    {openTraceId === t.trace_id && (
                      <AnnotateForm
                        traceId={t.trace_id}
                        onDone={() => {
                          setOpenTraceId(null);
                          queryClient.invalidateQueries({ queryKey: ["annotations", "completed"] });
                        }}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Submitted annotations</h2>
        {completed.data && completed.data.length === 0 && <EmptyState label="No annotations submitted yet." />}
        {completed.data && completed.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Trace</th>
                <th>Label</th>
                <th>Comment</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {completed.data.map((a) => (
                <tr key={a.id}>
                  <td className="mono">
                    <Link to={`/traces/${a.trace_id}`}>{a.trace_id.slice(0, 8)}</Link>
                  </td>
                  <td>
                    <span className={`badge ${a.label === "bad" ? "badge-error" : a.label === "needs_review" ? "badge-warn" : "badge-ok"}`}>{a.label}</span>
                  </td>
                  <td className="text-muted">{a.comment ?? "—"}</td>
                  <td>{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
