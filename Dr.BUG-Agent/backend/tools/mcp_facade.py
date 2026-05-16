from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional
from pathlib import Path

import pandas as pd

try:
    from fastmcp import FastMCP  # type: ignore
    REAL_FASTMCP_AVAILABLE = True
except Exception:
    REAL_FASTMCP_AVAILABLE = False

    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str):
            self.name = name

        def tool(self):
            def decorator(func):
                return func
            return decorator

        def run(self, *args, **kwargs):
            print("fastmcp not installed, running in API-only fallback mode.")

from backend.runtime import dataset_repo, model_repo, task_repo
from backend.schemas.task import JobType
from backend.utils.time_utils import now_iso
from backend.workers.task_executor import submit_job
from backend.agent.training_contract import validate_phase1_training_payload_to_dict

mcp = FastMCP("ClinicalWorkbenchMCP")


def _load_dataset_df_for_precheck(dataset_meta: Dict[str, Any]) -> pd.DataFrame:
    p = Path(str(dataset_meta.get("file_path", "")))
    if not p.exists():
        raise FileNotFoundError(f"Dataset file not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p, encoding="utf-8-sig")
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(p)
    raise ValueError(f"Unsupported dataset file type: {suffix}")


def _training_precheck_classification(
    job_id: str,
    dataset_id: str,
    target_column: str,
    ml_task_type: str,
) -> Dict[str, Any]:
    ds = dataset_repo.get(dataset_id)
    if not ds:
        return {"ok": False, "reason": f"dataset_id not found: {dataset_id}"}
    df = _load_dataset_df_for_precheck(ds)
    total_rows = int(len(df))
    if target_column not in df.columns:
        return {
            "ok": False,
            "reason": f"Target column not found: {target_column}",
            "total_rows": total_rows,
            "non_null_target_rows": 0,
            "label_distribution": {},
        }
    y = df[target_column]
    y_non_null = y.dropna()
    non_null_target_rows = int(len(y_non_null))
    label_counts = y_non_null.value_counts().to_dict()
    label_distribution = {str(k): int(v) for k, v in label_counts.items()}
    fail_reason: Optional[str] = None
    if non_null_target_rows < 2:
        fail_reason = "The target column has too few non-null samples for classification training."
    elif len(label_distribution) < 2:
        fail_reason = "The target column contains only one class, so classification training cannot proceed."
    else:
        min_class = min(label_distribution.values())
        if min_class < 2:
            fail_reason = "The smallest class has fewer than 2 samples, so basic stratified splitting cannot proceed."
    payload = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "target_column": target_column,
        "ml_task_type": ml_task_type,
        "total_rows": total_rows,
        "non_null_target_rows": non_null_target_rows,
        "label_distribution": label_distribution,
        "precheck_passed": fail_reason is None,
        "fail_reason": fail_reason,
    }
    task_repo.append_log(job_id, "[training-precheck] " + json.dumps(payload, ensure_ascii=False))
    if fail_reason:
        return {
            "ok": False,
            "reason": f"{fail_reason} Current label distribution: {label_distribution or '{}'}",
            "total_rows": total_rows,
            "non_null_target_rows": non_null_target_rows,
            "label_distribution": label_distribution,
        }
    return {
        "ok": True,
        "total_rows": total_rows,
        "non_null_target_rows": non_null_target_rows,
        "label_distribution": label_distribution,
    }


@mcp.tool()
def list_datasets() -> Dict[str, Any]:
    data = dataset_repo.list()
    return {"status": "success", "total": len(data), "datasets": data}


@mcp.tool()
def get_dataset_detail(dataset_id: str) -> Dict[str, Any]:
    dataset = dataset_repo.get(dataset_id)
    if not dataset:
        return {"status": "error", "message": f"dataset_id={dataset_id} not found"}
    return {"status": "success", "dataset": dataset}


@mcp.tool()
def list_models(task_type: Optional[str] = None) -> Dict[str, Any]:
    models = model_repo.list(task_type=task_type)
    return {"status": "success", "total": len(models), "models": models}


def create_training_job_from_contract(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a training workflow job and schedule Phase 2 asynchronously; HTTP paths must return quickly and not run the pipeline synchronously."""
    normalized = validate_phase1_training_payload_to_dict(payload)
    dataset_id = normalized["dataset_id"]
    if not dataset_repo.get(dataset_id):
        return {"status": "error", "message": "dataset_id not found"}
    task = task_repo.create(JobType.train_model, normalized)
    jid = task["id"]
    ml_task_type = str(normalized.get("ml_task_type", "binary"))
    if ml_task_type != "regression":
        precheck = _training_precheck_classification(
            job_id=jid,
            dataset_id=str(normalized.get("dataset_id", "")).strip(),
            target_column=str(normalized.get("target_column", "")).strip(),
            ml_task_type=ml_task_type,
        )
        if not precheck.get("ok"):
            reason = str(precheck.get("reason") or "Training precheck failed")
            task_repo.update(
                jid,
                status="failed",
                progress=100,
                current_stage="training_precheck_failed",
                message="Training precheck failed",
                error_message=reason,
                completed_at=now_iso(),
                result_summary={
                    "train_workflow_phase": "training_precheck_failed",
                    "headline": "Training job failed validation after creation",
                    "task_kind": "train_model",
                    "precheck_failed": True,
                    "precheck_reason": reason,
                    "label_distribution": precheck.get("label_distribution") or {},
                },
            )
            task_repo.append_log(jid, f"[training-precheck] failed_before_phase2: {reason}")
            task = task_repo.get(jid)
            return {
                "status": "success",
                "message": f"Training job was created but did not enter Phase 2: {reason}",
                "job_id": jid,
                "job": task,
            }
    task_repo.update(
        jid,
        current_stage="train_phase2_feature_search_running",
        message="Phase 2 feature screening has been queued and will run asynchronously.",
        result_summary={
            "train_workflow_phase": "train_phase2_feature_search_running",
            "headline": "Training workflow created; feature screening is running (Phase 2).",
            "task_kind": "train_model",
        },
    )
    task = task_repo.get(jid)
    if task is None:
        return {"status": "error", "message": "Failed to read the task after creation"}
    submit_job("train_model", jid)

    return {"status": "success", "message": "Training job created; Phase 2 has started asynchronously", "job_id": jid, "job": task}


@mcp.tool()
def create_training_job(
    dataset_id: str,
    clinical_task_id: Literal[
        "clinical_efficacy", "mortality_28d", "polymyxin_resistance", "treatment_duration"
    ],
    ml_task_type: Literal["binary", "multiclass", "regression"],
    target_column: str,
    model_type: Literal[
        "xgboost", "lightgbm", "catboost", "random_forest", "logistic_regression", "svm", "knn"
    ],
    feature_set: Optional[str] = None,
    objective_metric: str = "auroc",
    use_cv_shap: bool = True,
) -> Dict[str, Any]:
    """MCP tool: explicit parameters -> unified contract -> task creation. feature_set is optional; when omitted, use_cv_shap can trigger the default candidate pool."""
    raw: Dict[str, Any] = {
        "dataset_id": dataset_id,
        "clinical_task_id": clinical_task_id,
        "ml_task_type": ml_task_type,
        "target_column": target_column,
        "model_type": model_type,
        "objective_metric": objective_metric,
        "use_cv_shap": use_cv_shap,
    }
    if feature_set and str(feature_set).strip():
        raw["feature_set"] = str(feature_set).strip()
    try:
        return create_training_job_from_contract(raw)
    except Exception as exc:  # noqa: BLE001 — MCP returns structured errors
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def create_prediction_job(model_id: str, patient_features: Dict[str, Any]) -> Dict[str, Any]:
    if not model_repo.get(model_id):
        return {"status": "error", "message": "model_id not found"}
    task = task_repo.create(JobType.predict_outcome, {"model_id": model_id, "patient_features": patient_features})
    submit_job("predict_outcome", task["id"])
    return {"status": "success", "message": "Prediction job created", "job_id": task["id"], "job": task}


@mcp.tool()
def create_recommendation_job(
    model_id: str,
    patient_features: Dict[str, Any],
    candidate_regimens: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if not model_repo.get(model_id):
        return {"status": "error", "message": "model_id not found"}
    task = task_repo.create(
        JobType.recommend_regimen,
        {
            "model_id": model_id,
            "patient_features": patient_features,
            "candidate_regimens": candidate_regimens or [],
        },
    )
    submit_job("recommend_regimen", task["id"])
    return {"status": "success", "message": "Recommendation job created", "job_id": task["id"], "job": task}


@mcp.tool()
def create_report_job(
    source_job_id: str,
    report_type: Literal["training_report", "prediction_report", "recommendation_report"],
) -> Dict[str, Any]:
    if not task_repo.get(source_job_id):
        return {"status": "error", "message": "source_job_id not found"}
    task = task_repo.create(JobType.generate_report, {"source_job_id": source_job_id, "report_type": report_type})
    submit_job("generate_report", task["id"])
    return {"status": "success", "message": "Report job created", "job_id": task["id"], "job": task}


@mcp.tool()
def get_job_status(job_id: str) -> Dict[str, Any]:
    task = task_repo.get(job_id)
    if not task:
        return {"status": "error", "message": f"job_id={job_id} not found"}
    return {
        "status": "success",
        "job_status": {
            "id": task["id"],
            "job_type": task["job_type"],
            "status": task["status"],
            "progress": task["progress"],
            "current_stage": task["current_stage"],
            "message": task["message"],
            "error_message": task["error_message"],
            "created_at": task["created_at"],
            "started_at": task["started_at"],
            "completed_at": task["completed_at"],
        },
    }


@mcp.tool()
def get_job_detail(job_id: str) -> Dict[str, Any]:
    task = task_repo.get(job_id)
    if not task:
        return {"status": "error", "message": f"job_id={job_id} not found"}
    return {"status": "success", "job": task, "logs": task_repo.read_logs(job_id), "artifacts": task_repo.list_artifacts(job_id)}


@mcp.tool()
def cancel_job(job_id: str) -> Dict[str, Any]:
    task = task_repo.get(job_id)
    if not task:
        return {"status": "error", "message": f"job_id={job_id} not found"}
    if task["status"] in {"completed", "failed", "canceled"}:
        return {"status": "error", "message": f"Task status is {task['status']}; it cannot be canceled"}
    # Soft cancel only: this updates task status but does not interrupt an already running thread.
    task_repo.update(
        job_id,
        status="canceled",
        current_stage="canceled",
        message="Job canceled by user",
        completed_at=now_iso(),
    )
    task_repo.append_log(job_id, "Task canceled.")
    return {"status": "success", "message": f"{job_id} canceled"}

