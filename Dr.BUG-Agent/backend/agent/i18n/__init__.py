from __future__ import annotations

from typing import Any, Optional


def chat_msg(locale: Optional[str], key: str, **kwargs: Any) -> str:
    from backend.agent.i18n.catalog import chat_msg as _chat_msg

    return _chat_msg(locale, key, **kwargs)


__all__ = ["chat_msg"]