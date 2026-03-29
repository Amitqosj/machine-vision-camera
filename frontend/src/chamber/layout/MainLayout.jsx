import { NavLink, Outlet } from "react-router-dom";

const nav = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/camera/machine-vision", label: "Machine vision" },
  { to: "/camera/usb-1", label: "USB cam 1" },
  { to: "/camera/usb-2", label: "USB cam 2" },
  { to: "/camera/all", label: "All cameras" },
  { to: "/recording", label: "Recording & session" },
  { to: "/hardware", label: "Hardware / Arduino" },
  { to: "/status", label: "System status" },
  { to: "/settings", label: "Settings" },
  { to: "/legacy-inspection", label: "Inspection (live API)" },
];

export function MainLayout() {
  return (
    <div className="ch-shell">
      <aside className="ch-sidebar">
        <div className="ch-brand">
          <div className="ch-brand-title">Chamber Control</div>
          <div className="ch-brand-sub">Hybrid recording system</div>
        </div>
        <nav className="ch-nav">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `ch-nav-link${isActive ? " ch-nav-active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="ch-sidebar-foot ch-muted">
          Mock services active. Replace with SDK/serial in service layer.
        </div>
      </aside>
      <div className="ch-main">
        <Outlet />
      </div>
    </div>
  );
}
