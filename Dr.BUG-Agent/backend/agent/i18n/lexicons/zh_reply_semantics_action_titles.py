"""Canonical Chinese pending-action titles and English display mapping (aligned with orchestrator catalog)."""

from __future__ import annotations

from typing import Dict, Final

# Prefix match for reasons that already carry the "complete in UI" tail from upstream.
REASON_SKIP_APPEND_TAIL_IF_CONTAINS: Final[str] = "请先在界面"

CANONICAL_ACTION_TITLE_TRAINING: Final[str] = "训练配置"
CANONICAL_ACTION_TITLE_PREDICTION: Final[str] = "预测配置"
CANONICAL_ACTION_TITLE_SINGLE_PREDICTION: Final[str] = "单样本预测"
CANONICAL_ACTION_TITLE_BATCH_PREDICTION: Final[str] = "批量预测"
CANONICAL_ACTION_TITLE_RECOMMENDATION_CONFIG: Final[str] = "推荐配置"
CANONICAL_ACTION_TITLE_MEDICATION_RECOMMENDATION: Final[str] = "用药推荐"
CANONICAL_ACTION_TITLE_REPORT: Final[str] = "报告生成"
CANONICAL_ACTION_TITLE_PENDING: Final[str] = "待确认操作"

ACTION_TITLE_ZH_TO_EN: Final[Dict[str, str]] = {
    CANONICAL_ACTION_TITLE_TRAINING: "training configuration",
    CANONICAL_ACTION_TITLE_PREDICTION: "prediction configuration",
    CANONICAL_ACTION_TITLE_SINGLE_PREDICTION: "single-sample prediction",
    CANONICAL_ACTION_TITLE_BATCH_PREDICTION: "batch prediction",
    CANONICAL_ACTION_TITLE_RECOMMENDATION_CONFIG: "recommendation configuration",
    CANONICAL_ACTION_TITLE_MEDICATION_RECOMMENDATION: "medication recommendation",
    CANONICAL_ACTION_TITLE_REPORT: "report generation",
    CANONICAL_ACTION_TITLE_PENDING: "pending action",
}
