/**
 * Arduino controls via /api/chamber/arduino/* (simulated on server; swap store for pyserial).
 */
import { normalizeChamberSnapshot, requestJson } from "../api/client";

function applyEnvelope(dispatch, body) {
  if (body?.chamber) {
    const n = normalizeChamberSnapshot(body.chamber);
    if (n) dispatch({ type: "HYDRATE_CHAMBER", payload: { snapshot: n, mode: "full" } });
  }
}

export async function connectArduino(dispatch, log) {
  dispatch({ type: "ARDUINO_PATCH", payload: { busy: true, lastError: null } });
  try {
    const body = await requestJson("/api/chamber/arduino/connect", { method: "POST" });
    applyEnvelope(dispatch, body);
    log("Arduino connected (API)");
  } catch (e) {
    dispatch({ type: "ARDUINO_PATCH", payload: { busy: false, lastError: e.message } });
    log(`Arduino connect failed: ${e.message}`);
    throw e;
  }
}

export async function disconnectArduino(dispatch, log) {
  dispatch({ type: "ARDUINO_PATCH", payload: { busy: true } });
  try {
    const body = await requestJson("/api/chamber/arduino/disconnect", { method: "POST" });
    applyEnvelope(dispatch, body);
    log("Arduino disconnected (API)");
  } catch (e) {
    dispatch({ type: "ARDUINO_PATCH", payload: { busy: false } });
    log(`Arduino disconnect failed: ${e.message}`);
    throw e;
  }
}

export async function setLight(dispatch, log, on) {
  try {
    const body = await requestJson("/api/chamber/arduino/light", {
      method: "POST",
      body: JSON.stringify({ on }),
    });
    applyEnvelope(dispatch, body);
    log(`Light ${on ? "ON" : "OFF"} (API)`);
  } catch (e) {
    log(`Light command failed: ${e.message}`);
    throw e;
  }
}

export async function setAutoLight(dispatch, log, enabled) {
  const body = await requestJson("/api/chamber/arduino/auto-light", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
  applyEnvelope(dispatch, body);
  log(`Auto light API: ${enabled}`);
}

export async function triggerCapture(dispatch, log) {
  const body = await requestJson("/api/chamber/arduino/trigger", { method: "POST" });
  applyEnvelope(dispatch, body);
  log("Trigger sent (API)");
}

export async function setRelayPlaceholder(dispatch, log, channel, on) {
  const body = await requestJson("/api/chamber/arduino/relay", {
    method: "POST",
    body: JSON.stringify({ channel, on }),
  });
  applyEnvelope(dispatch, body);
  log(`Relay CH${channel} (API)`);
}

export async function patchSerial(dispatch, log, comPort, baudRate) {
  const body = await requestJson("/api/chamber/arduino/serial", {
    method: "PATCH",
    body: JSON.stringify({ com_port: comPort, baud_rate: baudRate }),
  });
  applyEnvelope(dispatch, body);
  log("Serial settings PATCH (API)");
}
