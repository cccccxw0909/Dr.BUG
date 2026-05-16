"""
Arbitrate prediction follow-ups vs new-config entry: avoid misrouting result/explanation asks as concept questions or draft_single_prediction.
"""

from __future__ import annotations

from backend.agent.i18n.lexicons.zh_prediction_followup import (
    PRED_COMBINED_RESULT_ORDER_A,
    PRED_COMBINED_RESULT_ORDER_B,
    PRED_CONFIG_PREFIX,
    PRED_EXECUTE_VERBS,
    PRED_EXPLAIN_TOKEN,
    PRED_MEANING_QUESTION_PHRASE,
    PRED_RESULTS_PHRASE,
    PRED_RESULT_CONCEPT_SUFFIX_PLAIN,
    PRED_RESULT_CONCEPT_SUFFIX_QUESTION,
    PRED_SUMMARY_TOKEN,
    PRED_SUBSTRING,
    RESULT_SUBSTRING,
)
from backend.agent.i18n.lexicons.zh_intent_parser import (
    ZH_NEW_PREDICTION_MARKER,
    ZH_NEW_PREDICTION_PHRASE,
    ZH_NEW_PREDICTION_VOLITION_LOOSE,
    ZH_PREDICTION_ENTRY_WANT_PREFIXES,
    ZH_UNIFIED_PREDICTION_ENTRY_PHRASE,
)
from backend.agent.i18n.lexicons.zh_routing_core_tokens import ZH_TRAIN
from backend.agent.zh_intent_lexicon import (
    ZH_PRED_FOLLOWUP_LABEL_PROB_MARKERS,
    ZH_PREDICTION_COMBINED_RESULT_CONJ,
    ZH_PREDICTION_ENTRY_EXACT_FOLLOWUP,
    ZH_PREDICTION_FOLLOWUP_EXPLAIN_PHRASES,
    ZH_PREDICTION_FOLLOWUP_RECENT_PHRASES,
    ZH_PREDICTION_FOLLOWUP_TOPICS,
    ZH_PRED_RESULT_CONCEPT_PHRASES,
    ZH_PRED_RESULT_CONCEPT_TEMPORAL_RE,
    ZH_SUPPRESS_RESULT_EXPLAIN_EXTRA,
    ZH_TEMPORAL_ANCHORS,
)

# Temporal/discourse anchors: favor "follow up on an existing prediction" over pure definitional "what is a prediction result"


def explicit_new_prediction_config_intent(message: str) -> bool:
    """Only these phrases imply "new prediction config / draft" semantics (aligned with frontend entry)."""
    m = (message or "").strip()
    if not m or ZH_TRAIN in m:
        return False
    low = m.lower()
    if any(m.startswith(p) for p in ZH_PREDICTION_ENTRY_WANT_PREFIXES):
        return True
    if m == PRED_SUBSTRING or m.startswith(PRED_CONFIG_PREFIX):
        return True
    if ZH_NEW_PREDICTION_PHRASE in m or (
        ZH_NEW_PREDICTION_MARKER in m
        and any(k in m for k in ZH_NEW_PREDICTION_VOLITION_LOOSE)
    ):
        return True
    if m in ZH_PREDICTION_ENTRY_EXACT_FOLLOWUP:
        return True
    if ZH_UNIFIED_PREDICTION_ENTRY_PHRASE in m:
        return True
    if m in PRED_EXECUTE_VERBS:
        return True
    if "/predict" in low:
        return True
    return False


def suppresses_prediction_draft(message: str) -> bool:
    """
    When a "recent prediction follow-up" hits and there is no explicit new-config intent, block parse_intent from draft_single_prediction.
    """
    m = (message or "").strip()
    if not m:
        return False
    if explicit_new_prediction_config_intent(m):
        return False
    low = m.lower()
    # Explanation follow-ups may omit temporal anchors; still block new prediction-config draft
    if any(
        p in m
        for p in ZH_PREDICTION_FOLLOWUP_EXPLAIN_PHRASES
    ):
        return True
    if "SHAP" in m and (PRED_SUMMARY_TOKEN in m or PRED_EXPLAIN_TOKEN in m):
        return True
    if any(a in m for a in ZH_TEMPORAL_ANCHORS) and any(b in m for b in ZH_PREDICTION_FOLLOWUP_TOPICS):
        return True
    if (RESULT_SUBSTRING in m and PRED_EXPLAIN_TOKEN in m) and (
        any(a in m for a in ZH_TEMPORAL_ANCHORS) or any(x in m for x in ZH_SUPPRESS_RESULT_EXPLAIN_EXTRA)
    ):
        return True
    if any(p in m for p in ZH_PREDICTION_FOLLOWUP_RECENT_PHRASES):
        return True
    if any(marker in m for marker in ZH_PRED_FOLLOWUP_LABEL_PROB_MARKERS) and any(
        a in m for a in ZH_TEMPORAL_ANCHORS
    ):
        return True
    if ZH_PRED_RESULT_CONCEPT_TEMPORAL_RE.search(m):
        return True
    return False


def is_prediction_combined_followup(message: str) -> bool:
    """Combined result+explanation follow-up: fixed order summary then explanation."""
    m = (message or "").strip()
    if not m:
        return False
    if looks_like_prediction_result_concept_question(m):
        return False
    if (RESULT_SUBSTRING in m and PRED_EXPLAIN_TOKEN in m) and any(
        k in m for k in ZH_PREDICTION_COMBINED_RESULT_CONJ
    ):
        return True
    if PRED_COMBINED_RESULT_ORDER_A in m or PRED_COMBINED_RESULT_ORDER_B in m:
        return True
    return False


def looks_like_prediction_result_concept_question(msg: str) -> bool:
    """
    Pure definitional "what is a prediction result" asks; temporal "just now … what" is not treated as conceptual.
    """
    if any(a in msg for a in ZH_TEMPORAL_ANCHORS):
        return False
    if PRED_MEANING_QUESTION_PHRASE in msg and PRED_RESULTS_PHRASE in msg:
        return True
    if any(p in msg for p in ZH_PRED_RESULT_CONCEPT_PHRASES):
        return True
    if PRED_RESULTS_PHRASE in msg and (
        msg.rstrip().endswith(PRED_RESULT_CONCEPT_SUFFIX_PLAIN) or msg.rstrip().endswith(PRED_RESULT_CONCEPT_SUFFIX_QUESTION)
    ):
        return True
    return False
