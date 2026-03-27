"""Repository layer for inspection result persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import InspectionRecord
from app.inspection.models import InspectionResult


class InspectionRepository:
    """Persist and query inspection records."""

    def __init__(
        self, session_factory: sessionmaker[Session], logger: logging.Logger | None = None
    ) -> None:
        self._session_factory = session_factory
        self._logger = logger or logging.getLogger("app")

    def save_result(self, result: InspectionResult, image_path: str | None) -> InspectionRecord:
        """Insert one inspection record."""
        inspected_at = datetime.fromtimestamp(result.timestamp)
        record = InspectionRecord(
            inspection_id=result.inspection_id,
            frame_id=result.frame_id,
            inspected_at=inspected_at,
            passed=result.passed,
            confidence=result.confidence,
            measurements_json=json.dumps(result.measurements),
            failure_reasons_json=json.dumps(result.failure_reasons),
            roi_json=json.dumps(result.roi if result.roi is not None else []),
            image_path=image_path or "",
        )

        with self._session_factory() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return record

    def get_recent(self, limit: int = 100) -> list[InspectionRecord]:
        """Fetch latest inspection records."""
        stmt = (
            select(InspectionRecord)
            .order_by(InspectionRecord.inspected_at.desc())
            .limit(max(1, limit))
        )
        with self._session_factory() as session:
            return list(session.scalars(stmt).all())

    def get_recent_failures(self, limit: int = 20) -> list[InspectionRecord]:
        """Fetch latest failed records only."""
        stmt = (
            select(InspectionRecord)
            .where(InspectionRecord.passed.is_(False))
            .order_by(InspectionRecord.inspected_at.desc())
            .limit(max(1, limit))
        )
        with self._session_factory() as session:
            return list(session.scalars(stmt).all())

    def get_counters(self) -> dict[str, int]:
        """Return total, pass, and fail counters from DB."""
        with self._session_factory() as session:
            total = session.scalar(select(func.count(InspectionRecord.id))) or 0
            passed = (
                session.scalar(
                    select(func.count(InspectionRecord.id)).where(
                        InspectionRecord.passed.is_(True)
                    )
                )
                or 0
            )
            failed = (
                session.scalar(
                    select(func.count(InspectionRecord.id)).where(
                        InspectionRecord.passed.is_(False)
                    )
                )
                or 0
            )
        return {"total": int(total), "pass": int(passed), "fail": int(failed)}

    def get_all_for_export(self) -> list[InspectionRecord]:
        """Fetch all records ordered by inspection time."""
        stmt = select(InspectionRecord).order_by(InspectionRecord.inspected_at.asc())
        with self._session_factory() as session:
            return list(session.scalars(stmt).all())

    def get_by_inspection_id(self, inspection_id: str) -> InspectionRecord | None:
        """Fetch one inspection record by its public inspection ID."""
        stmt = select(InspectionRecord).where(InspectionRecord.inspection_id == inspection_id)
        with self._session_factory() as session:
            return session.scalar(stmt)

