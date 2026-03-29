/**
 * Camera orchestration via /api/chamber/*.
 * Machine vision: real inspection pipeline (start/stop) on preview & recording.
 * USB slots: simulated devices + MJPEG placeholders from backend.
 */
import { normalizeChamberSnapshot, requestJson } from "../api/client";
import { CAMERA_KEYS } from "../state/chamberReducer";

const SLUG_BY_KEY = {
  [CAMERA_KEYS.machineVision]: "machine-vision",
  [CAMERA_KEYS.usb1]: "usb-1",
  [CAMERA_KEYS.usb2]: "usb-2",
};

function slugFor(key) {
  const s = SLUG_BY_KEY[key];
  if (!s) throw new Error(`Unknown camera key: ${key}`);
  return s;
}

function applyEnvelope(dispatch, body) {
  if (body?.chamber) {
    const n = normalizeChamberSnapshot(body.chamber);
    if (n) dispatch({ type: "HYDRATE_CHAMBER", payload: { snapshot: n, mode: "full" } });
  }
}

function cameraLabel(key) {
  if (key === CAMERA_KEYS.machineVision) return "Machine vision";
  if (key === CAMERA_KEYS.usb1) return "USB 1";
  return "USB 2";
}

export async function connectCamera(dispatch, key, log) {
  const slug = slugFor(key);
  log(`[${cameraLabel(key)}] connect → API`);
  dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: true, lastError: null } } });
  try {
    const body = await requestJson(`/api/chamber/cameras/${slug}/connect`, { method: "POST" });
    applyEnvelope(dispatch, body);
    log(`[${cameraLabel(key)}] connected`);
  } catch (e) {
    dispatch({
      type: "CAMERA_PATCH",
      payload: { key, patch: { busy: false, lastError: e.message, status: "Error" } },
    });
    log(`[${cameraLabel(key)}] connect failed: ${e.message}`);
    throw e;
  }
}

export async function disconnectCamera(dispatch, key, log) {
  const slug = slugFor(key);
  log(`[${cameraLabel(key)}] disconnect → API`);
  dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: true } } });
  try {
    const body = await requestJson(`/api/chamber/cameras/${slug}/disconnect`, { method: "POST" });
    applyEnvelope(dispatch, body);
    log(`[${cameraLabel(key)}] disconnected`);
  } catch (e) {
    dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: false, lastError: e.message } } });
    log(`[${cameraLabel(key)}] disconnect failed: ${e.message}`);
    throw e;
  }
}

export async function togglePreview(dispatch, key, log, enabled) {
  const slug = slugFor(key);
  log(`[${cameraLabel(key)}] preview ${enabled ? "ON" : "OFF"} → API`);
  dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: true } } });
  try {
    const body = await requestJson(`/api/chamber/cameras/${slug}/preview`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    });
    applyEnvelope(dispatch, body);
  } catch (e) {
    dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: false, lastError: e.message } } });
    log(`[${cameraLabel(key)}] preview failed: ${e.message}`);
    throw e;
  }
}

export async function captureImage(dispatch, key, log, _sessionDispatch) {
  const slug = slugFor(key);
  log(`[${cameraLabel(key)}] capture → API`);
  dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: true } } });
  try {
    const body = await requestJson(`/api/chamber/cameras/${slug}/capture`, { method: "POST" });
    applyEnvelope(dispatch, body);
    log(`[${cameraLabel(key)}] capture ok`);
  } catch (e) {
    dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: false, lastError: e.message } } });
    log(`[${cameraLabel(key)}] capture failed: ${e.message}`);
    throw e;
  }
}

export async function setRecording(dispatch, key, log, _sessionDispatch, recording) {
  const slug = slugFor(key);
  log(`[${cameraLabel(key)}] recording ${recording ? "ON" : "OFF"} → API`);
  dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: true } } });
  try {
    const body = await requestJson(`/api/chamber/cameras/${slug}/recording`, {
      method: "POST",
      body: JSON.stringify({ recording }),
    });
    applyEnvelope(dispatch, body);
  } catch (e) {
    dispatch({ type: "CAMERA_PATCH", payload: { key, patch: { busy: false, lastError: e.message } } });
    log(`[${cameraLabel(key)}] recording failed: ${e.message}`);
    throw e;
  }
}

export async function connectAll(dispatch, log) {
  for (const key of Object.values(CAMERA_KEYS)) {
    await connectCamera(dispatch, key, log);
  }
}

export async function stopAllCameras(dispatch, log) {
  for (const key of Object.values(CAMERA_KEYS)) {
    await disconnectCamera(dispatch, key, log);
  }
}

export async function startAllPreviews(dispatch, log) {
  for (const key of Object.values(CAMERA_KEYS)) {
    await togglePreview(dispatch, key, log, true);
  }
}

export async function captureAll(dispatch, log, sessionDispatch) {
  for (const key of Object.values(CAMERA_KEYS)) {
    await captureImage(dispatch, key, log, sessionDispatch);
  }
}

export async function recordAll(dispatch, log, sessionDispatch, recording) {
  for (const key of Object.values(CAMERA_KEYS)) {
    await setRecording(dispatch, key, log, sessionDispatch, recording);
  }
}
