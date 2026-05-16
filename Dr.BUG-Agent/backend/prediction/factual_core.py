"""
Prediction read-only factual core: centralizes whitelist trimming for history records, task result_summary, and read-only tools.
Do not expose PHI, full results, per-feature inputs, full field_check data, download URLs, or SHAP URLs to the LLM.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from backend.tools.read_only_privacy import (
    MAX_SUMMARY_TEXT_LEN,
    MAX_TOP_FEATURES_COUNT,
    ReadonlyTruncateTracker,
    clip_str,
)

SourceKind = Literal["history_record", "task_result_summary"]

# Maximum drivers per side, coordinated with MAX_TOP_FEATURES_COUNT.
MAX_DRIVERS_PER_SIDE = 5

_NEXT_SINGLE = "Review details in Recent predictions, or use the unified prediction entry to start a new single-sample or batch prediction."
_NEXT_BATCH = "Download and review the result file in the workbench; use the unified prediction entry for single-case review if needed."
_UNAVAILABLE_EXPLANATION = "No explanation is currently available"


def _normalize_probability(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n > 1:
        n = n / 100.0
    if n < 0 or n > 1:
        return None
    return n


def _classify_direction(direction: Any) -> Optional[str]:
    """Return positive / negative; return None when unknown so the caller can place it in the positive list."""
    s = str(direction or "").strip().lower()
    if not s:
        return None
    if s in ("increase", "positive", "up", "pos"):
        return "positive"
    if s in ("decrease", "negative", "down", "neg"):
        return "negative"
    if "positive" in s and "contribution" in s:
        return "positive"
    if "negative" in s and "contribution" in s:
        return "negative"
    if "positive" in s:
        return "positive"
    if "negative" in s:
        return "negative"
    return None


def _split_top_features(raw: Any, tracker: Optional[ReadonlyTruncateTracker]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fixed rule: split by direction when present; otherwise put all drivers in positive and leave negative empty."""
    pos: List[Dict[str, Any]] = []
    neg: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return pos, neg
    for item in raw[: MAX_TOP_FEATURES_COUNT * 2]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        nm = clip_str(str(name), 120, "driver.name", tracker)
        direction = _classify_direction(item.get("direction"))
        contrib = item.get("contribution_text") or item.get("summary")
        ctext = ""
        if contrib is not None:
            ctext = clip_str(str(contrib), 200, "driver.contribution_text", tracker)
        cell: Dict[str, Any] = {"name": nm}
        if direction:
            cell["direction"] = direction
        if ctext:
            cell["contribution_text"] = ctext
        if direction == "negative":
            neg.append(cell)
        else:
            pos.append(cell)
    # Directionless items are currently in pos, satisfying the rule that unknown direction goes only to positive.
    return pos[:MAX_DRIVERS_PER_SIDE], neg[:MAX_DRIVERS_PER_SIDE]


def _extract_top_features_source(source: Dict[str, Any]) -> Any:
    expl = source.get("explanation")
    if isinstance(expl, dict) and expl.get("top_features"):
        return expl.get("top_features")
    return source.get("top_features")


def _safe_batch_summary_text(source: Dict[str, Any], tracker: Optional[ReadonlyTruncateTracker]) -> str:
    st = source.get("summary_text")
    if st is not None and str(st).strip():
        return clip_str(str(st).strip(), MAX_SUMMARY_TEXT_LEN, "batch.summary_text", tracker)
    inner = source.get("result")
    if isinstance(inner, dict):
        inner_st = inner.get("summary_text")
        if inner_st is not None and str(inner_st).strip():
            return clip_str(str(inner_st).strip(), MAX_SUMMARY_TEXT_LEN, "batch.result.summary_text", tracker)
    return ""


def _output_file_name_only(source: Dict[str, Any], tracker: Optional[ReadonlyTruncateTracker]) -> str:
    raw = str(source.get("file_name") or "").strip()
    if not raw:
        return ""
    base = os.path.basename(raw.replace("\\", "/"))
    return clip_str(base, 240, "batch.output_file_name", tracker)


def build_single_prediction_readonly_summary(
    source: Dict[str, Any],
    *,
    source_kind: SourceKind,
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Dict[str, Any]:
    task_name = clip_str(str(source.get("task_name") or ""), 400, "single.task_name", tracker)
    model_name = clip_str(
        str(source.get("display_name") or source.get("model_id") or ""),
        400,
        "single.model_name",
        tracker,
    )
    label = source.get("predicted_label")
    prob = _normalize_probability(source.get("predicted_probability") or source.get("probability"))
    expl_sup = bool(source.get("explanation_supported"))
    raw_tf = _extract_top_features_source(source)
    pos, neg = _split_top_features(raw_tf, tracker)
    summary_raw = str(source.get("summary_text") or "")
    if not summary_raw.strip() and isinstance(source.get("explanation"), dict):
        summary_raw = str(source["explanation"].get("summary_text") or "")
    summary_text = clip_str(summary_raw.strip(), MAX_SUMMARY_TEXT_LEN, "single.summary_text", tracker)
    return {
        "kind": "single",
        "task_name": task_name or "—",
        "model_name": model_name or "—",
        "predicted_label": label,
        "predicted_probability": prob,
        "explanation_supported": expl_sup,
        "top_positive_drivers": pos,
        "top_negative_drivers": neg,
        "summary_text": summary_text,
        "next_action_hint": _NEXT_SINGLE,
    }


def build_batch_prediction_readonly_summary(
    source: Dict[str, Any],
    *,
    source_kind: SourceKind,
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Dict[str, Any]:
    task_name = clip_str(str(source.get("task_name") or ""), 400, "batch.task_name", tracker)
    model_name = clip_str(
        str(source.get("display_name") or source.get("model_id") or ""),
        400,
        "batch.model_name",
        tracker,
    )
    tr = int(source.get("total_rows") or 0)
    sr = int(source.get("succeeded_rows") or 0)
    fr = int(source.get("failed_rows") or 0)
    summary_text = _safe_batch_summary_text(source, tracker)
    if not summary_text.strip():
        summary_text = clip_str(f"Total {tr} rows: {sr} succeeded, {fr} failed.", 200, "batch.summary_text.fallback", tracker)
    return {
        "kind": "batch",
        "task_name": task_name or "—",
        "model_name": model_name or "—",
        "total_rows": tr,
        "succeeded_rows": sr,
        "failed_rows": fr,
        "output_file_name": _output_file_name_only(source, tracker),
        "summary_text": summary_text,
        "next_action_hint": _NEXT_BATCH,
    }


def build_explanation_readonly_summary(
    source: Dict[str, Any],
    *,
    source_kind: SourceKind,
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Dict[str, Any]:
    """Explanation summary: use a fixed fallback when not single-sample or when explanation is unavailable."""
    if str(source.get("type") or "") == "batch":
        return {
            "kind": "explanation",
            "explanation_available": False,
            "explanation_summary_text": _UNAVAILABLE_EXPLANATION,
            "top_positive_drivers": [],
            "top_negative_drivers": [],
        }
    expl = source.get("explanation") if isinstance(source.get("explanation"), dict) else None
    expl_sup = bool(source.get("explanation_supported"))
    if expl and expl.get("supported") is not None:
        expl_sup = bool(expl.get("supported"))
    summary_raw = str(source.get("summary_text") or "")
    if not summary_raw.strip() and expl:
        summary_raw = str(expl.get("summary_text") or "")
    summary_stripped = summary_raw.strip()
    raw_tf = _extract_top_features_source(source)
    has_tf = isinstance(raw_tf, list) and any(isinstance(x, dict) and x.get("name") for x in raw_tf)
    available = str(source.get("type") or "single") == "single" and expl_sup and (bool(summary_stripped) or has_tf)
    if not available:
        return {
            "kind": "explanation",
            "explanation_available": False,
            "explanation_summary_text": _UNAVAILABLE_EXPLANATION,
            "top_positive_drivers": [],
            "top_negative_drivers": [],
        }
    pos, neg = _split_top_features(raw_tf, tracker)
    text = clip_str(summary_stripped, MAX_SUMMARY_TEXT_LEN, "explanation.summary_text", tracker)
    return {
        "kind": "explanation",
        "explanation_available": True,
        "explanation_summary_text": text,
        "top_positive_drivers": pos,
        "top_negative_drivers": neg,
    }


def is_batch_like_source(source: Dict[str, Any]) -> bool:
    """Determine batch mode from explicit type, compatible with task result_summary prediction_type=batch."""
    if str(source.get("type") or "") == "batch":
        return True
    if str(source.get("prediction_type") or "").strip().lower() == "batch":
        return True
    return False
