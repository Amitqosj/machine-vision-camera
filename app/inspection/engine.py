"""Inspection engine orchestrating all active strategies."""

from __future__ import annotations

import logging
from threading import RLock

import cv2
import numpy as np

from app.core.config import InspectionConfig, RoiConfig
from app.inspection.models import FramePacket, InspectionResult, RuleResult
from app.inspection.registry import build_strategy
from app.inspection.strategies import InspectionStrategy


class InspectionEngine:
    """Runs configured strategy chain and emits PASS/FAIL decisions."""

    def __init__(
        self, config: InspectionConfig, logger: logging.Logger | None = None
    ) -> None:
        self._config = config
        self._logger = logger or logging.getLogger("inspection")
        self._lock = RLock()
        self._strategies: list[InspectionStrategy] = []
        self._build_strategies()

    def _build_strategies(self) -> None:
        strategies: list[InspectionStrategy] = []
        for strategy_cfg in self._config.strategies:
            if not strategy_cfg.enabled:
                continue
            strategies.append(build_strategy(strategy_cfg.type, strategy_cfg.params))
        self._strategies = strategies
        self._logger.info("Loaded %s inspection strategies.", len(self._strategies))

    def update_roi(self, roi: RoiConfig) -> None:
        """Update ROI at runtime (typically from UI interaction)."""
        with self._lock:
            self._config.roi = roi
            self._logger.info(
                "ROI updated to enabled=%s, x=%s y=%s w=%s h=%s",
                roi.enabled,
                roi.x,
                roi.y,
                roi.width,
                roi.height,
            )

    def reload_strategies(self, config: InspectionConfig) -> None:
        """Reload strategy list from updated inspection config."""
        with self._lock:
            self._config = config
            self._build_strategies()

    def _resolve_roi(self, frame: np.ndarray) -> tuple[int, int, int, int] | None:
        roi = self._config.roi
        if not roi.enabled:
            return None

        frame_h, frame_w = frame.shape[:2]
        x = min(max(0, roi.x), frame_w - 1)
        y = min(max(0, roi.y), frame_h - 1)
        w = min(max(1, roi.width), frame_w - x)
        h = min(max(1, roi.height), frame_h - y)
        return x, y, w, h

    def _annotate_frame(
        self,
        frame: np.ndarray,
        passed: bool,
        confidence: float,
        roi: tuple[int, int, int, int] | None,
        rule_results: list[RuleResult],
    ) -> np.ndarray:
        annotated = frame.copy()
        color = (0, 180, 0) if passed else (0, 0, 255)
        label = "PASS" if passed else "FAIL"

        cv2.putText(
            annotated,
            f"{label} | confidence: {confidence:.2f}",
            (20, 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2,
            cv2.LINE_AA,
        )

        if roi is not None:
            x, y, w, h = roi
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 200, 0), 2)
            cv2.putText(
                annotated,
                "ROI",
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 200, 0),
                2,
                cv2.LINE_AA,
            )

        start_y = 70
        for idx, rule in enumerate(rule_results[:6]):
            rule_color = (0, 180, 0) if rule.passed else (0, 0, 255)
            text = f"{rule.rule_name}: {'OK' if rule.passed else 'NG'} ({rule.score:.2f})"
            cv2.putText(
                annotated,
                text,
                (20, start_y + idx * 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                rule_color,
                2,
                cv2.LINE_AA,
            )
        return annotated

    def inspect(self, packet: FramePacket) -> InspectionResult:
        """Evaluate one frame and return final decision payload."""
        frame = packet.frame

        with self._lock:
            roi = self._resolve_roi(frame)
            if roi is None:
                roi_img = frame
            else:
                x, y, w, h = roi
                roi_img = frame[y : y + h, x : x + w]

            rule_results: list[RuleResult] = []
            for strategy in self._strategies:
                try:
                    result = strategy.evaluate(roi_img)
                except Exception as exc:  # pylint: disable=broad-except
                    self._logger.exception("Strategy '%s' failed: %s", strategy.name, exc)
                    result = RuleResult(
                        rule_name=strategy.name,
                        passed=False,
                        score=0.0,
                        message=f"Runtime error: {exc}",
                    )
                rule_results.append(result)

            passed = all(result.passed for result in rule_results) if rule_results else False
            confidence = (
                sum(result.score for result in rule_results) / len(rule_results)
                if rule_results
                else 0.0
            )
            failure_reasons = [result.message for result in rule_results if not result.passed]

            merged_measurements: dict[str, float] = {}
            for result in rule_results:
                for key, value in result.measurements.items():
                    merged_measurements[f"{result.rule_name}.{key}"] = float(value)

            inspection_id = f"{int(packet.timestamp * 1000)}-{packet.frame_id}"
            annotated_frame = (
                self._annotate_frame(frame, passed, confidence, roi, rule_results)
                if self._config.annotation_enabled
                else frame.copy()
            )

            return InspectionResult(
                inspection_id=inspection_id,
                frame_id=packet.frame_id,
                timestamp=packet.timestamp,
                passed=passed,
                confidence=float(confidence),
                roi=roi,
                rule_results=rule_results,
                measurements=merged_measurements,
                failure_reasons=failure_reasons,
                annotated_frame=annotated_frame,
                raw_frame=frame.copy(),
            )

