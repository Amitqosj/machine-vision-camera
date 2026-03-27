"""Thread-safe runtime state shared by UI/API/services."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class RuntimeState:
    """Shared process state for telemetry and status reporting."""

    running: bool = False
    camera_connected: bool = False
    total_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    last_result: dict[str, Any] = field(default_factory=dict)
    last_error: str = ""
    recent_failed_images: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def set_running(self, running: bool) -> None:
        with self._lock:
            self.running = running

    def set_camera_connected(self, connected: bool) -> None:
        with self._lock:
            self.camera_connected = connected

    def increment_counter(self, passed: bool) -> None:
        with self._lock:
            self.total_count += 1
            if passed:
                self.pass_count += 1
            else:
                self.fail_count += 1

    def reset_counters(self) -> None:
        with self._lock:
            self.total_count = 0
            self.pass_count = 0
            self.fail_count = 0

    def set_last_result(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.last_result = payload

    def set_last_error(self, message: str) -> None:
        with self._lock:
            self.last_error = message

    def set_recent_failed_images(self, image_paths: list[str]) -> None:
        with self._lock:
            self.recent_failed_images = image_paths

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "camera_connected": self.camera_connected,
                "total_count": self.total_count,
                "pass_count": self.pass_count,
                "fail_count": self.fail_count,
                "last_result": dict(self.last_result),
                "last_error": self.last_error,
                "recent_failed_images": list(self.recent_failed_images),
            }

