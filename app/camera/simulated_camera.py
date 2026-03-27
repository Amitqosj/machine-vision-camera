"""Synthetic camera source used when hardware is unavailable."""

from __future__ import annotations

import logging
import time
from threading import RLock

import cv2
import numpy as np

from app.camera.base import BaseCamera
from app.core.config import CameraConfig


class SimulatedCamera(BaseCamera):
    """Generate synthetic frames to keep the full pipeline testable."""

    def __init__(self, config: CameraConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger("camera")
        self._running = False
        self._lock = RLock()
        self._frame_index = 0
        self._last_frame_ts = 0.0

    def start(self) -> None:
        with self._lock:
            self._running = True
            self._frame_index = 0
            self._last_frame_ts = 0.0
            self._logger.warning("Using simulated camera stream.")

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._logger.info("Simulated camera stopped.")

    def _throttle(self) -> None:
        frame_interval = 1.0 / max(self._config.fps, 1)
        now = time.time()
        wait = frame_interval - (now - self._last_frame_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_frame_ts = time.time()

    def _generate_frame(self) -> np.ndarray:
        frame = np.zeros((self._config.height, self._config.width, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)

        center_x = int(self._config.width * 0.5 + 60 * np.sin(self._frame_index * 0.05))
        center_y = int(self._config.height * 0.5 + 30 * np.cos(self._frame_index * 0.08))
        w, h = 260, 180

        top_left = (max(0, center_x - w // 2), max(0, center_y - h // 2))
        bottom_right = (
            min(self._config.width - 1, center_x + w // 2),
            min(self._config.height - 1, center_y + h // 2),
        )
        cv2.rectangle(frame, top_left, bottom_right, (220, 220, 220), -1)

        # Inject occasional synthetic defect every 30th frame.
        if self._frame_index % 30 == 0:
            cv2.circle(frame, (center_x, center_y), 30, (0, 0, 0), -1)

        cv2.putText(
            frame,
            "SIMULATED FEED",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        self._frame_index += 1
        return frame

    def read(self) -> tuple[bool, np.ndarray | None, float]:
        with self._lock:
            timestamp = time.time()
            if not self._running:
                return False, None, timestamp
        self._throttle()
        frame = self._generate_frame()
        return True, frame, time.time()

    def is_opened(self) -> bool:
        with self._lock:
            return self._running

