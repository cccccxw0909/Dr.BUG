"""Chinese-only alias keys for clinical/report normalization (matching clinician or document text)."""

from __future__ import annotations

from typing import Dict, Final

ZH_CLINICAL_TASK_ALIASES: Final[Dict[str, str]] = {
    "28天死亡": "mortality_28d",
    "死亡": "mortality_28d",
    "疗效": "clinical_efficacy",
    "耐药": "polymyxin_resistance",
    "疗程": "treatment_duration",
}

ZH_REPORT_TYPE_ALIASES: Final[Dict[str, str]] = {
    "训练": "training_report",
    "预测": "prediction_report",
    "推荐": "recommendation_report",
}
