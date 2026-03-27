"""Placeholder for future industrial camera SDK integration."""

from __future__ import annotations

from app.camera.base import BaseCamera


class IndustrialCameraStub(BaseCamera):
    """Integration point for SDKs such as pypylon, Spinnaker, or vendor APIs."""

    def start(self) -> None:  # pragma: no cover - intentionally unimplemented
        raise NotImplementedError("Industrial camera SDK integration not configured.")

    def stop(self) -> None:  # pragma: no cover - intentionally unimplemented
        raise NotImplementedError("Industrial camera SDK integration not configured.")

    def read(self) -> tuple[bool, None, float]:  # pragma: no cover
        raise NotImplementedError("Industrial camera SDK integration not configured.")

    def is_opened(self) -> bool:  # pragma: no cover
        return False

