"""FastAPI endpoints for machine vision runtime status."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.runtime_state import RuntimeState
from app.db.repository import InspectionRepository


def build_api_app(runtime_state: RuntimeState, repository: InspectionRepository) -> FastAPI:
    """Build FastAPI application with local status endpoints."""
    app = FastAPI(title="Machine Vision Inspection API", version="1.0.0")

    @app.get("/health")
    def health() -> dict:
        snapshot = runtime_state.snapshot()
        return {
            "status": "ok",
            "running": snapshot["running"],
            "camera_connected": snapshot["camera_connected"],
        }

    @app.get("/status")
    def status() -> dict:
        return runtime_state.snapshot()

    @app.get("/counters")
    def counters() -> dict:
        runtime_snapshot = runtime_state.snapshot()
        persisted = repository.get_counters()
        return {
            "runtime": {
                "total": runtime_snapshot["total_count"],
                "pass": runtime_snapshot["pass_count"],
                "fail": runtime_snapshot["fail_count"],
            },
            "database": persisted,
        }

    @app.get("/recent-failures")
    def recent_failures(limit: int = 10) -> list[dict]:
        rows = repository.get_recent_failures(limit=limit)
        return [
            {
                "inspection_id": row.inspection_id,
                "inspected_at": row.inspected_at.isoformat(),
                "image_path": row.image_path,
                "confidence": row.confidence,
            }
            for row in rows
        ]

    return app

