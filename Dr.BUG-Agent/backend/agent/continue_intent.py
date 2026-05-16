from __future__ import annotations

import re

from backend.agent.i18n.lexicons.zh_continue_intent import ZH_CONTINUE
from backend.agent.zh_intent_lexicon import (
    ZH_CONTINUE_ACT_ACK_TOKENS,
    ZH_CONTINUE_ACT_BLOCKLIST,
    ZH_CONTINUE_ACT_PHRASES,
    ZH_CONTINUE_EXPLAIN_STANDALONE,
    ZH_CONTINUE_EXPLAIN_SUFFIXES,
)


def wants_continue_to_explain(message: str) -> bool:
    m = (message or "").strip()
    if not m or len(m) > 120:
        return False
    if ZH_CONTINUE in m and any(
        k in m
        for k in ZH_CONTINUE_EXPLAIN_SUFFIXES
    ):
        return True
    if any(k in m for k in ZH_CONTINUE_EXPLAIN_STANDALONE):
        return True
    return False


def wants_continue_to_act(message: str) -> bool:

    if wants_continue_to_explain(message):
        return False
    m = (message or "").strip()
    if not m or len(m) > 80:
        return False
    # Full business sentences like "draft training job" belong to parse_intent / draft main chain; avoid mis-hitting short "help me draft" continuations.
    if any(b in m for b in ZH_CONTINUE_ACT_BLOCKLIST):
        return False
    low = m.lower()
    if m in ZH_CONTINUE_ACT_ACK_TOKENS:
        return True
    if any(p in m for p in ZH_CONTINUE_ACT_PHRASES):
        return True
    if re.match(r"^(ok|okay|go ahead)\b", low):
        return True
    return False
