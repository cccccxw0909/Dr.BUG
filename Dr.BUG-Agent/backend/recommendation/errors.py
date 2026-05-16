"""Typed errors for survival-only recommendation service (stable codes + English technical detail)."""

from __future__ import annotations

from typing import Any, Optional


class RecommendationServiceError(ValueError):
    """Subclass of ValueError so callers/tests expecting ValueError still match."""

    __slots__ = ("code", "detail", "context")

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.code = str(code or "").strip() or "RECOMMENDATION_SERVICE_ERROR"
        self.detail = str(detail or "").strip() or self.code
        self.context = dict(context or {})
        super().__init__(self.detail)
