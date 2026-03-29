export function StatusBadge({ tone = "neutral", children, pulse }) {
  return (
    <span className={`ch-status-badge ch-status-${tone}${pulse ? " ch-pulse" : ""}`}>
      {children}
    </span>
  );
}
