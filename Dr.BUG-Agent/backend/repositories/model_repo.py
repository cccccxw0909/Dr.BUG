from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _invalidate_model_registry_cache() -> None:
    """File-backed registry was mutated; drop ModelRegistry in-memory cache if loaded."""
    try:
        from backend.config import MODEL_REGISTRY_PATH
        from backend.ml_runtime.core.model_registry import ModelRegistry

        ModelRegistry(MODEL_REGISTRY_PATH).invalidate_cache()
    except Exception:
        logger.debug("model registry cache invalidate failed", exc_info=True)


class FileModelRepo:
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.write_text("[]", encoding="utf-8")
        self.lock = threading.Lock()

    def list(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data = raw.get("models", [])
        elif isinstance(raw, list):
            data = raw
        else:
            data = []
        if task_type:
            data = [item for item in data if item.get("task_type") == task_type]
        return data

    def get(self, model_id: str) -> Optional[Dict[str, Any]]:
        return next(
            (item for item in self.list() if item.get("model_id") == model_id or item.get("id") == model_id),
            None,
        )

    def upsert(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or merge one registry row by model_id (idempotent merge)."""
        mid = entry.get("model_id")
        if not mid:
            raise ValueError("upsert entry must include model_id")
        with self.lock:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                models_list: List[Dict[str, Any]] = list(raw.get("models", []))
            elif isinstance(raw, list):
                models_list = list(raw)
            else:
                models_list = []
            idx = next(
                (
                    i
                    for i, m in enumerate(models_list)
                    if m.get("model_id") == mid or m.get("id") == mid
                ),
                None,
            )
            if idx is not None:
                merged = {**models_list[idx], **entry}
                models_list[idx] = merged
                out = merged
            else:
                models_list.append(dict(entry))
                out = models_list[-1]
            self.registry_path.write_text(
                json.dumps(models_list, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        _invalidate_model_registry_cache()
        return out

    def delete(self, model_id: str) -> bool:
        mid = str(model_id or "").strip()
        if not mid:
            return False
        with self.lock:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                models_list: List[Dict[str, Any]] = list(raw.get("models", []))
            elif isinstance(raw, list):
                models_list = list(raw)
            else:
                models_list = []
            n0 = len(models_list)
            models_list = [
                m
                for m in models_list
                if str(m.get("model_id") or m.get("id") or "").strip() != mid
            ]
            if len(models_list) == n0:
                return False
            self.registry_path.write_text(
                json.dumps(models_list, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        _invalidate_model_registry_cache()
        return True

