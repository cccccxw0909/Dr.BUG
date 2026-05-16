from __future__ import annotations

from backend.runtime import executor, task_repo
from backend.utils.time_utils import now_iso
from backend.workers.job_runner import (
    run_prediction_job,
    run_recommendation_job,
    run_report_job,
    run_training_job,
)


def submit_job(job_type: str, job_id: str) -> None:
    if job_type == "train_model":
        executor.submit(run_training_job, job_id)
    elif job_type == "predict_outcome":
        executor.submit(run_prediction_job, job_id)
    elif job_type == "recommend_regimen":
        executor.submit(run_recommendation_job, job_id)
    elif job_type == "generate_report":
        executor.submit(run_report_job, job_id)
    else:
        raise ValueError(f"Unsupported job_type: {job_type}")


def reconcile_unfinished_tasks() -> None:
    """Mark unfinished tasks after a service restart to avoid zombie running tasks."""
    for task in task_repo.list():
        if task["status"] in {"queued", "running"}:
            task_repo.update(
                task["id"],
                status="failed",
                current_stage="reconciled_after_restart",
                message="Service restarted before completion",
                error_message="Task did not finish before service restart and was marked failed",
                completed_at=now_iso(),
            )
            task_repo.append_log(task["id"], "Service restart detected; unfinished task was marked failed.")

