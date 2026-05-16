from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.api.request_locale import api_locale_prefers_english, resolve_api_user_locale_from_request
from backend.api.responses import error_response, success_response
from backend.prediction.available_models import build_prediction_model_records
from backend.prediction.task_keys import normalize_requested_task_filter
from backend.runtime import model_repo
from backend.schemas.api_response import ErrorResponse, ModelDetailSuccessResponse, ModelListSuccessResponse
from backend.schemas.model import ModelItem

router = APIRouter(prefix="/models", tags=["models"])


class ModelPatchBody(BaseModel):
    """Frontend-editable display and business fields; other training artifact fields remain unchanged."""

    task_name: Optional[str] = Field(default=None, description="Model display name / task name")
    notes: Optional[str] = Field(default=None)
    is_published: Optional[bool] = Field(default=None, description="Whether the model is released (enabled state)")


@router.get("", response_model=ModelListSuccessResponse, responses={404: {"model": ErrorResponse}})
async def list_models(task_type: Optional[str] = Query(default=None)):
    models = [ModelItem.model_validate(item).model_dump(mode="json") for item in model_repo.list(task_type=task_type)]
    return success_response({"items": models, "total": len(models)})


@router.get("/available-for-prediction", response_model=None)
async def available_for_prediction(task: Optional[str] = Query(default=None, description="Canonical task key filter")):
    """
    Canonical picker list for prediction workflows: same registry file as GET /models,
    with released-only rows and normalized task_key. Omit task for all released models.
    """
    raw_task = str(task).strip() if task is not None else ""
    if raw_task:
        canon = normalize_requested_task_filter(raw_task)
        if canon is None:
            return success_response({"items": [], "total": 0, "invalid_task": True})
        items = build_prediction_model_records(task_filter=canon)
    else:
        items = build_prediction_model_records(task_filter=None)
    return success_response({"items": items, "total": len(items)})


@router.get("/{model_id}", response_model=ModelDetailSuccessResponse, responses={404: {"model": ErrorResponse}})
async def get_model(model_id: str, request: Request):
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    model = model_repo.get(model_id)
    if not model:
        detail = f"Model not found (model_id={model_id})." if en else f"model_id={model_id} not found"
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "MODEL_NOT_FOUND"),
        )
    return success_response({"model": ModelItem.model_validate(model).model_dump(mode="json")})


@router.patch("/{model_id}", response_model=ModelDetailSuccessResponse, responses={404: {"model": ErrorResponse}})
async def patch_model(model_id: str, request: Request, body: ModelPatchBody = Body(...)) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    existing = model_repo.get(model_id)
    if not existing:
        detail = f"Model not found (model_id={model_id})." if en else f"model_id={model_id} not found"
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "MODEL_NOT_FOUND"),
        )
    patch: Dict[str, Any] = {}
    if body.task_name is not None:
        patch["task_name"] = body.task_name
    if body.notes is not None:
        patch["notes"] = body.notes
    if body.is_published is not None:
        patch["is_published"] = body.is_published
    if not patch:
        return success_response({"model": ModelItem.model_validate(existing).model_dump(mode="json")})
    merged = {**existing, **patch, "model_id": existing.get("model_id") or model_id}
    saved = model_repo.upsert(merged)
    return success_response({"model": ModelItem.model_validate(saved).model_dump(mode="json")})


@router.delete("/{model_id}", responses={404: {"model": ErrorResponse}})
async def delete_model(model_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    ok = model_repo.delete(model_id)
    if not ok:
        detail = f"Model not found (model_id={model_id})." if en else f"model_id={model_id} not found"
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "MODEL_NOT_FOUND"),
        )
    msg = "Model removed from registry." if en else "Model removed from registry."
    return success_response({"message": msg, "model_id": model_id})

