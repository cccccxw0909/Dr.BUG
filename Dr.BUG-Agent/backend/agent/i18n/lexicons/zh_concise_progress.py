"""Chinese literals for backend.agent.concise_progress routing."""

from __future__ import annotations

from typing import Final, Tuple

from backend.agent.i18n.lexicons.zh_routing_core_tokens import (
    ZH_ACCURACY,
    ZH_AND,
    ZH_BATCH,
    ZH_METRIC,
    ZH_MODEL_TRAIN_PHRASE,
    ZH_PREDICT,
    ZH_RESULT,
    ZH_TRAIN,
)

ZH_TRAIN_RESULT_PHRASE: Final[str] = "训练结果"
ZH_PRED_RESULT_PHRASE: Final[str] = "预测结果"
ZH_BATCH_PREDICT_PHRASE: Final[str] = "批量预测"
ZH_FILTER: Final[str] = "筛选"

ZH_TRAIN_QUALITY_PHRASES: Final[Tuple[str, ...]] = (
    ZH_METRIC,
    "auc",
    "AUC",
    ZH_ACCURACY,
    "效果怎么样",
    "训练怎么样",
    "训练如何",
)

ZH_PRED_QUALITY_PHRASES: Final[Tuple[str, ...]] = (
    ZH_METRIC,
    "auc",
    "AUC",
    ZH_ACCURACY,
    "预测怎么样",
    "预测如何",
)

ZH_RESULT_OUTCOME_HINTS: Final[Tuple[str, ...]] = ("出来", "出了没", "出了吗")
