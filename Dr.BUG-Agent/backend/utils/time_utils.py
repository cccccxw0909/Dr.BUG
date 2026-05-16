from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _format_utc(dt: datetime) -> str:
    """Serialize an instant as ISO 8601 / RFC 3339 UTC with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_iso() -> str:
    """Current instant in UTC (consistent wall-clock when consumers interpret as UTC)."""
    return _format_utc(datetime.now(timezone.utc))


def utc_from_iso(s: str) -> datetime:
    """
    Parse a stored ISO timestamp as timezone-aware UTC.

    Strings without an offset are treated as UTC (matches legacy naive timestamps
    produced by older deployments).
    """
    raw = (s or "").strip()
    if not raw:
        return datetime.now(timezone.utc)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def expires_at_iso(*, ttl_minutes: int) -> str:
    """UTC expiry instant ``ttl_minutes`` after now."""
    return _format_utc(datetime.now(timezone.utc) + timedelta(minutes=int(ttl_minutes)))
