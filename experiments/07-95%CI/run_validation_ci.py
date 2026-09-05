"""Generate validation 95% CIs without changing the original protocols."""

import argparse
import json
import platform
import re
import warnings
from pathlib import Path

import catboost
import lightgbm
import numpy as np
import pandas as pd
import scipy
import sklearn
import xgboost
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

from bootstrap_utils import (
    CLASSIFICATION_METRICS,
    REGRESSION_METRICS,
    bootstrap_classification_metrics,
    bootstrap_regression_metrics,
    make_classification_plan,
    make_regression_plan,
    percentile_interval,
    regression_point_estimates,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUTPUT_DIR = HERE / "outputs" / "validation"
CI_LEVEL = 0.95
BOOTSTRAP_SEED = 42
CLASSIFICATION_THRESHOLD = 0.5
MODEL_NAMES = (
    "XGBoost",
    "LightGBM",
    "CatBoost",
    "RandomForest",
    "LogisticRegression",
    "SVM",
    "KNN",
)

TEMPORAL_CONFIGS = {
    "clinical_efficacy": {
        "target": "Clinical_outcome",
        "label": "Clinical efficacy",
        "notebook_stem": "01-predict-clinical_efficacy",
        "candidates": {
            "cand_21": ["Oxygen_concentration", "Comorbidity", "eGFR1", "PLT", "CRP1", "Cr_baseline", "Age", "TB"],
            "cand_38": ["Oxygen_concentration", "Coinfection_Fungi", "resistance_CFP-SUL", "Infection_HAP", "Infection_VAP", "resistance_KAN", "eGFR1"],
            "cand_39": ["Oxygen_concentration", "resistance_CFP-SUL", "Infection_HAP", "Infection_VAP", "eGFR1"],
            "cand_40": ["Oxygen_concentration", "resistance_CFP-SUL", "Infection_HAP", "resistance_KAN", "eGFR1"],
        },
        "candidate_labels": {"cand_21": "feature-setA", "cand_38": "feature-setB", "cand_39": "feature-setC", "cand_40": "feature-setD"},
    },
    "survival": {
        "target": "Survival",
        "label": "Survival",
        "notebook_stem": "02-predict-survival",
        "candidates": {
            "cand_16": ["PLT", "eGFR1", "Comorbidity", "PCT1", "Age", "ALB", "N_percent", "Oxygen_concentration", "Cr_baseline"],
            "cand_37": ["Comorbidity", "PLT", "Age", "N_percent", "CRP1", "Oxygen_concentration", "Immunosuppression", "Cr_baseline"],
        },
        "candidate_labels": {"cand_16": "feature-setA", "cand_37": "feature-setB"},
    },
    "polymyxin_resistance": {
        "target": "Target_Polymyxin",
        "label": "Polymyxin resistance",
        "notebook_stem": "03-predict-polymyxin_resistance",
        "candidates": {
            "cand_04": ["Comorbidity", "Age", "PLT", "AST", "ALB", "CRP1", "N_percent"],
            "cand_05": ["Comorbidity", "Age", "PLT", "ALB", "WBC", "CRP1", "N_percent"],
            "cand_11": ["Comorbidity", "Age", "AST", "PLT", "CRP1", "WBC", "N_percent"],
            "cand_27": ["Comorbidity", "Age", "WBC", "L_count"],
            "cand_40": ["PLT", "CRP1"],
        },
        "candidate_labels": {"cand_04": "feature-setA", "cand_05": "feature-setB", "cand_11": "feature-setC", "cand_27": "feature-setD", "cand_40": "feature-setE"},
    },
}


# MIMIC-IV CRPA external-cohort workflow.
# These definitions are frozen from 01-death-search-FeatureSet.ipynb and
# the formal results/crpa0411 run; SHAP and feature selection are not repeated.
CRPA_DATA_PATH = REPO / "datasets" / "MIMIC-IV-CRPA" / "crpa_merged_master.csv"
CRPA_NOTEBOOK_PATH = (
    REPO / "experiments" / "04-MIMIC-IV-CRPA" / "01-death-search-FeatureSet.ipynb"
)
CRPA_RESULTS_DIR = REPO / "results" / "crpa0411"
CRPA_SELECTED_REFERENCE_PATH = CRPA_RESULTS_DIR / "final_set_metrics-nogridsearch.csv"
CRPA_TARGET = "mortality_28d_all_cause"
CRPA_BINARY = [
    "gender_male", "diabetes", "hypertension", "heart_disease", "cerebrovascular_disease",
    "malignancy", "ckd", "chronic_liver_disease", "copd", "hiv_aids", "polymicrobial",
    "has_gram_negative_non_pa", "has_gram_positive_non_pa", "has_unknown_non_pa",
    "resp_invasivevent", "resp_supplementaloxygen", "resp_tracheostomy", "rrt_any",
    "carbapenem_exposure", "piptazo_exposure", "ceph_exposure", "fqn_exposure",
    "aminoglycoside_exposure", "other_abx_exposure",
]
CRPA_CONTINUOUS = [
    "age", "sofa_closest_to_t0_plus_48h", "alt_worst_4d", "aptt_worst_4d", "ast_worst_4d",
    "bicarbonate_worst_4d", "bilirubin_total_worst_4d", "calcium_total_worst_4d",
    "creatinine_worst_4d", "dbp_worst_4d", "hemoglobin_worst_4d", "hr_worst_4d",
    "inr_worst_4d", "lactate_worst_4d", "magnesium_worst_4d", "map_worst_4d",
    "phosphate_worst_4d", "platelets_worst_4d", "potassium_worst_4d", "pt_worst_4d",
    "rbc_worst_4d", "rdw_worst_4d", "rr_worst_4d", "sbp_worst_4d", "sodium_worst_4d",
    "spo2_worst_4d", "temp_worst_4d", "wbc_worst_4d",
]
CRPA_ALL_FEATURES = CRPA_BINARY + CRPA_CONTINUOUS
CRPA_MEDICATION_FEATURES = [
    "carbapenem_exposure", "piptazo_exposure", "ceph_exposure",
    "fqn_exposure", "aminoglycoside_exposure", "other_abx_exposure",
]
CRPA_SELECTED_FEATURES = {
    "cand_25": CRPA_MEDICATION_FEATURES + [
        "bicarbonate_worst_4d", "age", "aptt_worst_4d", "ast_worst_4d",
        "resp_invasivevent", "creatinine_worst_4d", "hr_worst_4d",
    ],
    "cand_04": CRPA_MEDICATION_FEATURES + [
        "pt_worst_4d", "lactate_worst_4d", "rr_worst_4d",
        "creatinine_worst_4d", "age", "rdw_worst_4d", "bicarbonate_worst_4d",
    ],
}
CRPA_MODEL_NAMES = (
    "XGBoost",
    "LightGBM",
    "CatBoost",
    "RandomForest",
    "LogisticRegression",
)

for _candidate, _columns in CRPA_SELECTED_FEATURES.items():
    if len(_columns) != 13:
        raise RuntimeError(f"{_candidate} must contain exactly 13 frozen CRPA columns")
    if len(set(_columns)) != 13:
        raise RuntimeError(f"{_candidate} contains duplicate frozen CRPA columns")


def get_classification_models(scale_pos_weight):
    return {
        "XGBoost": XGBClassifier(scale_pos_weight=scale_pos_weight, use_label_encoder=False, objective="binary:logistic", eval_metric="logloss", verbosity=0, random_state=42, n_jobs=1),
        "LightGBM": LGBMClassifier(class_weight="balanced", verbosity=-1, random_state=42, n_jobs=1),
        "CatBoost": CatBoostClassifier(auto_class_weights="Balanced", verbose=0, loss_function="Logloss", allow_writing_files=False, random_state=42, thread_count=1),
        "RandomForest": RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=1),
        "LogisticRegression": LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000),
        "SVM": SVC(class_weight="balanced", random_state=42, probability=True),
        "KNN": KNeighborsClassifier(weights="distance", n_jobs=1),
    }


def is_tree(model_name):
    return model_name in {"XGBoost", "LightGBM", "CatBoost", "RandomForest"}


def create_classification_pipeline(model, model_name):
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if not is_tree(model_name):
        steps.append(("scaler", StandardScaler()))
    steps.append(("clf", clone(model)))
    return Pipeline(steps)


def feature_selection(df, target):
    poly = ["colistin_cms_daily_freq", "polymyxin_b_daily_freq", "colistin_sulfate_daily_freq"]
    combination = [
        "carbapenem_daily_dose", "sulbactam_daily_dose", "tigecycline_daily_dose",
        "minocycline_daily_dose", "vancomycin_daily_dose", "eravacycline_daily_dose",
        "aminoglycoside_daily_dose",
    ]
    medication = poly + combination
    time = ["Pre_Hospital_Days", "Pre_ICU_Days"]
    base = ["Age", "Gender", "BMI"]
    comorb = [
        "Diabetes Mellitus", "Hypertension", "Heart Disease", "Stroke", "Malignant Tumor",
        "Chronic Kidney Disease", "Chronic Liver Disease", "COPD", "Comorb_other",
    ]
    df = df.copy()
    df[comorb] = df[comorb].fillna(0)
    df["Comorb_count"] = df[comorb].sum(axis=1)
    comorb = comorb + ["Comorb_count"]
    immuno = [
        "Use immunosuppressive agents", "Neutrophil Reduction", "HIV/AIDS",
        "Post-Transplant Status", "Chemotherapy/Radiation", "immuno_Other",
    ]
    support = ["Resp_support", "Oxygen_concentration"]
    labs = ["WBC", "N_percent", "L_count", "PLT", "CRP1", "PCT1", "D-d", "Cr_baseline", "eGFR1", "RRT", "ALT", "AST", "TB", "ALB"]
    infection = ["Infection_HAP", "Infection_VAP"]
    coinfection = ["Coinfection_G_Pos", "Coinfection_G_Neg", "Coinfection_Fungi"]
    df[coinfection] = df[coinfection].fillna(0).astype(int)
    infection += coinfection
    resistance = ["resistance_SXT", "resistance_KAN", "resistance_MIN", "resistance_TGC", "resistance_CFP-SUL", "resistance_TOB"]
    mapping = {"R": 1, "I": 1, "S": 0}
    for column in resistance:
        if column in df.columns:
            values = df[column].astype(str).str.strip().str.upper()
            df[column] = pd.to_numeric(values.map(mapping), errors="coerce")
    groups = {
        "Comorbidity": [column for column in comorb if column in df.columns],
        "Immunosuppression": [column for column in immuno if column in df.columns],
    }
    if target == "Target_Polymyxin":
        columns = base + time + comorb + immuno + support + labs
        include_medication = False
    else:
        columns = base + comorb + immuno + support + labs + infection + resistance + medication
        include_medication = True
    return [column for column in columns if column in df.columns], df, medication, groups, include_medication


def expand_featureset(features, available, groups):
    available = set(available)
    expanded = []
    for feature in features:
        if feature in groups:
            expanded.extend(column for column in groups[feature] if column in available)
        elif feature in available:
            expanded.append(feature)
    return list(dict.fromkeys(expanded))


def _prepare_temporal_task(task_key, data_variant="datasets"):
    config = TEMPORAL_CONFIGS[task_key]
    data_dir = REPO / data_variant
    train = pd.read_csv(data_dir / "train_set.csv", encoding="gbk")
    external = pd.read_csv(data_dir / "external-1.csv", encoding="gbk")
    target = config["target"]
    if target == "Target_Polymyxin":
        train = train[train["Polymyxin_MIC"].notna()].copy()
        external = external[external["Polymyxin_MIC"].notna()].copy()
        train[target] = (train["Polymyxin_MIC"] >= 2).astype(int)
        external[target] = (external["Polymyxin_MIC"] >= 2).astype(int)
    else:
        train = train[train[target].notna()].copy()
        external = external[external[target].notna()].copy()
        train[target] = train[target].astype(int)
        external[target] = external[target].astype(int)
    feature_columns, train, medication, groups, _ = feature_selection(train, target)
    _, external, _, _, _ = feature_selection(external, target)
    x_train = train[feature_columns]
    common = [column for column in feature_columns if column in external.columns]
    missing = [column for column in feature_columns if column not in external.columns]
    x_external = external[common].copy()
    for column in missing:
        x_external[column] = x_train[column].median()
    x_external = x_external[feature_columns]
    y_train = train[target]
    y_external = external[target].to_numpy(dtype=int)
    return config, train, external, x_train, y_train, x_external, y_external, medication, groups


def generate_temporal_predictions():
    frames = []
    for task_key in TEMPORAL_CONFIGS:
        config, _, external, x_train, y_train, x_external, y_external, medication, groups = _prepare_temporal_task(task_key, "datasets")
        configurations = []
        for candidate, features in config["candidates"].items():
            selected = expand_featureset(features, x_train.columns, groups)
            if task_key != "polymyxin_resistance":
                selected = medication + selected
            selected = list(dict.fromkeys(selected))
            configurations.append(("Featureset", candidate, config["candidate_labels"][candidate], selected, "datasets", external, x_train, y_train, x_external, y_external))

        full_variant = "datasets"
        _, _, full_external, full_x_train, full_y_train, full_x_external, full_y_external, _, _ = _prepare_temporal_task(task_key, full_variant)
        configurations.insert(0, ("FullFeature", "all_features", "all_features", full_x_train.columns.tolist(), full_variant, full_external, full_x_train, full_y_train, full_x_external, full_y_external))

        for feature_mode, candidate, feature_set, columns, data_variant, config_external, config_x_train, config_y_train, config_x_external, config_y_external in configurations:
            scale_pos_weight = float((config_y_train == 0).sum() / (config_y_train == 1).sum())
            models = get_classification_models(scale_pos_weight)
            for model_name, model in models.items():
                pipe = create_classification_pipeline(model, model_name)
                pipe.fit(config_x_train[columns], config_y_train)
                proba = pipe.predict_proba(config_x_external[columns])[:, 1].astype(float)
                pred = (proba >= CLASSIFICATION_THRESHOLD).astype(int)
                frames.append(pd.DataFrame({
                    "cohort": "temporal_external-1",
                    "task": task_key,
                    "feature_mode": feature_mode,
                    "candidate": candidate,
                    "feature_set": feature_set,
                    "model": model_name,
                    "patient_id": [f"external-1_row_{int(index):04d}" for index in config_external.index],
                    "y_true": config_y_external,
                    "y_proba": proba,
                    "y_pred": pred,
                    "threshold": CLASSIFICATION_THRESHOLD,
                    "prediction_source": "temporal_locked_model",
                    "data_version": data_variant,
                }))
    result = pd.concat(frames, ignore_index=True)
    expected_counts = {"clinical_efficacy": 111, "survival": 111, "polymyxin_resistance": 111}
    observed = result.groupby(["task", "feature_mode", "candidate", "model"]).size()
    for (task, _, _, _), count in observed.items():
        if count != expected_counts[task]:
            raise RuntimeError(f"Unexpected temporal prediction count for {task}: {count}")
    if not np.allclose(result["threshold"], CLASSIFICATION_THRESHOLD):
        raise RuntimeError("Temporal classification threshold changed from 0.5")
    return result


def load_mimic_predictions():
    path = REPO / "experiments" / "03-MIMIC-IV-CRAB" / "results" / "mimic-crab" / "survival_loocv_pred_for_confusion_matrix.csv"
    data = pd.read_csv(path)
    data["cohort"] = "external_mimic_crab"
    data["task"] = "survival"
    data["feature_mode"] = "Featureset"
    data["feature_set"] = data["candidate"].str.replace("feature-set", "feature-set", regex=False)
    data["patient_id"] = data["subject_id"].astype(str) + "|" + data["hadm_id"].astype(str)
    data["prediction_source"] = "external_loocv_oof"
    data["data_version"] = "datasets/MIMIC-IV-CRAB/mimicset0227.csv"
    columns = [
        "cohort", "task", "feature_mode", "candidate", "feature_set", "model", "patient_id",
        "y_true", "y_proba", "y_pred", "threshold", "prediction_source", "data_version",
    ]
    result = data[columns].copy()
    group_sizes = result.groupby(["candidate", "model"]).size()
    unique_patients = result.groupby(["candidate", "model"])["patient_id"].nunique()
    if not (group_sizes == 42).all() or not (unique_patients == 42).all():
        raise RuntimeError("MIMIC LOOCV predictions are not 42 unique patients per candidate/model")
    if result.groupby(["candidate", "model"])["y_true"].sum().nunique() != 1 or int(result.groupby(["candidate", "model"])["y_true"].sum().iloc[0]) != 33:
        raise RuntimeError("MIMIC class distribution is not 33 survival / 9 death")
    if not np.allclose(result["threshold"], CLASSIFICATION_THRESHOLD):
        raise RuntimeError("MIMIC classification threshold changed from 0.5")
    expected_y_pred = (result["y_proba"].to_numpy(dtype=float) >= result["threshold"].to_numpy(dtype=float)).astype(int)
    if not np.array_equal(result["y_pred"].to_numpy(dtype=int), expected_y_pred):
        raise RuntimeError("Saved MIMIC y_pred is inconsistent with y_proba and threshold")
    return result


def load_treatment_predictions():
    path = REPO / "experiments" / "02-Temporal-external-validation" / "results" / "regression_MSE-mse0430" / "regression_predictions_long0430.csv"
    data = pd.read_csv(path)
    data = data[(data["dataset"] == "External-1") & (data["pred_type"] == "External")].copy()
    data["cohort"] = "temporal_external-1"
    data["task"] = "treatment_duration"
    data["candidate"] = np.where(data["feature_mode"] == "FeatureSet", "mse_feature-setA", "all_features")
    data["feature_set"] = np.where(data["feature_mode"] == "FeatureSet", "feature-setA", "all_features")
    data["feature_mode"] = data["feature_mode"].replace({"AllFeatures": "FullFeature"})
    data["patient_id"] = data["sample_id"].map(lambda value: f"external-1_row_{int(value):04d}")
    data["prediction_source"] = "temporal_locked_model"
    data["data_version"] = "existing_saved_predictions_from_regression_MSE-mse0430"
    return data[["cohort", "task", "feature_mode", "candidate", "feature_set", "model", "patient_id", "y_true", "y_pred", "prediction_source", "data_version"]]


def get_crpa_models(scale_pos_weight):
    """Exact five model families used in the original MIMIC-IV CRPA notebook."""
    return {
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


def create_crpa_pipeline(model, model_name, columns):
    """Reproduce the CRPA notebook preprocessing exactly.

    Binary variables: most-frequent imputation.
    Continuous variables: median imputation followed by StandardScaler.
    The continuous scaling step is retained for every model family because this
    is how the original CRPA notebook was evaluated.
    """
    binary_columns = [column for column in columns if column in CRPA_BINARY]
    continuous_columns = [column for column in columns if column in CRPA_CONTINUOUS]
    unknown = [
        column for column in columns
        if column not in set(CRPA_BINARY) | set(CRPA_CONTINUOUS)
    ]
    if unknown:
        raise RuntimeError(f"Unexpected CRPA columns outside the frozen schema: {unknown}")

    binary_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="most_frequent"))]
    )
    continuous_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("bin", binary_transformer, binary_columns),
            ("cont", continuous_transformer, continuous_columns),
        ],
        remainder="drop",
    )
    return Pipeline([("preprocessor", preprocessor), ("clf", clone(model))])


def _prepare_crpa():
    data = pd.read_csv(CRPA_DATA_PATH)
    missing = [
        column for column in ["subject_id", CRPA_TARGET, *CRPA_ALL_FEATURES]
        if column not in data.columns
    ]
    if missing:
        raise RuntimeError(f"CRPA input is missing frozen notebook columns: {missing}")

    x = data[CRPA_ALL_FEATURES].copy()
    y = data[CRPA_TARGET].astype(int).copy()
    if len(data) != 286 or int((y == 1).sum()) != 80 or int((y == 0).sum()) != 206:
        raise RuntimeError(
            "CRPA cohort does not match the original notebook "
            f"(expected N=286, death=80, survival=206; observed "
            f"N={len(data)}, death={(y == 1).sum()}, survival={(y == 0).sum()})"
        )
    if data["subject_id"].nunique(dropna=False) != 286:
        raise RuntimeError("CRPA subject_id must identify exactly 286 unique patients")
    if len(CRPA_ALL_FEATURES) != 52 or len(set(CRPA_ALL_FEATURES)) != 52:
        raise RuntimeError("CRPA FullFeature definition must contain 52 unique columns")
    for candidate, columns in CRPA_SELECTED_FEATURES.items():
        unavailable = [column for column in columns if column not in x.columns]
        if unavailable:
            raise RuntimeError(f"{candidate} contains unavailable CRPA columns: {unavailable}")
    return data, x, y


def generate_crpa_predictions():
    """Generate one held-out 5-fold OOF probability per CRPA patient/configuration."""
    data, x, y = _prepare_crpa()
    scale_pos_weight = float((y == 0).sum() / (y == 1).sum())
    models = get_crpa_models(scale_pos_weight)
    if tuple(models) != CRPA_MODEL_NAMES:
        raise RuntimeError(f"Unexpected CRPA model set: {tuple(models)}")
    configurations = [
        ("FullFeature", "all_features", "all_features", list(CRPA_ALL_FEATURES)),
        ("Featureset", "cand_25", "cand_25", list(CRPA_SELECTED_FEATURES["cand_25"])),
        ("Featureset", "cand_04", "cand_04", list(CRPA_SELECTED_FEATURES["cand_04"])),
    ]
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    patient_ids = data["subject_id"].astype(str).to_numpy()

    prediction_frames = []
    fold_rows = []
    for feature_mode, candidate, feature_set, columns in configurations:
        for model_name, model in models.items():
            oof_probability = np.full(len(data), np.nan, dtype=float)
            oof_prediction = np.full(len(data), -1, dtype=int)
            fold_assignment = np.full(len(data), -1, dtype=int)

            for fold, (train_index, validation_index) in enumerate(
                splitter.split(x[columns], y), start=1
            ):
                x_train = x.iloc[train_index][columns]
                x_validation = x.iloc[validation_index][columns]
                y_train = y.iloc[train_index].to_numpy(dtype=int)
                y_validation = y.iloc[validation_index].to_numpy(dtype=int)

                pipe = create_crpa_pipeline(model, model_name, columns)
                pipe.fit(x_train, y_train)
                probability = pipe.predict_proba(x_validation)[:, 1].astype(float)
                prediction = (probability >= CLASSIFICATION_THRESHOLD).astype(int)

                oof_probability[validation_index] = probability
                oof_prediction[validation_index] = prediction
                fold_assignment[validation_index] = fold

                fold_values = {
                    "Accuracy": accuracy_score(y_validation, prediction),
                    "Precision": precision_score(y_validation, prediction, zero_division=0),
                    "Recall": recall_score(y_validation, prediction, zero_division=0),
                    "F1-score": f1_score(y_validation, prediction, zero_division=0),
                    "AUROC": roc_auc_score(y_validation, probability),
                    "AUPRC": average_precision_score(y_validation, probability),
                }
                for metric, estimate in fold_values.items():
                    fold_rows.append({
                        "cohort": "external_mimic_crpa",
                        "task": "crpa_28d_mortality",
                        "feature_mode": feature_mode,
                        "candidate": candidate,
                        "feature_set": feature_set,
                        "model": model_name,
                        "fold": fold,
                        "metric": metric,
                        "estimate": float(estimate),
                    })

            if np.isnan(oof_probability).any() or (fold_assignment < 1).any():
                raise RuntimeError(f"Incomplete CRPA OOF predictions for {candidate}/{model_name}")
            if not np.array_equal(
                oof_prediction,
                (oof_probability >= CLASSIFICATION_THRESHOLD).astype(int),
            ):
                raise RuntimeError(
                    f"CRPA y_pred is inconsistent with y_proba for {candidate}/{model_name}"
                )

            prediction_frames.append(pd.DataFrame({
                "cohort": "external_mimic_crpa",
                "task": "crpa_28d_mortality",
                "feature_mode": feature_mode,
                "candidate": candidate,
                "feature_set": feature_set,
                "model": model_name,
                "patient_id": patient_ids,
                "y_true": y.to_numpy(dtype=int),
                "y_proba": oof_probability,
                "y_pred": oof_prediction,
                "threshold": CLASSIFICATION_THRESHOLD,
                "prediction_source": "external_5fold_oof",
                "data_version": str(CRPA_DATA_PATH.relative_to(REPO)),
                "fold": fold_assignment,
            }))

    predictions = pd.concat(prediction_frames, ignore_index=True)
    fold_metrics = pd.DataFrame(fold_rows)
    expected_groups = 3 * len(CRPA_MODEL_NAMES)
    sizes = predictions.groupby(["candidate", "model"]).size()
    unique_patients = predictions.groupby(["candidate", "model"])["patient_id"].nunique()
    if len(sizes) != expected_groups or not (sizes == 286).all() or not (unique_patients == 286).all():
        raise RuntimeError("CRPA OOF output is not 286 unique patients for every one of 15 configurations")
    positive_counts = predictions.groupby(["candidate", "model"])["y_true"].sum()
    if not (positive_counts == 80).all():
        raise RuntimeError("CRPA OOF class distribution is not 80 death / 206 survival")
    if not np.allclose(predictions["threshold"], CLASSIFICATION_THRESHOLD):
        raise RuntimeError("CRPA classification threshold changed from 0.5")
    return predictions, fold_metrics


def _parse_crpa_fullfeature_reference():
    """Parse the original full-feature 5-fold mean±SD output from the CRPA notebook."""
    text = _notebook_output_text(CRPA_NOTEBOOK_PATH)
    rows = []
    for model in CRPA_MODEL_NAMES:
        matching_line = None
        for line in text.splitlines():
            if re.match(rf"^\s*{re.escape(model)}\s+", line):
                pairs = re.findall(r"(-?\d+\.\d+)\s*±\s*(\d+\.\d+)", line)
                if len(pairs) == len(CLASSIFICATION_METRICS):
                    matching_line = line
                    break
        if matching_line is None:
            raise RuntimeError(f"Could not parse CRPA full-feature reference for {model}")
        pairs = re.findall(r"(-?\d+\.\d+)\s*±\s*(\d+\.\d+)", matching_line)
        for metric, (mean_text, sd_text) in zip(CLASSIFICATION_METRICS, pairs):
            rows.append({
                "task": "crpa_28d_mortality",
                "feature_mode": "FullFeature",
                "candidate": "all_features",
                "model": model,
                "metric": metric,
                "original_estimate": float(mean_text),
                "original_sd": float(sd_text),
                "display_decimals": len(mean_text.split(".")[1]),
                "source": CRPA_NOTEBOOK_PATH.name,
            })
    reference = pd.DataFrame(rows)
    if len(reference) != 30:
        raise RuntimeError(f"CRPA FullFeature reference must contain 30 rows, got {len(reference)}")
    return reference


def _load_crpa_selected_reference():
    reference = pd.read_csv(CRPA_SELECTED_REFERENCE_PATH)
    if "model_name" in reference.columns:
        reference = reference.rename(columns={"model_name": "model"})
    required = {"set_id", "model", *CLASSIFICATION_METRICS}
    if not required.issubset(reference.columns):
        raise RuntimeError(
            f"CRPA selected-feature reference missing required columns: {CRPA_SELECTED_REFERENCE_PATH}"
        )

    reference = reference[reference["set_id"].isin(CRPA_SELECTED_FEATURES)].copy()
    expected_candidates = set(CRPA_SELECTED_FEATURES)
    observed_candidates = set(reference["set_id"].astype(str).unique())
    if observed_candidates != expected_candidates:
        raise RuntimeError(
            "CRPA selected-feature reference candidate coverage mismatch: "
            f"expected {sorted(expected_candidates)}, observed {sorted(observed_candidates)}"
        )
    if set(reference["model"].astype(str).unique()) != set(CRPA_MODEL_NAMES):
        raise RuntimeError("CRPA selected-feature reference does not contain exactly the five frozen models")
    combination_counts = reference.groupby(["set_id", "model"]).size()
    if len(combination_counts) != 10 or not (combination_counts == 1).all():
        raise RuntimeError("CRPA selected-feature reference must contain one row per candidate/model")

    reference = reference.melt(
        id_vars=["set_id", "model"],
        value_vars=list(CLASSIFICATION_METRICS),
        var_name="metric",
        value_name="original_estimate",
    ).rename(columns={"set_id": "candidate"})
    reference["task"] = "crpa_28d_mortality"
    reference["feature_mode"] = "Featureset"
    reference["source"] = str(CRPA_SELECTED_REFERENCE_PATH.relative_to(REPO))

    expected_rows = 60
    candidate_counts = reference.groupby("candidate").size().to_dict()
    if len(reference) != expected_rows:
        raise RuntimeError(
            f"CRPA selected-feature reference must contain {expected_rows} metric rows, got {len(reference)}"
        )
    if candidate_counts != {"cand_04": 30, "cand_25": 30}:
        raise RuntimeError(f"Unexpected CRPA selected-feature metric counts: {candidate_counts}")
    if reference["original_estimate"].isna().any():
        raise RuntimeError("CRPA selected-feature reference contains missing metric values")
    return reference


def audit_crpa_point_estimates(fold_metrics):
    """Verify that the unchanged CRPA 5-fold protocol reproduces original means.

    The reviewer CI point estimator is pooled patient-level OOF performance and is
    intentionally not used to replace the manuscript's original fold mean±SD.
    """
    keys = ["task", "feature_mode", "candidate", "model", "metric"]
    grouped = fold_metrics.groupby(keys, as_index=False)["estimate"].agg(
        recomputed_5fold_mean="mean"
    )
    sd = fold_metrics.groupby(keys, as_index=False)["estimate"].agg(
        recomputed_5fold_sd=lambda values: float(np.std(values, ddof=1))
    )
    current = grouped.merge(sd, on=keys, validate="one_to_one")
    if len(current) != 90:
        raise RuntimeError(f"CRPA recomputed audit must contain 90 metric rows, got {len(current)}")
    current_counts = current.groupby("candidate").size().to_dict()
    if current_counts != {"all_features": 30, "cand_04": 30, "cand_25": 30}:
        raise RuntimeError(f"Unexpected recomputed CRPA metric counts: {current_counts}")
    per_model_metric_counts = current.groupby(["candidate", "model"])["metric"].nunique()
    if len(per_model_metric_counts) != 15 or not (per_model_metric_counts == 6).all():
        raise RuntimeError("Every CRPA candidate/model must contain exactly six recomputed metrics")

    full_reference = _parse_crpa_fullfeature_reference()
    full_current = current[current["candidate"] == "all_features"].copy()
    full = full_reference.merge(
        full_current, on=keys, how="outer", validate="one_to_one", indicator=True
    )
    if len(full) != 30 or not (full["_merge"] == "both").all():
        raise RuntimeError("CRPA FullFeature audit coverage is not exactly 30 matched rows")
    full = full.drop(columns="_merge")
    if full[["original_estimate", "recomputed_5fold_mean", "recomputed_5fold_sd"]].isna().any().any():
        raise RuntimeError("CRPA FullFeature audit contains missing values")
    full["new_rounded"] = [
        round(value, int(decimals))
        for value, decimals in zip(full["recomputed_5fold_mean"], full["display_decimals"])
    ]
    full["new_sd_rounded"] = [
        round(value, int(decimals))
        for value, decimals in zip(full["recomputed_5fold_sd"], full["display_decimals"])
    ]
    full["mean_matches_original"] = full["new_rounded"] == full["original_estimate"]
    full["sd_matches_original"] = full["new_sd_rounded"] == full["original_sd"]
    full["matches_original"] = full["mean_matches_original"] & full["sd_matches_original"]

    selected_reference = _load_crpa_selected_reference()
    selected_current = current[current["candidate"].isin(CRPA_SELECTED_FEATURES)].copy()
    selected = selected_reference.merge(
        selected_current,
        on=keys,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if len(selected) != 60 or not (selected["_merge"] == "both").all():
        raise RuntimeError("CRPA selected-feature audit coverage is not exactly 60 matched rows")
    selected = selected.drop(columns="_merge")
    if selected[["original_estimate", "recomputed_5fold_mean"]].isna().any().any():
        raise RuntimeError("CRPA selected-feature audit contains missing values")
    selected_counts = selected.groupby("candidate").size().to_dict()
    if selected_counts != {"cand_04": 30, "cand_25": 30}:
        raise RuntimeError(f"Unexpected selected-feature audit counts: {selected_counts}")
    selected_model_counts = selected.groupby(["candidate", "model"])["metric"].nunique()
    if len(selected_model_counts) != 10 or not (selected_model_counts == 6).all():
        raise RuntimeError("Every selected CRPA candidate/model must contain exactly six metrics")
    selected["new_rounded"] = selected["recomputed_5fold_mean"]
    selected["matches_original"] = np.isclose(
        selected["recomputed_5fold_mean"],
        selected["original_estimate"],
        rtol=0,
        atol=1e-12,
    )

    audit = pd.concat([full, selected], ignore_index=True, sort=False)
    audit["estimate"] = audit["recomputed_5fold_mean"]
    audit["original_5fold_mean"] = audit["original_estimate"]
    audit["original_5fold_sd"] = np.where(
        audit["feature_mode"] == "FullFeature",
        audit["original_sd"],
        audit["recomputed_5fold_sd"],
    )
    audit["audit_estimator"] = "original_5fold_mean"
    if len(audit) != 90:
        raise RuntimeError(f"CRPA total point-estimate audit must contain 90 rows, got {len(audit)}")
    if not audit["matches_original"].all():
        bad = audit.loc[
            ~audit["matches_original"],
            ["candidate", "model", "metric", "original_estimate", "recomputed_5fold_mean"],
        ].copy()
        bad["difference"] = bad["recomputed_5fold_mean"] - bad["original_estimate"]
        raise RuntimeError(
            "CRPA five-fold point estimates do not reproduce the formal references:\n"
            + bad.to_string(index=False)
        )
    return audit


def _classification_metrics_from_predictions(predictions):
    rows = []
    group_columns = ["cohort", "task", "feature_mode", "candidate", "feature_set", "model"]
    for key, group in predictions.groupby(group_columns, sort=False):
        y = group["y_true"].to_numpy(dtype=int)
        p = group["y_proba"].to_numpy(dtype=float)
        pred = group["y_pred"].to_numpy(dtype=int)
        values = {
            "Accuracy": accuracy_score(y, pred),
            "Precision": precision_score(y, pred, zero_division=0),
            "Recall": recall_score(y, pred, zero_division=0),
            "F1-score": f1_score(y, pred, zero_division=0),
            "AUROC": roc_auc_score(y, p),
            "AUPRC": average_precision_score(y, p),
        }
        for metric, estimate in values.items():
            rows.append(dict(zip(group_columns, key)) | {"metric": metric, "estimate": float(estimate)})
    return pd.DataFrame(rows)


def _notebook_output_text(path):
    notebook = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            if "text" in output:
                text = output["text"]
            else:
                text = output.get("data", {}).get("text/plain", "")
            parts.append("".join(text) if isinstance(text, list) else str(text))
    return "\n".join(parts)


def _parse_notebook_reference(task_key, full_feature):
    config = TEMPORAL_CONFIGS[task_key]
    suffix = "FullFeature" if full_feature else "Featureset"
    path = REPO / "experiments" / "02-Temporal-external-validation" / f"{config['notebook_stem']}-{suffix}.ipynb"
    text = _notebook_output_text(path)
    marker = "External validation (external-1) results:" if full_feature else ("(external-1)" if task_key == "polymyxin_resistance" else "External-1")
    position = text.rfind(marker)
    if position < 0:
        raise RuntimeError(f"Could not locate external results in {path.name}")
    text = text[position:]
    candidate = "all_features" if full_feature else None
    rows = []
    model_pattern = "|".join(re.escape(name) for name in MODEL_NAMES)
    for line in text.splitlines():
        candidate_match = re.match(r"\s*---\s*(cand_\d+)\s*---", line)
        if candidate_match:
            candidate = candidate_match.group(1)
            continue
        match = re.match(rf"\s*({model_pattern})\s+((?:-?\d+\.\d+\s+){{5}}-?\d+\.\d+)\s*$", line)
        if not match or candidate is None:
            continue
        tokens = match.group(2).split()
        decimals = [len(token.split(".")[1]) for token in tokens]
        for metric, token, decimal_places in zip(CLASSIFICATION_METRICS, tokens, decimals):
            rows.append({
                "task": task_key,
                "feature_mode": "FullFeature" if full_feature else "Featureset",
                "candidate": candidate,
                "model": match.group(1),
                "metric": metric,
                "original_estimate": float(token),
                "display_decimals": decimal_places,
                "source": path.name,
            })
    expected = 7 * (1 if full_feature else len(config["candidates"])) * 6
    if len(rows) != expected:
        raise RuntimeError(f"Parsed {len(rows)} reference metrics from {path.name}; expected {expected}")
    return pd.DataFrame(rows)


def audit_temporal_point_estimates(predictions):
    current = _classification_metrics_from_predictions(predictions[predictions["cohort"] == "temporal_external-1"])
    references = []
    for task_key in TEMPORAL_CONFIGS:
        references.append(_parse_notebook_reference(task_key, full_feature=False))
        references.append(_parse_notebook_reference(task_key, full_feature=True))
    reference = pd.concat(references, ignore_index=True)
    keys = ["task", "feature_mode", "candidate", "model", "metric"]
    merged = reference.merge(current[keys + ["estimate"]], on=keys, how="left", validate="one_to_one")
    merged["new_rounded"] = [round(value, int(decimals)) for value, decimals in zip(merged["estimate"], merged["display_decimals"])]
    merged["matches_original"] = merged["new_rounded"] == merged["original_estimate"]
    if merged["estimate"].isna().any() or not merged["matches_original"].all():
        bad = merged[merged["estimate"].isna() | ~merged["matches_original"]]
        raise RuntimeError("Temporal point estimates do not match original notebook outputs:\n" + bad.to_string(index=False))
    return merged


def audit_mimic_point_estimates(predictions):
    current = _classification_metrics_from_predictions(predictions)
    path = REPO / "experiments" / "03-MIMIC-IV-CRAB" / "results" / "mimic-crab" / "survival_loocv_median.csv"
    reference = pd.read_csv(path).rename(columns={"Unnamed: 0": "model"})
    reference = reference.melt(id_vars=["model", "candidate"], value_vars=list(CLASSIFICATION_METRICS), var_name="metric", value_name="original_estimate")
    merged = reference.merge(current[["candidate", "model", "metric", "estimate"]], on=["candidate", "model", "metric"], validate="one_to_one")
    merged["source"] = path.name
    merged["matches_original"] = np.isclose(merged["estimate"], merged["original_estimate"], rtol=0, atol=1e-12)
    if not merged["matches_original"].all():
        raise RuntimeError("MIMIC point estimates do not match saved summary")
    return merged


def audit_treatment_point_estimates(predictions):
    reference_path = REPO / "experiments" / "02-Temporal-external-validation" / "results" / "regression_MSE-mse0430" / "regression_metrics_summary0430.csv"
    reference = pd.read_csv(reference_path)
    reference = reference[(reference["dataset"] == "External-1") & (reference["pred_type"] == "External")].copy()
    reference["feature_mode"] = reference["feature_mode"].replace({"AllFeatures": "FullFeature"})
    reference["candidate"] = np.where(reference["feature_mode"] == "FeatureSet", "mse_feature-setA", "all_features")
    reference = reference.melt(id_vars=["feature_mode", "candidate", "model"], value_vars=list(REGRESSION_METRICS), var_name="metric", value_name="original_estimate")
    rows = []
    for key, group in predictions.groupby(["feature_mode", "candidate", "model"], sort=False):
        values = regression_point_estimates(group["y_true"].to_numpy(), group["y_pred"].to_numpy())
        for metric, estimate in values.items():
            rows.append({"feature_mode": key[0], "candidate": key[1], "model": key[2], "metric": metric, "estimate": estimate})
    current = pd.DataFrame(rows)
    merged = reference.merge(current, on=["feature_mode", "candidate", "model", "metric"], validate="one_to_one")
    merged["source"] = reference_path.name
    merged["matches_original"] = np.isclose(merged["estimate"], merged["original_estimate"], rtol=0, atol=1e-10)
    if not merged["matches_original"].all():
        raise RuntimeError("Treatment-duration point estimates do not match saved summary")
    return merged


def compute_classification_ci(predictions, n_bootstrap):
    metrics_rows = []
    distributions = {}
    distribution_index = {}
    plan_meta = {}
    plan_cache = {}
    group_columns = ["cohort", "task", "feature_mode", "candidate", "feature_set", "model"]
    for key, group in predictions.groupby(group_columns, sort=False):
        cohort, task, feature_mode, candidate, feature_set, model = key
        y = group["y_true"].to_numpy(dtype=int)
        p = group["y_proba"].to_numpy(dtype=float)
        threshold = float(group["threshold"].iloc[0])
        plan_key = (cohort, task, tuple(y.tolist()))
        if plan_key not in plan_cache:
            plan_cache[plan_key] = make_classification_plan(y, n_bootstrap=n_bootstrap, seed=BOOTSTRAP_SEED)
            repeated_plan = make_classification_plan(y, n_bootstrap=n_bootstrap, seed=BOOTSTRAP_SEED)
            if not np.array_equal(plan_cache[plan_key].weights_all, repeated_plan.weights_all) or not np.array_equal(plan_cache[plan_key].weights_two_class, repeated_plan.weights_two_class):
                raise RuntimeError(f"Bootstrap reproducibility check failed for {cohort}|{task}")
            plan_meta[f"{cohort}|{task}"] = {
                "n": int(y.size),
                "n_positive": int((y == 1).sum()),
                "n_negative": int((y == 0).sum()),
                "requested": n_bootstrap,
                "valid_two_class": n_bootstrap,
                "rejected_single_class": int(plan_cache[plan_key].rejected_single_class),
            }
        point, dist, metric_meta = bootstrap_classification_metrics(y, p, threshold, plan_cache[plan_key])
        group_id = f"g{len(distribution_index):03d}"
        distribution_index[group_id] = dict(zip(group_columns, key))
        for metric in CLASSIFICATION_METRICS:
            lower, upper = percentile_interval(dist[metric], CI_LEVEL)
            point_within_ci = bool(lower <= point[metric] <= upper)
            if not point_within_ci:
                warnings.warn(
                    f"Point estimate outside percentile CI for {key}, {metric}; "
                    "the CI is retained unchanged because percentile bootstrap intervals "
                    "do not require the point estimate to lie within them.",
                    RuntimeWarning,
                )
            distributions[f"{group_id}__{metric}"] = dist[metric].astype(np.float32)
            metrics_rows.append({
                "cohort": cohort,
                "task": task,
                "feature_mode": feature_mode,
                "candidate": candidate,
                "feature_set": feature_set,
                "model": model,
                "n": int(y.size),
                "n_positive": int((y == 1).sum()),
                "n_negative": int((y == 0).sum()),
                "metric": metric,
                "estimate": point[metric],
                "ci_lower": lower,
                "ci_upper": upper,
                "ci_level": CI_LEVEL,
                "bootstrap_method": "percentile_patient_bootstrap",
                "bootstrap_replicates_requested": n_bootstrap,
                "bootstrap_replicates_valid": metric_meta[metric]["valid"],
                "bootstrap_replicates_rejected_single_class": metric_meta[metric]["rejected_single_class"],
                "bootstrap_seed": BOOTSTRAP_SEED,
                "threshold": threshold,
                "point_estimate_within_ci": point_within_ci,
            })
    return pd.DataFrame(metrics_rows), distributions, distribution_index, plan_meta


def compute_regression_ci(predictions, n_bootstrap):
    metrics_rows = []
    distributions = {}
    distribution_index = {}
    group_columns = ["cohort", "task", "feature_mode", "candidate", "feature_set", "model"]
    plan = make_regression_plan(predictions["patient_id"].nunique(), n_bootstrap=n_bootstrap, seed=BOOTSTRAP_SEED)
    repeated_plan = make_regression_plan(predictions["patient_id"].nunique(), n_bootstrap=n_bootstrap, seed=BOOTSTRAP_SEED)
    if not np.array_equal(plan.weights_all, repeated_plan.weights_all):
        raise RuntimeError("Regression bootstrap reproducibility check failed")
    for key, group in predictions.groupby(group_columns, sort=False):
        y = group["y_true"].to_numpy(dtype=float)
        p = group["y_pred"].to_numpy(dtype=float)
        point, dist, metric_meta = bootstrap_regression_metrics(y, p, plan)
        group_id = f"r{len(distribution_index):03d}"
        distribution_index[group_id] = dict(zip(group_columns, key))
        for metric in REGRESSION_METRICS:
            lower, upper = percentile_interval(dist[metric], CI_LEVEL)
            point_within_ci = bool(lower <= point[metric] <= upper)
            if not point_within_ci:
                warnings.warn(
                    f"Point estimate outside percentile CI for {key}, {metric}; "
                    "the CI is retained unchanged because percentile bootstrap intervals "
                    "do not require the point estimate to lie within them.",
                    RuntimeWarning,
                )
            distributions[f"{group_id}__{metric}"] = dist[metric].astype(np.float32)
            metrics_rows.append({
                "cohort": key[0], "task": key[1], "feature_mode": key[2], "candidate": key[3],
                "feature_set": key[4], "model": key[5], "n": int(y.size), "n_positive": np.nan,
                "n_negative": np.nan, "metric": metric, "estimate": point[metric], "ci_lower": lower,
                "ci_upper": upper, "ci_level": CI_LEVEL, "bootstrap_method": "percentile_patient_bootstrap",
                "bootstrap_replicates_requested": n_bootstrap,
                "bootstrap_replicates_valid": metric_meta[metric]["valid"],
                "bootstrap_replicates_rejected_single_class": np.nan, "bootstrap_seed": BOOTSTRAP_SEED,
                "threshold": np.nan, "point_estimate_within_ci": point_within_ci,
            })
    return pd.DataFrame(metrics_rows), distributions, distribution_index


def run(n_bootstrap):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporal = generate_temporal_predictions()
    mimic = load_mimic_predictions()
    crpa, crpa_fold_metrics = generate_crpa_predictions()
    classification_predictions = pd.concat([temporal, mimic, crpa], ignore_index=True, sort=False)
    treatment = load_treatment_predictions()

    temporal_audit = audit_temporal_point_estimates(temporal)
    mimic_audit = audit_mimic_point_estimates(mimic)
    crpa_audit = audit_crpa_point_estimates(crpa_fold_metrics)
    treatment_audit = audit_treatment_point_estimates(treatment)
    consistency = pd.concat([
        temporal_audit.assign(cohort="temporal_external-1"),
        mimic_audit.assign(cohort="external_mimic_crab"),
        crpa_audit.assign(cohort="external_mimic_crpa"),
        treatment_audit.assign(cohort="temporal_external-1", task="treatment_duration"),
    ], ignore_index=True, sort=False)

    classification_metrics, class_dist, class_index, plan_meta = compute_classification_ci(classification_predictions, n_bootstrap)
    regression_metrics, reg_dist, reg_index = compute_regression_ci(treatment, n_bootstrap)
    metrics = pd.concat([classification_metrics, regression_metrics], ignore_index=True)

    classification_predictions.to_csv(OUTPUT_DIR / "validation_predictions.csv", index=False)
    crpa_fold_metrics.to_csv(OUTPUT_DIR / "crpa_original_5fold_metrics.csv", index=False)
    treatment.to_csv(OUTPUT_DIR / "regression_validation_predictions.csv", index=False)
    metrics.to_csv(OUTPUT_DIR / "validation_metrics_95ci.csv", index=False)
    consistency.to_csv(OUTPUT_DIR / "point_estimate_consistency.csv", index=False)
    np.savez_compressed(OUTPUT_DIR / "bootstrap_metric_distributions.npz", **class_dist, **reg_dist)

    metadata = {
        "ci_level": CI_LEVEL,
        "bootstrap_method": "patient-level non-parametric percentile bootstrap",
        "bootstrap_replicates": n_bootstrap,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "classification_threshold_policy": "fixed according to original notebooks (0.5 for all audited classification analyses)",
        "external_mimic_protocol": "LOOCV out-of-fold prediction followed by patient-level bootstrap",
        "external_mimic_crpa_protocol": "unchanged stratified 5-fold CV for the frozen FullFeature, cand_25 and cand_04 configurations; patient-level OOF predictions followed by bootstrap; original fold-level mean ± SD retained",
        "crpa_dataset": str(CRPA_DATA_PATH.relative_to(REPO)),
        "crpa_reference_results": str(CRPA_RESULTS_DIR.relative_to(REPO)),
        "crpa_feature_selection_policy": "no SHAP, subset search, or feature reselection; the formal cand_25 and cand_04 column lists are fixed in the script from results/crpa0411",
        "temporal_protocol": "unchanged development-cohort model pipeline prediction on temporal cohort followed by patient-level bootstrap",
        "single_class_policy": "single-class draws excluded from AUROC/AUPRC only; resampling continued until requested valid count",
        "bootstrap_reproducibility_check": "passed (identical plans regenerated with the same seed)",
        "percentile_interval_diagnostic": {
            "note": "A percentile bootstrap CI does not require the original point estimate to lie within the interval; such cases are recorded without changing the CI or stopping the run.",
            "outside_interval_count": int((~metrics["point_estimate_within_ci"].astype(bool)).sum()),
            "outside_interval_records": metrics.loc[
                ~metrics["point_estimate_within_ci"].astype(bool),
                ["cohort", "task", "feature_mode", "candidate", "model", "metric", "estimate", "ci_lower", "ci_upper"],
            ].to_dict(orient="records"),
        },
        "bootstrap_plan_metadata": plan_meta,
        "distribution_index": class_index | reg_index,
        "software_versions": {
            "Python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
            "scipy": scipy.__version__,
            "xgboost": xgboost.__version__,
            "lightgbm": lightgbm.__version__,
            "catboost": catboost.__version__,
        },
    }
    (OUTPUT_DIR / "bootstrap_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = metrics[["task", "cohort", "feature_mode", "candidate", "model", "metric", "estimate", "ci_lower", "ci_upper"]].copy()
    summary["95% CI"] = summary.apply(lambda row: f"{row['ci_lower']:.3f}-{row['ci_upper']:.3f}", axis=1)
    print(summary[["task", "cohort", "feature_mode", "candidate", "model", "metric", "estimate", "95% CI"]].to_string(index=False))
    print(f"\nAll point-estimate consistency checks passed: {len(consistency)} metric rows.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    args = parser.parse_args()
    run(args.n_bootstrap)
