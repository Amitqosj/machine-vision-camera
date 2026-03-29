/** HTTP client for chamber dashboard — same origin or VITE_API_BASE. */

const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/+$/, "");

export function getApiBase() {
  return API_BASE;
}

export async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      detail =
        (typeof payload.detail === "string" ? payload.detail : null) ||
        payload.message ||
        detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return response.json();
}

/** Fetch full chamber snapshot (no envelope). */
export async function fetchChamberStatus() {
  return requestJson("/api/chamber/status");
}

export function normalizeChamberSnapshot(ch) {
  if (!ch || !ch.cameras) return null;

  const cam = (c) => ({
    connected: Boolean(c?.connected),
    preview: Boolean(c?.preview),
    recording: Boolean(c?.recording),
    status: c?.status ?? "—",
    resolution: c?.resolution ?? "—",
    fps: c?.fps ?? "—",
    lastError: c?.lastError ?? null,
    streamUrl: c?.streamUrl ?? null,
    busy: false,
  });

  return {
    cameras: {
      machineVision: cam(ch.cameras.machineVision),
      usb1: cam(ch.cameras.usb1),
      usb2: cam(ch.cameras.usb2),
    },
    arduino: {
      connected: Boolean(ch.arduino?.connected),
      lightOn: Boolean(ch.arduino?.lightOn),
      autoLight: Boolean(ch.arduino?.autoLight),
      comPort: ch.arduino?.comPort ?? "COM3",
      baudRate: Number(ch.arduino?.baudRate) || 115200,
      busy: false,
      lastError: ch.arduino?.lastError ?? null,
    },
    lightSystem: {
      mode: ch.lightSystem?.mode ?? "manual",
      level: Number(ch.lightSystem?.level) ?? 0,
      healthy: ch.lightSystem?.healthy !== false,
    },
    saveSystem: {
      ok: ch.saveSystem?.ok !== false,
      lastPath: ch.saveSystem?.lastPath ?? "—",
      lastWriteAt: ch.saveSystem?.lastWriteAt ?? null,
    },
    session: {
      name: ch.session?.name ?? "Session-001",
      batchId: ch.session?.batchId ?? "BATCH-2026-001",
      startedAt: ch.session?.startedAt ?? null,
      capturedImages: Array.isArray(ch.session?.capturedImages)
        ? ch.session.capturedImages
        : [],
      recordedVideos: Array.isArray(ch.session?.recordedVideos)
        ? ch.session.recordedVideos
        : [],
    },
    commandLog: Array.isArray(ch.commandLog) ? ch.commandLog : [],
  };
}
