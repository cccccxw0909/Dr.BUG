"""
Workbench "prediction answerability": shared preconditions for follow-up routing so empty results do not drift into definitions or global latest.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional

from backend.agent.chat_output_locale import is_english_output_locale
from backend.agent.concise_progress import _get_focus_task
from backend.agent.i18n import chat_msg
from backend.agent.i18n.lexicons.zh_prediction_followup import (
    EXPLICIT_GLOBAL_LATEST_PREDICTION_KEYWORDS,
    HOW_MANY_SUBSTRING,
    JUST_NOW_PREDICTION_RE,
    LABEL_SUBSTRING,
    OUTPUT_SUBSTRING,
    PREVIOUS_PREDICTION_KEYWORDS,
    PRED_SUBSTRING,
    PROB_SUBSTRING,
    RECENT_PREDICTION_RESULT_KEYWORDS,
    RECENT_SUBSTRING,
    RESULT_SUBSTRING,
    STICKY_BATCH_KEYWORDS,
    STICKY_LABEL_QUESTION_KEYWORDS,
    STICKY_PROBABILITY_QUESTION_KEYWORDS,
    STICKY_RISK_QUESTION_KEYWORDS,
    TARGET_COLUMN_QUESTION_KEYWORDS,
    TARGET_SUBSTRING,
    TRAIN_PREFIX,
    TRAIN_RESULT_PHRASE,
    WHAT_SUBSTRING,
    WORKSPACE_PREDICTION_FOLLOWUP_KEYWORDS,
)
from backend.agent.workflow_context_contract import get_workspace_model_id as _contract_workspace_model_id
from backend.prediction.prediction_factual_core import (
    build_prediction_factual_bundle_from_task,
)
from backend.tools.read_only_privacy import ReadonlyTruncateTracker

PredictionFollowupState = Literal[
    "current_prediction_available",
    "current_prediction_not_run",
    "no_prediction_context",
]

_PRED_MODES = frozenset(
    {
        "predict",
        "prediction",
        "single_prediction",
        "batch_prediction",
        "inference",
    }
)


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def workspace_model_id(chat_context: Optional[Dict[str, Any]]) -> str:
    return _contract_workspace_model_id(chat_context)


def in_prediction_like_workspace(chat_context: Optional[Dict[str, Any]]) -> bool:
    """Workbench shows prediction signals: model selected or mode is a prediction-like page."""
    ctx = chat_context or {}
    if workspace_model_id(ctx):
        return True
    mode = str(ctx.get("mode") or "").strip().lower()
    return mode in _PRED_MODES


def _task_model_id(task: Dict[str, Any]) -> str:
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    for k in ("model_id", "modelId"):
        v = str(params.get(k) or rs.get(k) or "").strip()
        if v:
            return v
    return ""


def task_model_matches_workspace(task: Dict[str, Any], workspace_model: str) -> bool:
    if not workspace_model:
        return True
    return _task_model_id(task) == workspace_model


def _focus_completed_predict_bundle(
    task_repo: Any, chat_context: Optional[Dict[str, Any]]
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    focus = _get_focus_task(task_repo, chat_context)
    if not focus or str(focus.get("job_type") or "") != "predict_outcome":
        return None, None
    if str(focus.get("status") or "") != "completed":
        return focus, None
    bundle = build_prediction_factual_bundle_from_task(focus, ReadonlyTruncateTracker())
    if not bundle:
        return focus, None
    return focus, bundle


def resolve_current_prediction_followup_state(
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> PredictionFollowupState:
    """
    Three-way split (agent layer only; does not replace factual core):

    - current_prediction_available: focus is completed predict_outcome, (no workbench model or model matches), factual bundle builds.
    - current_prediction_not_run: prediction-like workbench context but the above fails (running/mismatch/non-predict focus, etc.).
    - no_prediction_context: no prediction workbench signals; keep existing latest/LLM behavior.
    """
    if not in_prediction_like_workspace(chat_context):
        return "no_prediction_context"

    focus, bundle = _focus_completed_predict_bundle(task_repo, chat_context)
    wm = workspace_model_id(chat_context or {})

    if focus and str(focus.get("job_type") or "") == "predict_outcome":
        if bundle and task_model_matches_workspace(focus, wm):
            return "current_prediction_available"
        return "current_prediction_not_run"

    # No focused predict job: if UI looks like prediction and there is no bindable completed focus result, treat as no "current" output yet
    return "current_prediction_not_run"


def completed_workspace_predict_task(
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Aligned with current_prediction_available: returns bindable completed predict_outcome task row if any."""
    focus, bundle = _focus_completed_predict_bundle(task_repo, chat_context)
    if not focus or not bundle:
        return None
    if not task_model_matches_workspace(focus, workspace_model_id(chat_context)):
        return None
    return focus


def targets_model_prediction_target_column_question(message: str) -> bool:
    """User is clearly asking about training/modeling target column or which label the model predicts — not the current output label."""
    m = _norm_ws(message)
    if not m:
        return False
    if any(k in m for k in TARGET_COLUMN_QUESTION_KEYWORDS):
        return True
    if PRED_SUBSTRING in m and TARGET_SUBSTRING in m:
        return True
    return False


def wants_explicit_global_latest_prediction_query(message: str) -> bool:
    """User explicitly anchors on latest/last time global prediction records."""
    m = _norm_ws(message)
    if not m:
        return False
    if any(k in m for k in EXPLICIT_GLOBAL_LATEST_PREDICTION_KEYWORDS):
        return True
    if RECENT_SUBSTRING in m and PRED_SUBSTRING in m and any(k in m for k in RECENT_PREDICTION_RESULT_KEYWORDS):
        return True
    if any(k in m for k in PREVIOUS_PREDICTION_KEYWORDS):
        return True
    if JUST_NOW_PREDICTION_RE.search(m):
        return True
    return False


def is_workspace_current_prediction_outcome_followup(message: str) -> bool:
    """
    Per-sample prediction result follow-up: without explicit global recency anchors, bind to current workbench prediction (not target-column definitions).
    Excludes training-led phrasing; batch/cohort phrasing handled elsewhere in routing.
    """
    m = _norm_ws(message)
    if not m or len(m) > 120:
        return False
    if targets_model_prediction_target_column_question(m):
        return False
    if wants_explicit_global_latest_prediction_query(m):
        return False
    if m.startswith(TRAIN_PREFIX) or (TRAIN_RESULT_PHRASE in m and PRED_SUBSTRING not in m):
        return False
    if any(k in m for k in STICKY_BATCH_KEYWORDS) and (PRED_SUBSTRING in m or RESULT_SUBSTRING in m):
        return True
    if any(p in m for p in WORKSPACE_PREDICTION_FOLLOWUP_KEYWORDS):
        return True
    if (PROB_SUBSTRING in m or LABEL_SUBSTRING in m) and (
        HOW_MANY_SUBSTRING in m or WHAT_SUBSTRING in m
    ) and (PRED_SUBSTRING in m or OUTPUT_SUBSTRING in m):
        return True
    return False


def sticky_no_current_prediction_reply(message: str, locale: Optional[str] = None) -> str:
    """Neutral copy for result follow-ups when current_prediction_not_run."""
    m = _norm_ws(message)
    if any(k in m for k in STICKY_RISK_QUESTION_KEYWORDS):
        return chat_msg(locale, "pred_answer.sticky.risk")
    if any(k in m for k in STICKY_PROBABILITY_QUESTION_KEYWORDS):
        return chat_msg(locale, "pred_answer.sticky.probability")
    if any(k in m for k in STICKY_LABEL_QUESTION_KEYWORDS):
        return chat_msg(locale, "pred_answer.sticky.label")
    if any(k in m for k in STICKY_BATCH_KEYWORDS):
        return chat_msg(locale, "pred_answer.sticky.batch")
    return chat_msg(locale, "pred_answer.sticky.default")
