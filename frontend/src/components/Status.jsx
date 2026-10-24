export function Loading({ label = 'Loading data…' }) {
  return (
    <div className="status" role="status">
      {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="status status--error" role="alert">
      <div>{error?.message || 'Something went wrong loading this view.'}</div>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
