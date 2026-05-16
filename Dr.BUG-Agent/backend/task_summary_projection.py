from __future__ import annotations

from typing import Any, Dict, Optional

from backend.prediction.task_summary_projection import project_prediction_task_summary
from backend.tools.read_only_privacy import ReadonlyTruncateTracker
from backend.training.training_factual_core import build_training_factual_bundle


def project_task_summary(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Shared summary projection layer for task details and read-only queries."""
    job_type = str(task.get("job_type") or "")
    if job_type == "predict_outcome":
        return project_prediction_task_summary(task)
    if job_type == "train_model":
        tracker = ReadonlyTruncateTracker()
        bundle = build_training_factual_bundle(task, tracker)
        training = bundle.get("public_summary")
        if not training:
            return None
        return {
            "source": "train_model_task",
            "job_id": task.get("id"),
            "status": task.get("status"),
            "completed_at": task.get("completed_at"),
            "training_summary": training,
        }
    return None
