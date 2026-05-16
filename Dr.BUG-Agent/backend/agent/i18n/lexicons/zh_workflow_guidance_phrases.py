"""Chinese phrases for workflow guidance intent detection (next-step / continue style)."""

from __future__ import annotations

from typing import Final, Tuple

# Exclude narrow definition-style questions from workflow guidance routing.
DEFINITION_EXCLUDE_SUBSTRINGS: Final[Tuple[str, ...]] = (
    "是什么意思",
    "什么是",
)

# User utterances that signal organizational next-step guidance (not progress-only).
# Message substring markers for resolving workflow domain when no focused task is available.
WORKFLOW_DOMAIN_RECOMMENDATION_MSG_MARKERS: Final[Tuple[str, ...]] = ("推荐", "用药方案", "方案推荐", "regimen")
WORKFLOW_DOMAIN_TRAINING_MSG_MARKER: Final[str] = "训练"
WORKFLOW_DOMAIN_PREDICTION_MSG_MARKER: Final[str] = "预测"
WORKFLOW_DOMAIN_INFERENCE_MSG_MARKER: Final[str] = "推理"

WORKFLOW_GUIDANCE_NEXT_STEP_PHRASES: Final[Tuple[str, ...]] = (
    "下一步",
    "接下來",
    "接下来",
    "我该做什么",
    "我要做什么",
    "现在该做什么",
    "怎么办",
    "咋整",
    "如何做",
    "怎么做",
    "还差什么",
    "缺什么",
    "为什么停",
    "为啥停",
    "停在这里",
    "卡在这里",
    "继续哪",
    "继续做什么",
    "怎么继续",
    "如何继续",
    "继续干嘛",
    "然后呢",
    "然后呢？",
    "然后呢?",
    "我该继续",
    "要不要继续",
    "要不要做",
    "要不要提交",
    "要不要确认",
    "要不要执行",
)
