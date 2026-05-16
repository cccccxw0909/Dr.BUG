from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.agent.pending_action_policy import pending_domain_supersedes
from backend.agent.pending_action_storage import FilePendingActionStorage
from backend.schemas.agent import PendingAction
from backend.utils.time_utils import expires_at_iso, now_iso, utc_from_iso


class PendingActionRegistry:
    """In-memory registry with serializable DTO contracts."""

    def __init__(self, storage: Optional[FilePendingActionStorage] = None):
        self._data: Dict[str, PendingAction] = {}
        self._lock = threading.Lock()
        self._storage = storage
        if self._storage:
            self._data.update(self._storage.load_all())

    def create(
        self,
        action_type: str,
        payload: Dict,
        *,
        scope_key: str = "legacy:global",
        ttl_minutes: int = 15,
    ) -> PendingAction:
        action_id = f"pa_{uuid.uuid4().hex[:10]}"
        expires_at = expires_at_iso(ttl_minutes=ttl_minutes)
        item = PendingAction(
            pending_action_id=action_id,
            action_type=action_type,  # type: ignore[arg-type]
            payload=payload,
            created_at=now_iso(),
            expires_at=expires_at,
            status="pending",
            scope_key=str(scope_key),
        )
        with self._lock:
            # Supersede: same scope only; then by business domain or identical action_type.
            for existing_id, existing in self._data.items():
                if existing.status != "pending":
                    continue
                if str(existing.scope_key) != str(scope_key):
                    continue
                if pending_domain_supersedes(action_type, str(existing.action_type)):
                    existing.status = "superseded"
                    existing.superseded_by = action_id
                    self._data[existing_id] = existing
                    self._save(existing)
            self._data[action_id] = item
        self._save(item)
        return item

    def has_active_pending(self, scope_key: str) -> bool:
        with self._lock:
            sk = str(scope_key or "")
            return any(
                p.status == "pending" and str(p.scope_key or "") == sk for p in self._data.values()
            )

    def get_active_pending_for_scope(self, scope_key: str) -> Optional[PendingAction]:
        """Most recently created non-expired pending in scope; None if none."""
        sk = str(scope_key or "")
        with self._lock:
            candidates: List[PendingAction] = [
                p
                for p in self._data.values()
                if p.status == "pending" and str(p.scope_key or "") == sk
            ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: str(p.created_at or ""), reverse=True)
        for p in candidates:
            got = self.get(p.pending_action_id)
            if got is not None and got.status == "pending":
                return got
        return None

    def get(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._data.get(action_id)
        if not item:
            return None
        if item.status == "pending" and utc_from_iso(item.expires_at) < datetime.now(timezone.utc):
            return self.expire(action_id)
        return item

    def confirm(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._data.get(action_id)
            if not item:
                return None
            item.status = "confirmed"
            self._data[action_id] = item
            self._save(item)
            return item

    def mark_job_created(self, action_id: str, job_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._data.get(action_id)
            if not item:
                return None
            item.executed_job_id = job_id
            self._data[action_id] = item
            self._save(item)
            return item

    def cancel(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._data.get(action_id)
            if not item:
                return None
            item.status = "canceled"
            self._data[action_id] = item
            self._save(item)
            return item

    def expire(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._data.get(action_id)
            if not item:
                return None
            item.status = "expired"
            self._data[action_id] = item
            self._save(item)
            return item

    def _save(self, item: PendingAction) -> None:
        if self._storage:
            self._storage.save(item)

    def reconcile_on_startup(self) -> None:
        for action_id in list(self._data.keys()):
            self.get(action_id)

