"""Locale pairs for backend.agent.response_payloads user-visible copy."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "payload.semantic.boundary": ("（边界）", "(Boundary) "),
    "payload.semantic.pending_prefix": ("仍需确认：", "Still requires confirmation: "),
    "payload.probability_pct_numeric": ("{pct}%（数值 {num:g}）", "{pct}% (numeric value {num:g})"),
    "payload.probability_plain": ("{num:g}", "{num:g}"),
    "payload.batch_bundle.headline_counts": (
        "共 {tr} 行：成功 {sr}，失败 {fr}。",
        "{tr} rows total: {sr} succeeded, {fr} failed.",
    ),
    "payload.batch_result.headline_fallback": ("批量预测已完成", "Batch prediction completed"),
    "payload.batch_result.aggregate_note_zh": (
        "表级执行聚合（行数统计），不是评估或校准报告。",
        "Table-level execution aggregate (row counts), not an evaluation or calibration report.",
    ),
    "payload.batch_result.summary_zh_1": (
        "本次答复仅描述批量预测任务已完成后的聚合执行结果；不提供离线模型评估或性能对标结论。",
        (
            "This reply only describes the completed batch prediction job and its aggregate execution counts; "
            "it does not provide offline model evaluation or benchmark conclusions."
        ),
    ),
    "payload.batch_result.summary_zh_2": (
        "全表共 {tr} 行：成功产出预测 {sr} 行，逐行执行失败 {fr} 行。",
        "Across the table: {tr} rows total; predictions produced for {sr} rows; per-row execution failed for {fr} rows.",
    ),
    "payload.batch_result.summary_zh_partial_fail": (
        "部分行失败仅表示对应行未成功生成预测输出；批量任务整体状态仍以任务为「已完成」为准。",
        "Per-row failures mean those rows did not produce a prediction output; the batch job overall can still be completed.",
    ),
    "payload.batch_result.summary_zh_filename": (
        "整表结果文件名（与路径末段一致时）：「{ofn}」。",
        'Full-table result file name (when it matches the path tail): "{ofn}".',
    ),
    "payload.batch_result.summary_zh_has_dl": (
        "已提供结果文件下载路径；请到工作台按给定路径获取整表输出。",
        "A result file download path is available; use the path from the workbench to fetch the full-table output.",
    ),
    "payload.batch_result.summary_zh_no_dl": (
        "当前锁定摘要未提供下载路径；请勿声称可以下载整表结果文件。",
        "The locked summary does not include a download path; do not claim a full-table results file is downloadable.",
    ),
    "payload.batch_result.next_action_zh": (
        "请在工作台下载结果文件核对；如需单条复核请使用统一预测入口的单样本预测。",
        "Download and review the result file in the workbench; use the single-sample prediction entry if one row needs follow-up.",
    ),
    "payload.pred_result.unnamed_task": ("（未命名任务）", "(unnamed task)"),
    "payload.pred_result.unnamed_model": ("（未命名模型）", "(unnamed model)"),
    "payload.pred_result.semantic_summary": (
        "单样本预测任务「{tn}」已完成；模型输出标签 {lab!s}，预测概率见 facts。",
        'Single-sample prediction task "{tn}" is completed; model output label {lab!s}; see facts for probability.',
    ),
    "payload.pred_result.summary_zh_1": ("单样本预测任务「{tn}」当前状态为已完成。", 'The single-sample prediction task "{tn}" is completed.'),
    "payload.pred_result.summary_zh_2": (
        "当前模型输出显示预测标签为「{lab}」；预测概率为 {prob_txt}。",
        "The current model output shows predicted label {lab!s}; predicted probability {prob_txt}.",
    ),
    "payload.pred_result.summary_zh_3": (
        "以上均为模型预测/统计估计结果，不得替代临床诊疗中的个案认定与决策。",
        "These are model estimates only and must not replace individualized clinical judgment or decisions.",
    ),
    "payload.pred_result.summary_zh_shap_yes": (
        "工作台可提供解释摘要或 SHAP 相关信息，用户可自行打开查看；「可查看」不等于「系统已代为完成全部解释分析」。",
        (
            "The workbench may offer explanation summaries or SHAP details for the user to open; "
            "“can view” does not mean the system has already completed exhaustive explanation analysis."
        ),
    ),
    "payload.pred_result.summary_zh_shap_no": (
        "当前未标记有可用的单样本解释摘要入口；请勿声称已完成 SHAP 或完整解释分析。",
        "No single-sample explanation summary entry is marked as available; do not claim SHAP or full explanation is done.",
    ),
    "payload.pred_result.next_zh_shap": (
        "可在工作台结果卡片中查看预测详情与解释入口（如有）；如需可发起新的单样本预测。",
        "Review prediction details and any explanation entry in the workbench results card; start another single-sample prediction if needed.",
    ),
    "payload.pred_result.next_zh_no_shap": (
        "可在工作台结果卡片中查看预测详情；如需可发起新的单样本预测。",
        "Review prediction details in the workbench results card; start another single-sample prediction if needed.",
    ),
    "payload.pred_result.warning_zh_1": (
        "不得将「可查看解释」表述为「解释分析已全部完成」。",
        'Do not phrase “can view explanations” as “explanation analysis is fully complete”.',
    ),
    "payload.pred_result.warning_zh_2": (
        "不得弱化或改写上述 Predicted label / Predicted probability 的数值与标签含义。",
        "Do not weaken or change the numeric meaning of Predicted label / Predicted probability above.",
    ),
    "payload.pred_result.warning_zh_3": (
        "不得将模型输出表述为个体疾病认定、确定性治疗结论或替代医师决策的依据。",
        "Do not present model output as a definitive diagnosis, certain treatment conclusion, or a substitute for physician judgment.",
    ),
    "payload.pred_result.headline_zh": ("单样本预测已完成", "Single-patient prediction completed"),
    "payload.train_completed.unnamed_task": ("（未命名任务）", "(unnamed task)"),
    "payload.train_completed.unnamed_model": ("（未命名模型）", "(unnamed model)"),
    "payload.train_completed.semantic_summary": (
        "训练任务「{tn}」已完成；主指标与模型注册/发布状态以本回合 facts 为准，不得臆测。",
        'Training task "{tn}" is completed; primary metric and registry/release state are exactly as in facts—do not guess.',
    ),
    "payload.train_completed.summary_zh_1": ("训练任务「{tn}」当前状态为已完成。", 'Training task "{tn}" is completed.'),
    "payload.train_completed.summary_zh_metric": ("任务摘要中的主指标摘录：{pm_txt}。", "Primary metric excerpt from the task summary: {pm_txt}."),
    "payload.train_completed.summary_zh_no_metric": (
        "当前摘要未稳定暴露单一主指标键值；更细的指标请以任务详情为准。",
        "This summary does not stably expose a single primary metric key; see task details for finer metrics.",
    ),
    "payload.train_completed.summary_zh_released": (
        "根据任务摘要字段：产物已标记为已注册或已发布相关状态之一；具体仍以任务详情与模型库记录为准。",
        "Per task-summary fields: the artifact is marked as registered or release-related; still verify in task details and the model registry.",
    ),
    "payload.train_completed.summary_zh_not_released": (
        "根据任务摘要字段：尚未标记为已写入模型库/已发布；训练完成不等于已完成对外发布流程。",
        "Per task-summary fields: not marked as written to the model library / released; training finished does not mean the external release flow is done.",
    ),
    "payload.train_completed.summary_zh_unknown_1": (
        "任务摘要未包含明确的 model_registered / is_published 布尔字段；请勿断言注册或发布结论。",
        "The task summary lacks explicit model_registered / is_published booleans; do not assert registration or release conclusions.",
    ),
    "payload.train_completed.summary_zh_unknown_2": (
        "请到任务详情与模型库界面自行核对注册/发布相关字段；本回合不在缺少布尔字段时替用户下「已/未发布」结论。",
        "Open task details and the model registry to verify registration/release fields; do not substitute a definitive released/not-released verdict when booleans are missing.",
    ),
    "payload.train_completed.next_action_zh": (
        "先对照任务详情中的主指标与报告，再决定是否按引导发布模型。",
        "Review primary metrics and reports in task details first, then decide whether to release the model as guided.",
    ),
    "payload.train_completed.headline_zh": ("模型训练已完成", "Model training completed"),
    "payload.train_completed.warning_zh_1": (
        "不得将「训练跑完」等同于生产环境已上线或对外发布完成，除非 facts 中 release_state 为 released。",
        'Do not equate “training finished” with production go-live or external release unless facts.release_state is released.',
    ),
    "payload.train_completed.warning_zh_2": (
        "不得修改 facts 中的 model_id、model_name、primary_metric、model_registered、is_published、release_state 的含义。",
        "Do not change the meaning of model_id, model_name, primary_metric, model_registered, is_published, or release_state in facts.",
    ),
    "payload.train_completed.warning_zh_3": (
        "不得把 training_status=completed 说成失败、进行中或草稿未执行。",
        "Do not describe training_status=completed as failed, in progress, or an unexecuted draft.",
    ),
    "payload.train_completed.warning_zh_unknown": (
        "release_state 为 unknown：不得作注册/发布完成与否的断定；应引导用户到任务详情与模型库逐项核对。",
        "When release_state is unknown: do not assert registration or release completion; guide the user to task details and the model registry.",
    ),
    "payload.train_failed.summary_bucket_zh": ("粗分失败环节：{bucket}", "Failure stage bucket: {bucket}"),
    "payload.train_failed.summary_hint_zh": ("错误提示：{hint}", "Error hint: {hint}"),
    "payload.train_failed.headline_zh": ("训练任务失败", "Training job failed"),
    "payload.train_failed.warning_zh_1": (
        "不得将本回复表述为训练已完成、指标已就绪、模型已发布或已写入模型库。",
        "Do not describe training as completed, metrics-ready, published, or written to the model registry.",
    ),
    "payload.train_failed.warning_zh_2": (
        "不得修改 facts 中的 task_status、failure_stage_bucket、current_stage、error_hint 的含义与字面。",
        "Do not change the meaning or wording of task_status, failure_stage_bucket, current_stage, or error_hint in facts.",
    ),
    "payload.train_failed.warning_zh_3": (
        "不得引入同步 HTTP 预测 API 的 canonical error_code 口径（本载荷仅 task-backed）。",
        "Do not impersonate synchronous HTTP prediction API canonical error_code semantics (this payload is task-backed only).",
    ),
    "payload.pred_failed.summary_bucket_zh": ("粗分失败环节：{bucket}", "Failure stage bucket: {bucket}"),
    "payload.pred_failed.summary_hint_zh": ("错误提示：{hint}", "Error hint: {hint}"),
    "payload.pred_failed.headline_zh": ("预测任务失败", "Prediction job failed"),
    "payload.pred_failed.warning_zh_1": (
        "不得将本回复表述为预测已成功、标签/概率可用或结果表已生成。",
        "Do not describe prediction as successful with label/probability available or an output table generated.",
    ),
    "payload.pred_failed.warning_zh_2": (
        "不得修改 facts 中的 task_status、failure_stage_bucket、current_stage、error_hint 的含义与字面。",
        "Do not change the meaning or wording of task_status, failure_stage_bucket, current_stage, or error_hint in facts.",
    ),
    "payload.pred_failed.warning_zh_3": (
        "不得冒充同步 HTTP 校验失败或复述 PREDICTION_* canonical error_code（本载荷仅 task 行真值）。",
        "Do not impersonate synchronous HTTP validation failures or PREDICTION_* canonical error_code strings "
        "(this payload reflects task-row truth only).",
    ),
}
