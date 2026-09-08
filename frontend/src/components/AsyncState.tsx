export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return <div className="empty-state">{label}</div>;
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return <div className="empty-state">Failed to load: {message}</div>;
}

export function EmptyState({ label = "Nothing here yet." }: { label?: string }) {
  return <div className="empty-state">{label}</div>;
}
