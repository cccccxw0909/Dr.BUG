from __future__ import annotations

from difflib import get_close_matches
from typing import Dict, Optional

from backend.agent.i18n.lexicons.zh_normalizers import ZH_CLINICAL_TASK_ALIASES, ZH_REPORT_TYPE_ALIASES

# Non-English alias keys below are for matching clinician or document text only.
# They are not intended as user-visible UI strings.

CLINICAL_TASK_ALIASES: Dict[str, str] = {
    **ZH_CLINICAL_TASK_ALIASES,
    "mortality": "mortality_28d",
    "clinical efficacy": "clinical_efficacy",
    "resistance": "polymyxin_resistance",
    "duration": "treatment_duration",
}

TASK_TYPE_ALIASES = CLINICAL_TASK_ALIASES

MODEL_TYPE_ALIASES: Dict[str, str] = {
    "xgb": "xgboost",
    "xgboost": "xgboost",
    "lgbm": "lightgbm",
    "lightgbm": "lightgbm",
    "catboost": "catboost",
    "rf": "random_forest",
    "random forest": "random_forest",
    "lr": "logistic_regression",
    "logistic": "logistic_regression",
    "svm": "svm",
    "knn": "knn",
}

REPORT_TYPE_ALIASES: Dict[str, str] = {
    "training": "training_report",
    "prediction": "prediction_report",
    "recommendation": "recommendation_report",
    **ZH_REPORT_TYPE_ALIASES,
}


def normalize_whitespace(text: str) -> str:
    return " ".join(text.lower().strip().split())


def fuzzy_pick(value: str, candidates: list[str]) -> Optional[str]:
    if not value or not candidates:
        return None
    if value in candidates:
        return value
    matches = get_close_matches(value, candidates, n=1, cutoff=0.55)
    return matches[0] if matches else None

