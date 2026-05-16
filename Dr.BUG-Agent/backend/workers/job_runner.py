from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from backend.prediction.history_service import archive_single_prediction
from backend.prediction.inference import run_single_sample
from backend.prediction.task_summary_projection import build_prediction_task_result_summary
from backend.recommendation.service import run_survival_only_recommendation
from backend.runtime import model_repo, task_repo
from backend.training.pipeline_training import run_domain_training_job
from backend.utils.time_utils import now_iso


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_training_job(job_id: str) -> None:
    """Training task: run the real StateMachine pipeline (DomainTrainingPayload -> pipeline_training)."""
    try:
        task = task_repo.get(job_id)
        if not task:
            raise ValueError(f"Task not found: {job_id}")
        run_domain_training_job(job_id, task["params"])
    except Exception as exc:
        task_repo.update(
            job_id,
            status="failed",
            current_stage="failed",
            message="Training failed",
            error_message=str(exc),
            completed_at=now_iso(),
        )
        task_repo.append_log(job_id, f"Training failed: {exc}")


def run_prediction_job(job_id: str) -> None:
    try:
        task_repo.update(
            job_id,
            status="running",
            started_at=now_iso(),
            progress=30,
            current_stage="model_loading",
            message="Loading model",
        )
        task_repo.append_log(job_id, "Loading model.")
        task = task_repo.get(job_id)
        assert task is not None
        params = task.get("params") if isinstance(task.get("params"), dict) else {}
        model_id = str(params.get("model_id") or "").strip()
        patient_features = params.get("patient_features")
        if not model_id:
            raise ValueError("model_id is required")
        if not isinstance(patient_features, dict) or not patient_features:
            raise ValueError("patient_features cannot be empty")
        if not model_repo.get(model_id):
            raise ValueError("Model not found")

        task_repo.update(
            job_id,
            progress=70,
            current_stage="predicting",
            message="Running model inference",
        )
        prediction = run_single_sample(
            model_id=model_id,
            values=patient_features,
            session_id=f"job:{job_id}",
            include_explanation=True,
        )
        rec = archive_single_prediction(prediction)
        summary = build_prediction_task_result_summary(prediction, record_id=str(rec.get("record_id") or ""))
        _write_json(task_repo.artifacts_dir(job_id) / "prediction.json", prediction)
        task_repo.update(
            job_id,
            status="completed",
            progress=100,
            current_stage="completed",
            message="Prediction completed",
            completed_at=now_iso(),
            result_summary=summary,
            artifacts=task_repo.list_artifacts(job_id),
        )
        task_repo.append_log(job_id, f"Prediction task completed. history_record_id={rec.get('record_id')}")
    except Exception as exc:
        task_repo.update(
            job_id,
            status="failed",
            current_stage="failed",
            message="Prediction failed",
            error_message=str(exc),
            completed_at=now_iso(),
        )
        task_repo.append_log(job_id, f"Prediction failed: {exc}")


def run_recommendation_job(job_id: str) -> None:
    try:
        task_repo.update(
            job_id,
            status="running",
            started_at=now_iso(),
            progress=30,
            current_stage="regimen_scoring",
            message="Ranking regimens",
        )
        task = task_repo.get(job_id)
        assert task is not None
        params = task.get("params") if isinstance(task.get("params"), dict) else {}
        model_id = str(params.get("model_id") or "").strip()
        patient_features = params.get("patient_features")
        if not model_id:
            raise ValueError("model_id is required")
        if not isinstance(patient_features, dict) or not patient_features:
            raise ValueError("patient_features cannot be empty")
        if str(params.get("mode") or "").strip() != "survival_only":
            raise ValueError("recommendation mode only supports survival_only")
        if not model_repo.get(model_id):
            raise ValueError("Model not found")
        recommendation_result = run_survival_only_recommendation(
            model_id=model_id,
            patient_features=patient_features,
            observed_regimen=params.get("observed_regimen")
            if isinstance(params.get("observed_regimen"), dict)
            else None,
            regimen_ids=params.get("regimen_ids") if isinstance(params.get("regimen_ids"), list) else None,
            top_k=int(params.get("top_k") or 5),
            job_id=job_id,
        )
        _write_json(task_repo.artifacts_dir(job_id) / "recommendation.json", recommendation_result)
        top1 = recommendation_result.get("recommended_top1_regimen") or {}
        task_repo.update(
            job_id,
            status="completed",
            progress=100,
            current_stage="completed",
            message="Recommendation completed",
            completed_at=now_iso(),
            result_summary={
                "headline": "Regimen comparison completed",
                "task_kind": "recommend_regimen",
                "mode": "survival_only",
                "model_id": model_id,
                "recommended_top1_regimen": top1,
                "recommended_top1_probability": recommendation_result.get("recommended_top1_probability"),
                "delta_probability_top1": recommendation_result.get("delta_probability_top1"),
            },
            artifacts=task_repo.list_artifacts(job_id),
        )
        task_repo.append_log(job_id, "Recommendation task completed.")
    except Exception as exc:
        task_repo.update(
            job_id,
            status="failed",
            current_stage="failed",
            message="Recommendation failed",
            error_message=str(exc),
            completed_at=now_iso(),
        )
        task_repo.append_log(job_id, f"Recommendation failed: {exc}")


def run_report_job(job_id: str) -> None:
    try:
        task_repo.update(
            job_id,
            status="running",
            started_at=now_iso(),
            progress=40,
            current_stage="rendering_report",
            message="Rendering report",
        )
        task = task_repo.get(job_id)
        assert task is not None
        report = {"job_id": job_id, "report_type": task["params"]["report_type"], "generated_at": now_iso()}
        _write_json(task_repo.artifacts_dir(job_id) / "report.json", report)
        task_repo.update(
            job_id,
            status="completed",
            progress=100,
            current_stage="completed",
            message="Report completed",
            completed_at=now_iso(),
            result_summary={"headline": "Report generation completed", "report_type": task["params"]["report_type"]},
            artifacts=task_repo.list_artifacts(job_id),
        )
        task_repo.append_log(job_id, "Report task completed.")
    except Exception as exc:
        task_repo.update(
            job_id,
            status="failed",
            current_stage="failed",
            message="Report failed",
            error_message=str(exc),
            completed_at=now_iso(),
        )
        task_repo.append_log(job_id, f"Report generation failed: {exc}")
