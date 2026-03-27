from pathlib import Path

from app.core.config import AppConfig, load_config


def test_load_config_creates_default_when_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config = load_config(config_path)

    assert isinstance(config, AppConfig)
    assert config_path.exists()
    assert config.camera.width > 0


def test_load_config_reads_values(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
camera:
  kind: webcam
  source: 1
  width: 640
  height: 480
  fps: 20
pipeline:
  capture_queue_size: 2
inspection:
  roi:
    enabled: true
    x: 10
    y: 20
    width: 100
    height: 80
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.camera.source == 1
    assert config.camera.width == 640
    assert config.inspection.roi.enabled is True
    assert config.inspection.roi.width == 100

