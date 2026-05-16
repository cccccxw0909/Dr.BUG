"""Locale pairs for prediction_answerability sticky replies."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "pred_answer.sticky.risk": (
        "当前工作台尚未完成一次可绑定的预测执行，因此无法根据模型输出判断该样本风险高低。"
        "请先在工作台确认并执行预测后，再结合结果与解释区查看。",
        (
            "The workbench has not finished a bindable prediction run yet, so risk level cannot be judged "
            "from model output. Confirm and run prediction on the workbench first, then review results and "
            "the explanation panel."
        ),
    ),
    "pred_answer.sticky.probability": (
        "当前工作台尚未完成一次可绑定的预测执行，因此没有当前样本的预测概率可读。"
        "请先确认并执行预测后再追问概率。",
        (
            "The workbench has not finished a bindable prediction run yet, so there is no current-sample "
            "probability to read. Run prediction first, then ask about probability again."
        ),
    ),
    "pred_answer.sticky.label": (
        "当前工作台尚未完成一次可绑定的预测执行，因此没有当前样本的预测输出标签。"
        "若你问的是建模目标列名称，请以任务配置或数据字典中的目标列字段为准；"
        "这与「本次预测输出标签」不是同一概念。",
        (
            "The workbench has not finished a bindable prediction run yet, so there is no predicted output "
            "label for the current sample. If you meant the modeling target column name, use the task config "
            "or data dictionary—that is not the same as this prediction's output label."
        ),
    ),
    "pred_answer.sticky.batch": (
        "当前工作台尚未完成一次可绑定的批量预测执行，因此没有可读的整批结果摘要。"
        "请先执行批量预测后再追问。",
        (
            "The workbench has not finished a bindable batch prediction run yet, so there is no readable "
            "batch summary. Run batch prediction first, then ask again."
        ),
    ),
    "pred_answer.sticky.default": (
        "当前工作台尚未完成一次可绑定的预测执行，因此没有当前样本的预测结果可读。"
        "请先在工作台确认并执行预测后再追问结果、标签或概率。",
        (
            "The workbench has not finished a bindable prediction run yet, so there is no current-sample prediction "
            "result to read. Confirm and run prediction on the workbench first, then ask about label or probability."
        ),
    ),
}
