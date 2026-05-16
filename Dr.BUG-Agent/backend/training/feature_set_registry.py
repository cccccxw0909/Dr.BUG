"""Named feature-set resolution: load column names from the JSON registry and fail clearly when not configured."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from backend.config import RUNTIME_DIR

_PRESETS_PATH = RUNTIME_DIR / "config" / "feature_set_presets.json"
_cache: Dict[str, List[str]] | None = None


def _load_registry() -> Dict[str, List[str]]:
    global _cache
    if _cache is not None:
        return _cache
    _PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _PRESETS_PATH.exists():
        _PRESETS_PATH.write_text("{}", encoding="utf-8")
    raw = json.loads(_PRESETS_PATH.read_text(encoding="utf-8"))
    out: Dict[str, List[str]] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, list):
                out[str(k).strip()] = [str(x).strip() for x in v if str(x).strip()]
    _cache = out
    return out


def reload_feature_set_presets() -> None:
    global _cache
    _cache = None


def resolve_named_feature_set(name: str) -> List[str]:
    """Resolve a named group to a column-name list; raise ValueError if it is not registered."""
    key = str(name).strip()
    if not key:
        raise ValueError("feature_set is empty")
    reg = _load_registry()
    cols = reg.get(key)
    if not cols:
        raise ValueError(
            f"Cannot resolve named feature set {key!r}: configure "
            f'"{key}": ["column1", "column2", ...] in {_PRESETS_PATH}, or use final_features / selected_features to specify columns directly.'
        )
    return list(cols)
