"""Training contract entrypoint: alias normalization + defaults → DomainTrainingPayload.

Do not hand-build the final structure in orchestrator, parameter_completion, or the frontend;
use `normalize_training_payload` → `DomainTrainingPayload` (or `validate_training_payload`).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from backend.schemas.training_domain import (
    CLINICAL_TASK_IDS,
    ML_TASK_TYPES,
    DomainTrainingPayload,
    TrainingPhase1Payload,
)

# Phase1 (Chat initial confirm card): dataset/task/feature pool only; model + metrics finalized in Phase4
REQUIRED_TRAINING_PHASE1_FIELD_KEYS: List[str] = [
    "dataset_id",
    "clinical_task_id",
    "ml_task_type",
    "target_column",
]

# Full Domain contract (tooling / regression)
REQUIRED_TRAINING_FIELD_KEYS: List[str] = [
    "dataset_id",
    "clinical_task_id",
    "ml_task_type",
    "target_column",
    "model_type",
    "objective_metric",
]


def normalize_training_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shallow-copy, normalize aliases, strip ambiguous `task_type`, turn empty time strings into None.
    Does not raise domain validation errors (required fields / feature sources belong to DomainTrainingPayload).
    """
    data: Dict[str, Any] = copy.copy(dict(raw))

    # ---- legacy flat publish keys → publish_overrides ----
    if (data.get("publish_model_id") is not None or data.get("publish_notes") is not None) and not isinstance(
        data.get("publish_overrides"), dict
    ):
        po: Dict[str, Any] = {}
        pm = data.pop("publish_model_id", None)
        pn = data.pop("publish_notes", None)
        if pm is not None and str(pm).strip():
            po["model_id"] = str(pm).strip()
        if pn is not None and str(pn).strip():
            po["notes"] = str(pn).strip()
        data["publish_overrides"] = po
    elif isinstance(data.get("publish_overrides"), dict):
        pass
    else:
        data["publish_overrides"] = {}

    # ---- task_type disambiguation: never mix clinical id and ML task type in one field ----
    legacy_tt = data.pop("task_type", None)
    if legacy_tt is not None and isinstance(legacy_tt, str):
        lt = legacy_tt.strip()
        if lt in CLINICAL_TASK_IDS:
            data.setdefault("clinical_task_id", lt)
        elif lt in ML_TASK_TYPES:
            data.setdefault("ml_task_type", lt)
        else:
            data.setdefault("clinical_task_id", lt)

    # ---- Time fields: empty string → None ----
    for k in ("index_time", "label_time"):
        v = data.get(k)
        if isinstance(v, str) and not v.strip():
            data[k] = None

    # ---- List fields: defaults ----
    for k in ("med_cols", "selected_features", "final_features"):
        v = data.get(k)
        if v is None:
            data[k] = []
        elif not isinstance(v, list):
            data[k] = [v]  # lenient: accept scalar

    # ---- feature_set: empty string → None (feature-source validation handles the rest) ----
    fs = data.get("feature_set")
    if isinstance(fs, str) and not fs.strip():
        data["feature_set"] = None
    elif isinstance(fs, str):
        data["feature_set"] = fs.strip()

    # ---- target_column: trim ----
    tc = data.get("target_column")
    if isinstance(tc, str):
        data["target_column"] = tc.strip()

    # ---- objective_metric ----
    om = data.get("objective_metric")
    if isinstance(om, str):
        data["objective_metric"] = om.strip()

    # ---- model_name: empty / all-digit (mistyped registry row or model_id) → None ----
    mn = data.get("model_name")
    if mn is not None and isinstance(mn, str):
        stripped = mn.strip()
        if not stripped or stripped.isdigit():
            data["model_name"] = None
        else:
            data["model_name"] = stripped

    return data


def validate_training_payload(raw: Dict[str, Any]) -> DomainTrainingPayload:
    """Normalize then validate; returns a domain model instance."""
    normalized = normalize_training_payload(raw)
    # publish_overrides nested model conversion handled by Pydantic
    return DomainTrainingPayload.model_validate(normalized)


def validate_training_payload_to_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Final flat+nested-consistent dict for task params / API."""
    return validate_training_payload(raw).model_dump_for_task_params()


def normalize_phase1_training_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Phase1 input: clear locked columns; model_type/objective_metric optional (MCP may prefill Phase4)."""
    data = normalize_training_payload(raw)
    data["final_features"] = []
    po = data.get("publish_overrides")
    if not isinstance(po, dict) or not po:
        data["publish_overrides"] = {}
    return data


def training_phase1_missing_required_keys(payload: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for key in REQUIRED_TRAINING_PHASE1_FIELD_KEYS:
        v = payload.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(key)
    return missing


def validate_phase1_training_payload(raw: Dict[str, Any]) -> TrainingPhase1Payload:
    norm = normalize_phase1_training_payload(raw)
    return TrainingPhase1Payload.model_validate(norm)


def validate_phase1_training_payload_to_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    return validate_phase1_training_payload(raw).model_dump_for_task_params()


def training_missing_required_keys(payload: Dict[str, Any]) -> List[str]:
    """Minimum required keys only (non-empty strings); excludes the feature triple rule."""
    missing: List[str] = []
    for key in REQUIRED_TRAINING_FIELD_KEYS:
        v = payload.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(key)
    return missing


def is_training_payload_complete_for_pending(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Whether a pending action may enter confirmation: required keys first, then full model validation (feature sources).
    Returns (ok, missing_or_error_messages).
    """
    norm = normalize_phase1_training_payload(payload)
    miss = training_phase1_missing_required_keys(norm)
    if miss:
        return False, miss
    try:
        TrainingPhase1Payload.model_validate(norm)
    except ValidationError as exc:
        errs: List[str] = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e.get("loc", ()))
            errs.append(loc + ": " + str(e.get("msg", "")))
        return False, errs
    return True, []

