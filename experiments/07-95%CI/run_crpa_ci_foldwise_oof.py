"""CRPA 95% CIs from within-fold bootstrap of fixed five-fold OOF predictions.

This script handles MIMIC-IV CRPA only. It preserves the formal CRPA models,
features, preprocessing, threshold, and original five CV splits. Models are fit
once to regenerate the fixed OOF predictions; bootstrap resampling never refits.
"""

import argparse
import json
import platform
import re
from pathlib import Path

import catboost
import lightgbm
import numpy as np
import pandas as pd
import sklearn
import xgboost
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from bootstrap_utils import (
    BootstrapPlan,
    CLASSIFICATION_METRICS,
    bootstrap_classification_metrics,
    percentile_interval,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUTPUT_DIR = HERE / "outputs" / "crpa_foldwise_oof"
DATA_PATH = REPO / "datasets" / "MIMIC-IV-CRPA" / "crpa_merged_master.csv"
NOTEBOOK_PATH = REPO / "experiments" / "04-MIMIC-IV-CRPA" / "01-death-search-FeatureSet.ipynb"
RESULTS_DIR = REPO / "results" / "crpa0411"
SELECTED_REFERENCE_PATH = RESULTS_DIR / "final_set_metrics-nogridsearch.csv"
TARGET = "mortality_28d_all_cause"
THRESHOLD = 0.5
BOOTSTRAP_SEED = 42
CI_LEVEL = 0.95

BINARY_FEATURES = [
    "gender_male", "diabetes", "hypertension", "heart_disease", "cerebrovascular_disease",
    "malignancy", "ckd", "chronic_liver_disease", "copd", "hiv_aids", "polymicrobial",
    "has_gram_negative_non_pa", "has_gram_positive_non_pa", "has_unknown_non_pa",
    "resp_invasivevent", "resp_supplementaloxygen", "resp_tracheostomy", "rrt_any",
    "carbapenem_exposure", "piptazo_exposure", "ceph_exposure", "fqn_exposure",
    "aminoglycoside_exposure", "other_abx_exposure",
]
CONTINUOUS_FEATURES = [
    "age", "sofa_closest_to_t0_plus_48h", "alt_worst_4d", "aptt_worst_4d", "ast_worst_4d",
    "bicarbonate_worst_4d", "bilirubin_total_worst_4d", "calcium_total_worst_4d",
    "creatinine_worst_4d", "dbp_worst_4d", "hemoglobin_worst_4d", "hr_worst_4d",
    "inr_worst_4d", "lactate_worst_4d", "magnesium_worst_4d", "map_worst_4d",
    "phosphate_worst_4d", "platelets_worst_4d", "potassium_worst_4d", "pt_worst_4d",
    "rbc_worst_4d", "rdw_worst_4d", "rr_worst_4d", "sbp_worst_4d", "sodium_worst_4d",
    "spo2_worst_4d", "temp_worst_4d", "wbc_worst_4d",
]
FULL_FEATURES = BINARY_FEATURES + CONTINUOUS_FEATURES
MEDICATION_FEATURES = [
    "carbapenem_exposure", "piptazo_exposure", "ceph_exposure",
    "fqn_exposure", "aminoglycoside_exposure", "other_abx_exposure",
]
SELECTED_FEATURES = {
    "cand_25": MEDICATION_FEATURES + [
        "bicarbonate_worst_4d", "age", "aptt_worst_4d", "ast_worst_4d",
        "resp_invasivevent", "creatinine_worst_4d", "hr_worst_4d",
    ],
    "cand_04": MEDICATION_FEATURES + [
        "pt_worst_4d", "lactate_worst_4d", "rr_worst_4d", "creatinine_worst_4d",
        "age", "rdw_worst_4d", "bicarbonate_worst_4d",
    ],
}
MODEL_NAMES = (
    "XGBoost", "LightGBM", "CatBoost", "RandomForest", "LogisticRegression"
)
CONFIGURATIONS = (
    ("FullFeature", "all_features", "all_features", FULL_FEATURES),
    ("Featureset", "cand_25", "cand_25", SELECTED_FEATURES["cand_25"]),
    ("Featureset", "cand_04", "cand_04", SELECTED_FEATURES["cand_04"]),
)


def validate_frozen_definitions():
    if len(FULL_FEATURES) != 52 or len(set(FULL_FEATURES)) != 52:
        raise RuntimeError("CRPA FullFeature must contain 52 unique columns")
    for candidate, columns in SELECTED_FEATURES.items():
        if len(columns) != 13 or len(set(columns)) != 13:
            raise RuntimeError(f"{candidate} must contain exactly 13 unique columns")
    forbidden = {"hemoglobin_worst_4d", "has_unknown_non_pa"}
    for candidate, columns in SELECTED_FEATURES.items():
        overlap = forbidden.intersection(columns)
        if overlap:
            raise RuntimeError(f"{candidate} contains non-formal selected columns: {sorted(overlap)}")


def get_models(scale_pos_weight):
    models = {
        "XGBoost": XGBClassifier(
            scale_pos_weight=scale_pos_weight, use_label_encoder=False,
            objective="binary:logistic", eval_metric="logloss", verbosity=0,
            random_state=42, n_jobs=1,
        ),
        "LightGBM": LGBMClassifier(
            class_weight="balanced", verbosity=-1, random_state=42, n_jobs=1
        ),
        "CatBoost": CatBoostClassifier(
            auto_class_weights="Balanced", verbose=0, loss_function="Logloss",
            allow_writing_files=False, random_state=42, thread_count=1,
        ),
        "RandomForest": RandomForestClassifier(
            class_weight="balanced", random_state=42, n_jobs=1
        ),
        "LogisticRegression": LogisticRegression(
            class_weight="balanced", random_state=42, max_iter=1000
        ),
    }
    if tuple(models) != MODEL_NAMES:
        raise RuntimeError(f"Unexpected CRPA model set: {tuple(models)}")
    return models


def create_pipeline(model, columns):
    binary = [column for column in columns if column in BINARY_FEATURES]
    continuous = [column for column in columns if column in CONTINUOUS_FEATURES]
    if len(binary) + len(continuous) != len(columns):
        known = set(BINARY_FEATURES) | set(CONTINUOUS_FEATURES)
        raise RuntimeError(f"Unknown CRPA columns: {[c for c in columns if c not in known]}")
    preprocessor = ColumnTransformer(
        transformers=[
            ("bin", Pipeline([("imputer", SimpleImputer(strategy="most_frequent"))]), binary),
            ("cont", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]), continuous),
        ],
        remainder="drop",
    )
    return Pipeline([("preprocessor", preprocessor), ("clf", clone(model))])


def evaluate_metrics(y, probability):
    prediction = (probability >= THRESHOLD).astype(int)
    if np.unique(y).size != 2:
        raise ValueError("All original CRPA validation folds must contain both classes")
    return {
        "Accuracy": float(accuracy_score(y, prediction)),
        "Precision": float(precision_score(y, prediction, zero_division=0)),
        "Recall": float(recall_score(y, prediction, zero_division=0)),
        "F1-score": float(f1_score(y, prediction, zero_division=0)),
        "AUROC": float(roc_auc_score(y, probability)),
        "AUPRC": float(average_precision_score(y, probability)),
    }


def load_data():
    validate_frozen_definitions()
    data = pd.read_csv(DATA_PATH)
    required = ["subject_id", TARGET, *FULL_FEATURES]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise RuntimeError(f"CRPA dataset is missing frozen columns: {missing}")
    y = data[TARGET].astype(int)
    if len(data) != 286 or int(y.sum()) != 80 or int((y == 0).sum()) != 206:
        raise RuntimeError("CRPA cohort must be N=286, death=80, survival=206")
    if data["subject_id"].nunique(dropna=False) != 286:
        raise RuntimeError("CRPA subject_id must contain 286 unique patients")
    return data, data[FULL_FEATURES].copy(), y


def generate_original_oof():
    data, x, y = load_data()
    models = get_models(float((y == 0).sum() / (y == 1).sum()))
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    prediction_frames = []
    metric_rows = []
    for feature_mode, candidate, feature_set, columns in CONFIGURATIONS:
        for model_name, model in models.items():
            probability = np.full(len(data), np.nan)
            prediction = np.full(len(data), -1, dtype=int)
            folds = np.full(len(data), -1, dtype=int)
            for fold, (train_index, validation_index) in enumerate(splitter.split(x[columns], y), 1):
                pipe = create_pipeline(model, list(columns))
                pipe.fit(x.iloc[train_index][columns], y.iloc[train_index].to_numpy(dtype=int))
                fold_probability = pipe.predict_proba(x.iloc[validation_index][columns])[:, 1]
                fold_prediction = (fold_probability >= THRESHOLD).astype(int)
                probability[validation_index] = fold_probability
                prediction[validation_index] = fold_prediction
                folds[validation_index] = fold
                values = evaluate_metrics(y.iloc[validation_index].to_numpy(dtype=int), fold_probability)
                for metric, estimate in values.items():
                    metric_rows.append({
                        "feature_mode": feature_mode, "candidate": candidate,
                        "feature_set": feature_set, "model": model_name, "fold": fold,
                        "metric": metric, "estimate": estimate,
                    })
            if np.isnan(probability).any() or (folds < 1).any():
                raise RuntimeError(f"Incomplete OOF predictions for {candidate}/{model_name}")
            if not np.array_equal(prediction, (probability >= THRESHOLD).astype(int)):
                raise RuntimeError(f"Prediction/probability mismatch for {candidate}/{model_name}")
            prediction_frames.append(pd.DataFrame({
                "patient_id": data["subject_id"].astype(str), "fold": folds,
                "y_true": y.to_numpy(dtype=int), "y_proba": probability,
                "y_pred": prediction, "feature_mode": feature_mode,
                "candidate": candidate, "feature_set": feature_set, "model": model_name,
                "threshold": THRESHOLD, "prediction_source": "external_5fold_oof",
            }))
    predictions = pd.concat(prediction_frames, ignore_index=True)
    fold_metrics = pd.DataFrame(metric_rows)
    sizes = predictions.groupby(["candidate", "model"]).size()
    unique = predictions.groupby(["candidate", "model"])["patient_id"].nunique()
    deaths = predictions.groupby(["candidate", "model"])["y_true"].sum()
    if len(sizes) != 15 or not (sizes == 286).all() or not (unique == 286).all():
        raise RuntimeError("Every CRPA candidate/model must contain 286 unique OOF patients")
    if not (deaths == 80).all():
        raise RuntimeError("Every CRPA candidate/model must contain 80 deaths")
    return predictions, fold_metrics


def notebook_output_text():
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    parts = []
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            value = output.get("text", output.get("data", {}).get("text/plain", ""))
            parts.append("".join(value) if isinstance(value, list) else str(value))
    return "\n".join(parts)


def fullfeature_reference():
    text = notebook_output_text()
    rows = []
    for model in MODEL_NAMES:
        matching = None
        for line in text.splitlines():
            if re.match(rf"^\s*{re.escape(model)}\s+", line):
                pairs = re.findall(r"(-?\d+\.\d+)\s*±\s*(\d+\.\d+)", line)
                if len(pairs) == 6:
                    matching = pairs
                    break
        if matching is None:
            raise RuntimeError(f"Could not parse FullFeature reference for {model}")
        for metric, (mean_text, sd_text) in zip(CLASSIFICATION_METRICS, matching):
            rows.append({
                "feature_mode": "FullFeature", "candidate": "all_features",
                "model": model, "metric": metric,
                "original_estimate": float(mean_text), "original_sd": float(sd_text),
                "display_decimals": len(mean_text.split(".")[1]),
                "source": NOTEBOOK_PATH.name,
            })
    reference = pd.DataFrame(rows)
    if len(reference) != 30:
        raise RuntimeError(f"FullFeature reference must contain 30 rows, got {len(reference)}")
    return reference


def selected_reference():
    reference = pd.read_csv(SELECTED_REFERENCE_PATH)
    if "model_name" in reference.columns:
        reference = reference.rename(columns={"model_name": "model"})
    required = {"set_id", "model", *CLASSIFICATION_METRICS}
    if not required.issubset(reference.columns):
        raise RuntimeError(f"Selected reference is missing required columns: {SELECTED_REFERENCE_PATH}")
    reference = reference[reference["set_id"].isin(SELECTED_FEATURES)].copy()
    if set(reference["set_id"]) != set(SELECTED_FEATURES):
        raise RuntimeError("Selected reference must contain cand_25 and cand_04")
    combinations = reference.groupby(["set_id", "model"]).size()
    if set(reference["model"]) != set(MODEL_NAMES) or len(combinations) != 10 or not (combinations == 1).all():
        raise RuntimeError("Selected reference must contain both candidates and all five models exactly once")
    reference = reference.melt(
        id_vars=["set_id", "model"], value_vars=list(CLASSIFICATION_METRICS),
        var_name="metric", value_name="original_estimate",
    ).rename(columns={"set_id": "candidate"})
    reference["feature_mode"] = "Featureset"
    reference["source"] = str(SELECTED_REFERENCE_PATH.relative_to(REPO))
    counts = reference.groupby("candidate").size().to_dict()
    if len(reference) != 60 or counts != {"cand_04": 30, "cand_25": 30}:
        raise RuntimeError(f"Selected reference must contain exactly 60 rows; observed {counts}")
    if reference["original_estimate"].isna().any():
        raise RuntimeError("Selected reference contains missing metric values")
    return reference


def audit_original_metrics(fold_metrics):
    keys = ["feature_mode", "candidate", "model", "metric"]
    current = fold_metrics.groupby(keys, as_index=False)["estimate"].agg(
        recomputed_5fold_mean="mean",
        recomputed_5fold_sd=lambda values: float(np.std(values, ddof=1)),
    )
    if len(current) != 90:
        raise RuntimeError(f"Recomputed original metrics must contain 90 rows, got {len(current)}")
    full = fullfeature_reference().merge(
        current[current["candidate"] == "all_features"], on=keys,
        how="outer", validate="one_to_one", indicator=True,
    )
    if len(full) != 30 or not (full["_merge"] == "both").all():
        raise RuntimeError("FullFeature audit coverage must be exactly 30 matched rows")
    full = full.drop(columns="_merge")
    full["mean_matches_original"] = [
        round(value, int(decimals)) == original
        for value, decimals, original in zip(
            full["recomputed_5fold_mean"], full["display_decimals"], full["original_estimate"]
        )
    ]
    full["sd_matches_original"] = [
        round(value, int(decimals)) == original
        for value, decimals, original in zip(
            full["recomputed_5fold_sd"], full["display_decimals"], full["original_sd"]
        )
    ]
    full["matches_original"] = full["mean_matches_original"] & full["sd_matches_original"]

    selected = selected_reference().merge(
        current[current["candidate"].isin(SELECTED_FEATURES)], on=keys,
        how="outer", validate="one_to_one", indicator=True,
    )
    if len(selected) != 60 or not (selected["_merge"] == "both").all():
        raise RuntimeError("Selected audit coverage must be exactly 60 matched rows")
    selected = selected.drop(columns="_merge")
    counts = selected.groupby(["candidate", "model"])["metric"].nunique()
    if len(counts) != 10 or not (counts == 6).all():
        raise RuntimeError("Every selected candidate/model must contain exactly six metrics")
    selected["matches_original"] = np.isclose(
        selected["recomputed_5fold_mean"], selected["original_estimate"], rtol=0, atol=1e-12
    )
    audit = pd.concat([full, selected], ignore_index=True, sort=False)
    audit["formal_reference_mean"] = audit["original_estimate"]
    audit["formal_reference_sd"] = audit["original_sd"]
    audit["original_5fold_mean"] = audit["recomputed_5fold_mean"]
    audit["original_5fold_sd"] = audit["recomputed_5fold_sd"]
    if len(audit) != 90 or audit[["original_estimate", "recomputed_5fold_mean"]].isna().any().any():
        raise RuntimeError("CRPA total audit must contain 90 complete rows")
    if not audit["matches_original"].all():
        bad = audit.loc[
            ~audit["matches_original"],
            ["candidate", "model", "metric", "original_estimate", "recomputed_5fold_mean"],
        ].copy()
        bad["difference"] = bad["recomputed_5fold_mean"] - bad["original_estimate"]
        raise RuntimeError("Original CRPA metrics failed reproduction:\n" + bad.to_string(index=False))
    return audit


def make_foldwise_plans(predictions, n_bootstrap, seed):
    if n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be positive")
    base = predictions[
        (predictions["candidate"] == "all_features") & (predictions["model"] == "XGBoost")
    ].sort_values("patient_id").reset_index(drop=True)
    identity = base[["patient_id", "fold", "y_true"]].reset_index(drop=True)
    for _, group in predictions.groupby(["candidate", "model"], sort=False):
        observed = group.sort_values("patient_id")[["patient_id", "fold", "y_true"]].reset_index(drop=True)
        if not observed.equals(identity):
            raise RuntimeError("OOF patient/fold assignments differ across configurations")

    fold_y = {
        fold: base.loc[base["fold"] == fold, "y_true"].to_numpy(dtype=int)
        for fold in range(1, 6)
    }
    rng = np.random.default_rng(seed)

    def draw(batch_size):
        return {
            fold: rng.multinomial(
                len(values), np.full(len(values), 1.0 / len(values)), size=batch_size
            ).astype(np.int16)
            for fold, values in fold_y.items()
        }

    first = draw(n_bootstrap)

    def joint_valid(weights):
        valid = np.ones(next(iter(weights.values())).shape[0], dtype=bool)
        for fold, matrix in weights.items():
            y = fold_y[fold]
            valid &= (matrix[:, y == 1].sum(axis=1) > 0) & (matrix[:, y == 0].sum(axis=1) > 0)
        return valid

    mask = joint_valid(first)
    valid_chunks = {fold: [matrix[mask]] for fold, matrix in first.items()}
    valid_count = int(mask.sum())
    rejected = int((~mask).sum())
    while valid_count < n_bootstrap:
        need = n_bootstrap - valid_count
        batch = draw(max(need, 256))
        batch_mask = joint_valid(batch)
        positions = np.flatnonzero(batch_mask)
        stop = int(positions[need - 1] + 1) if len(positions) >= need else len(batch_mask)
        rejected += int((~batch_mask[:stop]).sum())
        for fold, matrix in batch.items():
            valid_chunks[fold].append(matrix[:stop][batch_mask[:stop]])
        valid_count += min(need, int(batch_mask[:stop].sum()))

    plans = {
        fold: BootstrapPlan(
            weights_all=first[fold],
            weights_two_class=np.concatenate(valid_chunks[fold], axis=0)[:n_bootstrap],
            rejected_single_class=rejected,
            requested=n_bootstrap,
            seed=seed,
        )
        for fold in range(1, 6)
    }
    return plans, rejected


def compute_foldwise_ci(predictions, fold_metrics, audit, n_bootstrap):
    plans, rejected = make_foldwise_plans(predictions, n_bootstrap, BOOTSTRAP_SEED)
    point = fold_metrics.groupby(["candidate", "model", "metric"], as_index=False)["estimate"].agg(
        original_5fold_mean="mean",
        original_5fold_sd=lambda values: float(np.std(values, ddof=1)),
    )
    audited_means = audit[["candidate", "model", "metric", "original_5fold_mean"]]
    check = point.merge(
        audited_means, on=["candidate", "model", "metric"], suffixes=("", "_audit"),
        validate="one_to_one",
    )
    if len(check) != 90 or not np.allclose(
        check["original_5fold_mean"], check["original_5fold_mean_audit"], rtol=0, atol=1e-12
    ):
        raise RuntimeError("Method A point estimates differ from the audited original means")

    rows = []
    distributions = {}
    for (candidate, model), group in predictions.groupby(["candidate", "model"], sort=False):
        group = group.sort_values("patient_id")
        fold_distributions = {metric: [] for metric in CLASSIFICATION_METRICS}
        for fold in range(1, 6):
            fold_data = group[group["fold"] == fold]
            _, distribution, _ = bootstrap_classification_metrics(
                fold_data["y_true"].to_numpy(dtype=int),
                fold_data["y_proba"].to_numpy(dtype=float),
                THRESHOLD,
                plans[fold],
            )
            for metric in CLASSIFICATION_METRICS:
                fold_distributions[metric].append(distribution[metric])
        for metric in CLASSIFICATION_METRICS:
            values = np.mean(np.vstack(fold_distributions[metric]), axis=0)
            lower, upper = percentile_interval(values, CI_LEVEL)
            point_row = point[
                (point["candidate"] == candidate)
                & (point["model"] == model)
                & (point["metric"] == metric)
            ].iloc[0]
            rejected_metric = rejected if metric in {"AUROC", "AUPRC"} else 0
            rows.append({
                "candidate": candidate, "model": model, "metric": metric, "n": 286,
                "original_5fold_mean": float(point_row["original_5fold_mean"]),
                "original_5fold_sd": float(point_row["original_5fold_sd"]),
                "estimate": float(point_row["original_5fold_mean"]),
                "ci_lower": lower, "ci_upper": upper,
                "bootstrap_replicates_requested": n_bootstrap,
                "bootstrap_replicates_valid": int(values.size),
                "bootstrap_replicates_rejected": rejected_metric,
                "bootstrap_seed": BOOTSTRAP_SEED,
                "bootstrap_method": "within_fold_patient_bootstrap_of_fixed_oof_predictions",
                "estimator": "mean_of_5fold_metrics",
            })
            distributions[f"{candidate}__{model}__{metric}".replace("-", "_")] = values.astype(np.float32)
    results = pd.DataFrame(rows)
    if len(results) != 90 or not np.array_equal(
        results["estimate"].to_numpy(), results["original_5fold_mean"].to_numpy()
    ):
        raise RuntimeError("Method A output must contain 90 rows with the original means as estimates")
    metadata = {
        "method": "within_fold_patient_bootstrap_of_fixed_oof_predictions",
        "estimator": "mean_of_5fold_metrics",
        "interpretation": "conditional patient-level uncertainty around fixed original CV splits and fixed OOF predictions",
        "models_refit_during_bootstrap": False,
        "n_bootstrap": n_bootstrap,
        "seed": BOOTSTRAP_SEED,
        "ci_level": CI_LEVEL,
        "threshold": THRESHOLD,
        "rank_metric_rejected_replicates": rejected,
        "common_resampling_plan": "same within-fold multinomial patient counts for all configurations and models",
        "single_class_policy": "reject the full five-fold replicate for AUROC and AUPRC if any resampled fold is single-class",
        "dataset": str(DATA_PATH.relative_to(REPO)),
        "reference_results": str(RESULTS_DIR.relative_to(REPO)),
        "cohort": {"n": 286, "death": 80, "survival": 206, "unique_subject_id": 286},
        "software_versions": {
            "Python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "scikit-learn": sklearn.__version__,
            "xgboost": xgboost.__version__, "lightgbm": lightgbm.__version__,
            "catboost": catboost.__version__,
        },
    }
    return results, distributions, metadata


def run(n_bootstrap):
    predictions, fold_metrics = generate_original_oof()
    audit = audit_original_metrics(fold_metrics)
    results, distributions, metadata = compute_foldwise_ci(
        predictions, fold_metrics, audit, n_bootstrap
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT_DIR / "crpa_oof_predictions.csv", index=False)
    fold_metrics.to_csv(OUTPUT_DIR / "crpa_original_5fold_metrics.csv", index=False)
    results.to_csv(OUTPUT_DIR / "crpa_foldwise_bootstrap_95ci.csv", index=False)
    audit.to_csv(OUTPUT_DIR / "crpa_point_estimate_consistency.csv", index=False)
    np.savez_compressed(OUTPUT_DIR / "crpa_foldwise_bootstrap_distributions.npz", **distributions)
    (OUTPUT_DIR / "crpa_foldwise_bootstrap_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"CRPA original point-estimate audit: {len(audit)}/90 matched")
    print(f"Method A CI rows: {len(results)}")
    print(f"Outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    args = parser.parse_args()
    run(args.n_bootstrap)
