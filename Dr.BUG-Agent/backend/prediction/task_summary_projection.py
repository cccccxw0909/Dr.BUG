from __future__ import annotations

from typing import Any, Dict, Optional

from backend.prediction import factual_core
from backend.prediction.prediction_factual_core import build_prediction_factual_bundle_from_task
from backend.tools.read_only_privacy import ReadonlyTruncateTracker


def _default_prediction_headline(result: Dict[str, Any], *, batch: bool) -> str:
    loc = str(result.get("ui_locale") or "").strip().lower()
    if loc.startswith("zh"):
        return "Batch prediction completed" if batch else "Prediction completed"
    return "Batch prediction complete" if batch else "Prediction complete"


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


def _single_http_display_lines_from_public(pub: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """single: rebuild HTTP display lines only from factual public data; do not reuse raw result_summary injected lines."""
    label = pub.get("predicted_label")
    line_label = str(label).strip() if label is not None and str(label).strip() != "" else None
    pn = _normalize_probability(pub.get("predicted_probability"))
    line_prob: Optional[str] = None
    if pn is not None:
        pct = round(pn * 100.0, 2)
        line_prob = f"{int(pct)}%" if pct == int(pct) else f"{pct}%"
    return line_label, line_prob


def build_batch_prediction_task_result_summary(
    result: Dict[str, Any],
    *,
    record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Write batch prediction task.result_summary, using prediction_type to distinguish it from the single-sample structure."""
    warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
    headline = str(result.get("summary_text") or "").strip() or _default_prediction_headline(result, batch=True)
    return {
        "task_kind": "predict_outcome",
        "headline": headline,
        "model_id": result.get("model_id"),
        "display_name": result.get("display_name"),
        "task_name": result.get("task_name"),
        "prediction_type": "batch",
        "total_rows": result.get("total_rows"),
        "succeeded_rows": result.get("succeeded_rows"),
        "failed_rows": result.get("failed_rows"),
        "timestamp": result.get("timestamp"),
        "history_record_id": record_id,
        "summary_text": str(result.get("summary_text") or ""),
        "download_url": result.get("download_url"),
        "file_name": result.get("file_name"),
        "warnings": [str(x) for x in warnings][:12],
    }


def build_prediction_task_result_summary(
    result: Dict[str, Any],
    *,
    record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize predict_outcome task.result_summary as the single-source projection."""
    p01 = _normalize_probability(result.get("predicted_probability"))
    label = result.get("predicted_label")
    prob_line = str(result.get("probability_display_line") or "").strip()
    label_line = str(result.get("label_display_line") or "").strip()
    explanation = result.get("explanation") if isinstance(result.get("explanation"), dict) else {}
    warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
    return {
        "task_kind": "predict_outcome",
        "headline": _default_prediction_headline(result, batch=False),
        "model_id": result.get("model_id"),
        "display_name": result.get("display_name"),
        "task_name": result.get("task_name"),
        "prediction_type": result.get("prediction_type"),
        "predicted_label": label,
        "predicted_probability": p01,
        "probability": p01,
        "predicted_value": result.get("predicted_value"),
        "risk_score": result.get("risk_score"),
        "probability_display_line": prob_line,
        "label_display_line": label_line,
        "outcome_display": result.get("outcome_display"),
        "label_display": result.get("label_display"),
        "timestamp": result.get("timestamp"),
        "history_record_id": record_id,
        "explanation_supported": bool(explanation.get("supported")),
        "summary_text": str(explanation.get("summary_text") or ""),
        "top_features": list(explanation.get("top_features") or []),
        "warnings": [str(x) for x in warnings][:12],
    }


def project_prediction_task_summary(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Unified prediction task summary view for HTTP task details and similar callers, preserving existing fields to avoid frontend breakage."""
    if str(task.get("job_type") or "") != "predict_outcome":
        return None
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    if not rs and not params:
        return None
    model_id = rs.get("model_id") or params.get("model_id")
    out: Dict[str, Any] = {
        "source": "predict_outcome_task",
        "job_id": task.get("id"),
        "status": task.get("status"),
        "completed_at": task.get("completed_at"),
        "model_id": model_id,
        "display_name": rs.get("display_name"),
        "task_name": rs.get("task_name"),
        "headline": rs.get("headline"),
        "prediction_type": rs.get("prediction_type"),
        "predicted_label": rs.get("predicted_label"),
        "predicted_probability": _normalize_probability(rs.get("predicted_probability") or rs.get("probability")),
        "predicted_value": rs.get("predicted_value"),
        "probability_display_line": rs.get("probability_display_line"),
        "label_display_line": rs.get("label_display_line"),
        "outcome_display": rs.get("outcome_display"),
        "label_display": rs.get("label_display"),
        "timestamp": rs.get("timestamp") or task.get("completed_at"),
        "history_record_id": rs.get("history_record_id"),
        "explanation_supported": bool(rs.get("explanation_supported")),
        "summary_text": rs.get("summary_text"),
        "top_features": rs.get("top_features") if isinstance(rs.get("top_features"), list) else [],
        "warnings": rs.get("warnings") if isinstance(rs.get("warnings"), list) else [],
        "public_payload_source": "task",
    }
    bundle = build_prediction_factual_bundle_from_task(task, ReadonlyTruncateTracker())
    if not bundle:
        out["label_display_line"] = None
        out["probability_display_line"] = None
        return out
    pub = bundle.get("public_summary") if isinstance(bundle.get("public_summary"), dict) else {}
    kind = str(pub.get("kind") or "")
    if kind == "single":
        out["predicted_label"] = pub.get("predicted_label")
        out["predicted_probability"] = pub.get("predicted_probability")
        out["explanation_supported"] = bool(pub.get("explanation_supported"))
        if pub.get("summary_text") is not None:
            out["summary_text"] = pub.get("summary_text")
        tn = str(pub.get("task_name") or "").strip()
        if tn and tn != "—":
            out["task_name"] = tn
        mn = str(pub.get("model_name") or "").strip()
        if mn and mn != "—":
            out["display_name"] = mn
        ld, pd = _single_http_display_lines_from_public(pub)
        out["label_display_line"] = ld
        out["probability_display_line"] = pd
        out["label_display"] = pub.get("predicted_label")
        out["outcome_display"] = None
    elif kind == "batch":
        if pub.get("summary_text") is not None:
            out["summary_text"] = pub.get("summary_text")
        out["total_rows"] = pub.get("total_rows")
        out["succeeded_rows"] = pub.get("succeeded_rows")
        out["failed_rows"] = pub.get("failed_rows")
        out["output_file_name"] = pub.get("output_file_name")
        tn = str(pub.get("task_name") or "").strip()
        if tn and tn != "—":
            out["task_name"] = tn
        mn = str(pub.get("model_name") or "").strip()
        if mn and mn != "—":
            out["display_name"] = mn
    return out


def project_prediction_task_summary_for_readonly_tools(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Read-only-tool only: same shape as factual_core and not used for HTTP task_summary."""
    if str(task.get("job_type") or "") != "predict_outcome":
        return None
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    if not rs and not params:
        return None
    source = dict(rs)
    source.setdefault("model_id", rs.get("model_id") or params.get("model_id"))
    source.setdefault("display_name", rs.get("display_name"))
    source.setdefault("task_name", rs.get("task_name"))
    if factual_core.is_batch_like_source(source):
        return factual_core.build_batch_prediction_readonly_summary(source, source_kind="task_result_summary")
    return factual_core.build_single_prediction_readonly_summary(source, source_kind="task_result_summary")
