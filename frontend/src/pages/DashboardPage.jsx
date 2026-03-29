import { Link } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import { StatusBadge } from "../chamber/components/StatusBadge";
import { CAMERA_KEYS } from "../chamber/state/chamberReducer";

const cards = [
  {
    to: "/camera/machine-vision",
    title: "Machine vision camera",
    desc: "Primary inspection / industrial sensor feed",
    icon: "MV",
  },
  {
    to: "/camera/usb-1",
    title: "USB camera 1",
    desc: "Secondary chamber overview",
    icon: "U1",
  },
  {
    to: "/camera/usb-2",
    title: "USB camera 2",
    desc: "Tertiary angle / witness camera",
    icon: "U2",
  },
  {
    to: "/camera/all",
    title: "All cameras",
    desc: "Synchronized multi-feed dashboard",
    icon: "ALL",
  },
  {
    to: "/recording",
    title: "Recording control",
    desc: "Session, batch, captures & exports",
    icon: "REC",
  },
  {
    to: "/hardware",
    title: "Hardware / lights",
    desc: "Arduino, relays, chamber I/O",
    icon: "IO",
  },
  {
    to: "/status",
    title: "System status",
    desc: "Health matrix for all subsystems",
    icon: "SYS",
  },
  {
    to: "/settings",
    title: "Settings",
    desc: "Paths, serial, SDK placeholders",
    icon: "CFG",
  },
];

export default function DashboardPage() {
  const { state } = useChamber();
  const mv = state.cameras[CAMERA_KEYS.machineVision];
  const anyRecording =
    mv.recording || state.cameras[CAMERA_KEYS.usb1].recording || state.cameras[CAMERA_KEYS.usb2].recording;

  return (
    <div className="ch-page">
      <header className="ch-page-head">
        <div>
          <h1>Operations dashboard</h1>
          <p className="ch-muted">
            Industrial recording chamber — modular control surface. Hardware integration plugs into
            service modules under <code>src/chamber/services/</code>.
          </p>
        </div>
        <div className="ch-head-badges">
          {anyRecording && <StatusBadge tone="warn pulse">Recording</StatusBadge>}
          <StatusBadge tone={state.arduino.connected ? "ok" : "neutral"}>
            Arduino {state.arduino.connected ? "online" : "offline"}
          </StatusBadge>
          <StatusBadge tone={state.saveSystem.ok ? "ok" : "bad"}>
            Save {state.saveSystem.ok ? "OK" : "fault"}
          </StatusBadge>
        </div>
      </header>

      <section className="ch-card-grid">
        {cards.map((c) => (
          <Link key={c.to} to={c.to} className="ch-dash-card">
            <div className="ch-dash-icon">{c.icon}</div>
            <div>
              <h2>{c.title}</h2>
              <p className="ch-muted">{c.desc}</p>
            </div>
            <span className="ch-dash-arrow" aria-hidden>
              →
            </span>
          </Link>
        ))}
      </section>
    </div>
  );
}
