from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    """Waiting for the user to confirm next-stage parameters in chat or task details for the multi-stage training workflow."""
    waiting_user = "waiting_user"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class JobType(str, Enum):
    train_model = "train_model"
    predict_outcome = "predict_outcome"
    generate_shap = "generate_shap"
    recommend_regimen = "recommend_regimen"
    generate_report = "generate_report"
    publish_model = "publish_model"


class Task(BaseModel):
    id: str
    job_type: JobType
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    current_stage: str
    message: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[Dict[str, Any]] = None
    artifacts: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskStatusView(BaseModel):
    id: str
    job_type: JobType
    status: TaskStatus
    progress: int
    current_stage: str
    message: str
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskDetailResponse(BaseModel):
    status: str = "success"
    job: Task
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    status: str = "success"
    total: int
    jobs: List[Task]


class TrainingWorkflowRequest(BaseModel):
    """Task details / API: advance the human gate for multi-stage training."""

    action: Literal["confirm_final_features", "confirm_train_config", "confirm_publish"]
    final_features: Optional[List[str]] = None
    model_type: Optional[str] = None
    objective_metric: Optional[str] = None
    model_name: Optional[str] = None
    enable_search: Optional[bool] = None
    do_publish: Optional[bool] = None
    publish_overrides: Optional[Dict[str, Any]] = None

