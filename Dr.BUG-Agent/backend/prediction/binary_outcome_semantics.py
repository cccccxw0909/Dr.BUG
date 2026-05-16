"""
Binary-output positive-class probability semantics: consistent with recommendation flow, inferred from model/task metadata.
Determines whether the positive class means survival or mortality risk for display copy and labels, without hard-coding a mortality template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import math

from backend.prediction.zh_compat_tokens import (
    EFFICACYISH_TASK_NAME_MARKERS,
    MORTALITY_HINTS,
    SURVIVAL_HINTS,
    WINDOW_28D_TEXT_MARKERS,
)

SCORE_DIRECTION_POSITIVE_IS_SURVIVAL = "positive_is_survival"
SCORE_DIRECTION_POSITIVE_IS_MORTALITY = "positive_is_mortality"


def _contains_any(text: str, hints: Tuple[str, ...]) -> bool:
    return any(h in text for h in hints)


def _is_survival_compatible(model_id: str, model_meta: Dict[str, Any], schema_bundle: Dict[str, Any]) -> bool:
    text_parts = [
        str(model_id or "").lower(),
        str(model_meta.get("task_name") or "").lower(),
        str(model_meta.get("clinical_task_id") or "").lower(),
        str(model_meta.get("target_column") or "").lower(),
        str(schema_bundle.get("task_name") or "").lower(),
    ]
    text = " ".join(text_parts)
    survival_keywords = (
        "survival",
        "mortality",
        "death",
        "28d",
        "28_day",
        "28-day",
        "mortality_28d",
    )
    return any(k in text for k in survival_keywords)


def determine_score_direction(
    model_id: str,
    model_meta: Dict[str, Any],
    schema_bundle: Dict[str, Any],
) -> str:
    """
    Return positive-class probability semantics:
    - positive_is_survival: p(class=1) means survival or a survival-related positive class
    - positive_is_mortality: p(class=1) means death or an adverse outcome
    Raise ValueError when semantics cannot be determined reliably, consistent with recommendation validation.
    """
    meta_block = schema_bundle.get("metadata") if isinstance(schema_bundle.get("metadata"), dict) else {}
    clinical_task_id = str(model_meta.get("clinical_task_id") or "").strip().lower()
    if clinical_task_id:
        has_survival = _contains_any(clinical_task_id, SURVIVAL_HINTS)
        has_mortality = _contains_any(clinical_task_id, MORTALITY_HINTS)
        if has_survival and has_mortality:
            raise ValueError("Model clinical-task semantics conflict: both survival and mortality hints are present")
        if has_survival:
            return SCORE_DIRECTION_POSITIVE_IS_SURVIVAL
        if has_mortality:
            return SCORE_DIRECTION_POSITIVE_IS_MORTALITY

    text_candidates = [
        str(model_id or "").lower(),
        str(model_meta.get("task_name") or "").lower(),
        str(model_meta.get("target_outcome") or "").lower(),
        str(model_meta.get("target_column") or "").lower(),
        str(schema_bundle.get("task_name") or "").lower(),
        str(meta_block.get("task_name") or "").lower(),
        str(meta_block.get("target_name") or "").lower(),
        str(meta_block.get("target_outcome") or "").lower(),
        str(meta_block.get("notes") or "").lower(),
    ]
    joined_text = " ".join([t for t in text_candidates if t])
    if joined_text:
        has_survival = _contains_any(joined_text, SURVIVAL_HINTS)
        has_mortality = _contains_any(joined_text, MORTALITY_HINTS)
        if has_survival and has_mortality:
            raise ValueError(
                "Cannot determine survival probability direction: model metadata contains both survival and mortality semantics; add explicit label semantics"
            )
        if has_survival:
            return SCORE_DIRECTION_POSITIVE_IS_SURVIVAL
        if has_mortality:
            return SCORE_DIRECTION_POSITIVE_IS_MORTALITY

    label_mapping = None
    if isinstance(meta_block.get("label_mapping"), dict):
        label_mapping = meta_block.get("label_mapping")
    elif isinstance(model_meta.get("label_mapping"), dict):
        label_mapping = model_meta.get("label_mapping")
    if isinstance(label_mapping, dict):
        pos_label = str(label_mapping.get("1") or "").strip().lower()
        if pos_label:
            has_survival = _contains_any(pos_label, SURVIVAL_HINTS)
            has_mortality = _contains_any(pos_label, MORTALITY_HINTS)
            if has_survival and has_mortality:
                raise ValueError("Cannot determine survival probability direction: label_mapping[1] contains both survival and mortality semantics")
            if has_survival:
                return SCORE_DIRECTION_POSITIVE_IS_SURVIVAL
            if has_mortality:
                return SCORE_DIRECTION_POSITIVE_IS_MORTALITY

    raise ValueError(
        "Cannot determine survival probability direction: explicit survival/mortality label semantics are missing (for example clinical_task_id, task_name, target_outcome, or label_mapping)"
    )


def _efficacyish(task_name: str, model_id: str) -> bool:
    tn = str(task_name or "").lower()
    mid = str(model_id or "").lower()
    return any(x in tn for x in EFFICACYISH_TASK_NAME_MARKERS) or "efficacy" in mid


def _window_28d_hint(model_meta: Dict[str, Any], schema_bundle: Dict[str, Any]) -> bool:
    meta_block = schema_bundle.get("metadata") if isinstance(schema_bundle.get("metadata"), dict) else {}
    parts = [
        str(model_meta.get("task_name") or ""),
        str(model_meta.get("target_outcome") or ""),
        str(model_meta.get("clinical_task_id") or ""),
        str(schema_bundle.get("task_name") or ""),
        str(meta_block.get("task_name") or ""),
        str(meta_block.get("target_outcome") or ""),
        str(meta_block.get("notes") or ""),
    ]
    t = " ".join(parts).lower()
    if any(k in t for k in WINDOW_28D_TEXT_MARKERS):
        return True
    return "28" in t and "day" in t


@dataclass
class BinaryClassificationDisplay:
    """Single-sample binary display: optionally override predicted_label / label_display / outcome_display to remove placeholder labels that contradict probability semantics, such as High risk."""

    probability_display_line: str
    label_display_line: str
    predicted_label: Optional[str] = None
    label_display: Optional[str] = None
    outcome_display: Optional[str] = None


def build_binary_classification_display(
    *,
    model_id: str,
    task_name: str,
    task_type: str,
    model_meta: Dict[str, Any],
    schema_bundle: Dict[str, Any],
    raw_label: str,
    predicted_probability: Optional[float],
    risk_score: Optional[float],
) -> BinaryClassificationDisplay:
    """
    Generate probability_display_line / label_display_line; when survival/mortality semantics are explicit, align predicted_label with probability meaning.
    For non-binary task_type values, do not infer survival/mortality; use efficacy or generic positive-class copy only.
    """
    p = predicted_probability
    if p is None and risk_score is not None:
        try:
            p = float(risk_score)
        except (TypeError, ValueError):
            p = None
    pct = f"{p * 100:.1f}%" if p is not None and not (isinstance(p, float) and math.isnan(p)) else "—"
    lab_low = (raw_label or "").strip().lower()

    if _efficacyish(task_name, model_id):
        prob_line = f"Probability of improvement: {pct}"
        if "fail" in lab_low or lab_low in ("0", "no"):
            plab = "Failure"
        elif "improv" in lab_low or "success" in lab_low or lab_low in ("1", "yes"):
            plab = "Improvement"
        else:
            plab = raw_label.strip() if raw_label.strip() else "—"
        label_line = f"Predicted label: {plab}"
        return BinaryClassificationDisplay(probability_display_line=prob_line, label_display_line=label_line)

    if task_type == "binary" and _is_survival_compatible(model_id, model_meta, schema_bundle):
        try:
            direction = determine_score_direction(model_id, model_meta, schema_bundle)
        except ValueError:
            prob_line = f"Estimated positive-class probability: {pct}"
            label_line = f"Predicted label: {raw_label.strip() if raw_label.strip() else '—'}"
            return BinaryClassificationDisplay(probability_display_line=prob_line, label_display_line=label_line)

        use_28d = _window_28d_hint(model_meta, schema_bundle)
        if p is None:
            label_en = "—"
        elif direction == SCORE_DIRECTION_POSITIVE_IS_SURVIVAL:
            label_en = "Survival" if p >= 0.5 else "Death"
        else:
            label_en = "Death" if p >= 0.5 else "Survival"

        if direction == SCORE_DIRECTION_POSITIVE_IS_SURVIVAL:
            if use_28d:
                prob_line = f"28-day survival probability: {pct}"
            else:
                prob_line = f"Predicted survival probability: {pct}"
        else:
            if use_28d:
                prob_line = f"28-day mortality probability: {pct}"
            else:
                prob_line = f"Predicted mortality probability: {pct}"

        label_line = f"Predicted label: {label_en}"
        return BinaryClassificationDisplay(
            probability_display_line=prob_line,
            label_display_line=label_line,
            predicted_label=label_en,
            label_display=label_en,
            outcome_display=label_en,
        )

    prob_line = f"Estimated positive-class probability: {pct}"
    label_line = f"Predicted label: {raw_label.strip() if raw_label.strip() else '—'}"
    return BinaryClassificationDisplay(probability_display_line=prob_line, label_display_line=label_line)
