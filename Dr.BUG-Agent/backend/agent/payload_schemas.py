from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator

from backend.agent.training_contract import validate_phase1_training_payload_to_dict


class PredictionPayload(BaseModel):
    model_id: str
    patient_features: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("patient_features")
    @classmethod
    def _patient_features_non_empty(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not v:
            raise ValueError("patient_features must be non-empty for prediction execution")
        return v


class DraftSinglePredictionPayload(BaseModel):
    """Pending-confirm draft: schema/field-name hints only; real values come from UI merge + PredictionPayload validation."""

    model_id: str = ""
    patient_features: Dict[str, Any] = Field(default_factory=dict)
    draft_schema_field_names: List[str] = Field(default_factory=list)


class RecommendationPayload(BaseModel):
    model_id: str
    patient_features: Dict[str, Any] = Field(default_factory=dict)
    candidate_regimens: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("patient_features")
    @classmethod
    def _patient_features_non_empty_rec(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not v:
            raise ValueError("patient_features must be non-empty for recommendation execution")
        return v


class ReportPayload(BaseModel):
    source_job_id: str
    report_type: Literal["training_report", "prediction_report", "recommendation_report"]


def validate_action_payload(action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate executable payload. Training actions always go through DomainTrainingPayload (with alias normalization).
    """
    if action_type in ("create_training_job", "draft_training_job"):
        return validate_phase1_training_payload_to_dict(payload)
    if action_type == "draft_single_prediction":
        return DraftSinglePredictionPayload.model_validate(payload).model_dump(mode="json")
    if action_type == "create_prediction_job":
        return PredictionPayload.model_validate(payload).model_dump(mode="json")
    if action_type == "create_recommendation_job":
        return RecommendationPayload.model_validate(payload).model_dump(mode="json")
    if action_type == "create_report_job":
        return ReportPayload.model_validate(payload).model_dump(mode="json")
    raise ValueError(f"unsupported action_type: {action_type}")