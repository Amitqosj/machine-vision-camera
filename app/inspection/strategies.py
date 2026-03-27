"""Pluggable inspection strategy implementations."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

import cv2
import numpy as np

from app.inspection.models import RuleResult


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _binary_threshold(gray: np.ndarray, threshold_value: int) -> np.ndarray:
    _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    return binary


class InspectionStrategy(ABC):
    """Base class for all inspection checks."""

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params = params or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""

    @abstractmethod
    def evaluate(self, image: np.ndarray) -> RuleResult:
        """Run rule logic and return result."""


class PresenceStrategy(InspectionStrategy):
    """Detect whether object is present in ROI."""

    @property
    def name(self) -> str:
        return "presence"

    def evaluate(self, image: np.ndarray) -> RuleResult:
        gray = _to_gray(image)
        total_pixels = max(1, gray.size)
        non_zero_ratio = cv2.countNonZero(gray) / total_pixels
        mean_intensity = float(np.mean(gray))
        min_non_zero_ratio = float(self.params.get("min_non_zero_ratio", 0.01))
        min_mean_intensity = float(self.params.get("min_mean_intensity", 15.0))

        passed = (
            non_zero_ratio >= min_non_zero_ratio and mean_intensity >= min_mean_intensity
        )
        score_ratio = min(1.0, non_zero_ratio / max(min_non_zero_ratio, 1e-6))
        score_mean = min(1.0, mean_intensity / max(min_mean_intensity, 1e-6))
        score = float(max(0.0, min(1.0, (score_ratio + score_mean) / 2.0)))

        return RuleResult(
            rule_name=self.name,
            passed=passed,
            score=score,
            message="Object presence check passed." if passed else "Object not present.",
            measurements={
                "non_zero_ratio": float(non_zero_ratio),
                "mean_intensity": mean_intensity,
            },
        )


class ContourCountStrategy(InspectionStrategy):
    """Ensure minimum contour count exists after thresholding."""

    @property
    def name(self) -> str:
        return "contour_count"

    def evaluate(self, image: np.ndarray) -> RuleResult:
        gray = _to_gray(image)
        threshold_value = int(self.params.get("threshold_value", 100))
        min_contours = int(self.params.get("min_contours", 1))
        min_area = float(self.params.get("min_contour_area", 100.0))

        binary = _binary_threshold(gray, threshold_value)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
        contour_count = len(valid_contours)
        passed = contour_count >= min_contours
        score = min(1.0, contour_count / max(min_contours, 1))

        return RuleResult(
            rule_name=self.name,
            passed=passed,
            score=float(score),
            message=(
                f"Found {contour_count} valid contours."
                if passed
                else f"Contour count below minimum ({contour_count}/{min_contours})."
            ),
            measurements={"valid_contours": float(contour_count)},
        )


class DefectThresholdStrategy(InspectionStrategy):
    """Detect defects using pixel threshold ratio."""

    @property
    def name(self) -> str:
        return "defect_threshold"

    def evaluate(self, image: np.ndarray) -> RuleResult:
        gray = _to_gray(image)
        threshold_value = int(self.params.get("threshold_value", 80))
        object_threshold_value = int(self.params.get("object_threshold_value", 100))
        mode = str(self.params.get("mode", "dark")).lower()
        max_defect_ratio = float(self.params.get("max_defect_ratio", 0.05))
        min_object_pixels = int(self.params.get("min_object_pixels", 500))

        object_mask = gray > object_threshold_value
        object_pixels = int(np.sum(object_mask))
        if object_pixels < min_object_pixels:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                score=0.0,
                message="Object region too small for defect check.",
                measurements={"defect_ratio": 1.0, "object_pixels": float(object_pixels)},
            )

        if mode == "bright":
            defect_mask = (gray > threshold_value) & object_mask
        else:
            defect_mask = (gray < threshold_value) & object_mask
        defect_pixels = float(np.sum(defect_mask))
        defect_ratio = defect_pixels / max(object_pixels, 1)
        passed = defect_ratio <= max_defect_ratio
        score = max(0.0, 1.0 - defect_ratio / max(max_defect_ratio, 1e-6))

        return RuleResult(
            rule_name=self.name,
            passed=passed,
            score=float(min(1.0, score)),
            message=(
                "Defect threshold check passed."
                if passed
                else f"Defect ratio too high ({defect_ratio:.4f})."
            ),
            measurements={
                "defect_ratio": float(defect_ratio),
                "object_pixels": float(object_pixels),
            },
        )


class AreaRangeStrategy(InspectionStrategy):
    """Check largest contour area is inside configured limits."""

    @property
    def name(self) -> str:
        return "area_range"

    def evaluate(self, image: np.ndarray) -> RuleResult:
        gray = _to_gray(image)
        threshold_value = int(self.params.get("threshold_value", 100))
        min_area = float(self.params.get("min_area", 1000.0))
        max_area = float(self.params.get("max_area", 1_000_000.0))

        binary = _binary_threshold(gray, threshold_value)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_area = max((cv2.contourArea(cnt) for cnt in contours), default=0.0)
        passed = min_area <= largest_area <= max_area

        center = (min_area + max_area) / 2.0
        span = max((max_area - min_area) / 2.0, 1e-6)
        score = max(0.0, 1.0 - abs(largest_area - center) / span)

        return RuleResult(
            rule_name=self.name,
            passed=passed,
            score=float(min(1.0, score)),
            message=(
                "Area range check passed."
                if passed
                else f"Largest area out of range ({largest_area:.2f})."
            ),
            measurements={"largest_area": float(largest_area)},
        )


class AlignmentStrategy(InspectionStrategy):
    """Check object centroid alignment relative to expected position."""

    @property
    def name(self) -> str:
        return "alignment"

    def evaluate(self, image: np.ndarray) -> RuleResult:
        gray = _to_gray(image)
        threshold_value = int(self.params.get("threshold_value", 100))
        expected_x_pct = float(self.params.get("expected_x_pct", 0.5))
        expected_y_pct = float(self.params.get("expected_y_pct", 0.5))
        tolerance_px = float(self.params.get("tolerance_px", 40.0))
        min_area = float(self.params.get("min_contour_area", 120.0))

        binary = _binary_threshold(gray, threshold_value)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
        if not contours:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                score=0.0,
                message="No contour found for alignment check.",
                measurements={"distance_px": float("inf")},
            )

        largest = max(contours, key=cv2.contourArea)
        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                score=0.0,
                message="Invalid contour moments for alignment check.",
                measurements={"distance_px": float("inf")},
            )

        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        expected_x = image.shape[1] * expected_x_pct
        expected_y = image.shape[0] * expected_y_pct
        distance_px = math.hypot(cx - expected_x, cy - expected_y)
        passed = distance_px <= tolerance_px
        score = max(0.0, 1.0 - distance_px / max(tolerance_px, 1e-6))

        return RuleResult(
            rule_name=self.name,
            passed=passed,
            score=float(min(1.0, score)),
            message=(
                "Alignment check passed."
                if passed
                else f"Alignment offset too high ({distance_px:.2f}px)."
            ),
            measurements={
                "distance_px": float(distance_px),
                "centroid_x": float(cx),
                "centroid_y": float(cy),
            },
        )

