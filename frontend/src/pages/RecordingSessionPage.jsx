import { useCallback } from "react";
import { Link } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import * as recordingService from "../chamber/services/recordingService";
import * as sessionService from "../chamber/services/sessionService";
import { StatusBadge } from "../chamber/components/StatusBadge";
import { CAMERA_KEYS } from "../chamber/state/chamberReducer";

export default function RecordingSessionPage() {
  const { state, dispatch } = useChamber();
  const log = useCallback(
    (line) => dispatch({ type: "LOG", payload: line }),
    [dispatch]
  );

  const session = state.session;
  const anyRec =
    state.cameras[CAMERA_KEYS.machineVision].recording ||
    state.cameras[CAMERA_KEYS.usb1].recording ||
    state.cameras[CAMERA_KEYS.usb2].recording;

  const updateSession = (patch) => dispatch({ type: "SESSION_PATCH", payload: patch });

  return (
    <div className="ch-page">
      <div className="ch-breadcrumb">
        <Link to="/">Dashboard</Link>
        <span>/</span>
        <span>Recording & session</span>
      </div>
      <header className="ch-page-head">
        <div>
          <h1>Recording & session management</h1>
          <p className="ch-muted">
            Recording flags sync to <code>/api/chamber</code>. Swap <code>recordingService</code> for
            FFmpeg mux when ready.
          </p>
        </div>
        <StatusBadge tone={anyRec ? "warn" : "neutral"} pulse={anyRec}>
          {anyRec ? "Recording" : "Idle"}
        </StatusBadge>
      </header>

      <section className="ch-panel ch-session-meta">
        <h2>Active session</h2>
        <div className="ch-form-row">
          <label className="ch-field">
            Session name
            <input
              value={session.name}
              onChange={(e) => updateSession({ name: e.target.value })}
            />
          </label>
          <label className="ch-field">
            Batch ID
            <input
              value={session.batchId}
              onChange={(e) => updateSession({ batchId: e.target.value })}
            />
          </label>
          <label className="ch-field">
            Timestamp (server sync later)
            <input readOnly value={new Date().toISOString()} className="ch-input-readonly" />
          </label>
        </div>
        <div className="ch-toolbar">
          <button
            type="button"
            onClick={() =>
              void sessionService.saveSession(dispatch, log, {
                savePath: state.settings.savePath,
                startedAt: session.startedAt || new Date().toISOString(),
              })
            }
          >
            Save session manifest
          </button>
          <button type="button" onClick={() => void recordingService.startGlobalRecording(dispatch, log, dispatch)}>
            Start all recordings
          </button>
          <button type="button" onClick={() => void recordingService.stopGlobalRecording(dispatch, log, dispatch)}>
            Stop all recordings
          </button>
          <button
            type="button"
            className="ch-ghost"
            onClick={() =>
              log("Export package (placeholder) — zip frames + CSV via backend job.")
            }
          >
            Export / download (placeholder)
          </button>
        </div>
      </section>

      <div className="ch-split">
        <section className="ch-panel">
          <h2>Captured images (from API)</h2>
          <ul className="ch-list">
            {session.capturedImages.length === 0 && (
              <li className="ch-muted">No captures yet.</li>
            )}
            {session.capturedImages.map((item) => (
              <li key={item.id}>
                <strong>{item.label}</strong>
                <span className="ch-muted"> {item.at}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="ch-panel">
          <h2>Recorded segments (from API)</h2>
          <ul className="ch-list">
            {session.recordedVideos.length === 0 && (
              <li className="ch-muted">No segments yet.</li>
            )}
            {session.recordedVideos.map((item) => (
              <li key={item.id}>
                <strong>{item.label}</strong>
                <span className="ch-muted"> {item.at}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
