"""Common image helper functions."""

from __future__ import annotations

from typing import Tuple

import numpy as np


def clamp_roi(
    roi: tuple[int, int, int, int], frame_shape: Tuple[int, int]
) -> tuple[int, int, int, int]:
    """Clamp ROI (x, y, w, h) to image bounds."""
    x, y, w, h = roi
    frame_h, frame_w = frame_shape
    x = min(max(0, x), frame_w - 1)
    y = min(max(0, y), frame_h - 1)
    w = min(max(1, w), frame_w - x)
    h = min(max(1, h), frame_h - y)
    return x, y, w, h


def ensure_uint8(image: np.ndarray) -> np.ndarray:
    """Convert image data to uint8 when needed."""
    if image.dtype == np.uint8:
        return image
    clipped = np.clip(image, 0, 255)
    return clipped.astype(np.uint8)

