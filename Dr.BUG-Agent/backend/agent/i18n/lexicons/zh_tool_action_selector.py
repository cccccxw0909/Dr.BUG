"""Chinese literals for backend.agent.tool_action_selector (pending control + workflow hints)."""

from __future__ import annotations

from typing import Final, FrozenSet, Tuple

ZH_PENDING_CONFIRM_PHRASES: Final[FrozenSet[str]] = frozenset(
    ("确认", "确认。", "好的确认", "好确认", "可以确认", "同意", "ok", "okay", "行")
)
ZH_PENDING_CONTINUE_PHRASES: Final[FrozenSet[str]] = frozenset(
    ("继续", "继续。", "继续吧", "先继续", "往下走", "往下进行")
)
ZH_PENDING_CANCEL_PHRASES: Final[FrozenSet[str]] = frozenset(
    ("取消", "取消。", "不要了", "算了", "否", "不", "不用", "别", "stop", "cancel")
)

ZH_TRAINING_RECENCY_ANCHOR_RE: Final[str] = r"(最近|刚才|刚刚|最新|上次|上一?次|最近一次)"
ZH_TRAINING_RESULT_QUALITY_RE: Final[str] = r"训练结果.{0,2}(如何|怎样|怎么样|啥样|好不好)"

ZH_STUCK_POINT: Final[str] = "卡点"
ZH_CURRENT_FLOW: Final[str] = "当前流程"
ZH_FLOW_PROGRESS_A: Final[str] = "流程走"
ZH_FLOW_PROGRESS_B: Final[str] = "流程到"
ZH_WORKFLOW_QUESTION_MARKERS: Final[Tuple[str, ...]] = ("哪", "什么", "怎么", "如何", "继续", "走")
