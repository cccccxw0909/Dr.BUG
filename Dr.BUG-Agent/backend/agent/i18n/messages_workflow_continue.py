"""Locale pairs for backend.agent.workflow_continue."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "workflow_continue.explain.user_intent": (
        "用户希望继续解释上一条工作流建议，而非起草执行。",
        "The user wants more explanation about the last workflow suggestion, not drafting execution.",
    ),
    "workflow_continue.explain.bullet_clarify": (
        "这是对上一条「下一步建议」的补充说明请求。",
        "This is a follow-up asking for clarification about the previous next-step suggestion.",
    ),
    "workflow_continue.explain.bullet_no_draft": (
        "不会创建待确认执行草稿。",
        "No executable pending draft will be created.",
    ),
    "workflow_continue.explain.summary": (
        "我会只补充解释建议背后的原因与注意点；不会代为起草或提交执行任务。",
        "I will only explain the rationale and caveats behind the suggestion; I will not draft or submit execution on your behalf.",
    ),
    "workflow_continue.pending_conflict.user_intent": (
        "continue-to-act 被拦截：已有待确认动作。",
        "continue-to-act blocked: a pending action already exists.",
    ),
    "workflow_continue.pending_conflict.bullet": (
        "当前会话已存在未处理完的待确认卡片。",
        "This session still has an unfinished pending confirmation card.",
    ),
    "workflow_continue.pending_conflict.summary": (
        "请先在工作台处理或取消现有待确认项后，再让我为新的步骤起草草稿。",
        "Please resolve or cancel the existing pending confirmation in the workbench before I draft a new step.",
    ),
    "workflow_continue.guidance_expired.user_intent": (
        "continue-to-act：上一条工作流建议已超过保留时间。",
        "continue-to-act: the last workflow suggestion is past its retention window.",
    ),
    "workflow_continue.guidance_expired.bullet": (
        "已保存的「下一步建议」已超过 follow-up 有效期（TTL），系统已丢弃过期快照。",
        "The stored next-step suggestion exceeded its follow-up TTL and was discarded.",
    ),
    "workflow_continue.guidance_expired.summary": (
        "guidance 已过期：请重新询问「下一步该怎么做」以刷新建议，再让我承接起草。",
        "That guidance has expired: ask again what to do next to refresh suggestions before asking me to draft.",
    ),
    "workflow_continue.no_stored_guidance.user_intent": (
        "continue-to-act：无最近可承接的工作流建议。",
        "continue-to-act: there is no recent workflow suggestion to continue from.",
    ),
    "workflow_continue.no_stored_guidance.bullet": (
        "当前会话下没有已保存的「下一步建议」快照；可能尚未询问过下一步，或记录属于其他会话。",
        "No saved next-step snapshot exists for this session; you may not have asked for next steps yet, or it belongs to another session.",
    ),
    "workflow_continue.no_stored_guidance.summary": (
        "无最近 guidance 可承接：请先在本会话再问一次「下一步该怎么做」，生成新的建议后再让我起草待确认草稿。",
        "No recent guidance to continue from: ask what to do next again in this session, then ask me to draft the pending confirmation.",
    ),
    "workflow_continue.drift.user_intent": (
        "continue-to-act：guidance 上下文漂移，不能承接起草。",
        "continue-to-act: guidance context drift; drafting cannot continue safely.",
    ),
    "workflow_continue.drift.bullet_detail": (
        "具体原因：{lab}（reason={code}）。",
        "Reason detail: {lab} (reason={code}).",
    ),
    "workflow_continue.drift.bullet_refresh": (
        "请重新询问「下一步该怎么做」以刷新工作流建议，再让我承接待确认草稿。",
        "Ask what to do next again to refresh workflow suggestions, then have me draft the pending confirmation.",
    ),
    "workflow_continue.drift.summary": (
        "guidance 已过期或上下文漂移：为安全起见，我不会用旧建议直接起草；请先刷新下一步建议。",
        "Guidance is stale or context drifted: for safety I will not draft from the old suggestion; refresh next-step guidance first.",
    ),
    "workflow_continue.drift_label.workflow_domain": (
        "工作流域已相对上次建议变化",
        "The workflow domain changed compared with the saved suggestion.",
    ),
    "workflow_continue.drift_label.focus_job": (
        "焦点任务 ID 已变化",
        "The focus job id changed.",
    ),
    "workflow_continue.drift_label.recommendation_state": (
        "推荐生命周期状态已变化",
        "The recommendation lifecycle state changed.",
    ),
    "workflow_continue.drift_label.prediction_context": (
        "预测单批或列映射阶段等信号已变化",
        "Prediction batch mode or column-mapping stage signals changed.",
    ),
    "workflow_continue.drift_label.workspace_model": (
        "工作台所选模型已变化",
        "The workbench selected model changed.",
    ),
    "workflow_continue.drift_label.workspace_mode": (
        "页面模式（mode）已变化",
        "The page mode changed.",
    ),
    "workflow_continue.drift_label.workflow_goal": (
        "工作流目标已变化",
        "The workflow goal changed.",
    ),
    "workflow_continue.drift_label.workflow_stage": (
        "工作流阶段已变化",
        "The workflow stage changed.",
    ),
    "workflow_continue.drift_label.generic": (
        "其他上下文指纹不一致",
        "Other context fingerprints no longer match.",
    ),
    "workflow_continue.drift_label.fallback": (
        "上下文与上次保存的建议不一致",
        "The context no longer matches the saved suggestion.",
    ),
    "workflow_continue.rec_completed.user_intent": (
        "continue-to-act：推荐已完成，不应再次起草推荐任务。",
        "continue-to-act: the recommendation is already completed; do not draft another recommendation task.",
    ),
    "workflow_continue.rec_completed.bullet_review": (
        "推荐任务已完成：更适合先查看方案排序、比较 original 与 top1、阅读解释，或回到预测工作流。",
        "The recommendation run is finished: review ranked regimens, compare baseline vs top1, read explanations, or return to prediction.",
    ),
    "workflow_continue.rec_completed.bullet_no_redraft": (
        "不会再次创建推荐 pending 或直接触发推荐执行。",
        "I will not create another recommendation pending action or trigger execution from chat.",
    ),
    "workflow_continue.rec_completed.summary": (
        "recommendation completed 后不允许 redraft：这一步我不为你起草新的推荐待确认项。",
        "After recommendation completes, redrafting is not supported: I will not draft a new recommendation pending item here.",
    ),
    "workflow_continue.rec_failed.user_intent": (
        "continue-to-act：推荐失败后应先走恢复指引，不直连重试执行。",
        "continue-to-act: after a failed recommendation, follow recovery guidance instead of retrying in chat.",
    ),
    "workflow_continue.rec_failed.bullet_recover": (
        "失败场景下请先在任务详情查看错误、修复前置条件，再重新获取「下一步」建议。",
        "On failure, check errors in task detail, fix prerequisites, then ask for next steps again.",
    ),
    "workflow_continue.rec_failed.bullet_no_retry": (
        "我不会在对话里替你重试执行推荐任务。",
        "I will not retry recommendation execution for you in chat.",
    ),
    "workflow_continue.rec_failed.summary": (
        "failed 后不做 continue 重试：请先按工作流建议排查，再决定是否重新起草推荐草稿。",
        "No continue-to-retry after failure: troubleshoot per workflow guidance, then decide whether to draft again.",
    ),
    "workflow_continue.rec_running.user_intent": (
        "continue-to-act：推荐在排队/运行中，不应并行起草新的推荐。",
        "continue-to-act: recommendation is queued or running; do not draft a parallel recommendation.",
    ),
    "workflow_continue.rec_running.bullet_wait": (
        "任务在队列或计算中时，请等待结束并在任务面板查看状态。",
        "While queued or running, wait for completion and check status in the task panel.",
    ),
    "workflow_continue.rec_running.bullet_no_draft": (
        "此阶段不会映射为新的推荐待确认草稿。",
        "This phase will not map to a new recommendation pending draft.",
    ),
    "workflow_continue.rec_running.summary": (
        "running/queued 不起新 draft：请先等待当前推荐任务结束。",
        "While running or queued, no new draft: wait for the current recommendation job to finish.",
    ),
    "workflow_continue.rec_state_not_ready.user_intent": (
        "continue-to-act：推荐状态已非可起草态。",
        "continue-to-act: recommendation state is no longer draftable.",
    ),
    "workflow_continue.rec_state_not_ready.bullet": (
        "上一条快照中的 recommendation_state 与当前可承接条件不一致；请重新询问下一步。",
        "recommendation_state in the saved snapshot conflicts with current draftable conditions; ask for next steps again.",
    ),
    "workflow_continue.rec_state_not_ready.summary": (
        "当前不适合承接推荐起草：请刷新工作流建议后再试。",
        "Recommendation drafting is not appropriate now; refresh workflow guidance and try again.",
    ),
    "workflow_continue.precondition_failed.user_intent": (
        "continue-to-act：当前前置条件不足以生成待确认草稿。",
        "continue-to-act: prerequisites are insufficient to generate a pending confirmation draft.",
    ),
    "workflow_continue.precondition_failed.bullet": (
        "例如尚未选定模型、训练任务状态已变化、推荐方案库为空，或上一条建议本身不可映射为可起草动作。",
        "For example: no model selected, training status changed, regimen library empty, or the suggestion cannot map to a draftable action.",
    ),
    "workflow_continue.precondition_failed.summary": (
        "当前前置条件不足，不能起草：请在工作台补齐必要条件，或重新获取下一步建议。",
        "Prerequisites are missing so I cannot draft: complete required setup in the workbench, or refresh next-step guidance.",
    ),
}
