from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    model_id: str
    task_type: Optional[str] = None
    task_name: Optional[str] = None
    display_name: Optional[str] = None
    model_name: Optional[str] = None
    name: Optional[str] = None
    model_path: Optional[str] = None
    version: Optional[str] = None
    required_features: List[str] = Field(default_factory=list)
    feature_order: List[str] = Field(default_factory=list)
    preprocess_config: Dict[str, Any] = Field(default_factory=dict)
    # Training artifacts / registry extension fields shared by list and detail responses; validation supplies defaults when missing.
    source_job_id: Optional[str] = None
    dataset_id: Optional[str] = None
    clinical_task_id: Optional[str] = None
    ml_task_type: Optional[str] = None
    target_column: Optional[str] = None
    objective_metric: Optional[str] = None
    model_type: Optional[str] = None
    feature_set: Optional[str] = None
    is_published: Optional[bool] = None
    published_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    key_metrics: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

