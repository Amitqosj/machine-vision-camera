"""Producer-consumer real-time capture and inspection pipeline."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

from app.camera.base import BaseCamera
from app.core.config import PipelineConfig
from app.core.exceptions import PipelineError
from app.inspection.engine import InspectionEngine
from app.inspection.models import FramePacket, InspectionResult


class RealTimePipeline:
    """Capture thread + processing thread with queue backpressure handling."""

    def __init__(
        self,
        camera: BaseCamera,
        inspection_engine: InspectionEngine,
        config: PipelineConfig,
        on_frame: Callable[[FramePacket], None] | None = None,
        on_result: Callable[[InspectionResult], None] | None = None,
        on_camera_state: Callable[[bool], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._camera = camera
        self._engine = inspection_engine
        self._config = config
        self._on_frame = on_frame
        self._on_result = on_result
        self._on_camera_state = on_camera_state
        self._on_error = on_error
        self._logger = logger or logging.getLogger("app")

        self._queue: queue.Queue[FramePacket] = queue.Queue(
            maxsize=self._config.capture_queue_size
        )
        self._stop_event = threading.Event()
        self._capture_thread: threading.Thread | None = None
        self._process_thread: threading.Thread | None = None
        self._frame_id = 0
        self._running = False
        self._state_lock = threading.RLock()

    def is_running(self) -> bool:
        with self._state_lock:
            return self._running

    def start(self) -> None:
        with self._state_lock:
            if self._running:
                return
            self._stop_event.clear()
            self._frame_id = 0
            try:
                self._camera.start()
            except Exception as exc:  # pylint: disable=broad-except
                raise PipelineError(f"Unable to start camera: {exc}") from exc

            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                name="capture-thread",
                daemon=True,
            )
            self._process_thread = threading.Thread(
                target=self._process_loop,
                name="process-thread",
                daemon=True,
            )
            self._capture_thread.start()
            self._process_thread.start()
            self._running = True
            self._logger.info("Real-time pipeline started.")

    def stop(self) -> None:
        with self._state_lock:
            if not self._running:
                return
            self._stop_event.set()

        if self._capture_thread is not None:
            self._capture_thread.join(timeout=2.0)
        if self._process_thread is not None:
            self._process_thread.join(timeout=2.0)

        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        self._camera.stop()
        with self._state_lock:
            self._running = False
        self._logger.info("Real-time pipeline stopped.")

    def _emit_error(self, message: str) -> None:
        self._logger.error(message)
        if self._on_error is not None:
            self._on_error(message)

    def _push_frame_packet(self, packet: FramePacket) -> None:
        if not self._queue.full():
            self._queue.put_nowait(packet)
            return

        if self._config.drop_policy == "drop_oldest":
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put_nowait(packet)
        else:
            # drop_newest policy: keep queue contents and ignore incoming frame.
            self._logger.debug("Frame dropped due to full queue and drop_newest policy.")

    def _capture_loop(self) -> None:
        was_connected = False
        while not self._stop_event.is_set():
            ok, frame, timestamp = self._camera.read()
            connected = bool(ok and frame is not None and self._camera.is_opened())
            if connected != was_connected and self._on_camera_state is not None:
                self._on_camera_state(connected)
            was_connected = connected

            if not ok or frame is None:
                time.sleep(0.02)
                continue

            packet = FramePacket(frame_id=self._frame_id, timestamp=timestamp, frame=frame)
            self._frame_id += 1

            if self._on_frame is not None:
                self._on_frame(packet)

            try:
                self._push_frame_packet(packet)
            except Exception as exc:  # pylint: disable=broad-except
                self._emit_error(f"Capture queue error: {exc}")

        if self._on_camera_state is not None:
            self._on_camera_state(False)

    def _process_loop(self) -> None:
        min_cycle = 1.0 / max(self._config.max_processing_fps, 1)
        while not self._stop_event.is_set():
            cycle_start = time.perf_counter()
            try:
                packet = self._queue.get(timeout=self._config.processing_poll_timeout_seconds)
            except queue.Empty:
                continue
            except Exception as exc:  # pylint: disable=broad-except
                self._emit_error(f"Processing queue error: {exc}")
                continue

            try:
                result = self._engine.inspect(packet)
                if self._on_result is not None:
                    self._on_result(result)
            except Exception as exc:  # pylint: disable=broad-except
                self._emit_error(f"Inspection processing failed: {exc}")

            elapsed = time.perf_counter() - cycle_start
            sleep_time = min_cycle - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

