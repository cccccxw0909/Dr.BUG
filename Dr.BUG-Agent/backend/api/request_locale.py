"""Resolve UI locale from explicit API fields and Accept-Language (for user-visible error text)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from starlette.requests import Request


def locale_from_accept_language(header: Optional[str]) -> Optional[str]:
    if not header or not str(header).strip():
        return None
    first = str(header).split(",")[0].strip().split(";")[0].strip().lower()
    if first.startswith("en"):
        return "en"
    if first.startswith("zh"):
        return "zh"
    return None


def api_locale_prefers_english(locale: str) -> bool:
    return str(locale or "").strip().lower().startswith("en")


def resolve_api_user_locale(
    explicit: Optional[str] = None,
    *,
    accept_language: Optional[str] = None,
    ui_locale_header: Optional[str] = None,
    default: str = "en",
) -> str:
    """Returns "en" or "zh".

    Precedence: explicit body/form locale > X-UI-Locale-style header > Accept-Language > default.
    """
    v = (explicit or "").strip().lower()
    if v.startswith("en"):
        return "en"
    if v.startswith("zh"):
        return "zh"
    uh = (ui_locale_header or "").strip().lower()
    if uh.startswith("en"):
        return "en"
    if uh.startswith("zh"):
        return "zh"
    al = locale_from_accept_language(accept_language)
    if al:
        return al
    d = (default or "en").strip().lower()
    return "en" if d.startswith("en") else "zh"


def resolve_api_user_locale_from_request(
    request: "Request",
    explicit: Optional[str] = None,
    *,
    default: str = "en",
) -> str:
    """Like ``resolve_api_user_locale`` but reads ``Accept-Language`` and ``X-UI-Locale`` from a request."""
    ui = request.headers.get("x-ui-locale") or request.headers.get("X-UI-Locale")
    return resolve_api_user_locale(
        explicit,
        accept_language=request.headers.get("accept-language"),
        ui_locale_header=ui,
        default=default,
    )
