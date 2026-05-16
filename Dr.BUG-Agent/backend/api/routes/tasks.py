from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons.zh_api_error_compat import (
    TASK_CANCEL_NOT_ALLOWED_FRAGMENT,
    TASK_CANCEL_NOT_FOUND_FRAGMENT,
    TASK_CANCEL_STATUS_AND_JOB_FRAGMENTS,
    TASK_CANCEL_SUCCEEDED_FRAGMENT,
)
from backend.api.request_locale import resolve_api_user_locale_from_request
from backend.api.responses import error_response, success_response
from backend.runtime import task_repo
from backend.schemas.api_response import (
    ErrorResponse,
    TaskArtifactsSuccessResponse,
    TaskCancelSuccessResponse,
    TaskDetailSuccessResponse,
    TaskDeleteSuccessResponse,
    TaskListSuccessResponse,
    TaskStatusSuccessResponse,
)
from backend.schemas.task import Task, TaskStatusView, TrainingWorkflowRequest
from backend.task_summary_projection import project_task_summary
from backend.tools.mcp_facade import cancel_job
from backend.training.pipeline_training import resume_training_workflow

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _localize_task_worker_line(text: Any, _loc: str) -> Any:
    """Worker progress lines are stored in English; no locale-specific rewrite."""
    return None if text is None else str(text)


def _task_not_found_message(job_id: str, loc: str) -> str:
    return chat_msg(loc, "api.tasks.not_found", job_id=job_id)


def _artifact_not_found_message(loc: str) -> str:
    return chat_msg(loc, "api.tasks.artifact_not_found")


def _workflow_rejected_message(loc: str) -> str:
    return chat_msg(loc, "api.tasks.workflow_rejected")


def _localize_workflow_rejection_message(_raw: Any, loc: str) -> str:
    """Do not surface raw worker messages; use stable catalog copy."""
    return _workflow_rejected_message(loc)


def _delete_not_allowed_message(job_id: str, status: str, loc: str) -> str:
    return chat_msg(loc, "api.tasks.delete_not_allowed", job_id=job_id, status=status)


def _task_deleted_message(loc: str) -> str:
    return chat_msg(loc, "api.tasks.deleted")


def _localize_cancel_user_message(raw: str, job_id: str, loc: str) -> str:
    s = str(raw or "")
    sl = s.lower()
    # Legacy/localized not-found phrases (Chinese fragments are recognition-only, not API copy).
    _st, _job = TASK_CANCEL_STATUS_AND_JOB_FRAGMENTS
    if (TASK_CANCEL_NOT_FOUND_FRAGMENT in s and job_id in s) or ("not found" in sl and job_id in s):
        return _task_not_found_message(job_id, loc)
    if TASK_CANCEL_NOT_ALLOWED_FRAGMENT in s or (_st in s and _job in s) or "cannot be canceled" in sl:
        return chat_msg(loc, "api.tasks.cancel_not_allowed")
    if (TASK_CANCEL_SUCCEEDED_FRAGMENT in s and job_id in s) or ("canceled" in sl and job_id in s):
        return chat_msg(loc, "api.tasks.cancel_succeeded", job_id=job_id)
    return s


@router.get("", response_model=TaskListSuccessResponse, responses={404: {"model": ErrorResponse}})
async def list_tasks(
    status: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    jobs = [Task.model_validate(item).model_dump(mode="json") for item in task_repo.list(status=status, job_type=job_type)]
    return success_response({"items": jobs, "total": len(jobs)})


@router.get("/{job_id}", response_model=TaskDetailSuccessResponse, responses={404: {"model": ErrorResponse}})
async def task_detail(job_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    task = task_repo.get(job_id)
    if not task:
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    task_dump = Task.model_validate(task).model_dump(mode="json")
    task_dump["message"] = _localize_task_worker_line(task_dump.get("message"), loc)
    task_dump["error_message"] = _localize_task_worker_line(task_dump.get("error_message"), loc)
    return success_response(
        {
            "task": task_dump,
            "task_summary": project_task_summary(task),
            "logs": task_repo.read_logs(job_id),
            # Use real-time artifacts scan instead of task.json snapshot.
            "artifacts": task_repo.list_artifacts(job_id),
        }
    )


@router.get("/{job_id}/status", response_model=TaskStatusSuccessResponse, responses={404: {"model": ErrorResponse}})
async def task_status(job_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    task = task_repo.get(job_id)
    if not task:
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    task_view = TaskStatusView.model_validate(
        {
            "id": task["id"],
            "job_type": task["job_type"],
            "status": task["status"],
            "progress": task["progress"],
            "current_stage": task["current_stage"],
            "message": _localize_task_worker_line(task.get("message"), loc),
            "error_message": _localize_task_worker_line(task.get("error_message"), loc),
            "created_at": task["created_at"],
            "started_at": task["started_at"],
            "completed_at": task["completed_at"],
        }
    ).model_dump(mode="json")
    return success_response({"task": task_view})


@router.get("/{job_id}/artifacts", response_model=TaskArtifactsSuccessResponse, responses={404: {"model": ErrorResponse}})
async def task_artifacts(job_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    task = task_repo.get(job_id)
    if not task:
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    return success_response({"job_id": job_id, "artifacts": task_repo.list_artifacts(job_id)})


@router.get("/{job_id}/artifacts/{filename}")
async def download_task_artifact(job_id: str, filename: str, request: Request) -> Any:
    """Serve a single artifact file under the job artifacts directory (basename only; path traversal rejected)."""
    loc = resolve_api_user_locale_from_request(request)
    task = task_repo.get(job_id)
    if not task:
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    path = task_repo.resolve_safe_artifact_file(job_id, filename)
    if not path:
        detail = _artifact_not_found_message(loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "ARTIFACT_NOT_FOUND"),
        )
    media = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
    download_name = f"training_report_{job_id}.pdf" if filename.lower() == "report.pdf" else path.name
    return FileResponse(
        str(path),
        media_type=media,
        filename=download_name,
    )


@router.post(
    "/{job_id}/training/workflow",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def post_training_workflow(
    job_id: str, request: Request, body: TrainingWorkflowRequest = Body(...)
) -> Dict[str, Any]:
    """Multi-stage training: submit final_features, training configuration, or release options while waiting_user."""
    loc = resolve_api_user_locale_from_request(request)
    if not task_repo.get(job_id):
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    payload = body.model_dump(exclude_none=True)
    action = str(payload.pop("action", ""))
    result = resume_training_workflow(job_id, action, payload)
    if result.get("status") == "error":
        msg = _localize_workflow_rejection_message(result.get("message"), loc)
        return JSONResponse(
            status_code=400,
            content=error_response(msg, "TRAINING_WORKFLOW_REJECTED"),
        )
    return success_response(result)


@router.post("/{job_id}/cancel", response_model=TaskCancelSuccessResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def task_cancel(job_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    result = cancel_job(job_id)
    if result["status"] == "error":
        msg_l = str(result["message"] or "").lower()
        rmsg = str(result.get("message") or "")
        error_code = "TASK_NOT_FOUND" if (TASK_CANCEL_NOT_FOUND_FRAGMENT in rmsg or "not found" in msg_l) else "TASK_CANCEL_NOT_ALLOWED"
        status_code = 404 if error_code == "TASK_NOT_FOUND" else 400
        out_msg = _localize_cancel_user_message(str(result["message"]), job_id, loc)
        return JSONResponse(
            status_code=status_code,
            content=error_response(out_msg, error_code),
        )
    out_msg = _localize_cancel_user_message(str(result["message"]), job_id, loc)
    return success_response({"message": out_msg, "job_id": job_id})


@router.delete(
    "/{job_id}",
    response_model=TaskDeleteSuccessResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def task_delete(job_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    task = task_repo.get(job_id)
    if not task:
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    status = str(task.get("status", ""))
    # Conservative semantics: running, queued, or waiting_user tasks must be canceled before deletion.
    if status in {"queued", "running", "waiting_user"}:
        detail = _delete_not_allowed_message(job_id, status, loc)
        return JSONResponse(
            status_code=400,
            content=error_response(
                detail,
                "TASK_DELETE_NOT_ALLOWED",
            ),
        )
    ok = task_repo.delete(job_id)
    if not ok:
        detail = _task_not_found_message(job_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "TASK_NOT_FOUND"),
        )
    msg = _task_deleted_message(loc)
    return success_response({"message": msg, "job_id": job_id})
