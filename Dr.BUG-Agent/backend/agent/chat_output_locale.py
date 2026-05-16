"""Resolve chat/agent output locale (en vs zh) from context and optional user message."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from backend.agent.i18n.lexicons.zh_routing_core_tokens import ZH_BATCH

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _locale_hint_from_accept_language(header: Optional[str]) -> Optional[str]:
    if not header or not str(header).strip():
        return None
    first = str(header).split(",")[0].strip().split(";")[0].strip().lower()
    if not first:
        return None
    if first.startswith("en"):
        return "en"
    if first.startswith("zh"):
        return "zh"
    return None


def normalize_chat_output_locale(
    explicit: Optional[str] = None,
    *,
    chat_context: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    accept_language: Optional[str] = None,
    default: str = "en",
) -> str:
    """
    Returns "en" or "zh" for user-visible assistant copy.

    Precedence: explicit > chat_context locale/ui_locale > Accept-Language (param or context)
    > CJK in message implies zh > default (en for public/demo safety).
    """
    v = (explicit or "").strip().lower()
    if v.startswith("en"):
        return "en"
    if v.startswith("zh"):
        return "zh"
    ctx = chat_context or {}
    loc = str(ctx.get("locale") or ctx.get("ui_locale") or "").strip().lower()
    if loc.startswith("en"):
        return "en"
    if loc.startswith("zh"):
        return "zh"
    al_src = accept_language
    if al_src is None:
        raw_al = ctx.get("accept_language") or ctx.get("http_accept_language")
        al_src = str(raw_al) if raw_al is not None else None
    hinted = _locale_hint_from_accept_language(al_src)
    if hinted:
        return hinted
    msg = (message or "").strip()
    if msg and _CJK_RE.search(msg):
        return "zh"
    d = (default or "en").strip().lower()
    return "en" if d.startswith("en") else "zh"


def is_english_output_locale(locale: Optional[str]) -> bool:
    """Return True for English output; omitted locale follows the public default (English)."""
    v = str(locale or "").strip().lower()
    if not v:
        return True
    return v.startswith("en")


_BATCH_EN_RE = re.compile(r"\bbatch\b", re.I)


def infer_batch_hint(message: str, output_locale: str) -> bool:
    m = message or ""
    if ZH_BATCH in m:
        return True
    if is_english_output_locale(output_locale):
        return bool(_BATCH_EN_RE.search(m))
    return False
