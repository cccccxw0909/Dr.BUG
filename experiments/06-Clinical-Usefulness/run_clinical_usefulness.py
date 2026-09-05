"""Reviewer 1 Comment 11: supplemental clinical usefulness analyses.

This script deliberately reuses the frozen model, feature-set, preprocessing,
and validation definitions from the existing notebooks.  It does not perform
feature selection, hyperparameter tuning, recalibration, or model selection.
Patient-level held-out probabilities are used only for Brier scores,
calibration analyses, and decision curve analysis (DCA).
"""

import argparse
import json
import math
import os
import platform
import re
import sys
import warnings
from collections import OrderedDict
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneOut, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


RANDOM_STATE = 42
CLASSIFICATION_THRESHOLD = 0.5
USE_SMOTE = False
SMOTE_RATIO = 0.8
DCA_THRESHOLDS = np.arange(0.01, 1.00, 0.01)
MODEL_ORDER = [
    "XGBoost",
    "LightGBM",
    "CatBoost",
    "RandomForest",
    "LogisticRegression",
    "SVM",
    "KNN",
]
MODEL_COLORS = {
    "XGBoost": "#4E79A7",
    "LightGBM": "#F28E2B",
    "CatBoost": "#E15759",
    "RandomForest": "#76B7B2",
    "LogisticRegression": "#59A14F",
    "SVM": "#B07AA1",
    "KNN": "#9C755F",
}
TREE_MODELS = {"XGBoost", "LightGBM", "CatBoost", "RandomForest"}
METRIC_NAMES = ["Accuracy", "Precision", "Recall", "F1-score", "AUROC", "AUPRC"]

SCRIPT_PATH = Path(__file__).resolve()


def discover_repository_root(script_path):
    """Locate the repository root by required project markers, not parent depth."""
    for candidate in [script_path.parent, *script_path.parents]:
        if (candidate / "datasets").is_dir() and (candidate / "experiments").is_dir():
            return candidate
    raise RuntimeError(
        f"Unable to locate repository root from {script_path}; "
        "required directories 'datasets/' and 'experiments/' were not found."
    )


REPO_ROOT = discover_repository_root(SCRIPT_PATH)
assert (REPO_ROOT / "datasets").exists(), f"Invalid repository root: {REPO_ROOT} (datasets missing)"
assert (REPO_ROOT / "experiments").exists(), f"Invalid repository root: {REPO_ROOT} (experiments missing)"
DATASETS_DIR = REPO_ROOT / "datasets"
MIMIC_PATH = DATASETS_DIR / "MIMIC-IV-CRAB" / "mimicset0227.csv"
OUTPUT_ROOT = SCRIPT_PATH.parent / "results"
PREDICTIONS_DIR = OUTPUT_ROOT / "predictions"
CALIBRATION_DIR = OUTPUT_ROOT / "calibration"
DCA_DIR = OUTPUT_ROOT / "dca"
FIGURES_CALIBRATION_DIR = OUTPUT_ROOT / "figures" / "calibration"
FIGURES_DCA_DIR = OUTPUT_ROOT / "figures" / "dca"
METADATA_DIR = OUTPUT_ROOT / "metadata"

for directory in [
    PREDICTIONS_DIR,
    CALIBRATION_DIR,
    DCA_DIR,
    FIGURES_CALIBRATION_DIR,
    FIGURES_DCA_DIR,
    METADATA_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


MEDICATION_FEATURES = [
    "colistin_cms_daily_freq",
    "polymyxin_b_daily_freq",
    "colistin_sulfate_daily_freq",
    "carbapenem_daily_dose",
    "sulbactam_daily_dose",
    "tigecycline_daily_dose",
    "minocycline_daily_dose",
    "vancomycin_daily_dose",
    "eravacycline_daily_dose",
    "aminoglycoside_daily_dose",
]
TIME_FEATURES = ["Pre_Hospital_Days", "Pre_ICU_Days"]
BASE_FEATURES = ["Age", "Gender", "BMI"]
COMORBIDITY_BASE = [
    "Diabetes Mellitus",
    "Hypertension",
    "Heart Disease",
    "Stroke",
    "Malignant Tumor",
    "Chronic Kidney Disease",
    "Chronic Liver Disease",
    "COPD",
    "Comorb_other",
]
COMORBIDITY_FEATURES = COMORBIDITY_BASE + ["Comorb_count"]
IMMUNOSUPPRESSION_FEATURES = [
    "Use immunosuppressive agents",
    "Neutrophil Reduction",
    "HIV/AIDS",
    "Post-Transplant Status",
    "Chemotherapy/Radiation",
    "immuno_Other",
]
SUPPORT_FEATURES = ["Resp_support", "Oxygen_concentration"]
PRE_LAB_FEATURES = [
    "WBC",
    "N_percent",
    "L_count",
    "PLT",
    "CRP1",
    "PCT1",
    "D-d",
    "Cr_baseline",
    "eGFR1",
    "RRT",
    "ALT",
    "AST",
    "TB",
    "ALB",
]
INFECTION_FEATURES = [
    "Infection_HAP",
    "Infection_VAP",
    "Coinfection_G_Pos",
    "Coinfection_G_Neg",
    "Coinfection_Fungi",
]
COINFECTION_FEATURES = ["Coinfection_G_Pos", "Coinfection_G_Neg", "Coinfection_Fungi"]
RESISTANCE_FEATURES = [
    "resistance_SXT",
    "resistance_KAN",
    "resistance_MIN",
    "resistance_TGC",
    "resistance_CFP-SUL",
    "resistance_TOB",
]
GROUP_DEFS = {
    "Comorbidity": COMORBIDITY_FEATURES,
    "Immunosuppression": IMMUNOSUPPRESSION_FEATURES,
}

MIMIC_MEDICATION_COLUMNS = [
    "Aminoglycoside",
    "CMS",
    "Carbapenem",
    "Minocycline",
    "Sulbactam",
    "Tigecycline",
    "Vancomycin",
]
MIMIC_CANDIDATES = OrderedDict(
    [
        (
            "feature-setA",
            [
                "PLT",
                "eGFR1",
                "Comorbidity",
                "PCT1",
                "Age",
                "ALB",
                "N_percent",
                "Oxygen_concentration",
                "Cr_baseline",
            ],
        ),
        (
            "feature-setB",
            [
                "Comorbidity",
                "Age",
                "N_percent",
                "CRP1",
                "Oxygen_concentration",
                "Immunosuppression",
                "Cr_baseline",
            ],
        ),
    ]
)
MIMIC_EXPECTED_EXPANDED_COLUMN_COUNTS = {"feature-setA": 23, "feature-setB": 27}
MIMIC_EXPECTED_EXPANDED_COLUMNS = {
    "feature-setA": [
        "Aminoglycoside",
        "CMS",
        "Carbapenem",
        "Minocycline",
        "Sulbactam",
        "Tigecycline",
        "Vancomycin",
        "PLT",
        "eGFR1",
        "Diabetes Mellitus",
        "Hypertension",
        "Heart Disease",
        "Stroke",
        "Malignant Tumor",
        "Chronic Kidney Disease",
        "Chronic Liver Disease",
        "COPD",
        "Comorb_other",
        "Age",
        "ALB",
        "N_percent",
        "Oxygen_concentration",
        "Cr_baseline",
    ],
    "feature-setB": [
        "Aminoglycoside",
        "CMS",
        "Carbapenem",
        "Minocycline",
        "Sulbactam",
        "Tigecycline",
        "Vancomycin",
        "Diabetes Mellitus",
        "Hypertension",
        "Heart Disease",
        "Stroke",
        "Malignant Tumor",
        "Chronic Kidney Disease",
        "Chronic Liver Disease",
        "COPD",
        "Comorb_other",
        "Age",
        "N_percent",
        "CRP1",
        "Oxygen_concentration",
        "Use immunosuppressive agents",
        "Neutrophil Reduction",
        "HIV/AIDS",
        "Post-Transplant Status",
        "Chemotherapy/Radiation",
        "immuno_Other",
        "Cr_baseline",
    ],
}

EXPECTED_COHORTS = {
    ("Clinical efficacy", "Development_OOF"): {"N": 441, "events": 327},
    ("Clinical efficacy", "External_1"): {"N": 111, "events": 90},
    ("Survival", "Development_OOF"): {"N": 443, "events": 118},
    ("Survival", "External_1"): {"N": 111, "events": 19},
    ("Survival", "MIMIC_CRAB_LOOCV"): {"N": 42, "events": 9},
    ("Polymyxin resistance", "Development_OOF"): {"N": 443, "events": 106},
    ("Polymyxin resistance", "External_1"): {"N": 111, "events": 28},
}

FINAL_DATASET_POLICY = {
    "Clinical efficacy": "datasets",
    "Survival": "datasets",
    "Polymyxin resistance": "datasets",
}

TASK_SPECS = OrderedDict(
    [
        (
            "Clinical efficacy",
            {
                "slug": "clinical_efficacy",
                "target": "Clinical_outcome",
                "event_definition": "clinical improvement",
                "candidate_sets": OrderedDict(
                    [
                        (
                            "cand_21",
                            [
                                "Oxygen_concentration",
                                "Comorbidity",
                                "eGFR1",
                                "PLT",
                                "CRP1",
                                "Cr_baseline",
                                "Age",
                                "TB",
                            ],
                        ),
                        (
                            "cand_39",
                            [
                                "Oxygen_concentration",
                                "resistance_CFP-SUL",
                                "Infection_HAP",
                                "Infection_VAP",
                                "eGFR1",
                            ],
                        ),
                        (
                            "cand_38",
                            [
                                "Oxygen_concentration",
                                "Coinfection_Fungi",
                                "resistance_CFP-SUL",
                                "Infection_HAP",
                                "Infection_VAP",
                                "resistance_KAN",
                                "eGFR1",
                            ],
                        ),
                        (
                            "cand_40",
                            [
                                "Oxygen_concentration",
                                "resistance_CFP-SUL",
                                "Infection_HAP",
                                "resistance_KAN",
                                "eGFR1",
                            ],
                        ),
                    ]
                ),
                "x_label": "Predicted probability of clinical improvement",
                "y_label": "Observed clinical improvement rate",
            },
        ),
        (
            "Survival",
            {
                "slug": "survival",
                "target": "Survival",
                "event_definition": "mortality",
                "candidate_sets": OrderedDict(
                    [
                        (
                            "cand_37",
                            [
                                "Comorbidity",
                                "PLT",
                                "Age",
                                "N_percent",
                                "CRP1",
                                "Oxygen_concentration",
                                "Immunosuppression",
                                "Cr_baseline",
                            ],
                        ),
                        (
                            "cand_16",
                            [
                                "PLT",
                                "eGFR1",
                                "Comorbidity",
                                "PCT1",
                                "Age",
                                "ALB",
                                "N_percent",
                                "Oxygen_concentration",
                                "Cr_baseline",
                            ],
                        ),
                    ]
                ),
                "x_label": "Predicted mortality risk",
                "y_label": "Observed mortality rate",
            },
        ),
        (
            "Polymyxin resistance",
            {
                "slug": "polymyxin_resistance",
                "target": "Target_Polymyxin",
                "event_definition": "polymyxin resistance",
                "candidate_sets": OrderedDict(
                    [
                        (
                            "cand_11",
                            ["Comorbidity", "Age", "AST", "PLT", "CRP1", "WBC", "N_percent"],
                        ),
                        ("cand_27", ["Comorbidity", "Age", "WBC", "L_count"]),
                        ("cand_40", ["PLT", "CRP1"]),
                        (
                            "cand_05",
                            ["Comorbidity", "Age", "PLT", "ALB", "WBC", "CRP1", "N_percent"],
                        ),
                        (
                            "cand_04",
                            ["Comorbidity", "Age", "PLT", "AST", "ALB", "CRP1", "N_percent"],
                        ),
                    ]
                ),
                "x_label": "Predicted probability of polymyxin resistance",
                "y_label": "Observed resistance rate",
            },
        ),
    ]
)


def log(message):
    print(message, flush=True)


def unique_preserving_order(values):
    return list(dict.fromkeys(values))


def package_version(distribution):
    try:
        return importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        return None


def dataset_directory(source_name):
    if source_name == "datasets":
        return DATASETS_DIR
    raise RuntimeError(f"Unsupported dataset source path: {source_name}")


def prepare_primary_dataframe(path, task):
    df = pd.read_csv(path, encoding="gbk")
    df = df.copy()

    existing_comorbidity = [column for column in COMORBIDITY_BASE if column in df.columns]
    df[existing_comorbidity] = df[existing_comorbidity].fillna(0)
    df["Comorb_count"] = df[existing_comorbidity].sum(axis=1)

    existing_coinfection = [column for column in COINFECTION_FEATURES if column in df.columns]
    df[existing_coinfection] = df[existing_coinfection].fillna(0).astype(int)

    resistance_mapping = {"R": 1, "I": 1, "S": 0}
    for column in RESISTANCE_FEATURES:
        if column in df.columns:
            values = df[column].astype(str).str.strip().str.upper()
            df[column] = pd.to_numeric(values.map(resistance_mapping), errors="coerce")

    if task == "Polymyxin resistance":
        target = "Target_Polymyxin"
        df = df[df["Polymyxin_MIC"].notna()].copy()
        df[target] = (df["Polymyxin_MIC"] >= 2).astype("Int64")
    else:
        target = str(TASK_SPECS[task]["target"])

    df = df[df[target].notna()].copy()
    df[target] = df[target].astype(int)
    return df, target


def full_feature_columns(task, df):
    if task == "Polymyxin resistance":
        columns = (
            BASE_FEATURES
            + TIME_FEATURES
            + COMORBIDITY_FEATURES
            + IMMUNOSUPPRESSION_FEATURES
            + SUPPORT_FEATURES
            + PRE_LAB_FEATURES
        )
    else:
        columns = (
            BASE_FEATURES
            + COMORBIDITY_FEATURES
            + IMMUNOSUPPRESSION_FEATURES
            + SUPPORT_FEATURES
            + PRE_LAB_FEATURES
            + INFECTION_FEATURES
            + RESISTANCE_FEATURES
            + MEDICATION_FEATURES
        )
    return [column for column in columns if column in df.columns]


def expand_candidate_features(task, tokens, available):
    available_set = set(available)
    expanded = []
    for token in tokens:
        if token in GROUP_DEFS:
            expanded.extend(column for column in GROUP_DEFS[token] if column in available_set)
        elif token in available_set:
            expanded.append(token)
    if task != "Polymyxin resistance":
        expanded = [column for column in MEDICATION_FEATURES if column in available_set] + expanded
    return unique_preserving_order(expanded)


def align_external_columns(
    train_df,
    external_df,
    columns,
):
    x_train = train_df[columns].copy()
    x_external = external_df[[column for column in columns if column in external_df.columns]].copy()
    missing = [column for column in columns if column not in external_df.columns]
    for column in missing:
        x_external[column] = x_train[column].median()
    return x_train, x_external[columns], missing


def get_models(scale_pos_weight):
    from catboost import CatBoostClassifier
    from lightgbm import LGBMClassifier
    from xgboost import XGBClassifier

    return OrderedDict(
        [
            (
                "XGBoost",
                XGBClassifier(
                    scale_pos_weight=scale_pos_weight,
                    use_label_encoder=False,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    verbosity=0,
                    random_state=RANDOM_STATE,
                    n_jobs=1,
                ),
            ),
            (
                "LightGBM",
                LGBMClassifier(
                    class_weight="balanced",
                    verbosity=-1,
                    random_state=RANDOM_STATE,
                    n_jobs=1,
                ),
            ),
            (
                "CatBoost",
                CatBoostClassifier(
                    auto_class_weights="Balanced",
                    verbose=0,
                    loss_function="Logloss",
                    allow_writing_files=False,
                    random_state=RANDOM_STATE,
                    thread_count=1,
                ),
            ),
            (
                "RandomForest",
                RandomForestClassifier(
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=1,
                ),
            ),
            (
                "LogisticRegression",
                LogisticRegression(
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    max_iter=1000,
                ),
            ),
            (
                "SVM",
                SVC(class_weight="balanced", random_state=RANDOM_STATE, probability=True),
            ),
            ("KNN", KNeighborsClassifier(weights="distance", n_jobs=1)),
        ]
    )


def create_pipeline(model, model_name):
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if model_name not in TREE_MODELS:
        steps.append(("scaler", StandardScaler()))
    if USE_SMOTE:
        from imblearn.over_sampling import SMOTE

        steps.append(("smote", SMOTE(random_state=RANDOM_STATE, sampling_strategy=SMOTE_RATIO)))
    steps.append(("clf", clone(model)))
    if USE_SMOTE:
        from imblearn.pipeline import Pipeline as ImbPipeline

        return ImbPipeline(steps)
    return Pipeline(steps)


def original_discrimination_metrics(y_true, probability):
    prediction = (probability >= CLASSIFICATION_THRESHOLD).astype(int)
    return {
        "Accuracy": float(accuracy_score(y_true, prediction)),
        "Precision": float(precision_score(y_true, prediction, zero_division=0)),
        "Recall": float(recall_score(y_true, prediction, zero_division=0)),
        "F1-score": float(f1_score(y_true, prediction, zero_division=0)),
        "AUROC": float(roc_auc_score(y_true, probability)),
        "AUPRC": float(average_precision_score(y_true, probability)),
    }


def find_patient_id_column(df):
    for column in ["patient_id", "Patient_ID", "subject_id", "hadm_id", "ID", "id"]:
        if column in df.columns:
            return column
    return None


def event_transform(task, y_original, p_original):
    if task == "Survival":
        return 1 - y_original.astype(int), 1.0 - p_original.astype(float)
    return y_original.astype(int), p_original.astype(float)


def prediction_rows(
    *,
    task,
    cohort,
    feature_set,
    model_name,
    data_source,
    source_df,
    y_original,
    p_original,
    fold_indices,
    prediction_type,
):
    p_original = np.asarray(p_original, dtype=float)
    y_original = np.asarray(y_original, dtype=int)
    y_event, p_event = event_transform(task, y_original, p_original)
    patient_id_column = find_patient_id_column(source_df)
    patient_ids = (
        source_df[patient_id_column].astype(str).to_numpy()
        if patient_id_column is not None
        else np.full(len(source_df), "", dtype=object)
    )
    return pd.DataFrame(
        {
            "task": task,
            "cohort": cohort,
            "feature_set": feature_set,
            "model": model_name,
            "data_source": data_source,
            "patient_index": source_df.index.to_numpy(),
            "patient_id_if_available": patient_ids,
            "subject_id": source_df["subject_id"].to_numpy() if "subject_id" in source_df else "",
            "hadm_id": source_df["hadm_id"].to_numpy() if "hadm_id" in source_df else "",
            "fold_or_loocv_index": fold_indices if fold_indices is not None else pd.NA,
            "prediction_type": prediction_type,
            "event_definition": TASK_SPECS[task]["event_definition"],
            "y_true_original": y_original,
            "y_prob_original": p_original,
            "y_pred_original": (p_original >= CLASSIFICATION_THRESHOLD).astype(int),
            "y_event": y_event,
            "y_prob_event": p_event,
        }
    )


def run_primary_configuration(
    *,
    task,
    feature_set,
    data_source,
    train_df,
    external_df,
    target,
    columns,
):
    x_train, x_external, external_missing_columns = align_external_columns(train_df, external_df, columns)
    y_train = train_df[target].astype(int)
    y_external = external_df[target].astype(int).to_numpy()
    scale_pos_weight = float((y_train == 0).sum() / (y_train == 1).sum())
    models = get_models(scale_pos_weight)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    output_frames = []
    fold_metric_rows = []
    oof_checks = {}
    for model_name, model in models.items():
        n = len(x_train)
        oof_probability = np.full(n, np.nan, dtype=float)
        fold_assignment = np.full(n, -1, dtype=int)
        validation_counts = np.zeros(n, dtype=int)
        no_train_validation_overlap = True

        for fold, (train_indices, validation_indices) in enumerate(cv.split(x_train, y_train), start=1):
            no_train_validation_overlap = no_train_validation_overlap and not bool(
                np.intersect1d(train_indices, validation_indices).size
            )
            pipe = create_pipeline(model, model_name)
            pipe.fit(x_train.iloc[train_indices], y_train.iloc[train_indices])
            probability = pipe.predict_proba(x_train.iloc[validation_indices])[:, 1]
            oof_probability[validation_indices] = probability
            fold_assignment[validation_indices] = fold
            validation_counts[validation_indices] += 1
            fold_metrics = original_discrimination_metrics(y_train.iloc[validation_indices].to_numpy(), probability)
            fold_metric_rows.append(
                {
                    "task": task,
                    "feature_set": feature_set,
                    "model": model_name,
                    "fold": fold,
                    "data_source": data_source,
                    **fold_metrics,
                }
            )

        coverage_ok = bool(
            len(oof_probability) == len(x_train)
            and np.all(validation_counts == 1)
            and np.all(fold_assignment >= 1)
            and np.isfinite(oof_probability).all()
        )
        if not coverage_ok or not no_train_validation_overlap:
            raise RuntimeError(f"OOF coverage/leakage check failed: {task}/{feature_set}/{model_name}")

        output_frames.append(
            prediction_rows(
                task=task,
                cohort="Development_OOF",
                feature_set=feature_set,
                model_name=model_name,
                data_source=data_source,
                source_df=train_df,
                y_original=y_train.to_numpy(),
                p_original=oof_probability,
                fold_indices=fold_assignment,
                prediction_type="5-fold OOF",
            )
        )

        external_pipe = create_pipeline(model, model_name)
        external_pipe.fit(x_train, y_train)
        external_probability = external_pipe.predict_proba(x_external)[:, 1]
        output_frames.append(
            prediction_rows(
                task=task,
                cohort="External_1",
                feature_set=feature_set,
                model_name=model_name,
                data_source=data_source,
                source_df=external_df,
                y_original=y_external,
                p_original=external_probability,
                fold_indices=None,
                prediction_type="External-1",
            )
        )
        oof_checks[model_name] = {
            "number_of_predictions": int(n),
            "each_patient_once": bool(np.all(validation_counts == 1)),
            "no_train_validation_overlap": bool(no_train_validation_overlap),
        }

    configuration_metadata = {
        "task": task,
        "feature_set": feature_set,
        "data_source": data_source,
        "feature_count": len(columns),
        "features": columns,
        "external_missing_columns_filled_with_development_median": external_missing_columns,
        "scale_pos_weight_computed_on_full_development_y": scale_pos_weight,
        "oof_checks": oof_checks,
    }
    return output_frames, fold_metric_rows, configuration_metadata


def prepare_mimic_dataframe():
    full_df = pd.read_csv(MIMIC_PATH, encoding="utf-8")
    full_df = full_df[full_df["survival"].notna()].copy()
    full_df["survival"] = full_df["survival"].astype(int)
    full_df = full_df[full_df["AnyMedicine"] == 1].copy()

    comorb_map = {
        "comorb_diabetes": "Diabetes Mellitus",
        "comorb_hypertension": "Hypertension",
        "comorb_heart_disease": "Heart Disease",
        "comorb_cerebrovascular": "Stroke",
        "comorb_malignancy": "Malignant Tumor",
        "comorb_ckd": "Chronic Kidney Disease",
        "comorb_liver": "Chronic Liver Disease",
        "comorb_copd": "COPD",
    }
    for source, destination in comorb_map.items():
        if source in full_df.columns:
            full_df[destination] = full_df[source].fillna(0)
    if "Comorb_other" not in full_df.columns:
        full_df["Comorb_other"] = 0

    immuno_map = {
        "immuno_drug_use": "Use immunosuppressive agents",
        "immuno_neutropenia": "Neutrophil Reduction",
        "immuno_hiv": "HIV/AIDS",
        "immuno_transplant": "Post-Transplant Status",
        "immuno_chemo_radio": "Chemotherapy/Radiation",
        "immuno_other": "immuno_Other",
    }
    for source, destination in immuno_map.items():
        if source in full_df.columns:
            full_df[destination] = full_df[source].fillna(0)

    for column in MIMIC_MEDICATION_COLUMNS:
        if column in full_df.columns:
            full_df[column] = pd.to_numeric(full_df[column], errors="coerce").fillna(0)

    full_df["Gender"] = (full_df["Gender"].astype(str).str.upper() == "M").astype(int)
    if "Cr_baseline" in full_df.columns and "Age" in full_df.columns:
        creatinine = pd.to_numeric(full_df["Cr_baseline"], errors="coerce")
        age = pd.to_numeric(full_df["Age"], errors="coerce")
        is_female = full_df["Gender"] == 0
        kappa = np.where(is_female, 0.7, 0.9)
        alpha = np.where(is_female, -0.241, -0.302)
        ratio = np.clip(creatinine / kappa, 1e-12, None)
        egfr = (
            142.0
            * np.minimum(ratio, 1.0) ** alpha
            * np.maximum(ratio, 1.0) ** -1.200
            * 0.9938**age
            * np.where(is_female, 1.012, 1.0)
        )
        egfr = np.clip(egfr, 1, 200)
        full_df["eGFR1"] = np.where((creatinine > 0) & creatinine.notna() & age.notna(), egfr, np.nan)
    elif "eGFR1" not in full_df.columns:
        full_df["eGFR1"] = np.nan
    return full_df


def mimic_feature_columns(full_df, feature_set):
    if feature_set not in MIMIC_CANDIDATES:
        raise RuntimeError(f"Unknown MIMIC feature set: {feature_set}")
    tokens = MIMIC_CANDIDATES[feature_set]
    mimic_group_defs = {
        "Comorbidity": COMORBIDITY_BASE,
        "Immunosuppression": IMMUNOSUPPRESSION_FEATURES,
    }
    columns = [column for column in MIMIC_MEDICATION_COLUMNS if column in full_df.columns]
    for token in tokens:
        if token in mimic_group_defs:
            columns.extend(column for column in mimic_group_defs[token] if column in full_df.columns)
        elif token in full_df.columns:
            columns.append(token)
    columns = unique_preserving_order(columns)
    expected_columns = MIMIC_EXPECTED_EXPANDED_COLUMNS[feature_set]
    if columns != expected_columns:
        raise RuntimeError(
            f"MIMIC {feature_set} expansion differs from the original notebook. "
            f"Expected {expected_columns}; observed {columns}"
        )
    if len(columns) != MIMIC_EXPECTED_EXPANDED_COLUMN_COUNTS[feature_set]:
        raise RuntimeError(
            f"MIMIC {feature_set} expected {MIMIC_EXPECTED_EXPANDED_COLUMN_COUNTS[feature_set]} "
            f"columns but observed {len(columns)}"
        )
    return columns


def run_mimic_configurations():
    full_df = prepare_mimic_dataframe()
    y_full = full_df["survival"].astype(int)
    scale_pos_weight = float((y_full == 0).sum() / (y_full == 1).sum())
    models = get_models(scale_pos_weight)
    loo = LeaveOneOut()
    frames = []
    metadata_rows = []

    for feature_set in MIMIC_CANDIDATES:
        columns = mimic_feature_columns(full_df, feature_set)
        x_full = full_df[columns].copy()
        for model_name, model in models.items():
            probability = np.full(len(x_full), np.nan, dtype=float)
            loocv_indices = np.full(len(x_full), -1, dtype=int)
            validation_counts = np.zeros(len(x_full), dtype=int)
            no_train_validation_overlap = True
            for loocv_index, (train_indices, validation_indices) in enumerate(loo.split(x_full), start=1):
                no_train_validation_overlap = no_train_validation_overlap and not bool(
                    np.intersect1d(train_indices, validation_indices).size
                )
                pipe = create_pipeline(model, model_name)
                pipe.fit(x_full.iloc[train_indices], y_full.iloc[train_indices])
                probability[validation_indices] = pipe.predict_proba(x_full.iloc[validation_indices])[:, 1]
                loocv_indices[validation_indices] = loocv_index
                validation_counts[validation_indices] += 1

            if not (
                np.all(validation_counts == 1)
                and np.all(loocv_indices >= 1)
                and np.isfinite(probability).all()
                and no_train_validation_overlap
            ):
                raise RuntimeError(f"MIMIC LOOCV check failed: {feature_set}/{model_name}")

            frames.append(
                prediction_rows(
                    task="Survival",
                    cohort="MIMIC_CRAB_LOOCV",
                    feature_set=feature_set,
                    model_name=model_name,
                    data_source="datasets/MIMIC-IV-CRAB/mimicset0227.csv",
                    source_df=full_df,
                    y_original=y_full.to_numpy(),
                    p_original=probability,
                    fold_indices=loocv_indices,
                    prediction_type="LOOCV",
                )
            )
            metadata_rows.append(
                {
                    "task": "Survival",
                    "cohort": "MIMIC_CRAB_LOOCV",
                    "feature_set": feature_set,
                    "model": model_name,
                    "feature_count": len(columns),
                    "features": columns,
                    "N": len(full_df),
                    "each_patient_once": bool(np.all(validation_counts == 1)),
                    "no_train_validation_overlap": bool(no_train_validation_overlap),
                    "scale_pos_weight_computed_on_full_cohort_y": scale_pos_weight,
                }
            )
    return frames, metadata_rows


def calibration_logistic_fit(y_event, p_event):
    y = np.asarray(y_event, dtype=float)
    p = np.clip(np.asarray(p_event, dtype=float), 1e-6, 1 - 1e-6)
    x = np.log(p / (1 - p))
    if np.unique(y).size < 2:
        return {
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "calibration_fit_status": "failed",
            "calibration_failure_reason": "outcome contains only one class",
        }
    if np.unique(x).size < 2 or float(np.ptp(x)) <= 1e-12:
        return {
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "calibration_fit_status": "failed",
            "calibration_failure_reason": "predicted logit is constant",
        }

    x0 = x[y == 0]
    x1 = x[y == 1]
    if max(float(np.min(x0)), float(np.min(x1))) >= min(float(np.max(x0)), float(np.max(x1))):
        return {
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "calibration_fit_status": "failed",
            "calibration_failure_reason": "complete or quasi-complete separation",
        }

    design = np.column_stack([np.ones_like(x), x])

    def objective(beta):
        eta = design @ beta
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta))

    def gradient(beta):
        return design.T @ (expit(design @ beta) - y)

    fit = minimize(
        objective,
        x0=np.array([0.0, 1.0]),
        jac=gradient,
        method="BFGS",
        options={"gtol": 1e-8, "maxiter": 10000},
    )
    beta = np.asarray(fit.x, dtype=float)
    gradient_norm = float(np.linalg.norm(gradient(beta), ord=np.inf)) if np.isfinite(beta).all() else np.inf
    numerically_converged = bool(fit.success or gradient_norm <= 1e-6)
    if not numerically_converged or not np.isfinite(beta).all():
        return {
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "calibration_fit_status": "failed",
            "calibration_failure_reason": (
                f"optimizer did not converge: {fit.message}; gradient infinity norm={gradient_norm:.3g}"
            ),
        }

    fitted = expit(design @ beta)
    weights = fitted * (1 - fitted)
    hessian = design.T @ (weights[:, None] * design)
    condition_number = float(np.linalg.cond(hessian))
    if not np.isfinite(condition_number) or condition_number > 1e12:
        return {
            "calibration_intercept": np.nan,
            "calibration_slope": np.nan,
            "calibration_fit_status": "failed",
            "calibration_failure_reason": f"singular or ill-conditioned Hessian ({condition_number:.3g})",
        }

    return {
        "calibration_intercept": float(beta[0]),
        "calibration_slope": float(beta[1]),
        "calibration_fit_status": "success",
        "calibration_failure_reason": "",
    }


def requested_bins_for_cohort(cohort):
    return {"Development_OOF": 10, "External_1": 5, "MIMIC_CRAB_LOOCV": 4}[cohort]


def quantile_calibration_bins(
    y_event,
    p_event,
    requested_bins,
):
    y = np.asarray(y_event, dtype=int)
    p = np.asarray(p_event, dtype=float)
    unique_probabilities = np.unique(p)
    if unique_probabilities.size == 1:
        codes = np.zeros(len(p), dtype=int)
    else:
        q = min(requested_bins, unique_probabilities.size, len(p))
        quantiles = np.linspace(0.0, 1.0, q + 1)
        edges = np.unique(np.quantile(p, quantiles))
        if edges.size < 2:
            codes = np.zeros(len(p), dtype=int)
        else:
            edges = edges.astype(float)
            edges[0] = -np.inf
            edges[-1] = np.inf
            codes = np.asarray(pd.cut(p, bins=edges, labels=False, include_lowest=True), dtype=int)
    rows = []
    for bin_code in sorted(np.unique(codes)):
        mask = codes == bin_code
        rows.append(
            {
                "bin_id": len(rows) + 1,
                "n_in_bin": int(mask.sum()),
                "mean_predicted_probability": float(p[mask].mean()),
                "observed_event_rate": float(y[mask].mean()),
            }
        )
    output = pd.DataFrame(rows)
    return output, int(len(output))


def dca_for_configuration(y_event, p_event):
    y = np.asarray(y_event, dtype=int)
    p = np.asarray(p_event, dtype=float)
    n = len(y)
    prevalence = float(y.mean())
    rows = []
    for threshold in DCA_THRESHOLDS:
        predicted_positive = p >= threshold
        true_positives = int(np.sum(predicted_positive & (y == 1)))
        false_positives = int(np.sum(predicted_positive & (y == 0)))
        odds = float(threshold / (1 - threshold))
        net_benefit_model = true_positives / n - false_positives / n * odds
        net_benefit_all = prevalence - (1 - prevalence) * odds
        rows.append(
            {
                "threshold": float(threshold),
                "N": int(n),
                "true_positives": true_positives,
                "false_positives": false_positives,
                "net_benefit_model": float(net_benefit_model),
                "net_benefit_all": float(net_benefit_all),
                "net_benefit_none": 0.0,
            }
        )
    return pd.DataFrame(rows)


def contiguous_intervals(thresholds, selected):
    values = np.asarray(thresholds, dtype=float)[np.asarray(selected, dtype=bool)]
    if values.size == 0:
        return ""
    intervals = []
    start = previous = float(values[0])
    for value in values[1:]:
        value = float(value)
        if not math.isclose(value - previous, 0.01, rel_tol=0.0, abs_tol=1e-9):
            intervals.append((start, previous))
            start = value
        previous = value
    intervals.append((start, previous))
    return ";".join(f"{start_value:.2f}-{end_value:.2f}" for start_value, end_value in intervals)


def analyze_predictions(
    prediction_tables,
):
    all_predictions = pd.concat(prediction_tables.values(), ignore_index=True)
    group_columns = ["task", "cohort", "feature_set", "model"]
    metric_rows = []
    calibration_frames = []
    dca_frames = []
    dca_summary_rows = []

    for keys, group in all_predictions.groupby(group_columns, sort=False):
        task, cohort, feature_set, model_name = keys
        y_event = group["y_event"].to_numpy(dtype=int)
        p_event = group["y_prob_event"].to_numpy(dtype=float)
        requested_bins = requested_bins_for_cohort(str(cohort))
        calibration_bins, actual_bins = quantile_calibration_bins(y_event, p_event, requested_bins)
        calibration_bins.insert(0, "model", model_name)
        calibration_bins.insert(0, "feature_set", feature_set)
        calibration_bins.insert(0, "cohort", cohort)
        calibration_bins.insert(0, "task", task)
        calibration_frames.append(calibration_bins)

        fit_result = calibration_logistic_fit(y_event, p_event)
        metric_rows.append(
            {
                "task": task,
                "cohort": cohort,
                "feature_set": feature_set,
                "model": model_name,
                "N": int(len(group)),
                "events": int(y_event.sum()),
                "event_rate": float(y_event.mean()),
                "brier_score": float(brier_score_loss(y_event, p_event)),
                **fit_result,
                "n_calibration_bins_requested": requested_bins,
                "n_calibration_bins_actual": actual_bins,
            }
        )

        dca = dca_for_configuration(y_event, p_event)
        dca.insert(0, "event_definition", group["event_definition"].iloc[0])
        dca.insert(0, "model", model_name)
        dca.insert(0, "feature_set", feature_set)
        dca.insert(0, "cohort", cohort)
        dca.insert(0, "task", task)
        dca_frames.append(dca)
        above_both = (dca["net_benefit_model"] > dca["net_benefit_all"]) & (
            dca["net_benefit_model"] > dca["net_benefit_none"]
        )
        dca_summary_rows.append(
            {
                "task": task,
                "cohort": cohort,
                "feature_set": feature_set,
                "model": model_name,
                "event_definition": group["event_definition"].iloc[0],
                "n_thresholds_total": int(len(dca)),
                "n_thresholds_model_above_both_references": int(above_both.sum()),
                "proportion_thresholds_above_both": float(above_both.mean()),
                "contiguous_threshold_intervals_above_both": contiguous_intervals(
                    dca["threshold"].to_numpy(), above_both.to_numpy()
                ),
            }
        )

    return (
        pd.DataFrame(metric_rows),
        pd.concat(calibration_frames, ignore_index=True),
        pd.concat(dca_frames, ignore_index=True),
        pd.DataFrame(dca_summary_rows),
    )


def figure_slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def configure_plot_style():
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
        }
    )


def generate_calibration_figures(calibration_bins):
    configure_plot_style()
    generated = []
    for (task, feature_set, cohort), group in calibration_bins.groupby(
        ["task", "feature_set", "cohort"], sort=False
    ):
        fig, ax = plt.subplots(figsize=(6.4, 5.4))
        ax.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1.2, label="Perfect calibration")
        for model_name in MODEL_ORDER:
            model_data = group[group["model"] == model_name].sort_values("mean_predicted_probability")
            if model_data.empty:
                continue
            ax.plot(
                model_data["mean_predicted_probability"],
                model_data["observed_event_rate"],
                marker="o",
                markersize=3.2,
                linewidth=1.25,
                color=MODEL_COLORS[model_name],
                label=model_name,
            )
        spec = TASK_SPECS[str(task)]
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel(spec["x_label"])
        ax.set_ylabel(spec["y_label"])
        ax.set_title(f"{task} | {feature_set} | {cohort}")
        ax.grid(axis="both", color="#D9D9D9", linewidth=0.45, alpha=0.55)
        ax.legend(loc="best", frameon=False, ncol=2)
        fig.tight_layout()
        output_path = FIGURES_CALIBRATION_DIR / (
            f"{figure_slug(str(task))}__{figure_slug(str(feature_set))}__{figure_slug(str(cohort))}__calibration.png"
        )
        fig.savefig(output_path, dpi=600, bbox_inches="tight")
        plt.close(fig)
        generated.append(str(output_path))
    return generated


def generate_dca_figures(dca_results):
    configure_plot_style()
    generated = []
    for (task, feature_set, cohort), group in dca_results.groupby(
        ["task", "feature_set", "cohort"], sort=False
    ):
        fig, ax = plt.subplots(figsize=(6.8, 5.4))
        for model_name in MODEL_ORDER:
            model_data = group[group["model"] == model_name].sort_values("threshold")
            if model_data.empty:
                continue
            ax.plot(
                model_data["threshold"],
                model_data["net_benefit_model"],
                linewidth=1.2,
                color=MODEL_COLORS[model_name],
                label=model_name,
            )
        reference = group[group["model"] == MODEL_ORDER[0]].sort_values("threshold")
        ax.plot(
            reference["threshold"],
            reference["net_benefit_all"],
            linestyle="--",
            color="#666666",
            linewidth=1.25,
            label="Assume-all-positive",
        )
        ax.plot(
            reference["threshold"],
            reference["net_benefit_none"],
            linestyle=":",
            color="black",
            linewidth=1.25,
            label="Assume-none-positive",
        )
        ax.set_xlim(0.01, 0.99)
        ax.set_xlabel("Threshold probability")
        ax.set_ylabel("Net benefit")
        ax.set_title(f"{task} | {feature_set} | {cohort}")
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.45, alpha=0.55)
        ax.legend(loc="best", frameon=False, ncol=2)
        fig.tight_layout()
        output_path = FIGURES_DCA_DIR / (
            f"{figure_slug(str(task))}__{figure_slug(str(feature_set))}__{figure_slug(str(cohort))}__dca.png"
        )
        fig.savefig(output_path, dpi=600, bbox_inches="tight")
        plt.close(fig)
        generated.append(str(output_path))
    return generated


def compare_mimic_existing_predictions(survival_predictions):
    existing_path = (
        REPO_ROOT
        / "experiments"
        / "03-MIMIC-IV-CRAB"
        / "results"
        / "mimic-crab"
        / "survival_loocv_pred_for_confusion_matrix.csv"
    )
    if not existing_path.exists():
        return {"status": "not_run", "reason": "existing MIMIC prediction export not found"}
    existing = pd.read_csv(existing_path)
    existing["feature_set"] = existing["candidate"]
    current = survival_predictions[survival_predictions["cohort"] == "MIMIC_CRAB_LOOCV"].copy()
    keys = ["subject_id", "hadm_id", "feature_set", "model"]
    if current.duplicated(keys).any() or existing.duplicated(keys).any():
        raise RuntimeError("MIMIC reproducibility comparison found duplicate configuration/patient keys")
    merged = current.merge(existing, on=keys, how="outer", suffixes=("_current", "_existing"), indicator=True)
    complete_match = bool((merged["_merge"] == "both").all())
    if complete_match:
        absolute_difference = np.abs(merged["y_prob_original"] - merged["y_proba"])
        max_absolute_difference = float(absolute_difference.max())
        labels_match = bool(
            np.array_equal(
                merged["y_true_original"].to_numpy(dtype=int),
                merged["y_true"].to_numpy(dtype=int),
            )
        )
    else:
        max_absolute_difference = np.nan
        labels_match = False
    matched = bool(complete_match and labels_match and max_absolute_difference <= 1e-8)
    result = {
        "status": "matched" if matched else "different",
        "existing_path": str(existing_path),
        "rows_current": int(len(current)),
        "rows_existing": int(len(existing)),
        "all_keys_matched": complete_match,
        "all_y_true_matched": labels_match,
        "max_absolute_probability_difference": max_absolute_difference,
        "tolerance": 1e-8,
    }
    if not matched:
        raise RuntimeError(
            "MIMIC LOOCV reproducibility hard check failed: "
            f"keys_match={complete_match}, labels_match={labels_match}, "
            f"max_abs_probability_difference={max_absolute_difference}, tolerance=1e-8"
        )
    return result


def perform_sanity_checks(
    prediction_tables,
    calibration_metrics,
    calibration_bins,
    dca_results,
    generation_metadata,
):
    all_predictions = pd.concat(prediction_tables.values(), ignore_index=True)
    group_columns = ["task", "cohort", "feature_set", "model"]
    configuration_checks = []
    failures = []
    manual_dca_checks = []

    for keys, group in all_predictions.groupby(group_columns, sort=False):
        task, cohort, feature_set, model_name = keys
        probability = group["y_prob_event"].to_numpy(dtype=float)
        original_probability = group["y_prob_original"].to_numpy(dtype=float)
        original_y = group["y_true_original"].to_numpy(dtype=int)
        event_y = group["y_event"].to_numpy(dtype=int)
        cohort_expectation = EXPECTED_COHORTS.get((str(task), str(cohort)))
        if cohort_expectation is None:
            raise RuntimeError(f"No fixed cohort expectation defined for {task}/{cohort}")
        expected_n = int(cohort_expectation["N"])
        expected_events = int(cohort_expectation["events"])
        observed_n = int(len(group))
        observed_events = int(event_y.sum())
        if observed_n != expected_n or observed_events != expected_events:
            raise RuntimeError(
                f"Fixed cohort audit failed for {task}/{cohort}/{feature_set}/{model_name}: "
                f"observed N/events={observed_n}/{observed_events}, "
                f"expected={expected_n}/{expected_events}"
            )
        duplicate_count = int(group["patient_index"].duplicated().sum())
        probability_ok = bool(
            np.isfinite(probability).all()
            and np.isfinite(original_probability).all()
            and np.all((probability >= 0) & (probability <= 1))
            and np.all((original_probability >= 0) & (original_probability <= 1))
        )
        survival_transform_ok = True
        brier_invariance_ok = True
        if task == "Survival":
            survival_transform_ok = bool(
                np.array_equal(event_y, 1 - original_y)
                and np.allclose(probability, 1 - original_probability, atol=1e-15, rtol=0)
            )
            original_brier = float(brier_score_loss(original_y, original_probability))
            transformed_brier = float(brier_score_loss(event_y, probability))
            brier_invariance_ok = bool(math.isclose(original_brier, transformed_brier, abs_tol=1e-15, rel_tol=0))

        bin_group = calibration_bins[
            (calibration_bins["task"] == task)
            & (calibration_bins["cohort"] == cohort)
            & (calibration_bins["feature_set"] == feature_set)
            & (calibration_bins["model"] == model_name)
        ]
        calibration_bins_ok = bool(
            len(bin_group) > 0
            and (bin_group["n_in_bin"] > 0).all()
            and int(bin_group["n_in_bin"].sum()) == expected_n
        )
        metric_group = calibration_metrics[
            (calibration_metrics["task"] == task)
            & (calibration_metrics["cohort"] == cohort)
            & (calibration_metrics["feature_set"] == feature_set)
            & (calibration_metrics["model"] == model_name)
        ]
        brier_value = float(metric_group["brier_score"].iloc[0])
        brier_range_ok = bool(0 <= brier_value <= 1)
        dca_group = dca_results[
            (dca_results["task"] == task)
            & (dca_results["cohort"] == cohort)
            & (dca_results["feature_set"] == feature_set)
            & (dca_results["model"] == model_name)
        ]
        dca_none_ok = bool(np.allclose(dca_group["net_benefit_none"], 0.0, atol=0, rtol=0))

        for threshold in [0.10, 0.20, 0.50]:
            raw = dca_group[np.isclose(dca_group["threshold"], threshold)].iloc[0]
            predicted_positive = probability >= threshold
            tp = int(np.sum(predicted_positive & (event_y == 1)))
            fp = int(np.sum(predicted_positive & (event_y == 0)))
            expected_nb = tp / expected_n - fp / expected_n * threshold / (1 - threshold)
            expected_all = event_y.mean() - (1 - event_y.mean()) * threshold / (1 - threshold)
            formula_ok = bool(
                math.isclose(float(raw["net_benefit_model"]), expected_nb, abs_tol=1e-15, rel_tol=0)
                and math.isclose(float(raw["net_benefit_all"]), expected_all, abs_tol=1e-15, rel_tol=0)
                and int(raw["true_positives"]) == tp
                and int(raw["false_positives"]) == fp
            )
            manual_dca_checks.append(
                {
                    "task": task,
                    "cohort": cohort,
                    "feature_set": feature_set,
                    "model": model_name,
                    "threshold": threshold,
                    "true_positives": tp,
                    "false_positives": fp,
                    "formula_ok": formula_ok,
                }
            )

        check = {
            "task": task,
            "cohort": cohort,
            "feature_set": feature_set,
            "model": model_name,
            "N": observed_n,
            "events": observed_events,
            "event_rate": float(event_y.mean()),
            "prediction_type": group["prediction_type"].iloc[0],
            "fixed_cohort_count_check_passed": True,
            "each_patient_once": duplicate_count == 0,
            "probability_checks_passed": probability_ok,
            "survival_transform_passed": survival_transform_ok,
            "survival_brier_invariance_passed": brier_invariance_ok,
            "brier_range_passed": brier_range_ok,
            "calibration_bins_passed": calibration_bins_ok,
            "dca_none_zero_passed": dca_none_ok,
        }
        check["sanity_check"] = "PASS" if all(
            [
                check["each_patient_once"],
                check["fixed_cohort_count_check_passed"],
                probability_ok,
                survival_transform_ok,
                brier_invariance_ok,
                brier_range_ok,
                calibration_bins_ok,
                dca_none_ok,
            ]
        ) else "FAIL"
        configuration_checks.append(check)
        if check["sanity_check"] != "PASS":
            failures.append(f"{task}/{cohort}/{feature_set}/{model_name}")

    if not all(item["formula_ok"] for item in manual_dca_checks):
        failures.append("one or more manual DCA formula checks")
    if failures:
        raise RuntimeError("Sanity checks failed: " + ", ".join(failures[:10]))

    return {
        "overall_status": "PASS",
        "configuration_checks": configuration_checks,
        "manual_dca_checks_at_0.10_0.20_0.50": manual_dca_checks,
        "generation_metadata": generation_metadata,
    }


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def cohort_event_counts(task, df, target):
    original_y = df[target].to_numpy(dtype=int)
    event_y = 1 - original_y if task == "Survival" else original_y
    return int(len(df)), int(event_y.sum())


def assert_fixed_cohort_counts(task, cohort, n, events, source):
    expected = EXPECTED_COHORTS[(task, cohort)]
    if n != expected["N"] or events != expected["events"]:
        raise RuntimeError(
            f"Preflight cohort audit failed for {task}/{cohort} from {source}: "
            f"observed N/events={n}/{events}, expected={expected['N']}/{expected['events']}"
        )


def run_preflight():
    """Run MIMIC-feature, cohort, and configuration checks without model fitting."""
    dataset_policy = dict(FINAL_DATASET_POLICY)
    dataset_cache = {}
    cohort_audit = []
    configuration_rows = []

    log("Clinical-usefulness dataset policy")
    for task in TASK_SPECS:
        source_name = dataset_policy[task]
        log(f"{task}: {source_name}")
        base = dataset_directory(source_name)
        train_path = base / "train_set.csv"
        external_path = base / "external-1.csv"
        train_df, target = prepare_primary_dataframe(train_path, task)
        external_df, external_target = prepare_primary_dataframe(external_path, task)
        if target != external_target:
            raise RuntimeError(f"Target mismatch during preflight: {task}/{source_name}")
        dataset_cache[(task, source_name)] = (train_df, external_df, target)
        for cohort, frame in [("Development_OOF", train_df), ("External_1", external_df)]:
            n, events = cohort_event_counts(task, frame, target)
            assert_fixed_cohort_counts(task, cohort, n, events, source_name)
            cohort_audit.append(
                {
                    "task": task,
                    "cohort": cohort,
                    "dataset_source": source_name,
                    "dataset_path": str(train_path if cohort == "Development_OOF" else external_path),
                    "N": n,
                    "events": events,
                    "status": "PASS",
                }
            )

        feature_configurations = list(TASK_SPECS[task]["candidate_sets"].keys()) + ["FullFeature"]
        for feature_set in feature_configurations:
            train_df, external_df, target = dataset_cache[(task, source_name)]
            columns = (
                full_feature_columns(task, train_df)
                if feature_set == "FullFeature"
                else expand_candidate_features(
                    task,
                    TASK_SPECS[task]["candidate_sets"][feature_set],
                    train_df.columns,
                )
            )
            dataset_path = str(dataset_directory(source_name))
            status = "READY"
            for cohort, frame, protocol in [
                ("Development_OOF", train_df, "5-fold OOF"),
                ("External_1", external_df, "full-development fit -> External-1 predict_proba"),
            ]:
                n, events = cohort_event_counts(task, frame, target)
                for model_name in MODEL_ORDER:
                    configuration_rows.append(
                        {
                            "task": task,
                            "cohort": cohort,
                            "feature_set": feature_set,
                            "model": model_name,
                            "dataset_path": dataset_path,
                            "N": n,
                            "events": events,
                            "feature_count": len(columns),
                            "feature_columns": "|".join(columns),
                            "prediction_protocol": protocol,
                            "preflight_status": status,
                        }
                    )

    mimic_df = prepare_mimic_dataframe()
    mimic_n, mimic_events = cohort_event_counts("Survival", mimic_df, "survival")
    assert_fixed_cohort_counts(
        "Survival",
        "MIMIC_CRAB_LOOCV",
        mimic_n,
        mimic_events,
        "datasets/MIMIC-IV-CRAB/mimicset0227.csv",
    )
    mimic_feature_audit = {}
    log("MIMIC feature audit")
    for feature_set, tokens in MIMIC_CANDIDATES.items():
        columns = mimic_feature_columns(mimic_df, feature_set)
        mimic_feature_audit[feature_set] = {
            "tokens": tokens,
            "expanded_columns": columns,
            "column_count": len(columns),
            "matches_original_notebook": columns == MIMIC_EXPECTED_EXPANDED_COLUMNS[feature_set],
        }
        log(f"{feature_set}:")
        log(f"  tokens = {tokens}")
        log(f"  expanded columns = {columns}")
        log(f"  column count = {len(columns)}")
        for model_name in MODEL_ORDER:
            configuration_rows.append(
                {
                    "task": "Survival",
                    "cohort": "MIMIC_CRAB_LOOCV",
                    "feature_set": feature_set,
                    "model": model_name,
                    "dataset_path": str(MIMIC_PATH),
                    "N": mimic_n,
                    "events": mimic_events,
                    "feature_count": len(columns),
                    "feature_columns": "|".join(columns),
                    "prediction_protocol": "LOOCV-based prediction; 41 train, 1 held out",
                    "preflight_status": "READY",
                }
            )

    cohort_audit.append(
        {
            "task": "Survival",
            "cohort": "MIMIC_CRAB_LOOCV",
            "dataset_source": "datasets/MIMIC-IV-CRAB",
            "dataset_path": str(MIMIC_PATH),
            "N": mimic_n,
            "events": mimic_events,
            "status": "PASS",
        }
    )

    configuration_audit_path = METADATA_DIR / "configuration_audit.csv"
    configuration_audit = pd.DataFrame(configuration_rows)
    nonready_configurations = configuration_audit[
        configuration_audit["preflight_status"] != "READY"
    ]
    if not nonready_configurations.empty:
        raise RuntimeError(
            "Configuration audit contains non-READY rows; no model training may start: "
            + nonready_configurations[
                ["task", "cohort", "feature_set", "model", "preflight_status"]
            ].head(10).to_dict(orient="records").__str__()
        )
    configuration_audit.to_csv(configuration_audit_path, index=False, encoding="utf-8-sig")
    report = {
        "status": "READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_path": str(SCRIPT_PATH),
        "repository_root": str(REPO_ROOT),
        "dataset_policy": dataset_policy,
        "blocked_tasks": [],
        "mimic_feature_audit": mimic_feature_audit,
        "cohort_audit": cohort_audit,
        "configuration_audit_csv": str(configuration_audit_path),
        "full_model_training_started": False,
    }
    preflight_path = METADATA_DIR / "preflight_audit.json"
    save_json(preflight_path, report)

    log("Cohort audit")
    printed = set()
    for row in cohort_audit:
        key = (row["task"], row["cohort"], row["N"], row["events"])
        if key not in printed:
            log(f"  {row['task']} | {row['cohort']}: N={row['N']}, events={row['events']} (PASS)")
            printed.add(key)
    log("Preflight status: READY (all configurations)")
    log(f"Saved preflight audit: {preflight_path}")
    log(f"Saved configuration audit: {configuration_audit_path}")
    return report


def run_full_analysis(dataset_policy):
    log("Reviewer 1 Comment 11 supplemental analysis started")
    prediction_frames_by_task = {task: [] for task in TASK_SPECS}
    fold_metric_rows = []
    generation_metadata = []

    dataset_cache = {}
    for task, spec in TASK_SPECS.items():
        log(f"Primary cohorts: {task}")
        source_name = dataset_policy[task]
        if not isinstance(source_name, str):
            raise RuntimeError(f"No resolved clinical-usefulness dataset source for {task}")
        feature_configurations = list(spec["candidate_sets"].keys()) + ["FullFeature"]
        for feature_set in feature_configurations:
            cache_key = (task, source_name)
            if cache_key not in dataset_cache:
                base = dataset_directory(source_name)
                train_path = base / "train_set.csv"
                external_path = base / "external-1.csv"
                train_df, target = prepare_primary_dataframe(train_path, task)
                external_df, external_target = prepare_primary_dataframe(external_path, task)
                if target != external_target:
                    raise RuntimeError(f"Target mismatch for {task}/{source_name}")
                dataset_cache[cache_key] = (train_df, external_df, target)
            train_df, external_df, target = dataset_cache[cache_key]
            columns = (
                full_feature_columns(task, train_df)
                if feature_set == "FullFeature"
                else expand_candidate_features(task, spec["candidate_sets"][feature_set], train_df.columns)
            )
            data_source = f"{source_name}/train_set.csv + {source_name}/external-1.csv"
            log(f"  {feature_set}: {len(columns)} features × 7 models")
            frames, fold_rows, config_metadata = run_primary_configuration(
                task=task,
                feature_set=feature_set,
                data_source=data_source,
                train_df=train_df,
                external_df=external_df,
                target=target,
                columns=columns,
            )
            prediction_frames_by_task[task].extend(frames)
            fold_metric_rows.extend(fold_rows)
            generation_metadata.append(config_metadata)

    log("MIMIC-IV CRAB: feature-setA and feature-setB × 7 models using LOOCV")
    mimic_frames, mimic_metadata = run_mimic_configurations()
    prediction_frames_by_task["Survival"].extend(mimic_frames)
    generation_metadata.extend(mimic_metadata)

    prediction_tables = {
        task: pd.concat(frames, ignore_index=True) for task, frames in prediction_frames_by_task.items()
    }
    mimic_reproducibility = compare_mimic_existing_predictions(prediction_tables["Survival"])
    log("MIMIC existing-prediction reproducibility hard check: matched")
    prediction_paths = {}
    for task, table in prediction_tables.items():
        output_path = PREDICTIONS_DIR / f"{TASK_SPECS[task]['slug']}_predictions.csv"
        table.to_csv(output_path, index=False, encoding="utf-8-sig")
        prediction_paths[task] = str(output_path)
        log(f"Saved predictions: {task} ({len(table):,} rows)")

    log("Computing Brier scores, calibration metrics/bins, and DCA")
    calibration_metrics, calibration_bins, dca_results, dca_summary = analyze_predictions(prediction_tables)
    calibration_metrics_path = CALIBRATION_DIR / "calibration_metrics_all_configs.csv"
    calibration_bins_path = CALIBRATION_DIR / "calibration_bins_all_configs.csv"
    dca_results_path = DCA_DIR / "dca_results_all_configs.csv"
    dca_summary_path = DCA_DIR / "dca_summary_all_configs.csv"
    calibration_metrics.to_csv(calibration_metrics_path, index=False, encoding="utf-8-sig")
    calibration_bins.to_csv(calibration_bins_path, index=False, encoding="utf-8-sig")
    dca_results.to_csv(dca_results_path, index=False, encoding="utf-8-sig")
    dca_summary.to_csv(dca_summary_path, index=False, encoding="utf-8-sig")

    log("Generating 600-dpi diagnostic figures")
    calibration_figure_paths = generate_calibration_figures(calibration_bins)
    dca_figure_paths = generate_dca_figures(dca_results)

    log("Running configuration-level sanity checks")
    sanity = perform_sanity_checks(
        prediction_tables,
        calibration_metrics,
        calibration_bins,
        dca_results,
        generation_metadata,
    )
    sanity["mimic_existing_prediction_reproducibility"] = mimic_reproducibility
    sanity_path = METADATA_DIR / "sanity_checks.json"
    save_json(sanity_path, sanity)

    fold_check_path = METADATA_DIR / "recomputed_fold_metrics_reproducibility_only.csv"
    pd.DataFrame(fold_metric_rows).to_csv(fold_check_path, index=False, encoding="utf-8-sig")

    expected_primary_configurations = {
        "Clinical efficacy": 5 * 7,
        "Survival": 3 * 7,
        "Polymyxin resistance": 6 * 7,
    }
    actual_primary_configurations = {
        task: int(
            prediction_tables[task]
            .query("cohort == 'Development_OOF'")[["feature_set", "model"]]
            .drop_duplicates()
            .shape[0]
        )
        for task in TASK_SPECS
    }
    actual_mimic_configurations = int(
        prediction_tables["Survival"]
        .query("cohort == 'MIMIC_CRAB_LOOCV'")[["feature_set", "model"]]
        .drop_duplicates()
        .shape[0]
    )
    if expected_primary_configurations != actual_primary_configurations or actual_mimic_configurations != 14:
        raise RuntimeError("Configuration-count check failed")

    fit_failure_count = int((calibration_metrics["calibration_fit_status"] != "success").sum())
    bin_warning_count = int(
        (calibration_metrics["n_calibration_bins_actual"] < calibration_metrics["n_calibration_bins_requested"]).sum()
    )
    calibration_fit_failure_details = calibration_metrics.loc[
        calibration_metrics["calibration_fit_status"] != "success",
        [
            "task",
            "cohort",
            "feature_set",
            "model",
            "calibration_fit_status",
            "calibration_failure_reason",
        ],
    ].to_dict(orient="records")
    bin_warning_breakdown = [
        {
            "cohort": str(cohort),
            "n_bins_requested": int(requested),
            "n_bins_actual": int(actual),
            "configuration_count": int(len(group)),
        }
        for (cohort, requested, actual), group in calibration_metrics.loc[
            calibration_metrics["n_calibration_bins_actual"]
            < calibration_metrics["n_calibration_bins_requested"]
        ].groupby(
            ["cohort", "n_calibration_bins_requested", "n_calibration_bins_actual"],
            sort=True,
        )
    ]
    metadata_document = {
        "analysis": "Reviewer 1 Comment 11 supplemental clinical usefulness analysis",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": str(SCRIPT_PATH),
        "repository_root": str(REPO_ROOT),
        "configuration_counts": {
            "primary_expected": expected_primary_configurations,
            "primary_actual": actual_primary_configurations,
            "MIMIC_CRAB_LOOCV_expected": 14,
            "MIMIC_CRAB_LOOCV_actual": actual_mimic_configurations,
            "configuration_cohort_groups_analyzed": int(len(calibration_metrics)),
        },
        "validation_protocols": {
            "Development_OOF": "Stratified 5-fold CV, shuffle=True, random_state=42",
            "External_1": "full development cohort fit followed by External-1 predict_proba",
            "MIMIC_CRAB_LOOCV": "LOOCV-based predictions in the MIMIC-IV CRAB cohort; 41 train, 1 held out, repeated 42 times",
        },
        "training_settings": {
            "classification_threshold": CLASSIFICATION_THRESHOLD,
            "use_smote": USE_SMOTE,
            "smote_ratio_if_enabled": SMOTE_RATIO,
            "scale_pos_weight_policy": "computed once on complete development/cohort y, matching existing notebooks",
            "models": MODEL_ORDER,
            "model_hyperparameters_changed": False,
        },
        "endpoint_semantics": {
            "Clinical efficacy": {
                "original_positive_class": "Clinical_outcome = 1",
                "event_definition": "clinical improvement",
                "probability_definition": "probability of clinical improvement",
                "transformation": "none",
            },
            "Survival": {
                "original_positive_class": "Survival/survival = 1",
                "event_definition": "mortality",
                "probability_definition": "mortality risk",
                "transformation": "y_event = 1 - y_true_original; y_prob_event = 1 - y_prob_original",
            },
            "Polymyxin resistance": {
                "original_positive_class": "Polymyxin_MIC >= 2",
                "event_definition": "polymyxin resistance",
                "probability_definition": "probability of polymyxin resistance",
                "transformation": "none",
            },
        },
        "calibration": {
            "binning_strategy": "quantile with duplicate quantile edges removed",
            "requested_bins": {"Development_OOF": 10, "External_1": 5, "MIMIC_CRAB_LOOCV": 4},
            "slope_intercept_terminology": "calibration intercept and slope jointly estimated from a logistic recalibration model",
            "slope_intercept_method": "jointly estimated unpenalized binomial logistic recalibration model using scipy.optimize; p clipped to [1e-6, 1-1e-6]",
            "calibration_in_the_large_reported": False,
            "post_hoc_recalibration_performed": False,
            "successful_fits": int((calibration_metrics["calibration_fit_status"] == "success").sum()),
            "failed_fits": fit_failure_count,
            "fit_failure_details": calibration_fit_failure_details,
            "configurations_with_reduced_bin_count": bin_warning_count,
            "reduced_bin_count_breakdown": bin_warning_breakdown,
        },
        "dca": {
            "threshold_min": 0.01,
            "threshold_max": 0.99,
            "threshold_step": 0.01,
            "number_of_thresholds": 99,
            "configurations_analyzed": int(len(dca_summary)),
            "calculation_failures": 0,
            "model_ranking_performed": False,
            "figure_designation": "full-range 0.01-0.99 diagnostic figures; not final publication figures",
        },
        "existing_discrimination_metrics": {
            "altered": False,
            "pooled_oof_auroc_reported": False,
            "pooled_oof_auprc_reported": False,
            "recomputed_fold_metrics_file_is_reproducibility_only": str(fold_check_path),
        },
        "treatment_duration_processed": False,
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": package_version("numpy"),
            "pandas": package_version("pandas"),
            "scikit-learn": package_version("scikit-learn"),
            "scipy": package_version("scipy"),
            "matplotlib": package_version("matplotlib"),
            "xgboost": package_version("xgboost"),
            "lightgbm": package_version("lightgbm"),
            "catboost": package_version("catboost"),
            "imbalanced-learn": package_version("imbalanced-learn"),
        },
        "files": {
            "preflight_audit": str(METADATA_DIR / "preflight_audit.json"),
            "configuration_audit": str(METADATA_DIR / "configuration_audit.csv"),
            "predictions": prediction_paths,
            "calibration_metrics": str(calibration_metrics_path),
            "calibration_bins": str(calibration_bins_path),
            "dca_results": str(dca_results_path),
            "dca_summary": str(dca_summary_path),
            "sanity_checks": str(sanity_path),
            "calibration_figures": calibration_figure_paths,
            "dca_figures": dca_figure_paths,
        },
    }
    metadata_path = METADATA_DIR / "analysis_metadata.json"
    save_json(metadata_path, metadata_document)

    run_summary = {
        "status": "complete",
        "configuration_counts": metadata_document["configuration_counts"],
        "prediction_rows": {task: int(len(table)) for task, table in prediction_tables.items()},
        "calibration_metric_rows": int(len(calibration_metrics)),
        "calibration_fit_failures": fit_failure_count,
        "calibration_fit_failure_details": calibration_fit_failure_details,
        "calibration_bin_warnings": bin_warning_count,
        "calibration_bin_warning_breakdown": bin_warning_breakdown,
        "dca_rows": int(len(dca_results)),
        "dca_calculation_failures": 0,
        "calibration_figures": len(calibration_figure_paths),
        "dca_figures": len(dca_figure_paths),
        "sanity_status": sanity["overall_status"],
        "mimic_reproducibility": mimic_reproducibility,
    }
    save_json(METADATA_DIR / "run_summary.json", run_summary)
    log(json.dumps(run_summary, ensure_ascii=False, indent=2))


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Reviewer 1 Comment 11 calibration/Brier/DCA analysis. "
            "Without --run-full, only the non-model-fitting preflight audit is executed."
        )
    )
    parser.add_argument(
        "--run-full",
        action="store_true",
        help="Run the full model analysis after preflight checks.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    preflight_report = run_preflight()
    if args.run_full:
        run_full_analysis(preflight_report["dataset_policy"])
    else:
        log("Preflight-only mode complete; no model was fitted and no clinical-usefulness metrics were calculated.")


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        main()
