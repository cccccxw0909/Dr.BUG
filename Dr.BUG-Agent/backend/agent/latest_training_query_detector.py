"""
Very narrow "latest training summary" detector for mcp_latest_training_summary; avoids colliding with mcp_context_query.
"""

from __future__ import annotations

import re
from typing import Optional

from backend.agent.i18n.lexicons.zh_latest_training_query_detector import (
    LATEST_TRAINING_FOCUS_RE,
    LATEST_TRAINING_NEGATIVE_RE,
    WORKFLOW_OR_STEP_PROBE_RE,
)
from backend.agent.i18n.lexicons.zh_routing_core_tokens import ZH_TRAIN

_NEG = re.compile(LATEST_TRAINING_NEGATIVE_RE)
_FOCUS = re.compile(LATEST_TRAINING_FOCUS_RE)


def is_narrow_mcp_latest_training_summary_query(message: Optional[str]) -> bool:
    m = (message or "").strip()
    if not m or len(m) > 120:
        return False
    if ZH_TRAIN not in m and "train" not in m.lower():
        return False
    if _NEG.search(m):
        return False
    if not _FOCUS.search(m):
        return False
    # Phrases like "which training step" belong to concise / workflow
    if re.search(WORKFLOW_OR_STEP_PROBE_RE, m):
        return False
    return True
