"""Pre-flight coverage check for regimen comparison (aligns with prediction inference thresholds)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from backend.prediction.service import get_model_schema_bundle
from backend.recommendation.regimen_repo import TREATMENT_FIELD_NAMES

_TREATMENT = set(TREATMENT_FIELD_NAMES)


def _non_empty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return False
        return True
    if isinstance(v, str):
        return bool(v.strip())
    return True


def count_recommendation_coverage_slots(
    patient_features: Dict[str, Any],
    feature_order: List[str],
) -> Tuple[int, int]:
    """Treatment slots count as filled (library supplies numeric values including 0)."""
    filled = 0
    for name in feature_order:
        if name in _TREATMENT:
            filled += 1
        elif _non_empty(patient_features.get(name)):
            filled += 1
    return filled, len(feature_order)


def assert_recommendation_patient_coverage(model_id: str, patient_features: Dict[str, Any]) -> None:
    """Raises ValueError with an English message if coverage is below the model threshold."""
    bundle = get_model_schema_bundle(model_id)
    if bundle is None:
        raise ValueError("Model is not available or has no registered prediction schema.")
    order = [str(x) for x in (bundle.get("feature_order") or []) if str(x).strip()]
    if not order:
        raise ValueError("Model is missing a canonical feature order.")
    filled, total = count_recommendation_coverage_slots(patient_features, order)
    if total >= 4:
        min_need = max(3, int(round(total * 0.5)))
        if filled < min_need:
            raise ValueError(
                f"Too few patient features have been completed ({filled}/{total}). "
                "Please complete most required fields before running the comparison."
            )
