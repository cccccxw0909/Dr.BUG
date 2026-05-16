"""Chinese substrings for recognizing legacy/localized error messages (compatibility only, not user-facing API copy)."""

from __future__ import annotations

from typing import Final, Tuple

PREDICTION_VALUE_ERROR_MISMATCH_FRAGMENTS: Final[Tuple[str, ...]] = (
    "模型不存在",
    "未注册",
    "模型未配置特征顺序",
)

PREDICTION_VALUE_ERROR_INVALID_FRAGMENTS: Final[Tuple[str, ...]] = (
    "请提供 model_id",
    "未填写",
    "校验",
    "表单为空",
    "格式不正确",
    "须为整数",
    "选项不合法",
    "已填特征过少",
    "仅支持 csv",
    "缺少关键必需字段",
)

TASK_CANCEL_NOT_FOUND_FRAGMENT: Final[str] = "不存在"
TASK_CANCEL_NOT_ALLOWED_FRAGMENT: Final[str] = "无法取消"
TASK_CANCEL_STATUS_AND_JOB_FRAGMENTS: Final[Tuple[str, str]] = ("当前状态", "任务")
TASK_CANCEL_SUCCEEDED_FRAGMENT: Final[str] = "已取消"
