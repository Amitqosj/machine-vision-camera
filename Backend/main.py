"""Web backend for machine vision system (FastAPI)."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
import json
import logging
import os
import sys
import time
from pathlib import Path
from threading import Event, RLock
from typing import Any

import cv2
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import load_config
from app.core.logging_config import setup_logging
from app.core.runtime_state import RuntimeState
from app.db.base import create_engine_and_session, initialize_database
from app.db.models import InspectionRecord
from app.db.repository import InspectionRepository
from app.inspection.models import FramePacket, InspectionResult
from app.services.image_storage_service import ImageStorageService
from app.services.inspection_service import InspectionService
from app.services.report_service import ReportService


class RoiUpdateRequest(BaseModel):
    """ROI update payload from web client."""

    enabled: bool = True
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class BackendRuntime:
    """Owns backend service dependencies and runtime callbacks."""

    def __init__(self, config_path: Path) -> None:
        self.project_root = PROJECT_ROOT
        self.config_path = config_path
        load_dotenv(self.project_root / ".env")
        self.config = load_config(self.config_path)
        setup_logging(self.config.logging, project_root=self.project_root)
        self.logger = logging.getLogger("app")
        self.logger.info("Backend loaded configuration from %s", self.config_path)

        self.runtime_state = RuntimeState()
        db_engine, session_factory = create_engine_and_session(
            database_url=self.config.resolve_database_url(),
            echo=self.config.database.echo,
        )
        initialize_database(db_engine)
        self.repository = InspectionRepository(session_factory=session_factory, logger=self.logger)
        self.image_storage = ImageStorageService(
            storage_config=self.config.storage,
            inspection_config=self.config.inspection,
            project_root=self.project_root,
            logger=self.logger,
        )
        self.report_service = ReportService(
            repository=self.repository,
            image_storage=self.image_storage,
            logger=self.logger,
        )
        self.inspection_service = InspectionService(
            config=self.config,
            repository=self.repository,
            image_storage=self.image_storage,
            runtime_state=self.runtime_state,
            logger=self.logger,
        )

        self._latest_frame = None
        self._latest_result: dict[str, Any] = {}
        self._frame_lock = RLock()
        self.shutdown_event = Event()

        self.inspection_service.set_callbacks(
            on_frame=self._on_frame,
            on_result=self._on_result,
            on_status=self._on_status,
            on_error=self._on_error,
        )

    def _on_frame(self, packet: FramePacket) -> None:
        with self._frame_lock:
            self._latest_frame = packet.frame.copy()

    def _on_result(self, result: InspectionResult) -> None:
        with self._frame_lock:
            annotated = result.annotated_frame if result.annotated_frame is not None else result.raw_frame
            if annotated is not None:
                self._latest_frame = annotated.copy()
            self._latest_result = result.as_dict()

    def _on_status(self, _: dict[str, Any]) -> None:
        # Runtime state is already updated in service; no extra action needed here.
        return

    def _on_error(self, message: str) -> None:
        self.logger.error("Inspection runtime error: %s", message)

    def get_latest_frame(self):
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def get_latest_result(self) -> dict[str, Any]:
        with self._frame_lock:
            return dict(self._latest_result)

    @staticmethod
    def _encode_jpeg(frame) -> bytes | None:
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return None
        return encoded.tobytes()

    def resolve_failure_image(self, inspection_id: str) -> Path | None:
        row = self.repository.get_by_inspection_id(inspection_id)
        if row is None or not row.image_path:
            return None

        image_path = Path(row.image_path)
        if not image_path.is_absolute():
            image_path = self.project_root / image_path
        image_path = image_path.resolve()

        base_dir = self.image_storage.base_dir.resolve()
        try:
            image_path.relative_to(base_dir)
        except ValueError:
            self.logger.warning("Rejected image access outside data directory: %s", image_path)
            return None
        if not image_path.exists():
            return None
        return image_path

    @staticmethod
    def serialize_record(row: InspectionRecord) -> dict[str, Any]:
        def parse_json(raw: str, fallback):
            try:
                return json.loads(raw) if raw else fallback
            except json.JSONDecodeError:
                return fallback

        return {
            "inspection_id": row.inspection_id,
            "frame_id": row.frame_id,
            "inspected_at": row.inspected_at.isoformat(),
            "passed": row.passed,
            "confidence": row.confidence,
            "measurements": parse_json(row.measurements_json, {}),
            "failure_reasons": parse_json(row.failure_reasons_json, []),
            "roi": parse_json(row.roi_json, []),
            "image_path": row.image_path,
        }


def _default_allowed_origins() -> list[str]:
    raw = os.getenv(
        "MVS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


def create_app(config_path: Path) -> FastAPI:
    """Create FastAPI backend app with inspection endpoints."""
    runtime = BackendRuntime(config_path=config_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            runtime.shutdown_event.set()
            runtime.inspection_service.stop()
            runtime.logger.info("Backend shutdown complete.")

    app = FastAPI(
        title="Machine Vision Backend API",
        version="2.0.0",
        description="Backend service for real-time machine vision with React frontend",
        lifespan=lifespan,
    )
    app.state.runtime = runtime

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_default_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        snapshot = runtime.runtime_state.snapshot()
        return {
            "status": "ok",
            "running": snapshot["running"],
            "camera_connected": snapshot["camera_connected"],
        }

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        cfg = runtime.inspection_service.config
        return {
            "camera": {
                "source": cfg.camera.source,
                "width": cfg.camera.width,
                "height": cfg.camera.height,
                "fps": cfg.camera.fps,
                "kind": cfg.camera.kind,
            },
            "inspection": {
                "roi": cfg.inspection.roi.model_dump(mode="python"),
                "save_fail_images": cfg.inspection.save_fail_images,
                "save_pass_images": cfg.inspection.save_pass_images,
            },
            "api": {
                "host": cfg.api.host,
                "port": cfg.api.port,
            },
        }

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return {
            "runtime": runtime.runtime_state.snapshot(),
            "database": runtime.repository.get_counters(),
            "latest_result": runtime.get_latest_result(),
        }

    @app.post("/api/control/start")
    def start_inspection() -> dict[str, str]:
        try:
            runtime.inspection_service.start()
            return {"message": "Inspection started."}
        except Exception as exc:  # pylint: disable=broad-except
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/control/stop")
    def stop_inspection() -> dict[str, str]:
        runtime.inspection_service.stop()
        return {"message": "Inspection stopped."}

    @app.post("/api/control/reset-counters")
    def reset_counters() -> dict[str, str]:
        runtime.inspection_service.reset_counters()
        return {"message": "Runtime counters reset."}

    @app.post("/api/control/capture-snapshot")
    def capture_snapshot() -> dict[str, Any]:
        path = runtime.inspection_service.capture_snapshot()
        if path is None:
            raise HTTPException(status_code=409, detail="No frame available to capture.")
        return {"message": "Snapshot captured.", "path": str(path)}

    @app.post("/api/control/export-csv")
    def export_csv() -> dict[str, Any]:
        path = runtime.report_service.export_csv()
        return {"message": "CSV report exported.", "path": str(path)}

    @app.post("/api/control/save-config")
    def save_config() -> dict[str, Any]:
        runtime.inspection_service.save_current_config(runtime.config_path)
        return {"message": "Configuration saved.", "path": str(runtime.config_path)}

    @app.post("/api/roi")
    def update_roi(payload: RoiUpdateRequest) -> dict[str, Any]:
        runtime.inspection_service.update_roi(
            x=payload.x,
            y=payload.y,
            width=payload.width,
            height=payload.height,
            enabled=payload.enabled,
        )
        return {"message": "ROI updated.", "roi": payload.model_dump(mode="python")}

    @app.get("/api/results/recent")
    def recent_results(limit: int = Query(default=25, ge=1, le=200)) -> list[dict[str, Any]]:
        rows = runtime.repository.get_recent(limit=limit)
        return [runtime.serialize_record(row) for row in rows]

    @app.get("/api/failures/recent")
    def recent_failures(limit: int = Query(default=10, ge=1, le=100)) -> list[dict[str, Any]]:
        rows = runtime.repository.get_recent_failures(limit=limit)
        payload: list[dict[str, Any]] = []
        for row in rows:
            item = runtime.serialize_record(row)
            item["image_url"] = f"/api/images/{row.inspection_id}" if row.image_path else None
            payload.append(item)
        return payload

    @app.get("/api/images/{inspection_id}")
    def get_failure_image(inspection_id: str):
        image_path = runtime.resolve_failure_image(inspection_id)
        if image_path is None:
            raise HTTPException(status_code=404, detail="Image not found.")
        return FileResponse(path=image_path, media_type="image/jpeg")

    @app.get("/api/frame.jpg")
    def latest_frame() -> Response:
        frame = runtime.get_latest_frame()
        if frame is None:
            raise HTTPException(status_code=404, detail="No frame available.")
        jpeg = runtime._encode_jpeg(frame)
        if jpeg is None:
            raise HTTPException(status_code=500, detail="Frame encoding failed.")
        return Response(content=jpeg, media_type="image/jpeg")

    @app.get("/api/stream.mjpg")
    def stream() -> StreamingResponse:
        def frame_generator():
            while not runtime.shutdown_event.is_set():
                frame = runtime.get_latest_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                jpeg = runtime._encode_jpeg(frame)
                if jpeg is None:
                    time.sleep(0.03)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                    + jpeg
                    + b"\r\n"
                )
                time.sleep(0.08)

        return StreamingResponse(
            frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    return app


def parse_args() -> argparse.Namespace:
    """Parse backend CLI arguments."""
    parser = argparse.ArgumentParser(description="Machine vision backend server")
    parser.add_argument(
        "--config",
        type=str,
        default="../config/config.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only)",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point for backend API server."""
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        cwd_candidate = (Path.cwd() / config_path).resolve()
        if cwd_candidate.exists():
            config_path = cwd_candidate
        else:
            config_path = (Path(__file__).resolve().parent / config_path).resolve()

    app = create_app(config_path=config_path)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

