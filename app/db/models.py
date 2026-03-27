"""SQLAlchemy ORM entities for inspection results."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InspectionRecord(Base):
    """Persistent inspection audit record."""

    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    frame_id: Mapped[int] = mapped_column(Integer, index=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    passed: Mapped[bool] = mapped_column(Boolean, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    measurements_json: Mapped[str] = mapped_column(Text)
    failure_reasons_json: Mapped[str] = mapped_column(Text)
    roi_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

