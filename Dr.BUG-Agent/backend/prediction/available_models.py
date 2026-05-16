"""Build prediction model lists from the same file-backed registry as GET /models."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.ml_runtime.core.model_registry import ModelRegistry
from backend.ml_runtime.core.schemas import ModelEntry

from backend.config import MODEL_REGISTRY_PATH
from backend.prediction.schema_adapter import load_raw_metadata_dict, supports_shap_from_metadata
from backend.prediction.task_keys import (
    CANONICAL_TASK_KEYS,
    CLINICAL_EFFICACY,
    POLYMYXIN_RESISTANCE,
    SURVIVAL_OUTCOME,
    TREATMENT_DURATION,
    normalize_clinical_task_id,
)
from backend.runtime import model_repo

logger = logging.getLogger(__name__)

_SEP = " — "


def normalize_duplicate_em_dash_label(label: str) -> str:
    """Collapse `X — X` (same token) to `X` to avoid duplicated display names."""
    t = (label or "").strip()
    if not t or _SEP not in t:
        return t
    parts = t.split(_SEP)
    if len(parts) == 2 and parts[0].strip() == parts[1].strip():
        return parts[0].strip()
    return t


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _prediction_record_sort_key(rec: Dict[str, Any]) -> Tuple[float, float, str, str]:
    """
    published_at desc, registered_at desc, display_name asc, model_id asc.
    Missing timestamps sort after rows that have them (within the same tier).
    """
    pub = _parse_iso_datetime(rec.get("published_at"))
    reg = _parse_iso_datetime(rec.get("registered_at"))
    pub_k = pub.timestamp() if pub else float("-inf")
    reg_k = reg.timestamp() if reg else float("-inf")
    dn = (rec.get("display_name") or "").lower()
    mid = rec.get("model_id") or ""
    return (-pub_k, -reg_k, dn, mid)


def _normalize_ml_task_kind(raw: Optional[str]) -> str:
    s = (raw or "").strip().lower()
    if s in ("multiclass", "multi_class", "multinomial"):
        return "multiclass"
    if s in ("regression", "continuous"):
        return "regression"
    if s in ("binary", "binary_classification", "classification"):
        return "binary"
    return "binary"


def _coerce_entry(reg: ModelRegistry, raw: Dict[str, Any]) -> Optional[ModelEntry]:
    mid = str(raw.get("model_id") or raw.get("id") or "").strip()
    if not mid:
        return None
    got = reg.get(mid)
    if got is not None:
        return got
    d = dict(raw)
    d["model_id"] = mid
    d["task_type"] = _normalize_ml_task_kind(str(d.get("task_type") or d.get("ml_task_type") or "binary"))
    tn = d.get("task_name") or d.get("clinical_task_id") or ""
    d["task_name"] = str(tn).strip() or "model"
    try:
        return ModelEntry.from_dict(d)
    except (TypeError, ValueError) as e:
        logger.warning("ModelEntry.from_dict failed for model_id=%s: %s", mid, e)
        return None


def _is_ml_task_kind_token(s: str) -> bool:
    k = str(s or "").strip().lower().replace(" ", "_").replace("-", "_")
    return k in {
        "binary",
        "multiclass",
        "regression",
        "binary_classification",
        "classification",
        "multi_class",
        "multinomial",
        "continuous",
        "multilabel",
    }


def registry_display_name(raw: Dict[str, Any], entry: ModelEntry) -> str:
    """display_name > model_name > name > model_id (no task_name — avoids generic clinical ids as title)."""
    for key in ("display_name", "model_name", "name", "model_id"):
        v = raw.get(key)
        if v is not None and str(v).strip():
            return normalize_duplicate_em_dash_label(str(v).strip())
    return normalize_duplicate_em_dash_label((entry.model_id or "").strip() or "model")


def extract_algorithm(raw: Dict[str, Any], meta: Dict[str, Any]) -> Optional[str]:
    """Estimator only (LightGBM, …). Never use ML task kind (binary, …) as algorithm."""
    md = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    # Registry rows from training store the estimator in model_type (see pipeline upsert).
    candidates = [
        raw.get("model_family"),
        raw.get("model_type"),
        md.get("model_family"),
        md.get("model_type"),
        meta.get("estimator"),
        meta.get("algorithm"),
        md.get("estimator"),
        md.get("algorithm"),
        meta.get("model_type"),
    ]
    for c in candidates:
        if c is None:
            continue
        s = str(c).strip()
        if not s or _is_ml_task_kind_token(s):
            continue
        return s
    return None


def _feature_list(entry: ModelEntry, raw: Dict[str, Any]) -> List[str]:
    if entry.feature_order:
        return [str(x) for x in entry.feature_order if str(x).strip()]
    if entry.required_features:
        return [str(x) for x in entry.required_features if str(x).strip()]
    fo = raw.get("feature_order")
    if isinstance(fo, list) and fo:
        return [str(x) for x in fo if str(x).strip()]
    rf = raw.get("required_features") or raw.get("final_features")
    if isinstance(rf, list) and rf:
        return [str(x) for x in rf if str(x).strip()]
    return []


def _is_published_raw(raw: Dict[str, Any], has_usable_features: bool, joblib_ok: bool) -> bool:
    if "is_published" in raw:
        return bool(raw.get("is_published"))
    return bool(has_usable_features and joblib_ok)


def _infer_task_key_from_text_bundle(raw: Dict[str, Any], entry: ModelEntry) -> Optional[str]:
    """
    Last-resort task classification when clinical_task_id was missing on older registry rows.
    Conservative substring checks on stable ids — avoids dropping released models from filtered pickers.
    """
    blob = " ".join(
        [
            str(raw.get("task_name") or ""),
            str(raw.get("model_id") or ""),
            str(entry.task_name or ""),
            str(entry.model_id or ""),
        ]
    ).lower()
    if "clinical_efficacy" in blob or "clinical_outcome" in blob:
        return CLINICAL_EFFICACY
    if "mortality_28d" in blob or "survival_outcome" in blob:
        return SURVIVAL_OUTCOME
    if "polymyxin_resistance" in blob:
        return POLYMYXIN_RESISTANCE
    if "treatment_duration" in blob:
        return TREATMENT_DURATION
    return None


def _package_has_feature_schema(reg: ModelRegistry, model_id: str) -> bool:
    root = reg.get_package_root(model_id)
    if root is None:
        return False
    return (root / "feature_schema.json").exists()


def build_prediction_model_records(
    *,
    task_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Single source for prediction pickers: rows from model_repo merged with ModelRegistry paths.

    task_filter: optional canonical key (one of CANONICAL_TASK_KEYS); None returns all released models.
    """
    if task_filter is not None and task_filter not in CANONICAL_TASK_KEYS:
        return []

    reg = ModelRegistry(MODEL_REGISTRY_PATH)
    reg.invalidate_cache()
    rows = model_repo.list()
    out: List[Dict[str, Any]] = []

    for raw in rows:
        if not isinstance(raw, dict):
            continue
        entry = _coerce_entry(reg, raw)
        if entry is None:
            continue

        mid = entry.model_id
        feats = _feature_list(entry, raw)
        has_usable_features = len(feats) > 0
        mf_path = reg.resolve_model_path(mid)
        joblib_ok = mf_path is not None and mf_path.is_file()
        has_file_schema = _package_has_feature_schema(reg, mid)
        has_schema = bool(has_file_schema or has_usable_features)

        root = reg.get_package_root(mid)
        if root is None and mf_path is not None and mf_path.is_file():
            parent = mf_path.parent
            if (parent / "metadata.json").exists():
                root = parent

        meta: Dict[str, Any] = {}
        if root is not None:
            meta = load_raw_metadata_dict(root)
        has_meta = bool(meta)

        ct_raw = raw.get("clinical_task_id") or getattr(entry, "clinical_task_id", None) or meta.get("clinical_task_id")
        clinical_task_id = str(ct_raw).strip() if ct_raw is not None and str(ct_raw).strip() else None
        task_key = normalize_clinical_task_id(clinical_task_id)
        if task_key is None:
            meta_ct = meta.get("clinical_task_id") if isinstance(meta.get("clinical_task_id"), str) else None
            task_key = normalize_clinical_task_id(meta_ct)
        if task_key is None:
            md = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
            task_key = normalize_clinical_task_id(str(md.get("clinical_task_id") or "").strip() or None)
        if task_key is None:
            task_key = _infer_task_key_from_text_bundle(raw, entry)

        if task_filter is not None and task_key != task_filter:
            continue

        published = _is_published_raw(raw, has_usable_features, joblib_ok)
        if not published:
            continue

        ml_kind = _normalize_ml_task_kind(str(raw.get("ml_task_type") or raw.get("task_type") or entry.task_type))

        algo = extract_algorithm(raw, meta)
        disp = registry_display_name(raw, entry)
        mn = raw.get("model_name")
        name_opt = str(mn).strip() if mn is not None and str(mn).strip() else None

        summary = (entry.notes or entry.target_outcome or "").strip() or None
        version = str(raw.get("version") or entry.version or "").strip() or None
        published_at = str(raw.get("published_at") or "").strip() or None
        registered_at = str(raw.get("created_at") or "").strip() or None
        released_at = str(raw.get("published_at") or raw.get("created_at") or "").strip() or None

        out.append(
            {
                "model_id": mid,
                "display_name": disp,
                "name": name_opt,
                "model_name": name_opt,
                "task_name": entry.task_name or "",
                "task_key": task_key,
                "clinical_task_id": clinical_task_id,
                # Estimator / family only — never ML task kind (binary, …).
                "algorithm": algo,
                "model_family": algo,
                "model_type": algo or "",
                "model_kind": ml_kind,
                "version": version,
                "published_at": published_at or None,
                "registered_at": registered_at or None,
                "released_at": released_at,
                "feature_count": len(feats),
                "required_features": feats,
                "status": "released" if published else "unpublished",
                "is_published": published,
                "package_path": str(root) if root else entry.model_path,
                "registry_path": str(MODEL_REGISTRY_PATH),
                "has_schema": has_schema,
                "has_metadata": has_meta,
                "supports_shap": supports_shap_from_metadata(meta) if has_meta else False,
                "summary": summary,
            }
        )

    out.sort(key=_prediction_record_sort_key)
    return out


def list_prediction_models() -> List[Dict[str, Any]]:
    """Backward-compatible list for GET /prediction/models."""
    return build_prediction_model_records(task_filter=None)
