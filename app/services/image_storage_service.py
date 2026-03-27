"""Filesystem image persistence for inspection outputs."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.core.config import InspectionConfig, StorageConfig
from app.inspection.models import InspectionResult


class ImageStorageService:
    """Manage structured image folders and save inspection images."""

    def __init__(
        self,
        storage_config: StorageConfig,
        inspection_config: InspectionConfig,
        project_root: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        self._storage_config = storage_config
        self._inspection_config = inspection_config
        self._project_root = project_root
        self._logger = logger or logging.getLogger("app")

        base_dir = Path(storage_config.base_dir)
        self._base_dir = base_dir if base_dir.is_absolute() else project_root / base_dir
        self._failed_dir = self._base_dir / storage_config.failed_dir_name
        self._passed_dir = self._base_dir / storage_config.passed_dir_name
        self._raw_dir = self._base_dir / storage_config.raw_dir_name
        self._snapshot_dir = self._base_dir / storage_config.snapshots_dir_name
        self._exports_dir = self._base_dir / storage_config.exports_dir_name
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        for folder in [
            self._base_dir,
            self._failed_dir,
            self._passed_dir,
            self._raw_dir,
            self._snapshot_dir,
            self._exports_dir,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def _get_target_dir(self, is_fail: bool) -> Path:
        root = self._failed_dir if is_fail else self._passed_dir
        if not self._storage_config.daily_rotation:
            root.mkdir(parents=True, exist_ok=True)
            return root
        date_folder = datetime.now().strftime("%Y-%m-%d")
        target = root / date_folder
        target.mkdir(parents=True, exist_ok=True)
        return target

    def save_inspection_image(self, result: InspectionResult) -> str | None:
        """Save annotated frame for pass/fail based on config."""
        should_save = (
            (not result.passed and self._inspection_config.save_fail_images)
            or (result.passed and self._inspection_config.save_pass_images)
        )
        if not should_save:
            return None

        frame = result.annotated_frame if result.annotated_frame is not None else result.raw_frame
        if frame is None:
            self._logger.warning("No frame available to save for inspection %s", result.inspection_id)
            return None

        target_dir = self._get_target_dir(is_fail=not result.passed)
        stamp = datetime.fromtimestamp(result.timestamp).strftime("%Y%m%d_%H%M%S_%f")
        decision = "FAIL" if not result.passed else "PASS"
        file_name = f"{stamp}_{result.inspection_id}_{decision}.jpg"
        file_path = target_dir / file_name
        saved = cv2.imwrite(str(file_path), frame)
        if not saved:
            self._logger.error("Failed to write image to %s", file_path)
            return None
        return str(file_path)

    def save_snapshot(self, frame: np.ndarray) -> Path:
        """Save user-triggered snapshot."""
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self._snapshot_dir / f"snapshot_{stamp}.jpg"
        cv2.imwrite(str(path), frame)
        return path

    def list_recent_failed_images(self, limit: int = 8) -> list[str]:
        """Return latest failed image file paths."""
        if not self._failed_dir.exists():
            return []
        files = [f for f in self._failed_dir.rglob("*.jpg") if f.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(path) for path in files[: max(1, limit)]]

    @property
    def exports_dir(self) -> Path:
        """Directory used for CSV/report exports."""
        self._exports_dir.mkdir(parents=True, exist_ok=True)
        return self._exports_dir

    @property
    def base_dir(self) -> Path:
        """Base directory where inspection artifacts are written."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        return self._base_dir

