"""Normalize field specifications from ModelEntry + feature_schema.json into the API form schema.

Logic aligns with `get_feature_metadata` in `src/ui/predict_page.py` and merges package-level `features[name]` extension fields.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.ml_runtime.core.published_model_loader import FEATURE_SCHEMA_FILENAME, METADATA_FILENAME
from backend.ml_runtime.core.schemas import ModelEntry

logger = logging.getLogger(__name__)

FIELD_TYPES = ("numeric", "float", "integer", "binary", "categorical", "string", "text")
_NUMERIC_NAME_HINTS = (
    "_dose",
    "_daily_dose",
    "_freq",
    "_daily_freq",
    "_duration",
    "_days",
    "_concentration",
    "_value",
)
_NUMERIC_EXACT_HINTS = {"sofa", "apache", "apacheii", "apache_ii"}


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("read_json failed %s: %s", path, e)
        return None
    return data if isinstance(data, dict) else None


def load_raw_feature_schema_map(package_root: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if package_root is None:
        return {}
    doc = _read_json(package_root / FEATURE_SCHEMA_FILENAME)
    if not doc:
        return {}
    feats = doc.get("features")
    if not isinstance(feats, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for name, spec in feats.items():
        if isinstance(spec, dict):
            out[str(name)] = dict(spec)
    return out


def load_raw_metadata_dict(package_root: Optional[Path]) -> Dict[str, Any]:
    if package_root is None:
        return {}
    doc = _read_json(package_root / METADATA_FILENAME)
    return dict(doc) if doc else {}


def _streamlit_style_feature_meta(entry: ModelEntry, feature: str) -> Dict[str, Any]:
    """Mirror predict_page.get_feature_metadata (without Streamlit)."""
    config = entry.preprocess_config or {}
    units_cfg = config.get("expected_units") or {}
    bounds_cfg = config.get("feature_bounds") or {}
    feature_types = config.get("feature_types") or {}
    feature_options = config.get("feature_options") or {}
    feature_defs = config.get("feature_definitions") or {}

    unit = units_cfg.get(feature) if isinstance(units_cfg, dict) else None
    bounds = bounds_cfg.get(feature) if isinstance(bounds_cfg, dict) else None
    fd0 = feature_defs.get(feature) if isinstance(feature_defs.get(feature), dict) else {}
    raw_t = (feature_types.get(feature) or fd0.get("type") or "numeric")
    field_type = str(raw_t).strip().lower() if raw_t else "numeric"
    if field_type not in FIELD_TYPES:
        field_type = "numeric"
    options = feature_options.get(feature) or fd0.get("options")
    if options is not None and not isinstance(options, list):
        options = None

    def _humanize(name: str) -> str:
        return name.replace("_", " ").strip().title()

    label = None
    if isinstance(feature_defs.get(feature), dict):
        label = feature_defs[feature].get("label")
    if not label:
        label = _humanize(feature)
        if unit:
            label = f"{label} ({unit})"

    reference_range: Optional[str] = None
    if isinstance(bounds, dict):
        lo, hi = bounds.get("min"), bounds.get("max")
        if lo is not None and hi is not None:
            reference_range = f"Reference: {lo}–{hi}"
        elif lo is not None:
            reference_range = f"Reference: ≥ {lo}"
        elif hi is not None:
            reference_range = f"Reference: ≤ {hi}"

    description = fd0.get("help") if isinstance(fd0.get("help"), str) else None
    group = fd0.get("group") if isinstance(fd0.get("group"), str) else None

    return {
        "label": label,
        "unit": unit,
        "reference_range": reference_range,
        "field_type": field_type,
        "options": options,
        "description": description,
        "group": group,
        "bounds": bounds if isinstance(bounds, dict) else None,
    }


def _looks_numeric_feature_name(name: str) -> bool:
    n = str(name or "").strip().lower()
    if not n:
        return False
    if n in _NUMERIC_EXACT_HINTS:
        return True
    if n.startswith("egfr"):
        return True
    if any(n.endswith(sfx) for sfx in _NUMERIC_NAME_HINTS):
        return True
    if re.search(r"(?:^|[_\-\s])(sofa|apache)(?:$|[_\-\s]|\d)", n):
        return True
    return False


def _api_type(streamlit_type: str, raw_spec: Dict[str, Any], feature_name: str) -> str:
    t = streamlit_type.strip().lower()
    raw_json = str(raw_spec.get("type", "") or "").strip().lower()
    if (raw_json == "binary" or t == "binary") and _looks_numeric_feature_name(feature_name):
        logger.warning(
            "feature_schema type corrected to numeric by name hint: feature=%s raw_type=%s streamlit_type=%s",
            feature_name,
            raw_json or "(empty)",
            t or "(empty)",
        )
        return "float"
    if raw_json in ("int", "integer"):
        return "int"
    if raw_json in ("float", "double", "numeric", "number"):
        return "float"
    if raw_json in ("binary",):
        return "binary"
    if raw_json in ("categorical",):
        return "categorical"
    if raw_json in ("string", "text", "str"):
        return "string"
    if t in ("integer",):
        return "int"
    if t in ("numeric", "float"):
        return "float"
    if t == "binary":
        return "binary"
    if t == "categorical":
        return "categorical"
    return "float"


def _merge_options(sm_opts: Any, raw_opts: Any) -> Optional[List[Any]]:
    if isinstance(raw_opts, list) and raw_opts:
        return list(raw_opts)
    if isinstance(sm_opts, list) and sm_opts:
        return list(sm_opts)
    return None


def build_form_fields(entry: ModelEntry, raw_by_feature: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = list(entry.feature_order or entry.required_features or [])
    rows: List[Dict[str, Any]] = []
    for name in order:
        sm = _streamlit_style_feature_meta(entry, name)
        raw = raw_by_feature.get(name) or {}
        api_type = _api_type(sm["field_type"], raw, name)

        default = raw.get("default") if "default" in raw else None
        req = raw.get("required")
        if isinstance(req, bool):
            required = req
        else:
            required = not bool(raw.get("allow_missing", True))

        bounds = sm.get("bounds") or {}
        rmin = raw.get("min") if "min" in raw else bounds.get("min")
        rmax = raw.get("max") if "max" in raw else bounds.get("max")

        unit = raw.get("unit") if raw.get("unit") is not None else sm.get("unit")
        ref = sm.get("reference_range")
        desc = raw.get("description") if isinstance(raw.get("description"), str) else sm.get("description")
        grp = raw.get("group") if isinstance(raw.get("group"), str) else sm.get("group")
        label = raw.get("label") if isinstance(raw.get("label"), str) else None
        if not label:
            label = raw.get("display_name") if isinstance(raw.get("display_name"), str) else sm.get("label")
        options = _merge_options(sm.get("options"), raw.get("options"))

        rows.append(
            {
                "name": name,
                "label": str(label or name),
                "type": api_type,
                "required": required,
                "default": default,
                "options": options,
                "unit": unit,
                "reference_range": ref,
                "min": rmin,
                "max": rmax,
                "description": desc,
                "group": grp,
            }
        )
    return rows


def metadata_for_response(full_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Metadata subset for frontend display, avoiding overly large or unused fields."""
    keys = (
        "model_id",
        "task_name",
        "clinical_task_id",
        "target_name",
        "task_type",
        "version",
        "threshold",
        "label_mapping",
        "positive_class",
        "negative_class",
        "notes",
        "target_outcome",
        "intended_population",
        "has_shap",
        "show_shap",
        "shap_plot_types",
    )
    out: Dict[str, Any] = {}
    for k in keys:
        if k in full_meta:
            out[k] = full_meta[k]
    return out


def supports_shap_from_metadata(meta: Dict[str, Any]) -> bool:
    if meta.get("has_shap") is True:
        return True
    if meta.get("show_shap") is True:
        return True
    return False
