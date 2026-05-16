"""Deterministic onboarding / greeting copy (welcome_policy); zh/en pairs for catalog."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "onboarding.greeting.body": (
        "你好，我是 Dr.BUG，一个面向 CRGNB 抗感染决策支持的临床 AI 助手。\n"
        "我可以帮助你完成模型训练与发布、单个患者预测或批量预测、SHAP 解释、模型性能查看，以及个体化抗菌方案推荐。\n\n"
        "你可以直接说：\n"
        "“训练一个临床疗效预测模型”\n"
        "“使用当前模型做预测”\n"
        "“查看最近一次训练结果”\n"
        "“帮我推荐用药方案”\n"
        "“比较候选用药方案”",
        "Hello, I'm Dr.BUG, a clinical AI assistant for CRGNB anti-infective decision support.\n\n"
        "I can help you train and publish prediction models, run single-sample or batch predictions, "
        "review model performance and SHAP explanations, and compare candidate antibiotic regimens "
        "for individualized treatment support.\n\n"
        "You can start with:\n"
        "\"Train a clinical efficacy prediction model with the current dataset\"\n"
        "\"Run a prediction using the current model\"\n"
        "\"Show the latest training result\"\n"
        "\"Compare candidate antibiotic regimens\"\n"
        "\"Recommend candidate antibiotic regimens\"",
    ),
    "onboarding.suffix.selected_dataset": (
        "我看到你当前选择的数据集是 {name}，可以直接基于它创建训练任务。",
        "I see that the current dataset is {name}; you can start a training task with it directly.",
    ),
    "onboarding.suffix.selected_model": (
        "当前已选择模型 {label}，可以直接用于预测或查看模型摘要。",
        "The current model is {label}; you can use it for prediction or review its summary.",
    ),
    "onboarding.suffix.training_waiting_confirm": (
        "当前还有一个训练步骤正在等待确认，你可以先在下方卡片中完成确认。",
        "A training step is currently waiting for confirmation; you can complete it in the card below.",
    ),
    "onboarding.suffix.pending_draft": (
        "当前有一项操作等待你在对话卡片中确认后再继续。",
        "An action is waiting for confirmation in the chat card before we can continue.",
    ),
}
