import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || payload.message || detail;
    } catch {
      // Keep default detail when response body is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function boolText(value) {
  return value ? "YES" : "NO";
}

export default function App() {
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [recentFailures, setRecentFailures] = useState([]);
  const [recentResults, setRecentResults] = useState([]);
  const [roiDraft, setRoiDraft] = useState({
    enabled: true,
    x: 100,
    y: 100,
    width: 400,
    height: 300,
  });
  const [streamSeed, setStreamSeed] = useState(Date.now());
  const [message, setMessage] = useState("Backend connected. Ready.");
  const [busyAction, setBusyAction] = useState("");

  const fetchStatus = useCallback(async () => {
    const payload = await requestJson("/api/status");
    setStatus(payload);
  }, []);

  const fetchConfig = useCallback(async () => {
    const payload = await requestJson("/api/config");
    setConfig(payload);
    if (payload?.inspection?.roi) {
      setRoiDraft(payload.inspection.roi);
    }
  }, []);

  const fetchRecentFailures = useCallback(async () => {
    const payload = await requestJson("/api/failures/recent?limit=8");
    setRecentFailures(payload);
  }, []);

  const fetchRecentResults = useCallback(async () => {
    const payload = await requestJson("/api/results/recent?limit=12");
    setRecentResults(payload);
  }, []);

  const refreshAll = useCallback(async () => {
    try {
      await Promise.all([
        fetchStatus(),
        fetchRecentFailures(),
        fetchRecentResults(),
      ]);
    } catch (error) {
      setMessage(`Refresh failed: ${error.message}`);
    }
  }, [fetchRecentFailures, fetchRecentResults, fetchStatus]);

  useEffect(() => {
    fetchConfig()
      .then(() => refreshAll())
      .catch((error) => setMessage(`Initialization failed: ${error.message}`));

    const interval = setInterval(() => {
      refreshAll();
    }, 1500);
    return () => clearInterval(interval);
  }, [fetchConfig, refreshAll]);

  const runControlAction = useCallback(
    async (actionPath, successFallback, options = {}) => {
      try {
        setBusyAction(actionPath);
        const payload = await requestJson(actionPath, {
          method: "POST",
          body: options.body ? JSON.stringify(options.body) : undefined,
        });
        setMessage(payload.message || successFallback);
        if (actionPath === "/api/control/start") {
          setStreamSeed(Date.now());
        }
        await refreshAll();
      } catch (error) {
        setMessage(`Action failed: ${error.message}`);
      } finally {
        setBusyAction("");
      }
    },
    [refreshAll]
  );

  const applyRoi = async (event) => {
    event.preventDefault();
    await runControlAction("/api/roi", "ROI updated.", {
      body: {
        enabled: roiDraft.enabled,
        x: Number(roiDraft.x),
        y: Number(roiDraft.y),
        width: Number(roiDraft.width),
        height: Number(roiDraft.height),
      },
    });
  };

  const runtime = status?.runtime || {};
  const dbCounters = status?.database || {};
  const lastResult = status?.latest_result || runtime?.last_result || {};
  const streamUrl = useMemo(
    () => `${API_BASE}/api/stream.mjpg?seed=${streamSeed}`,
    [streamSeed]
  );

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div>
          <h1>Machine Vision Inspection Dashboard</h1>
          <p className="subtle">
            Backend status:{" "}
            <span className={runtime.running ? "ok" : "bad"}>
              {runtime.running ? "RUNNING" : "STOPPED"}
            </span>{" "}
            | Camera connected:{" "}
            <span className={runtime.camera_connected ? "ok" : "bad"}>
              {boolText(runtime.camera_connected)}
            </span>
          </p>
        </div>
        <div className="status-message">{message}</div>
      </header>

      <main className="layout">
        <section className="panel stream-panel">
          <h2>Live Stream</h2>
          <div className="stream-wrap">
            <img className="stream-view" src={streamUrl} alt="Inspection stream" />
            {!runtime.running && (
              <div className="stream-overlay">Start inspection to view stream</div>
            )}
          </div>
          <div className="button-row">
            <button
              onClick={() => runControlAction("/api/control/start", "Inspection started.")}
              disabled={busyAction.length > 0}
            >
              Start
            </button>
            <button
              onClick={() => runControlAction("/api/control/stop", "Inspection stopped.")}
              disabled={busyAction.length > 0}
            >
              Stop
            </button>
            <button
              onClick={() =>
                runControlAction("/api/control/reset-counters", "Runtime counters reset.")
              }
              disabled={busyAction.length > 0}
            >
              Reset Counters
            </button>
            <button
              onClick={() =>
                runControlAction("/api/control/capture-snapshot", "Snapshot captured.")
              }
              disabled={busyAction.length > 0}
            >
              Capture Snapshot
            </button>
            <button
              onClick={() => runControlAction("/api/control/export-csv", "CSV exported.")}
              disabled={busyAction.length > 0}
            >
              Export CSV
            </button>
            <button
              onClick={() => runControlAction("/api/control/save-config", "Config saved.")}
              disabled={busyAction.length > 0}
            >
              Save Config
            </button>
          </div>
        </section>

        <section className="panel info-panel">
          <h2>Runtime Overview</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">Total (runtime)</div>
              <div className="value">{runtime.total_count ?? 0}</div>
            </div>
            <div className="stat-card ok">
              <div className="label">Pass (runtime)</div>
              <div className="value">{runtime.pass_count ?? 0}</div>
            </div>
            <div className="stat-card bad">
              <div className="label">Fail (runtime)</div>
              <div className="value">{runtime.fail_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="label">Total (database)</div>
              <div className="value">{dbCounters.total ?? 0}</div>
            </div>
          </div>

          <h3>Last Decision</h3>
          <div className="last-result">
            <p>
              Result:{" "}
              <span className={lastResult.passed ? "ok" : "bad"}>
                {lastResult.passed === undefined
                  ? "---"
                  : lastResult.passed
                    ? "PASS"
                    : "FAIL"}
              </span>
            </p>
            <p>Inspection ID: {lastResult.inspection_id || "-"}</p>
            <p>Confidence: {lastResult.confidence?.toFixed?.(3) ?? "-"}</p>
            <p>Failure reasons: {(lastResult.failure_reasons || []).join(", ") || "-"}</p>
          </div>

          <h3>ROI Settings</h3>
          <form className="roi-form" onSubmit={applyRoi}>
            <label>
              ROI Enabled
              <input
                type="checkbox"
                checked={Boolean(roiDraft.enabled)}
                onChange={(event) =>
                  setRoiDraft((prev) => ({
                    ...prev,
                    enabled: event.target.checked,
                  }))
                }
              />
            </label>
            <label>
              X
              <input
                type="number"
                min="0"
                value={roiDraft.x}
                onChange={(event) =>
                  setRoiDraft((prev) => ({ ...prev, x: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              Y
              <input
                type="number"
                min="0"
                value={roiDraft.y}
                onChange={(event) =>
                  setRoiDraft((prev) => ({ ...prev, y: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              Width
              <input
                type="number"
                min="1"
                value={roiDraft.width}
                onChange={(event) =>
                  setRoiDraft((prev) => ({ ...prev, width: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              Height
              <input
                type="number"
                min="1"
                value={roiDraft.height}
                onChange={(event) =>
                  setRoiDraft((prev) => ({ ...prev, height: Number(event.target.value) }))
                }
              />
            </label>
            <button type="submit" disabled={busyAction.length > 0}>
              Apply ROI
            </button>
          </form>

          {config && (
            <div className="config-meta subtle">
              Camera source: {String(config.camera?.source ?? 0)} | Resolution:{" "}
              {config.camera?.width}x{config.camera?.height} @ {config.camera?.fps} FPS
            </div>
          )}
        </section>

        <section className="panel recent-panel">
          <h2>Recent Failed Inspections</h2>
          <div className="failure-list">
            {recentFailures.length === 0 && (
              <div className="subtle">No recent failed records available.</div>
            )}
            {recentFailures.map((item) => (
              <article className="failure-item" key={item.inspection_id}>
                <div className="failure-info">
                  <div>ID: {item.inspection_id}</div>
                  <div>Time: {formatDate(item.inspected_at)}</div>
                  <div>Confidence: {Number(item.confidence || 0).toFixed(3)}</div>
                  <div>Reason: {(item.failure_reasons || []).join(", ") || "-"}</div>
                </div>
                {item.image_url ? (
                  <img
                    src={`${API_BASE}${item.image_url}?v=${encodeURIComponent(item.inspected_at)}`}
                    alt={item.inspection_id}
                  />
                ) : (
                  <div className="no-image">No image saved</div>
                )}
              </article>
            ))}
          </div>
        </section>

        <section className="panel table-panel">
          <h2>Recent Inspection Records</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Inspection ID</th>
                  <th>Timestamp</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {recentResults.length === 0 && (
                  <tr>
                    <td colSpan="4" className="subtle center">
                      No inspection records available.
                    </td>
                  </tr>
                )}
                {recentResults.map((row) => (
                  <tr key={row.inspection_id}>
                    <td>{row.inspection_id}</td>
                    <td>{formatDate(row.inspected_at)}</td>
                    <td className={row.passed ? "ok" : "bad"}>
                      {row.passed ? "PASS" : "FAIL"}
                    </td>
                    <td>{Number(row.confidence || 0).toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

