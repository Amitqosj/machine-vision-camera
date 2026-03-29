/**
 * Recording orchestration — mock.
 * Real: backend muxer (FFmpeg) with synchronized timestamps from all cameras.
 */
import { CAMERA_KEYS } from "../state/chamberReducer";
import { setRecording } from "./cameraService";

export async function startGlobalRecording(dispatch, log, sessionDispatch) {
  dispatch({ type: "SESSION_PATCH", payload: { name: `REC-${Date.now()}` } });
  for (const key of Object.values(CAMERA_KEYS)) {
    await setRecording(dispatch, key, log, sessionDispatch, true);
  }
  log("Global recording started (mock)");
}

export async function stopGlobalRecording(dispatch, log, sessionDispatch) {
  for (const key of Object.values(CAMERA_KEYS)) {
    await setRecording(dispatch, key, log, sessionDispatch, false);
  }
  log("Global recording stopped (mock)");
}
