"""Application configuration models and YAML loading helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class CameraConfig(BaseModel):
    """Camera source and capture settings."""

    kind: Literal["webcam", "simulated"] = "webcam"
    source: int | str = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    reconnect_interval_seconds: float = 2.0
    open_timeout_seconds: float = 5.0
    simulate_on_failure: bool = True

    @field_validator("width", "height", "fps")
    @classmethod
    def must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be positive.")
        return value


class PipelineConfig(BaseModel):
    """Real-time producer/consumer pipeline configuration."""

    capture_queue_size: int = 4
    processing_poll_timeout_seconds: float = 0.25
    drop_policy: Literal["drop_oldest", "drop_newest"] = "drop_oldest"
    max_processing_fps: int = 30

    @field_validator("capture_queue_size", "max_processing_fps")
    @classmethod
    def positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be positive.")
        return value


class RoiConfig(BaseModel):
    """Region of interest for inspection."""

    enabled: bool = False
    x: int = 100
    y: int = 100
    width: int = 400
    height: int = 300

    @field_validator("x", "y", "width", "height")
    @classmethod
    def non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("ROI values cannot be negative.")
        return value


class StrategyConfig(BaseModel):
    """Per-inspection strategy configuration."""

    type: str
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class InspectionConfig(BaseModel):
    """Configuration for defect detection and decision logic."""

    roi: RoiConfig = Field(default_factory=RoiConfig)
    save_fail_images: bool = True
    save_pass_images: bool = False
    annotation_enabled: bool = True
    strategies: list[StrategyConfig] = Field(
        default_factory=lambda: [
            StrategyConfig(
                type="presence",
                params={"min_non_zero_ratio": 0.005, "min_mean_intensity": 20.0},
            ),
            StrategyConfig(
                type="contour_count",
                params={
                    "threshold_value": 100,
                    "min_contours": 1,
                    "min_contour_area": 250.0,
                },
            ),
            StrategyConfig(
                type="defect_threshold",
                params={
                    "threshold_value": 80,
                    "object_threshold_value": 100,
                    "mode": "dark",
                    "max_defect_ratio": 0.08,
                },
            ),
            StrategyConfig(
                type="area_range",
                params={
                    "threshold_value": 100,
                    "min_area": 5000.0,
                    "max_area": 150000.0,
                },
            ),
            StrategyConfig(
                type="alignment",
                params={
                    "threshold_value": 100,
                    "expected_x_pct": 0.5,
                    "expected_y_pct": 0.5,
                    "tolerance_px": 80.0,
                },
            ),
        ]
    )


class StorageConfig(BaseModel):
    """Filesystem layout and image saving behavior."""

    base_dir: str = "data"
    failed_dir_name: str = "failed"
    passed_dir_name: str = "passed"
    snapshots_dir_name: str = "snapshots"
    exports_dir_name: str = "exports"
    raw_dir_name: str = "images"
    daily_rotation: bool = True


class DatabaseConfig(BaseModel):
    """Database backend settings."""

    url: str = "sqlite:///data/inspection.db"
    echo: bool = False


class LoggingConfig(BaseModel):
    """Logger setup and rotating file handler configuration."""

    level: str = "INFO"
    log_dir: str = "data/logs"
    max_bytes: int = 5_000_000
    backup_count: int = 5
    format: str = (
        "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    )


class UiConfig(BaseModel):
    """Desktop UI settings."""

    window_title: str = "Machine Vision Inspection System"
    preview_width: int = 960
    preview_height: int = 540
    max_recent_failed: int = 8
    ui_refresh_ms: int = 100


class ApiConfig(BaseModel):
    """Optional local API server settings."""

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8000


class AppConfig(BaseModel):
    """Top-level config root for the full application."""

    camera: CameraConfig = Field(default_factory=CameraConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    inspection: InspectionConfig = Field(default_factory=InspectionConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)

    def resolve_database_url(self) -> str:
        """Return DB URL with environment override support."""
        return os.getenv("MVS_DATABASE_URL", self.database.url)


def load_config(config_path: Path) -> AppConfig:
    """
    Load YAML configuration from disk.

    If no file exists, a default configuration is created.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        default_config = AppConfig()
        save_config(default_config, config_path)
        return default_config

    with config_path.open("r", encoding="utf-8") as file:
        raw_data = yaml.safe_load(file) or {}

    return AppConfig.model_validate(raw_data)


def save_config(config: AppConfig, config_path: Path) -> None:
    """Persist config to YAML file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump(mode="python")
    with config_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, sort_keys=False)

