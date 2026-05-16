"""ModelRegistry: model registry for querying model configuration by task_name or model_id.

Model information is not hard-coded in the UI or agents; this module loads it from models/registry.json.
It provides required_features, threshold, model_path, and related fields to the prediction page, RouterAgent, and PredictionStateMachine.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from .schemas import ModelEntry
from .published_model_loader import merge_package_into_entry

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Manage callable models by loading registry.json and querying by model_id or task_name.
    Returns ModelEntry values with required_features, feature_order, threshold, label_mapping, model_path, task_type, and related fields.
    Decoupled from the training pipeline; future real-model integration only needs to load by model_path without changing the interface.
    """

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self._path = Path(registry_path) if registry_path else Path("models/registry.json")
        self._cache: Optional[List[ModelEntry]] = None

    def _ensure_dir(self) -> None:
        """Ensure the registry directory exists."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> List[ModelEntry]:
        """Load registry.json from disk and return ModelEntry values; return an empty list if missing or loading fails."""
        if self._cache is not None:
            return self._cache
        if not self._path.exists():
            logger.info("Registry not found: %s, using empty list", self._path)
            self._cache = []
            return self._cache
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning("Registry JSON invalid: %s", e)
            self._cache = []
            return self._cache
        except OSError as e:
            logger.warning("Registry read failed: %s", e)
            self._cache = []
            return self._cache

        if isinstance(data, list):
            raw = data
        elif isinstance(data, dict):
            raw = data.get("models")
        else:
            raw = None
        if not isinstance(raw, list):
            logger.warning("Registry root is not a list and has no 'models' list, using empty")
            self._cache = []
            return self._cache

        entries: List[ModelEntry] = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                logger.warning("Registry models[%s] is not a dict, skip", i)
                continue
            try:
                entry = ModelEntry.from_dict(item)
                if not entry.model_id:
                    logger.warning("Registry models[%s] has empty model_id, skip", i)
                    continue
                entries.append(entry)
            except (TypeError, ValueError) as e:
                logger.warning("Registry models[%s] parse error: %s, skip", i, e)
                continue
        self._cache = entries
        return self._cache

    def _save(self, entries: List[ModelEntry]) -> None:
        """Write ModelEntry values back to registry.json."""
        self._ensure_dir()
        data = {"models": [e.to_dict() for e in entries]}
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("Registry save failed: %s", e)
            return
        self._cache = entries

    def get(self, model_id: str) -> Optional[ModelEntry]:
        """
        Return one model configuration by model_id, or None if it does not exist.
        If the entry model_path points to a published package directory containing metadata.json, load metadata/feature_schema from the package and merge them into the returned entry.
        Callers can directly use entry.required_features, feature_order, threshold, label_mapping, model_path, and task_type.
        """
        if not (model_id or "").strip():
            return None
        entry = None
        for e in self._load():
            if e.model_id == model_id:
                entry = e
                break
        if entry is None:
            return None
        package_root = self.get_package_root(model_id)
        if package_root is not None:
            return merge_package_into_entry(entry, package_root)
        return entry

    def list_models(self, task_name: Optional[str] = None) -> List[ModelEntry]:
        """
        Return model entries. If task_name is provided, return only models for that task; otherwise return all models.
        """
        entries = self._load()
        if not (task_name or "").strip():
            return list(entries)
        return [e for e in entries if e.task_name == task_name]

    def list_task_names(self) -> List[str]:
        """Return all task_name values in the current registry, deduplicated and ordered, for UI filtering and similar use."""
        names = sorted({e.task_name for e in self._load() if e.task_name})
        return names

    def register(self, entry: ModelEntry) -> None:
        """Register or overwrite one model; the same model_id replaces the existing entry."""
        if not (entry.model_id or "").strip():
            logger.warning("Register skipped: empty model_id")
            return
        entries = self._load()
        entries = [e for e in entries if e.model_id != entry.model_id]
        entries.append(entry)
        self._save(entries)
        logger.info("Registered model: %s (task: %s)", entry.model_id, entry.task_name)

    def _task_runtime_dir(self) -> Path:
        """Training task artifact root, matching the backend StaticFiles mount (/static -> TASK_DIR)."""
        project_root = self._path.resolve().parent.parent
        return project_root / "backend" / "runtime_data" / "tasks"

    def _resolve_http_static_artifact(self, url: str) -> Optional[Path]:
        """
        registry may contain model_path values in STATIC_BASE_URL form after training publication.
        Resolve them to local artifact paths to avoid Path() mis-parsing values like models/http:/...
        Expected path shape: .../static/{job_id}/artifacts/model.joblib
        """
        try:
            parsed = urlparse(url.strip())
        except (TypeError, ValueError):
            return None
        if parsed.scheme not in ("http", "https"):
            return None
        path = (parsed.path or "").lstrip("/")
        if not path.startswith("static/"):
            return None
        rel = path[len("static/") :]
        if not rel:
            return None
        p = (self._task_runtime_dir() / rel).resolve()
        return p

    def resolve_model_path(self, model_id: str) -> Optional[Path]:
        """
        Return the local absolute path for the model matching model_id.
        Relative model_path values are resolved relative to the registry.json directory.
        If the resolved path is a directory (published package root), return <dir>/model.joblib; otherwise return the original path.
        If model_path is http(s) and the path is /static/... (task artifact URL), map it to backend/runtime_data/tasks/....
        If the final path does not exist, log a warning and let the caller decide whether to fail.
        """
        entry = None
        for e in self._load():
            if e.model_id == model_id:
                entry = e
                break
        if not entry or not (entry.model_path or "").strip():
            return None
        raw = entry.model_path.strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            p_http = self._resolve_http_static_artifact(raw)
            if p_http is not None:
                if not p_http.exists():
                    logger.warning(
                        "Resolved model path does not exist for model_id=%s: configured model_path=%r, resolved_path=%s",
                        model_id,
                        entry.model_path,
                        str(p_http),
                    )
                return p_http
            logger.warning(
                "model_path is HTTP but not under /static/: model_id=%s model_path=%r",
                model_id,
                entry.model_path,
            )
            return None
        p = Path(raw)
        if not p.is_absolute():
            p = self._path.parent / p
        p = p.resolve()
        if p.is_dir():
            p = p / "model.joblib"
        if not p.exists():
            logger.warning(
                "Resolved model path does not exist for model_id=%s: configured model_path=%r, resolved_path=%s",
                model_id,
                entry.model_path,
                str(p),
            )
        return p

    def get_package_root(self, model_id: str) -> Optional[Path]:
        """
        If the model_path for model_id points to a published package directory containing metadata.json, return the absolute directory path; otherwise return None.
        """
        model_file = self.resolve_model_path(model_id)
        if model_file is None:
            return None
        root = model_file.parent
        if (root / "metadata.json").exists():
            return root
        return None

    def invalidate_cache(self) -> None:
        """Clear the in-memory cache so the next _load rereads files, for example after external registry.json changes."""
        self._cache = None
