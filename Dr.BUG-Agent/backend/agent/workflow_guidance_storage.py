"""Persist last workflow_guidance under the same scope_key semantics as pending, for continue handoff."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple

from backend.config import RUNTIME_DIR
from backend.utils.time_utils import now_iso, utc_from_iso

_FOLLOWUP_DIR = RUNTIME_DIR / "workflow_guidance_followup"

DEFAULT_GUIDANCE_FOLLOWUP_TTL_SECONDS = int(
    os.getenv("WORKFLOW_GUIDANCE_FOLLOWUP_TTL_SECONDS", "1800").strip() or "1800"
)


def _safe_scope_key(scope_key: str) -> str:
    s = str(scope_key or "legacy:global").strip() or "legacy:global"
    return "".join(c if c.isalnum() or c in ("-", "_", ":") else "_" for c in s)[:200]


def _parse_saved_at(ts: str) -> Optional[datetime]:
    """Parse saved_at as UTC-aware; missing or invalid → None."""
    t = (ts or "").strip()
    if not t:
        return None
    try:
        return utc_from_iso(t)
    except ValueError:
        return None


def record_is_stale(record: Dict[str, Any], *, now: Optional[datetime] = None) -> bool:
    """Treat as expired after ttl_seconds (tests may inject now)."""
    dt = _parse_saved_at(str(record.get("saved_at") or ""))
    if dt is None:
        return True
    ttl = int(record.get("ttl_seconds") or DEFAULT_GUIDANCE_FOLLOWUP_TTL_SECONDS)
    ref = datetime.now(timezone.utc) if now is None else now
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    age = (ref - dt).total_seconds()
    return age > float(ttl)


def save_last_guidance(
    scope_key: str,
    record: Dict[str, Any],
    *,
    ttl_seconds: Optional[int] = None,
) -> None:
    """Saving again for the same scope overwrites the file so fresh guidance replaces stale snapshots."""
    _FOLLOWUP_DIR.mkdir(parents=True, exist_ok=True)
    path = _FOLLOWUP_DIR / f"{_safe_scope_key(scope_key)}.json"
    rec = dict(record)
    rec.setdefault("saved_at", now_iso())
    rec["ttl_seconds"] = int(ttl_seconds if ttl_seconds is not None else rec.get("ttl_seconds") or DEFAULT_GUIDANCE_FOLLOWUP_TTL_SECONDS)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last_guidance_record(
    scope_key: str,
    *,
    now: Optional[datetime] = None,
) -> Tuple[Optional[Dict[str, Any]], Literal["missing", "expired", "ok"]]:
    path = _FOLLOWUP_DIR / f"{_safe_scope_key(scope_key)}.json"
    if not path.exists():
        return None, "missing"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, "missing"
    if not isinstance(raw, dict):
        return None, "missing"
    if record_is_stale(raw, now=now):
        path.unlink(missing_ok=True)
        return None, "expired"
    return raw, "ok"


def load_last_guidance(scope_key: str) -> Optional[Dict[str, Any]]:
    """Legacy helper: returns None when missing or expired."""
    rec, st = load_last_guidance_record(scope_key)
    return rec if st == "ok" else None


def clear_last_guidance(scope_key: str) -> None:
    path = _FOLLOWUP_DIR / f"{_safe_scope_key(scope_key)}.json"
    if path.exists():
        path.unlink()
