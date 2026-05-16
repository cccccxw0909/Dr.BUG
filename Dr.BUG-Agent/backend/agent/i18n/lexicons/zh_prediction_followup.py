"""Chinese phrases for prediction follow-up intent detection."""

from __future__ import annotations

import re
from typing import Final, Pattern, Tuple

TARGET_COLUMN_QUESTION_KEYWORDS: Final[Tuple[str, ...]] = (
    "目标变量",
    "目标列",
    "因变量",
    "结局变量",
    "label column",
    "哪一列",
    "哪个字段",
    "预测哪个标签",
    "预测的是哪个",
    "模型预测哪个",
)

EXPLICIT_GLOBAL_LATEST_PREDICTION_KEYWORDS: Final[Tuple[str, ...]] = (
    "最近一次预测",
    "最近一次有效预测",
    "最近一次预测结果",
    "最近一次的单样本预测",
)

RECENT_PREDICTION_RESULT_KEYWORDS: Final[Tuple[str, ...]] = ("结果", "输出", "标签", "概率", "怎样", "如何")

PREVIOUS_PREDICTION_KEYWORDS: Final[Tuple[str, ...]] = (
    "刚才的预测",
    "刚才那个预测",
    "上次预测",
    "上一次预测",
    "之前的预测",
)

WORKSPACE_PREDICTION_FOLLOWUP_KEYWORDS: Final[Tuple[str, ...]] = (
    "标签是什么",
    "预测标签是什么",
    "输出标签是什么",
    "预测输出标签",
    "概率是多少",
    "预测概率是多少",
    "可能性是多少",
    "风险高不高",
    "风险高吗",
    "风险低吗",
    "风险大不大",
    "预测结果是什么",
    "结果是多少",
    "当前预测结果",
)

STICKY_RISK_QUESTION_KEYWORDS: Final[Tuple[str, ...]] = ("风险高不高", "风险高吗", "风险低吗", "风险大不大")

STICKY_PROBABILITY_QUESTION_KEYWORDS: Final[Tuple[str, ...]] = ("概率是多少", "预测概率是多少", "可能性是多少")

STICKY_LABEL_QUESTION_KEYWORDS: Final[Tuple[str, ...]] = (
    "标签是什么",
    "预测标签是什么",
    "输出标签是什么",
    "预测输出标签",
)

STICKY_BATCH_KEYWORDS: Final[Tuple[str, ...]] = ("批量", "整批", "这批")

# Substrings used only in composite routing checks (not exported user-facing copy).
PRED_SUBSTRING: Final[str] = "预测"
TARGET_SUBSTRING: Final[str] = "目标"
RECENT_SUBSTRING: Final[str] = "最近"
TRAIN_PREFIX: Final[str] = "训练"
TRAIN_RESULT_PHRASE: Final[str] = "训练结果"
RESULT_SUBSTRING: Final[str] = "结果"
PROB_SUBSTRING: Final[str] = "概率"
LABEL_SUBSTRING: Final[str] = "标签"
HOW_MANY_SUBSTRING: Final[str] = "多少"
WHAT_SUBSTRING: Final[str] = "什么"
OUTPUT_SUBSTRING: Final[str] = "输出"

JUST_NOW_PREDICTION_RE: Final[Pattern[str]] = re.compile(r"刚才.*预测|预测.*刚才")

# --- prediction_followup.py routing (not user-facing reply templates) ---
PRED_CONFIG_PREFIX: Final[str] = "预测配置"
PRED_EXECUTE_VERBS: Final[Tuple[str, ...]] = ("执行预测", "确认预测", "开始预测")
PRED_COMBINED_RESULT_ORDER_A: Final[str] = "结果和解释"
PRED_COMBINED_RESULT_ORDER_B: Final[str] = "解释和结果"
PRED_RESULT_CONCEPT_SUFFIX_PLAIN: Final[str] = "是什么"
PRED_RESULT_CONCEPT_SUFFIX_QUESTION: Final[str] = "是什么？"
PRED_SUMMARY_TOKEN: Final[str] = "摘要"
PRED_EXPLAIN_TOKEN: Final[str] = "解释"
PRED_MEANING_QUESTION_PHRASE: Final[str] = "是什么意思"
PRED_RESULTS_PHRASE: Final[str] = "预测结果"
