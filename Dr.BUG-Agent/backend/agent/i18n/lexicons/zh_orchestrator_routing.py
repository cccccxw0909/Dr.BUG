"""Chinese intent / routing literals for backend.agent.orchestrator (approved CJK concentration)."""

from __future__ import annotations

import re
from typing import Dict, Final, Pattern, Tuple

# Used when extracting "next step" text from verbatim assistant copy.
NEXT_STEP_PREFIX_ZH: Final[str] = "下一步："

# Completed recommendation result latch (substring match).
RECOMMENDATION_RESULT_NEEDLES: Final[Tuple[str, ...]] = (
    "推荐结果",
    "用药推荐结果",
    "推荐任务结果",
    "候选方案排序",
    "top1方案",
    "排名第一的方案",
    "推荐排序结果",
)

# Explicit prediction summary / explanation routing (substring match).
EXPLICIT_PREDICTION_SUMMARY_KEYWORDS: Final[Tuple[str, ...]] = (
    "预测结果",
    "最近一次预测",
    "刚才那个预测",
    "刚才的预测",
    "单样本预测结果",
    "批量预测结果",
    "为什么这样预测",
    "解释一下这次预测",
    "SHAP 摘要",
    "模型解释是什么",
    "这次批量预测",
    "结果和解释",
    "预测标签",
    "预测概率",
)

# Generic training/prediction progress phrasing (substring match).
GENERIC_STATUS_QUERY_KEYWORDS: Final[Tuple[str, ...]] = (
    "现在怎么样了",
    "结果出了没有",
    "好了吗",
    "结束了吗",
    "到哪一步了",
    "怎么样了",
    "多久",
    "多长时间",
    "还要等",
    "什么时候",
    "啥时候",
    "预计",
    "卡在哪",
    "筛选",
    "特征筛选",
    "什么阶段",
)

# Short utterances that may trigger the LLM status classifier fallback path.
FALLBACK_CLASSIFIER_HINTS_ZH: Final[Tuple[str, ...]] = (
    "好了吗",
    "怎么样",
    "如何了",
    "是不是完成",
    "完成没",
    "结果呢",
    "为什么这样",
    "为啥这样",
    "解释下",
    "解释一下",
)

FALLBACK_CLASSIFIER_HINTS_EN: Final[Tuple[str, ...]] = (
    "how is it",
    "is it done",
)

# Batch prediction entry detection.
BATCH_ENTRY_PREFIX_ZH: Final[str] = "批量"
PREDICTION_ENTRY_OPEN_BATCH_PATTERN: Final[str] = r"批量预测|批量推理|上传文件|上传文件预测"
PREDICTION_ENTRY_OPEN_BATCH_RE: Final[Pattern[str]] = re.compile(
    PREDICTION_ENTRY_OPEN_BATCH_PATTERN,
    re.IGNORECASE,
)

# Focus-bound classifier probe messages (Chinese only; English paths use separate wording upstream).
FOCUS_PROBE_TRAIN_COMPLETION: Final[str] = "训练结束了吗"
FOCUS_PROBE_TRAIN_PROGRESS: Final[str] = "现在训练到哪一步了"
FOCUS_PROBE_PRED_COMPLETION: Final[str] = "预测结束了吗"
FOCUS_PROBE_PRED_PROGRESS: Final[str] = "现在预测到哪一步了"

# Generic status binding probe (when job_type is not train/predict-specific branch).
GENERIC_FOCUS_PROBE: Final[str] = "现在到哪一步了"

# Read-only planner label (Chinese canonical) -> orchestrator i18n message key for English substitution.
READONLY_QUERY_ZH_TO_MSG_KEY: Final[Dict[str, str]] = {
    "运行中的任务": "orchestrator.readonly_label.running_tasks",
    "排队中的任务": "orchestrator.readonly_label.queued_tasks",
    "近期任务概况": "orchestrator.readonly_label.recent_overview",
    "工作区与模型概况": "orchestrator.readonly_label.workspace_model_overview",
    "工作台上下文摘要": "orchestrator.readonly_label.workspace_context",
    "指定任务状态": "orchestrator.readonly_label.specified_task_status",
    "最近失败信息": "orchestrator.readonly_label.latest_failure",
    "最近训练摘要": "orchestrator.readonly_label.latest_training",
    "最近预测摘要": "orchestrator.readonly_label.latest_prediction",
    "预测解释摘要": "orchestrator.readonly_label.prediction_explanation",
}
