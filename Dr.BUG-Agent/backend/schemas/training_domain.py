"""Training job domain models (Phase 1: contract layer, aligned with Streamlit StateMachine / PipelineContext).

Defines **DomainTrainingPayload**: the canonical contract between Vue/FastAPI and future StateMachine executors.
Clinical task identity and ML task type are separate fields; do not use a vague combined `task_type`.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

ClinicalTaskId = Literal["clinical_efficacy", "mortality_28d", "polymyxin_resistance", "treatment_duration"]
MlTaskType = Literal["binary", "multiclass", "regression"]
WorkbenchModelType = Literal[
    "xgboost",
    "lightgbm",
    "catboost",
    "random_forest",
    "logistic_regression",
    "svm",
    "knn",
]


class PublishOverrides(BaseModel):
    """Optional overrides when publishing to the model registry (Streamlit Phase5 publish overrides)."""

    model_id: Optional[str] = None
    notes: Optional[str] = None


class TrainingPhase1Payload(BaseModel):
    """
    Chat Phase1: dataset/task, candidate pool, feature-search toggles (Streamlit data check + candidate features).
    Does not collect final_features; model_type / objective_metric are optional (placeholders in task params until Phase4).
    """

    dataset_id: str = Field(..., min_length=1)
    clinical_task_id: ClinicalTaskId = Field(...)
    ml_task_type: MlTaskType = Field(...)
    target_column: str = Field(..., min_length=1)

    med_cols: List[str] = Field(default_factory=list)
    selected_features: List[str] = Field(default_factory=list)
    feature_set: Optional[str] = Field(default=None)

    enable_feature_set_search: bool = Field(default=False)
    min_features: int = Field(default=1, ge=1, le=20)
    max_features: int = Field(default=10, ge=1, le=20)
    use_cv_shap: bool = Field(default=False)
    index_time: Optional[str] = Field(default=None)
    label_time: Optional[str] = Field(default=None)

    model_type: Optional[WorkbenchModelType] = Field(
        default=None,
        description="Optional; if set early it is prefilled in Phase4 (may be omitted in Chat Phase1).",
    )
    objective_metric: Optional[str] = Field(
        default=None,
        description="Optional; defaults to auroc/mse based on ml_task_type when omitted.",
    )

    @field_validator("target_column", mode="before")
    @classmethod
    def _strip_target(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("index_time", "label_time", mode="before")
    @classmethod
    def _empty_time_phase1(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("feature_set", mode="before")
    @classmethod
    def _fs_empty_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return str(v).strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _feature_source_phase1(self) -> TrainingPhase1Payload:
        has_fs = bool(self.feature_set and str(self.feature_set).strip())
        has_sel = len(self.selected_features) > 0
        auto_pool = bool(self.enable_feature_set_search) or bool(self.use_cv_shap)
        if not (has_fs or has_sel or auto_pool):
            raise ValueError(
                "Insufficient feature sources: provide selected_features, a named feature_set, "
                "or enable enable_feature_set_search / use_cv_shap. "
                "Note: med_cols alone does not satisfy the feature-source requirement."
            )
        return self

    @model_validator(mode="after")
    def _bounds_phase1(self) -> TrainingPhase1Payload:
        if self.enable_feature_set_search and self.min_features > self.max_features:
            raise ValueError("When enable_feature_set_search is true, min_features must not exceed max_features")
        return self

    def model_dump_for_task_params(self) -> dict[str, Any]:
        """Serialize into task.params with placeholders and workflow step hints for executors/consumers."""
        base = self.model_dump(mode="json")
        om_default = "mse" if self.ml_task_type == "regression" else "auroc"
        om = str(self.objective_metric).strip() if self.objective_metric else om_default
        mt = self.model_type or "xgboost"
        return {
            **base,
            "final_features": [],
            "enable_search": False,
            "model_type": mt,
            "model_name": None,
            "objective_metric": om,
            "primary_metric": om,
            "publish_overrides": {},
            "train_workflow_step": "phase2",
        }


class DomainTrainingPayload(BaseModel):
    """
    Unified training contract (flat JSON friendly; only publish_overrides is nested).

    feature_set / selected_features / final_features (priority explained in normalizers):
    - final_features: locked modeling columns after Phase3 (Streamlit semantics). If set, the feature plan is fixed.
    - selected_features: candidate feature pool (column list), Streamlit Step0 selected_features.
    - feature_set: named feature group key (e.g. cand16), Workbench preset; coexists with lists per normalizer rules.
    At least one non-empty source is required (see validators).
    """

    dataset_id: str = Field(..., min_length=1, description="Dataset id aligned with task_repo / upload entrypoints")

    clinical_task_id: ClinicalTaskId = Field(
        ...,
        description="Clinical task identifier (business semantics); independent of legacy binary/ml task_type",
    )
    ml_task_type: MlTaskType = Field(
        ...,
        description="ML task type aligned with legacy PipelineContext.task_type / programmer.get_models_for_task",
    )

    target_column: str = Field(
        ...,
        min_length=1,
        description="Target column name (legacy Streamlit target_col); training requires an explicit label column",
    )

    med_cols: List[str] = Field(
        default_factory=list,
        description="Forced-in feature column names (Streamlit med_cols)",
    )
    selected_features: List[str] = Field(
        default_factory=list,
        description="Candidate feature pool column names; when empty with only feature_set, named groups resolve later",
    )
    final_features: List[str] = Field(
        default_factory=list,
        description="Final modeling feature columns; when non-empty the feature plan is locked",
    )

    enable_feature_set_search: bool = Field(default=False, description="Enable feature-set search (Phase2 branch)")
    min_features: int = Field(default=1, ge=1, le=20)
    max_features: int = Field(default=10, ge=1, le=20)

    enable_search: bool = Field(default=False, description="Enable hyperparameter RandomizedSearchCV (Phase4)")
    use_cv_shap: bool = Field(default=False, description="Use 5-fold CV variable importance")

    index_time: Optional[str] = Field(default=None, description="Index time column name or marker (optional)")
    label_time: Optional[str] = Field(default=None, description="Label time (optional)")

    model_type: WorkbenchModelType = Field(
        ...,
        description="Workbench algorithm family (API enum); may coexist with sklearn display model_name",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Optional exact model display name (e.g. XGBoost); preferred by Streamlit/programmer executors",
    )

    feature_set: Optional[str] = Field(
        default=None,
        description="Named feature group key (e.g. cand16); combine with selected_features/final_features per normalizer rules",
    )

    objective_metric: str = Field(
        default="auroc",
        min_length=1,
        description="Primary optimization/display metric (user-selectable); regression often uses mse/mae",
    )
    primary_metric: Optional[str] = Field(
        default=None,
        description="When empty, aligns with objective_metric or is derived by executors from ml_task_type",
    )

    publish_overrides: PublishOverrides = Field(default_factory=PublishOverrides)

    @field_validator("target_column", "objective_metric", mode="before")
    @classmethod
    def _strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("index_time", "label_time", mode="before")
    @classmethod
    def _empty_time_to_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _feature_source_rule(self) -> DomainTrainingPayload:
        has_fs = bool(self.feature_set and str(self.feature_set).strip())
        has_sel = len(self.selected_features) > 0
        has_fin = len(self.final_features) > 0
        auto_pool = bool(self.enable_feature_set_search) or bool(self.use_cv_shap)
        if not (has_fs or has_sel or has_fin or auto_pool):
            raise ValueError(
                "Insufficient feature sources: provide final_features, selected_features, a named feature_set, "
                "or enable enable_feature_set_search / use_cv_shap for the default candidate pool. "
                "Note: med_cols alone does not satisfy the feature-source requirement."
            )
        return self

    @model_validator(mode="after")
    def _feature_search_bounds(self) -> DomainTrainingPayload:
        if self.enable_feature_set_search and self.min_features > self.max_features:
            raise ValueError("When enable_feature_set_search is true, min_features must not exceed max_features")
        return self

    @model_validator(mode="after")
    def _align_primary_metric(self) -> DomainTrainingPayload:
        if not self.primary_metric:
            return self.model_copy(update={"primary_metric": self.objective_metric})
        return self

    def model_dump_for_task_params(self) -> dict[str, Any]:
        """Flat + nested-consistent dict for task params / API (JSON-serializable)."""
        return self.model_dump(mode="json")


# Convenience sets for typing and tests
CLINICAL_TASK_IDS = frozenset(
    {"clinical_efficacy", "mortality_28d", "polymyxin_resistance", "treatment_duration"}
)
ML_TASK_TYPES = frozenset({"binary", "multiclass", "regression"})


