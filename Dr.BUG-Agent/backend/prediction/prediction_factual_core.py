"""
Prediction read-only factual-core facade: task-selection semantics plus public_summary and evidence,
aligned with factual_core.build_* projections for shared use by read-only tools, dialogue composition, and task summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.prediction import factual_core
from backend.prediction import history_service
from backend.prediction.factual_core import SourceKind
from backend.schemas.task import JobType
from backend.tools.read_only_privacy import ReadonlyTruncateTracker


def _task_recency_key(t: Dict[str, Any]) -> str:
    return str(t.get("completed_at") or t.get("started_at") or t.get("created_at") or "")


def select_latest_predict_outcome_task_row(task_repo: Any) -> Optional[Dict[str, Any]]:
    """
    Latest prediction task selection, symmetrical with training factual selection:
    - job_type=predict_outcome only
    - If completed tasks exist, choose the most recent one within the completed subset.
    - Otherwise fall back to the most recent task across all prediction tasks.
    """
    rows: List[Dict[str, Any]] = task_repo.list(job_type=JobType.predict_outcome.value)
    if not rows:
        return None
    completed = [t for t in rows if str(t.get("status") or "") == "completed"]
    pool = completed if completed else rows
    try:
        return max(pool, key=_task_recency_key)
    except ValueError:
        return None


# Explicit alias: layer A only identifies which predict_outcome task row is latest in the repository.
select_latest_prediction_task = select_latest_predict_outcome_task_row


def _task_has_readonly_usable_payload(task: Optional[Dict[str, Any]]) -> bool:
    if not task:
        return False
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    return bool(rs or params)


def merge_task_result_summary(task: Dict[str, Any]) -> Dict[str, Any]:
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    return dict(rs)


def _build_evidence(
    public: Dict[str, Any],
    raw: Dict[str, Any],
    *,
    task_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    st = str(task_row.get("status") or "") if task_row else ""
    kind = str(public.get("kind") or "")
    is_batch = kind == "batch"
    has_prob_single = not is_batch and public.get("predicted_probability") is not None
    has_label_single = (
        not is_batch
        and public.get("predicted_label") is not None
        and str(public.get("predicted_label")).strip() != ""
    )
    summary_text = str(public.get("summary_text") or "").strip()
    expl_sup = bool(public.get("explanation_supported"))
    return {
        "task_status": st,
        "has_completed_prediction_task": st == "completed",
        "has_public_summary": bool(public),
        "has_probability": bool(has_prob_single),
        "has_label": bool(has_label_single),
        "has_summary_text": bool(summary_text),
        "has_explanation": bool(expl_sup),
        "is_batch_prediction": is_batch,
        "risk_claimable": bool(has_prob_single and has_label_single),
        "label_claimable": bool(has_label_single),
        "probability_claimable": bool(has_prob_single),
    }


def build_prediction_factual_bundle_from_task(
    task: Dict[str, Any],
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Optional[Dict[str, Any]]:
    """Build the factual core from a predict_outcome task row for dialogue and task-summary projections."""
    if str(task.get("job_type") or "") != JobType.predict_outcome.value:
        return None
    if not _task_has_readonly_usable_payload(task):
        return None
    raw = merge_task_result_summary(task)
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    raw.setdefault("model_id", raw.get("model_id") or params.get("model_id"))
    raw.setdefault("display_name", raw.get("display_name"))
    raw.setdefault("task_name", raw.get("task_name"))
    sk: Any = "task_result_summary"
    if factual_core.is_batch_like_source(raw):
        public = factual_core.build_batch_prediction_readonly_summary(raw, source_kind=sk, tracker=tracker)
    else:
        public = factual_core.build_single_prediction_readonly_summary(raw, source_kind=sk, tracker=tracker)
    evidence = _build_evidence(public, raw, task_row=task)
    return {"public_summary": public, "evidence": evidence}


def build_prediction_tool_payload(
    raw: Dict[str, Any],
    *,
    source_kind: SourceKind,
    task_row: Optional[Dict[str, Any]],
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Dict[str, Any]:
    """Read-only tool: add source/job_id and evidence to the factual_core projection."""
    sk: SourceKind = source_kind
    if factual_core.is_batch_like_source(raw):
        public = factual_core.build_batch_prediction_readonly_summary(raw, source_kind=sk, tracker=tracker)
    else:
        public = factual_core.build_single_prediction_readonly_summary(raw, source_kind=sk, tracker=tracker)
    if task_row is not None:
        public = dict(public)
        public["source"] = "predict_outcome_task"
        public["job_id"] = task_row.get("id")
    evidence = _build_evidence(public, raw, task_row=task_row)
    return {"public_summary": public, "evidence": evidence}


LatestPayloadSource = Literal["task", "history", "none"]


@dataclass
class LatestPredictionResolution:
    """
    Layer B: after layer A selects latest_task_row, identify the payload actually used by the read-only summary.

    - latest_task_row: always the result of select_latest_prediction_task, possibly None.
    - payload_source: whether the raw payload merged into factual data comes from the task row or history
    - task_row: non-None means public data can attach job_id, sharing source with task_result_summary
    """

    raw: Dict[str, Any]
    source_kind: SourceKind
    payload_source: LatestPayloadSource
    latest_task_row: Optional[Dict[str, Any]]
    task_row: Optional[Dict[str, Any]] = None


def resolve_latest_prediction_payload_source(task_repo: Any) -> Optional[LatestPredictionResolution]:
    """
    Layer B single entry point: decide whether the latest prediction payload comes from task_merged_result or history.

    Rules, aligned with read-only tools and kept explicit for tests:
    1) First take latest_task_row = select_latest_prediction_task, preferring the completed pool and otherwise max recency across the full pool.
    2) If there is no history index: use the readable task payload when available, otherwise no result.
    3) If history exists: read record_id from the index head and fetch the full history record; use record.timestamp, falling back to index-head timestamp.
    4) If record_id exists but fetch fails and the task is readable, fall back to task.
    5) If task is readable and task_time >= history_time (same fallback rules; empty string when no rid), use task.
    6) Otherwise, if a history record exists, use history.
    7) Otherwise, if task is readable, use task.
    8) Otherwise, build a minimal synthetic dict from the index head and mark it as history, without row-level details.
    """
    latest_task = select_latest_prediction_task(task_repo)
    task_readonly = _task_has_readonly_usable_payload(latest_task)

    task_time = ""
    if latest_task:
        task_time = str(
            latest_task.get("completed_at")
            or latest_task.get("started_at")
            or latest_task.get("created_at")
            or ""
        )

    idx = history_service.list_prediction_history()
    if not idx:
        if task_readonly and latest_task:
            merged = merge_task_result_summary(latest_task)
            return LatestPredictionResolution(
                merged,
                "task_result_summary",
                "task",
                latest_task,
                latest_task,
            )
        return None

    head = idx[0]
    rid = str(head.get("record_id") or "").strip()
    history_time = str(head.get("timestamp") or "")

    rec: Optional[Dict[str, Any]] = None
    rec_time = history_time
    if rid:
        got = history_service.get_prediction_history_record(rid)
        if isinstance(got, dict):
            rec = got
            rec_time = str(rec.get("timestamp") or history_time)

    if rid and rec is None and latest_task and task_readonly:
        merged = merge_task_result_summary(latest_task)
        return LatestPredictionResolution(
            merged,
            "task_result_summary",
            "task",
            latest_task,
            latest_task,
        )

    if latest_task and task_readonly and task_time and (not rid or task_time >= rec_time):
        merged = merge_task_result_summary(latest_task)
        return LatestPredictionResolution(
            merged,
            "task_result_summary",
            "task",
            latest_task,
            latest_task,
        )

    if rec is not None:
        return LatestPredictionResolution(
            dict(rec),
            "history_record",
            "history",
            latest_task,
            None,
        )

    if latest_task and task_readonly:
        merged = merge_task_result_summary(latest_task)
        return LatestPredictionResolution(
            merged,
            "task_result_summary",
            "task",
            latest_task,
            latest_task,
        )

    synthetic = {
        "type": str(head.get("type") or "single"),
        "task_name": head.get("task_name"),
        "model_id": head.get("model_id"),
        "display_name": head.get("display_name"),
        "summary_text": str(head.get("summary") or ""),
    }
    return LatestPredictionResolution(
        synthetic,
        "history_record",
        "history",
        latest_task,
        None,
    )


def resolve_latest_prediction_sources(task_repo: Any) -> Optional[LatestPredictionResolution]:
    """Compatibility name equivalent to resolve_latest_prediction_payload_source."""
    return resolve_latest_prediction_payload_source(task_repo)
