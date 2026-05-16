from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.time_utils import now_iso

DEFAULT_AVAILABLE_TASKS = [
    "clinical_efficacy",
    "mortality_28d",
    "polymyxin_resistance",
    "treatment_duration",
]


class FileDatasetRepo:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        if not self.index_path.exists():
            self._write_index([])

    def _read_index(self) -> List[Dict[str, Any]]:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _write_index(self, data: List[Dict[str, Any]]) -> None:
        self.index_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list(self) -> List[Dict[str, Any]]:
        return self._read_index()

    def get(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        return next((item for item in self._read_index() if item["id"] == dataset_id), None)

    def delete(self, dataset_id: str) -> bool:
        """Remove a dataset from the index and delete its directory; return False if it does not exist."""
        index = self._read_index()
        idx = next((i for i, item in enumerate(index) if item.get("id") == dataset_id), None)
        if idx is None:
            return False
        index.pop(idx)
        self._write_index(index)
        folder = self.root / dataset_id
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        return True

    def create_from_uploaded_file(
        self,
        filename: str,
        src_path: Path,
        available_tasks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
        dataset_folder = self.root / dataset_id
        dataset_folder.mkdir(parents=True, exist_ok=True)

        target_path = dataset_folder / filename
        shutil.copy2(src_path, target_path)

        meta = {
            "id": dataset_id,
            "name": filename,
            "file_name": filename,
            "file_path": str(target_path),
            "file_type": target_path.suffix.lower().lstrip("."),
            "created_at": now_iso(),
            "description": "",
            "available_tasks": _normalize_available_tasks(available_tasks),
        }
        index = self._read_index()
        index.append(meta)
        self._write_index(index)
        return meta


def _normalize_available_tasks(raw: Optional[List[str]]) -> List[str]:
    if not raw:
        return list(DEFAULT_AVAILABLE_TASKS)
    cleaned = [str(x).strip() for x in raw if str(x).strip()]
    allowed = set(DEFAULT_AVAILABLE_TASKS)
    picked = [x for x in cleaned if x in allowed]
    return picked if picked else list(DEFAULT_AVAILABLE_TASKS)

