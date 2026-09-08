import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";

function DiffLine({ line }: { line: string }) {
  if (line.startsWith("+") && !line.startsWith("+++")) return <div className="diff-add">{line}</div>;
  if (line.startsWith("-") && !line.startsWith("---")) return <div className="diff-remove">{line}</div>;
  return <div>{line}</div>;
}

export default function Prompts() {
  const queryClient = useQueryClient();
  const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
  const [diffFrom, setDiffFrom] = useState<number | null>(null);
  const [diffTo, setDiffTo] = useState<number | null>(null);
  const [newTemplate, setNewTemplate] = useState("");
  const [commitMessage, setCommitMessage] = useState("");

  const prompts = useQuery({ queryKey: ["prompts"], queryFn: () => api.listPrompts() });
  const activePromptId = selectedPromptId ?? prompts.data?.[0]?.id ?? null;

  const promptDetail = useQuery({
    queryKey: ["prompt", activePromptId],
    queryFn: () => api.getPrompt(activePromptId!),
    enabled: !!activePromptId,
  });

  const diff = useQuery({
    queryKey: ["prompt-diff", activePromptId, diffFrom, diffTo],
    queryFn: () => api.diffPromptVersions(activePromptId!, diffFrom!, diffTo!),
    enabled: !!activePromptId && diffFrom !== null && diffTo !== null,
  });

  const createVersion = useMutation({
    mutationFn: () => api.createPromptVersion(activePromptId!, { template: newTemplate, commit_message: commitMessage || undefined }),
    onSuccess: () => {
      setNewTemplate("");
      setCommitMessage("");
      queryClient.invalidateQueries({ queryKey: ["prompt", activePromptId] });
    },
  });

  const rollback = useMutation({
    mutationFn: (toVersion: number) => api.rollbackPrompt(activePromptId!, toVersion),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prompt", activePromptId] }),
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Prompt Registry</h1>
          <p>Version history, diffing, and rollback for every prompt template</p>
        </div>
      </div>

      {prompts.isLoading && <LoadingState />}
      {prompts.isError && <ErrorState error={prompts.error} />}
      {prompts.data && prompts.data.length === 0 && <EmptyState label="No prompts yet. Run scripts/seed_data.py to create one." />}

      {prompts.data && prompts.data.length > 0 && (
        <>
          <div className="filters-row">
            <select value={activePromptId ?? ""} onChange={(e) => setSelectedPromptId(Number(e.target.value))}>
              {prompts.data.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {promptDetail.data && (
            <div className="grid-2">
              <div className="card">
                <h2>Versions</h2>
                <table>
                  <thead>
                    <tr>
                      <th>Version</th>
                      <th>Commit message</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {promptDetail.data.versions.map((v) => (
                      <tr key={v.id}>
                        <td>v{v.version}</td>
                        <td>{v.commit_message ?? "—"}</td>
                        <td>{new Date(v.created_at).toLocaleString()}</td>
                        <td>
                          <button className="btn btn-secondary" onClick={() => rollback.mutate(v.version)} disabled={rollback.isPending}>
                            Rollback to this
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <h3 style={{ marginTop: 18 }}>Diff two versions</h3>
                <div className="filters-row">
                  <select value={diffFrom ?? ""} onChange={(e) => setDiffFrom(Number(e.target.value))}>
                    <option value="">from...</option>
                    {promptDetail.data.versions.map((v) => (
                      <option key={v.id} value={v.version}>
                        v{v.version}
                      </option>
                    ))}
                  </select>
                  <select value={diffTo ?? ""} onChange={(e) => setDiffTo(Number(e.target.value))}>
                    <option value="">to...</option>
                    {promptDetail.data.versions.map((v) => (
                      <option key={v.id} value={v.version}>
                        v{v.version}
                      </option>
                    ))}
                  </select>
                </div>
                {diff.data && (
                  <div className="diff-view">
                    {diff.data.diff.split("\n").map((line, i) => (
                      <DiffLine line={line} key={i} />
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h2>New version</h2>
                <div className="form-row">
                  <label>Template</label>
                  <textarea rows={10} value={newTemplate} onChange={(e) => setNewTemplate(e.target.value)} placeholder="Use {question} and {context} placeholders" />
                </div>
                <div className="form-row">
                  <label>Commit message</label>
                  <input value={commitMessage} onChange={(e) => setCommitMessage(e.target.value)} />
                </div>
                <button className="btn" disabled={!newTemplate || createVersion.isPending} onClick={() => createVersion.mutate()}>
                  {createVersion.isPending ? "Saving..." : "Save new version"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
