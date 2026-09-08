import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";

export default function Datasets() {
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const activeDatasetId = selectedDatasetId ?? datasets.data?.[0]?.id ?? null;

  const versions = useQuery({
    queryKey: ["dataset-versions", activeDatasetId],
    queryFn: () => api.listDatasetVersions(activeDatasetId!),
    enabled: !!activeDatasetId,
  });
  const activeVersion = selectedVersion ?? versions.data?.[versions.data.length - 1]?.version ?? null;

  const items = useQuery({
    queryKey: ["dataset-items", activeDatasetId, activeVersion],
    queryFn: () => api.getDatasetVersionItems(activeDatasetId!, activeVersion!),
    enabled: !!activeDatasetId && !!activeVersion,
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Datasets</h1>
          <p>Golden Q&A sets used for evaluation and regression testing</p>
        </div>
      </div>

      {datasets.isLoading && <LoadingState />}
      {datasets.isError && <ErrorState error={datasets.error} />}
      {datasets.data && datasets.data.length === 0 && <EmptyState label="No datasets yet. Run scripts/seed_data.py to create one." />}

      {datasets.data && datasets.data.length > 0 && (
        <>
          <div className="filters-row">
            <select
              value={activeDatasetId ?? ""}
              onChange={(e) => {
                setSelectedDatasetId(Number(e.target.value));
                setSelectedVersion(null);
              }}
            >
              {datasets.data.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            {versions.data && (
              <select value={activeVersion ?? ""} onChange={(e) => setSelectedVersion(Number(e.target.value))}>
                {versions.data.map((v) => (
                  <option key={v.id} value={v.version}>
                    v{v.version} ({v.item_count} items)
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="card">
            <h2>Items</h2>
            {items.isLoading && <LoadingState />}
            {items.data && (
              <table>
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Expected answer</th>
                    <th>Expected doc(s)</th>
                  </tr>
                </thead>
                <tbody>
                  {items.data.map((item) => (
                    <tr key={item.id}>
                      <td>{item.question}</td>
                      <td className="text-muted">{item.expected_answer ?? "—"}</td>
                      <td className="mono">{item.expected_retrieval_doc_ids.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}
