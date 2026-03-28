"""Local FastAPI app for machine-vision dashboard APIs."""

from __future__ import annotations

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

MAX_QUERY_LIMIT = 250


class RoiUpdateRequest(BaseModel):
    """Payload for ROI updates from dashboard."""

    enabled: bool = True
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


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


def _coerce_limit(limit: int) -> int:
    return max(1, min(limit, MAX_QUERY_LIMIT))


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
