"""Chinese token spellings for backend.agent.query_normalization evidence keys (values must stay stable)."""

from __future__ import annotations

from typing import Final

# intent_hint keys (also matched as substrings in user text)
QN_TOKEN_PROGRESS: Final[str] = "进度"
QN_ALT_STATUS: Final[str] = "状态"
QN_ALT_DONE: Final[str] = "完成"
QN_ALT_READY_QUESTION: Final[str] = "好了吗"
QN_ALT_HOW: Final[str] = "怎么样"

QN_TOKEN_EXPLAIN: Final[str] = "解释"
QN_ALT_WHY: Final[str] = "为什么"
QN_ALT_WHY2: Final[str] = "为何"
QN_ALT_READ: Final[str] = "怎么看"

QN_TOKEN_EDIT: Final[str] = "修改"
QN_ALT_EDIT_SHORT: Final[str] = "改一下"
QN_ALT_ADJUST: Final[str] = "调整"
QN_ALT_REWRITE: Final[str] = "重写"

# scope_hint
QN_SCOPE_TRAIN: Final[str] = "训练"
QN_SCOPE_PREDICT: Final[str] = "预测"
QN_SCOPE_RECENT: Final[str] = "最近"
QN_SCOPE_JUST_NOW: Final[str] = "刚才"
QN_SCOPE_LATEST: Final[str] = "最新"
