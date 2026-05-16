from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from backend.agent.i18n.lexicons.zh_parameter_completion import (
    TARGET_COLUMN_EXTRACTION_PATTERNS,
    ZH_ML_TASK_BINARY_MARKERS,
    ZH_ML_TASK_GENERIC_CLASS_MARKERS,
    ZH_ML_TASK_MULTICLASS_MARKERS,
    ZH_ML_TASK_REGRESSION_MARKERS,
)
from backend.agent.normalizers import (
    CLINICAL_TASK_ALIASES,
    REPORT_TYPE_ALIASES,
    fuzzy_pick,
    normalize_whitespace,
)
from backend.agent.training_contract import (
    normalize_phase1_training_payload,
    training_phase1_missing_required_keys,
)
from backend.runtime import dataset_repo, model_repo, task_repo

REQUIRED_FIELDS: Dict[str, List[str]] = {
    "create_training_job": [
        "dataset_id",
        "clinical_task_id",
        "ml_task_type",
        "target_column",
    ],
    "draft_training_job": [
        "dataset_id",
        "clinical_task_id",
        "ml_task_type",
        "target_column",
    ],
    "create_prediction_job": ["model_id", "patient_features"],
    "draft_single_prediction": ["model_id", "patient_features"],
    "create_recommendation_job": ["model_id", "patient_features", "candidate_regimens"],
    "create_report_job": ["source_job_id", "report_type"],
}


def _extract_id(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(0) if m else None


def _model_schema_field_names(model_id: str) -> List[str]:
    meta = model_repo.get(model_id) if model_id else None
    if not meta:
        return []
    for key in ("feature_order", "required_features", "prediction_feature_order"):
        v = meta.get(key)
        if isinstance(v, list) and v:
            return [str(x) for x in v if x is not None]
    return []


def _prediction_missing(payload: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    if not (payload.get("model_id") or "").strip():
        missing.append("model_id")
    pf = payload.get("patient_features")
    if not isinstance(pf, dict) or len(pf) == 0:
        missing.append("patient_features")
    return missing


def enrich_draft_single_prediction_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """After merging context, fill field-name schema hints only; never write patient values."""
    mid = str(payload.get("model_id") or "").strip()
    hints = _model_schema_field_names(mid)
    out = dict(payload)
    if hints:
        out["draft_schema_field_names"] = hints
    return out


def prediction_action_missing(action_type: str, payload: Dict[str, Any]) -> List[str]:
    """Recompute missing fields for prediction actions after merging chat_context / client_completed_params."""
    if action_type in {"draft_single_prediction", "create_prediction_job"}:
        return _prediction_missing(payload)
    if action_type == "create_recommendation_job":
        m = _prediction_missing(payload)
        cr = payload.get("candidate_regimens")
        if not isinstance(cr, list) or len(cr) == 0:
            m.append("candidate_regimens")
        return m
    return []


def _try_extract_target_column(text: str) -> str | None:
    """Best-effort target column extraction from natural language (no hard medical semantics; None on miss)."""
    for pat in TARGET_COLUMN_EXTRACTION_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def complete_params(action_type: str, message: str) -> Tuple[Dict[str, Any], List[str], List[str]]:
    payload: Dict[str, Any] = {}
    completed: List[str] = []
    text = normalize_whitespace(message)

    datasets = dataset_repo.list()
    models = model_repo.list()
    tasks = task_repo.list()

    if action_type == "draft_single_prediction":
        # Never default to first/fuzzy model without explicit reference (e.g. "I want to predict" must not lock survival_28d_v1)
        model_id = _extract_id(r"(model_[a-zA-Z0-9_]+|demo_binary_v1|survival_28d_v1)", message)
        if not model_id:
            model_names = [str(m.get("model_id", "")) for m in models]
            token_pick = next((name for name in model_names if name and name.lower() in text.lower()), None)
            model_id = token_pick
        if model_id:
            payload["model_id"] = model_id
            completed.append("model_id")
        payload["patient_features"] = {}
        hints = _model_schema_field_names(str(model_id or ""))
        if hints:
            payload["draft_schema_field_names"] = hints
            completed.append("draft_schema_field_names")
        missing = _prediction_missing(payload)
        return payload, completed, missing

    if action_type in {"create_prediction_job", "create_recommendation_job"}:
        model_id = _extract_id(r"(model_[a-zA-Z0-9_]+|demo_binary_v1|survival_28d_v1)", message)
        if not model_id:
            model_names = [str(m.get("model_id", "")) for m in models]
            token_pick = next((name for name in model_names if name and name.lower() in text.lower()), None)
            model_id = token_pick
        if model_id:
            payload["model_id"] = model_id
            completed.append("model_id")
        payload["patient_features"] = {}
        if action_type == "create_recommendation_job":
            payload["candidate_regimens"] = []

    if action_type in {"create_training_job", "draft_training_job"}:
        dataset_id = _extract_id(r"ds_[a-zA-Z0-9]+", message)
        if not dataset_id:
            dataset_names = [d.get("name", "") for d in datasets]
            dataset_ids = [d.get("id", "") for d in datasets]
            hit_name = next((name for name in dataset_names if name and str(name).lower() in text), None)
            if hit_name:
                matched = next((d for d in datasets if d.get("name") == hit_name), None)
                dataset_id = matched["id"] if matched else None
            if not dataset_id:
                fuzzy_name = fuzzy_pick(text, [str(n).lower() for n in dataset_names])
                if fuzzy_name:
                    matched = next((d for d in datasets if str(d.get("name", "")).lower() == fuzzy_name), None)
                    dataset_id = matched["id"] if matched else None
            if not dataset_id:
                dataset_id = fuzzy_pick(text, dataset_ids) or (datasets[0]["id"] if datasets else None)
        if dataset_id:
            payload["dataset_id"] = dataset_id
            completed.append("dataset_id")

        matched_ct = None
        for k, v in CLINICAL_TASK_ALIASES.items():
            if k in text:
                matched_ct = v
                break
        if matched_ct:
            payload["clinical_task_id"] = matched_ct
            completed.append("clinical_task_id")

        ml_task_type = None
        if any(m in message for m in ZH_ML_TASK_REGRESSION_MARKERS) or "regression" in text:
            ml_task_type = "regression"
        elif any(m in message for m in ZH_ML_TASK_MULTICLASS_MARKERS) or "multiclass" in text:
            ml_task_type = "multiclass"
        elif any(m in message for m in ZH_ML_TASK_BINARY_MARKERS) or "binary" in text:
            ml_task_type = "binary"
        elif any(m in message for m in ZH_ML_TASK_GENERIC_CLASS_MARKERS):
            ml_task_type = "binary"
        if ml_task_type:
            payload["ml_task_type"] = ml_task_type
            completed.append("ml_task_type")

        feature_set_hit = _extract_id(r"(cand\d+)", text)
        target_guess = _try_extract_target_column(message)
        if feature_set_hit:
            payload["feature_set"] = feature_set_hit
            completed.append("feature_set")
        else:
            # Named feature set optional: allow default full candidate pool + CV-SHAP to satisfy contract; user refines final/selected in editor
            payload["use_cv_shap"] = True
            completed.append("use_cv_shap")
        if target_guess:
            payload["target_column"] = target_guess
            completed.append("target_column")

    if action_type == "create_report_job":
        source_job_id = _extract_id(r"job_[a-zA-Z0-9]+", message)
        if not source_job_id:
            source_job_id = tasks[0]["id"] if tasks else None
        if source_job_id:
            payload["source_job_id"] = source_job_id
            completed.append("source_job_id")
        report_type = next((v for k, v in REPORT_TYPE_ALIASES.items() if k in text), "training_report")
        payload["report_type"] = report_type
        completed.append("report_type")

    required = REQUIRED_FIELDS.get(action_type, [])
    if action_type in {"create_training_job", "draft_training_job"}:
        norm = normalize_phase1_training_payload(payload)
        missing = training_phase1_missing_required_keys(norm)
    elif action_type == "create_prediction_job":
        missing = _prediction_missing(payload)
    elif action_type == "create_recommendation_job":
        missing = _prediction_missing(payload)
        cr = payload.get("candidate_regimens")
        if not isinstance(cr, list) or len(cr) == 0:
            missing.append("candidate_regimens")
    else:
        missing = [key for key in required if key not in payload]
    return payload, completed, missing
