from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import RUNTIME_DIR
from backend.utils.time_utils import now_iso

TREATMENT_FIELD_NAMES: List[str] = [
    "colistin_cms_daily_freq",
    "polymyxin_b_daily_freq",
    "colistin_sulfate_daily_freq",
    "carbapenem_daily_dose",
    "sulbactam_daily_dose",
    "tigecycline_daily_dose",
    "minocycline_daily_dose",
    "vancomycin_daily_dose",
    "eravacycline_daily_dose",
    "aminoglycoside_daily_dose",
]

REGIMEN_LIBRARY_PATH = RUNTIME_DIR / "config" / "regimen_library.json"


class FileRegimenRepo:
    def __init__(self, storage_path: Path = REGIMEN_LIBRARY_PATH):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text(
                json.dumps({"items": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self.lock = threading.Lock()

    def _read_items(self) -> List[Dict[str, Any]]:
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            return [item for item in raw["items"] if isinstance(item, dict)]
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        return []

    def _write_items(self, items: List[Dict[str, Any]]) -> None:
        with self.lock:
            self.storage_path.write_text(
                json.dumps({"items": items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def list(self) -> List[Dict[str, Any]]:
        items = self._read_items()
        items.sort(key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""), reverse=True)
        return items

    def get(self, regimen_id: str) -> Optional[Dict[str, Any]]:
        rid = str(regimen_id or "").strip()
        if not rid:
            return None
        return next((item for item in self._read_items() if str(item.get("regimen_id")) == rid), None)

    def create(
        self,
        *,
        regimen_name: str,
        enabled: bool,
        notes: Optional[str],
        treatment_values: Dict[str, float],
    ) -> Dict[str, Any]:
        items = self._read_items()
        ts = now_iso()
        entry = {
            "regimen_id": f"reg_{uuid.uuid4().hex[:10]}",
            "regimen_name": regimen_name,
            "enabled": bool(enabled),
            "notes": notes,
            "treatment_values": {k: float(treatment_values.get(k, 0.0)) for k in TREATMENT_FIELD_NAMES},
            "created_at": ts,
            "updated_at": ts,
        }
        items.append(entry)
        self._write_items(items)
        return entry

    def update(
        self,
        regimen_id: str,
        *,
        regimen_name: str,
        enabled: bool,
        notes: Optional[str],
        treatment_values: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        rid = str(regimen_id or "").strip()
        if not rid:
            return None
        items = self._read_items()
        idx = next((i for i, item in enumerate(items) if str(item.get("regimen_id")) == rid), -1)
        if idx < 0:
            return None
        prev = items[idx]
        updated = {
            "regimen_id": rid,
            "regimen_name": regimen_name,
            "enabled": bool(enabled),
            "notes": notes,
            "treatment_values": {k: float(treatment_values.get(k, 0.0)) for k in TREATMENT_FIELD_NAMES},
            "created_at": str(prev.get("created_at") or now_iso()),
            "updated_at": now_iso(),
        }
        items[idx] = updated
        self._write_items(items)
        return updated

    def delete(self, regimen_id: str) -> bool:
        rid = str(regimen_id or "").strip()
        if not rid:
            return False
        items = self._read_items()
        kept = [item for item in items if str(item.get("regimen_id")) != rid]
        if len(kept) == len(items):
            return False
        self._write_items(kept)
        return True
