"""Strategy registry to enable plug-in style inspection checks."""

from __future__ import annotations

from typing import Type

from app.inspection.strategies import (
    AlignmentStrategy,
    AreaRangeStrategy,
    ContourCountStrategy,
    DefectThresholdStrategy,
    InspectionStrategy,
    PresenceStrategy,
)

STRATEGY_REGISTRY: dict[str, Type[InspectionStrategy]] = {
    "presence": PresenceStrategy,
    "contour_count": ContourCountStrategy,
    "defect_threshold": DefectThresholdStrategy,
    "area_range": AreaRangeStrategy,
    "alignment": AlignmentStrategy,
}


def build_strategy(strategy_type: str, params: dict) -> InspectionStrategy:
    """Create strategy instance by configured type."""
    strategy_class = STRATEGY_REGISTRY.get(strategy_type)
    if strategy_class is None:
        raise ValueError(f"Unsupported strategy type: {strategy_type}")
    return strategy_class(params=params)

