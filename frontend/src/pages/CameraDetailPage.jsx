import { useCallback, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import { CAMERA_KEYS } from "../chamber/state/chamberReducer";
import * as cameraService from "../chamber/services/cameraService";
import * as sessionService from "../chamber/services/sessionService";
import { CameraPreviewPlaceholder } from "../chamber/components/CameraPreviewPlaceholder";
import { StatusBadge } from "../chamber/components/StatusBadge";

const SLUG_MAP = {
  "machine-vision": CAMERA_KEYS.machineVision,
  "usb-1": CAMERA_KEYS.usb1,
  "usb-2": CAMERA_KEYS.usb2,
};

const TITLES = {
  [CAMERA_KEYS.machineVision]: "Machine vision camera",
  [CAMERA_KEYS.usb1]: "USB camera 1",
  [CAMERA_KEYS.usb2]: "USB camera 2",
};

export default function CameraDetailPage() {
  const { slug } = useParams();
  const { state, dispatch } = useChamber();
  const key = SLUG_MAP[slug];

  const camera = key ? state.cameras[key] : null;

  const log = useCallback(
    (line) => dispatch({ type: "LOG", payload: line }),
    [dispatch]
  );

  const title = useMemo(() => (key ? TITLES[key] : "Camera"), [key]);

  if (!key || !camera) {
    return (
      <div className="ch-page">
        <p>Unknown camera route.</p>
        <Link to="/">Back</Link>
      </div>
    );
  }

  const busy = camera.busy;

  return (
    <div className="ch-page">
      <div className="ch-breadcrumb">
        <Link to="/">Dashboard</Link>
        <span>/</span>
        <span>{title}</span>
      </div>
      <header className="ch-page-head">
        <div>
          <h1>{title}</h1>
          <p className="ch-muted">
            Device control surface — no browser webcam coupling. Backend will expose frames via
            SDK/OpenCV pipeline.
          </p>
        </div>
        <div className="ch-head-badges">
          <StatusBadge tone={camera.connected ? "ok" : "bad"}>
            {camera.status}
          </StatusBadge>
          {camera.recording && <StatusBadge tone="warn">REC</StatusBadge>}
        </div>
      </header>

      <CameraPreviewPlaceholder
        label={title}
        preview={camera.preview}
        connected={camera.connected}
        busy={busy}
        streamUrl={camera.streamUrl}
      />

      <div className="ch-toolbar">
        <button
          type="button"
          disabled={busy || camera.connected}
          onClick={() => void cameraService.connectCamera(dispatch, key, log)}
        >
          Connect
        </button>
        <button
          type="button"
          disabled={busy || !camera.connected}
          onClick={() => void cameraService.disconnectCamera(dispatch, key, log)}
        >
          Disconnect
        </button>
        <button
          type="button"
          disabled={busy || !camera.connected || camera.preview}
          onClick={() => void cameraService.togglePreview(dispatch, key, log, true)}
        >
          Start preview
        </button>
        <button
          type="button"
          disabled={busy || !camera.preview}
          onClick={() => void cameraService.togglePreview(dispatch, key, log, false)}
        >
          Stop preview
        </button>
        <button
          type="button"
          disabled={busy || !camera.connected}
          onClick={() => void cameraService.captureImage(dispatch, key, log, dispatch)}
        >
          Capture image
        </button>
        <button
          type="button"
          disabled={busy || !camera.connected || camera.recording}
          onClick={() =>
            void cameraService.setRecording(dispatch, key, log, dispatch, true)
          }
        >
          Start recording
        </button>
        <button
          type="button"
          disabled={busy || !camera.recording}
          onClick={() =>
            void cameraService.setRecording(dispatch, key, log, dispatch, false)
          }
        >
          Stop recording
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            void sessionService.saveSession(dispatch, log, {
              savePath: state.settings.savePath,
              startedAt: state.session.startedAt,
            })
          }
        >
          Save session
        </button>
      </div>

      <section className="ch-panel ch-metrics">
        <h2>Telemetry</h2>
        <dl className="ch-dl">
          <dt>Resolution</dt>
          <dd>{camera.resolution}</dd>
          <dt>FPS</dt>
          <dd>{camera.fps}</dd>
          <dt>Stream</dt>
          <dd>{camera.streamUrl || "—"}</dd>
          <dt>Connection</dt>
          <dd>{camera.connected ? "API / backend" : "None"}</dd>
          {camera.lastError && (
            <>
              <dt>Last error</dt>
              <dd className="ch-error-text">{camera.lastError}</dd>
            </>
          )}
        </dl>
      </section>
    </div>
  );
}
