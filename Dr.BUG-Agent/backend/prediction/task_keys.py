"""Canonical clinical prediction task keys shared by registry and prediction UI."""

from __future__ import annotations

from typing import FrozenSet, Optional

CLINICAL_EFFICACY = "clinical_efficacy"
SURVIVAL_OUTCOME = "survival_outcome"
POLYMYXIN_RESISTANCE = "polymyxin_resistance"
TREATMENT_DURATION = "treatment_duration"

CANONICAL_TASK_KEYS: FrozenSet[str] = frozenset(
    {
        CLINICAL_EFFICACY,
        SURVIVAL_OUTCOME,
        POLYMYXIN_RESISTANCE,
        TREATMENT_DURATION,
    }
)

# Normalizes historical / UI aliases to the four canonical keys.
_CLINICAL_TASK_ALIASES = {
    # Survival / mortality
    "mortality_28d": SURVIVAL_OUTCOME,
    "survival": SURVIVAL_OUTCOME,
    "survival_outcome": SURVIVAL_OUTCOME,
    "mortality": SURVIVAL_OUTCOME,
    "28d_mortality": SURVIVAL_OUTCOME,
    "28_day_mortality": SURVIVAL_OUTCOME,
    # Clinical efficacy
    "clinical_efficacy": CLINICAL_EFFICACY,
    "clinical_outcome": CLINICAL_EFFICACY,
    "efficacy": CLINICAL_EFFICACY,
    # Resistance
    "polymyxin_resistance": POLYMYXIN_RESISTANCE,
    "resistance": POLYMYXIN_RESISTANCE,
    # Duration
    "treatment_duration": TREATMENT_DURATION,
    "duration": TREATMENT_DURATION,
    "therapy_duration": TREATMENT_DURATION,
}


def normalize_clinical_task_id(raw: Optional[str]) -> Optional[str]:
    """Map registry clinical_task_id (or alias) to a canonical task key, or None if unknown."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    return _CLINICAL_TASK_ALIASES.get(s) or _CLINICAL_TASK_ALIASES.get(s.replace("-", "_"))


def normalize_requested_task_filter(raw: Optional[str]) -> Optional[str]:
    """Validate query param for GET .../available-for-prediction?task=."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    mapped = _CLINICAL_TASK_ALIASES.get(s) or _CLINICAL_TASK_ALIASES.get(s.replace("-", "_"))
    if mapped is not None:
        return mapped
    if s in CANONICAL_TASK_KEYS:
        return s
    return None
