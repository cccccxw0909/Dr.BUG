
from __future__ import annotations

from typing import Optional

ANONYMOUS_DEFAULT_SCOPE = "session:_anon_default"


def resolve_pending_scope_key(user_id: Optional[str], session_id: Optional[str]) -> str:
    """
    - Explicit user_id and not anonymous → user:{id}
    - Else if session_id → session:{id}
    - Else ANONYMOUS_DEFAULT_SCOPE (clients should generate and pass a per-browser session_id)
    """
    uid = (user_id or "").strip()
    if uid and uid.lower() != "anonymous":
        return f"user:{uid}"
    sid = (session_id or "").strip()
    if sid:
        return f"session:{sid}"
    return ANONYMOUS_DEFAULT_SCOPE
