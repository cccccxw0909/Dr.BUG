from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agent.i18n.lexicons.zh_query_normalization import (
    QN_ALT_ADJUST,
    QN_ALT_DONE,
    QN_ALT_EDIT_SHORT,
    QN_ALT_HOW,
    QN_ALT_READ,
    QN_ALT_READY_QUESTION,
    QN_ALT_REWRITE,
    QN_ALT_STATUS,
    QN_ALT_WHY,
    QN_ALT_WHY2,
    QN_SCOPE_JUST_NOW,
    QN_SCOPE_LATEST,
    QN_SCOPE_PREDICT,
    QN_SCOPE_RECENT,
    QN_SCOPE_TRAIN,
    QN_TOKEN_EDIT,
    QN_TOKEN_EXPLAIN,
    QN_TOKEN_PROGRESS,
)


def normalize_query_for_routing(message: str, chat_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Lightweight normalization: produces hints/trace only; does not drive execution.
    """
    raw = str(message or "")
    text = " ".join(raw.strip().split())
    low = text.lower()
    tokens: List[str] = []

    def hit(key: str, *alts: str) -> bool:
        all_keys = (key, *alts)
        ok = any(k in text or k in low for k in all_keys)
        if ok:
            tokens.append(key)
        return ok

    intent_hint = "unknown"
    if hit(QN_TOKEN_PROGRESS, QN_ALT_STATUS, QN_ALT_DONE, QN_ALT_READY_QUESTION, QN_ALT_HOW):
        intent_hint = "status_like"
    if hit(QN_TOKEN_EXPLAIN, QN_ALT_WHY, QN_ALT_WHY2, QN_ALT_READ):
        intent_hint = "explain_like"
    if hit(QN_TOKEN_EDIT, QN_ALT_EDIT_SHORT, QN_ALT_ADJUST, QN_ALT_REWRITE):
        intent_hint = "edit_like"

    scope_hint = "unknown"
    if hit(QN_SCOPE_TRAIN, "train"):
        scope_hint = "training"
    if hit(QN_SCOPE_PREDICT, "predict"):
        scope_hint = "prediction"
    if hit(QN_SCOPE_RECENT, QN_SCOPE_JUST_NOW, QN_SCOPE_LATEST):
        scope_hint = f"{scope_hint}|latest"

    focus_job_id = ""
    ctx = chat_context or {}
    for k in ("focus_job_id", "current_job_id", "active_job_id", "task_id", "selected_job_id"):
        v = str(ctx.get(k) or "").strip()
        if v.startswith("job_"):
            focus_job_id = v
            break

    return {
        "canonical_text": text,
        "intent_hint": intent_hint,
        "scope_hint": scope_hint,
        "focus_job_id": focus_job_id or None,
        "evidence_tokens": sorted(set(tokens)),
    }
