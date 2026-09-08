import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";
import { StatusBadge } from "../components/StatusBadge";

const MODELS = ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5"];

export default function Regression() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState<number | "">("");
  const [promptVersionId, setPromptVersionId] = useState<number | "">("");
  const [modelId, setModelId] = useState(MODELS[0]);
  const [baselineRunId, setBaselineRunId] = useState<number | "">("");
  const [limit, setLimit] = useState<number | "">(5);

  const runs = useQuery({
    queryKey: ["regression-runs"],
    queryFn: () => api.listRegressionRuns(),
    refetchInterval: (query) => (query.state.data?.some((r) => r.status === "running") ? 3000 : false),
  });
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const dataset0 = datasets.data?.[0];
  const datasetVersions = useQuery({
    queryKey: ["dataset-versions", dataset0?.id],
    queryFn: () => api.listDatasetVersions(dataset0!.id),
    enabled: !!dataset0,
  });
  const prompts = useQuery({ queryKey: ["prompts"], queryFn: () => api.listPrompts() });
  const prompt0 = prompts.data?.[0];
  const promptDetail = useQuery({
    queryKey: ["prompt", prompt0?.id],
    queryFn: () => api.getPrompt(prompt0!.id),
    enabled: !!prompt0,
  });

  const createRun = useMutation({
    mutationFn: () =>
      api.createRegressionRun({
        name: name || `regression run ${new Date().toLocaleString()}`,
        dataset_version_id: Number(datasetVersionId),
        prompt_version_id: Number(promptVersionId),
        model_id: modelId,
        baseline_run_id: baselineRunId === "" ? undefined : Number(baselineRunId),
        limit: limit === "" ? undefined : Number(limit),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regression-runs"] }),
  });

  const setBaseline = useMutation({
    mutationFn: (id: number) => api.setBaseline(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["regression-runs"] }),
  });

  const canSubmit = datasetVersionId !== "" && promptVersionId !== "";

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Regression Tests</h1>
          <p>Run a golden dataset against a prompt/model version and compare against a stored baseline</p>
        </div>
      </div>

      <div className="card">
        <h2>Run a new regression test</h2>
        <p className="text-muted" style={{ marginTop: -6, marginBottom: 14 }}>
          Makes real Claude API calls (one answer + up to 3 judge calls per item). Use a small limit for a cheap smoke test first.
        </p>
        <div className="grid-2">
          <div>
            <div className="form-row">
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. v2 prompt vs baseline" />
            </div>
            <div className="form-row">
              <label>Dataset version</label>
              <select value={datasetVersionId} onChange={(e) => setDatasetVersionId(Number(e.target.value))}>
                <option value="">select...</option>
                {datasetVersions.data?.map((v) => (
                  <option key={v.id} value={v.id}>
                    {dataset0?.name} v{v.version} ({v.item_count} items)
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Prompt version</label>
              <select value={promptVersionId} onChange={(e) => setPromptVersionId(Number(e.target.value))}>
                <option value="">select...</option>
                {promptDetail.data?.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {promptDetail.data?.name} v{v.version}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <div className="form-row">
              <label>Model</label>
              <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
                {MODELS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Baseline run (optional)</label>
              <select value={baselineRunId} onChange={(e) => setBaselineRunId(e.target.value === "" ? "" : Number(e.target.value))}>
                <option value="">none</option>
                {runs.data
                  ?.filter((r) => r.status === "passed" || r.is_baseline)
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      #{r.id} {r.name} {r.is_baseline ? "(baseline)" : ""}
                    </option>
                  ))}
              </select>
            </div>
            <div className="form-row">
              <label>Item limit (cost control)</label>
              <input type="number" min={1} value={limit} onChange={(e) => setLimit(e.target.value === "" ? "" : Number(e.target.value))} />
            </div>
          </div>
        </div>
        <button className="btn" disabled={!canSubmit || createRun.isPending} onClick={() => createRun.mutate()}>
          {createRun.isPending ? "Starting..." : "Run regression test"}
        </button>
        {createRun.isError && <div className="empty-state">{(createRun.error as Error).message}</div>}
      </div>

      <div className="card">
        <h2>Run history</h2>
        {runs.isLoading && <LoadingState />}
        {runs.isError && <ErrorState error={runs.error} />}
        {runs.data && runs.data.length === 0 && <EmptyState label="No regression runs yet." />}
        {runs.data && runs.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Model</th>
                <th>Items</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.data.map((r) => (
                <tr key={r.id}>
                  <td>
                    #{r.id} {r.name} {r.is_baseline && <span className="badge badge-neutral">baseline</span>}
                  </td>
                  <td>
                    <StatusBadge status={r.status} />
                  </td>
                  <td>{r.model_id}</td>
                  <td>{r.summary.item_count ?? "—"}</td>
                  <td>{new Date(r.started_at).toLocaleString()}</td>
                  <td>
                    {!r.is_baseline && r.status === "passed" && (
                      <button className="btn btn-secondary" onClick={() => setBaseline.mutate(r.id)}>
                        Set as baseline
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {runs.data
        ?.filter((r) => r.summary.comparison)
        .slice(0, 1)
        .map((r) => (
          <div className="card" key={r.id}>
            <h2>
              Latest comparison — run #{r.id} vs baseline #{r.baseline_run_id}
            </h2>
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Baseline</th>
                  <th>Current</th>
                  <th>Delta</th>
                  <th>Threshold</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {r.summary.comparison!.comparisons.map((c) => (
                  <tr key={c.metric_name}>
                    <td>{c.metric_name}</td>
                    <td className="mono">{c.baseline.toFixed(4)}</td>
                    <td className="mono">{c.current.toFixed(4)}</td>
                    <td className="mono">{c.delta >= 0 ? "+" : ""}{c.delta.toFixed(4)}</td>
                    <td className="mono">{c.threshold}</td>
                    <td>
                      <StatusBadge status={c.passed ? "ok" : "error"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </>
  );
}
