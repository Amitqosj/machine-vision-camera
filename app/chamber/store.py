"""In-process chamber device state. USB slots are simulated; machine vision delegates to InspectionService."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import AppConfig
    from app.services.inspection_service import InspectionService

CAM_MACHINE = "machineVision"
CAM_USB1 = "usb1"
CAM_USB2 = "usb2"
CAMERA_IDS = frozenset({CAM_MACHINE, CAM_USB1, CAM_USB2})

USB_SPECS: dict[str, tuple[str, str]] = {
    CAM_USB1: ("1280×720", "30"),
    CAM_USB2: ("1280×720", "25"),
}


@dataclass
class CameraSlot:
    connected: bool = False
    preview: bool = False
    recording: bool = False
    status: str = "Disconnected"
    resolution: str = "—"
    fps: str = "—"
    last_error: str | None = None


@dataclass
class ChamberStore:
    """Thread-safe store mirrored by GET /api/chamber/status."""

    _lock: Lock = field(default_factory=Lock)
    cameras: dict[str, CameraSlot] = field(
        default_factory=lambda: {
            CAM_MACHINE: CameraSlot(),
            CAM_USB1: CameraSlot(),
            CAM_USB2: CameraSlot(),
        }
    )
    arduino_connected: bool = False
    arduino_busy: bool = False
    arduino_light_on: bool = False
    arduino_auto_light: bool = False
    com_port: str = "COM3"
    baud_rate: int = 115200
    light_mode: str = "manual"
    light_level: int = 0
    light_healthy: bool = True
    save_ok: bool = True
    save_last_path: str = "—"
    save_last_write_at: str | None = None
    session_name: str = "Session-001"
    batch_id: str = "BATCH-2026-001"
    session_started_at: str | None = None
    captured_images: list[dict[str, Any]] = field(default_factory=list)
    recorded_videos: list[dict[str, Any]] = field(default_factory=list)
    command_log: deque[str] = field(default_factory=lambda: deque(maxlen=200))

    def _log(self, line: str) -> None:
        self.command_log.append(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  {line}")

    def _slot(self, camera_id: str) -> CameraSlot:
        return self.cameras[camera_id]

    def append_command(self, line: str) -> None:
        with self._lock:
            self._log(line)

    def usb_preview_active(self, camera_id: str) -> bool:
        with self._lock:
            s = self._slot(camera_id)
            return s.connected and s.preview

    def to_public_dict(self, config: AppConfig, runtime_running: bool, runtime_camera_connected: bool) -> dict[str, Any]:
        with self._lock:
            w, h, fps = config.camera.width, config.camera.height, config.camera.fps
            mv = self.cameras[CAM_MACHINE]
            stream_base = "/api/stream.mjpg"
            usb1_stream = "/api/chamber/stream/usb1"
            usb2_stream = "/api/chamber/stream/usb2"

            def cam_payload(cid: str, slot: CameraSlot) -> dict[str, Any]:
                stream_url: str | None = None
                if cid == CAM_MACHINE:
                    if (slot.preview or slot.recording) and runtime_running:
                        stream_url = stream_base
                elif cid == CAM_USB1 and slot.preview and slot.connected:
                    stream_url = usb1_stream
                elif cid == CAM_USB2 and slot.preview and slot.connected:
                    stream_url = usb2_stream
                return {
                    "connected": slot.connected,
                    "preview": slot.preview,
                    "recording": slot.recording,
                    "status": slot.status,
                    "resolution": slot.resolution,
                    "fps": slot.fps,
                    "lastError": slot.last_error,
                    "streamUrl": stream_url,
                    "pipelineRunning": bool(runtime_running) if cid == CAM_MACHINE else None,
                    "deviceConnected": bool(runtime_camera_connected) if cid == CAM_MACHINE else None,
                }

            cameras_out = {cid: cam_payload(cid, self.cameras[cid]) for cid in CAMERA_IDS}

            return {
                "cameras": cameras_out,
                "arduino": {
                    "connected": self.arduino_connected,
                    "lightOn": self.arduino_light_on,
                    "autoLight": self.arduino_auto_light,
                    "comPort": self.com_port,
                    "baudRate": self.baud_rate,
                    "busy": self.arduino_busy,
                    "lastError": None,
                },
                "lightSystem": {
                    "mode": self.light_mode,
                    "level": self.light_level,
                    "healthy": self.light_healthy,
                },
                "saveSystem": {
                    "ok": self.save_ok,
                    "lastPath": self.save_last_path,
                    "lastWriteAt": self.save_last_write_at,
                },
                "session": {
                    "name": self.session_name,
                    "batchId": self.batch_id,
                    "startedAt": self.session_started_at,
                    "capturedImages": list(self.captured_images),
                    "recordedVideos": list(self.recorded_videos),
                },
                "commandLog": list(self.command_log),
            }

    def connect_machine_vision(self, config: AppConfig, logger: logging.Logger) -> None:
        with self._lock:
            slot = self._slot(CAM_MACHINE)
            slot.connected = True
            slot.last_error = None
            slot.resolution = f"{config.camera.width}×{config.camera.height}"
            slot.fps = str(config.camera.fps)
            slot.status = "Ready"
            self._log("Machine vision: logical connect (no pipeline start).")

    def disconnect_machine_vision(self, inspection: InspectionService, logger: logging.Logger) -> None:
        inspection.stop()
        with self._lock:
            slot = self._slot(CAM_MACHINE)
            slot.connected = False
            slot.preview = False
            slot.recording = False
            slot.status = "Disconnected"
            slot.resolution = "—"
            slot.fps = "—"
            self._log("Machine vision: disconnected; inspection stopped.")

    def set_preview_machine_vision(self, enabled: bool, inspection: InspectionService, logger: logging.Logger) -> None:
        if enabled:
            try:
                inspection.start()
            except Exception as exc:
                logger.exception("Chamber MV preview start failed")
                with self._lock:
                    sl = self._slot(CAM_MACHINE)
                    sl.last_error = str(exc)
                    sl.status = "Error"
                raise
            with self._lock:
                sl = self._slot(CAM_MACHINE)
                sl.preview = True
                sl.status = "Preview"
                sl.last_error = None
                self._log("Machine vision: preview ON (inspection pipeline started).")
        else:
            inspection.stop()
            with self._lock:
                sl = self._slot(CAM_MACHINE)
                sl.preview = False
                sl.recording = False
                sl.status = "Ready" if sl.connected else "Disconnected"
                self._log("Machine vision: preview OFF (pipeline stopped).")

    def capture_machine_vision(self, inspection: InspectionService, logger: logging.Logger) -> str:
        path = inspection.capture_snapshot()
        if path is None:
            raise ValueError(
                "No frame available. Start preview or recording so the pipeline provides frames."
            )
        cid = f"img-mv-{int(time.time() * 1000)}"
        with self._lock:
            self.captured_images.insert(
                0,
                {"id": cid, "label": f"MV snapshot: {path}", "at": _utc_now()},
            )
            del self.captured_images[50:]
            self._log(f"Machine vision: snapshot captured -> {path}")
        return str(path)

    def set_recording_machine_vision(self, recording: bool, inspection: InspectionService, logger: logging.Logger) -> None:
        if recording:
            try:
                inspection.start()
            except Exception as exc:
                logger.exception("Chamber MV recording start failed")
                with self._lock:
                    sl = self._slot(CAM_MACHINE)
                    sl.last_error = str(exc)
                    sl.status = "Error"
                raise
            with self._lock:
                sl = self._slot(CAM_MACHINE)
                sl.recording = True
                sl.preview = True
                sl.status = "Recording"
                sl.last_error = None
                self._log("Machine vision: recording started (pipeline running).")
                vid = f"mv-{int(time.time() * 1000)}"
                self.recorded_videos.insert(
                    0, {"id": vid, "label": "Machine vision segment", "at": _utc_now()}
                )
                del self.recorded_videos[50:]
        else:
            inspection.stop()
            with self._lock:
                sl = self._slot(CAM_MACHINE)
                sl.recording = False
                sl.preview = False
                sl.status = "Ready" if sl.connected else "Disconnected"
                self._log("Machine vision: recording stopped.")

    def connect_usb(self, camera_id: str, logger: logging.Logger) -> None:
        res, rs = USB_SPECS[camera_id]
        with self._lock:
            slot = self._slot(camera_id)
            slot.connected = True
            slot.preview = False
            slot.recording = False
            slot.resolution = res
            slot.fps = rs
            slot.status = "Ready"
            slot.last_error = None
            self._log(f"{camera_id}: simulated USB camera connected.")

    def disconnect_usb(self, camera_id: str, logger: logging.Logger) -> None:
        with self._lock:
            slot = self._slot(camera_id)
            slot.connected = False
            slot.preview = False
            slot.recording = False
            slot.status = "Disconnected"
            slot.resolution = "—"
            slot.fps = "—"
            self._log(f"{camera_id}: disconnected.")

    def set_preview_usb(self, camera_id: str, enabled: bool, logger: logging.Logger) -> None:
        with self._lock:
            slot = self._slot(camera_id)
            if enabled and not slot.connected:
                raise ValueError("Connect the camera before starting preview.")
            slot.preview = enabled
            slot.status = "Preview" if enabled else ("Ready" if slot.connected else "Disconnected")
            self._log(f"{camera_id}: preview {'ON' if enabled else 'OFF'} (simulated stream).")

    def capture_usb(self, camera_id: str, logger: logging.Logger) -> str:
        label = f"{camera_id} capture (simulated)"
        cid = f"img-{camera_id}-{int(time.time() * 1000)}"
        with self._lock:
            slot = self._slot(camera_id)
            if not slot.connected:
                raise ValueError("Camera not connected.")
            self.captured_images.insert(0, {"id": cid, "label": label, "at": _utc_now()})
            del self.captured_images[50:]
            self._log(f"{camera_id}: capture saved (placeholder).")
        return cid

    def set_recording_usb(self, camera_id: str, recording: bool, logger: logging.Logger) -> None:
        with self._lock:
            slot = self._slot(camera_id)
            if recording and not slot.connected:
                raise ValueError("Camera not connected.")
            slot.recording = recording
            slot.status = "Recording" if recording else ("Preview" if slot.preview else "Ready")
            if recording:
                vid = f"vid-{camera_id}-{int(time.time() * 1000)}"
                self.recorded_videos.insert(
                    0, {"id": vid, "label": f"{camera_id} segment (simulated)", "at": _utc_now()}
                )
                del self.recorded_videos[50:]
            self._log(f"{camera_id}: recording {'ON' if recording else 'OFF'} (simulated).")

    # Arduino (simulated; swap for pyserial)
    def arduino_connect(self) -> None:
        with self._lock:
            self.arduino_connected = True
            self.arduino_busy = False
            self._log("Arduino: connected (simulated).")

    def arduino_disconnect(self) -> None:
        with self._lock:
            self.arduino_connected = False
            self.arduino_light_on = False
            self.arduino_auto_light = False
            self.light_mode = "manual"
            self.light_level = 0
            self._log("Arduino: disconnected.")

    def arduino_set_serial(self, com_port: str | None, baud_rate: int | None) -> None:
        with self._lock:
            if com_port is not None:
                self.com_port = com_port
            if baud_rate is not None:
                self.baud_rate = int(baud_rate)
            self._log(f"Arduino: serial set {self.com_port} @ {self.baud_rate}")

    def arduino_light(self, on: bool) -> None:
        with self._lock:
            if not self.arduino_connected:
                raise ValueError("Arduino not connected.")
            self.arduino_light_on = on
            self.light_mode = "on" if on else "off"
            self.light_level = 100 if on else 0
            self.light_healthy = True
            self._log(f"Arduino: light {'ON' if on else 'OFF'} (simulated).")

    def set_auto_light_enabled(self, enabled: bool) -> None:
        """Toggle auto-light (avoid naming this `arduino_auto_light` — it would shadow the bool field)."""
        with self._lock:
            self.arduino_auto_light = enabled
            self.light_mode = "auto" if enabled else "manual"
            self._log(f"Arduino: auto-light {'enabled' if enabled else 'disabled'}.")

    def arduino_trigger(self) -> None:
        with self._lock:
            self._log("Arduino: hardware trigger pulse (simulated).")

    def arduino_relay(self, channel: int, on: bool) -> None:
        with self._lock:
            self._log(f"Arduino: relay CH{channel} -> {'HIGH' if on else 'LOW'} (placeholder).")

    def save_session(self, save_path: str, session_name: str | None, batch_id: str | None) -> None:
        with self._lock:
            if session_name:
                self.session_name = session_name
            if batch_id:
                self.batch_id = batch_id
            self.save_ok = True
            self.save_last_path = save_path
            self.save_last_write_at = _utc_now()
            if self.session_started_at is None:
                self.session_started_at = _utc_now()
            self._log(f"Session manifest written (simulated) -> {save_path}")


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
