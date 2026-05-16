"""Shared dataclasses and schemas for routing, prediction, and validation.

All core context and result types live here. No business logic; only data shape and simple accessors.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


# ---------------------------------------------------------------------------
# Intake / Router (home-page intent and routing)
# ---------------------------------------------------------------------------


@dataclass
class IntakeResult:
    """
    Structured intent returned by IntakeAgent.parse().
    - route: target workbench or clarification-needed route
    - task_name: for example, train / predict / history
    - input_mode: manual / table / image / unknown
    - need_model_selection: whether a prediction task needs model selection from the registry
    - confidence: intent confidence [0, 1]
    """

    route: Literal["train_workbench", "predict_workbench", "history_workbench", "clarify_before_route"]
    task_name: str = ""
    input_mode: Literal["manual", "table", "image", "unknown"] = "manual"
    need_model_selection: bool = True
    confidence: float = 0.0


# Alias corresponding to "intent" in the architecture docs.
IntentResult = IntakeResult


@dataclass
class RouteResult:
    """
    Return value from RouterAgent.route(): destination and optional parameters.
    - A non-empty clarify_message means stay on the home page and display that prompt.
    """

    route: Literal["train_workbench", "predict_workbench", "history_workbench", "clarify_before_route"]
    model_id: Optional[str] = None
    task_name: Optional[str] = None
    clarify_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Input quality and validation
# ---------------------------------------------------------------------------


@dataclass
class InputQualityReport:
    """
    Output from the input-governance layer: missing, invalid, out-of-range, low-confidence fields, and overall status.
    Used for pre-prediction validation to decide whether inference may proceed.
    """

    missing_required_features: List[str] = field(default_factory=list)
    invalid_fields: List[str] = field(default_factory=list)
    out_of_range_fields: List[str] = field(default_factory=list)
    low_confidence_fields: List[str] = field(default_factory=list)
    # Unit / scope related warnings (non-blocking; warning-first design)
    unit_context_missing: List[str] = field(default_factory=list)
    unit_mismatch_suspected: List[str] = field(default_factory=list)
    time_window_warnings: List[str] = field(default_factory=list)
    input_quality_status: Literal["ok", "warning", "block"] = "ok"

    @property
    def can_proceed(self) -> bool:
        """Whether prediction may proceed, meaning status is not block."""
        return self.input_quality_status != "block"


@dataclass
class ValidationReport:
    """Shape-compatible with InputQualityReport for API compatibility or aliases; validation currently uses InputQualityReport."""

    missing_required_features: List[str] = field(default_factory=list)
    invalid_fields: List[str] = field(default_factory=list)
    out_of_range_fields: List[str] = field(default_factory=list)
    low_confidence_fields: List[str] = field(default_factory=list)
    input_quality_status: Literal["ok", "warning", "block"] = "ok"

    @property
    def can_proceed(self) -> bool:
        return self.input_quality_status != "block"


# ---------------------------------------------------------------------------
# Image/table extraction results from ExtractorAgent for prediction-page display and user confirmation; not direct model input.
# ---------------------------------------------------------------------------

@dataclass
class ImageExtractionResult:
    """
    Structured extraction result from an image or table for the upload -> review -> clinician confirm/edit -> predict flow.
    - parsed_fields: extracted feature name -> value, used as raw_input_payload only after user confirmation.
    - missing_required_features: features required by the model but not extracted this time.
    - low_confidence_fields: low-confidence extracted feature names that require careful review.
    Image-recognition results must not go directly into the model; they require user confirmation or editing first.
    """

    parsed_fields: Dict[str, Any] = field(default_factory=dict)
    missing_required_features: List[str] = field(default_factory=list)
    low_confidence_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed_fields": self.parsed_fields,
            "missing_required_features": self.missing_required_features,
            "low_confidence_fields": self.low_confidence_fields,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ImageExtractionResult":
        return cls(
            parsed_fields=d.get("parsed_fields") or {},
            missing_required_features=d.get("missing_required_features") or [],
            low_confidence_fields=d.get("low_confidence_fields") or [],
        )


# ---------------------------------------------------------------------------
# Prediction results and explanations as structured output for UI and archive use.
# ---------------------------------------------------------------------------


@dataclass
class PredictionResult:
    """
    Structured output for a single prediction, aligned with the prediction-page output protocol in the architecture docs.
    Used for display and archiving; does not carry intermediate state.
    """

    risk_score: float = 0.0
    predicted_label: str = ""
    threshold: float = 0.5
    top_positive_drivers: List[str] = field(default_factory=list)
    top_negative_drivers: List[str] = field(default_factory=list)
    prediction_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplanationResult:
    """
    Individual-level explanation result for a single sample, separate from training-time global explanations and used only on the prediction page.
    - force_plot / waterfall_plot: references such as file paths or base64 values; large objects are not stored.
    - top_positive_drivers: factors (feature names) that increase risk.
    - top_negative_drivers: factors that decrease risk.
    - narrative_summary: clinician-readable auxiliary explanation text; not treatment advice.
    """

    force_plot: Optional[str] = None
    waterfall_plot: Optional[str] = None
    top_positive_drivers: List[str] = field(default_factory=list)
    top_negative_drivers: List[str] = field(default_factory=list)
    narrative_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for writing into PredictionContext.explanation_cache."""
        return {
            "force_plot": self.force_plot,
            "waterfall_plot": self.waterfall_plot,
            "top_positive_drivers": self.top_positive_drivers,
            "top_negative_drivers": self.top_negative_drivers,
        }


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------


@dataclass
class ModelEntry:
    """
    One model record in the registry, used by ModelRegistry and the prediction path.
    Field notes:
    - model_id: unique identifier
    - task_name: task name such as survival_28d, used for filtering and display
    - task_type: binary / multiclass / regression
    - model_path: local model file path, such as a joblib pipeline
    - required_features: feature-name list required for prediction
    - feature_order: model input feature order, which may match required_features
    - preprocess_config: preprocessing configuration such as feature_bounds, used by InputValidator / preprocessing
    - threshold: binary classification decision threshold
    - label_mapping: label index to display copy, such as {"0":"Low risk","1":"High risk"}
    - version / train_cohort / notes: metadata and notes
    - target_outcome: textual description of the predicted outcome (e.g. "28-day mortality")
    - intended_population: textual description of intended patient population
    - inclusion_scope: textual description of inclusion criteria or applicable settings
    - exclusion_notes: textual description of known exclusions (e.g. "Not validated in pediatric patients")
    - caution_notes: exclusions or caution statements; MUST NOT contain treatment recommendations
    - last_updated: optional ISO date string, e.g. "2025-02-01"
    """

    model_id: str
    task_name: str
    task_type: Literal["binary", "multiclass", "regression"] = "binary"
    model_path: str = ""
    required_features: List[str] = field(default_factory=list)
    feature_order: List[str] = field(default_factory=list)
    preprocess_config: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 0.5
    label_mapping: Dict[str, str] = field(default_factory=dict)
    version: str = "1.0.0"
    train_cohort: Optional[str] = None
    notes: Optional[str] = None
    target_outcome: Optional[str] = None
    intended_population: Optional[str] = None
    inclusion_scope: Optional[str] = None
    exclusion_notes: Optional[str] = None
    caution_notes: Optional[str] = None
    last_updated: Optional[str] = None
    clinical_task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "task_name": self.task_name,
            "task_type": self.task_type,
            "model_path": self.model_path,
            "required_features": self.required_features,
            "feature_order": self.feature_order,
            "preprocess_config": self.preprocess_config,
            "threshold": self.threshold,
            "label_mapping": self.label_mapping,
            "version": self.version,
            "train_cohort": self.train_cohort,
            "notes": self.notes,
            "target_outcome": self.target_outcome,
            "intended_population": self.intended_population,
            "inclusion_scope": self.inclusion_scope,
            "exclusion_notes": self.exclusion_notes,
            "caution_notes": self.caution_notes,
            "last_updated": self.last_updated,
            "clinical_task_id": self.clinical_task_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ModelEntry:
        ct = d.get("clinical_task_id")
        ct_norm = str(ct).strip() if ct is not None and str(ct).strip() else None
        return cls(
            model_id=d.get("model_id", ""),
            task_name=d.get("task_name", ""),
            task_type=d.get("task_type", "binary"),
            model_path=d.get("model_path", ""),
            required_features=d.get("required_features", []),
            feature_order=d.get("feature_order", []),
            preprocess_config=d.get("preprocess_config", {}),
            threshold=float(d.get("threshold", 0.5)),
            label_mapping=d.get("label_mapping") or {},
            version=d.get("version", "1.0.0"),
            train_cohort=d.get("train_cohort"),
            notes=d.get("notes"),
            target_outcome=d.get("target_outcome"),
            intended_population=d.get("intended_population"),
            inclusion_scope=d.get("inclusion_scope"),
            exclusion_notes=d.get("exclusion_notes"),
            caution_notes=d.get("caution_notes"),
            last_updated=d.get("last_updated"),
            clinical_task_id=ct_norm,
        )


# ---------------------------------------------------------------------------
# Session and prediction context, the core state objects in the current architecture.
# ---------------------------------------------------------------------------


@dataclass
class AppSessionContext:
    """
    Application-level session context shared by the home page and routing; does not carry internal training/prediction state.
    - session_id: current session identifier
    - active_route: current target workbench
    - conversation_history: home-page conversation turns
    - intent_summary: latest intent summary from IntakeAgent
    - selected_model_id: model currently selected on the prediction page
    - last_action: latest action type, such as route
    - error: session-level error message
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    active_route: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    intent_summary: Optional[Dict[str, Any]] = None
    current_user_role: str = ""
    selected_model_id: Optional[str] = None
    last_action: str = ""
    error: Optional[str] = None
    # LLM provider reference (not serialized). Typed as Any to avoid core
    # depending directly on the LLM layer.
    llm_provider: Any = field(default=None, repr=False)

    def get_current_route(self) -> str:
        return self.active_route or ""

    def set_route(self, route: str) -> None:
        self.active_route = route
        self.last_action = "route"

    def append_conversation(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})

    def set_intent(self, intent_summary: Optional[Dict[str, Any]]) -> None:
        self.intent_summary = intent_summary

    def set_error(self, msg: Optional[str]) -> None:
        self.error = msg

    def clear_error(self) -> None:
        self.error = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_route": self.active_route,
            "conversation_history": self.conversation_history,
            "intent_summary": self.intent_summary,
            "current_user_role": self.current_user_role,
            "selected_model_id": self.selected_model_id,
            "last_action": self.last_action,
            "error": self.error,
        }


@dataclass
class PredictionContext:
    """
    Prediction workbench context carrying state for one prediction flow, separate from the training PipelineContext.
    - prediction_task: prediction task name, such as survival_28d
    - model_id: current model ID
    - task_type: binary / multiclass / regression
    - required_features: feature list required by the model
    - input_source: manual | table | image
    - raw_input_payload: raw user input keyed by feature name
    - normalized_input_payload: preprocessed model input
    - input_quality_report: validation result, either InputQualityReport or compatible dict
    - risk_score / predicted_label: inference result
    - prediction_metadata: inference-process metadata
    - explanation_cache: explanation cache, such as force_plot, waterfall_plot, and top_*_drivers
    - narrative_summary: clinician-readable narrative
    - save_dir: archive directory for this prediction
    - error: prediction-flow error message
    - loaded_pipeline: model pipeline loaded by PredictionAgent at runtime and reused by ExplainerAgent; not serialized.
    """

    prediction_task: str = ""
    model_id: str = ""
    task_type: str = "binary"
    required_features: List[str] = field(default_factory=list)
    input_source: str = "manual"
    raw_input_payload: Dict[str, Any] = field(default_factory=dict)
    normalized_input_payload: Optional[Dict[str, Any]] = None
    input_quality_report: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    predicted_label: Optional[str] = None
    prediction_metadata: Dict[str, Any] = field(default_factory=dict)
    explanation_cache: Dict[str, Any] = field(default_factory=dict)
    narrative_summary: Optional[str] = None
    save_dir: Optional[Path] = None
    error: Optional[str] = None
    loaded_pipeline: Any = None  # Runtime reuse only; not exported by to_dict.

    def to_dict(self) -> Dict[str, Any]:
        """Serializable dict that excludes non-serializable values."""
        out: Dict[str, Any] = {
            "prediction_task": self.prediction_task,
            "model_id": self.model_id,
            "task_type": self.task_type,
            "required_features": self.required_features,
            "input_source": self.input_source,
            "raw_input_payload": self.raw_input_payload,
            "normalized_input_payload": self.normalized_input_payload,
            "input_quality_report": self.input_quality_report,
            "risk_score": self.risk_score,
            "predicted_label": self.predicted_label,
            "prediction_metadata": self.prediction_metadata,
            "narrative_summary": self.narrative_summary,
            "save_dir": str(self.save_dir) if self.save_dir else None,
            "error": self.error,
        }
        # Keep only serializable items in explanation_cache.
        safe_cache = {}
        for k, v in self.explanation_cache.items():
            if v is None or isinstance(v, (str, int, float, bool, list)):
                safe_cache[k] = v
            elif isinstance(v, dict):
                safe_cache[k] = v
            # Skip ndarray, figures, and similar objects.
        out["explanation_cache"] = safe_cache
        return out
