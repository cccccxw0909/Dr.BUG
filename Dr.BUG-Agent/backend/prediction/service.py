from __future__ import annotations

from typing import Any, Dict, Optional

from backend.ml_runtime.core.model_registry import ModelRegistry
from backend.ml_runtime.core.schemas import ModelEntry

from backend.config import MODEL_REGISTRY_PATH
from backend.prediction.available_models import list_prediction_models, registry_display_name
from backend.prediction.schema_adapter import (
    build_form_fields,
    load_raw_feature_schema_map,
    load_raw_metadata_dict,
    metadata_for_response,
)
from backend.runtime import model_repo


def _registry() -> ModelRegistry:
    return ModelRegistry(MODEL_REGISTRY_PATH)


def resolve_prediction_display_name(model_id: str, entry: ModelEntry) -> str:
    """Single display label aligned with registry JSON + GET /models (no task — id concatenation)."""
    raw_row: Dict[str, Any] = dict(model_repo.get(model_id) or {})
    return registry_display_name(raw_row, entry)


def get_model_schema_bundle(model_id: str) -> Optional[Dict[str, Any]]:
    reg = _registry()
    entry = reg.get(model_id)
    if entry is None:
        return None
    root = reg.get_package_root(model_id)
    raw_map = load_raw_feature_schema_map(root)
    full_meta = load_raw_metadata_dict(root)
    meta_subset = metadata_for_response({**entry.to_dict(), **full_meta})
    fields = build_form_fields(entry, raw_map)
    disp = resolve_prediction_display_name(model_id, entry)
    return {
        "model_id": entry.model_id,
        "display_name": disp,
        "task_name": entry.task_name,
        "model_type": entry.task_type,
        "feature_order": list(entry.feature_order or entry.required_features or []),
        "fields": fields,
        "metadata": meta_subset,
    }