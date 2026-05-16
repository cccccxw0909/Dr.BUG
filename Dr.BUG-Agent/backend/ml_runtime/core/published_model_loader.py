"""Load metadata.json and feature_schema.json from a published model package directory.

Maps package format into ModelEntry-compatible fields. Used when registry entry
model_path points to a package directory (contains model.joblib, metadata.json, feature_schema.json).
Does not load SHAP artifacts (P1).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .schemas import ModelEntry

logger = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"
FEATURE_SCHEMA_FILENAME = "feature_schema.json"
MODEL_FILENAME = "model.joblib"


def _normalize_task_type(raw: str) -> str:
    """Map package task_type to ModelEntry task_type (binary, multiclass, regression)."""
    if not raw:
        return "binary"
    s = str(raw).strip().lower()
    if s in ("binary", "multiclass", "regression"):
        return s
    if s in ("binary_classification", "binary_class"):
        return "binary"
    if "regress" in s:
        return "regression"
    if "multi" in s or "multiclass" in s:
        return "multiclass"
    return "binary"


def _label_mapping_from_metadata(meta: Dict[str, Any]) -> Dict[str, str]:
    """Build label_mapping from positive_class/negative_class or default."""
    pos = meta.get("positive_class")
    neg = meta.get("negative_class")
    if pos is not None and neg is not None:
        return {
            str(neg): "Low risk",
            str(pos): "High risk",
        }
    existing = meta.get("label_mapping")
    if isinstance(existing, dict):
        return {str(k): str(v) for k, v in existing.items()}
    return {"0": "Low risk", "1": "High risk"}


def load_metadata(package_root: Path) -> Optional[Dict[str, Any]]:
    """
    Read metadata.json from package_root. Returns dict with keys aligned to ModelEntry
    (task_type normalized, task_name, threshold, label_mapping, version, etc.).
    Returns None if file missing or invalid.
    """
    path = package_root / METADATA_FILENAME
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path, e)
        return None
    if not isinstance(data, dict):
        return None

    task_type = _normalize_task_type(data.get("task_type", "binary"))
    task_name = data.get("target_name") or data.get("task_name") or data.get("model_id") or ""
    threshold = float(data.get("threshold", 0.5))
    label_mapping = _label_mapping_from_metadata(data)
    version = str(data.get("version", "1.0.0"))

    return {
        "task_type": task_type,
        "task_name": task_name,
        "threshold": threshold,
        "label_mapping": label_mapping,
        "version": version,
        "model_id": data.get("model_id"),
        "notes": data.get("notes"),
    }


def load_feature_schema(package_root: Path) -> Optional[Dict[str, Any]]:
    """
    Read feature_schema.json from package_root. Returns dict with required_features,
    feature_order, and preprocess_config (feature_types, feature_definitions for UI).
    Returns None if file missing or invalid.
    """
    path = package_root / FEATURE_SCHEMA_FILENAME
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path, e)
        return None
    if not isinstance(data, dict):
        return None

    feature_order = data.get("feature_order")
    if not isinstance(feature_order, list):
        feature_order = []
    required_features = list(feature_order)

    features = data.get("features") or {}
    feature_types: Dict[str, str] = {}
    feature_definitions: Dict[str, Dict[str, Any]] = {}
    for name, spec in features.items():
        if not isinstance(spec, dict):
            continue
        t = spec.get("type", "numeric")
        if isinstance(t, str):
            feature_types[name] = t.strip().lower() if t else "numeric"
        label = spec.get("display_name") or spec.get("label") or name
        feature_definitions[name] = {"label": label, "type": feature_types.get(name, "numeric")}

    preprocess_config: Dict[str, Any] = {
        "feature_types": feature_types,
        "feature_definitions": feature_definitions,
    }

    return {
        "required_features": required_features,
        "feature_order": feature_order,
        "preprocess_config": preprocess_config,
    }


def merge_package_into_entry(base_entry: ModelEntry, package_root: Path) -> ModelEntry:
    """
    Load metadata.json and feature_schema.json from package_root and merge into a copy
    of base_entry. Preserves base_entry.model_id and base_entry.model_path.
    Returns the merged ModelEntry.
    """
    merged = ModelEntry(
        model_id=base_entry.model_id,
        task_name=base_entry.task_name,
        task_type=base_entry.task_type,
        model_path=base_entry.model_path,
        required_features=list(base_entry.required_features),
        feature_order=list(base_entry.feature_order),
        preprocess_config=dict(base_entry.preprocess_config),
        threshold=base_entry.threshold,
        label_mapping=dict(base_entry.label_mapping),
        version=base_entry.version,
        train_cohort=base_entry.train_cohort,
        notes=base_entry.notes,
        target_outcome=base_entry.target_outcome,
        intended_population=base_entry.intended_population,
        inclusion_scope=base_entry.inclusion_scope,
        exclusion_notes=base_entry.exclusion_notes,
        caution_notes=base_entry.caution_notes,
        last_updated=base_entry.last_updated,
        clinical_task_id=base_entry.clinical_task_id,
    )

    raw_meta_path = package_root / METADATA_FILENAME
    if raw_meta_path.exists():
        try:
            with open(raw_meta_path, "r", encoding="utf-8") as f:
                raw_meta_full = json.load(f)
            if isinstance(raw_meta_full, dict):
                rct = raw_meta_full.get("clinical_task_id")
                if rct is not None and str(rct).strip():
                    merged.clinical_task_id = str(rct).strip()
        except (json.JSONDecodeError, OSError):
            pass

    meta = load_metadata(package_root)
    if meta:
        if meta.get("task_type"):
            merged.task_type = meta["task_type"]
        if meta.get("task_name"):
            merged.task_name = meta["task_name"]
        if "threshold" in meta:
            merged.threshold = meta["threshold"]
        if meta.get("label_mapping"):
            merged.label_mapping = meta["label_mapping"]
        if meta.get("version"):
            merged.version = meta["version"]
        if meta.get("notes") is not None:
            merged.notes = meta["notes"]

    schema = load_feature_schema(package_root)
    if schema:
        if schema.get("required_features"):
            merged.required_features = schema["required_features"]
        if schema.get("feature_order"):
            merged.feature_order = schema["feature_order"]
        if schema.get("preprocess_config"):
            merged.preprocess_config.update(schema["preprocess_config"])

    return merged
