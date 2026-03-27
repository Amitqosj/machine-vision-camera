"""Camera abstraction used by real-time frame pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseCamera(ABC):
    """Abstract camera interface for different hardware providers."""

    @abstractmethod
    def start(self) -> None:
        """Start camera connection or stream."""

    @abstractmethod
    def stop(self) -> None:
        """Stop camera connection or stream."""

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None, float]:
        """Read one frame and return (ok, frame, timestamp)."""

    @abstractmethod
    def is_opened(self) -> bool:
        """Return True when camera stream is available."""

