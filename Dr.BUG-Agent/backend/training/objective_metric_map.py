"""Align workbench objective_metric values (lowercase/underscore) with Programmer metric names used for display."""

from __future__ import annotations

from typing import Tuple


def normalize_objective_token(raw: str) -> str:
    return str(raw or "").strip().lower().replace("-", "_")


def map_to_recommendation_metric(objective: str, ml_task_type: str) -> str:
    """
    Map objective_metric to the keys used by run_final_recommendation / recommended_sets_by_metric.
    Classification uses AUROC, AUPRC, F1-score, etc.; regression uses RMSE, MAE, and R2.
    """
    t = normalize_objective_token(objective)
    if ml_task_type == "regression":
        mapping = {
            "mse": "RMSE",
            "rmse": "RMSE",
            "mae": "MAE",
            "r2": "R2",
            "r2_score": "R2",
        }
        return mapping.get(t, "RMSE")
    mapping = {
        "auroc": "AUROC",
        "roc_auc": "AUROC",
        "auprc": "AUPRC",
        "average_precision": "AUPRC",
        "f1": "F1-score",
        "f1_score": "F1-score",
        "accuracy": "Accuracy",
        "acc": "Accuracy",
        "precision": "Precision",
        "recall": "Recall",
    }
    return mapping.get(t, "AUROC")


def validate_objective_supported(objective: str, ml_task_type: str) -> Tuple[bool, str]:
    """Return (False, reason) when not allowlisted; otherwise return (True, "")."""
    t = normalize_objective_token(objective)
    if ml_task_type == "regression":
        allowed = {"mse", "rmse", "mae", "r2", "r2_score"}
        if t not in allowed:
            return False, f"Unsupported objective_metric for regression: {objective!r}; use mse / rmse / mae / r2"
        return True, ""
    allowed = {
        "auroc",
        "roc_auc",
        "auprc",
        "average_precision",
        "f1",
        "f1_score",
        "accuracy",
        "acc",
        "precision",
        "recall",
    }
    if t not in allowed:
        return False, (
            f"Unsupported objective_metric for classification: {objective!r}; "
            "supported values are auroc / auprc / f1 / accuracy / precision / recall"
        )
    return True, ""
