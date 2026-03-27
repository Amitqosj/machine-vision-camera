import time
from pathlib import Path

import numpy as np

from app.db.base import create_engine_and_session, initialize_database
from app.db.repository import InspectionRepository
from app.inspection.models import InspectionResult, RuleResult


def _build_result(passed: bool) -> InspectionResult:
    return InspectionResult(
        inspection_id=f"test-{int(time.time() * 1000)}-{int(passed)}",
        frame_id=1,
        timestamp=time.time(),
        passed=passed,
        confidence=0.9 if passed else 0.2,
        roi=(0, 0, 10, 10),
        rule_results=[RuleResult("presence", passed=passed, score=0.9, message="ok")],
        measurements={"presence.non_zero_ratio": 0.2},
        failure_reasons=[] if passed else ["Object not present"],
        annotated_frame=np.zeros((10, 10, 3), dtype=np.uint8),
        raw_frame=np.zeros((10, 10, 3), dtype=np.uint8),
    )


def test_repository_persists_and_counts(tmp_path: Path) -> None:
    db_path = tmp_path / "inspection.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    engine, session_factory = create_engine_and_session(db_url)
    initialize_database(engine)

    repo = InspectionRepository(session_factory=session_factory)
    repo.save_result(_build_result(True), image_path="")
    repo.save_result(_build_result(False), image_path="")

    counters = repo.get_counters()
    assert counters["total"] == 2
    assert counters["pass"] == 1
    assert counters["fail"] == 1

