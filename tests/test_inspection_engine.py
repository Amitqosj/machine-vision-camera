import time

import cv2
import numpy as np

from app.core.config import InspectionConfig, StrategyConfig
from app.inspection.engine import InspectionEngine
from app.inspection.models import FramePacket


def _build_engine() -> InspectionEngine:
    cfg = InspectionConfig(
        annotation_enabled=False,
        strategies=[
            StrategyConfig(
                type="presence",
                params={"min_non_zero_ratio": 0.01, "min_mean_intensity": 5.0},
            ),
            StrategyConfig(
                type="contour_count",
                params={"threshold_value": 100, "min_contours": 1, "min_contour_area": 300.0},
            ),
            StrategyConfig(
                type="area_range",
                params={"threshold_value": 100, "min_area": 5000.0, "max_area": 50000.0},
            ),
            StrategyConfig(
                type="alignment",
                params={
                    "threshold_value": 100,
                    "expected_x_pct": 0.5,
                    "expected_y_pct": 0.5,
                    "tolerance_px": 60.0,
                },
            ),
        ],
    )
    return InspectionEngine(config=cfg)


def test_inspection_engine_pass_case() -> None:
    engine = _build_engine()
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(image, (140, 130), (260, 270), (255, 255, 255), -1)
    packet = FramePacket(frame_id=1, timestamp=time.time(), frame=image)

    result = engine.inspect(packet)

    assert result.passed is True
    assert result.confidence > 0.5
    assert len(result.rule_results) == 4


def test_inspection_engine_fail_alignment_case() -> None:
    engine = _build_engine()
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (140, 160), (255, 255, 255), -1)
    packet = FramePacket(frame_id=2, timestamp=time.time(), frame=image)

    result = engine.inspect(packet)

    assert result.passed is False
    assert any("Alignment" in reason or "alignment" in reason for reason in result.failure_reasons)

