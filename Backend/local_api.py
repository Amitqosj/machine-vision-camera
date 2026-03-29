"""Local FastAPI app for machine-vision dashboard APIs."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import load_config
from app.core.logging_config import setup_logging
from app.core.runtime_state import RuntimeState
from app.db.base import create_engine_and_session, initialize_database
from app.db.models import InspectionRecord
from app.db.repository import InspectionRepository
from app.services.image_storage_service import ImageStorageService
from app.services.inspection_service import InspectionService
from app.services.report_service import ReportService
from app.chamber.store import CAM_MACHINE, CAM_USB1, CAM_USB2, ChamberStore

MAX_QUERY_LIMIT = 250


class RoiUpdateRequest(BaseModel):
    """Payload for ROI updates from dashboard."""

    enabled: bool = True
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class BrowserFrameRequest(BaseModel):
    """Payload for browser-captured frame uploads."""

    image_base64: str


class ChamberPreviewBody(BaseModel):
    """Enable or disable preview for a chamber camera slot."""

    enabled: bool


class ChamberRecordingBody(BaseModel):
    """Start or stop recording flag for a camera slot."""

    recording: bool


class ChamberSessionSaveBody(BaseModel):
    """Persist session manifest (simulated until storage is wired)."""

    save_path: str = "D:\\ChamberRecordings"
    session_name: str | None = None
    batch_id: str | None = None


class ArduinoLightBody(BaseModel):
    on: bool


class ArduinoAutoLightBody(BaseModel):
    enabled: bool


class ArduinoRelayBody(BaseModel):
    channel: int = Field(ge=1, le=8)
    on: bool


class ArduinoSerialBody(BaseModel):
    com_port: str | None = None
    baud_rate: int | None = None


def _resolve_database_url(database_url: str, project_root: Path) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url
    sqlite_target = database_url.replace("sqlite:///", "", 1)
    if sqlite_target in {"", ":memory:"}:
        return database_url

    sqlite_path = Path(sqlite_target)
    if sqlite_path.is_absolute():
        return database_url
    absolute_path = (project_root / sqlite_path).resolve()
    return f"sqlite:///{absolute_path.as_posix()}"


def _safe_json(raw: str, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _serialize_record(record: InspectionRecord, include_image_url: bool = False) -> dict[str, Any]:
    payload = {
        "inspection_id": record.inspection_id,
        "frame_id": record.frame_id,
        "inspected_at": record.inspected_at.isoformat(),
        "passed": bool(record.passed),
        "confidence": float(record.confidence),
        "failure_reasons": _safe_json(record.failure_reasons_json, []),
        "measurements": _safe_json(record.measurements_json, {}),
        "roi": _safe_json(record.roi_json, []),
    }
    if include_image_url:
        payload["image_url"] = f"/api/images/{record.inspection_id}" if record.image_path else None
    return payload


def _encode_jpeg(frame: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".jpg", frame)
    if not success:
        raise ValueError("Failed to encode frame as JPEG.")
    return encoded.tobytes()


def _placeholder_frame(width: int, height: int) -> np.ndarray:
    frame = np.zeros((max(height, 120), max(width, 160), 3), dtype=np.uint8)
    cv2.putText(
        frame,
        "No frame available",
        (24, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (220, 220, 220),
        2,
        cv2.LINE_AA,
    )
    return frame


def _decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Unable to decode uploaded image.")
    return frame


def _decode_base64_image(image_base64: str) -> np.ndarray:
    payload = image_base64.strip()
    if not payload:
        raise ValueError("Uploaded frame is empty.")
    if payload.startswith("data:"):
        _, _, payload = payload.partition(",")
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Uploaded frame is not valid base64 image data.") from exc
    return _decode_image_bytes(raw)


def _coerce_limit(limit: int) -> int:
    return max(1, min(limit, MAX_QUERY_LIMIT))


CHAMBER_CAMERA_SLUGS = {
    "machine-vision": CAM_MACHINE,
    "usb-1": CAM_USB1,
    "usb-2": CAM_USB2,
}


def _usb_sim_mjpeg_frame(label: str, width: int = 640, height: int = 480) -> bytes:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        label,
        (24, height // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (200, 220, 240),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Simulated USB feed (OpenCV)",
        (24, height // 2 + 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (140, 160, 200),
        1,
        cv2.LINE_AA,
    )
    success, encoded = cv2.imencode(".jpg", frame)
    if not success:
        raise ValueError("USB placeholder encode failed")
    return encoded.tobytes()


def create_backend_app(config_path: Path, project_root: Path) -> FastAPI:
    """Create local FastAPI app with dashboard-compatible routes."""
    config = load_config(config_path)
    setup_logging(config.logging, project_root=project_root)
    logger = logging.getLogger("app")
    logger.info("Loaded configuration from %s", config_path)

    runtime_state = RuntimeState()
    db_url = _resolve_database_url(config.resolve_database_url(), project_root=project_root)
    db_engine, session_factory = create_engine_and_session(database_url=db_url, echo=config.database.echo)
    initialize_database(db_engine)

    repository = InspectionRepository(session_factory=session_factory, logger=logger)
    image_storage = ImageStorageService(
        storage_config=config.storage,
        inspection_config=config.inspection,
        project_root=project_root,
        logger=logger,
    )
    report_service = ReportService(repository=repository, image_storage=image_storage, logger=logger)
    inspection_service = InspectionService(
        config=config,
        repository=repository,
        image_storage=image_storage,
        runtime_state=runtime_state,
        logger=logger,
    )
    chamber_store = ChamberStore()

    app = FastAPI(title="Machine Vision Inspection API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("shutdown")
    def _shutdown() -> None:
        inspection_service.stop()

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Machine Vision backend is running", "docs": "/docs"}

    @app.get("/health")
    def health() -> dict[str, Any]:
        snapshot = runtime_state.snapshot()
        return {
            "status": "ok",
            "running": snapshot["running"],
            "camera_connected": snapshot["camera_connected"],
        }

    @app.get("/api/health")
    def api_health() -> dict[str, Any]:
        return health()

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        return config.model_dump(mode="python")

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        runtime_snapshot = runtime_state.snapshot()
        return {
            "runtime": runtime_snapshot,
            "database": repository.get_counters(),
            "latest_result": runtime_snapshot.get("last_result", {}),
        }

    @app.get("/api/results/recent")
    def get_recent_results(limit: int = 25) -> list[dict[str, Any]]:
        rows = repository.get_recent(limit=_coerce_limit(limit))
        return [_serialize_record(row, include_image_url=False) for row in rows]

    @app.get("/api/failures/recent")
    def get_recent_failures(limit: int = 10) -> list[dict[str, Any]]:
        rows = repository.get_recent_failures(limit=_coerce_limit(limit))
        return [_serialize_record(row, include_image_url=True) for row in rows]

    @app.post("/api/control/start")
    def start_inspection() -> dict[str, str]:
        try:
            inspection_service.start()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to start inspection service: %s", exc)
            raise HTTPException(status_code=500, detail=f"Unable to start inspection: {exc}") from exc
        return {"message": "Inspection started."}

    @app.post("/api/control/stop")
    def stop_inspection() -> dict[str, str]:
        inspection_service.stop()
        return {"message": "Inspection stopped."}

    @app.post("/api/browser/stop")
    def stop_browser_camera_mode() -> dict[str, str]:
        inspection_service.stop_browser_camera_mode()
        return {"message": "Browser camera mode stopped."}

    @app.post("/api/control/reset-counters")
    def reset_counters() -> dict[str, str]:
        inspection_service.reset_counters()
        return {"message": "Runtime counters reset."}

    @app.post("/api/control/capture-snapshot")
    def capture_snapshot() -> dict[str, str]:
        snapshot_path = inspection_service.capture_snapshot()
        if snapshot_path is None:
            raise HTTPException(
                status_code=409,
                detail="No frame available yet. Start inspection before capturing a snapshot.",
            )
        return {"message": "Snapshot captured.", "path": str(snapshot_path)}

    @app.post("/api/control/export-csv")
    def export_csv() -> dict[str, str]:
        csv_path = report_service.export_csv()
        return {"message": "CSV exported.", "path": str(csv_path)}

    @app.post("/api/control/save-config")
    def save_config() -> dict[str, str]:
        inspection_service.save_current_config(config_path)
        return {"message": "Config saved."}

    @app.post("/api/roi")
    def update_roi(payload: RoiUpdateRequest) -> dict[str, str]:
        inspection_service.update_roi(
            x=payload.x,
            y=payload.y,
            width=payload.width,
            height=payload.height,
            enabled=payload.enabled,
        )
        return {"message": "ROI updated."}

    @app.post("/api/browser/process-frame")
    def process_browser_frame(payload: BrowserFrameRequest) -> dict[str, Any]:
        try:
            decoded = _decode_base64_image(payload.image_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            result = inspection_service.process_uploaded_frame(decoded)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to process browser frame: %s", exc)
            raise HTTPException(
                status_code=500,
                detail=f"Unable to process uploaded frame: {exc}",
            ) from exc

        return {"message": "Frame processed.", "result": result.as_dict()}

    @app.get("/api/frame.jpg")
    def get_frame() -> Response:
        frame = inspection_service.get_latest_frame()
        if frame is None:
            frame = _placeholder_frame(config.camera.width, config.camera.height)
        try:
            jpeg = _encode_jpeg(frame)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return Response(content=jpeg, media_type="image/jpeg")

    @app.get("/api/stream.mjpg")
    def stream_mjpg() -> StreamingResponse:
        frame_delay = 1.0 / max(config.camera.fps, 1)

        def frame_generator():
            while True:
                frame = inspection_service.get_latest_frame()
                if frame is None:
                    frame = _placeholder_frame(config.camera.width, config.camera.height)
                try:
                    encoded = _encode_jpeg(frame)
                except ValueError:
                    time.sleep(frame_delay)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n\r\n" + encoded + b"\r\n"
                )
                time.sleep(frame_delay)

        return StreamingResponse(
            frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    def _chamber_public() -> dict[str, Any]:
        snap = runtime_state.snapshot()
        return chamber_store.to_public_dict(
            config,
            snap["running"],
            snap["camera_connected"],
        )

    @app.get("/api/chamber/status")
    def chamber_status() -> dict[str, Any]:
        return _chamber_public()

    def _usb_stream_response(cam_id: str, title_live: str, title_idle: str) -> StreamingResponse:
        delay = 1.0 / 15.0

        def frame_generator():
            while True:
                live = chamber_store.usb_preview_active(cam_id)
                label = title_live if live else title_idle
                try:
                    encoded = _usb_sim_mjpeg_frame(label)
                except ValueError:
                    time.sleep(delay)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n\r\n" + encoded + b"\r\n"
                )
                time.sleep(delay)

        return StreamingResponse(
            frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/chamber/stream/usb1")
    def chamber_stream_usb1() -> StreamingResponse:
        return _usb_stream_response(
            CAM_USB1,
            "USB Camera 1 — LIVE (simulated)",
            "USB1 — connect & start preview",
        )

    @app.get("/api/chamber/stream/usb2")
    def chamber_stream_usb2() -> StreamingResponse:
        return _usb_stream_response(
            CAM_USB2,
            "USB Camera 2 — LIVE (simulated)",
            "USB2 — connect & start preview",
        )

    @app.post("/api/chamber/cameras/{slug}/connect")
    def chamber_camera_connect(slug: str) -> dict[str, Any]:
        cam = CHAMBER_CAMERA_SLUGS.get(slug)
        if cam is None:
            raise HTTPException(status_code=404, detail="Unknown camera.")
        try:
            if cam == CAM_MACHINE:
                chamber_store.connect_machine_vision(config, logger)
            else:
                chamber_store.connect_usb(cam, logger)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Chamber connect failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": "Camera connected.", "chamber": _chamber_public()}

    @app.post("/api/chamber/cameras/{slug}/disconnect")
    def chamber_camera_disconnect(slug: str) -> dict[str, Any]:
        cam = CHAMBER_CAMERA_SLUGS.get(slug)
        if cam is None:
            raise HTTPException(status_code=404, detail="Unknown camera.")
        try:
            if cam == CAM_MACHINE:
                chamber_store.disconnect_machine_vision(inspection_service, logger)
            else:
                chamber_store.disconnect_usb(cam, logger)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Chamber disconnect failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": "Camera disconnected.", "chamber": _chamber_public()}

    @app.post("/api/chamber/cameras/{slug}/preview")
    def chamber_camera_preview(slug: str, body: ChamberPreviewBody) -> dict[str, Any]:
        cam = CHAMBER_CAMERA_SLUGS.get(slug)
        if cam is None:
            raise HTTPException(status_code=404, detail="Unknown camera.")
        try:
            if cam == CAM_MACHINE:
                chamber_store.set_preview_machine_vision(body.enabled, inspection_service, logger)
            else:
                chamber_store.set_preview_usb(cam, body.enabled, logger)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Chamber preview failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": "Preview updated.", "chamber": _chamber_public()}

    @app.post("/api/chamber/cameras/{slug}/capture")
    def chamber_camera_capture(slug: str) -> dict[str, Any]:
        cam = CHAMBER_CAMERA_SLUGS.get(slug)
        if cam is None:
            raise HTTPException(status_code=404, detail="Unknown camera.")
        try:
            if cam == CAM_MACHINE:
                snap_path = chamber_store.capture_machine_vision(inspection_service, logger)
                return {"message": "Snapshot captured.", "path": snap_path, "chamber": _chamber_public()}
            capture_id = chamber_store.capture_usb(cam, logger)
            return {"message": "Capture recorded (simulated).", "captureId": capture_id, "chamber": _chamber_public()}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Chamber capture failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/chamber/cameras/{slug}/recording")
    def chamber_camera_recording(slug: str, body: ChamberRecordingBody) -> dict[str, Any]:
        cam = CHAMBER_CAMERA_SLUGS.get(slug)
        if cam is None:
            raise HTTPException(status_code=404, detail="Unknown camera.")
        try:
            if cam == CAM_MACHINE:
                chamber_store.set_recording_machine_vision(body.recording, inspection_service, logger)
            else:
                chamber_store.set_recording_usb(cam, body.recording, logger)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Chamber recording failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": "Recording updated.", "chamber": _chamber_public()}

    @app.post("/api/chamber/session/save")
    def chamber_session_save(body: ChamberSessionSaveBody) -> dict[str, Any]:
        chamber_store.save_session(
            save_path=body.save_path,
            session_name=body.session_name,
            batch_id=body.batch_id,
        )
        return {"message": "Session saved.", "chamber": _chamber_public()}

    @app.post("/api/chamber/arduino/connect")
    def chamber_arduino_connect() -> dict[str, Any]:
        chamber_store.arduino_connect()
        return {"message": "Arduino connected.", "chamber": _chamber_public()}

    @app.post("/api/chamber/arduino/disconnect")
    def chamber_arduino_disconnect() -> dict[str, Any]:
        chamber_store.arduino_disconnect()
        return {"message": "Arduino disconnected.", "chamber": _chamber_public()}

    @app.patch("/api/chamber/arduino/serial")
    def chamber_arduino_serial(body: ArduinoSerialBody) -> dict[str, Any]:
        chamber_store.arduino_set_serial(body.com_port, body.baud_rate)
        return {"message": "Serial settings updated.", "chamber": _chamber_public()}

    @app.post("/api/chamber/arduino/light")
    def chamber_arduino_light(body: ArduinoLightBody) -> dict[str, Any]:
        try:
            chamber_store.arduino_light(body.on)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"message": "Light updated.", "chamber": _chamber_public()}

    @app.post("/api/chamber/arduino/auto-light")
    def chamber_arduino_auto_light(body: ArduinoAutoLightBody) -> dict[str, Any]:
        chamber_store.set_auto_light_enabled(body.enabled)
        return {"message": "Auto light updated.", "chamber": _chamber_public()}

    @app.post("/api/chamber/arduino/trigger")
    def chamber_arduino_trigger() -> dict[str, Any]:
        chamber_store.arduino_trigger()
        return {"message": "Trigger sent.", "chamber": _chamber_public()}

    @app.post("/api/chamber/arduino/relay")
    def chamber_arduino_relay(body: ArduinoRelayBody) -> dict[str, Any]:
        chamber_store.arduino_relay(body.channel, body.on)
        return {"message": "Relay command logged.", "chamber": _chamber_public()}

    @app.get("/api/images/{inspection_id}")
    def get_image(inspection_id: str) -> FileResponse:
        record = repository.get_by_inspection_id(inspection_id)
        if record is None or not record.image_path:
            raise HTTPException(status_code=404, detail="Image not found for inspection.")

        image_path = Path(record.image_path)
        if not image_path.is_absolute():
            image_path = (project_root / image_path).resolve()
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Stored image file is missing.")
        return FileResponse(path=image_path, media_type="image/jpeg", filename=image_path.name)

    return app
