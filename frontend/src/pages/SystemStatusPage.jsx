import { Link } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import { CAMERA_KEYS } from "../chamber/state/chamberReducer";
import { StatusBadge } from "../chamber/components/StatusBadge";

function Row({ label, value, tone }) {
  return (
    <div className="ch-status-row">
      <span>{label}</span>
      <StatusBadge tone={tone}>{value}</StatusBadge>
    </div>
  );
}

export default function SystemStatusPage() {
  const { state } = useChamber();
  const mv = state.cameras[CAMERA_KEYS.machineVision];
  const u1 = state.cameras[CAMERA_KEYS.usb1];
  const u2 = state.cameras[CAMERA_KEYS.usb2];

  const recordingAny = mv.recording || u1.recording || u2.recording;

  return (
    <div className="ch-page">
      <div className="ch-breadcrumb">
        <Link to="/">Dashboard</Link>
        <span>/</span>
        <span>System status</span>
      </div>
      <header className="ch-page-head">
        <div>
          <h1>System status</h1>
          <p className="ch-muted">Subsystem health matrix — extend with heartbeat from backend.</p>
        </div>
      </header>

      <section className="ch-status-grid">
        <div className="ch-panel">
          <h2>Cameras</h2>
          <Row label="Machine vision" value={mv.status} tone={mv.connected ? "ok" : "bad"} />
          <Row label="USB camera 1" value={u1.status} tone={u1.connected ? "ok" : "bad"} />
          <Row label="USB camera 2" value={u2.status} tone={u2.connected ? "ok" : "bad"} />
        </div>
        <div className="ch-panel">
          <h2>Chamber I/O</h2>
          <Row
            label="Arduino"
            value={state.arduino.connected ? "Online" : "Offline"}
            tone={state.arduino.connected ? "ok" : "neutral"}
          />
          <Row
            label="Light system"
            value={`${state.lightSystem.mode} · ${state.lightSystem.level}%`}
            tone={state.lightSystem.healthy ? "ok" : "bad"}
          />
        </div>
        <div className="ch-panel">
          <h2>Recording & storage</h2>
          <Row
            label="Recording"
            value={recordingAny ? "Active" : "Idle"}
            tone={recordingAny ? "warn" : "neutral"}
          />
          <Row
            label="Save system"
            value={state.saveSystem.ok ? "Healthy" : "Fault"}
            tone={state.saveSystem.ok ? "ok" : "bad"}
          />
          <p className="ch-muted ch-small">
            Last write: {state.saveSystem.lastWriteAt || "—"} to {state.saveSystem.lastPath}
          </p>
        </div>
      </section>
    </div>
  );
}
