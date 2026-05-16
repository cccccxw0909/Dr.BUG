"""Chinese phrases for welcome / greeting intent detection (not user-facing catalog copy)."""

from __future__ import annotations

import re
from typing import Final, FrozenSet, Tuple

# Normalized greeting tokens (strip + collapse whitespace + lower on Latin).
GREETING_NORMALIZED: Final[FrozenSet[str]] = frozenset(
    {
        "你好",
        "您好",
        "嗨",
        "哈喽",
        "hello",
        "hi",
        "hey",
        "goodmorning",
        "goodafternoon",
        "goodevening",
        "在吗",
    }
)

# Substrings that imply task intent (mixed greetings must not match pure greeting).
TASK_INTENT_ZH_SUBSTR: Final[Tuple[str, ...]] = (
    "训练",
    "预测",
    "模型",
    "推荐",
    "方案",
    "用药",
    "数据集",
    "任务",
    "发布",
    "批量",
    "shap",
    "抗生素",
    "疗效",
    "比较方案",
    "对比方案",
)

# Characters stripped from utterance edges when testing pure greetings.
EDGE_STRIP_CHARS: Final[str] = ' \t\n\r!"\'「」『』().（）[]【】;；:：,，.。?？!！'

# Regex patterns applied to normalize_text() output for identity questions.
IDENTITY_QUERY_PATTERNS: Final[Tuple[str, ...]] = (
    r"你是谁",
    r"你是干什么的",
    r"你能做什么",
    r"你可以做什么",
    r"介绍一下你自己",
    r"whoareyou",
    r"whatcanyoudo",
    r"whatareyou",
)

TASK_INTENT_EN_RE = re.compile(
    r"\b(train|training|predict|prediction|model|dataset|datasets|recommend|regimen|regimens|batch|publish|shap)\b",
    re.I,
)
