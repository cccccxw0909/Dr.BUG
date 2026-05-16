"""Metrics by task type: binary/multi-class classification, regression."""

from __future__ import annotations

from typing import Callable, Dict, List, Literal, Tuple, Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

TASK_TYPES = ("binary", "multiclass", "regression")
TaskType = Literal["binary", "multiclass", "regression"]


def get_primary_metric(task_type: TaskType) -> str:
    """Primary metric for model selection."""
    if task_type == "binary":
        return "auroc"
    if task_type == "multiclass":
        return "macro_f1"
    return "mse"


def get_scoring_string(task_type: TaskType) -> str:
    """Scoring string for cross_val_score / GridSearchCV."""
    if task_type == "binary":
        return "roc_auc"
    if task_type == "multiclass":
        return "f1_macro"
    return "neg_mean_squared_error"


def get_all_metric_names(task_type: TaskType) -> List[str]:
    """All metric names for reporting. Only: Accuracy, Precision, Recall, F1-score, AUROC, AUPRC."""
    if task_type in ("binary", "multiclass"):
        return ["Accuracy", "Precision", "Recall", "F1-score", "AUROC", "AUPRC"]
    # Regression: include MSE for Phase4 comparison; keep RMSE/MAE/R² for Phase2 screening compatibility.
    return ["MSE", "MAE", "RMSE", "R2", "PCC"]


def get_recommendation_metrics(task_type: TaskType) -> List[str]:
    """Metrics used for final recommendation (top 6 per metric)."""
    if task_type == "binary":
        return ["AUPRC", "AUROC", "F1-score", "Accuracy", "Recall", "Precision"]
    if task_type == "multiclass":
        return ["AUPRC", "AUROC", "F1-score", "Accuracy", "Recall", "Precision"]
    return ["MAE", "RMSE", "R2"]


def evaluate_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
    task_type: str = "binary",
) -> Dict[str, float]:
    """Evaluate classification metrics."""
    n_classes = len(np.unique(y_true))
    if n_classes == 1:
        return {m: 0.0 for m in get_all_metric_names(task_type)}

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rec = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    result = {
        "Accuracy": acc,
        "Precision": prec,
        "Recall": rec,
        "F1-score": f1,
    }

    if y_proba is not None and len(y_proba.shape) >= 2:
        try:
            if task_type == "binary" and y_proba.shape[1] == 2:
                auroc = float(roc_auc_score(y_true, y_proba[:, 1]))
                auprc = float(average_precision_score(y_true, y_proba[:, 1]))
            else:
                auroc = float(roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro"))
                auprc = float(average_precision_score(y_true, y_proba, average="macro"))
            result["AUROC"] = auroc
            result["AUPRC"] = auprc
        except Exception:
            result["AUROC"] = 0.0
            result["AUPRC"] = 0.0
    else:
        result["AUROC"] = 0.0
        result["AUPRC"] = 0.0

    return result


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Evaluate regression metrics."""
    mse = float(mean_squared_error(y_true, y_pred))
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))
    pcc = float(np.corrcoef(y_true, y_pred)[0, 1]) if len(y_true) > 1 else 0.0
    if np.isnan(pcc):
        pcc = 0.0
    return {"MSE": mse, "MAE": mae, "RMSE": rmse, "R2": r2, "PCC": pcc}


def get_evaluate_fn(task_type: TaskType) -> Callable[..., Dict[str, float]]:
    """Get evaluation function for task type."""
    if task_type == "regression":
        return evaluate_regression

    def _eval(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray | None = None) -> Dict[str, float]:
        return evaluate_classification(y_true, y_pred, y_proba, task_type)

    return _eval


def get_metrics_for_task(task_type: TaskType) -> Dict[str, Any]:
    """Return full metrics config for task type."""
    return {
        "primary_metric": get_primary_metric(task_type),
        "scoring": get_scoring_string(task_type),
        "metric_names": get_all_metric_names(task_type),
        "recommendation_metrics": get_recommendation_metrics(task_type),
        "evaluate_fn": get_evaluate_fn(task_type),
    }
