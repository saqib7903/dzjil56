export function StatGrid({ children }) {
  return <div className="stats">{children}</div>;
}

export function StatTile({ label, value, note, tone }) {
  return (
    <div className={`stat${tone ? ` stat--${tone}` : ''}`}>
      <p className="stat__label">{label}</p>
      <p className="stat__value">{value}</p>
      {note && <p className="stat__note">{note}</p>}
    </div>
  );
}
