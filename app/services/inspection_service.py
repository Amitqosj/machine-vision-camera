"""Application orchestration service connecting camera, pipeline, DB, and storage."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np

from app.camera.base import BaseCamera
from app.camera.factory import create_camera, create_simulated_camera
from app.core.config import AppConfig, RoiConfig, save_config
from app.core.exceptions import PipelineError
from app.core.runtime_state import RuntimeState
from app.db.repository import InspectionRepository
from app.inspection.engine import InspectionEngine
from app.inspection.models import FramePacket, InspectionResult
from app.pipeline.frame_pipeline import RealTimePipeline
from app.services.image_storage_service import ImageStorageService


class InspectionService:
    """High-level service consumed by UI and API layers."""

    def __init__(
        self,
        config: AppConfig,
        repository: InspectionRepository,
        image_storage: ImageStorageService,
        runtime_state: RuntimeState,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._image_storage = image_storage
        self._runtime_state = runtime_state
        self._logger = logger or logging.getLogger("app")
        self._camera_logger = logging.getLogger("camera")
        self._inspection_logger = logging.getLogger("inspection")

        self._engine = InspectionEngine(config.inspection, logger=self._inspection_logger)
        self._camera: BaseCamera = create_camera(config.camera, logger=self._camera_logger)
        self._pipeline: RealTimePipeline | None = None
        self._latest_frame: np.ndarray | None = None
        self._lock = RLock()

        self._on_frame_callback: Callable[[FramePacket], None] | None = None
        self._on_result_callback: Callable[[InspectionResult], None] | None = None
        self._on_status_callback: Callable[[dict[str, Any]], None] | None = None
        self._on_error_callback: Callable[[str], None] | None = None

    def set_callbacks(
        self,
        on_frame: Callable[[FramePacket], None] | None = None,
        on_result: Callable[[InspectionResult], None] | None = None,
        on_status: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Register callbacks for UI/state updates."""
        self._on_frame_callback = on_frame
        self._on_result_callback = on_result
        self._on_status_callback = on_status
        self._on_error_callback = on_error

    def _ensure_pipeline(self) -> None:
        self._pipeline = RealTimePipeline(
            camera=self._camera,
            inspection_engine=self._engine,
            config=self._config.pipeline,
            on_frame=self._handle_frame,
            on_result=self._handle_result,
            on_camera_state=self._handle_camera_state,
            on_error=self._handle_error,
            logger=self._logger,
        )

    def start(self) -> None:
        """Start capture and processing runtime."""
        with self._lock:
            if self._pipeline is not None and self._pipeline.is_running():
                return
            self._ensure_pipeline()

        try:
            self._pipeline.start()
            self._runtime_state.set_running(True)
            self._publish_status()
            self._logger.info("Inspection service started.")
        except PipelineError as exc:
            self._logger.exception("Primary camera failed to start: %s", exc)
            if self._config.camera.simulate_on_failure and self._config.camera.kind == "webcam":
                self._logger.warning(
                    "Falling back to simulated camera because hardware is unavailable."
                )
                self._camera = create_simulated_camera(
                    self._config.camera, logger=self._camera_logger
                )
                self._ensure_pipeline()
                self._pipeline.start()
                self._runtime_state.set_running(True)
                self._publish_status()
            else:
                self._handle_error(str(exc))
                raise

    def stop(self) -> None:
        """Stop capture and processing runtime."""
        with self._lock:
            if self._pipeline is not None:
                self._pipeline.stop()
            self._runtime_state.set_running(False)
            self._runtime_state.set_camera_connected(False)
            self._publish_status()
            self._logger.info("Inspection service stopped.")

    def _handle_frame(self, packet: FramePacket) -> None:
        with self._lock:
            self._latest_frame = packet.frame.copy()
        if self._on_frame_callback is not None:
            self._on_frame_callback(packet)

    def _handle_result(self, result: InspectionResult) -> None:
        image_path = self._image_storage.save_inspection_image(result)
        self._repository.save_result(result, image_path=image_path)
        self._runtime_state.increment_counter(result.passed)
        self._runtime_state.set_last_result(result.as_dict())

        recent_failed = self._image_storage.list_recent_failed_images(
            self._config.ui.max_recent_failed
        )
        self._runtime_state.set_recent_failed_images(recent_failed)
        self._publish_status()

        if self._on_result_callback is not None:
            self._on_result_callback(result)

    def _handle_camera_state(self, connected: bool) -> None:
        self._runtime_state.set_camera_connected(connected)
        self._publish_status()

    def _handle_error(self, message: str) -> None:
        self._runtime_state.set_last_error(message)
        logging.getLogger("error").error(message)
        if self._on_error_callback is not None:
            self._on_error_callback(message)
        self._publish_status()

    def _publish_status(self) -> None:
        if self._on_status_callback is not None:
            self._on_status_callback(self._runtime_state.snapshot())

    def get_latest_frame(self) -> np.ndarray | None:
        """Return latest captured frame."""
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def capture_snapshot(self) -> Path | None:
        """Save a manual snapshot image from latest frame."""
        frame = self.get_latest_frame()
        if frame is None:
            self._handle_error("Snapshot requested but no frame is available.")
            return None
        path = self._image_storage.save_snapshot(frame)
        self._logger.info("Snapshot saved to %s", path)
        return path

    def update_roi(self, x: int, y: int, width: int, height: int, enabled: bool = True) -> None:
        """Update ROI in both runtime engine and in-memory config."""
        roi = RoiConfig(enabled=enabled, x=x, y=y, width=width, height=height)
        self._config.inspection.roi = roi
        self._engine.update_roi(roi)

    def reset_counters(self) -> None:
        """Reset runtime counters shown on dashboard."""
        self._runtime_state.reset_counters()
        self._publish_status()

    def save_current_config(self, config_path: Path) -> None:
        """Persist current in-memory configuration to YAML."""
        save_config(self._config, config_path)
        self._logger.info("Configuration saved to %s", config_path)

    @property
    def config(self) -> AppConfig:
        """Expose current application config."""
        return self._config

