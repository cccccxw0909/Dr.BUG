"""Locale pairs for backend.agent.workflow_guidance (deterministic summary skeleton)."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "workflow_guidance.summary.header": (
        "工作流域：{domain}；阶段：{stage}；目标：{goal}。",
        "Workflow domain: {domain}; stage: {stage}; goal: {goal}.",
    ),
    "workflow_guidance.summary.recommendation_state": (
        "推荐工作流状态：{state}。",
        "Recommendation workflow state: {state}.",
    ),
    "workflow_guidance.summary.followup_actions": (
        "可用后续动作：{actions}。",
        "Available follow-up actions: {actions}.",
    ),
    "workflow_guidance.summary.blockers": (
        "阻塞点：{blockers}",
        "Blocking points: {blockers}",
    ),
    "workflow_guidance.summary.preferred_next": (
        "首选下一步：{title}（{reason}）",
        "Preferred next step: {title} ({reason})",
    ),
    "workflow_guidance.summary.draft_hint": (
        "如需调整，可在聊天说明以生成草稿，但仍需在界面确认后才会执行。",
        "You can describe changes in chat to regenerate a draft, but execution still requires confirmation in the UI.",
    ),
}
