from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

from backend.schemas.agent import PendingAction


class FilePendingActionStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, action_id: str) -> Path:
        return self.root / f"{action_id}.json"

    def save(self, item: PendingAction) -> None:
        self._path(item.pending_action_id).write_text(
            json.dumps(item.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_all(self) -> Dict[str, PendingAction]:
        data: Dict[str, PendingAction] = {}
        for path in self.root.glob("*.json"):
            raw = json.loads(path.read_text(encoding="utf-8"))
            item = PendingAction.model_validate(raw)
            data[item.pending_action_id] = item
        return data

    def delete(self, action_id: str) -> None:
        self._path(action_id).unlink(missing_ok=True)

    def keys(self) -> Iterable[str]:
        for path in self.root.glob("*.json"):
            yield path.stem

