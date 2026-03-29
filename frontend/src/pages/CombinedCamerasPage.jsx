import { useCallback } from "react";
import { Link } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import { CAMERA_KEYS } from "../chamber/state/chamberReducer";
import * as cameraService from "../chamber/services/cameraService";
import { CameraPreviewPlaceholder } from "../chamber/components/CameraPreviewPlaceholder";
import { StatusBadge } from "../chamber/components/StatusBadge";

const ORDER = [
  { key: CAMERA_KEYS.machineVision, label: "Machine vision" },
  { key: CAMERA_KEYS.usb1, label: "USB 1" },
  { key: CAMERA_KEYS.usb2, label: "USB 2" },
];

export default function CombinedCamerasPage() {
  const { state, dispatch } = useChamber();
  const log = useCallback(
    (line) => dispatch({ type: "LOG", payload: line }),
    [dispatch]
  );

  const anyBusy = ORDER.some(({ key }) => state.cameras[key].busy);

  return (
    <div className="ch-page">
      <div className="ch-breadcrumb">
        <Link to="/">Dashboard</Link>
        <span>/</span>
        <span>All cameras</span>
      </div>
      <header className="ch-page-head">
        <div>
          <h1>Multi-camera view</h1>
          <p className="ch-muted">
            Synchronized controls — implement timestamp alignment & mux in{" "}
            <code>recordingService</code>.
          </p>
        </div>
      </header>

      <div className="ch-multi-toolbar">
        <button type="button" disabled={anyBusy} onClick={() => void cameraService.connectAll(dispatch, log)}>
          Start all (connect)
        </button>
        <button
          type="button"
          disabled={anyBusy}
          onClick={() => void cameraService.startAllPreviews(dispatch, log)}
        >
          Start all previews
        </button>
        <button
          type="button"
          disabled={anyBusy}
          onClick={() => void cameraService.captureAll(dispatch, log, dispatch)}
        >
          Capture all
        </button>
        <button
          type="button"
          disabled={anyBusy}
          onClick={() => void cameraService.recordAll(dispatch, log, dispatch, true)}
        >
          Record all
        </button>
        <button
          type="button"
          disabled={anyBusy}
          onClick={() => void cameraService.recordAll(dispatch, log, dispatch, false)}
        >
          Stop all recordings
        </button>
        <button type="button" disabled={anyBusy} onClick={() => void cameraService.stopAllCameras(dispatch, log)}>
          Disconnect all
        </button>
      </div>

      <div className="ch-multi-grid">
        {ORDER.map(({ key, label }) => {
          const cam = state.cameras[key];
          return (
            <div key={key} className="ch-multi-cell">
              <div className="ch-multi-cell-head">
                <strong>{label}</strong>
                <StatusBadge tone={cam.connected ? "ok" : "bad"}>{cam.status}</StatusBadge>
                {cam.recording && <StatusBadge tone="warn">REC</StatusBadge>}
              </div>
              <CameraPreviewPlaceholder
                label={label}
                preview={cam.preview}
                connected={cam.connected}
                busy={cam.busy}
                streamUrl={cam.streamUrl}
              />
              <div className="ch-muted ch-mini-metrics">
                {cam.resolution} @ {cam.fps} FPS
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
