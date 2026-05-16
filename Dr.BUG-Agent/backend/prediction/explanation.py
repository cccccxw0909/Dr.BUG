"""
Single-sample prediction explanation: reuses src.utils.shap_utils.compute_single_sample_shap and existing plotting logic.
Does not introduce a new inference engine; returns supported=False on failure for frontend fallback display.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.config import TASK_DIR
from backend.agent.chat_output_locale import is_english_output_locale

logger = logging.getLogger(__name__)

EXPLAIN_SUBDIR = "prediction_explain"


def _build_shap_row_dataframe(normalized_payload: Dict[str, Any], feature_order: List[str]) -> pd.DataFrame:
    row_values: List[float] = []
    for f in feature_order:
        v = normalized_payload.get(f)
        if v is None or v == "" or (isinstance(v, float) and np.isnan(v)):
            row_values.append(float("nan"))
        elif isinstance(v, (int, float)):
            row_values.append(float(v))
        else:
            try:
                row_values.append(float(v))
            except (TypeError, ValueError):
                row_values.append(float("nan"))
    X_row = pd.DataFrame([row_values], columns=feature_order)
    return X_row.reindex(columns=feature_order, fill_value=np.nan).astype(float)


def _path_under_task_dir_to_url(abs_path: Optional[str]) -> Optional[str]:
    if not abs_path:
        return None
    p = Path(abs_path)
    if not p.is_file():
        return None
    try:
        rel = p.resolve().relative_to(TASK_DIR.resolve())
    except ValueError:
        logger.debug("SHAP plot path not under TASK_DIR: %s", abs_path)
        return None
    return f"/static/{rel.as_posix()}"


def _shap_task_type(registry_task_type: str) -> str:
    if registry_task_type == "regression":
        return "regression"
    return "binary"


def rule_based_summary_en(top_pos: List[str], top_neg: List[str], prediction_type: str) -> str:
    """Rule-based English summary (non-LLM), aligned with rule_based_summary_cn."""
    ordered: List[str] = []
    for n in top_pos + top_neg:
        if n and n not in ordered:
            ordered.append(n)
        if len(ordered) >= 5:
            break
    if not ordered:
        return (
            "SHAP decomposition did not surface a single dominant driver for this row; contributions may be "
            "similar across features. (Local model approximation for research support only; not medical advice.)"
        )
    main_line = ", ".join(ordered[:5])
    parts = [f"This prediction is most influenced by: {main_line}. "]
    if prediction_type == "regression":
        if top_pos:
            parts.append(f"{', '.join(top_pos[:3])} push the prediction higher. ")
        if top_neg:
            parts.append(f"{', '.join(top_neg[:3])} push the prediction lower. ")
    else:
        if top_pos:
            parts.append(
                f"{', '.join(top_pos[:3])} push the output toward higher risk (or higher positive probability). "
            )
        if top_neg:
            parts.append(f"{', '.join(top_neg[:3])} act in a mitigating (or probability-lowering) direction. ")
    parts.append("(Explanation uses SHAP additive approximation for research support only; not medical advice.)")
    return " ".join(parts)


def rule_based_summary_cn(top_pos: List[str], top_neg: List[str], prediction_type: str) -> str:
    """Rule-based English summary (non-LLM) combining positive and negative driver features."""
    ordered: List[str] = []
    for n in top_pos + top_neg:
        if n and n not in ordered:
            ordered.append(n)
        if len(ordered) >= 5:
            break
    if not ordered:
        return (
            "The SHAP decomposition for this sample did not identify a single dominant feature; variable contributions may be similar. "
            "This local model explanation is for research support only and is not medical advice."
        )
    main_line = ", ".join(ordered[:5])
    parts = [f"This prediction is primarily influenced by the following features: {main_line}."]
    if prediction_type == "regression":
        if top_pos:
            parts.append(f"{', '.join(top_pos[:3])} move the predicted value higher.")
        if top_neg:
            parts.append(f"{', '.join(top_neg[:3])} move the predicted value lower.")
    else:
        if top_pos:
            parts.append(f"{', '.join(top_pos[:3])} move the output toward higher risk or positive probability.")
        if top_neg:
            parts.append(f"{', '.join(top_neg[:3])} move the output toward lower risk or lower probability.")
    parts.append("This explanation is based on an additive SHAP approximation and is for research support only; it is not medical advice.")
    return " ".join(parts)


def _user_facing_shap_error(err: str, *, locale: Optional[str] = None) -> str:
    low = err.lower()
    en = is_english_output_locale(locale)
    if "shap not installed" in low or "no module named 'shap'" in low:
        return (
            "SHAP is not installed in this runtime; single-sample explanation is unavailable."
            if en
            else "SHAP is not installed in the current environment; single-sample explanation is unavailable."
        )
    if "only supported for tree" in low or "tree models" in low:
        return (
            "This model type does not support single-sample SHAP (tree models required)."
            if en
            else "The current model type does not support single-sample SHAP; a tree model is required."
        )
    if "shap computation failed" in low or "treeexplainer" in low:
        logger.debug("SHAP computation diagnostic (not shown to user): %s", err)
        return (
            "SHAP computation failed for this sample; check server logs if needed."
            if en
            else "SHAP computation failed; check server logs for details."
        )
    logger.debug("SHAP error raw (not shown to user): %s", err)
    return (
        "Single-sample SHAP explanation is unavailable; check server logs if needed."
        if en
        else "Single-sample SHAP explanation is unavailable; check server logs for details."
    )


def compute_and_format_explanation(
    pipe: Any,
    normalized_payload: Dict[str, Any],
    feature_order: List[str],
    registry_task_type: str,
    prediction_type_frontend: str,
    *,
    output_locale: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call compute_single_sample_shap, convert artifact paths to /static/... URLs, and generate a rule-based summary.
    """
    from backend.ml_runtime.utils.shap_utils import compute_single_sample_shap

    explain_id = uuid.uuid4().hex
    save_dir = TASK_DIR / EXPLAIN_SUBDIR / explain_id
    save_dir.mkdir(parents=True, exist_ok=True)

    X_row = _build_shap_row_dataframe(normalized_payload, feature_order)
    shap_res = compute_single_sample_shap(
        pipe,
        X_row,
        task_type=_shap_task_type(registry_task_type or "binary"),
        feature_names=feature_order,
        save_dir=save_dir,
        top_n=10,
    )

    err = shap_res.get("error")
    top_pos = [str(x) for x in (shap_res.get("top_positive_drivers") or [])]
    top_neg = [str(x) for x in (shap_res.get("top_negative_drivers") or [])]

    top_features: List[Dict[str, str]] = []
    for n in top_pos[:5]:
        top_features.append({"name": n, "direction": "increase"})
    for n in top_neg[:5]:
        if len(top_features) >= 5:
            break
        top_features.append({"name": n, "direction": "decrease"})

    warnings: List[str] = []

    if err:
        warnings.append(_user_facing_shap_error(str(err), locale=output_locale))
        return {
            "supported": False,
            "summary_text": "",
            "top_features": [],
            "waterfall_image_url": None,
            "force_image_url": None,
            "warnings": warnings,
        }

    wf_url = _path_under_task_dir_to_url(shap_res.get("waterfall_plot_path"))
    force_url = _path_under_task_dir_to_url(shap_res.get("force_plot_path"))

    if not wf_url and not force_url:
        warnings.append(
            "SHAP ran, but plot export failed (check server logs)."
            if is_english_output_locale(output_locale)
            else "SHAP was computed, but plot export failed; check server logs."
        )

    summary_text = (
        rule_based_summary_en(top_pos, top_neg, prediction_type_frontend)
        if is_english_output_locale(output_locale)
        else rule_based_summary_cn(top_pos, top_neg, prediction_type_frontend)
    )

    return {
        "supported": True,
        "summary_text": summary_text,
        "top_features": top_features,
        "waterfall_image_url": wf_url,
        "force_image_url": force_url,
        "warnings": warnings,
    }
