"""Locale pairs for backend.agent.workflow_rules (workflow next-step rule table)."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "workflow_rules.general.blocker.insufficient_context.message": (
        "当前上下文中没有明确的工作流锚点。",
        "There is no clear workflow anchor in the current context.",
    ),
    "workflow_rules.general.candidate.pick_workflow.title": (
        "先在工作台选择训练、预测或推荐相关页面",
        "Select a training, prediction, or recommendation related page in the workbench first",
    ),
    "workflow_rules.general.candidate.pick_workflow.reason": (
        "有了页面模式或焦点任务后，系统才能对齐建议。",
        "With a page mode or focus task, the system can align suggestions reliably.",
    ),
    "workflow_rules.general.candidate.describe_goal.title": (
        "用一句话说明你想完成的是训练、预测还是推荐",
        "State in one sentence whether you want training, prediction, or recommendation",
    ),
    "workflow_rules.general.candidate.describe_goal.reason": (
        "避免把配置动作误当成普通问答。",
        "This reduces mistaking configuration actions for general Q&A.",
    ),
    "workflow_rules.training.blocker.no_training_task.message": (
        "当前未绑定到一条训练任务。",
        "No training task is bound to the current workspace context.",
    ),
    "workflow_rules.training.candidate.start_or_open_training.title": (
        "从工作台发起训练或选中进行中的训练任务",
        "Start training from the workbench or select an in-progress training task",
    ),
    "workflow_rules.training.candidate.start_or_open_training.reason": (
        "需要先有一条训练任务上下文，才能讨论确认节点与后续配置。",
        "A training task context is required before discussing confirmation steps and follow-up configuration.",
    ),
    "workflow_rules.training.candidate.draft_training_explore.title": (
        "在聊天中说明训练目标以生成训练配置草稿",
        "Describe your training goal in chat to generate a training configuration draft",
    ),
    "workflow_rules.training.candidate.draft_training_explore.reason": (
        "若尚未开始，可用自然语言描述需求；系统会整理成待确认卡片，不会在对话里直接开训。",
        "If you have not started yet, describe requirements in natural language; the workbench will prepare a card to confirm, not start training directly in chat.",
    ),
    "workflow_rules.training.blocker.waiting_confirm.message": (
        "流水线在等待你在界面确认当前阶段。",
        "The workflow is waiting for you to confirm the current step in the UI.",
    ),
    "workflow_rules.training.candidate.confirm_training_card.title": (
        "在训练待确认卡片中核对并点击确认",
        "Review the training confirmation card and click confirm",
    ),
    "workflow_rules.training.candidate.confirm_training_card.reason": (
        "当前阶段的结果已就绪，需要你的显式确认后后台才会继续。",
        "The current step is ready; explicit confirmation in the UI is required before the backend continues.",
    ),
    "workflow_rules.training.precondition.training_confirm_card.label": (
        "界面展示的训练确认卡",
        "Training confirmation card shown in the UI",
    ),
    "workflow_rules.training.candidate.review_then_confirm.title": (
        "先快速核对摘要，再确认",
        "Review the summary quickly, then confirm",
    ),
    "workflow_rules.training.waiting_hint.feature_confirm": (
        "此节点通常涉及最终入模特征清单。",
        "This step usually concerns the final feature set that will enter the model.",
    ),
    "workflow_rules.training.waiting_hint.train_config": (
        "此节点通常涉及训练超参与模型类型等配置。",
        "This step usually involves training hyperparameters and model type choices.",
    ),
    "workflow_rules.training.waiting_hint.release": (
        "此节点通常涉及是否发布及发布方式。",
        "This step usually concerns whether to release and how to release.",
    ),
    "workflow_rules.training.waiting_hint.generic": (
        "请对照卡片标题核对当前等待确认的内容。",
        "Check the confirmation card title to see what is waiting for confirmation.",
    ),
    "workflow_rules.training.candidate.draft_training_adjust.title": (
        "若需改条件，可用聊天说明以重新生成训练配置草稿",
        "If you need to change conditions, describe them in chat to regenerate a training draft",
    ),
    "workflow_rules.training.candidate.draft_training_adjust.reason": (
        "重大参数变更仍应走草稿与确认，不会在对话里直接改跑中的任务。",
        "Major parameter changes should still go through draft and confirmation; the system will not silently change a running job.",
    ),
    "workflow_rules.training.blocker.task_running.message": (
        "训练任务正在后台执行。",
        "The training task is running in the background; check the task panel for progress.",
    ),
    "workflow_rules.training.candidate.wait_train.title": (
        "等待当前阶段跑完并在任务面板查看进度",
        "Wait for the current stage to finish and watch progress in the task panel",
    ),
    "workflow_rules.training.candidate.wait_train.reason": (
        "计算进行中，界面确认通常需等本阶段结束或系统再次请求确认。",
        "While compute is running, UI confirmation may need to wait until this stage ends or the system asks again.",
    ),
    "workflow_rules.training.candidate.open_task_detail.title": (
        "打开任务详情核对日志与阶段提示",
        "Open task details to review logs and stage hints",
    ),
    "workflow_rules.training.candidate.open_task_detail.reason": (
        "需要更细的执行信息时，以任务详情页为准。",
        "Use the task detail page when you need finer-grained execution information.",
    ),
    "workflow_rules.training.blocker.completed.message": (
        "训练流程已到达完成态。",
        "The training workflow has reached a completed state.",
    ),
    "workflow_rules.training.candidate.review_train_outcome.title": (
        "在任务详情查看指标与产物摘要",
        "Review metrics and artifacts in task details",
    ),
    "workflow_rules.training.candidate.review_train_outcome.reason": (
        "先核对 headline/指标块，再决定是否发布或用于下游预测。",
        "Check the headline and metric blocks first, then decide whether to release or use the model downstream.",
    ),
    "workflow_rules.training.candidate.goto_prediction_or_rec.title": (
        "若模型已就绪，可转入预测或生存获益推荐流程",
        "If the model is ready, move on to prediction or regimen comparison",
    ),
    "workflow_rules.training.candidate.goto_prediction_or_rec.reason": (
        "下游动作仍各自需要确认，不会在对话里自动执行。",
        "Downstream actions still require their own confirmations; nothing auto-runs from chat.",
    ),
    "workflow_rules.training.blocker.queued.message": (
        "任务已排队，尚未开始执行。",
        "The task is queued and has not started executing yet.",
    ),
    "workflow_rules.training.candidate.wait_queue.title": (
        "稍等排队并关注任务面板",
        "Wait in the queue and watch the task panel",
    ),
    "workflow_rules.training.candidate.wait_queue.reason": (
        "轮到执行后会自动进入运行态。",
        "Execution will move to running automatically when it is this task's turn.",
    ),
    "workflow_rules.training.candidate.inspect_failure_train.title": (
        "在任务详情查看失败原因与日志",
        "Review failure details and logs in task details",
    ),
    "workflow_rules.training.candidate.inspect_failure_train.reason": (
        "先定位失败阶段，再决定是否重试或调整数据/配置。",
        "Identify the failed stage first, then decide whether to retry or adjust data or configuration.",
    ),
    "workflow_rules.training.candidate.draft_training_retry.title": (
        "修正后可重新发起训练配置草稿",
        "After fixes, start a new training configuration draft",
    ),
    "workflow_rules.training.candidate.draft_training_retry.reason": (
        "重训仍须经过待确认卡片，不会在聊天中直接重启训练。",
        "Retraining still goes through confirmation cards; chat will not directly restart training.",
    ),
    "workflow_rules.prediction.blocker.missing_model.message": (
        "工作台尚未选定用于预测的模型。",
        "No prediction model is selected in the workspace yet.",
    ),
    "workflow_rules.prediction.candidate.pick_model.title": (
        "先在模型列表中选择目标模型",
        "Select a target model in the model list first",
    ),
    "workflow_rules.prediction.candidate.pick_model.reason": (
        "预测入口依赖模型 ID，不选模型无法对齐特征 schema 与输出口径。",
        "Prediction entry depends on a model id; without a model, feature schema alignment is not available.",
    ),
    "workflow_rules.prediction.candidate.open_predict_entry.title": (
        "打开统一预测入口（单样本/批量）",
        "Open the unified prediction entry (single-sample or batch)",
    ),
    "workflow_rules.prediction.candidate.open_predict_entry.reason": (
        "进入卡片后再补输入与确认执行。",
        "Complete inputs and confirm execution inside the card after you enter.",
    ),
    "workflow_rules.prediction.blocker.missing_dataset.message": (
        "批量预测仍缺上传文件或等效输入。",
        "Batch prediction still needs an uploaded file or equivalent input.",
    ),
    "workflow_rules.prediction.candidate.upload_batch_file.title": (
        "在批量预测卡片中上传数据文件",
        "Upload the data file in the batch prediction card",
    ),
    "workflow_rules.prediction.candidate.upload_batch_file.reason": (
        "没有输入文件就无法对齐列并完成映射。",
        "Without an input file, columns cannot be aligned and mapping cannot finish.",
    ),
    "workflow_rules.prediction.blocker.mapping_incomplete.message": (
        "列映射尚未完成或仍有未解析字段。",
        "Column mapping is incomplete or some fields are still unresolved.",
    ),
    "workflow_rules.prediction.candidate.finish_column_mapping.title": (
        "完成字段映射并保存",
        "Finish field mapping and save",
    ),
    "workflow_rules.prediction.candidate.finish_column_mapping.reason": (
        "映射决定模型可读的特征来源，未完成前不应提交执行。",
        "Mapping defines which inputs the model can read; do not submit before it is complete.",
    ),
    "workflow_rules.prediction.blocker.task_running.message": (
        "批量预测任务正在执行。",
        "The batch prediction job is running; check the task list for status.",
    ),
    "workflow_rules.prediction.candidate.wait_batch.title": (
        "等待批量任务结束并在任务列表查看状态",
        "Wait for the batch job to finish and check status in the task list",
    ),
    "workflow_rules.prediction.candidate.wait_batch.reason": (
        "批量耗时会随行数变化，以任务详情为准。",
        "Batch duration scales with row count; use task details as the source of truth.",
    ),
    "workflow_rules.prediction.blocker.batch_completed.message": (
        "批量预测已完成。",
        "Batch prediction has completed.",
    ),
    "workflow_rules.prediction.candidate.review_batch_summary.title": (
        "在任务详情或历史记录查看汇总行数与下载入口",
        "Review aggregate row counts and download entry in task details or history",
    ),
    "workflow_rules.prediction.candidate.review_batch_summary.reason": (
        "先核对成功/失败计数，再决定是否复跑或抽样复核。",
        "Check success and failure counts first, then decide whether to rerun or sample-check rows.",
    ),
    "workflow_rules.prediction.candidate.consider_rec.title": (
        "若临床路径需要，可转入用药推荐（生存获益）",
        "If clinically needed, switch to medication recommendation (survival benefit)",
    ),
    "workflow_rules.prediction.candidate.consider_rec.reason": (
        "推荐仍须单独确认，不会在对话中自动触发。",
        "Recommendation still requires separate confirmation; it will not auto-trigger from chat.",
    ),
    "workflow_rules.prediction.blocker.ready_batch.message": (
        "批量预测已具备提交条件或等待你确认执行。",
        "Batch prediction is ready to submit or waiting for you to confirm execution.",
    ),
    "workflow_rules.prediction.candidate.confirm_batch_run.title": (
        "在批量预测卡片中核对映射后确认执行",
        "Review mapping in the batch prediction card, then confirm execution",
    ),
    "workflow_rules.prediction.candidate.confirm_batch_run.reason": (
        "执行仍走待确认主链，聊天不会直接写结果。",
        "Execution follows the main confirmation chain; chat will not write results directly.",
    ),
    "workflow_rules.prediction.candidate.draft_batch_explainer.title": (
        "如需调整任务名或备注，可在卡片内修改后再确认",
        "Optionally adjust task name or notes in the card before confirming",
    ),
    "workflow_rules.prediction.candidate.draft_batch_explainer.reason": (
        "降低误跑风险。",
        "Small edits reduce accidental runs.",
    ),
    "workflow_rules.prediction.blocker.current_prediction_available.message": (
        "当前工作台已绑定一条完成的预测结果。",
        "The workbench has a bound completed prediction result.",
    ),
    "workflow_rules.prediction.candidate.read_prediction_explanation.title": (
        "查看预测摘要与解释（若有）",
        "Review the prediction summary and explanation (if available)",
    ),
    "workflow_rules.prediction.candidate.read_prediction_explanation.reason": (
        "先理解标签/概率与解释口径，再决定是否进入推荐或其他流程。",
        "Understand label, probability, and explanation framing before moving to recommendation or other flows.",
    ),
    "workflow_rules.prediction.candidate.goto_rec_if_needed.title": (
        "若需要方案层面的比较，可走用药推荐工作流",
        "If regimen-level comparison is needed, use the medication recommendation workflow",
    ),
    "workflow_rules.prediction.candidate.goto_rec_if_needed.reason": (
        "推荐与预测是不同确认链，不会自动接续执行。",
        "Recommendation and prediction use different confirmation chains; they do not auto-chain.",
    ),
    "workflow_rules.prediction.blocker.no_result_yet.message": (
        "尚未有可绑定的完成预测结果，或焦点任务仍在进行。",
        "No completed prediction result is available to bind yet, or the focus task is still in progress.",
    ),
    "workflow_rules.prediction.candidate.draft_single_prediction.title": (
        "为单样本预测生成待确认草稿（已选模型时优先）",
        "Generate a pending single-sample prediction draft (preferred when a model is selected)",
    ),
    "workflow_rules.prediction.candidate.draft_single_prediction.reason": (
        "草稿仅整理模型与字段框架；确认后才会创建预测任务，不会在聊天里直接推理。",
        "The draft only frames model and fields; a prediction task is created only after confirmation, not inferred directly in chat.",
    ),
    "workflow_rules.prediction.candidate.fill_single_or_batch.title": (
        "在预测工作区补全输入（单样本表单或批量文件/映射）",
        "Complete inputs in the prediction workspace (single-sample form or batch file and mapping)",
    ),
    "workflow_rules.prediction.candidate.fill_single_or_batch.reason": (
        "执行前必须在卡片内确认；系统不会替用户填入真实患者取值。",
        "Execution must be confirmed in the card; the system will not fill real patient values for you.",
    ),
    "workflow_rules.recommendation.blocker.missing_regimens.message": (
        "方案库中暂无启用候选方案。",
        "No enabled candidate regimens are available in the regimen library.",
    ),
    "workflow_rules.recommendation.candidate.open_regimen_management.title": (
        "先在方案管理中启用至少一条候选方案",
        "Enable at least one candidate regimen in regimen management first",
    ),
    "workflow_rules.recommendation.candidate.open_regimen_management.reason": (
        "候选方案范围未就绪时，我不建议起草推荐任务；请先扩展启用列表。",
        "When the candidate regimen set is not ready, avoid drafting a regimen recommendation task; expand the enabled list first.",
    ),
    "workflow_rules.recommendation.blocker.missing_schema.message": (
        "尚未加载推荐用的患者特征 schema。",
        "The patient feature schema for the regimen recommendation workflow has not been loaded yet.",
    ),
    "workflow_rules.recommendation.candidate.load_rec_schema.title": (
        "在推荐卡片中选择生存模型并加载特征表",
        "Select a survival model in the regimen recommendation card and load the feature table",
    ),
    "workflow_rules.recommendation.candidate.load_rec_schema.reason": (
        "需要先对齐字段定义，才能安全收集非治疗特征。",
        "Field definitions must be aligned before safely collecting non-treatment features.",
    ),
    "workflow_rules.recommendation.blocker.incomplete_features.message": (
        "患者特征尚未按表单要求填齐。",
        "Patient features are not yet complete per the form requirements.",
    ),
    "workflow_rules.recommendation.candidate.complete_rec_form.title": (
        "按表单补齐非治疗类特征并处理校验提示",
        "Complete non-treatment features per the form and resolve validation prompts",
    ),
    "workflow_rules.recommendation.candidate.complete_rec_form.reason": (
        "推荐打分依赖完整输入；表单未齐时起草也会在确认前被拦截。",
        "Scoring depends on complete input; drafting may be blocked until the form is complete.",
    ),
    "workflow_rules.recommendation.blocker.ready_to_run.message": (
        "当前推荐流程已具备起草条件；确认后系统才会真正执行推荐。",
        "The regimen recommendation workflow is ready to draft; execution only starts after you confirm.",
    ),
    "workflow_rules.recommendation.candidate.submit_rec_when_ready.title": (
        "生成待确认推荐草稿（核对后在界面确认执行）",
        "Generate a pending regimen recommendation draft (review and confirm execution in the UI)",
    ),
    "workflow_rules.recommendation.candidate.submit_rec_when_ready.reason": (
        "最建议的下一步是先生成待确认草稿；聊天不会直接创建推荐任务。",
        "The best next step is to create a pending draft first; chat will not directly create a recommendation task.",
    ),
    "workflow_rules.recommendation.candidate.draft_rec_explore.title": (
        "若还不确定参数，可先在工作台调整再让我起草",
        "If parameters are uncertain, adjust them in the workbench before asking for a draft",
    ),
    "workflow_rules.recommendation.candidate.draft_rec_explore.reason": (
        "降低误提交风险；仍不绕过 pending 确认。",
        "Reduces accidental submission; pending confirmation is still required.",
    ),
    "workflow_rules.recommendation.blocker.task_queued.message": (
        "推荐任务已在队列或等待触发，尚未进入计算。",
        "The regimen recommendation task is queued or waiting to start; it is not computing yet.",
    ),
    "workflow_rules.recommendation.candidate.view_task_status.queued.title": (
        "在任务列表查看推荐任务状态与阶段",
        "Check regimen recommendation task status and stage in the task list",
    ),
    "workflow_rules.recommendation.candidate.view_task_status.queued.reason": (
        "此阶段不需要再次起草推荐；关注排队与开始时间即可。",
        "At this stage, avoid drafting another recommendation; focus on queue position and timing.",
    ),
    "workflow_rules.recommendation.candidate.wait_for_completion.queued.title": (
        "等待任务进入运行或直至结束，再在任务面板查看进度",
        "Wait until the task starts running or finishes, then check progress in the task panel",
    ),
    "workflow_rules.recommendation.candidate.wait_for_completion.queued.reason": (
        "排队阶段不重复起草推荐；以任务状态为准。",
        "Do not draft another recommendation while queued; use task status as the source of truth.",
    ),
    "workflow_rules.recommendation.blocker.task_running.message": (
        "推荐任务正在计算中。",
        "The regimen recommendation task is computing; check the task panel for progress.",
    ),
    "workflow_rules.recommendation.candidate.view_task_status.running.title": (
        "在工作台任务面板关注当前阶段与日志摘要",
        "Watch the current stage and log summary in the workbench task panel",
    ),
    "workflow_rules.recommendation.candidate.view_task_status.running.reason": (
        "运行中优先核对任务状态，不并行起草新的推荐。",
        "While running, prioritize task status and avoid drafting another recommendation in parallel.",
    ),
    "workflow_rules.recommendation.candidate.wait_for_completion.running.title": (
        "等待推荐完成后再查看排序与解释入口",
        "Wait until regimen recommendation completes before reviewing ranking and explanation entry points",
    ),
    "workflow_rules.recommendation.candidate.wait_for_completion.running.reason": (
        "计算未结束前不建议再次生成推荐待确认项。",
        "Do not draft another pending recommendation while compute is still running.",
    ),
    "workflow_rules.recommendation.blocker.completed.message": (
        "推荐任务已完成。",
        "The regimen recommendation task has completed.",
    ),
    "workflow_rules.recommendation.candidate.view_ranked_regimens.title": (
        "先查看方案排序与概率摘要（推荐结果卡片）",
        "Review regimen ranking and probability summary in the regimen recommendation result card",
    ),
    "workflow_rules.recommendation.candidate.view_ranked_regimens.reason": (
        "完成后更适合先理解排序与置信度，而不是再次提交推荐。",
        "After completion, prefer understanding ranking and confidence before submitting another recommendation.",
    ),
    "workflow_rules.recommendation.candidate.compare_original_vs_top1.title": (
        "比较当前用药方案与 Top1 推荐方案",
        "Compare the current regimen with the top-1 recommended regimen",
    ),
    "workflow_rules.recommendation.candidate.compare_original_vs_top1.reason": (
        "并排对比有助于判断临床可接受性与获益信号。",
        "Side-by-side comparison helps assess clinical acceptability and benefit signals.",
    ),
    "workflow_rules.recommendation.candidate.view_explanation.title": (
        "若界面提供解释入口，再查看特征贡献或说明",
        "If the UI offers an explanation entry, review feature contributions or notes",
    ),
    "workflow_rules.recommendation.candidate.view_explanation.reason": (
        "解释以工作台脱敏展示为准。",
        "Explanations follow de-identified workbench presentation rules.",
    ),
    "workflow_rules.recommendation.candidate.return_to_prediction_or_next_step.title": (
        "若需更新输入、复核预测或进入下一步工作流，请回到对应工作台页面",
        "To refresh inputs, re-check prediction, or continue another workflow, return to the relevant workbench page",
    ),
    "workflow_rules.recommendation.candidate.return_to_prediction_or_next_step.reason": (
        "预测与推荐确认链分离，不会自动跳转执行。",
        "Prediction and regimen recommendation confirmation paths are separate; they do not auto-continue.",
    ),
    "workflow_rules.recommendation.candidate.view_error.title": (
        "在任务详情阅读完整错误信息与阶段",
        "Read the full error message and stage in task details",
    ),
    "workflow_rules.recommendation.candidate.view_error.reason": (
        "先看清失败原因再行动，避免盲目重试。",
        "Understand the failure reason before retrying blindly.",
    ),
    "workflow_rules.recommendation.candidate.fix_preconditions.title": (
        "根据错误摘要检查模型、方案库与必填字段",
        "Check model, regimen library, and required fields based on the error summary",
    ),
    "workflow_rules.recommendation.candidate.fix_preconditions.reason": (
        "修复前置条件后再重新获取「下一步」建议；不在此直连重试执行。",
        "Restore preconditions before asking for next-step guidance again; this path does not directly retry execution.",
    ),
    "workflow_rules.recommendation.candidate.redraft_recommendation_if_applicable.title": (
        "前置恢复后，可再问「下一步」并让我生成新的推荐待确认草稿",
        "After recovery, ask for next steps again to generate a new pending regimen recommendation draft",
    ),
    "workflow_rules.recommendation.candidate.redraft_recommendation_if_applicable.reason": (
        "仅在工作台条件满足后通过 pending 主链重试，不在对话内代为执行。",
        "Retry only through the main pending chain when workbench conditions are satisfied; chat does not execute on your behalf.",
    ),
    "workflow_rules.recommendation.candidate.generic_rec.title": (
        "在工作台打开用药推荐卡片并按提示完成每一步",
        "Open the medication regimen recommendation card in the workbench and complete each guided step",
    ),
    "workflow_rules.recommendation.candidate.generic_rec.reason": (
        "推荐链路步骤较多，以界面校验为准。",
        "The regimen recommendation chain has many steps; follow UI validation as the source of truth.",
    ),
    "workflow_rules.training.blocker.task_failed.message": (
        "训练任务失败或已中断。",
        "The training job failed or was interrupted.",
    ),
    "workflow_rules.training.blocker.task_failed.err_suffix": (
        " 摘要：{err}",
        " Summary: {err}",
    ),
    "workflow_rules.training.blocker.unknown_state.message": (
        "训练状态：{st}。",
        "Training status: {st}.",
    ),
    "workflow_rules.training.candidate.open_task_train.title": (
        "打开任务详情核对当前阶段",
        "Open task details to check the current stage",
    ),
    "workflow_rules.training.candidate.open_task_train.reason": (
        "以任务仓库展示的状态为准。",
        "Follow the state shown in the task repository.",
    ),
    "workflow_rules.recommendation.blocker.task_failed.message": (
        "推荐任务失败。",
        "The recommendation job failed.",
    ),
    "workflow_rules.recommendation.blocker.task_failed.err_suffix": (
        " 摘要：{em}",
        " Summary: {em}",
    ),
}
