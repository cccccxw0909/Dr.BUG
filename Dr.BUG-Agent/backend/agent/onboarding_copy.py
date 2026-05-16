# backend/agent/onboarding_copy.py
"""
Deterministic Dr.BUG onboarding / greeting copy (welcome_policy).

English copy is the canonical backend text; strings are sourced from
``backend/agent/i18n/messages_onboarding.py``. Localized variants for the UI
also live under ``frontend/src/i18n/locales/*`` (see ``chat.onboarding.*``).
"""
from __future__ import annotations

from typing import Optional

from backend.agent.i18n.catalog import chat_msg


def _loc_to_chat_locale(locale: Optional[str]) -> str:
    if locale is None:
        return "en"
    v = str(locale).strip().replace("_", "-").lower()
    if v == "zh" or v.startswith("zh-"):
        return "zh"
    return "en"


def dr_bug_onboarding_body(locale: Optional[str]) -> str:
    return chat_msg(_loc_to_chat_locale(locale), "onboarding.greeting.body")


def suffix_selected_dataset(locale: Optional[str], dataset_name: str) -> str:
    name = (dataset_name or "").strip()
    return chat_msg(_loc_to_chat_locale(locale), "onboarding.suffix.selected_dataset", name=name)


def suffix_selected_model(locale: Optional[str], model_label: str) -> str:
    label = (model_label or "").strip()
    return chat_msg(_loc_to_chat_locale(locale), "onboarding.suffix.selected_model", label=label)


def suffix_training_waiting_confirm(locale: Optional[str]) -> str:
    return chat_msg(_loc_to_chat_locale(locale), "onboarding.suffix.training_waiting_confirm")


def suffix_pending_draft(locale: Optional[str]) -> str:
    return chat_msg(_loc_to_chat_locale(locale), "onboarding.suffix.pending_draft")
