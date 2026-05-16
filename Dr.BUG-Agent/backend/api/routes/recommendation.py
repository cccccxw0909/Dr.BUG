from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.messages_api import recommendation_service_message_key
from backend.api.request_locale import resolve_api_user_locale_from_request
from backend.api.responses import error_response, success_response
from backend.recommendation.errors import RecommendationServiceError
from backend.recommendation.input_coverage import assert_recommendation_patient_coverage
from backend.recommendation.service import SURVIVAL_ONLY_MODE, normalize_treatment_values, validate_survival_model
from backend.recommendation.regimen_repo import FileRegimenRepo, TREATMENT_FIELD_NAMES
from backend.runtime import task_repo
from backend.schemas.task import JobType
from backend.workers.task_executor import submit_job


class TreatmentValuesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colistin_cms_daily_freq: float = 0.0
    polymyxin_b_daily_freq: float = 0.0
    colistin_sulfate_daily_freq: float = 0.0
    carbapenem_daily_dose: float = 0.0
    sulbactam_daily_dose: float = 0.0
    tigecycline_daily_dose: float = 0.0
    minocycline_daily_dose: float = 0.0
    vancomycin_daily_dose: float = 0.0
    eravacycline_daily_dose: float = 0.0
    aminoglycoside_daily_dose: float = 0.0


class RegimenWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regimen_name: str = Field(..., min_length=1)
    enabled: bool = True
    notes: Optional[str] = None
    treatment_values: TreatmentValuesInput = Field(default_factory=TreatmentValuesInput)


class RecommendationJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1)
    patient_features: Dict[str, Any] = Field(default_factory=dict)
    observed_regimen: Optional[TreatmentValuesInput] = None
    regimen_ids: Optional[list[str]] = None
    top_k: int = Field(default=5, ge=1)
    mode: str = Field(default=SURVIVAL_ONLY_MODE)
    locale: Optional[str] = None


repo = FileRegimenRepo()
router = APIRouter(prefix="/recommendation", tags=["recommendation"])


class RegimenValidationError(ValueError):
    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _rec_user_visible_error(_msg: str, loc: str) -> str:
    """Unmapped recommendation errors: stable user-facing text only (no raw passthrough)."""
    return chat_msg(loc, "api.recommendation.generic_processing_failed")


def _recommendation_service_user_message(code: str, loc: str) -> str:
    key = recommendation_service_message_key(code)
    return chat_msg(loc, key)


def _regimen_validation_user_message(code: str, loc: str) -> str:
    if code == "REGIMEN_NAME_REQUIRED":
        return chat_msg(loc, "api.recommendation.regimen_name_required")
    return chat_msg(loc, "api.recommendation.regimen_invalid_default")


def _regimen_value_error_user_message(_raw: str, loc: str) -> str:
    """Do not pass through repo-layer ValueError text (may be internal or non-locale-safe)."""
    return chat_msg(loc, "api.recommendation.regimen_invalid_default")


def _assert_coverage_message(raw: str, loc: str) -> Optional[str]:
    """Map known coverage errors to stable user-facing text (locale-aware)."""
    s = str(raw or "").strip()
    if "Model is not available or has no registered prediction schema" in s:
        return chat_msg(loc, "api.recommendation.model_unavailable_or_no_schema")
    if "Model is missing a canonical feature order" in s:
        return chat_msg(loc, "api.recommendation.model_missing_feature_order")
    if "Too few patient features have been completed" in s:
        return chat_msg(loc, "api.recommendation.patient_features_too_few")
    if "Cannot determine survival probability direction" in s:
        return chat_msg(loc, "api.recommendation.survival_semantics_unknown")
    if "Model clinical-task semantics conflict" in s:
        return chat_msg(loc, "api.recommendation.clinical_task_semantics_conflict")
    return None


def _regimen_not_found_detail(regimen_id: str, loc: str) -> str:
    return chat_msg(loc, "api.recommendation.regimen_not_found", regimen_id=regimen_id)


def _regimen_deleted_success_message(loc: str) -> str:
    return chat_msg(loc, "api.recommendation.regimen_deleted")


def _recommendation_value_error_message(raw: str, loc: str) -> str:
    mapped = _assert_coverage_message(raw, loc)
    if mapped:
        return mapped
    return _rec_user_visible_error(raw, loc)


def _normalize_request(body: RegimenWriteRequest) -> Dict[str, Any]:
    regimen_name = body.regimen_name.strip()
    if not regimen_name:
        raise RegimenValidationError("REGIMEN_NAME_REQUIRED")
    notes = body.notes.strip() if isinstance(body.notes, str) else None
    if notes == "":
        notes = None
    treatment_values_raw = body.treatment_values.model_dump(mode="python")
    treatment_values = {k: float(treatment_values_raw.get(k, 0.0)) for k in TREATMENT_FIELD_NAMES}
    return {
        "regimen_name": regimen_name,
        "enabled": bool(body.enabled),
        "notes": notes,
        "treatment_values": treatment_values,
    }


@router.get("/regimens", response_model=None)
async def list_regimens() -> Dict[str, Any]:
    items = repo.list()
    return success_response({"items": items, "total": len(items)})


@router.post("/regimens", response_model=None)
async def create_regimen(body: RegimenWriteRequest, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    try:
        payload = _normalize_request(body)
        created = repo.create(**payload)
        return success_response({"regimen": created})
    except RegimenValidationError as exc:
        msg = _regimen_validation_user_message(exc.code, loc)
        return JSONResponse(status_code=400, content=error_response(msg, "REGIMEN_INVALID_INPUT"))
    except ValueError as exc:
        msg = _regimen_value_error_user_message(str(exc), loc)
        return JSONResponse(status_code=400, content=error_response(msg, "REGIMEN_INVALID_INPUT"))


@router.put("/regimens/{regimen_id}", response_model=None)
async def update_regimen(regimen_id: str, body: RegimenWriteRequest, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    try:
        payload = _normalize_request(body)
        updated = repo.update(regimen_id, **payload)
        if not updated:
            detail = _regimen_not_found_detail(regimen_id, loc)
            return JSONResponse(
                status_code=404,
                content=error_response(detail, "REGIMEN_NOT_FOUND"),
            )
        return success_response({"regimen": updated})
    except RegimenValidationError as exc:
        msg = _regimen_validation_user_message(exc.code, loc)
        return JSONResponse(status_code=400, content=error_response(msg, "REGIMEN_INVALID_INPUT"))
    except ValueError as exc:
        msg = _regimen_value_error_user_message(str(exc), loc)
        return JSONResponse(status_code=400, content=error_response(msg, "REGIMEN_INVALID_INPUT"))


@router.delete("/regimens/{regimen_id}", response_model=None)
async def delete_regimen(regimen_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    ok = repo.delete(regimen_id)
    if not ok:
        detail = _regimen_not_found_detail(regimen_id, loc)
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "REGIMEN_NOT_FOUND"),
        )
    msg = _regimen_deleted_success_message(loc)
    return success_response({"message": msg, "regimen_id": regimen_id})


@router.post("/jobs", response_model=None)
async def create_recommendation_job(body: RecommendationJobCreateRequest, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request, explicit=body.locale)
    try:
        mode = str(body.mode or "").strip()
        if mode != SURVIVAL_ONLY_MODE:
            raise RecommendationServiceError("REC_JOB_MODE_INVALID", "mode must be survival_only")
        model_id = body.model_id.strip()
        if not model_id:
            raise RecommendationServiceError("REC_JOB_MODEL_ID_REQUIRED", "model_id is required")
        if not isinstance(body.patient_features, dict) or not body.patient_features:
            raise RecommendationServiceError("REC_JOB_PATIENT_FEATURES_EMPTY", "patient_features cannot be empty")
        validate_survival_model(model_id)
        assert_recommendation_patient_coverage(model_id, dict(body.patient_features))
        observed_regimen = (
            normalize_treatment_values(body.observed_regimen.model_dump(mode="python"))
            if body.observed_regimen is not None
            else None
        )
        regimen_ids: list[str] = []
        if isinstance(body.regimen_ids, list):
            regimen_ids = [str(x).strip() for x in body.regimen_ids if str(x).strip()]
        params: Dict[str, Any] = {
            "mode": SURVIVAL_ONLY_MODE,
            "model_id": model_id,
            "patient_features": dict(body.patient_features),
            "observed_regimen": observed_regimen,
            "regimen_ids": regimen_ids,
            "top_k": int(body.top_k),
        }
        task = task_repo.create(JobType.recommend_regimen, params)
        submit_job("recommend_regimen", task["id"])
        return success_response({"job_id": task["id"], "job": task})
    except RecommendationServiceError as exc:
        msg = _recommendation_service_user_message(exc.code, loc)
        return JSONResponse(status_code=400, content=error_response(msg, exc.code))
    except ValueError as exc:
        msg = _recommendation_value_error_message(str(exc), loc)
        return JSONResponse(status_code=400, content=error_response(msg, "RECOMMENDATION_INVALID_INPUT"))
