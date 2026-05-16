"""
Latest-training-summary MCP payload: reuse training_factual_core plus read_only_privacy projection instead of duplicating trimming rules.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.training.training_factual_core import (
    build_training_factual_bundle,
    select_latest_training_task_for_summary,
)
from backend.tools.read_only_privacy import (
    ReadonlyTruncateTracker,
    attach_truncated_marker,
    task_public_view,
)

_TRAINING_SUMMARY_KEYS = (
    "headline",
    "train_workflow_phase",
    "task_kind",
    "model_id",
    "model_registered",
    "model_id_draft",
    "primary_metric_requested",
    "feature_set_search_executed",
    "next_action",
    "filter_summary",
)

_ALLOWED_TASK_STATUS = frozenset({"completed", "running", "failed", "waiting_user", "queued"})


def _as_bool(v: Any) -> bool:
    if v is True:
        return True
    if v is False or v is None:
        return False
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "y")


def _normalize_job_type(raw: Optional[str]) -> Optional[str]:
    jt = str(raw or "").strip()
    if jt == "train_model":
        return "train"
    return jt or None


def _task_mcp_block(tp: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    if not tp:
        return {
            "id": None,
            "status": None,
            "job_type": None,
            "created_at": None,
            "completed_at": None,
        }
    st = str(tp.get("status") or "").strip() or None
    if st and st not in _ALLOWED_TASK_STATUS:
        st = None
    return {
        "id": str(tp.get("id") or "").strip() or None,
        "status": st,
        "job_type": _normalize_job_type(str(tp.get("job_type") or "").strip() or None),
        "created_at": str(tp.get("created_at") or "").strip() or None,
        "completed_at": str(tp.get("completed_at") or "").strip() or None,
    }


def _empty_training_summary_block() -> Dict[str, Any]:
    d: Dict[str, Any] = {k: None for k in _TRAINING_SUMMARY_KEYS}
    d["model_registered"] = False
    d["feature_set_search_executed"] = False
    return d


def _training_summary_block(public: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = _empty_training_summary_block()
    if not public or not isinstance(public, dict):
        return base
    for k in _TRAINING_SUMMARY_KEYS:
        if k not in public:
            continue
        v = public.get(k)
        if k in ("model_registered", "feature_set_search_executed"):
            base[k] = _as_bool(v)
        else:
            base[k] = v if v is None or isinstance(v, (str, int, float, bool)) else str(v)
    return base


def _build_summary_text(public: Optional[Dict[str, Any]]) -> Optional[str]:
    if not public or not isinstance(public, dict):
        return None
    parts = []
    h = public.get("headline")
    if isinstance(h, str) and h.strip():
        parts.append(h.strip())
    fs = public.get("filter_summary")
    if isinstance(fs, str) and fs.strip():
        parts.append(fs.strip())
    if not parts:
        return None
    raw = " — ".join(parts)
    if len(raw) > 800:
        return raw[:799] + "…"
    return raw


def build_latest_training_summary_mcp_result(task_repo: Any) -> Dict[str, Any]:  # noqa: ANN401
    """
    Uses the same source selection and factual core as read-only _get_latest_training_summary; emits the stable MCP schema.
    """
    task = select_latest_training_task_for_summary(task_repo)
    if not task:
        out_unavail: Dict[str, Any] = {
            "available": False,
            "task": _task_mcp_block(None),
            "training_summary": _empty_training_summary_block(),
            "key_metrics": {},
            "summary_text": None,
        }
        return out_unavail

    tracker = ReadonlyTruncateTracker()
    bundle = build_training_factual_bundle(task, tracker)
    public = bundle.get("public_summary") if isinstance(bundle.get("public_summary"), dict) else None
    tp = task_public_view(task)

    key_metrics: Dict[str, Any] = {}
    if public and isinstance(public.get("key_metrics"), dict):
        key_metrics = dict(public.get("key_metrics") or {})

    ts_block = _training_summary_block(public)

    out: Dict[str, Any] = {
        "available": True,
        "task": _task_mcp_block(tp),
        "training_summary": ts_block,
        "key_metrics": key_metrics,
        "summary_text": _build_summary_text(public),
    }
    attach_truncated_marker(out, tracker)
    return out
