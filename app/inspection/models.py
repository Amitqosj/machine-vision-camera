"""Inspection domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(slots=True)
class FramePacket:
    """Single captured frame with metadata."""

    frame_id: int
    timestamp: float
    frame: np.ndarray


@dataclass(slots=True)
class RuleResult:
    """Result from one inspection strategy."""

    rule_name: str
    passed: bool
    score: float
    message: str
    measurements: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class InspectionResult:
    """Final inspection decision for a single frame."""

    inspection_id: str
    frame_id: int
    timestamp: float
    passed: bool
    confidence: float
    roi: tuple[int, int, int, int] | None
    rule_results: list[RuleResult]
    measurements: dict[str, float]
    failure_reasons: list[str]
    annotated_frame: np.ndarray | None = None
    raw_frame: np.ndarray | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize into dictionary for API/state snapshots."""
        return {
            "inspection_id": self.inspection_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "confidence": self.confidence,
            "roi": self.roi,
            "measurements": self.measurements,
            "failure_reasons": self.failure_reasons,
            "rules": [
                {
                    "rule_name": rule.rule_name,
                    "passed": rule.passed,
                    "score": rule.score,
                    "message": rule.message,
                    "measurements": rule.measurements,
                }
                for rule in self.rule_results
            ],
        }

