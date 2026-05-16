"""Lightweight classification for terminal-state result questions and deterministic fallback when no read-only tools (does not replace task selection)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Union

from backend.agent import concise_progress as cp
from backend.agent.chat_output_locale import infer_batch_hint, normalize_chat_output_locale
from backend.agent.prediction_answerability import (
    is_workspace_current_prediction_outcome_followup,
    resolve_current_prediction_followup_state,
    sticky_no_current_prediction_reply,
    wants_explicit_global_latest_prediction_query,
)
from backend.agent.result_presentation import terminal_reply_for_task_and_intent
from backend.agent.i18n.lexicons.zh_routing_core_tokens import (
    ZH_HIGH_RISK,
    ZH_MODEL,
    ZH_PREDICT,
    ZH_RESULT,
    ZH_RISK,
    ZH_TRAIN,
)
from backend.agent.i18n.lexicons.zh_terminal_result_query import (
    ZH_GO_LIVE,
    ZH_GOOD_BAD,
    ZH_HOW_MUCH,
    ZH_LABEL,
    ZH_METRIC,
    ZH_PERFORMANCE,
    ZH_PROBABILITY,
    ZH_RELEASE,
    ZH_RESULT_GOOD_BAD_PHRASE,
    ZH_SINGLE_SAMPLE,
    ZH_TRAIN_DONE_QUESTION,
    ZH_TRAIN_RESULT_PHRASE,
)
from backend.agent.zh_intent_lexicon import (
    ZH_PRED_BATCH_ANOMALY_TERMS,
    ZH_PRED_BATCH_HIGH_RISK_TERMS,
    ZH_PRED_BATCH_NEXT_TERMS,
    ZH_PRED_BATCH_OVERVIEW_TERMS,
    ZH_PRED_BATCH_SCOPE_TERMS,
    ZH_PRED_CAUTION_TERMS,
    ZH_PRED_CLINICAL_MEANING_TERMS,
    ZH_PRED_EXPLAIN_AVAIL_TERMS,
    ZH_PRED_LABEL_PROB_COMBO_TERMS,
    ZH_PRED_LABEL_QUESTION_TERMS,
    ZH_PRED_MEANING_TERMS,
    ZH_PRED_PROB_QUESTION_TERMS,
    ZH_PRED_READING_TERMS,
    ZH_PRED_RISK_LEVEL_TERMS,
    ZH_PRED_SINGLE_SAMPLE_RESULT_TERMS,
    ZH_PRED_WHY_TERMS,
    ZH_TERMINAL_FAIL_CHECK_TERMS,
    ZH_TERMINAL_FAIL_WHERE_TERMS,
    ZH_TERMINAL_RELEASE_COLLOQUIAL_TERMS,
    ZH_TERMINAL_RELEASE_QUESTION_PARTICLES,
    ZH_TRAIN_BEST_MODEL_TERMS,
    ZH_TRAIN_COMPLETION_SHORT_TERMS,
    ZH_TRAIN_METRIC_QUALITY_TERMS,
    ZH_TRAIN_MODEL_READY_TERMS,
    ZH_TRAIN_NOTABLE_TERMS,
    ZH_TRAIN_RELEASE_CONTEXT_TERMS,
    ZH_TRAIN_RELEASE_INLINE_TERMS,
    ZH_TRAIN_RELEASE_LIBRARY_TERMS,
    ZH_TRAIN_RELEASE_STATUS_TERMS,
    ZH_TRAIN_RESULT_QUALITY_TERMS,
    ZH_TRAIN_USABILITY_TERMS,
)


def _norm(msg: str) -> str:
    t = (msg or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t


def classify_terminal_result_intent(message: str) -> Optional[str]:
    """
    Classify common terminal-result question intents; returns None for default terminal summary wording.
    Used only to vary phrasing on an already-selected terminal task; does not choose tasks.
    """
    m = _norm(message)
    if not m or len(m) > 160:
        return None

    # --- Failure intents: take precedence over generic training/prediction tokens ---
    if any(k in m for k in ZH_TERMINAL_FAIL_CHECK_TERMS):
        return "fail_check_first"
    if any(k in m for k in ZH_TERMINAL_FAIL_WHERE_TERMS):
        return "fail_where"

    # Colloquial "release" often omits "model"; still resolve via training job artifacts (bound to focus train job)
    if any(k in m for k in ZH_TERMINAL_RELEASE_COLLOQUIAL_TERMS) or (
        "release" in m.lower() and any(k in m for k in ZH_TERMINAL_RELEASE_QUESTION_PARTICLES)
    ):
        return "train_release_status"

    # Short colloquial asks: without a prediction anchor, treat as training artifacts (task binding stays in resolve layer)
    if ZH_PREDICT not in m:
        if any(k in m for k in ZH_TRAIN_RELEASE_STATUS_TERMS):
            return "train_release_status"
        if any(k in m for k in ZH_TRAIN_USABILITY_TERMS) and (
            ZH_MODEL in m or ZH_TRAIN in m
        ):
            return "train_release_status"

    # --- Training results: require explicit training/model anchors to avoid confusion with prediction ---
    if ZH_TRAIN in m or (ZH_MODEL in m and ZH_PREDICT not in m):
        if any(
            k in m
            for k in ZH_TRAIN_RELEASE_INLINE_TERMS + ZH_TRAIN_RELEASE_LIBRARY_TERMS
        ):
            return "train_release_status"
        if (ZH_RELEASE in m or "release" in m.lower() or ZH_GO_LIVE in m) and any(
            k in m for k in ZH_TRAIN_RELEASE_CONTEXT_TERMS
        ):
            return "train_release_status"
        if any(k in m for k in ZH_TRAIN_BEST_MODEL_TERMS):
            return "train_best_model"
        if ZH_PERFORMANCE in m:
            return "train_performance"
        if ZH_GOOD_BAD in m or ZH_RESULT_GOOD_BAD_PHRASE in m:
            return "train_good_bad"
        if any(k in m for k in ZH_TRAIN_NOTABLE_TERMS):
            return "train_notable"
        if any(k in m for k in ZH_TRAIN_COMPLETION_SHORT_TERMS) or (
            ZH_TRAIN in m and ZH_TRAIN_DONE_QUESTION in m
        ):
            return "train_performance"
        if ZH_TRAIN_RESULT_PHRASE in m and any(k in m for k in ZH_TRAIN_RESULT_QUALITY_TERMS):
            return "train_performance"
        if ZH_METRIC in m and any(k in m for k in ZH_TRAIN_METRIC_QUALITY_TERMS):
            return "train_performance"
        if ZH_MODEL in m and ZH_PREDICT not in m and any(
            k in m for k in ZH_TRAIN_MODEL_READY_TERMS
        ):
            return "train_performance"

    # --- Batch prediction results ---
    if any(k in m for k in ZH_PRED_BATCH_SCOPE_TERMS) and (
        ZH_PREDICT in m or ZH_RESULT in m or ZH_RISK in m or ZH_HIGH_RISK in m
    ):
        if any(k in m for k in ZH_PRED_BATCH_HIGH_RISK_TERMS):
            return "pred_batch_high_risk"
        if any(k in m for k in ZH_PRED_BATCH_ANOMALY_TERMS):
            return "pred_batch_anomaly"
        if any(k in m for k in ZH_PRED_BATCH_NEXT_TERMS):
            return "pred_batch_next"
        if any(k in m for k in ZH_PRED_BATCH_OVERVIEW_TERMS):
            return "pred_batch_overview"

    # --- Single-record / generic prediction results ---
    if ZH_TRAIN not in m:
        if any(k in m for k in ZH_PRED_LABEL_QUESTION_TERMS):
            return "pred_ask_label"
        if any(k in m for k in ZH_PRED_PROB_QUESTION_TERMS):
            return "pred_ask_prob"
        if ZH_PREDICT in m and ZH_PROBABILITY in m and ZH_HOW_MUCH in m:
            return "pred_ask_prob"
        if any(k in m for k in ZH_PRED_CLINICAL_MEANING_TERMS):
            return "pred_meaning"
        if ZH_PREDICT in m and ZH_LABEL in m and ZH_PROBABILITY in m and any(k in m for k in ZH_PRED_LABEL_PROB_COMBO_TERMS):
            return "pred_meaning"
        if ZH_SINGLE_SAMPLE in m and ZH_PREDICT in m and any(k in m for k in ZH_PRED_SINGLE_SAMPLE_RESULT_TERMS):
            return "pred_meaning"
        if any(k in m for k in ZH_PRED_EXPLAIN_AVAIL_TERMS) and (
            ZH_PREDICT in m or ZH_SINGLE_SAMPLE in m
        ):
            return "pred_why"
    if ZH_PREDICT in m or (ZH_RISK in m and ZH_TRAIN not in m):
        if any(k in m for k in ZH_PRED_WHY_TERMS):
            return "pred_why"
        if ZH_RISK in m and any(k in m for k in ZH_PRED_RISK_LEVEL_TERMS):
            return "pred_risk"
        if any(k in m for k in ZH_PRED_MEANING_TERMS):
            return "pred_meaning"
        if any(k in m for k in ZH_PRED_READING_TERMS):
            return "pred_meaning"
        if any(k in m for k in ZH_PRED_CAUTION_TERMS):
            return "pred_caution"

    return None


def _latest_failed_task(task_repo: Any) -> Optional[Dict[str, Any]]:
    failed = task_repo.list(status="failed")
    if not failed:
        return None

    def sort_key(t: Dict[str, Any]) -> str:
        return str(t.get("completed_at") or t.get("created_at") or "")

    return max(failed, key=sort_key)


def _resolve_failed_task(task_repo: Any, chat_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    focus = cp._get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("status") or "") in ("failed", "canceled"):
        return focus
    return _latest_failed_task(task_repo)


TerminalResultRouting = Union["TerminalResultHit", Literal["sticky_no_prediction"]]


@dataclass(frozen=True)
class TerminalResultHit:
    object_kind: Literal["train", "predict"]
    task: Dict[str, Any]
    intent: str
    batch_hint: bool


def resolve_terminal_result_when_no_tools(
    message: str,
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> Optional[TerminalResultRouting]:
    """
    Same parsing as build_terminal_result_query_reply_when_no_tools, but returns a structured hit
    for semantics/finalization layers.
    """
    if (
        resolve_current_prediction_followup_state(task_repo, chat_context) == "current_prediction_not_run"
        and is_workspace_current_prediction_outcome_followup(message)
        and not wants_explicit_global_latest_prediction_query(message)
    ):
        return "sticky_no_prediction"

    intent = classify_terminal_result_intent(message)
    if intent is None:
        return None

    raw = task_repo.list()
    if intent in ("fail_where", "fail_check_first"):
        task = _resolve_failed_task(task_repo, chat_context)
        if not task:
            return None
        jt = str(task.get("job_type") or "")
        if jt == "train_model":
            return TerminalResultHit(object_kind="train", task=task, intent=intent, batch_hint=False)
        if jt == "predict_outcome":
            return TerminalResultHit(object_kind="predict", task=task, intent=intent, batch_hint=False)
        return None

    if intent == "train_release_status" or intent.startswith("train_"):
        task = cp._resolve_train_task_for_status(task_repo, raw, chat_context)
        if not task:
            return None
        return TerminalResultHit(object_kind="train", task=task, intent=intent, batch_hint=False)

    if intent.startswith("pred_"):
        task = cp._resolve_predict_task_for_status(task_repo, raw, chat_context)
        if not task:
            return None
        loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
        batch_hint = infer_batch_hint(message, loc)
        return TerminalResultHit(object_kind="predict", task=task, intent=intent, batch_hint=batch_hint)

    return None


def build_terminal_result_query_reply_when_no_tools(
    message: str,
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> Optional[str]:
    """
    When plan_readonly_tools is empty but the user clearly asks for a terminal-state result, reuse the same
    _resolve_* task pickers as concise_progress for a deterministic reply. Does not change task selection; only reuses helpers.
    """
    hit = resolve_terminal_result_when_no_tools(message, task_repo, chat_context)
    if hit is None:
        return None
    if hit == "sticky_no_prediction":
        loc_sn = normalize_chat_output_locale(chat_context=chat_context, message=message)
        return sticky_no_current_prediction_reply(message, locale=loc_sn)
    loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
    return terminal_reply_for_task_and_intent(
        hit.task,
        hit.object_kind,
        hit.intent,
        batch_hint=hit.batch_hint,
        locale=loc,
    )
