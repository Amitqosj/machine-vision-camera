"""CSV export for inspection records."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from app.db.repository import InspectionRepository
from app.services.image_storage_service import ImageStorageService


class ReportService:
    """Generate structured CSV report from persisted inspections."""

    def __init__(
        self,
        repository: InspectionRepository,
        image_storage: ImageStorageService,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._image_storage = image_storage
        self._logger = logger or logging.getLogger("app")

    def export_csv(self, destination: Path | None = None) -> Path:
        """Export all records to CSV and return output path."""
        if destination is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = self._image_storage.exports_dir / f"inspection_report_{stamp}.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)

        records = self._repository.get_all_for_export()
        with destination.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "inspection_id",
                    "frame_id",
                    "inspected_at",
                    "passed",
                    "confidence",
                    "image_path",
                    "failure_reasons_json",
                    "measurements_json",
                    "roi_json",
                ]
            )
            for row in records:
                writer.writerow(
                    [
                        row.inspection_id,
                        row.frame_id,
                        row.inspected_at.isoformat(),
                        row.passed,
                        f"{row.confidence:.4f}",
                        row.image_path,
                        row.failure_reasons_json,
                        row.measurements_json,
                        row.roi_json,
                    ]
                )
        self._logger.info("Exported %s inspection records to %s", len(records), destination)
        return destination

