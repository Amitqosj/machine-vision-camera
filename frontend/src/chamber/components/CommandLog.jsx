export function CommandLog({ lines, title = "Command log" }) {
  return (
    <div className="ch-command-log">
      <div className="ch-command-log-header">{title}</div>
      <pre className="ch-command-log-body">
        {lines.length === 0 ? (
          <span className="ch-muted">No serial commands yet (mock).</span>
        ) : (
          lines
            .slice()
            .reverse()
            .map((line, i) => (
              <div key={`${line}-${i}`} className="ch-command-line">
                {line}
              </div>
            ))
        )}
      </pre>
    </div>
  );
}
