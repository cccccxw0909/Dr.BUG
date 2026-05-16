"""Chinese substrings used only for train/predict failure stage heuristics (not user-facing sentences)."""

from __future__ import annotations

from typing import Final

# Appears in lowercased training error message text (Chinese UI) to classify early-phase failures.
TRAIN_MSG_VALIDATION_CUE: Final[str] = "校验"

# Appear in localized prediction error hints when classifying failure buckets.
PREDICT_HINT_READ_CUE: Final[str] = "读"
PREDICT_HINT_FIELD_CUE: Final[str] = "字段"
PREDICT_HINT_MAP_CUE: Final[str] = "映射"
PREDICT_HINT_MODEL_CUE: Final[str] = "模型"
PREDICT_ROUGH_READ_PREFIX: Final[str] = "读取"
PREDICT_ROUGH_FIELD_OR_MAP: Final[str] = "字段"
PREDICT_ROUGH_MAP: Final[str] = "映射"
PREDICT_ROUGH_LOAD_MODEL: Final[str] = "加载模型"
PREDICT_ROUGH_ENV: Final[str] = "环境"
PREDICT_ROUGH_GENERATE: Final[str] = "生成"
