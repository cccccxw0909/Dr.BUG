"""Locale pairs for backend.agent.orchestrator user-facing copy and system prompts."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "orchestrator.readonly_mixed_hint": (
        "\n\n——\n我先回答了当前查询。若要继续执行训练、预测或推荐，请在下一条消息中明确告诉我。",
        "\n\n——\nI answered the current query first. "
        "To continue with training, prediction, or regimen comparison, send the action as a separate request.",
    ),
    "orchestrator.tool_readonly.with_verbatim": (
        "只读查询：需要结合系统摘要答复用户。",
        "Read-only query: answer the user using the system summary together with tool facts.",
    ),
    "orchestrator.tool_readonly.without_verbatim": (
        "只读查询：根据工具脱敏结果解释当前局面。",
        "Read-only query: explain the situation from sanitized tool outputs.",
    ),
    "orchestrator.chat_system.metric_hint": (
        "当前所选模型任务类型摘要（来自注册表，非患者数据）：{task_hint}。"
        "用户若问 AUC、C-index、校准等指标，请先按该任务类型作答，再补充通用说明。",
        "Selected model task-type summary (from registry, not patient data): {task_hint}. "
        "If the user asks about AUC, C-index, calibration, etc., answer for that task type first, then add general caveats.",
    ),
    "orchestrator.chat_system.body": (
        "你是临床工作台中的对话助手。"
        "你可以回答一般医学/机器学习概念问题，并可用一句话引导用户去工作台执行高风险操作。"
        "你不得访问或复述任何患者级原始表格、逐行样本、或可重新识别个人的明细；"
        "若用户询问此类数据，请拒绝并建议其使用工作台中的合规导出/脱敏流程。"
        "你不得编造系统中不存在的任务 ID、任务状态或运行结果；不确定时请明确说无法从当前信息确认。"
        "执行类动作（训练、预测、推荐、报告等）必须经界面确认（pending_confirmation）完成，"
        "你不得声称已代为执行或绕过确认。"
        "若任务仓库或页面焦点上已有处于 running / queued / waiting_user 的训练任务，而用户询问的是进度、阶段或耗时，"
        "你必须以该训练任务的真实状态为准作答，不得回答「训练尚未启动」或把用户引导到与真实状态矛盾的 pending 路径。"
        "系统支持通过只读工具查询进度、失败原因、训练/预测结果摘要与工作区上下文；你本人不要假装已读取后台数据库。"
        "回答用户问题时，优先采用分段：当前状态；原因或摘要；下一步建议。避免 Markdown 星号加粗、反引号包裹的技术标签、"
        "以及英文错误码堆砌；用语贴近临床工作台而非调试日志。"
        "回答保持简洁、可操作。"
        "当前页面上下文字段摘要（非原始数据）：mode={mode}; dataset={dataset}; model={model}。"
        "{metric_hint}",
        "You are the clinical workbench chat assistant. "
        "You may answer general medical / ML questions and may use one sentence to direct the user to run high-risk actions in the workbench UI. "
        "You must not access or restate patient-level raw tables, row-by-row samples, or identifiable line-level detail; "
        "if asked, refuse and point them to compliant export / de-identification flows in the workbench. "
        "You must not invent task IDs, task states, or run outcomes that are not in the system; say clearly when the current information is insufficient. "
        "Executable actions (training, prediction, recommendation, reports, etc.) require UI confirmation (pending_confirmation); "
        "do not claim you executed them or bypassed confirmation. "
        "If the task repository or page focus already has a training job in running / queued / waiting_user and the user asks about progress, stage, or ETA, "
        "you must answer from that real task state—do not say training has not started or steer them to a pending path that contradicts truth. "
        "The system supports read-only tools for progress, failure reasons, training/prediction summaries, and workspace context; do not pretend you queried raw databases. "
        "Prefer three parts: current state; reason or summary; next-step suggestion. Avoid Markdown bold stars, backtick-wrapped technical tags, "
        "and dumping raw English error codes; sound like a clinical workbench, not a debug log. "
        "Keep answers concise and actionable. "
        "Page context summary (not raw PHI): mode={mode}; dataset={dataset}; model={model}. "
        "{metric_hint}",
    ),
    "orchestrator.pending_welcome.create_training_job": ("训练任务", "Training"),
    "orchestrator.pending_welcome.draft_training_job": ("训练任务", "Training"),
    "orchestrator.pending_welcome.create_prediction_job": ("预测任务", "Prediction"),
    "orchestrator.pending_welcome.draft_single_prediction": ("单样本预测", "Single-sample prediction"),
    "orchestrator.pending_welcome.create_recommendation_job": ("推荐任务", "Recommendation"),
    "orchestrator.pending_welcome.create_report_job": ("报告或发布", "Report or publish"),
    "orchestrator.pending_welcome.prediction_entry": ("预测入口", "Prediction entry"),
    "orchestrator.user_action_title.create_training_job": ("训练配置", "training configuration"),
    "orchestrator.user_action_title.draft_training_job": ("训练配置", "training configuration"),
    "orchestrator.user_action_title.create_prediction_job": ("预测配置", "prediction configuration"),
    "orchestrator.user_action_title.draft_single_prediction": ("预测配置", "prediction configuration"),
    "orchestrator.user_action_title.create_recommendation_job": ("用药推荐", "medication recommendation"),
    "orchestrator.user_action_title.create_report_job": ("报告生成", "report generation"),
    "orchestrator.user_action_title.default": ("待确认操作", "pending action"),
    "orchestrator.training_user_title": ("训练配置", "training configuration"),
    "orchestrator.field.training.dataset_id": ("数据集", "dataset"),
    "orchestrator.field.training.clinical_task_id": ("临床任务", "clinical task"),
    "orchestrator.field.training.ml_task_type": ("ML 任务类型", "ML task type"),
    "orchestrator.field.training.target_column": ("目标列", "target column"),
    "orchestrator.field.training.selected_features": ("候选特征", "candidate features"),
    "orchestrator.field.training.final_features": ("最终入模特征", "final model features"),
    "orchestrator.field.training.med_cols": ("强制纳入列", "forced-in columns"),
    "orchestrator.field.training.model_type": ("模型类型", "model type"),
    "orchestrator.field.training.model_name": ("模型名称", "model name"),
    "orchestrator.field.training.feature_set": ("特征组", "feature set"),
    "orchestrator.field.training.objective_metric": ("主指标", "primary metric"),
    "orchestrator.field.training.publish_overrides": ("发布选项", "release options"),
    "orchestrator.field.prediction.model_id": ("模型", "model"),
    "orchestrator.field.prediction.patient_features": ("患者特征（表单）", "patient feature form"),
    "orchestrator.field.prediction.prediction_mode": ("预测模式", "prediction mode"),
    "orchestrator.field.prediction.task_name": ("任务名称", "task name"),
    "orchestrator.missing_fields_contract_placeholder": ("（见契约）", "see contract"),
    "orchestrator.readonly_label.running_tasks": ("运行中的任务", "running tasks"),
    "orchestrator.readonly_label.queued_tasks": ("排队中的任务", "queued tasks"),
    "orchestrator.readonly_label.recent_overview": ("近期任务概况", "recent task overview"),
    "orchestrator.readonly_label.workspace_model_overview": ("工作区与模型概况", "workspace and model overview"),
    "orchestrator.readonly_label.workspace_context": ("工作台上下文摘要", "workspace context summary"),
    "orchestrator.readonly_label.specified_task_status": ("指定任务状态", "specified task status"),
    "orchestrator.readonly_label.latest_failure": ("最近失败信息", "latest failure information"),
    "orchestrator.readonly_label.latest_training": ("最近训练摘要", "latest training summary"),
    "orchestrator.readonly_label.latest_prediction": ("最近预测摘要", "latest prediction summary"),
    "orchestrator.readonly_label.prediction_explanation": ("预测解释摘要", "prediction explanation summary"),
    "orchestrator.pred_readonly.no_recent": ("当前没有可供摘要的最近预测记录。", "No recent prediction record available for summary."),
    "orchestrator.pred_readonly.batch_first_line": (
        "【批量预测摘要】任务「{task}」，模型「{model}」；共 {tr} 行，成功 {sr}，失败 {fr}。{summary}",
        'Batch prediction summary: task “{task}”, model “{model}”; {tr} rows total, {sr} succeeded, {fr} failed. {summary}',
    ),
    "orchestrator.pred_readonly.summary_none": ("（无）", "(none)"),
    "orchestrator.pred_readonly.single_first_line": (
        "【单样本预测摘要】任务「{task}」，模型「{model}」；标签：{label}，概率：{prob}。摘要：{summary}",
        'Single-sample prediction summary: task “{task}”, model “{model}”; label: {label}, probability: {prob}. Summary: {summary}',
    ),
    "orchestrator.pred_readonly.explain_none": ("【解释】当前无解释块返回。", "Explanation: no explanation block was returned."),
    "orchestrator.pred_readonly.explain_batch_no_shap": (
        "【解释】本次为批量预测，不提供单样本 SHAP/逐特征解释；如需单条解释请使用单样本预测入口。",
        "Explanation: batch predictions do not provide per-sample SHAP/feature explanations; "
        "use the single-sample prediction entry if you need row-level explanation.",
    ),
    "orchestrator.pred_readonly.explain_line": ("【解释】{text}", "Explanation: {text}"),
    "orchestrator.status_payload.intent_progress": (
        "询问进度、阶段或任务完成情况",
        "The user is asking about progress, stage, or task completion.",
    ),
    "orchestrator.status_payload.intent_generic_bind": (
        "泛化状态问句绑定到当前焦点任务",
        "A generic status question is bound to the current focus task.",
    ),
    "orchestrator.status_payload.intent_classifier_fallback": (
        "短句状态追问（分类器兜底）",
        "Short status follow-up (classifier fallback path).",
    ),
    "orchestrator.continue_handoff.missing_action_type": (
        "continue 承接缺少 action_type",
        "Continue handoff is missing action_type.",
    ),
    "orchestrator.continue.completed_summary_carryover": (
        "（由上一步工作流建议承接）",
        "carried over from the previous workflow suggestion",
    ),
    "orchestrator.continue.pending_preview_workflow": (
        "已按你上一步认可的「下一步建议」生成待确认草稿：请在界面核对后确认，系统才会真正执行。",
        "Created a pending-confirmation draft from the next-step suggestion you accepted; review and confirm it in the interface before the system executes.",
    ),
    "orchestrator.context_note.single_prediction_form": (
        "单样本预测需在工作台表单中补全字段；系统不会自动填入真实患者取值。",
        "Single-sample prediction fields must be completed in the workspace form; "
        "the system will not automatically fill real patient values.",
    ),
    "orchestrator.pending_confirm.bullet_a": (
        "高风险确认与阶段放行需要在工作台界面中的待确认卡片上完成。",
        "High-risk confirmation and stage release must be completed on the pending-confirmation card in the workbench interface.",
    ),
    "orchestrator.pending_confirm.bullet_b": (
        "请在卡片上查看摘要并点击「确认」或「取消」；对话内不会代为执行该确认。",
        "Review the summary on the card and click Confirm or Cancel; the chat will not perform that confirmation for you.",
    ),
    "orchestrator.pending_confirm.summary": (
        "请在工作台当前待确认卡片或训练等待节点上完成操作。",
        "Complete the action on the current pending-confirmation card or training wait node in the workbench.",
    ),
    "orchestrator.fallback_template.bullet_a": ("未检测到有效输入。", "No valid input was detected."),
    "orchestrator.fallback_template.bullet_b": ("请在工作台输入具体问题或指令。", "Enter a specific question or instruction in the workbench."),
    "orchestrator.fallback_template.summary": ("请输入内容后再试。", "Enter a message and try again."),
    "orchestrator.pending.standard_completed_none": ("（无）", "none"),
    "orchestrator.pending.standard_preview": (
        "已生成待确认卡片：请在界面核对参数，确认后系统才会执行对应动作。",
        "Pending confirmation card created: review the parameters in the interface; the system will execute only after confirmation.",
    ),
    "orchestrator.cannot_enter_pending": (
        "已识别为「{action}」，但当前配置无法进入待确认流程；仍缺：{missing}。",
        "Recognized as {action}, but the current configuration cannot enter the pending-confirmation flow; still missing: {missing}.",
    ),
    "orchestrator.tool_failure_default": ("执行失败", "Operation failed"),
    "orchestrator.confirm.pending_not_found": ("pending_action_id 不存在", "pending_action_id was not found."),
    "orchestrator.confirm.pending_expired": ("pending_action 已过期", "This pending action has expired."),
    "orchestrator.confirm.pending_superseded": (
        "pending_action 已被更新动作替代",
        "This pending action was superseded by a newer action.",
    ),
    "orchestrator.confirm.already_executed": (
        "该 pending action 已执行，返回已创建任务。",
        "This pending action was already executed; returning the existing job.",
    ),
    "orchestrator.confirm.invalid_status": (
        "pending action 状态为 {status}，无法确认",
        'Pending action status is “{status}”; it cannot be confirmed.',
    ),
    "orchestrator.confirm.canceled": ("操作已取消。", "Action canceled."),
    "orchestrator.confirm.confirm_failed": ("pending_action 确认失败", "Could not confirm the pending action."),
    "orchestrator.confirm.payload_validation_failed": (
        "payload 校验失败：{detail}",
        "Payload validation failed: {detail}",
    ),
    "orchestrator.confirm.job_id_missing": ("未返回 job_id，任务创建失败", "job_id was not returned; job creation failed."),
    "orchestrator.confirm.success_generic": ("已确认，任务已创建。", "Confirmed; the task was created."),
    "orchestrator.confirm.success_training": (
        "训练配置已提交。特征筛选将在后台进行，请在任务面板查看进度。",
        "Training configuration submitted. Feature screening will continue in the background—check the Tasks panel for progress.",
    ),
    "orchestrator.confirm.success_draft_prediction": (
        "预测配置已提交。可在任务列表或预测历史中查看执行情况。",
        "Prediction configuration submitted. You can monitor execution in the task list or prediction history.",
    ),
    "orchestrator.confirm.success_batch_prediction": (
        "预测配置已提交。可在任务列表或预测历史中查看执行情况。",
        "Prediction job submitted. You can monitor execution in the task list or prediction history.",
    ),
    "orchestrator.confirm.success_recommendation": (
        "推荐任务已提交。可在任务列表中查看执行情况。",
        "Recommendation job submitted. You can monitor execution in the task list.",
    ),
    "orchestrator.confirm.success_report": (
        "报告任务已提交。可在任务列表中查看执行情况。",
        "Report job submitted. You can monitor execution in the task list.",
    ),
    "orchestrator.confirm.unsupported_action_type": (
        "不支持的 action_type：{action}",
        "Unsupported action_type: {action}.",
    ),
}
