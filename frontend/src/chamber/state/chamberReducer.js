/** Global mock state for the hybrid chamber dashboard. Replace dispatch targets with real SDK/serial calls in service layer. */

export const CAMERA_KEYS = {
  machineVision: "machineVision",
  usb1: "usb1",
  usb2: "usb2",
};

export function createInitialCameraState() {
  return {
    connected: false,
    preview: false,
    recording: false,
    status: "Disconnected",
    resolution: "—",
    fps: "—",
    busy: false,
    lastError: null,
    streamUrl: null,
  };
}

export const initialChamberState = {
  cameras: {
    [CAMERA_KEYS.machineVision]: createInitialCameraState(),
    [CAMERA_KEYS.usb1]: createInitialCameraState(),
    [CAMERA_KEYS.usb2]: createInitialCameraState(),
  },
  arduino: {
    connected: false,
    lightOn: false,
    autoLight: false,
    comPort: "COM3",
    baudRate: 115200,
    busy: false,
    lastError: null,
  },
  lightSystem: {
    mode: "manual",
    level: 0,
    healthy: true,
  },
  saveSystem: {
    ok: true,
    lastPath: "—",
    lastWriteAt: null,
  },
  session: {
    name: "Session-001",
    batchId: "BATCH-2026-001",
    startedAt: null,
    capturedImages: [],
    recordedVideos: [],
  },
  settings: {
    savePath: "D:\\ChamberRecordings",
    sessionNameFormat: "{date}_{batch}_{session}",
    captureMode: "still",
    autoRecordOnTrigger: false,
    futureSdkNotes:
      "Wire OpenCV / vendor SDK here; expose device index and transport in backend.",
  },
  commandLog: [],
};

const MAX_LOG = 120;

function pushLog(state, line) {
  const next = [...state.commandLog, `${new Date().toISOString()}  ${line}`];
  return next.slice(-MAX_LOG);
}

export function chamberReducer(state, action) {
  switch (action.type) {
    case "LOG": {
      return { ...state, commandLog: pushLog(state, action.payload) };
    }
    case "CAMERA_PATCH": {
      const { key, patch } = action.payload;
      return {
        ...state,
        cameras: {
          ...state.cameras,
          [key]: { ...state.cameras[key], ...patch },
        },
      };
    }
    case "ARDUINO_PATCH": {
      return {
        ...state,
        arduino: { ...state.arduino, ...action.payload },
      };
    }
    case "LIGHT_PATCH": {
      return {
        ...state,
        lightSystem: { ...state.lightSystem, ...action.payload },
      };
    }
    case "SAVE_SYSTEM_PATCH": {
      return {
        ...state,
        saveSystem: { ...state.saveSystem, ...action.payload },
      };
    }
    case "SESSION_PATCH": {
      return {
        ...state,
        session: { ...state.session, ...action.payload },
      };
    }
    case "SESSION_ADD_IMAGE": {
      return {
        ...state,
        session: {
          ...state.session,
          capturedImages: [
            {
              id: action.payload.id,
              label: action.payload.label,
              at: new Date().toISOString(),
            },
            ...state.session.capturedImages,
          ].slice(0, 50),
        },
      };
    }
    case "SESSION_ADD_VIDEO": {
      return {
        ...state,
        session: {
          ...state.session,
          recordedVideos: [
            {
              id: action.payload.id,
              label: action.payload.label,
              at: new Date().toISOString(),
            },
            ...state.session.recordedVideos,
          ].slice(0, 50),
        },
      };
    }
    case "SETTINGS_PATCH": {
      return {
        ...state,
        settings: { ...state.settings, ...action.payload },
      };
    }
    case "HYDRATE_CHAMBER": {
      const { snapshot: n, mode = "full" } = action.payload || {};
      if (!n) return state;
      const base = {
        ...state,
        cameras: {
          machineVision: { ...state.cameras.machineVision, ...n.cameras.machineVision },
          usb1: { ...state.cameras.usb1, ...n.cameras.usb1 },
          usb2: { ...state.cameras.usb2, ...n.cameras.usb2 },
        },
        arduino: { ...state.arduino, ...n.arduino },
        lightSystem: { ...state.lightSystem, ...n.lightSystem },
        saveSystem: { ...state.saveSystem, ...n.saveSystem },
        commandLog: n.commandLog,
      };
      if (mode === "status") {
        return {
          ...base,
          session: {
            ...state.session,
            startedAt: n.session.startedAt ?? state.session.startedAt,
            capturedImages: n.session.capturedImages,
            recordedVideos: n.session.recordedVideos,
          },
        };
      }
      return {
        ...base,
        session: {
          ...state.session,
          name: n.session.name,
          batchId: n.session.batchId,
          startedAt: n.session.startedAt,
          capturedImages: n.session.capturedImages,
          recordedVideos: n.session.recordedVideos,
        },
      };
    }
    default:
      return state;
  }
}
