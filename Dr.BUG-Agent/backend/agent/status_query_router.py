from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.agent.prediction_followup import (
    is_prediction_combined_followup,
    looks_like_prediction_result_concept_question,
)
from backend.agent.i18n.lexicons.zh_routing_core_tokens import ZH_MODEL, ZH_PREDICT, ZH_RESULT, ZH_TRAIN
from backend.agent.i18n.lexicons.zh_status_query_routing import (
    ZH_CONCEPT_DEF_PARTICLES,
    ZH_EXPLAIN,
    ZH_JUST_NOW,
    ZH_MEANING_QUESTION_PHRASE,
    ZH_NARROW_TASK_STATUS_TERMS,
    ZH_PREDICTION_RESULT_JUST_NOW_PHRASE,
    ZH_PREDICTION_RESULT_PHRASE,
    ZH_PRED_LABEL_PHRASE,
    ZH_PRED_PROB_PHRASE,
    ZH_SHAP,
    ZH_SUMMARY,
    ZH_TASK_STATUS_COMPOUND,
    ZH_THIS_BATCH_PREDICT_PHRASE,
    ZH_THIS_BATCH_SHORT,
    ZH_TRAINING_RESULT_PHRASE,
    ZH_WHAT_IS_PAIR,
    ZH_WHAT_IS_SUFFIX_PLAIN,
    ZH_WHAT_IS_SUFFIX_QUESTION,
)
from backend.agent.zh_intent_lexicon import (
    ZH_BROAD_LIST_QUERY_TERMS,
    ZH_CONTEXT_QUERY_TERMS,
    ZH_FAILURE_QUERY_TERMS,
    ZH_MODEL_SUPERLATIVE_TERMS,
    ZH_PREDICTION_BATCH_EVAL_TERMS,
    ZH_PREDICTION_BATCH_SCOPE_TERMS,
    ZH_PREDICTION_BATCH_TAIL_TERMS,
    ZH_PREDICTION_EXPLANATION_PHRASES,
    ZH_PREDICTION_LABEL_PROX_TERMS,
    ZH_PREDICTION_RISK_INTERP_TERMS,
    ZH_PREDICTION_SUMMARY_FOLLOWUP_TERMS,
    ZH_PREDICTION_SUMMARY_HEAD_TERMS,
    ZH_READONLY_OVERRIDE_TRIGGER_TERMS,
    ZH_READONLY_TRAINING_OVERRIDE_PHRASES,
    ZH_STATUS_CONCEPT_ANCHOR_TERMS,
    ZH_TRAINING_METRIC_TOKENS,
    ZH_TRAINING_QUALITY_TOKENS,
    ZH_TRAINING_RESULT_CONCEPT_MARKERS,
    ZH_TRAINING_RESULT_INTERROGATIVE_PARTICLES,
    ZH_TRAINING_SUMMARY_TERMS,
    ZH_VIEW_VERBS_CONCEPT_EXPLANATION,
    ZH_VIEW_VERBS_TASK_STATUS_CONCEPT,
)

# Decide before action-intent parsing: avoid misrouting "training progress" into create_training_job
_JOB_ID_RE = re.compile(r"job_[0-9a-f]{10}", re.IGNORECASE)


def _normalize(text: str) -> str:
    return (text or "").strip()


def extract_job_id(message: str) -> Optional[str]:
    m = _JOB_ID_RE.search(message or "")
    return m.group(0) if m else None


def _task_status_concept_phrase(message: str) -> bool:
    """Pure conceptual 'what is task status' phrasing (no view/list verbs) must not trigger task-status queries."""
    msg = _normalize(message)
    if not msg:
        return False
    if ZH_TASK_STATUS_COMPOUND not in msg:
        return False
    if not any(k in msg for k in ZH_WHAT_IS_PAIR):
        return False
    if any(x in msg for x in ZH_VIEW_VERBS_TASK_STATUS_CONCEPT):
        return False
    if extract_job_id(msg):
        return False
    return True


def _concept_explanation_without_operational_anchor(message: str) -> bool:
    """
    Treat bare "what does … mean" without view/list verbs as conceptual Q&A (skip read-only tools).
    """
    msg = _normalize(message)
    if not msg:
        return False
    if ZH_MEANING_QUESTION_PHRASE not in msg:
        return False
    if extract_job_id(msg):
        return False
    if any(x in msg for x in ZH_VIEW_VERBS_CONCEPT_EXPLANATION):
        return False
    return True


def _status_concept_without_operational_anchor(message: str) -> bool:
    """Concept Q&A guardrail: phrases with 'what is/definition/meaning' and no task/system anchor skip tools."""
    msg = _normalize(message)
    if not msg:
        return False
    if any(k in msg for k in ZH_CONCEPT_DEF_PARTICLES) and ZH_MEANING_QUESTION_PHRASE not in msg:
        if not any(
            k in msg
            for k in ZH_STATUS_CONCEPT_ANCHOR_TERMS
        ):
            return True
    return False


def _wants_failure(msg: str) -> bool:
    low = msg.lower()
    if any(
        p in low
        for p in (
            "why did training fail",
            "why did the training fail",
        )
    ):
        return True
    return any(
        k in msg
        for k in ZH_FAILURE_QUERY_TERMS
    )


def _wants_failed_training_jobs_english(msg: str) -> bool:
    low = msg.lower()
    if "show failed training jobs" in low:
        return True
    if "failed training job" in low and any(w in low for w in ("show", "list", "what", "which")):
        return True
    return False


def _wants_context(msg: str) -> bool:
    return any(
        k in msg
        for k in ZH_CONTEXT_QUERY_TERMS
    )


def _wants_broad_list(msg: str) -> bool:
    return any(
        k in msg
        for k in ZH_BROAD_LIST_QUERY_TERMS
    )


def _wants_narrow_running_queued(msg: str, jid: Optional[str]) -> bool:
    if jid:
        return False
    zt_task, zt_stat, zt_prog, zt_list = ZH_NARROW_TASK_STATUS_TERMS
    return zt_task in msg and (zt_stat in msg or zt_prog in msg) and zt_list not in msg


def _looks_like_training_result_concept_question(msg: str) -> bool:
    if ZH_MEANING_QUESTION_PHRASE in msg and ZH_TRAINING_RESULT_PHRASE in msg:
        return True
    if any(p in msg for p in ZH_TRAINING_RESULT_CONCEPT_MARKERS):
        return True
    if ZH_TRAINING_RESULT_PHRASE in msg and (
        msg.rstrip().endswith(ZH_WHAT_IS_SUFFIX_PLAIN) or msg.rstrip().endswith(ZH_WHAT_IS_SUFFIX_QUESTION)
    ):
        return True
    return False


def _wants_training_summary(msg: str) -> bool:
    if _looks_like_training_result_concept_question(msg):
        return False
    low = msg.lower()
    if any(
        p in low
        for p in (
            "latest training result",
            "training summary",
            "training metrics",
            "training status",
            "completed training job",
            # Do not use "failed training job(s)" here: substring of "show failed training jobs"
            # would over-plan get_latest_training_summary (Stage 4D).
            "most recent training result",
            "recent training result",
        )
    ):
        return True
    if any(
        k in msg
        for k in ZH_TRAINING_SUMMARY_TERMS
    ):
        return True
    if ZH_TRAIN in msg and ZH_RESULT in msg and any(x in msg for x in ZH_TRAINING_RESULT_INTERROGATIVE_PARTICLES):
        return True
    if ZH_TRAIN in msg and any(x in msg for x in ZH_TRAINING_METRIC_TOKENS):
        return True
    if ZH_TRAIN in msg and any(x in msg for x in ZH_TRAINING_QUALITY_TOKENS):
        return True
    if ZH_MODEL in msg and ZH_PREDICT not in msg and any(x in msg for x in ZH_MODEL_SUPERLATIVE_TERMS):
        return True
    return False


def _wants_prediction_explanation(msg: str) -> bool:
    """Explanation asks: prefer read-only get_prediction_explanation_summary."""
    if is_prediction_combined_followup(msg):
        return False
    if looks_like_prediction_result_concept_question(msg):
        return False
    if any(p in msg for p in ZH_PREDICTION_EXPLANATION_PHRASES):
        return True
    if ZH_SHAP in msg and (ZH_SUMMARY in msg or ZH_EXPLAIN in msg):
        return True
    return False


def _wants_prediction_summary(msg: str) -> bool:
    if is_prediction_combined_followup(msg):
        return False
    if looks_like_prediction_result_concept_question(msg):
        return False
    # Only when the user explicitly names "prediction result" may we route to latest prediction summary.
    if any(k in msg for k in ZH_PREDICTION_SUMMARY_HEAD_TERMS):
        return True
    if ZH_PREDICTION_RESULT_JUST_NOW_PHRASE in msg or (ZH_JUST_NOW in msg and ZH_PREDICTION_RESULT_PHRASE in msg):
        return True
    if ZH_THIS_BATCH_PREDICT_PHRASE in msg and any(k in msg for k in ZH_PREDICTION_SUMMARY_FOLLOWUP_TERMS):
        return True
    if ZH_PREDICT in msg and ZH_RESULT in msg:
        return True
    if (ZH_PRED_LABEL_PHRASE in msg or ZH_PRED_PROB_PHRASE in msg) and any(
        a in msg for a in ZH_PREDICTION_LABEL_PROX_TERMS
    ):
        return True
    if ZH_PREDICT in msg and any(
        k in msg
        for k in ZH_PREDICTION_RISK_INTERP_TERMS
    ):
        return True
    if any(k in msg for k in ZH_PREDICTION_BATCH_SCOPE_TERMS) and (ZH_PREDICT in msg or ZH_RESULT in msg) and any(
        k in msg
        for k in ZH_PREDICTION_BATCH_EVAL_TERMS
    ):
        return True
    if ZH_THIS_BATCH_SHORT in msg and any(
        k in msg for k in ZH_PREDICTION_BATCH_TAIL_TERMS
    ):
        return True
    return False


def plan_readonly_tools(message: str) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
    """
    Plan read-only tool calls for this turn; supports composite sentences (multiple tools in fixed order).
    Returns None when the read-only tool chain should not run.
    """
    msg = _normalize(message)
    if not msg:
        return None

    if _concept_explanation_without_operational_anchor(msg):
        return None

    if _task_status_concept_phrase(msg):
        return None

    if _status_concept_without_operational_anchor(msg):
        return None

    steps: List[Tuple[str, Dict[str, Any]]] = []
    seen = set()

    def add(name: str, args: Dict[str, Any]) -> None:
        key = (name, tuple(sorted((args or {}).items())))
        if key in seen:
            return
        seen.add(key)
        steps.append((name, dict(args)))

    jid = extract_job_id(msg)

    if _wants_context(msg):
        add("get_current_context", {})

    if _wants_failed_training_jobs_english(msg):
        add("list_tasks", {"status": "failed", "limit": 50})
    elif _wants_broad_list(msg):
        add("list_tasks", {"limit": 30})
    elif jid:
        add("get_task_status", {"job_id": jid})
    elif _wants_narrow_running_queued(msg, jid):
        add("list_tasks", {"status": "running", "limit": 15})
        add("list_tasks", {"status": "queued", "limit": 15})

    if _wants_training_summary(msg):
        add("get_latest_training_summary", {})
    if is_prediction_combined_followup(msg):
        add("get_latest_prediction_summary", {})
        add("get_prediction_explanation_summary", {})
    else:
        if _wants_prediction_explanation(msg):
            add("get_prediction_explanation_summary", {})
        if _wants_prediction_summary(msg):
            add("get_latest_prediction_summary", {})

    if _wants_failure(msg):
        add("get_latest_failure", {})

    return steps if steps else None


def readonly_query_overrides_action_intent(message: str) -> bool:
    """
    When both action-style keywords and read-only planning match, prefer read-only if the utterance
    clearly asks for status/progress/failure-style information. (Only one primary route per turn;
    execution requests should be sent in a later turn.)
    """
    m = _normalize(message)
    if extract_job_id(m):
        return True
    low = m.lower()
    en_triggers = (
        "latest training result",
        "training summary",
        "training metrics",
        "training status",
        "completed training job",
        "failed training job",
        "failed training jobs",
        "why did training fail",
        "why did the training fail",
        "show failed training jobs",
    )
    if any(t in low for t in en_triggers):
        return True
    if any(t in m for t in ZH_READONLY_TRAINING_OVERRIDE_PHRASES):
        return True
    return any(t in m for t in ZH_READONLY_OVERRIDE_TRIGGER_TERMS)
