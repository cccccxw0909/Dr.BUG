"""Localized strings for backend.agent.reply_semantics (semantic payload builders)."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "reply_semantics.placeholder.none": ("（无）", "none"),
    "reply_semantics.placeholder.see_contract": ("（见契约）", "see contract"),
    # --- tool_result ---
    "reply_semantics.tool_result.mixed_action_note": (
        "本回合仅完成信息查询，未自动创建或修改训练、预测任务。",
        "This turn only completed an information query; no training or prediction task was created or modified automatically.",
    ),
    "reply_semantics.tool_result.label_queried": ("已查询：", "Queried: "),
    "reply_semantics.tool_result.label_query_types": (
        "系统已执行的查询类型：",
        "Query types executed by the system: ",
    ),
    "reply_semantics.tool_result.boundary_draft_note": (
        "另附：规则层有一条较长的事实答复草稿，仅供核对边界，请优先依据下方结构化事实组织语言。",
        "A longer rule-layer factual draft is available only for boundary checks; prioritize the structured facts below.",
    ),
    "reply_semantics.tool_result.summary": (
        "用户在做只读查询；下面是系统返回的事实摘要投影（已脱敏）。",
        "The user is making a read-only query; below is the system-returned factual summary projection (sanitized).",
    ),
    "reply_semantics.tool_result.obs_focus_relevant": (
        "请抓住与用户问题最相关的一条信息先说清楚，不必逐条复述工具里的所有字段。",
        "Start with the point most relevant to the user's question; do not repeat every tool field.",
    ),
    "reply_semantics.tool_result.next_train_predict_confirm": (
        "如需训练或预测，请在卡片中确认后再执行。",
        "If training or prediction is needed, confirm it in the card before execution.",
    ),
    "reply_semantics.tool_result.next_task_panel": (
        "可在任务面板核对进度与结果入口。",
        "Use the task panel to check progress and result entry points.",
    ),
    "reply_semantics.tool_result.block_no_claim_execution": (
        "不得声称已代为执行训练、预测或推荐。",
        "Do not claim that training, prediction, or recommendation was executed on the user's behalf.",
    ),
    "reply_semantics.tool_result.block_no_fabricate_ids": (
        "不得编造任务编号或状态。",
        "Do not fabricate job ids or statuses.",
    ),
    # --- draft_created ---
    "reply_semantics.draft_created.stage_ready_confirm": (
        "卡片字段已齐，等待用户在界面确认。",
        "The card fields are complete and waiting for confirmation in the interface.",
    ),
    "reply_semantics.draft_created.stage_need_fields": (
        "尚需在卡片中补齐信息后才能确认。",
        "More card fields must be completed before confirmation.",
    ),
    "reply_semantics.draft_created.parsed_summary_line": (
        "解析到的有效信息摘要：{summary}",
        "Parsed valid information summary: {summary}",
    ),
    "reply_semantics.draft_created.missing_fields_line": (
        "仍缺项（仅列名）：{fields}",
        "Missing fields (names only): {fields}",
    ),
    "reply_semantics.draft_created.train_not_started": (
        "尚未开始训练；对话内不会自动执行训练任务。",
        "Training has not started; the chat will not execute a training task automatically.",
    ),
    "reply_semantics.draft_created.train_wait_required_fields": (
        "未确认前不会开始训练；须在卡片补全必填项后再确认。",
        "Training will not start before confirmation; complete required card fields first.",
    ),
    "reply_semantics.draft_created.train_after_confirm": (
        "确认后才会开始训练。",
        "Training starts only after confirmation.",
    ),
    "reply_semantics.draft_created.pred_no_inference": (
        "尚未执行推理或写入预测历史。",
        "Inference has not run and prediction history has not been written.",
    ),
    "reply_semantics.draft_created.pred_wait_no_autofill": (
        "系统不会自动填入真实患者数值；未确认前不会发起推理或写入预测历史。",
        "The system will not fill real patient values automatically; no inference or prediction history is produced before confirmation.",
    ),
    "reply_semantics.draft_created.pred_after_confirm_task": (
        "确认后才会创建预测任务并执行推理。",
        "A prediction task and inference will be created only after confirmation.",
    ),
    "reply_semantics.draft_created.other_stage_ready_confirm": (
        "可在卡片中确认。",
        "Ready for card confirmation.",
    ),
    "reply_semantics.draft_created.other_stage_complete_first": (
        "请先补齐参数后在卡片中确认。",
        "Complete the parameters before confirming in the card.",
    ),
    "reply_semantics.draft_created.interface_stage_hint": (
        "界面阶段提示：{hint}",
        "Interface stage hint: {hint}",
    ),
    "reply_semantics.draft_created.user_intent": (
        "配置草稿已生成，等待确认后才会执行。",
        "A configuration draft has been generated and will run only after confirmation.",
    ),
    "reply_semantics.draft_created.summary_prepared": (
        "已准备「{title}」。{stage}",
        "Prepared {title}. {stage}",
    ),
    "reply_semantics.draft_created.obs_draft_pending": (
        "当前仅为草稿与待确认状态，后台尚未开始执行对应高风险动作。",
        "This is only a draft/pending-confirmation state; the backend has not started the corresponding high-risk action.",
    ),
    "reply_semantics.draft_created.next_review_params": (
        "在卡片中核对参数",
        "Review parameters in the card",
    ),
    "reply_semantics.draft_created.next_complete_then_confirm": (
        "补齐缺项后点击确认",
        "Complete missing fields, then confirm",
    ),
    "reply_semantics.draft_created.next_review_confirm_execute": (
        "在卡片中核对后确认执行",
        "Review the card, then confirm execution",
    ),
    "reply_semantics.draft_created.block_no_claim_started": (
        "不得声称训练/预测/推荐已在对话中开始或完成。",
        "Do not claim that training, prediction, or recommendation has started or completed in the chat.",
    ),
    "reply_semantics.draft_created.safety_execution_after_confirm": (
        "执行权仅在用户确认之后由系统主链触发。",
        "Execution is triggered by the system path only after user confirmation.",
    ),
    # --- missing_info ---
    "reply_semantics.missing_info.prediction_entry_ready": (
        "预测入口已就绪：已解析字段框架，系统不会替你填入真实患者数值。",
        "Prediction entry is ready: the field framework was parsed, and the system will not fill real patient values for you.",
    ),
    "reply_semantics.missing_info.still_required_items": (
        "尚需补齐：{items}。",
        "Still required: {items}.",
    ),
    "reply_semantics.missing_info.prediction_complete_form_before_confirm": (
        "请在统一预测卡片中按表单补全后再确认；未确认前不会发起推理或写入预测历史。",
        "Complete the unified prediction card form before confirming; no inference or prediction history will be written before confirmation.",
    ),
    "reply_semantics.missing_info.key_missing_fields": (
        "缺项（仅名称）：{items}",
        "Missing fields (names only): {items}",
    ),
    "reply_semantics.missing_info.not_executable_yet": (
        "尚未进入可执行状态，需先在界面补齐后再确认。",
        "This is not executable yet; complete the fields in the interface before confirming.",
    ),
    "reply_semantics.missing_info.pred_no_history_before_confirm": (
        "未确认前不会发起推理或写入预测历史。",
        "No inference or prediction history will be written before confirmation.",
    ),
    "reply_semantics.missing_info.user_intent": (
        "参数不齐，无法进入待确认或执行。",
        "Parameters are incomplete, so this cannot enter confirmation or execution.",
    ),
    "reply_semantics.missing_info.summary_missing_items": (
        "「{title}」仍缺关键项，需先在界面补齐。",
        "{title} is still missing required items; complete them in the interface first.",
    ),
    "reply_semantics.missing_info.next_complete_fields": (
        "在对应卡片或表单中补齐字段",
        "Complete fields in the corresponding card or form",
    ),
    "reply_semantics.missing_info.next_start_again": (
        "补齐后再次发起",
        "Start again after completing the fields",
    ),
    "reply_semantics.missing_info.block_no_fake_job": (
        "不得模拟已提交任务或给出 job 结果。",
        "Do not simulate a submitted job or provide job results.",
    ),
    # --- cannot_execute ---
    "reply_semantics.cannot_execute.user_intent": (
        "动作被识别但无法进入待确认流程。",
        "The action was recognized but cannot enter the pending-confirmation flow.",
    ),
    "reply_semantics.cannot_execute.key_relevant_capability": (
        "涉及能力：{title}",
        "Relevant capability: {title}",
    ),
    "reply_semantics.cannot_execute.next_check_page_mode": (
        "检查页面是否处于正确模式",
        "Check whether the page is in the correct mode",
    ),
    "reply_semantics.cannot_execute.next_complete_contract_fields": (
        "按提示补齐契约要求的字段",
        "Complete the contract-required fields as prompted",
    ),
    "reply_semantics.cannot_execute.block_no_bypass_pending": (
        "不得绕过待确认主链直接宣称已执行。",
        "Do not bypass the pending-confirmation path and claim execution.",
    ),
    "reply_semantics.cannot_execute.append_complete_info_tail": (
        "请先在界面补齐必要信息。",
        "Complete the required information in the interface first.",
    ),
    # --- status ---
    "reply_semantics.status.default_summary": (
        "用户询问进度、完成情况或当前任务状态。",
        "The user is asking about progress, completion, or current task status.",
    ),
    "reply_semantics.status.obs_public_fields_only": (
        "以下为系统根据任务仓库整理的公开字段摘要，不含患者明细表。",
        "The following is a public-field summary from the task repository and does not include patient-level tables.",
    ),
    "reply_semantics.status.obs_explain_stuck_and_next": (
        "请先用一句话说明「为何停在此处」与「下一步用户要做什么」，避免只复述阶段名或与卡片标题重复。",
        "First explain why it is at this point and what the user should do next; avoid only repeating the stage name or card title.",
    ),
    "reply_semantics.status.next_open_task_details": (
        "需要细节可在任务详情查看",
        "Open task details for more information",
    ),
    "reply_semantics.status.next_prediction_explanation_entry": (
        "若要结果解释请使用预测解释入口",
        "Use the prediction explanation entry point for result interpretation",
    ),
    "reply_semantics.status.block_no_fabricate_or_rows": (
        "不得编造任务状态或输出患者级逐行数据。",
        "Do not fabricate task status or output patient-level row data.",
    ),
    # --- terminal_result ---
    "reply_semantics.terminal_result.obs_bind_selected_facts": (
        "答复须严格绑定系统已选定的任务事实。",
        "The reply must stay strictly bound to the selected task facts.",
    ),
    "reply_semantics.terminal_result.obs_train_metric_interpretation": (
        "若涉及训练指标解读：先给审慎的总体判断，再分层解释各指标含义（避免单独把某一标量当唯一证据），最后只列建议核对项；禁止仅凭 AUROC<0.5 或 Accuracy<0.5 就下「系统性错误」「远低于随机猜测」或「绝对不可用于辅助决策」等强结论，除非局面说明中已给出充分支撑。",
        "For training metric interpretation: give a cautious overall assessment, explain metrics in layers, and list verification items only. Do not make strong conclusions from a single scalar unless the situation summary fully supports them.",
    ),
    "reply_semantics.terminal_result.object_kind.training": ("训练", "training"),
    "reply_semantics.terminal_result.object_kind.prediction": ("预测", "prediction"),
    "reply_semantics.terminal_result.user_intent": (
        "用户追问已完成/失败任务的结果或原因。",
        "The user is asking about the result or reason for a completed/failed task.",
    ),
    "reply_semantics.terminal_result.summary_for_task": (
        "针对{label}任务的终端态答复。",
        "Terminal-state reply for the {label} task.",
    ),
    "reply_semantics.terminal_result.key_intent_label": (
        "问法意图归类：{intent}",
        "Intent classification: {intent}",
    ),
    "reply_semantics.terminal_result.key_stay_on_facts": (
        "须严格绑定系统已选定任务上的事实，不得外推未给出的指标或解释细节。",
        "Stay bound to facts on the selected task; do not extrapolate missing metrics or explanation details.",
    ),
    "reply_semantics.terminal_result.next_review_metrics": (
        "到任务详情核对指标与报告",
        "Review metrics and reports in task details",
    ),
    "reply_semantics.terminal_result.next_retry_after_fix": (
        "失败时按提示修正输入后重试",
        "If failed, correct the input as prompted and retry",
    ),
    "reply_semantics.terminal_result.block_no_fake_current": (
        "不得把历史摘要冒充为当前工作台未执行任务的结果。",
        "Do not present a historical summary as the result of a task that has not run in the current workspace.",
    ),
    # --- sticky_no_prediction ---
    "reply_semantics.sticky_no_prediction.user_intent": (
        "用户在预测页追问结果，但工作台尚无一次可绑定的预测执行。",
        "The user asks for a result on the prediction page, but the workspace has no bindable prediction run.",
    ),
    "reply_semantics.sticky_no_prediction.summary": (
        "当前没有可读的单次预测输出。",
        "There is no readable single-prediction output yet.",
    ),
    "reply_semantics.sticky_no_prediction.key_no_bound_record": (
        "尚未形成与当前工作台绑定的预测结果记录。",
        "No prediction result record is bound to the current workspace yet.",
    ),
    "reply_semantics.sticky_no_prediction.obs_complete_flow_first": (
        "需要用户先在工作台完成预测流程。",
        "The user must complete the prediction flow in the workspace first.",
    ),
    "reply_semantics.sticky_no_prediction.next_configure_prediction": (
        "先配置并确认执行预测",
        "Configure and confirm prediction first",
    ),
    "reply_semantics.sticky_no_prediction.next_then_ask_label_prob": (
        "完成后再问标签、概率或风险",
        "After completion, ask about label, probability, or risk",
    ),
    "reply_semantics.sticky_no_prediction.block_no_guess_from_model": (
        "不得根据模型常识臆测该样本风险或概率。",
        "Do not infer this sample's risk or probability from model knowledge alone.",
    ),
    # --- disclaimed_latest_prediction ---
    "reply_semantics.disclaimed_prediction.user_intent": (
        "用户追问最近一次预测，但工作台上下文与历史摘要可能不一致。",
        "The user asks for the latest prediction, but workspace context and archived history may differ.",
    ),
    "reply_semantics.disclaimed_prediction.summary": (
        "需区分「当前工作台这一次」与「历史归档摘要」。",
        "Distinguish the current workspace run from the archived historical summary.",
    ),
    "reply_semantics.disclaimed_prediction.key_historical_index": (
        "工具返回的可能是历史索引摘要，不等价于当前未执行的操作结果。",
        "The tool may return a historical index summary, which is not equivalent to a result for an unexecuted current operation.",
    ),
    "reply_semantics.disclaimed_prediction.next_run_prediction_first": (
        "若要看当前模型输出请先执行预测",
        "Run prediction first to see the current model output",
    ),
    "reply_semantics.disclaimed_prediction.next_check_history": (
        "历史记录请在预测历史中核对",
        "Verify historical records in prediction history",
    ),
    "reply_semantics.disclaimed_prediction.block_no_equate_history": (
        "不得把历史记录描述成当前页面刚跑完的任务输出。",
        "Do not describe a historical record as output just produced by the current page.",
    ),
    # --- status bullets (Chinese locale branch) ---
    "reply_semantics.status_bullet.job_type.training": ("训练", "training"),
    "reply_semantics.status_bullet.job_type.prediction": ("预测", "prediction"),
    "reply_semantics.status_bullet.job_type.unknown": ("未知", "unknown"),
    "reply_semantics.status_bullet.job_type_line": ("任务类型：{value}", "Job type: {value}"),
    "reply_semantics.status_bullet.status_line": ("状态：{value}", "Status: {value}"),
    "reply_semantics.status_bullet.progress_line": ("进度数值：{value}", "Progress value: {value}"),
    "reply_semantics.status_bullet.stage_line": ("当前阶段代码摘要：{snippet}", "Current stage (code snippet): {snippet}"),
    "reply_semantics.status_bullet.internal_job_hint": (
        "内部任务引用已存在（不要在对话里逐字复述长 id，可用「当前任务」指代）。",
        "An internal job id exists; do not read it aloud verbatim—refer to it as the current task.",
    ),
    "reply_semantics.status_bullet.matched_scene": ("命中场景：{scene}", "Matched scene: {scene}"),
    # --- workflow_guidance ---
    "reply_semantics.workflow_guidance.key_domain": (
        "工作流域：{domain}",
        "Workflow domain: {domain}",
    ),
    "reply_semantics.workflow_guidance.key_stage": (
        "流程阶段：{stage}",
        "Workflow stage: {stage}",
    ),
    "reply_semantics.workflow_guidance.key_goal": (
        "目标类型：{goal}",
        "Workflow goal: {goal}",
    ),
    "reply_semantics.workflow_guidance.key_rec_state": (
        "用药推荐工作流状态 recommendation_state={state}",
        "Recommendation workflow state: recommendation_state={state}",
    ),
    "reply_semantics.workflow_guidance.key_prediction_bind_signal": (
        "是否已绑定可用于推荐的预测结果摘要信号：{flag}",
        "Prediction result summary signal bound for recommendation: {flag}",
    ),
    "reply_semantics.workflow_guidance.followup_actions_prefix": (
        "后续可组织动作（仅指导，非执行）：",
        "Follow-up actions to organize (guidance only, not execution): ",
    ),
    "reply_semantics.workflow_guidance.blocking_points_prefix": (
        "阻塞点（代码:说明）：",
        "Blocking points (code: guidance): ",
    ),
    "reply_semantics.workflow_guidance.candidate_next_steps_prefix": (
        "候选下一步：",
        "Candidate next steps: ",
    ),
    "reply_semantics.workflow_guidance.key_system_recommended_action": (
        "系统推荐动作 id={rid} kind={kind}",
        "System recommended action id={rid} kind={kind}",
    ),
    "reply_semantics.workflow_guidance.obs_three_part_reply": (
        "回复须分三段组织：① 当前处于什么局面；② 最建议的下一步；③ 为什么这样建议。",
        "Organize the reply in three parts: current situation, recommended next step, and why.",
    ),
    "reply_semantics.workflow_guidance.obs_no_claim_execution_or_tables": (
        "不得声称已在对话中执行训练、预测或推荐；不得编造 job 细节或患者级表格。",
        "Do not claim training, prediction, or recommendation was executed in chat; do not fabricate job details or patient-level tables.",
    ),
    "reply_semantics.workflow_guidance.obs_draft_requires_confirm": (
        "若候选里含 draft 类动作，须明确「可先生成草稿，仍需在界面确认后才会真正执行」。",
        "If candidates include draft actions, state that a draft can be generated and still requires interface confirmation before execution.",
    ),
    "reply_semantics.workflow_guidance.obs_recommendation_organizer_tone": (
        "用药推荐：语气像「工作流组织助手」。若 recommendation_state 为 completed，应引导先看排序与 original/top1 比较，明确不建议再次起草推荐；若为 running/queued，强调等待与看任务状态；若为 precondition_missing，说明还差什么、为何不能推荐；仅 ready_to_run 时可积极建议生成待确认推荐草稿。",
        "Recommendation guidance: sound like a workflow organizer. If completed, guide the user to review ranking and original/top1 comparison; if running/queued, emphasize waiting and task status; if precondition_missing, explain what is missing and why recommendation cannot run; only ready_to_run should suggest generating a pending recommendation draft.",
    ),
    "reply_semantics.workflow_guidance.primary_next_fallback": (
        "在工作台核对当前卡片与任务状态",
        "Review the current card and task status in the workspace",
    ),
    "reply_semantics.workflow_guidance.user_intent": (
        "用户询问工作流中下一步该怎么做或为何停在此处。",
        "The user asks what to do next in the workflow or why it is blocked.",
    ),
    "reply_semantics.workflow_guidance.block_no_bypass_pending": (
        "不得绕过 pending 确认直接宣称已创建或完成任务。",
        "Do not bypass pending confirmation and claim a task was created or completed.",
    ),
    "reply_semantics.workflow_guidance.block_no_patient_feature_table": (
        "不得输出患者逐行特征表。",
        "Do not output patient-level feature tables.",
    ),
    "reply_semantics.workflow_guidance.safety_execution_after_ui_confirm": (
        "执行权仅在用户于界面确认之后由系统主链触发。",
        "Execution is triggered by the system path only after the user confirms in the interface.",
    ),
}
