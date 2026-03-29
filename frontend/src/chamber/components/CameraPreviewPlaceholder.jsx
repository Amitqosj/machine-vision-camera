import { getApiBase } from "../api/client";
import { StatusBadge } from "./StatusBadge";

export function CameraPreviewPlaceholder({
  label,
  preview,
  connected,
  busy,
  streamUrl,
}) {
  const apiBase = getApiBase();
  const src = streamUrl && preview ? `${apiBase}${streamUrl}` : null;

  return (
    <div className={`ch-preview ${preview ? "ch-preview-live" : ""} ${busy ? "ch-preview-busy" : ""}`}>
      {src ? (
        <div className="ch-preview-stream">
          <img className="ch-stream-img" key={src} src={src} alt={`${label} live`} />
        </div>
      ) : (
        <div className="ch-preview-grid" aria-hidden />
      )}
      <div className="ch-preview-meta">
        <span className="ch-preview-label">{label}</span>
        {!connected && <StatusBadge tone="bad">No device</StatusBadge>}
        {connected && !preview && <StatusBadge tone="warn">Idle</StatusBadge>}
        {connected && preview && <StatusBadge tone="ok">Preview</StatusBadge>}
        {busy && <StatusBadge tone="neutral">Working…</StatusBadge>}
      </div>
      <p className="ch-preview-note">
        {streamUrl && preview
          ? "Live stream from backend (MJPEG)."
          : "Connect, then start preview to open the MJPEG stream."}
      </p>
    </div>
  );
}
