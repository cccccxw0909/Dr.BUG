"""Reproducible patient-level percentile bootstrap utilities.

The functions in this module operate on already-generated patient-level
predictions.  They never refit a model, select a feature set, or change a
classification threshold.
"""

from collections import namedtuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


CLASSIFICATION_METRICS = (
    "Accuracy",
    "Precision",
    "Recall",
    "F1-score",
    "AUROC",
    "AUPRC",
)
REGRESSION_METRICS = ("MSE", "PCC")


BootstrapPlan = namedtuple(
    "BootstrapPlan",
    ["weights_all", "weights_two_class", "rejected_single_class", "requested", "seed"],
)
BootstrapPlan.__doc__ = "Bootstrap multiplicities shared across models for one patient cohort."


def classification_point_estimates(y_true, y_proba, threshold):
    y = np.asarray(y_true, dtype=int).ravel()
    p = np.asarray(y_proba, dtype=float).ravel()
    pred = (p >= threshold).astype(int)
    if y.size != p.size or y.size == 0:
        raise ValueError("y_true and y_proba must be non-empty and equal length")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("All classification probabilities must be in [0, 1]")
    if np.unique(y).size != 2:
        raise ValueError("Point-estimate AUROC/AUPRC require two outcome classes")
    return {
        "Accuracy": float(accuracy_score(y, pred)),
        "Precision": float(precision_score(y, pred, zero_division=0)),
        "Recall": float(recall_score(y, pred, zero_division=0)),
        "F1-score": float(f1_score(y, pred, zero_division=0)),
        "AUROC": float(roc_auc_score(y, p)),
        "AUPRC": float(average_precision_score(y, p)),
    }


def regression_point_estimates(y_true, y_pred):
    y = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(y_pred, dtype=float).ravel()
    if y.size != p.size or y.size == 0:
        raise ValueError("y_true and y_pred must be non-empty and equal length")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("Regression inputs must be finite")
    mse = float(np.mean((p - y) ** 2))
    pcc = float(np.corrcoef(y, p)[0, 1]) if np.std(y) > 0 and np.std(p) > 0 else np.nan
    return {"MSE": mse, "PCC": pcc}


def make_classification_plan(y_true, n_bootstrap=10_000, seed=42):
    """Create bootstrap weights, retaining 10,000 valid two-class draws.

    All first ``n_bootstrap`` draws are retained for threshold-based metrics.
    Single-class draws are excluded only from AUROC/AUPRC and replacement draws
    are generated until those metrics also have ``n_bootstrap`` valid values.
    """

    y = np.asarray(y_true, dtype=int).ravel()
    if y.size == 0 or np.unique(y).size != 2:
        raise ValueError("Classification bootstrap requires a non-empty binary outcome")
    rng = np.random.default_rng(seed)
    probs = np.full(y.size, 1.0 / y.size)
    first = rng.multinomial(y.size, probs, size=n_bootstrap).astype(np.int16)

    def is_two_class(weights):
        pos = weights[:, y == 1].sum(axis=1)
        neg = weights[:, y == 0].sum(axis=1)
        return (pos > 0) & (neg > 0)

    valid_chunks = [first[is_two_class(first)]]
    rejected = int(n_bootstrap - len(valid_chunks[0]))
    valid_count = len(valid_chunks[0])
    while valid_count < n_bootstrap:
        need = n_bootstrap - valid_count
        batch = rng.multinomial(y.size, probs, size=max(need, 256)).astype(np.int16)
        mask = is_two_class(batch)
        valid_positions = np.flatnonzero(mask)
        if valid_positions.size >= need:
            stop = int(valid_positions[need - 1] + 1)
            rejected += int((~mask[:stop]).sum())
            valid_chunks.append(batch[:stop][mask[:stop]])
            valid_count += need
        else:
            rejected += int((~mask).sum())
            valid_chunks.append(batch[mask])
            valid_count += int(valid_positions.size)
    two_class = np.concatenate(valid_chunks, axis=0)[:n_bootstrap]
    return BootstrapPlan(first, two_class, rejected, n_bootstrap, seed)


def make_regression_plan(n_patients, n_bootstrap=10_000, seed=42):
    if n_patients <= 0:
        raise ValueError("n_patients must be positive")
    rng = np.random.default_rng(seed)
    probs = np.full(n_patients, 1.0 / n_patients)
    weights = rng.multinomial(n_patients, probs, size=n_bootstrap).astype(np.int16)
    return BootstrapPlan(weights, None, 0, n_bootstrap, seed)


def _group_sums_by_score(weights, y, scores, descending):
    order = np.argsort(scores, kind="mergesort")
    if descending:
        order = order[::-1]
    sorted_scores = scores[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_scores) != 0) + 1]
    sorted_weights = weights[:, order].astype(float, copy=False)
    sorted_y = y[order].astype(float)
    pos = np.add.reduceat(sorted_weights * sorted_y, starts, axis=1)
    neg = np.add.reduceat(sorted_weights * (1.0 - sorted_y), starts, axis=1)
    return pos, neg


def _weighted_auroc(weights, y, scores):
    pos_group, neg_group = _group_sums_by_score(weights, y, scores, descending=False)
    neg_before = np.cumsum(neg_group, axis=1) - neg_group
    numerator = np.sum(pos_group * (neg_before + 0.5 * neg_group), axis=1)
    denominator = pos_group.sum(axis=1) * neg_group.sum(axis=1)
    return numerator / denominator


def _weighted_average_precision(weights, y, scores):
    pos_group, neg_group = _group_sums_by_score(weights, y, scores, descending=True)
    cum_pos = np.cumsum(pos_group, axis=1)
    cum_total = np.cumsum(pos_group + neg_group, axis=1)
    precision = np.divide(cum_pos, cum_total, out=np.zeros_like(cum_pos), where=cum_total > 0)
    total_pos = pos_group.sum(axis=1)
    return np.sum(precision * pos_group, axis=1) / total_pos


def bootstrap_classification_metrics(y_true, y_proba, threshold, plan):
    y = np.asarray(y_true, dtype=int).ravel()
    p = np.asarray(y_proba, dtype=float).ravel()
    point = classification_point_estimates(y, p, threshold)
    if plan.weights_all.shape[1] != y.size or plan.weights_two_class is None:
        raise ValueError("Bootstrap plan does not match classification input")

    pred = (p >= threshold).astype(int)
    weights = plan.weights_all.astype(float, copy=False)
    tp = weights[:, (y == 1) & (pred == 1)].sum(axis=1)
    tn = weights[:, (y == 0) & (pred == 0)].sum(axis=1)
    fp = weights[:, (y == 0) & (pred == 1)].sum(axis=1)
    fn = weights[:, (y == 1) & (pred == 0)].sum(axis=1)
    accuracy = (tp + tn) / y.size
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(2 * tp, 2 * tp + fp + fn, out=np.zeros_like(tp), where=(2 * tp + fp + fn) > 0)

    two_class = plan.weights_two_class
    distributions = {
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1,
        "AUROC": _weighted_auroc(two_class, y, p),
        "AUPRC": _weighted_average_precision(two_class, y, p),
    }
    metric_meta = {
        metric: {
            "valid": int(values.size),
            "rejected_single_class": int(plan.rejected_single_class if metric in {"AUROC", "AUPRC"} else 0),
        }
        for metric, values in distributions.items()
    }
    return point, distributions, metric_meta


def bootstrap_regression_metrics(y_true, y_pred, plan):
    y = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(y_pred, dtype=float).ravel()
    point = regression_point_estimates(y, p)
    if plan.weights_all.shape[1] != y.size:
        raise ValueError("Bootstrap plan does not match regression input")
    weights = plan.weights_all.astype(float, copy=False)
    n = weights.sum(axis=1)
    mse = (weights * ((p - y) ** 2)).sum(axis=1) / n
    mean_y = (weights * y).sum(axis=1) / n
    mean_p = (weights * p).sum(axis=1) / n
    dy = y[None, :] - mean_y[:, None]
    dp = p[None, :] - mean_p[:, None]
    cov = (weights * dy * dp).sum(axis=1)
    var_y = (weights * dy * dy).sum(axis=1)
    var_p = (weights * dp * dp).sum(axis=1)
    denom = np.sqrt(var_y * var_p)
    pcc = np.divide(cov, denom, out=np.full_like(cov, np.nan), where=denom > 0)
    valid_pcc = pcc[np.isfinite(pcc)]
    rejected_pcc = int(pcc.size - valid_pcc.size)
    if valid_pcc.size < plan.requested:
        raise RuntimeError("Fewer than requested valid PCC bootstrap replicates")
    pcc = valid_pcc[: plan.requested]
    distributions = {"MSE": mse, "PCC": pcc}
    metric_meta = {
        "MSE": {"valid": int(mse.size), "rejected_zero_variance": 0},
        "PCC": {
            "valid": int(pcc.size),
            "rejected_zero_variance": rejected_pcc,
        },
    }
    return point, distributions, metric_meta


def percentile_interval(values, ci_level=0.95):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return np.nan, np.nan
    alpha = 1.0 - ci_level
    lower, upper = np.quantile(values, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lower), float(upper)
