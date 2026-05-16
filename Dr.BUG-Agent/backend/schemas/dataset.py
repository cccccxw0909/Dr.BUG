from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class DatasetMeta(BaseModel):
    id: str
    name: str
    file_name: str
    file_path: str
    file_type: str
    created_at: str
    description: str = ""
    available_tasks: List[str] = Field(default_factory=list)


class DatasetColumnInfo(BaseModel):
    name: str
    dtype: str
    is_numeric: bool = False


class DatasetSchemaInfo(BaseModel):
    dataset_id: str
    columns: List[DatasetColumnInfo] = Field(default_factory=list)


class DatasetListResponse(BaseModel):
    status: str = "success"
    total: int
    datasets: List[DatasetMeta]


class GenericResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)

