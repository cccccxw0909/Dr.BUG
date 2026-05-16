from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from backend.config import AUDIT_DIR
from backend.utils.time_utils import now_iso

AUDIT_LOG_PATH = Path(AUDIT_DIR) / "agent_actions.jsonl"


def audit_event(event_type: str, payload: Dict[str, Any]) -> None:
    row = {"time": now_iso(), "event_type": event_type, "payload": payload}
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")

