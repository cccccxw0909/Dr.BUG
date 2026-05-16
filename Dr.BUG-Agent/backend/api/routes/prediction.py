from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons.zh_api_error_compat import (
    PREDICTION_VALUE_ERROR_INVALID_FRAGMENTS,
    PREDICTION_VALUE_ERROR_MISMATCH_FRAGMENTS,
)
from backend.api.request_locale import resolve_api_user_locale_from_request
from backend.api.responses import error_response, success_response
from backend.prediction.batch_service import check_batch_file, read_upload_bytes, run_batch_prediction
from backend.prediction.history_service import (
    archive_batch_prediction,
    archive_single_prediction,
    get_prediction_history_record,
    list_prediction_history,
)
from backend.prediction.sync_task_registration import (
    register_completed_batch_prediction_task,
    register_completed_single_prediction_task,
)
from backend.prediction.inference import run_single_sample
from backend.prediction.service import get_model_schema_bundle, list_prediction_models
from backend.schemas.api_response import ErrorResponse

logger = logging.getLogger(__name__)

INVALID = "PREDICTION_INVALID_INPUT"
MISMATCH = "PREDICTION_MODEL_TASK_MISMATCH"
FAILED = "PREDICTION_EXECUTION_FAILED"

def _prediction_user_messages(loc: str) -> Tuple[str, str, str]:
    inv = chat_msg(loc, "api.prediction.invalid_input")
    mismatch = chat_msg(loc, "api.prediction.model_task_mismatch")
    failed = chat_msg(loc, "api.prediction.execution_failed")
    return inv, mismatch, failed


def _canonical_value_error(exc: ValueError, locale: str) -> Tuple[str, str]:
    """Map inference-layer ValueError values to three canonical codes with stable user-facing messages."""
    s = str(exc).strip()
    sl = s.lower()
    inv, mismatch, failed = _prediction_user_messages(locale)
    if any(
        x in s
        for x in PREDICTION_VALUE_ERROR_MISMATCH_FRAGMENTS
    ) or any(
        x in sl
        for x in (
            "model not found",
            "not registered",
            "no feature order",
            "feature order configured",
        )
    ):
        return MISMATCH, mismatch
    if any(
        x in s
        for x in PREDICTION_VALUE_ERROR_INVALID_FRAGMENTS
    ) or any(
        x in sl
        for x in (
            "model_id is required",
            "required field",
            "validation",
            "form is empty",
            "invalid format",
            "must be an integer",
            "invalid option",
            "too few patient features",
            "only csv",
            "xlsx",
            "missing required columns",
        )
    ):
        return INVALID, inv
    return FAILED, failed


def _attach_single_whitelist_compat(out: Dict[str, Any]) -> Dict[str, Any]:
    """Derive top-level compatibility fields from canonical `explanation` without creating a second schema source."""
    ex = out.get("explanation")
    if not isinstance(ex, dict):
        out.setdefault("explanation_supported", False)
        out.setdefault("shap_supported", False)
        out.setdefault("waterfall_plot_url", None)
        out.setdefault("force_plot_url", None)
        out.setdefault("top_positive_drivers", [])
        out.setdefault("top_negative_drivers", [])
        return out
    sup = bool(ex.get("supported"))
    wf = ex.get("waterfall_image_url")
    ff = ex.get("force_image_url")
    out["explanation_supported"] = sup
    out["waterfall_plot_url"] = wf
    out["force_plot_url"] = ff
    out["shap_supported"] = bool(sup and (wf or ff))
    pos: list[Dict[str, str]] = []
    neg: list[Dict[str, str]] = []
    for tf in ex.get("top_features") or []:
        if not isinstance(tf, dict):
            continue
        name = tf.get("name")
        if not name:
            continue
        direction = str(tf.get("direction") or "")
        if direction == "increase":
            pos.append({"name": str(name)})
        elif direction == "decrease":
            neg.append({"name": str(name)})
    out["top_positive_drivers"] = pos
    out["top_negative_drivers"] = neg
    return out


class SinglePredictionRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    values: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    locale: Optional[str] = None


router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.get("/models", response_model=None)
async def prediction_models_list() -> Dict[str, Any]:
    items = list_prediction_models()
    return success_response({"items": items, "total": len(items)})


@router.get("/models/{model_id}/schema", response_model=None, responses={404: {"model": ErrorResponse}})
async def prediction_model_schema(model_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    _, mismatch_msg, _ = _prediction_user_messages(loc)
    bundle = get_model_schema_bundle(model_id)
    if bundle is None:
        return JSONResponse(
            status_code=404,
            content=error_response(mismatch_msg, MISMATCH),
        )
    return success_response(bundle)


@router.post("/single", response_model=None, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def prediction_single(request: Request, body: SinglePredictionRequest) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request, explicit=body.locale)
    _, _, failed_msg = _prediction_user_messages(loc)
    try:
        out = run_single_sample(
            body.model_id, body.values, body.session_id, ui_locale=loc
        )
        _attach_single_whitelist_compat(out)
        rec = archive_single_prediction(out)
        rid = str(rec.get("record_id") or "").strip()
        if rid:
            register_completed_single_prediction_task(out, history_record_id=rid, session_id=body.session_id)
        return success_response(out)
    except ValueError as exc:
        code, msg = _canonical_value_error(exc, loc)
        return JSONResponse(status_code=400, content=error_response(msg, code))
    except Exception:
        logger.exception("prediction_single execution failed")
        return JSONResponse(status_code=500, content=error_response(failed_msg, FAILED))


@router.post("/batch/check", response_model=None, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def prediction_batch_check(
    request: Request,
    model_id: str = Form(...),
    file: UploadFile = File(...),
    locale: Optional[str] = Form(None),
) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request, explicit=locale)
    _, _, failed_msg = _prediction_user_messages(loc)
    try:
        content = await read_upload_bytes(file)
        out = check_batch_file(model_id, file.filename or "", content, ui_locale=loc)
        return success_response(out)
    except ValueError as exc:
        code, msg = _canonical_value_error(exc, loc)
        return JSONResponse(status_code=400, content=error_response(msg, code))
    except Exception:
        logger.exception("prediction_batch_check failed")
        return JSONResponse(status_code=500, content=error_response(failed_msg, FAILED))


@router.post("/batch/run", response_model=None, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def prediction_batch_run(
    request: Request,
    model_id: str = Form(...),
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    locale: Optional[str] = Form(None),
) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request, explicit=locale)
    _, _, failed_msg = _prediction_user_messages(loc)
    try:
        content = await read_upload_bytes(file)
        out = run_batch_prediction(model_id, file.filename or "", content, ui_locale=loc)
        rec = archive_batch_prediction(out, session_id=session_id)
        rid = str(rec.get("record_id") or "").strip()
        if rid:
            register_completed_batch_prediction_task(out, history_record_id=rid, session_id=session_id)
        return success_response(out)
    except ValueError as exc:
        code, msg = _canonical_value_error(exc, loc)
        return JSONResponse(status_code=400, content=error_response(msg, code))
    except Exception:
        logger.exception("prediction_batch_run failed")
        return JSONResponse(status_code=500, content=error_response(failed_msg, FAILED))


@router.get("/history", response_model=None)
async def prediction_history_list(
    type: Optional[str] = None,  # noqa: A002
    task: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    items = list_prediction_history(ptype=type, task=task, model=model)
    return success_response({"items": items, "total": len(items)})


@router.get("/history/{record_id}", response_model=None, responses={404: {"model": ErrorResponse}})
async def prediction_history_detail(record_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    rec = get_prediction_history_record(record_id)
    if rec is None:
        detail = chat_msg(loc, "api.prediction.history_not_found", record_id=record_id)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "PREDICTION_HISTORY_NOT_FOUND"),
        )
    return success_response(rec)
