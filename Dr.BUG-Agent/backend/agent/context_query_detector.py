"""
Very narrow workbench-context question detector for mcp_context_query routing; avoids intercepting normal business utterances.
"""

from __future__ import annotations

import re
from typing import Optional

from backend.agent.zh_intent_lexicon import (
    BARE_CURRENT_MODEL_METRICS_EXCLUDE_RE,
    MODEL_SELECTION_CONTEXT_EXCLUDE_RE,
    MODEL_SELECTION_CONTEXT_RE,
    MODEL_SELECTION_METRICS_EXCLUDE_RE,
    MODEL_SELECTION_WHICH_MODEL_RE,
    NEG_PROGRESS_CONTEXT_RE,
    STRONG_CONTEXT_PATTERNS,
    ZH_BARE_CURRENT_MODEL_TERMS,
    ZH_LLM_MODEL_QUERY_TERMS,
)


def _model_selection_context(msg: str) -> bool:
    if MODEL_SELECTION_CONTEXT_EXCLUDE_RE.search(msg):
        return False
    if MODEL_SELECTION_METRICS_EXCLUDE_RE.search(msg):
        return False
    if MODEL_SELECTION_CONTEXT_RE.search(msg):
        return True
    if MODEL_SELECTION_WHICH_MODEL_RE.search(msg):
        return True
    return False


def _bare_current_model_ok(msg: str) -> bool:
    if not any(k in msg for k in ZH_BARE_CURRENT_MODEL_TERMS):
        return False
    if len(msg) > 36:
        return False
    if BARE_CURRENT_MODEL_METRICS_EXCLUDE_RE.search(msg):
        return False
    return True


def is_narrow_mcp_context_query(message: Optional[str]) -> bool:
    m = (message or "").strip()
    if not m or len(m) > 96:
        return False
    if NEG_PROGRESS_CONTEXT_RE.search(m):
        return False
    for p in STRONG_CONTEXT_PATTERNS:
        if p.search(m):
            return True
    if _model_selection_context(m):
        return True
    if _bare_current_model_ok(m):
        return True
    if any(k in m for k in ZH_LLM_MODEL_QUERY_TERMS):
        return True
    return False
