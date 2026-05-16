"""Locale pairs for backend.agent.status_presentation."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "status.train_wait.features": ("建模将采纳哪些特征", "which features are adopted for modeling"),
    "status.train_wait.hyperparams": ("超参数与模型类型", "hyperparameters and model type"),
    "status.train_wait.publish": ("是否以及如何发布该模型", "whether and how to release the model"),
    "status.train_wait.next_step": ("下一项训练配置步骤", "the next training configuration step"),
    "status.card.feature_confirm": ("模型训练 — 特征确认", "Model training — feature confirmation"),
    "status.card.train_config": ("模型训练 — 训练配置", "Model training — training configuration"),
    "status.card.publish_confirm": ("模型训练 — 发布确认", "Model training — release confirmation"),
    "status.card.pending": ("模型训练 — 待确认", "Model training — pending confirmation"),
    "status.stage.train_workflow": ("训练工作流", "training workflow"),
    "status.stage.data_checks": ("数据检查", "data checks"),
    "status.stage.feature_search": ("候选特征搜索", "candidate feature search"),
    "status.stage.apply_features": ("训练前应用特征", "applying features before training"),
    "status.stage.feature_confirm": ("特征确认", "feature confirmation"),
    "status.stage.model_training": ("模型训练", "model training"),
    "status.stage.wrap_publish": ("收尾并准备发布", "wrapping up and preparing release"),
    "status.stage.current_step": ("当前步骤", "current step"),
    "status.pred.prediction_workflow": ("预测工作流", "prediction workflow"),
    "status.pred.read_input": ("读取输入数据", "reading input data"),
    "status.pred.field_mapping": ("字段映射", "field mapping"),
    "status.pred.generating": ("生成预测", "generating predictions"),
    "status.pred.postprocess": ("后处理输出", "post-processing outputs"),
    "status.pred.loading_model": ("加载模型", "loading the model"),
    "status.pred.completed": ("已完成", "completed"),
    "status.pred.processing_samples": ("处理样本中", "processing samples"),
    "status.train_reply.current_step_fallback": ("当前步骤", "current step"),
    "status.train_reply.waiting_item_fallback": ("下一项训练配置步骤", "the next training configuration step"),
    "status.train_reply.waiting_user": (
        "当前状态为等待确认（{title}）：请在您确认{item}后继续。这并非工作进程卡住或系统无响应。",
        (
            "Status is waiting for confirmation ({title}): continue after you confirm {item}. "
            "This is not the worker being stuck or the system being unresponsive."
        ),
    ),
    "status.train_reply.queued": (
        "训练任务已排队；被调度后将自动在后台运行。",
        "The training job is queued; it will run in the background when scheduled.",
    ),
    "status.train_reply.running": (
        "正在后台运行：{stage}。完成后请在任务详情中查看进度与指标。",
        "Running in the background: {stage}. When it finishes, open task details for progress and metrics.",
    ),
    "status.train_duration.phase2": (
        (
            "本阶段在后台运行特征搜索，耗时通常为几分钟到数十分钟，取决于数据规模与搜索设置。"
            "此处无法给出可靠 ETA——请以任务详情、进度与日志为准。"
        ),
        (
            "This phase runs feature search in the background; it often takes minutes to tens of minutes "
            "depending on data size and search settings. There is no reliable ETA here—use task details, "
            "progress, and logs."
        ),
    ),
    "status.train_duration.phase3_running": (
        "准备建模特征与下一屏通常较快；仍请以任务详情中的状态为准。",
        "Preparing modeling features and the next screen is usually quick; still follow task details for status.",
    ),
    "status.train_duration.phase4": (
        "训练与评估耗时因配置而异，常见为数十分钟量级；无法给出精确 ETA——请查看任务详情。",
        (
            "Training and evaluation duration varies and is often on the order of tens of minutes; "
            "there is no precise ETA—check task details."
        ),
    ),
    "status.train_duration.phase5": (
        "发布前收尾通常较快；请以任务详情为准。",
        "Pre-release wrap-up is usually short; follow task details.",
    ),
    "status.train_duration.default": (
        "整体耗时取决于数据与配置，无法给出单一 ETA——请在任务详情中关注进度。",
        "Overall time depends on data and configuration; there is no single ETA—watch progress in task details.",
    ),
    "status.predict_reply.stage_fallback": ("处理样本中", "processing samples"),
    "status.predict_reply.queued_batch": (
        "批量预测已提交；开始后将逐行生成结果。",
        "Batch prediction is submitted; once it starts, results are produced row by row.",
    ),
    "status.predict_reply.queued_single": (
        "单样本预测已提交；运行完成后可获得该行的概率与标签。",
        "Single-sample prediction is submitted; when it runs, you will get probability and label for that row.",
    ),
    "status.predict_reply.queued_generic": (
        "预测已提交；开始运行后请在任务视图中查看进度与输出。",
        "Prediction is submitted; track progress and outputs in the task view once it starts.",
    ),
    "status.predict_reply.running_batch": (
        "批量预测运行中；完成后可获取完整结果表。",
        "Batch prediction is running; you can retrieve the full table when it completes.",
    ),
    "status.predict_reply.running_single": (
        "单样本预测当前处于「{stage}」；完成后请查看该行的概率与标签。",
        "Single-sample prediction is at “{stage}”; when it finishes, review probability and label for that row.",
    ),
    "status.predict_reply.running_generic": (
        "预测仍在「{stage}」阶段运行；完成后请查看概率与标签。",
        "Prediction is still running at “{stage}”; when it finishes, review probability and label.",
    ),
    "status.no_active_tasks": (
        "当前没有进行中的训练或预测任务。",
        "There is no active training or prediction task right now.",
    ),
}
