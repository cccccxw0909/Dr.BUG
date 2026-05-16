"""Register synchronous HTTP predictions (single-sample / batch) in task_repo to align with GET /tasks management.

Prediction/report history uses prediction_history (index + records). Previously, single and batch prediction APIs only wrote to that repository
and did not create task.json, so task management lists were missing entries. This module appends a completed predict_outcome task after history archiving.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.runtime import task_repo
from backend.schemas.task import JobType, TaskStatus
from backend.utils.time_utils import now_iso


def register_completed_single_prediction_task(
    result: Dict[str, Any],
    *,
    history_record_id: str,
    session_id: Optional[str] = None,
) -> str:
    from backend.prediction.task_summary_projection import build_prediction_task_result_summary

    task = task_repo.create(
        JobType.predict_outcome,
        params={
            "model_id": str(result.get("model_id") or ""),
            "prediction_mode": "single",
            "history_record_id": history_record_id,
            "session_id": session_id,
        },
    )
    job_id = str(task["id"])
    ts = str(result.get("timestamp") or now_iso())
    summary = build_prediction_task_result_summary(result, record_id=history_record_id)
    task_repo.update(
        job_id,
        status=TaskStatus.completed.value,
        progress=100,
        current_stage="completed",
        message="Prediction completed",
        started_at=ts,
        completed_at=ts,
        result_summary=summary,
    )
    task_repo.append_log(job_id, f"Single-sample prediction completed; history record {history_record_id}")
    return job_id


def register_completed_batch_prediction_task(
    result: Dict[str, Any],
    *,
    history_record_id: str,
    session_id: Optional[str] = None,
) -> str:
    from backend.prediction.task_summary_projection import build_batch_prediction_task_result_summary

    task = task_repo.create(
        JobType.predict_outcome,
        params={
            "model_id": str(result.get("model_id") or ""),
            "prediction_mode": "batch",
            "history_record_id": history_record_id,
            "session_id": session_id,
        },
    )
    job_id = str(task["id"])
    ts = str(result.get("timestamp") or now_iso())
    summary = build_batch_prediction_task_result_summary(result, record_id=history_record_id)
    task_repo.update(
        job_id,
        status=TaskStatus.completed.value,
        progress=100,
        current_stage="completed",
        message="Batch prediction completed",
        started_at=ts,
        completed_at=ts,
        result_summary=summary,
    )
    task_repo.append_log(job_id, f"Batch prediction completed; history record {history_record_id}")
    return job_id
