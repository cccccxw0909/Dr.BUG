from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.prediction.binary_outcome_semantics import (
    SCORE_DIRECTION_POSITIVE_IS_MORTALITY,
    SCORE_DIRECTION_POSITIVE_IS_SURVIVAL,
    _is_survival_compatible,
    determine_score_direction,
)
from backend.prediction.inference import run_single_sample
from backend.prediction.service import get_model_schema_bundle
from backend.recommendation.errors import RecommendationServiceError
from backend.recommendation.regimen_repo import FileRegimenRepo, TREATMENT_FIELD_NAMES
from backend.runtime import model_repo

SURVIVAL_ONLY_MODE = "survival_only"


def validate_survival_model(model_id: str) -> Dict[str, Any]:
    mid = str(model_id or "").strip()
    if not mid:
        raise RecommendationServiceError("REC_MODEL_ID_REQUIRED", "model_id is required")
    meta = model_repo.get(mid)
    if not meta:
        raise RecommendationServiceError("REC_MODEL_NOT_FOUND", f"Model not found: {mid}", context={"model_id": mid})
    bundle = get_model_schema_bundle(mid)
    if bundle is None:
        raise RecommendationServiceError(
            "REC_MODEL_SCHEMA_UNAVAILABLE",
            f"No registered prediction schema for model_id={mid}",
            context={"model_id": mid},
        )
    if not _is_survival_compatible(mid, meta, bundle):
        raise RecommendationServiceError(
            "REC_MODEL_SURVIVAL_INCOMPATIBLE",
            "Model metadata is not compatible with survival-only regimen recommendation",
            context={"model_id": mid},
        )
    score_direction = determine_score_direction(mid, meta, bundle)
    return {"model_meta": meta, "schema_bundle": bundle, "score_direction": score_direction}


def normalize_treatment_values(raw: Optional[Dict[str, Any]]) -> Dict[str, float]:
    data = raw if isinstance(raw, dict) else {}
    out: Dict[str, float] = {}
    for field_name in TREATMENT_FIELD_NAMES:
        v = data.get(field_name, 0.0)
        try:
            out[field_name] = float(v)
        except (TypeError, ValueError):
            raise RecommendationServiceError(
                "REC_TREATMENT_FIELD_NOT_NUMERIC",
                f"treatment_values field is not numeric: {field_name}",
                context={"field_name": field_name},
            ) from None
    return out


def _select_candidate_regimens(
    repo: FileRegimenRepo,
    regimen_ids: Optional[List[str]],
) -> List[Dict[str, Any]]:
    all_items = repo.list()
    enabled_items = [x for x in all_items if bool(x.get("enabled"))]
    if regimen_ids:
        id_set = {str(x).strip() for x in regimen_ids if str(x).strip()}
        if not id_set:
            selected = enabled_items
        else:
            selected = [x for x in enabled_items if str(x.get("regimen_id")) in id_set]
            selected_ids = {str(x.get("regimen_id")) for x in selected}
            missing = sorted(id_set - selected_ids)
            if missing:
                raise RecommendationServiceError(
                    "REC_REGIMEN_IDS_NOT_FOUND_OR_DISABLED",
                    f"regimen_id not found or not enabled: {', '.join(missing)}",
                    context={"missing_regimen_ids": missing},
                )
    else:
        selected = enabled_items
    if not selected:
        raise RecommendationServiceError(
            "REC_NO_ENABLED_REGIMEN_CANDIDATES",
            "No enabled regimen candidates are available",
        )
    return selected


def _build_aligned_candidate_values(
    patient_features: Dict[str, Any],
    regimen_treatment_values: Dict[str, float],
    feature_order: List[str],
) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(patient_features)
    for field_name in TREATMENT_FIELD_NAMES:
        merged[field_name] = regimen_treatment_values.get(field_name, 0.0)
    # Merge by field name first, then take values in model canonical feature_order; extra keys kept for existing inference checks.
    aligned: Dict[str, Any] = {name: merged.get(name) for name in feature_order}
    for k, v in merged.items():
        if k not in aligned:
            aligned[k] = v
    return aligned


def _extract_survival_probability(prediction: Dict[str, Any], score_direction: str) -> float:
    prob = prediction.get("predicted_probability")
    if prob is None:
        prob = prediction.get("risk_score")
    if prob is None:
        raise RecommendationServiceError(
            "REC_MODEL_OUTPUT_MISSING_PROBABILITY",
            "Model output did not include predicted_probability or risk_score",
        )
    p = float(prob)
    if p < 0.0 or p > 1.0:
        raise RecommendationServiceError(
            "REC_PROBABILITY_OUT_OF_RANGE",
            "Model probability output is outside the inclusive [0,1] range",
        )
    if score_direction == SCORE_DIRECTION_POSITIVE_IS_SURVIVAL:
        return p
    if score_direction == SCORE_DIRECTION_POSITIVE_IS_MORTALITY:
        return 1.0 - p
    raise RecommendationServiceError(
        "REC_UNKNOWN_SCORE_DIRECTION",
        f"Unknown score_direction: {score_direction}",
        context={"score_direction": score_direction},
    )


def run_survival_only_recommendation(
    *,
    model_id: str,
    patient_features: Dict[str, Any],
    observed_regimen: Optional[Dict[str, Any]],
    regimen_ids: Optional[List[str]],
    top_k: int,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(patient_features, dict) or not patient_features:
        raise RecommendationServiceError("REC_PATIENT_FEATURES_EMPTY", "patient_features cannot be empty")
    if top_k <= 0:
        raise RecommendationServiceError("REC_TOP_K_INVALID", "top_k must be a positive integer")

    validated = validate_survival_model(model_id)
    bundle = validated["schema_bundle"]
    score_direction = str(validated["score_direction"])
    feature_order = [str(x) for x in (bundle.get("feature_order") or []) if str(x).strip()]
    if not feature_order:
        raise RecommendationServiceError(
            "REC_FEATURE_ORDER_MISSING",
            "Model schema is missing canonical feature_order",
            context={"model_id": model_id},
        )

    repo = FileRegimenRepo()
    candidates = _select_candidate_regimens(repo, regimen_ids)

    observed_overlay = normalize_treatment_values(observed_regimen)
    observed_values = _build_aligned_candidate_values(patient_features, observed_overlay, feature_order)
    observed_pred = run_single_sample(
        model_id=model_id,
        values=observed_values,
        session_id=f"job:{job_id}:observed" if job_id else None,
        include_explanation=False,
    )
    observed_probability = _extract_survival_probability(observed_pred, score_direction)

    scored: List[Dict[str, Any]] = []
    for item in candidates:
        treatment_values = normalize_treatment_values(item.get("treatment_values"))
        candidate_values = _build_aligned_candidate_values(patient_features, treatment_values, feature_order)
        pred = run_single_sample(
            model_id=model_id,
            values=candidate_values,
            session_id=f"job:{job_id}:regimen:{item.get('regimen_id')}" if job_id else None,
            include_explanation=False,
        )
        prob = _extract_survival_probability(pred, score_direction)
        scored.append(
            {
                "regimen_id": str(item.get("regimen_id")),
                "regimen_name": str(item.get("regimen_name") or ""),
                "predicted_probability": prob,
                "treatment_values": dict(treatment_values),
            }
        )

    scored.sort(key=lambda x: float(x.get("predicted_probability") or 0.0), reverse=True)
    for i, row in enumerate(scored, start=1):
        row["rank"] = i

    top_candidates = scored[:top_k]
    top1 = top_candidates[0]
    result = {
        "task": "survival_only_recommendation",
        "mode": SURVIVAL_ONLY_MODE,
        "score_direction": score_direction,
        "model_id": model_id,
        "observed_regimen": observed_overlay if observed_regimen is not None else None,
        "observed_prediction_probability": observed_probability,
        "recommended_top1_regimen": {
            "regimen_id": top1["regimen_id"],
            "regimen_name": top1["regimen_name"],
            "rank": top1["rank"],
            "treatment_values": dict(top1.get("treatment_values") or {}),
        },
        "recommended_top1_probability": top1["predicted_probability"],
        "delta_probability_top1": float(top1["predicted_probability"]) - float(observed_probability),
        "top_candidates": top_candidates,
        "disclaimer": (
            "For research support only. Estimates reflect model output under fixed patient features "
            "and regimen-specific therapy fields; they are not treatment directives."
        ),
    }
    return result
