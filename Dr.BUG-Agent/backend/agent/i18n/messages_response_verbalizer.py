"""Locale pairs for backend.agent.response_verbalizer deterministic strict templates."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    # --- training_draft_created ---
    "response_verbalizer.training_draft.placeholder_none": ("（无）", "(none)"),
    "response_verbalizer.training_draft.headline": (
        "训练配置草稿已准备。",
        "Training configuration draft prepared.",
    ),
    "response_verbalizer.training_draft.card_ready": (
        "卡片上所需字段已齐全；请在工作台核对并在就绪后确认。",
        "All required fields are present on the card; review them and confirm in the workbench when ready.",
    ),
    "response_verbalizer.training_draft.card_incomplete": (
        "草稿卡片上仍有部分必填字段缺失；请先补全后再进行确认。",
        "Some required fields are still missing on the draft card; complete them before confirmation is available.",
    ),
    "response_verbalizer.training_draft.parsed_summary": (
        "已解析输入摘要：{summary}",
        "Parsed inputs summary: {summary}",
    ),
    "response_verbalizer.training_draft.missing_fields": (
        "仍缺字段（仅名称）：{missing}",
        "Missing fields (names only): {missing}",
    ),
    "response_verbalizer.training_draft.not_started": (
        "训练尚未开始；本对话不会自动执行训练任务。",
        "Training has not started. This chat will not run training automatically.",
    ),
    "response_verbalizer.training_draft.no_job_until_filled": (
        "在补全必填字段并由您确认之前，不会开始训练任务。",
        "No training job will run until required fields are filled and you confirm.",
    ),
    "response_verbalizer.training_draft.no_job_until_ui_confirm": (
        "在您于界面明确确认之前，不会开始训练任务。",
        "No training job runs until you explicitly confirm in the UI.",
    ),
    "response_verbalizer.training_draft.draft_only_backend": (
        "当前仅为草稿；该训练相关动作的后台执行尚未开始。",
        "This is a draft only; backend execution for this training action has not begun.",
    ),
    "response_verbalizer.training_draft.after_intro_workflow": (
        "已根据您上一步认可的工作流建议生成草稿；请在界面核对并确认，确认后才会开始执行。",
        "Draft created from your accepted workflow suggestion. Review it in the UI and confirm; "
        "execution starts only after confirmation.",
    ),
    "response_verbalizer.training_draft.after_intro_standard": (
        "待确认卡片已就绪；请在界面核对参数，确认后才会开始执行。",
        "A pending confirmation card is ready. Review parameters in the UI; execution starts only after you confirm.",
    ),
    "response_verbalizer.training_draft.execution_after_confirm": (
        "仅在您确认之后，才会由系统主工作流触发执行。",
        "Execution is triggered only by the main workflow after your confirmation.",
    ),
    "response_verbalizer.training_draft.do_not_claim_started": (
        "请勿将训练描述为已基于本消息启动、正在运行或已完成。",
        "Do not describe training as already started, running, or completed based on this message.",
    ),
    "response_verbalizer.training_draft.do_not_invent_metrics": (
        "请勿编造训练指标数值、模型注册/发布状态或写入模型库的结论。",
        "Do not invent training metrics, model registration or release status, or registry conclusions.",
    ),
    "response_verbalizer.training_draft.next_review_card": (
        "下一步：在卡片中核对并确认以开始训练。",
        "Next: review the card and confirm to start training.",
    ),
    "response_verbalizer.training_draft.next_complete_fields": (
        "下一步：先在卡片上补全缺失字段，然后再确认。",
        "Next: complete the missing fields on the card, then confirm.",
    ),
    "response_verbalizer.training_draft.stage_can_confirm": (
        "卡片字段已齐，等待用户在界面确认。",
        "All required fields are complete on the card; waiting for confirmation in the UI.",
    ),
    "response_verbalizer.training_draft.stage_need_fill": (
        "尚需在卡片中补齐信息后才能确认。",
        "Some information still needs to be completed on the card before confirmation.",
    ),
    "response_verbalizer.training_draft.opening": (
        "已准备「训练配置」。{stage}",
        "Prepared training configuration draft. {stage}",
    ),
    "response_verbalizer.training_draft.line_parsed": (
        "· 解析到的有效信息摘要：{summary}",
        "· Parsed inputs summary: {summary}",
    ),
    "response_verbalizer.training_draft.line_missing": (
        "· 仍缺项（仅列名）：{missing}",
        "· Missing fields (names only): {missing}",
    ),
    "response_verbalizer.training_draft.line_not_started": (
        "· 尚未开始训练；对话内不会自动执行训练任务。",
        "· Training has not started; this chat will not run training automatically.",
    ),
    "response_verbalizer.training_draft.line_wait_fill": (
        "· 未确认前不会开始训练；须在卡片补全必填项后再确认。",
        "· Training will not start before confirmation; complete required fields on the card first.",
    ),
    "response_verbalizer.training_draft.line_after_confirm": (
        "· 确认后才会开始训练。",
        "· Training starts only after confirmation.",
    ),
    "response_verbalizer.training_draft.line_draft_state": (
        "· 当前仅为草稿与待确认状态，后台尚未开始执行对应高风险动作。",
        "· This is only a draft pending confirmation; the backend has not started the corresponding high-risk action.",
    ),
    "response_verbalizer.training_draft.line_round_is_draft": (
        "本回合仅为训练配置草稿：并非训练已启动、运行中或已完成。",
        "This turn is only a training configuration draft: training has not started, is not running, and is not completed.",
    ),
    "response_verbalizer.training_draft.line_pending_confirm": (
        "训练任务尚未启动；仍需用户在工作台界面明确确认后才会执行。",
        "The training job has not started; it will run only after explicit confirmation in the workbench UI.",
    ),
    "response_verbalizer.training_draft.line_pending_incomplete": (
        "训练任务尚未启动；草稿卡片可能仍缺必填项，补全后才可进入确认。",
        "The training job has not started; the draft card may still be missing required fields—complete them before confirming.",
    ),
    "response_verbalizer.training_draft.line_execution_rights": (
        "执行权仅在用户确认之后由系统主链触发。",
        "Execution is triggered by the main system path only after user confirmation.",
    ),
    "response_verbalizer.training_draft.line_no_false_claims": (
        "不得声称训练/预测/推荐已在对话中开始或完成。",
        "Do not claim that training, prediction, or recommendation has started or completed in the chat.",
    ),
    "response_verbalizer.training_draft.line_no_false_state": (
        "请勿将本轮表述为训练任务已在后台「启动」或「正在运行」，也勿表述为训练「已完成」或「已结束」。",
        "Do not describe this turn as training having been started or running in the backend, or as training having finished or ended.",
    ),
    "response_verbalizer.training_draft.line_no_invent_metrics": (
        "请勿编造训练指标数值、模型注册/发布状态或写入模型库结论。",
        "Do not invent training metric values, model registration or release status, or registry conclusions.",
    ),
    "response_verbalizer.training_draft.fallback_when_empty": (
        "当前信息有限，请在工作台任务面板查看待确认卡片或稍后重试。",
        "Current information is limited; check the task panel for the pending-confirmation card or try again later.",
    ),
    # --- training_failed ---
    "response_verbalizer.training_failed.default_bucket": ("训练流程中的某一环节", "a step in the training workflow"),
    "response_verbalizer.training_failed.default_hint": (
        "执行过程中出现问题",
        "Something went wrong during execution.",
    ),
    "response_verbalizer.training_failed.core_fail_check_first": (
        "从排查角度先关注：{bucket}。{hint}。",
        "For troubleshooting, start with: {bucket}. {hint}",
    ),
    "response_verbalizer.training_failed.core_default": (
        "训练失败，问题大致出在{bucket}。{hint}。",
        "Training failed; the issue likely involves {bucket}. {hint}",
    ),
    "response_verbalizer.training_failed.next_step_with_na": ("下一步：{na}", " Next step: {na}"),
    # --- prediction_failed ---
    "response_verbalizer.prediction_failed.default_bucket": ("预测流程中的某一环节", "a step in the prediction workflow"),
    "response_verbalizer.prediction_failed.default_hint": (
        "输入或环境可能有问题",
        "The input or environment may be invalid.",
    ),
    "response_verbalizer.prediction_failed.core_fail_check_first": (
        "从排查角度，优先核对「{bucket}」一侧：{hint}。",
        "For troubleshooting, prioritize checking: {bucket}. {hint}",
    ),
    "response_verbalizer.prediction_failed.core_default": (
        "预测失败，看起来更像是{bucket}方面的问题（{hint}）。",
        "Prediction failed; this most likely relates to {bucket}. {hint}",
    ),
    "response_verbalizer.prediction_failed.next_step_with_na": ("下一步：{na}", " Next step: {na}"),
    # --- prediction_result ---
    "response_verbalizer.prediction_result.headline": ("单样本预测已完成。", "Single-patient prediction completed."),
    "response_verbalizer.prediction_result.context": (
        "上下文：{details}。",
        "Context: {details}.",
    ),
    "response_verbalizer.prediction_result.line_status": (
        "预测状态：{status}。",
        "Prediction status: {status}.",
    ),
    "response_verbalizer.prediction_result.line_label": (
        "预测标签：{label}。",
        "Predicted label: {label}.",
    ),
    "response_verbalizer.prediction_result.line_prob": (
        "预测概率：{prob}。",
        "Predicted probability: {prob}.",
    ),
    "response_verbalizer.prediction_result.task_line": ("任务：{name}", "Task: {name}"),
    "response_verbalizer.prediction_result.model_line": ("模型：{name}", "Model: {name}"),
    "response_verbalizer.prediction_result.explain_shap_yes_a": (
        "解释：工作台可能提供 SHAP 或特征级解释入口，可按需查看。",
        "Explanation: SHAP or feature-level explanation may be available in the workbench for review.",
    ),
    "response_verbalizer.prediction_result.explain_shap_yes_b": (
        "下一步：可在工作台结果卡片中查看预测详情与解释入口（如有）。",
        "Next step: review the prediction details and explanation entry in the workbench, if needed.",
    ),
    "response_verbalizer.prediction_result.explain_shap_no_a": (
        "解释：当前摘要未标记有可用的 SHAP 或特征级解释入口。",
        "Explanation: no SHAP or feature-level explanation is marked as available in this summary.",
    ),
    "response_verbalizer.prediction_result.explain_shap_no_b": (
        "下一步：可在工作台结果卡片中查看预测详情；如需可发起新的单样本预测。",
        "Next step: review the prediction details in the workbench "
        "or start another single-patient prediction if needed.",
    ),
    "response_verbalizer.prediction_result.clinical_boundary": (
        "临床边界：以上为模型估计结果，不能替代个体化临床判断。",
        "Clinical boundary: this is a model estimate and does not replace individualized clinical judgment.",
    ),
    # --- batch_prediction_result ---
    "response_verbalizer.batch_prediction.headline_default": ("批量预测已完成", "Batch prediction completed"),
    "response_verbalizer.batch_prediction.aggregate": (
        "· 聚合执行结果：全表共 {tr} 行，其中成功 {sr} 行，失败 {fr} 行。",
        "· Aggregate run: {tr} total rows; succeeded {sr}; failed {fr}.",
    ),
    "response_verbalizer.batch_prediction.download_with_suffix": (
        "· 可提供整表结果下载（文件名末段：{ofn}）。",
        "· A full-table download is available (file suffix: {ofn}).",
    ),
    "response_verbalizer.batch_prediction.download_path_only": (
        "· 已记录结果文件下载路径，可在工作台使用该路径获取整表输出。",
        "· A download path was recorded; use it from the workbench to fetch the full table.",
    ),
    "response_verbalizer.batch_prediction.no_download_path": (
        "· 当前摘要不包含下载路径；请勿理解为已可直接下载整表结果文件。",
        "· This summary does not include a download path; do not assume a full-table file is downloadable yet.",
    ),
    "response_verbalizer.batch_prediction.summary_point_line": ("· {t}", "· {t}"),
    "response_verbalizer.batch_prediction.next_action_fallback": (
        "请在工作台下载并核对结果文件；若需对单行进一步说明，请使用单样本预测入口。",
        "Download and review the result file in the workbench; use the single-sample prediction entry point if one row needs follow-up.",
    ),
    "response_verbalizer.batch_prediction.empty_fallback": (
        "批量预测任务已完成；更细信息请在工作台任务详情中查看。",
        "Batch prediction finished; see the task panel for details.",
    ),
    # --- recommendation_result ---
    "response_verbalizer.recommendation.intro": (
        "推荐任务已完成。以下为模型对方案的评分与排序结果，仅供决策支持参考，不构成处方或治疗指令。",
        "Recommendation job completed. This is a model-based regimen comparison, not a prescription.",
    ),
    "response_verbalizer.recommendation.section_top_regimen": ("排序第一的方案：", "Top-ranked regimen:"),
    "response_verbalizer.recommendation.top_line_prob_suffix": (
        " — 模型给出的生存概率约 {rtp}",
        " — predicted survival probability {rtp}",
    ),
    "response_verbalizer.recommendation.observed_prob": ("观测方案对应的模型概率：{obs}", "Observed-regimen probability: {obs}"),
    "response_verbalizer.recommendation.observed_prob_missing": (
        "本摘要未提供观测方案对应的模型概率。",
        "Observed-regimen probability: not reported in this summary.",
    ),
    "response_verbalizer.recommendation.top_prob_line": ("排名第一方案的模型概率：{rtp}", "Top-regimen probability: {rtp}"),
    "response_verbalizer.recommendation.delta_pp": (
        "差值：{sign}{mag} 个百分点（模型概率差，非疗效承诺）",
        "Difference: {sign}{mag} percentage points",
    ),
    "response_verbalizer.recommendation.section_other_candidates": ("其余候选（按任务排序）：", "Other ranked candidates:"),
    "response_verbalizer.recommendation.candidate_line_with_prob": ("{rank}. {name} — {prob}", "{rank}. {name} — {prob}"),
    "response_verbalizer.recommendation.candidate_line_no_prob": ("{rank}. {name}", "{rank}. {name}"),
    "response_verbalizer.recommendation.footer": (
        "完整排序与工件请在任务详情中查看。",
        "See task details for the full ranked list and artifacts.",
    ),
    "response_verbalizer.common.next_step": ("下一步：{action}", "Next step: {action}"),
    "response_verbalizer.recommendation.empty_fallback": (
        "当前可展示信息不足，请在工作台推荐任务详情中查看。",
        "Recommendation summary is unavailable from the current facts; open task details.",
    ),
    # --- render_strict_template (generic) ---
    "response_verbalizer.strict_template.bullet": ("· {t}", "- {t}"),
    "response_verbalizer.strict_template.empty_fallback": (
        "当前信息有限，请在工作台任务面板查看状态或稍后重试。",
        "Information is limited; check the task panel for status or try again later.",
    ),
    # --- LLM polish (build_verbalizer_messages) ---
    "response_verbalizer.llm_polish.system_zh": (
        "你是临床 AI 工作台的 response verbalizer（回复润色器），不是任务规划器，也不是工具执行器。\n"
        "你只能根据用户消息与下方「已锁定事实材料」组织中文自然语言；不得新增材料中不存在的结论、数值、"
        "概率、标签、任务状态、排序、路由或执行结果。\n"
        "不得修改「下一步」句子的含义；不得假装训练/预测/推荐已执行；不得输出 JSON；不要解释本规则；"
        "不要暴露内部字段名或英文键名。\n"
        "若材料表明仍需用户确认（waiting_user_confirm），必须在回复中保留「仍需确认 / 尚未执行」的语义。\n"
        "若材料中列出「必须保留语义的句子」，须在回复中完整保留其含义（可轻微理顺语序，不得削弱或矛盾）。\n"
        "语气简洁、专业、可信；不要编造患者级表格或逐行数据。\n"
        "回复使用简体中文。",
        "You are the clinical AI workbench response verbalizer (polisher), not a task planner or tool executor.\n"
        "You may ONLY reorganize the user's message together with the locked factual materials below into clear, "
        "professional English. Do not add conclusions, numbers, probabilities, labels, task states, routing, "
        "or execution outcomes that are not explicitly supported by the materials.\n"
        "Do not change the meaning of the 'next step' sentence; do not claim training/prediction/recommendation "
        "already ran; do not output JSON; do not explain these rules; do not expose internal field names or raw "
        "English API keys to the user.\n"
        "If materials indicate the user still must confirm in the UI, preserve that meaning (not executed yet).\n"
        "If materials list sentences that must be preserved, keep their meaning (light wording edits allowed; "
        "do not weaken or contradict).\n"
        "Tone: concise, professional, trustworthy; do not fabricate patient-level tables or row-level data.\n"
        "Write the final user-visible reply in English.",
    ),
    "response_verbalizer.llm_polish.user_brief_zh": ("页面模式摘要（非患者数据）：{mode}", "Workbench mode summary (non-PHI): {mode}"),
    "response_verbalizer.llm_polish.user_points_empty_zh": ("（无要点列表）", "(no bullet list)"),
    "response_verbalizer.llm_polish.user_strict_empty_zh": ("（无额外必须保留句）", "(none)"),
    "response_verbalizer.llm_polish.user_warns_empty_zh": ("（无）", "(none)"),
    "response_verbalizer.llm_polish.user_next_action_empty_zh": (
        "（材料未给出单一固定下一步句，勿编造）",
        "(No single fixed next-step sentence in materials; do not invent one.)",
    ),
    "response_verbalizer.llm_polish.user_original_zh": ("用户原话：{text}", "User message: {text}"),
    "response_verbalizer.llm_polish.user_answer_type_zh": (
        "answer_type（内部，勿复述）：{answer_type}",
        "answer_type (internal, do not repeat to user): {answer_type}",
    ),
    "response_verbalizer.llm_polish.user_facts_header_zh": ("【已锁定事实材料（只读）】", "[LOCKED FACTS — READ ONLY]"),
    "response_verbalizer.llm_polish.user_points_header_zh": ("【要点】", "[Key points]"),
    "response_verbalizer.llm_polish.user_strict_header_zh": ("【必须保留语义的句子】", "[Sentences whose meaning must be preserved]"),
    "response_verbalizer.llm_polish.user_warns_header_zh": ("【提示与边界】", "[Warnings and boundaries]"),
    "response_verbalizer.llm_polish.user_next_header_zh": ("【下一步（含义不得改变）】{na}", "[Next step — meaning must not change] {na}"),
    "response_verbalizer.llm_polish.constraints.batch_prediction_zh": (
        "\n【batch_prediction_result 专约束】\n"
        "1) 仅描述批量预测任务已完成及其聚合执行结果（总行数/成功行数/失败行数）；不得写成模型评估或性能报告。\n"
        "2) 不得修改 facts 中的 total_records、successful_records、failed_records 数值与含义。\n"
        "3) 仅当 has_download_url 为 true 且材料给出 download_url 时，才可提示用户按工作台路径下载；"
        "has_download_url 为 false 时不得声称可以下载整表。\n"
        "4) 不得引入 Accuracy、AUROC、F1、混淆矩阵、与参考标签逐行一致率等未出现在材料中的内容。\n"
        "5) 不得使用单样本预测口吻（例如把「某一标签/概率」当作本次答复的主线结论）。\n"
        "6) warnings 列表为空时不得编造额外警示；非空时不得弱化或改写其语义。\n"
        "7) 下一步句子的含义不得改变。\n",
        "\n[batch_prediction_result constraints]\n"
        "1) Only describe the completed batch prediction job and its aggregate execution counts; "
        "do not frame it as model evaluation or performance reporting.\n"
        "2) Do not change total_records / successful_records / failed_records values or meanings.\n"
        "3) Only mention a downloadable full table when has_download_url is true and a path is provided; "
        "otherwise do not claim a full-table download exists.\n"
        "4) Do not introduce Accuracy, AUROC, F1, confusion matrix, or row-wise agreement vs labels unless present.\n"
        "5) Do not use single-sample prediction framing as the main conclusion.\n"
        "6) If warnings is empty, do not invent warnings; if non-empty, preserve their meaning.\n"
        "7) Do not change the meaning of the next-step sentence.\n",
    ),
    "response_verbalizer.llm_polish.constraints.prediction_result_zh": (
        "\n【prediction_result 专约束】\n"
        "1) 不得修改 facts 中的 predicted_label 含义与取值。\n"
        "2) 不得修改 facts 中的 predicted_probability 数值；不得改写成含糊区间而丢失原值。\n"
        "3) prediction_status 为 completed 时，不得说成失败、排队、进行中或已提交草稿等其他状态。\n"
        "4) 若 has_shap_explanation 为 true：仅能说用户「可以」在工作台查看解释摘要/SHAP，"
        "不得说成「系统已完成全部解释分析」或等价强结论。\n"
        "5) 若 has_shap_explanation 为 false：不得虚构存在 SHAP 或已完成解释。\n"
        "6) 语气须保持「模型预测/模型估计/当前模型结果显示」，不得上升为个体疾病认定或确定性医学结论。\n",
        "\n[prediction_result constraints]\n"
        "1) Do not change predicted_label meaning or value.\n"
        "2) Do not change predicted_probability numeric value.\n"
        "3) If prediction_status is completed, do not describe failure/queued/running/draft states.\n"
        "4) If has_shap_explanation is true: only say the user may review SHAP/explanation in the workbench; "
        "do not claim exhaustive explanation is done.\n"
        "5) If has_shap_explanation is false: do not invent SHAP.\n"
        "6) Keep model-estimate language; do not assert definitive medical diagnoses.\n",
    ),
    "response_verbalizer.llm_polish.constraints.training_completed_zh": (
        "\n【training_completed 专约束】\n"
        "1) 不得修改 facts 中的 training_status；completed 不得说成失败、等待中或未开始。\n"
        "2) 不得修改 facts 中的 model_id、model_name 字符串与含义。\n"
        "3) 不得修改 primary_metric_name / primary_metric_value；不得编造未出现在 facts 中的指标名或数值。\n"
        "4) 仅当 release_state 为 released 时，才可说产物已按摘要标记为已注册/已发布相关状态；"
        "若为 not_released 或 unknown，不得说成「已正式发布到生产」或「已可直接用于正式发布」。\n"
        "5) 不得把 model_registered=false 或 release_state 非 released 说成已完成全部后续部署动作。\n"
        "6) 下一步句子的含义不得改变。\n"
        "7) 语气保持「训练已完成 / 当前训练结果表明」，不夸大、不写成已完成全部后续运维动作。\n"
        "8) 若 facts 中 release_state 为 unknown：不得以已发布或未发布作断言；应引导用户到任务详情与模型库核对。\n",
        "\n[training_completed constraints]\n"
        "1) Do not change training_status; if completed, do not describe failure/pending/not started.\n"
        "2) Do not change model_id / model_name strings or meanings.\n"
        "3) Do not change primary_metric_name / primary_metric_value; do not invent metrics.\n"
        "4) Only describe registry/release as released when release_state is released.\n"
        "5) Do not claim full deployment if not supported by facts.\n"
        "6) Preserve next-step meaning.\n"
        "7) Keep tone measured; training finished does not mean all operations are done.\n"
        "8) If release_state is unknown, do not assert published vs not; direct user to task details/registry.\n",
    ),
    "response_verbalizer.llm_polish.constraints.training_draft_created_zh": (
        "\n【training_draft_created 专约束】\n"
        "1) 仅表示训练配置草稿已生成；不得说成训练任务已启动、正在运行、排队执行或已完成。\n"
        "2) 若 facts 中 awaiting_explicit_user_confirm_before_run 为 true：必须保留「等待用户在界面确认」语义。\n"
        "3) 若 facts 中 awaiting_field_completion_before_confirm 为 true：说明尚有缺项，不得假装已可一键开始训练。\n"
        "4) 不得编造指标、AUC、注册、发布、写入模型库等 facts 未给出的状态。\n"
        "5) 下一步句子的含义不得改变；材料未给出下一步时勿编造。\n",
        "\n[training_draft_created constraints]\n"
        "1) Only a draft was prepared; do not say training started, is running, queued, or completed.\n"
        "2) If awaiting_explicit_user_confirm_before_run: preserve waiting-for-UI-confirm meaning.\n"
        "3) If awaiting_field_completion_before_confirm: fields are still missing.\n"
        "4) Do not invent metrics, AUC, registry/release conclusions.\n"
        "5) Preserve next-step meaning.\n",
    ),
    "response_verbalizer.llm_polish.constraints.training_failed_zh": (
        "\n【training_failed 专约束】\n"
        "1) 仅表示训练任务失败；不得说成训练已完成、指标可用、模型已发布或已写入模型库。\n"
        "2) 不得改写 facts 中的 failure_stage_bucket、current_stage、error_hint 的字面或含义。\n"
        "3) 下一步句子的含义不得改变；材料未给出下一步时勿编造。\n",
        "\n[training_failed constraints]\n"
        "1) Only training failure; do not describe success, metrics, registry, or release.\n"
        "2) Do not rewrite failure_stage_bucket / current_stage / error_hint meaning.\n"
        "3) Preserve next-step meaning.\n",
    ),
    "response_verbalizer.llm_polish.constraints.prediction_failed_zh": (
        "\n【prediction_failed 专约束】\n"
        "1) 仅表示 task-backed 预测任务失败；不得复述标签、概率、批量成功行数或 SHAP 可用性。\n"
        "2) 不得改写 facts 中的 failure_stage_bucket、current_stage、error_hint 的字面或含义。\n"
        "3) 不得引入或模仿同步 HTTP 的 PREDICTION_* canonical error_code 话术。\n"
        "4) 下一步句子的含义不得改变；材料未给出下一步时勿编造。\n",
        "\n[prediction_failed constraints]\n"
        "1) Task-backed prediction failed only; do not restate labels/probabilities/batch SHAP.\n"
        "2) Do not rewrite failure_stage_bucket / current_stage / error_hint meaning.\n"
        "3) Do not mimic HTTP PREDICTION_* error_code wording.\n"
        "4) Preserve next-step meaning.\n",
    ),
}
