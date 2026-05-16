from __future__ import annotations

import re
from typing import Dict, Optional

from backend.agent.normalizers import normalize_whitespace
from backend.agent.prediction_followup import suppresses_prediction_draft
from backend.agent.i18n.lexicons.zh_intent_parser import (
    ZH_MEANING_QUESTION_PHRASE,
    ZH_NEW_PREDICTION_MARKER,
    ZH_NEW_PREDICTION_PHRASE,
    ZH_NEW_PREDICTION_VOLITION_MARKERS,
    ZH_POINT_WHAT_PHRASE,
    ZH_PREDICTION_ENTRY_PREFIXES_A,
    ZH_PREDICTION_ENTRY_PREFIXES_B,
    ZH_TRAIN_ONE_PHRASE,
    ZH_UNIFIED_PREDICTION_ENTRY_PHRASE,
)
from backend.agent.i18n.lexicons.zh_routing_core_tokens import ZH_PREDICT, ZH_RECOMMEND, ZH_REPORT, ZH_TRAIN
from backend.agent.zh_intent_lexicon import (
    PRED_ENTRY_CLINICAL_TOPIC_RE,
    ZH_PREDICTION_DRAFT_SIGNAL_TERMS,
    ZH_PREDICTION_DRAFT_SINGLE_SAMPLE_RE,
    ZH_PREDICTION_ENTRY_EXACT_CMDS,
    ZH_TRAINING_COMMAND_TOKENS,
    ZH_TRAINING_CONCEPT_READONLY_PHRASES,
    ZH_TRAINING_SURVIVAL_SPAN_RE,
    ZH_WHAT_IS_TRAINING_TRIO_RE,
)

_MODEL_ID_RE = re.compile(r"(model_[a-zA-Z0-9_]+|demo_binary_v1|survival_28d_v1)", re.IGNORECASE)

# Natural utterances like “predict this patient’s survival” — open prediction workspace (no LLM essay).

# English imperative training commands -> pending draft path.
_ENGLISH_TRAIN_COMMAND = re.compile(
    r"(\bwant\s+to\s+train\b|\btrain\s+a\b|\btrain\s+an\b|\btrain\s+the\b|\btrain\s+my\b|\btrain\s+this\b|\btrain\s+your\b|"
    r"\btrain\s+a\s+[\w.-]+\s+model\b|"
    r"\btrain\s+models?\b|"
    r"\bstart(ing)?\s+training\b|\brun(ning)?\s+training\b|\bbegin(ning)?\s+training\b|"
    r"\bbuild\s+a\s+model\b|\bfit\s+a\s+model\b)",
    re.IGNORECASE,
)


def _english_training_command_intent(lowered: str) -> bool:
    return bool(_ENGLISH_TRAIN_COMMAND.search(lowered))


def _zh_training_concept_or_readonly_query(msg: str) -> bool:
    """Chinese: training status / result questions and definitions — not a training draft."""
    m = msg.strip()
    if ZH_MEANING_QUESTION_PHRASE in m and ZH_TRAIN in m:
        return True
    if ZH_WHAT_IS_TRAINING_TRIO_RE.search(m):
        return True
    if ZH_TRAIN in m and ZH_POINT_WHAT_PHRASE in m:
        return True
    for p in ZH_TRAINING_CONCEPT_READONLY_PHRASES:
        if p in m:
            return True
    return False


def _zh_training_command_intent(msg: str) -> bool:
    """Chinese: explicit requests to start or configure a training draft."""
    m = msg.strip()
    # Imperative / workflow tokens win over read-only subphrases in the same sentence (e.g. combined train command + status question).
    if any(t in m for t in ZH_TRAINING_COMMAND_TOKENS):
        return True
    if _zh_training_concept_or_readonly_query(m):
        return False
    if ZH_TRAIN_ONE_PHRASE in m:
        return True
    if ZH_TRAINING_SURVIVAL_SPAN_RE.search(m):
        return True
    return False


def is_prediction_entry_intent(message: str) -> bool:
    """
    Open unified prediction entry only (no structured payload, no pending).
    Uses exact phrases/prefixes to avoid accidental hits on internal phrases like "prepare single-sample prediction draft".
    """
    m = (message or "").strip()
    if not m or ZH_TRAIN in m:
        return False
    low = m.lower()
    if m in ZH_PREDICTION_ENTRY_EXACT_CMDS:
        return True
    if any(m.startswith(p) for p in ZH_PREDICTION_ENTRY_PREFIXES_A):
        return True
    if any(m.startswith(p) for p in ZH_PREDICTION_ENTRY_PREFIXES_B):
        return True
    if ZH_NEW_PREDICTION_PHRASE in m or (
        ZH_NEW_PREDICTION_MARKER in m and any(k in m for k in ZH_NEW_PREDICTION_VOLITION_MARKERS)
    ):
        return True
    if ZH_UNIFIED_PREDICTION_ENTRY_PHRASE in m:
        return True
    if "/predict" in low:
        return True
    return False


def _looks_like_open_prediction_workspace(message: str) -> bool:
    """Clinical or operational prediction request — route to prediction_entry instead of free-form LLM."""
    m = (message or "").strip()
    if not m or ZH_TRAIN in m:
        return False
    if PRED_ENTRY_CLINICAL_TOPIC_RE.search(m):
        return True
    low = m.lower()
    if re.search(r"\b(predict|prediction)\b.*\b(patient|survival|mortality|efficacy|batch|table)\b", low):
        return True
    return False


def wants_structured_prediction_draft(message: str) -> bool:
    """True when structured draft signals or controlled internal phrasing appear — then route to draft_single_prediction."""
    m = (message or "").strip()
    if not m:
        return False
    if any(s in m for s in ZH_PREDICTION_DRAFT_SIGNAL_TERMS):
        return True
    compact = m.replace(" ", "").lower()
    if "patient_features" in compact:
        return True
    text = normalize_whitespace(m)
    if not _MODEL_ID_RE.search(text):
        return False
    if "{" in text and "}" in text and ":" in text:
        return True
    return False


def parse_intent(message: str) -> Dict[str, Optional[str]]:
    raw = message or ""
    if not raw.strip():
        return {"action_type": None}

    if ZH_TRAIN in raw and _zh_training_command_intent(raw):
        return {"action_type": "draft_training_job"}

    lowered = raw.lower().strip()

    # English: only explicit training commands become draft_training_job (no raw "train" substring).
    if _english_training_command_intent(lowered):
        return {"action_type": "draft_training_job"}

    text = lowered
    predictish = (ZH_PREDICT in raw) or ("predict" in text)
    if predictish and suppresses_prediction_draft(message):
        predictish = False

    if predictish and is_prediction_entry_intent(message):
        return {"action_type": "prediction_entry"}

    if predictish and ZH_PREDICTION_DRAFT_SINGLE_SAMPLE_RE.search(message):
        return {"action_type": "draft_single_prediction"}
    if predictish and wants_structured_prediction_draft(message):
        return {"action_type": "draft_single_prediction"}
    if predictish and _looks_like_open_prediction_workspace(message):
        return {"action_type": "prediction_entry"}
    if predictish:
        return {"action_type": None}

    if (ZH_RECOMMEND in message) or ("regimen" in text):
        return {"action_type": "create_recommendation_job"}
    if (ZH_REPORT in message) or ("report" in text):
        return {"action_type": "create_report_job"}
    return {"action_type": None}
