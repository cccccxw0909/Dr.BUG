"""Chinese literals for backend.agent.intent_parser (draft vs read-only disambiguation)."""

from __future__ import annotations

from typing import Final, Tuple

ZH_MEANING_QUESTION_PHRASE: Final[str] = "是什么意思"
ZH_POINT_WHAT_PHRASE: Final[str] = "指什么"
ZH_TRAIN_ONE_PHRASE: Final[str] = "训练一个"

ZH_PREDICTION_ENTRY_WANT_PREFIXES: Final[Tuple[str, str]] = ("我想预测", "我要预测")
ZH_PREDICTION_ENTRY_PREFIXES_A: Final[Tuple[str, ...]] = ("我想预测", "我要预测", "帮我预测")
ZH_PREDICTION_ENTRY_PREFIXES_B: Final[Tuple[str, ...]] = ("做个预测", "预测一下")
ZH_NEW_PREDICTION_PHRASE: Final[str] = "做一个新预测"
ZH_NEW_PREDICTION_MARKER: Final[str] = "新预测"
ZH_NEW_PREDICTION_VOLITION_LOOSE: Final[Tuple[str, str, str]] = ("我要", "想", "帮我")
ZH_NEW_PREDICTION_VOLITION_MARKERS: Final[Tuple[str, ...]] = ("我要", "我想", "帮我")
ZH_UNIFIED_PREDICTION_ENTRY_PHRASE: Final[str] = "统一预测入口"
