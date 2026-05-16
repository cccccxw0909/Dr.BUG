"""Tool layer package.

Lazy exports avoid importing ``read_only_tools`` during ``backend.tools`` package init,
which prevents circular imports when ``backend.prediction.factual_core`` loads
``backend.tools.read_only_privacy`` (parent ``__init__`` must not eagerly pull read_only_tools).
"""

from __future__ import annotations

from typing import Any

_LAZY_EXPORTS = frozenset(
    {
        "ReadonlyToolContext",
        "TOOL_HANDLERS",
        "execute_readonly_tool",
        "friendly_readonly_query_labels",
        "tool_registry_public_specs",
    }
)


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        import backend.tools.read_only_tools as _rot

        return getattr(_rot, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = sorted(_LAZY_EXPORTS)
