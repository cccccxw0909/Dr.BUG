# backend/agent/welcome_policy.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from backend.agent.i18n.lexicons.zh_welcome_intent import (
    EDGE_STRIP_CHARS,
    GREETING_NORMALIZED,
    IDENTITY_QUERY_PATTERNS,
    TASK_INTENT_EN_RE,
    TASK_INTENT_ZH_SUBSTR,
)
from backend.agent.onboarding_copy import (
    dr_bug_onboarding_body,
    suffix_pending_draft,
    suffix_selected_dataset,
    suffix_selected_model,
    suffix_training_waiting_confirm,
)

Mode = Literal["home", "train", "predict", "recommend", "unknown"]
PendingActionType = Literal[
    "training",
    "single_prediction",
    "batch_prediction",
    "recommendation",
    "publish",
    "unknown",
]

_LOCALE_TYPE = Literal["zh-CN", "en-US"]

_MODEL_ID_LIKE_RE = re.compile(r"^model_[a-f0-9]{8,}$", re.I)

# Explicit UI / request locale keys (top-level or inside nested dicts below).
_WELCOME_UI_LOCALE_KEYS: Tuple[str, ...] = (
    "locale",
    "ui_locale",
    "chat_output_locale",
    "output_locale",
    "language",
    "lang",
)
_WELCOME_UI_LOCALE_NESTED: Tuple[str, ...] = ("chat_context", "context", "ui", "frontend")


def _normalize_explicit_welcome_ui_locale(raw: object) -> Optional[str]:
    """Map common zh/en tokens to zh-CN / en-US; unknown values return None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    v = s.replace("_", "-").lower()
    if v == "zh" or v.startswith("zh-"):
        return "zh-CN"
    if v == "en" or v.startswith("en-"):
        return "en-US"
    return None


def _extract_explicit_ui_locale_from_welcome_dict(data: dict) -> Optional[str]:
    """
    Prefer explicit UI/request locale over inferring from the user message.

    Checks top-level keys first, then nested dicts (chat_context, context, ui, frontend).
    """
    if not isinstance(data, dict):
        return None
    for key in _WELCOME_UI_LOCALE_KEYS:
        norm = _normalize_explicit_welcome_ui_locale(data.get(key))
        if norm:
            return norm
    for nest in _WELCOME_UI_LOCALE_NESTED:
        sub = data.get(nest)
        if isinstance(sub, dict):
            for key in _WELCOME_UI_LOCALE_KEYS:
                norm = _normalize_explicit_welcome_ui_locale(sub.get(key))
                if norm:
                    return norm
    return None


@dataclass
class WelcomeContext:
    """
    Minimal context for deterministic onboarding / greeting replies (user-visible).
    """

    is_new_session: bool = False
    mode: Mode = "unknown"

    ui_locale: Optional[str] = None

    selected_model_id: Optional[str] = None
    selected_model_display_name: Optional[str] = None

    selected_dataset_display_name: Optional[str] = None

    focus_job_id: Optional[str] = None

    has_pending_action: bool = False
    pending_action_type: PendingActionType = "unknown"
    pending_action_label: Optional[str] = None

    focus_training_waiting_confirm: bool = False


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    s = text.strip().lower()
    s = re.sub(r"\s+", "", s)
    return s


def strip_surrounding_junk(text: str) -> str:
    s = (text or "").strip()
    while s and s[0] in EDGE_STRIP_CHARS:
        s = s[1:].strip()
    while s and s[-1] in EDGE_STRIP_CHARS:
        s = s[:-1].strip()
    return s.strip()


def utterance_has_task_intent_cues(text: str) -> bool:
    if not text or not text.strip():
        return False
    if any(k in text for k in TASK_INTENT_ZH_SUBSTR):
        return True
    return bool(TASK_INTENT_EN_RE.search(text))


def is_pure_greeting(text: Optional[str]) -> bool:
    """
    True only for short, standalone greetings (punctuation-tolerant).
    Mixed task intent (e.g. a greeting immediately followed by a training request) must return False.
    """
    raw = (text or "").strip()
    if not raw:
        return False
    if utterance_has_task_intent_cues(raw):
        return False
    if len(raw) > 56:
        return False
    core = strip_surrounding_junk(raw).lower()
    collapsed = re.sub(r"\s+", "", core)
    return collapsed in GREETING_NORMALIZED


def is_greeting(text: Optional[str]) -> bool:
    """Backward-compatible alias for tests / callers."""
    return is_pure_greeting(text)


def is_identity_query(text: Optional[str]) -> bool:
    s = normalize_text(text)
    if not s:
        return False

    return any(re.search(p, s) for p in IDENTITY_QUERY_PATTERNS)


def should_handle_as_welcome(ctx: WelcomeContext, user_utterance: Optional[str]) -> bool:
    u = (user_utterance or "").strip()
    if ctx.is_new_session and not u:
        return True
    if is_pure_greeting(user_utterance):
        return True
    if is_identity_query(user_utterance):
        return True
    return False


def resolve_onboarding_locale(ctx: WelcomeContext, user_utterance: Optional[str]) -> _LOCALE_TYPE:
    raw = (ctx.ui_locale or "").strip().replace("_", "-").lower()
    if raw.startswith("zh"):
        return "zh-CN"
    if raw.startswith("en"):
        return "en-US"
    u = user_utterance or ""
    if re.search(r"[\u4e00-\u9fff]", u):
        return "zh-CN"
    return "en-US"


def _friendly_model_label(ctx: WelcomeContext) -> Optional[str]:
    if ctx.selected_model_display_name and str(ctx.selected_model_display_name).strip():
        return str(ctx.selected_model_display_name).strip()
    mid = (ctx.selected_model_id or "").strip()
    if not mid:
        return None
    if _MODEL_ID_LIKE_RE.match(mid):
        return None
    return mid


def compose_dr_bug_onboarding_reply(ctx: WelcomeContext, user_utterance: Optional[str]) -> str:
    loc = resolve_onboarding_locale(ctx, user_utterance)
    parts: list[str] = [dr_bug_onboarding_body(loc)]

    if ctx.selected_dataset_display_name:
        parts.append(suffix_selected_dataset(loc, ctx.selected_dataset_display_name))

    model_label = _friendly_model_label(ctx)
    if model_label:
        parts.append(suffix_selected_model(loc, model_label))

    if ctx.focus_training_waiting_confirm:
        parts.append(suffix_training_waiting_confirm(loc))
    elif ctx.has_pending_action:
        parts.append(suffix_pending_draft(loc))

    return "\n\n".join(parts)


def build_welcome_reply(ctx: WelcomeContext, user_utterance: Optional[str]) -> Optional[str]:
    """
    Deterministic onboarding / greeting / identity reply for Dr.BUG.
    Returns None when welcome_policy should not short-circuit the turn.
    """
    if not should_handle_as_welcome(ctx, user_utterance):
        return None
    return compose_dr_bug_onboarding_reply(ctx, user_utterance)


def _opt_str(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def build_welcome_context_from_dict(data: dict) -> WelcomeContext:
    selected_model_display = _opt_str(
        data.get("selected_model_display_name")
        or data.get("workspace_model_display_name")
        or data.get("model_display_name")
    )

    selected_model_id = _opt_str(
        data.get("selected_model_id") or data.get("workspace_model_id") or data.get("model_id"),
    )
    raw_model = _opt_str(data.get("model"))
    if selected_model_id is None and raw_model:
        selected_model_id = raw_model

    pending_action = data.get("pending_action") or {}
    has_pending_action = bool(
        data.get("has_pending_action") or pending_action or data.get("pending_action_type")
    )

    mode = data.get("mode") or "unknown"
    if mode not in {"home", "train", "predict", "recommend"}:
        mode = "unknown"

    pending_action_type = pending_action.get("type") or data.get("pending_action_type") or "unknown"
    if pending_action_type not in {
        "training",
        "single_prediction",
        "batch_prediction",
        "recommendation",
        "publish",
    }:
        pending_action_type = "unknown"

    ds_display: Optional[str] = None
    raw_ds = data.get("dataset")
    if isinstance(raw_ds, str) and "|" in raw_ds:
        _, rhs = raw_ds.split("|", 1)
        if rhs.strip():
            ds_display = rhs.strip()
    elif isinstance(raw_ds, str) and raw_ds.strip() and "|" not in raw_ds:
        # id-only pipeline: avoid exposing raw ids in onboarding suffix
        ds_display = None

    fts = str(data.get("focus_task_status") or "").strip().lower()
    fjt = str(data.get("focus_job_type") or "").strip().lower()
    focus_training_waiting_confirm = fts == "waiting_user" and fjt in (
        "train_model",
        "training",
        "train",
    )

    return WelcomeContext(
        is_new_session=bool(data.get("is_new_session", False)),
        mode=mode,
        ui_locale=_extract_explicit_ui_locale_from_welcome_dict(data),
        selected_model_id=selected_model_id,
        selected_model_display_name=selected_model_display,
        selected_dataset_display_name=ds_display,
        focus_job_id=data.get("focus_job_id"),
        has_pending_action=has_pending_action,
        pending_action_type=pending_action_type,
        pending_action_label=pending_action.get("label") or data.get("pending_action_label"),
        focus_training_waiting_confirm=focus_training_waiting_confirm,
    )
