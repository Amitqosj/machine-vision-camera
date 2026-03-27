"""Factory for camera provider creation."""

from __future__ import annotations

import logging

from app.camera.base import BaseCamera
from app.camera.simulated_camera import SimulatedCamera
from app.camera.webcam_camera import WebcamCamera
from app.core.config import CameraConfig


def create_camera(config: CameraConfig, logger: logging.Logger | None = None) -> BaseCamera:
    """Create a camera provider from configuration."""
    if config.kind == "simulated":
        return SimulatedCamera(config=config, logger=logger)
    return WebcamCamera(config=config, logger=logger)


def create_simulated_camera(
    config: CameraConfig, logger: logging.Logger | None = None
) -> BaseCamera:
    """Create a simulated camera provider using existing capture settings."""
    simulated_config = config.model_copy(update={"kind": "simulated"})
    return SimulatedCamera(config=simulated_config, logger=logger)

