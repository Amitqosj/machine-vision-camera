"""Entry point for the machine vision inspection application."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

from app.api.app import build_api_app
from app.core.config import load_config
from app.core.logging_config import setup_logging
from app.core.runtime_state import RuntimeState
from app.db.base import create_engine_and_session, initialize_database
from app.db.repository import InspectionRepository
from app.services.api_service import ApiService
from app.services.image_storage_service import ImageStorageService
from app.services.inspection_service import InspectionService
from app.services.report_service import ReportService
from app.ui.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for local execution."""
    parser = argparse.ArgumentParser(description="Real-time machine vision inspection system")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to YAML configuration file",
    )
    return parser.parse_args()


def main() -> int:
    """Application bootstrap."""
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_root / config_path

    config = load_config(config_path)
    setup_logging(config.logging, project_root=project_root)
    app_logger = logging.getLogger("app")
    app_logger.info("Loaded configuration from %s", config_path)

    runtime_state = RuntimeState()

    db_url = config.resolve_database_url()
    db_engine, session_factory = create_engine_and_session(
        database_url=db_url, echo=config.database.echo
    )
    initialize_database(db_engine)
    repository = InspectionRepository(session_factory=session_factory, logger=app_logger)

    image_storage = ImageStorageService(
        storage_config=config.storage,
        inspection_config=config.inspection,
        project_root=project_root,
        logger=app_logger,
    )
    report_service = ReportService(
        repository=repository,
        image_storage=image_storage,
        logger=app_logger,
    )
    inspection_service = InspectionService(
        config=config,
        repository=repository,
        image_storage=image_storage,
        runtime_state=runtime_state,
        logger=app_logger,
    )

    api_service: ApiService | None = None
    if config.api.enabled:
        api_app = build_api_app(runtime_state=runtime_state, repository=repository)
        api_service = ApiService(
            api_app=api_app,
            host=config.api.host,
            port=config.api.port,
            logger=app_logger,
        )
        api_service.start()

    qt_app = QApplication(sys.argv)
    window = MainWindow(
        service=inspection_service,
        report_service=report_service,
        config_path=config_path,
    )
    window.show()

    try:
        return qt_app.exec()
    finally:
        inspection_service.stop()
        if api_service is not None:
            api_service.stop()


if __name__ == "__main__":
    raise SystemExit(main())

