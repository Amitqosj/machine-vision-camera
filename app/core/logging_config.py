"""Logging setup with rotating handlers for production use."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import LoggingConfig


def _build_file_handler(
    file_path: Path, level: int, fmt: str, max_bytes: int, backup_count: int
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))
    return handler


def setup_logging(config: LoggingConfig, project_root: Path) -> dict[str, logging.Logger]:
    """Configure root and module-specific loggers."""
    log_dir = Path(config.log_dir)
    if not log_dir.is_absolute():
        log_dir = project_root / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    root_level = getattr(logging, config.level.upper(), logging.INFO)
    formatter = config.format

    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(root_level)
    console.setFormatter(logging.Formatter(formatter))
    root_logger.addHandler(console)
    root_logger.addHandler(
        _build_file_handler(
            log_dir / "app.log",
            root_level,
            formatter,
            config.max_bytes,
            config.backup_count,
        )
    )

    logger_specs = {
        "camera": ("camera.log", root_level),
        "inspection": ("inspection.log", root_level),
        "error": ("error.log", logging.ERROR),
    }

    configured_loggers: dict[str, logging.Logger] = {}
    for logger_name, (file_name, level) in logger_specs.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        logger.addHandler(
            _build_file_handler(
                log_dir / file_name,
                level,
                formatter,
                config.max_bytes,
                config.backup_count,
            )
        )
        logger.propagate = True
        configured_loggers[logger_name] = logger

    configured_loggers["app"] = logging.getLogger("app")
    configured_loggers["app"].setLevel(root_level)
    return configured_loggers

