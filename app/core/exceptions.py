"""Custom exceptions used across the application."""


class CameraError(RuntimeError):
    """Raised when camera operations fail."""


class PipelineError(RuntimeError):
    """Raised when pipeline operations fail."""

