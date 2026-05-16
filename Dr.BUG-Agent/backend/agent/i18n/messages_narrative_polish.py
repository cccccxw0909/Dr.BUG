"""Locale pairs for backend.agent.narrative_polish (deterministic training-completed narrative)."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "narrative_polish.task_fallback": ("本训练任务", "this training task"),
    "narrative_polish.next_step.available_for_prediction_and_regimen_comparison": (
        "在工作台允许的情况下，可将该模型用于预测与方案比较。",
        "You can use this model for prediction and regimen comparison where the workbench allows.",
    ),
    "narrative_polish.next_step.review_metrics_consider_publishing": (
        "请先查看指标与报告，如需在选模列表中使用，再执行发布到模型库。",
        "Review the metrics and reports, then publish to the model library if you want it selectable for prediction.",
    ),
    "narrative_polish.next_step.check_task_and_registry": (
        "请到任务详情与模型库界面核对注册与发布状态。",
        "Open the task detail and model library to confirm registration and publication status.",
    ),
    "narrative_polish.other_metrics.sentence": (
        "其他可用指标包括 {inner}。",
        "Additional metrics included {inner}.",
    ),
    "narrative_polish.feature.list": (
        "最终模型使用 {count} 个入模特征：{joined}。",
        "The final model used {count} input features: {joined}.",
    ),
    "narrative_polish.feature.count_only": (
        "最终模型使用 {count} 个入模特征。",
        "The final model used {count} input features.",
    ),
    "narrative_polish.zh.opening_done": ("训练已顺利完成。", "Training was completed successfully."),
    "narrative_polish.zh.base_algo": ("Dr.BUG 已完成用于「{task_name}」的 {algorithm} 模型训练", "Dr.BUG trained a {algorithm} model for {task_name}"),
    "narrative_polish.zh.base_plain": ("Dr.BUG 已完成用于「{task_name}」的模型训练", "Dr.BUG trained a model for {task_name}"),
    "narrative_polish.zh.suffix_registered": ("，并已注册到模型库。", " and registered it in the model library."),
    "narrative_polish.zh.suffix_saved_unpublished": ("，并已保存但未发布。", " and saved it without publishing."),
    "narrative_polish.zh.suffix_period": ("。", "."),
    "narrative_polish.zh.primary_metric_with_value": (
        "在最终评估中，主指标 {pm} 为 {pmv}。",
        "In the final evaluation, the primary metric was {pm}, with a value of {pmv}.",
    ),
    "narrative_polish.zh.primary_metric_name_only": (
        "本次记录的主指标名称为 {pm}；本摘要未给出稳定的主指标数值。",
        "The primary metric name recorded for this run was {pm}; a stable headline value was not included in this summary.",
    ),
    "narrative_polish.zh.primary_metric_none": (
        "本摘要未包含单一主指标，请在任务详情中查看完整指标表。",
        "This summary does not include a single headline metric; open the task detail for the full metric table.",
    ),
    "narrative_polish.zh.shap_beeswarm": (
        "SHAP beeswarm 图可用于查看模型层面的特征归因。",
        "A SHAP beeswarm plot is available to show model-based feature attribution.",
    ),
    "narrative_polish.zh.model_ready_use": (
        "该模型现已可在 Dr.BUG 中用于后续预测与方案比较。",
        "The model can now be used for prediction and regimen comparison in Dr.BUG.",
    ),
    "narrative_polish.zh.model_saved_not_listed": (
        "训练产物已保存，但该模型不会出现在预测模型列表中。",
        "The training outputs were saved, but the model will not appear in the prediction model list.",
    ),
    "narrative_polish.zh.confirm_publish_before_predict": (
        "请在任务详情与模型库中确认发布状态后，再用于预测选模。",
        "Confirm publication status in the task detail and model library before selecting this model for prediction.",
    ),
}
