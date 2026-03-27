"""USB/webcam camera provider implementation."""

from __future__ import annotations

import logging
import time
from threading import RLock

import cv2
import numpy as np

from app.camera.base import BaseCamera
from app.core.config import CameraConfig
from app.core.exceptions import CameraError


class WebcamCamera(BaseCamera):
    """OpenCV-based webcam implementation with reconnect support."""

    def __init__(self, config: CameraConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger("camera")
        self._capture: cv2.VideoCapture | None = None
        self._running = False
        self._lock = RLock()
        self._last_reconnect_attempt = 0.0

    def _parse_source(self) -> int | str:
        if isinstance(self._config.source, int):
            return self._config.source
        source_text = str(self._config.source).strip()
        return int(source_text) if source_text.isdigit() else source_text

    def _configure_capture(self, capture: cv2.VideoCapture) -> None:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)
        capture.set(cv2.CAP_PROP_FPS, self._config.fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _open_capture(self) -> bool:
        source = self._parse_source()
        capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            capture.release()
            return False
        self._configure_capture(capture)
        self._capture = capture
        return True

    def _open_capture_with_timeout(self) -> bool:
        deadline = time.time() + self._config.open_timeout_seconds
        while time.time() <= deadline:
            if self._open_capture():
                return True
            time.sleep(0.25)
        return False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            if not self._open_capture_with_timeout():
                self._running = False
                raise CameraError("Unable to open webcam source.")
            self._logger.info("Webcam started successfully.")

    def stop(self) -> None:
        with self._lock:
            self._running = False
            if self._capture is not None:
                self._capture.release()
                self._capture = None
            self._logger.info("Webcam stopped.")

    def _reconnect_if_needed(self) -> bool:
        now = time.time()
        if now - self._last_reconnect_attempt < self._config.reconnect_interval_seconds:
            return False
        self._last_reconnect_attempt = now
        self._logger.warning("Camera stream lost. Attempting reconnect...")
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        reconnected = self._open_capture()
        if reconnected:
            self._logger.info("Camera reconnect succeeded.")
        else:
            self._logger.error("Camera reconnect failed.")
        return reconnected

    def read(self) -> tuple[bool, np.ndarray | None, float]:
        with self._lock:
            timestamp = time.time()
            if not self._running:
                return False, None, timestamp

            if self._capture is None or not self._capture.isOpened():
                self._reconnect_if_needed()
                if self._capture is None:
                    return False, None, timestamp

            ok, frame = self._capture.read()
            if not ok or frame is None:
                self._logger.warning("Failed to grab frame from webcam.")
                self._reconnect_if_needed()
                return False, None, timestamp
            return True, frame, timestamp

    def is_opened(self) -> bool:
        with self._lock:
            return bool(self._capture and self._capture.isOpened() and self._running)

