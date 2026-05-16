"""Localized strings for backend.agent.result_presentation."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    # --- round 1 ---
    "result_presentation.append_next_step.zh_appended": (
        "{body}下一步：{step}",
        "{body} Next step: {step}",
    ),
    "result_presentation.error_hint.default_predict": (
        "输入或环境可能有问题",
        "The input or environment may be invalid. ",
    ),
    "result_presentation.error_hint.default_train": (
        "执行过程中出现问题",
        "Something went wrong during execution. ",
    ),
    "result_presentation.error_hint.job_placeholder": (
        "该任务",
        "this job",
    ),
    "result_presentation.next_step.predict_completed_batch": (
        "优先下载整表结果做离线核对，需要时再回任务详情抽查异常行。",
        "Download the full results table for offline review; spot-check unusual rows in task details if needed.",
    ),
    "result_presentation.next_step.predict_completed_single": (
        "在解释区打开 SHAP 与主要影响因素，核对驱动项是否临床可解释。",
        "Open SHAP and the top contributing factors in the explanation panel and check clinical plausibility.",
    ),
    "result_presentation.next_step.predict_completed_unknown": (
        "在任务详情查看逐行明细，或下载整表后再做统一核对。",
        "Review row-level details in task details, or download the full table and verify there.",
    ),
    "result_presentation.next_step.train_completed": (
        "先对照任务详情中的主指标与报告，再决定是否按引导发布模型。",
        "Review the primary metric and reports in task details, then decide whether to release the model.",
    ),
    "result_presentation.predict_canceled.body": (
        "预测任务已取消。如需继续，可在工作台重新发起预测。",
        "The prediction job was canceled. To continue, start a new prediction from the workbench.",
    ),
    "result_presentation.scrub.local_path_placeholder": (
        "本地路径",
        "local path",
    ),
    "result_presentation.train_canceled.body": (
        "训练任务已取消。如需继续，可在工作台重新发起训练流程。",
        "The training job was canceled. To continue, start a new training flow from the workbench.",
    ),
    # --- round 2: train completed / policy constants ---
    "result_presentation.train_completed.fact_tail": (
        "主要结果、指标与报告已在任务详情中生成，可先对照主指标与报告查看。",
        "Key results, metrics, and reports are available in the task details; start with the primary metric and reports.",
    ),
    "result_presentation.train_completed.good_bad_unified": (
        "从本次摘要里的几项指标本身，不足以对模型做「好/坏」的强结论，更不宜对临床场景做绝对化判断。"
        "Accuracy 会受类别分布影响，不宜单独解读好坏；Precision / Recall / F1 反映阳性识别的取舍；"
        "AUROC 描述整体区分能力；在类别明显不平衡时，AUPRC 往往更值得对照。"
        "建议回到任务详情逐项核对：标签定义与正负类方向、类别分布与阈值、混淆矩阵、是否存在数据泄漏或关键特征缺失、"
        "交叉验证与外部验证是否一致。除非有额外证据，不要仅凭 AUROC<0.5 或 Accuracy<0.5 就断言「系统性错误」「远低于随机猜测」"
        "或「绝对不可用于辅助决策」之类表述。",
        "A few headline metrics alone are not enough for a strong good/bad verdict, and they should not be "
        "over-interpreted clinically. Accuracy depends on class balance; Precision/Recall/F1 reflect trade-offs for "
        "the positive class; AUROC summarizes separability; under imbalance, AUPRC is often more informative. "
        "Return to task details to verify label definitions, class balance, thresholds, confusion matrices, leakage, "
        "and validation consistency. Avoid claiming systematic failure or unusability solely from AUROC<0.5 or "
        "Accuracy<0.5 without stronger evidence.",
    ),
    "result_presentation.train_completed.best_model_degrade": (
        "当前结果里已包含各模型表现，但这里没有稳定的最优模型摘要；建议到任务详情对比主指标后再决定。",
        "Candidate model metrics are available, but this reply does not include a reliable best-model summary; "
        "compare primary metrics in task details before deciding.",
    ),
    "result_presentation.train_completed.notable_degrade": (
        "值得关注与注意点以任务详情中的报告与提示为准；这里不额外下结论。",
        "Notable caveats are governed by reports and prompts in task details; no extra conclusions are added here.",
    ),
    "result_presentation.train_completed.opening": (
        "训练已经完成。以下摘要仅供对照；是否满足你的使用预期，仍需结合任务目标、标签定义与数据语境审慎判断。",
        "Training has finished. This summary is for reference only; whether it meets your expectations still "
        "depends on the task objective, label definition, and data context.",
    ),
    "result_presentation.predict_completed.batch_no_aggregate_stats": (
        "当前摘要里没有整批统计，建议先下载结果表，再按概率或标签筛查重点样本。",
        "This summary does not include cohort-level aggregates; download the results table and screen by probability or label.",
    ),
    "result_presentation.predict_completed.batch_aggregate": (
        "批量预测已完成。共 {tr} 行：成功 {sr} 行，失败 {fr} 行。"
        "以上为任务执行层聚合摘要，不是与参考标签逐行对照的评估报告。",
        "Batch prediction finished. {tr} rows total: {sr} succeeded, {fr} failed. "
        "This is an execution-level aggregate summary, not a row-wise evaluation against reference labels.",
    ),
    "result_presentation.predict_completed.single_head": (
        "单条预测已完成。",
        "Single-sample prediction finished. ",
    ),
    "result_presentation.predict_completed.single_label_prob": (
        "该样本当前预测标签为「{label_p}」，对应概率为 {prob_p}。",
        "Predicted label: {label_p}; probability: {prob_p}. ",
    ),
    "result_presentation.predict_completed.single_label_only_line": (
        "该样本当前预测标签为「{label_p}」。",
        "Predicted label: {label_p}. ",
    ),
    "result_presentation.predict_completed.single_prob_extra": (
        "其余概率信息可在任务详情查看。",
        "See task details for additional probability information. ",
    ),
    "result_presentation.predict_completed.single_prob_only_line": (
        "该样本对应预测概率为 {prob_p}。",
        "Predicted probability: {prob_p}. ",
    ),
    "result_presentation.predict_completed.single_label_extra": (
        "标签可在任务详情查看。",
        "See task details for the label. ",
    ),
    "result_presentation.predict_completed.single_no_label_prob": (
        "概率与标签可在任务详情查看。",
        "See task details for probability and label. ",
    ),
    "result_presentation.predict_completed.single_interpretation_note": (
        "含义与临床意义需结合任务定义以及解释区与 SHAP 一起看。",
        "Interpretation should combine task definitions with the explanation panel and SHAP.",
    ),
    "result_presentation.predict_completed.single_risk_note": (
        "以上输出不作医学风险分级，仅提供标签与概率供排序与解释参考。",
        "This output is not a medical risk classification; it only provides label and probability for review.",
    ),
    "result_presentation.predict_completed.batch_done_download": (
        "批量预测已完成。整批样本的概率与标签结果均已生成，可在任务详情中逐行查看，"
        "也可直接下载结果文件。",
        "Batch prediction finished. Per-row labels and probabilities are available in task details "
        "and via the downloadable results file.",
    ),
    "result_presentation.predict_completed.unknown_batch_done": (
        "预测已完成，结果可在任务详情或预测记录中查看；若是整表批量任务，还可下载结果文件并逐行核对。",
        "Prediction finished. Review results in task details or prediction history; for table batch jobs, "
        "download the results file and verify row by row.",
    ),
    "result_presentation.common.status_unknown": ("未知", "unknown"),
    "result_presentation.train_release.failed_or_canceled": (
        "这条训练任务未成功完成，讨论 release 没有意义；请以任务详情中的状态与日志为准。"
        "这与工作台当前绑定的预测用模型不是同一口径。",
        "This training job did not finish successfully, so discussing release is not meaningful; "
        "use the task status and logs in task details. "
        "This is not the same notion as the workbench's currently bound prediction model.",
    ),
    "result_presentation.train_release.not_completed": (
        "这条训练任务当前状态为「{status}」，是否已 release 请以任务详情与结果摘要为准。"
        "不要把它与工作台右侧「当前绑定模型」是否已注册混为一谈。",
        'For this training job, the current status is "{status}". '
        "Whether it has been released should be confirmed from task details and the result summary. "
        "Do not conflate this with whether the currently selected model on the right is registered.",
    ),
    "result_presentation.train_release.no_verifiable_fields": (
        "就你当前关注的这条训练任务而言：任务摘要未包含可核对的「是否已写入模型库/是否已发布」字段，"
        "请勿在本对话中直接断言已发布或未发布；请到任务详情与模型库对照 model_id 与注册/发布状态。",
        "For this training job: the summary does not include verifiable fields for whether the artifact was written "
        "to the model library or released there; do not assert release status in chat—"
        "verify model_id against task details and the model library. ",
    ),
    "result_presentation.train_release.mid_phrase_model_id": (
        "任务摘要中的模型标识为「{mid}」。",
        'The summary lists model_id as "{mid}". ',
    ),
    "result_presentation.train_release.released": (
        "就你当前关注的这条训练任务而言：根据任务摘要，本次产物已 release 并已写入模型库。",
        "For this training job: according to the summary, this artifact is released and recorded "
        "in the model library. ",
    ),
    "result_presentation.train_release.released_suffix_compare": (
        "若你还想核对「工作台当前选中的预测绑定模型」是否同一条记录，请到模型库列表对照 model_id，两者不是自动等价字段。",
        "If you need to confirm whether the workbench's currently selected prediction-bound model "
        "is the same record, compare model_ids in the model library; these fields are not automatically equivalent.",
    ),
    "result_presentation.train_release.not_released": (
        "就你当前关注的这条训练任务而言：根据任务摘要，本次尚未 release 或未写入模型库。"
        "这不代表工作台里其他已注册模型不可用；也不应反推为「模型库中同名条目已发布」。",
        "For this training job: according to the summary, this artifact is not yet released or not written "
        "to the model library. "
        "That does not mean other registered models are unavailable; do not infer release status for a same-name "
        "library entry from this summary alone.",
    ),
    "result_presentation.train_intent.best_model_marked": (
        "任务摘要中已标注的最优模型为「{ev}」；更细的对比仍以任务详情为准。",
        "The task summary marks the best candidate as “{ev}”; use task details for finer comparisons.",
    ),
    "result_presentation.train_intent.filter_summary_excerpt": (
        "任务摘要中的筛选说明包含：{clip}完整取舍仍以任务详情报告为准。",
        "Filter summary excerpt: {clip} Full trade-offs remain in task-detail reports.",
    ),
    "result_presentation.predict_intent.batch_no_single_label": (
        "整批预测已完成。批量任务没有单一「输出标签」口径；请在导出表或任务详情中按行查看每条样本的标签。",
        "Batch prediction finished. There is no single output-label summary; review labels per row in exports or task details.",
    ),
    "result_presentation.predict_intent.batch_no_single_prob": (
        "整批预测已完成。批量任务不提供单一概率口径；请在导出表或任务详情中按行查看每条样本的概率。",
        "Batch prediction finished. There is no single probability summary; review probabilities per row in exports or task details.",
    ),
    "result_presentation.predict_intent.single_label": (
        "当前该条预测的输出标签为「{label_p}」。",
        "Predicted label for this row: {label_p}.",
    ),
    "result_presentation.predict_intent.single_prob": (
        "当前该条预测的输出概率为 {prob_p}。",
        "Predicted probability for this row: {prob_p}.",
    ),
    "result_presentation.predict_intent.single_label_missing": (
        "预测已完成，但当前摘要里没有稳定的单条输出标签字段，请到任务详情查看。",
        "Prediction finished, but a stable single-row label field is not in this summary; open task details.",
    ),
    "result_presentation.predict_intent.single_prob_missing": (
        "预测已完成，但当前摘要里没有稳定的单条概率字段，请到任务详情查看。",
        "Prediction finished, but a stable single-row probability field is not in this summary; open task details.",
    ),
    "result_presentation.predict_intent.single_without_batch_stats": (
        "当前任务更像单条预测结果，没有整批统计口径；可先查看该条的标签、概率与解释，再决定是否改为批量任务。",
        "This looks like a single-row prediction without cohort-level stats; review label/probability/explanation, "
        "then switch to a batch job if needed.",
    ),
    "result_presentation.predict_intent.batch_done_short": (
        "整批预测已完成。",
        "Batch prediction finished. ",
    ),
    "result_presentation.predict_intent.batch_count_stat": (
        "整批预测已完成。从任务摘要可见条数类统计约为 {n}；更细的分布仍以任务详情与导出表为准。",
        "Batch prediction finished. A coarse count-style statistic in the summary is about {n}; "
        "see task details and exports for finer distribution.",
    ),
    "result_presentation.predict_intent.pred_why": (
        "具体驱动因素会在解释结果中体现；请打开 SHAP 与主要影响因素逐项查看，对话里不推断特征贡献细节。",
        "Drivers appear in the explanation output; open SHAP/top factors and do not infer contributions from chat alone.",
    ),
    "result_presentation.predict_intent.pred_caution_suffix": (
        "请同时留意任务详情与解释区中的提示与警告。",
        " Also review warnings in task details and the explanation panel.",
    ),
    # --- latest prediction disclaimer (no bindable workspace run) ---
    "result_presentation.latest_prediction_disclaimer.no_current_run": (
        "当前工作台尚未完成一次可绑定的预测执行，因此没有「当前这一次」的预测结果可读。",
        "The workbench has not finished a bindable prediction run yet, so there is no "
        "“current run” prediction output to read.",
    ),
    "result_presentation.latest_prediction_disclaimer.no_history_summary": (
        "系统也未返回可用的历史预测摘要；可在执行预测后再从预测历史或任务列表查看。",
        "No usable historic prediction summary was returned; run a prediction first, then check prediction "
        "history or the task list.",
    ),
    "result_presentation.latest_prediction_disclaimer.history_intro": (
        "若你指的是历史归档中的最近一次有效预测记录（不等同于当前工作台这一次任务的结果），摘要如下：",
        "If you mean the latest valid archived prediction record (not equivalent to the current workbench run), "
        "the summary is:",
    ),
    "result_presentation.latest_prediction_disclaimer.model_mismatch_note": (
        "注意：该条记录涉及的模型标识「{mid}」与当前工作台所选「{wm}」不一致，请勿将其当作当前模型的输出。",
        "Note: this record involves model_id “{mid}”, which differs from the workbench selection “{wm}”; "
        "do not treat it as output from the currently selected model.",
    ),
    "result_presentation.latest_prediction_disclaimer.batch_record": (
        "该历史记录（批量）：任务「{tn}」，模型「{mn}」。{summary_text}",
        "Historic record (batch): task “{tn}”, model “{mn}”. {summary_text}",
    ),
    "result_presentation.latest_prediction_disclaimer.single_record_label_prob": (
        "该历史记录（单条）：任务「{tn}」，模型「{mn}」；输出标签「{lab_s}」，概率约 {ptxt}。",
        "Historic record (single-row): task “{tn}”, model “{mn}”; label “{lab_s}”, probability ~{ptxt}.",
    ),
    "result_presentation.latest_prediction_disclaimer.single_record_label_only": (
        "该历史记录（单条）：任务「{tn}」，模型「{mn}」；输出标签「{lab_s}」。",
        "Historic record (single-row): task “{tn}”, model “{mn}”; label “{lab_s}”.",
    ),
    "result_presentation.latest_prediction_disclaimer.task_source_note": (
        "（该段文字来自一条已完成的预测任务摘要投影，但仍不应理解为你在当前页面尚未执行的那次预测。）",
        "(This text comes from a completed prediction task summary projection; it still must not be read as "
        "the prediction you have not yet run on this page.)",
    ),
    # --- train metric one-liner (compose_train_completed_standard) ---
    "result_presentation.metric_label.accuracy": (
        "准确率",
        "Accuracy",
    ),
    "result_presentation.train_metric.primary_metric_sentence": (
        "详情中已汇总主指标（如 {label} 约为 {value}）。",
        "Primary metrics are summarized in task details (e.g., {label} ≈ {value}).",
    ),
    "result_presentation.train_metric.metrics_available": (
        "详情中已汇总主要评估指标，可直接对照查看。",
        "Key evaluation metrics are summarized in task details.",
    ),
    # --- train / predict failure buckets, cores, and next-step hints ---
    "result_presentation.train_failure.rough.data_validation_prep": (
        "数据校验或数据准备",
        "data validation or data preparation",
    ),
    "result_presentation.train_failure.rough.feature_screening": (
        "特征筛选或特征配置",
        "feature screening or feature configuration",
    ),
    "result_presentation.train_failure.rough.feature_confirmation": (
        "特征确认",
        "feature confirmation",
    ),
    "result_presentation.train_failure.rough.model_training_eval": (
        "模型训练或评估",
        "model training or evaluation",
    ),
    "result_presentation.train_failure.rough.wrap_up_publish": (
        "结果整理或发布准备",
        "wrap-up or publishing",
    ),
    "result_presentation.train_failure.rough.generic": (
        "训练流程中的某一环节",
        "a step in the training workflow",
    ),
    "result_presentation.train_failure.core": (
        "训练失败，问题大致出在{rough}。{hint}。",
        "Training failed; the issue likely involves {rough}. {hint}",
    ),
    "result_presentation.train_failure.fail_check_first": (
        "失败原因概括：{hint}；大致卡在{rough}。",
        "Failure summary: {hint} Likely stage: {rough}.",
    ),
    "result_presentation.train_failure.next_step.data_validation_prep": (
        "打开任务日志定位校验失败点，并回到数据准备核对字段规则与样本，修正后再重试。",
        "Open task logs to find validation failures, review field rules and samples in data prep, fix, and retry.",
    ),
    "result_presentation.train_failure.next_step.feature_screening": (
        "查看日志中的特征相关报错，并检查候选与入模特征配置。",
        "Check feature-related errors in logs and review candidate vs final feature settings.",
    ),
    "result_presentation.train_failure.next_step.feature_confirmation": (
        "回到特征确认清单逐项核对，并结合日志中的阻塞项修改。",
        "Review the feature confirmation checklist and address blockers noted in logs.",
    ),
    "result_presentation.train_failure.next_step.model_training_eval": (
        "查看训练与评估日志，必要时调整超参或数据划分后重试。",
        "Review training/evaluation logs; adjust hyperparameters or data splits if needed, then retry.",
    ),
    "result_presentation.train_failure.next_step.wrap_up_publish": (
        "查看日志中的发布前检查项，修正后再提交发布。",
        "Review pre-publish checks in logs, fix issues, then submit again.",
    ),
    "result_presentation.train_failure.next_step.generic": (
        "先查看任务日志中的首尾报错，再按提示逐项修正后重试。",
        "Open task logs for the first/last errors, follow the hints, fix issues, and retry.",
    ),
    "result_presentation.predict_failure.rough.read_input": (
        "读取输入数据",
        "reading input data",
    ),
    "result_presentation.predict_failure.rough.field_mapping": (
        "字段匹配或列名映射",
        "column mapping or field alignment",
    ),
    "result_presentation.predict_failure.rough.load_model_env": (
        "加载模型或环境",
        "model loading or runtime environment",
    ),
    "result_presentation.predict_failure.rough.generating": (
        "生成预测结果",
        "generating predictions",
    ),
    "result_presentation.predict_failure.rough.generic": (
        "预测流程中的某一环节",
        "a step in the prediction workflow",
    ),
    "result_presentation.predict_failure.core": (
        "预测失败，看起来更像是{rough}方面的问题（{hint}）。",
        "Prediction failed; this most likely relates to {rough}. {hint}",
    ),
    "result_presentation.predict_failure.fail_check_first": (
        "失败原因概括：{hint}；大致卡在{rough}。",
        "Failure summary: {hint} Likely stage: {rough}.",
    ),
    "result_presentation.predict_failure.next_step.read_input": (
        "检查上传文件是否可读、编码与路径是否正确，并打开日志查看读入报错。",
        "Check that the upload is readable (encoding/path) and review read errors in logs.",
    ),
    "result_presentation.predict_failure.next_step.field_mapping": (
        "对照模型字段清单逐项修正列名映射，并在日志中查看缺失或类型不符项。",
        "Fix column-to-field mapping against the model checklist; check logs for missing/type issues.",
    ),
    "result_presentation.predict_failure.next_step.load_model_env": (
        "确认所选模型版本与权限，并在日志中查看加载或依赖相关错误。",
        "Confirm model version/permissions and review load/dependency errors in logs.",
    ),
    "result_presentation.predict_failure.next_step.generating": (
        "查看推理阶段日志中的行级报错，并核对输入值是否在允许范围内。",
        "Review row-level errors in inference logs and verify inputs are within allowed ranges.",
    ),
    "result_presentation.predict_failure.next_step.generic": (
        "先打开任务日志定位首条报错，再核对上传数据与字段是否与模型一致。",
        "Open task logs for the first error, then verify uploaded data and fields match the model.",
    ),
}
