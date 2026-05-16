"""Single-sample inference: reuses PredictionAgent + ModelRegistry without Streamlit dependencies."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import math

from backend.ml_runtime.agents.prediction import PredictionAgent
from backend.ml_runtime.core.prediction_context import PredictionContext
from backend.ml_runtime.core.model_registry import ModelRegistry

from backend.config import MODEL_REGISTRY_PATH
from backend.agent.chat_output_locale import is_english_output_locale
from backend.prediction.binary_outcome_semantics import build_binary_classification_display
from backend.prediction.explanation import compute_and_format_explanation
from backend.prediction.service import get_model_schema_bundle, resolve_prediction_display_name
from backend.runtime import model_repo

logger = logging.getLogger(__name__)


def _inf_msg(locale: Optional[str], zh: str, en: str) -> str:
    return en if is_english_output_locale(locale) else zh


def _registry() -> ModelRegistry:
    return ModelRegistry(MODEL_REGISTRY_PATH)


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


def _validate_inputs(
    model_id: str, values: Dict[str, Any], locale: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Return (fields, error_messages). Inference should not continue if any error is present.
    """
    bundle = get_model_schema_bundle(model_id)
    if bundle is None:
        return [], [_inf_msg(locale, "Model not found or not registered", "Model not found or not registered")]
    fields: List[Dict[str, Any]] = bundle.get("fields") or []
    errs: List[str] = []
    order = bundle.get("feature_order") or []
    if not order:
        errs.append(_inf_msg(locale, "Model has no feature order configured", "Model has no feature order configured"))
    any_filled = False
    for f in fields:
        name = f.get("name")
        if not name:
            continue
        raw = values.get(name)
        empty = not _non_empty(raw)
        if not empty:
            any_filled = True
        if f.get("required") and empty:
            label = f.get("label") or name
            errs.append(
                _inf_msg(locale, f"Required field “{label}” is empty", f"Required field “{label}” is empty")
            )
    if not any_filled:
        errs.append(_inf_msg(locale, "The form is empty; cannot run prediction", "The form is empty; cannot run prediction"))
    # Simple type recheck aligned with the frontend.
    for f in fields:
        name = f.get("name")
        if not name:
            continue
        raw = values.get(name)
        if not _non_empty(raw):
            continue
        ft = str(f.get("type") or "float")
        label = f.get("label") or name
        if ft in ("float", "int"):
            try:
                x = float(raw)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                errs.append(_inf_msg(locale, f"Field “{label}” has invalid format", f"Field “{label}” has invalid format"))
                continue
            if ft == "int" and abs(x - round(x)) > 1e-9:
                errs.append(_inf_msg(locale, f"Field “{label}” must be an integer", f"Field “{label}” must be an integer"))
        opts = f.get("options")
        if ft in ("categorical", "binary") and isinstance(opts, list) and opts:
            if str(raw) not in [str(o) for o in opts]:
                errs.append(
                    _inf_msg(locale, f"Field “{label}” has an invalid option", f"Field “{label}” has an invalid option")
                )
    return fields, errs


def run_single_sample(
    model_id: str,
    values: Dict[str, Any],
    session_id: Optional[str] = None,
    include_explanation: bool = True,
    ui_locale: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a single-sample prediction. On success, return the frontend contract shape; on validation failure, raise ValueError with merged messages.
    """
    mid = (model_id or "").strip()
    if not mid:
        raise ValueError(_inf_msg(ui_locale, "model_id is required", "model_id is required"))

    _fields, val_errs = _validate_inputs(mid, values, ui_locale)
    if val_errs:
        if len(val_errs) == 1:
            raise ValueError(val_errs[0])
        raise ValueError(
            _inf_msg(
                ui_locale,
                f"{len(val_errs)} validation items still failed; correct the form first.",
                f"{len(val_errs)} validation issues remain; fix the form and retry.",
            )
        )

    reg = _registry()
    entry = reg.get(mid)
    if entry is None:
        raise ValueError(_inf_msg(ui_locale, "Model not found or not registered", "Model not found or not registered"))

    order = list(entry.feature_order or entry.required_features or [])
    filled_non_empty = sum(1 for n in order if _non_empty(values.get(n)))
    if len(order) >= 4:
        min_need = max(3, int(round(len(order) * 0.5)))
        if filled_non_empty < min_need:
            raise ValueError(
                _inf_msg(
                    ui_locale,
                    f"Too few patient features are filled ({filled_non_empty}/{len(order)}); complete most fields before prediction.",
                    f"Too few patient features have been completed ({filled_non_empty}/{len(order)}). "
                    "Please complete most required fields before running prediction.",
                )
            )

    ctx = PredictionContext(
        prediction_task=entry.task_name or "",
        model_id=mid,
        task_type=entry.task_type,
        required_features=list(entry.required_features or order),
        input_source="manual",
        raw_input_payload=dict(values),
    )

    PredictionAgent().run(ctx, reg)

    if ctx.error:
        raw_detail = str(ctx.error).strip().split("\n")[0]
        logger.warning(
            "prediction pipeline failed model_id=%s detail=%s",
            mid,
            raw_detail,
        )
        raise ValueError(
            _inf_msg(
                ui_locale,
                "Prediction could not be completed (prediction_pipeline_error). Check server logs or retry later.",
                "Prediction could not complete (prediction_pipeline_error). Check server logs or retry later.",
            )
        )

    norm = ctx.normalized_input_payload or {}
    warnings: List[str] = []
    for name in order:
        v = norm.get(name)
        if v is None or v == "":
            warnings.append(
                _inf_msg(
                    ui_locale,
                    f"Feature “{name}” is missing and was handled by the model workflow",
                    f"Feature “{name}” is missing; handled per model pipeline",
                )
            )
    if len(warnings) > 12:
        extra = len(warnings) - 12
        warnings = warnings[:12]
        warnings.append(
            _inf_msg(ui_locale, f"{extra} additional missing-feature notes omitted", f"{extra} additional missing-feature notes omitted")
        )

    probs = ctx.prediction_metadata.get("probabilities") if isinstance(ctx.prediction_metadata, dict) else None
    task_type = entry.task_type
    pred_type = "regression" if task_type == "regression" else "classification"

    predicted_probability: Optional[float] = None
    predicted_value: Optional[float] = None
    if task_type == "regression":
        predicted_value = float(ctx.risk_score) if ctx.risk_score is not None else None
    elif task_type == "binary" and isinstance(probs, list) and len(probs) >= 2:
        predicted_probability = float(probs[1])
    elif task_type == "multiclass" and isinstance(probs, list) and probs:
        predicted_probability = float(max(float(x) for x in probs))

    if predicted_probability is None and task_type == "binary" and ctx.risk_score is not None:
        predicted_probability = float(ctx.risk_score)

    label_display = str(ctx.predicted_label or "—")
    outcome_display = label_display
    predicted_label_out: Optional[str] = ctx.predicted_label
    if pred_type == "regression":
        pv = predicted_value
        prob_line = f"Model output: {pv:.4f}" if pv is not None else "Model output: —"
        label_line_clinical = "Regression (continuous outcome)"
    else:
        bundle = get_model_schema_bundle(mid) or {}
        meta: Dict[str, Any] = dict(model_repo.get(mid) or {})
        if isinstance(bundle.get("metadata"), dict):
            meta = {**meta, **bundle["metadata"]}
        clinical = build_binary_classification_display(
            model_id=mid,
            task_name=str(entry.task_name or ""),
            task_type=str(entry.task_type or "binary"),
            model_meta=meta,
            schema_bundle=bundle,
            raw_label=label_display,
            predicted_probability=predicted_probability,
            risk_score=float(ctx.risk_score) if ctx.risk_score is not None else None,
        )
        prob_line = clinical.probability_display_line
        label_line_clinical = clinical.label_display_line
        if clinical.predicted_label is not None:
            predicted_label_out = clinical.predicted_label
            label_display = clinical.label_display or clinical.predicted_label
            outcome_display = clinical.outcome_display or clinical.predicted_label

    feature_values_used: Dict[str, Any] = {}
    for name in order:
        feature_values_used[name] = norm.get(name)

    ts = datetime.now(timezone.utc).isoformat()

    out: Dict[str, Any] = {
        "ok": True,
        "ui_locale": "en" if is_english_output_locale(ui_locale) else "zh",
        "model_id": mid,
        "display_name": resolve_prediction_display_name(mid, entry),
        "task_name": entry.task_name or "",
        "prediction_type": pred_type,
        "predicted_label": predicted_label_out,
        "predicted_probability": predicted_probability,
        "predicted_value": predicted_value,
        "label_display": label_display,
        "outcome_display": outcome_display,
        "probability_display_line": prob_line,
        "label_display_line": label_line_clinical,
        "feature_values_used": feature_values_used,
        "warnings": warnings,
        "timestamp": ts,
        "session_id": session_id,
        "risk_score": float(ctx.risk_score) if ctx.risk_score is not None else None,
    }

    if include_explanation:
        try:
            pipe = getattr(ctx, "loaded_pipeline", None)
            if pipe is not None and norm and order:
                out["explanation"] = compute_and_format_explanation(
                    pipe,
                    norm,
                    order,
                    str(entry.task_type or "binary"),
                    pred_type,
                    output_locale=ui_locale,
                )
            else:
                out["explanation"] = {
                    "supported": False,
                    "summary_text": "",
                    "top_features": [],
                    "waterfall_image_url": None,
                    "force_image_url": None,
                    "warnings": [
                        _inf_msg(
                            ui_locale,
                            "Prediction context has no loaded model; skipping single-sample explanation.",
                            "Loaded model missing in prediction context; skipping single-sample explanation.",
                        )
                    ],
                }
        except Exception as exc:
            logger.exception("single-sample SHAP explanation failed after successful prediction")
            out["explanation"] = {
                "supported": False,
                "summary_text": "",
                "top_features": [],
                "waterfall_image_url": None,
                "force_image_url": None,
                "warnings": [
                    _inf_msg(
                        ui_locale,
                        "Explanation generation failed for this request (explanation_generation_error). Check server logs.",
                        "Explanation generation failed (explanation_generation_error). Check server logs.",
                    )
                ],
            }
    else:
        out["explanation"] = {
            "supported": False,
            "summary_text": "",
            "top_features": [],
            "waterfall_image_url": None,
            "force_image_url": None,
            "warnings": [
                _inf_msg(
                    ui_locale,
                    "Single-sample SHAP explanation is disabled for batch prediction to preserve execution efficiency.",
                    "SHAP explanation is disabled for this run.",
                )
            ],
        }

    return out
