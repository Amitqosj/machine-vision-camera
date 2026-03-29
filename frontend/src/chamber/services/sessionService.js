/**
 * Session manifest — POST /api/chamber/session/save (server updates saveSystem + session).
 */
import { normalizeChamberSnapshot, requestJson } from "../api/client";

function applyEnvelope(dispatch, body) {
  if (body?.chamber) {
    const n = normalizeChamberSnapshot(body.chamber);
    if (n) dispatch({ type: "HYDRATE_CHAMBER", payload: { snapshot: n, mode: "full" } });
  }
}

export async function saveSession(dispatch, log, sessionSnapshot) {
  try {
    const body = await requestJson("/api/chamber/session/save", {
      method: "POST",
      body: JSON.stringify({
        save_path: sessionSnapshot?.savePath || "D:\\ChamberRecordings",
        session_name: sessionSnapshot?.name,
        batch_id: sessionSnapshot?.batchId,
      }),
    });
    applyEnvelope(dispatch, body);
    log("Session saved (API)");
  } catch (e) {
    dispatch({ type: "SAVE_SYSTEM_PATCH", payload: { ok: false } });
    log(`Session save failed: ${e.message}`);
    throw e;
  }
}

export function generateSessionName(format, batchId) {
  const date = new Date().toISOString().slice(0, 10);
  return format
    .replace("{date}", date)
    .replace("{batch}", batchId || "batch")
    .replace("{session}", "live");
}
