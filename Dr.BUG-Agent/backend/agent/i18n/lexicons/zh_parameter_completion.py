"""Chinese fragments for parameter extraction from natural language (regex + task-type keywords)."""

from __future__ import annotations

from typing import Final, List, Tuple

# Captures ASCII or CJK identifier tokens for target column names.
_CJK_ID_TOKEN: Final[str] = r"[\w\u4e00-\u9fff]+"

TARGET_COLUMN_EXTRACTION_PATTERNS: Final[List[str]] = [
    rf"目标列[:：\s]+['\"]?({_CJK_ID_TOKEN})['\"]?",
    rf"target[_\s]*column[:：\s]+['\"]?({_CJK_ID_TOKEN})['\"]?",
    rf"标签列[:：\s]+['\"]?({_CJK_ID_TOKEN})['\"]?",
]

ZH_ML_TASK_REGRESSION_MARKERS: Final[Tuple[str, ...]] = ("回归",)
ZH_ML_TASK_MULTICLASS_MARKERS: Final[Tuple[str, ...]] = ("多分类",)
ZH_ML_TASK_BINARY_MARKERS: Final[Tuple[str, ...]] = ("二分类",)
ZH_ML_TASK_GENERIC_CLASS_MARKERS: Final[Tuple[str, ...]] = ("分类",)
