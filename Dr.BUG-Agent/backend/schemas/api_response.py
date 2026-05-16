from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.schemas.dataset import DatasetMeta, DatasetSchemaInfo
from backend.schemas.agent import ActionConfirmData, ChatTurnData, PendingAction
from backend.schemas.model import ModelItem
from backend.schemas.task import Task, TaskStatusView


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    error_code: str


class TaskListData(BaseModel):
    items: List[Task]
    total: int


class TaskListSuccessResponse(BaseModel):
    status: str = "success"
    data: TaskListData


class TaskDetailData(BaseModel):
    task: Task
    task_summary: Optional[Dict[str, Any]] = None
    logs: List[Dict[str, str]] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(default_factory=dict)


class TaskDetailSuccessResponse(BaseModel):
    status: str = "success"
    data: TaskDetailData


class TaskStatusData(BaseModel):
    task: TaskStatusView


class TaskStatusSuccessResponse(BaseModel):
    status: str = "success"
    data: TaskStatusData


class TaskArtifactsData(BaseModel):
    job_id: str
    artifacts: Dict[str, str] = Field(default_factory=dict)


class TaskArtifactsSuccessResponse(BaseModel):
    status: str = "success"
    data: TaskArtifactsData


class DatasetListData(BaseModel):
    items: List[DatasetMeta]
    total: int


class DatasetListSuccessResponse(BaseModel):
    status: str = "success"
    data: DatasetListData


class DatasetDetailData(BaseModel):
    dataset: DatasetMeta


class DatasetDetailSuccessResponse(BaseModel):
    status: str = "success"
    data: DatasetDetailData


class DatasetUploadData(BaseModel):
    dataset: DatasetMeta


class DatasetUploadSuccessResponse(BaseModel):
    status: str = "success"
    data: DatasetUploadData


class DatasetSchemaData(BaseModel):
    schema: DatasetSchemaInfo


class DatasetSchemaSuccessResponse(BaseModel):
    status: str = "success"
    data: DatasetSchemaData


class ModelListData(BaseModel):
    items: List[ModelItem]
    total: int


class ModelListSuccessResponse(BaseModel):
    status: str = "success"
    data: ModelListData


class ModelDetailData(BaseModel):
    model: ModelItem


class ModelDetailSuccessResponse(BaseModel):
    status: str = "success"
    data: ModelDetailData


class TaskCancelData(BaseModel):
    message: str
    job_id: str


class TaskCancelSuccessResponse(BaseModel):
    status: str = "success"
    data: TaskCancelData


class TaskDeleteData(BaseModel):
    message: str
    job_id: str


class TaskDeleteSuccessResponse(BaseModel):
    status: str = "success"
    data: TaskDeleteData


class ChatTurnSuccessResponse(BaseModel):
    status: str = "success"
    data: ChatTurnData


class ActionConfirmSuccessResponse(BaseModel):
    status: str = "success"
    data: ActionConfirmData


class PendingActionDetailData(BaseModel):
    pending_action: PendingAction


class PendingActionDetailSuccessResponse(BaseModel):
    status: str = "success"
    data: PendingActionDetailData

