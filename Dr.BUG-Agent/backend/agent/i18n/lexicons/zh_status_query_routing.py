"""Chinese substrings for backend.agent.status_query_router (read-only tool planning)."""

from __future__ import annotations

from typing import Final, Tuple

from backend.agent.i18n.lexicons.zh_routing_core_tokens import (
    ZH_LIST,
    ZH_PROGRESS,
    ZH_STATUS,
    ZH_TASK,
)

ZH_TASK_STATUS_COMPOUND: Final[str] = "任务状态"
ZH_WHAT_IS_PAIR: Final[Tuple[str, str]] = ("是什么", "什么是")
ZH_MEANING_QUESTION_PHRASE: Final[str] = "是什么意思"
ZH_CONCEPT_DEF_PARTICLES: Final[Tuple[str, ...]] = ("是什么", "什么是", "定义", "含义")
ZH_TRAINING_RESULT_PHRASE: Final[str] = "训练结果"
ZH_WHAT_IS_SUFFIX_PLAIN: Final[str] = "是什么"
ZH_WHAT_IS_SUFFIX_QUESTION: Final[str] = "是什么？"
ZH_SHAP: Final[str] = "SHAP"
ZH_SUMMARY: Final[str] = "摘要"
ZH_EXPLAIN: Final[str] = "解释"
ZH_PREDICTION_RESULT_PHRASE: Final[str] = "预测结果"
ZH_JUST_NOW: Final[str] = "刚才"
ZH_PREDICTION_RESULT_JUST_NOW_PHRASE: Final[str] = "刚才的预测结果"
ZH_THIS_BATCH_PREDICT_PHRASE: Final[str] = "这次批量预测"
ZH_THIS_BATCH_SHORT: Final[str] = "这批"
ZH_PRED_LABEL_PHRASE: Final[str] = "预测标签"
ZH_PRED_PROB_PHRASE: Final[str] = "预测概率"

ZH_NARROW_TASK_STATUS_TERMS: Final[Tuple[str, ...]] = (ZH_TASK, ZH_STATUS, ZH_PROGRESS, ZH_LIST)
