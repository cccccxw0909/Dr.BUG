"""Phase 2/4: Feature pre-study and model training (ProgrammerAgent)."""

from __future__ import annotations

import logging
from itertools import combinations
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.model_selection import (
    KFold,
    RandomizedSearchCV,
    StratifiedKFold,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..utils.metrics import (
    get_metrics_for_task,
    get_primary_metric,
    get_scoring_string,
    evaluate_classification,
    evaluate_regression,
)
from ..utils.shap_utils import (
    TREE_MODELS,
    compute_global_importance,
    rank_features,
    plot_shap_bar,
    plot_shap_interaction_heatmap,
    plot_shap_bar_beeswarm_rose,
    _normalize_shap_values_2d,
    _set_chart_font,
    _ensure_shap_2d,
    _sample_indices,
    shap_raw_type_and_shape,
)

logger = logging.getLogger(__name__)
RANDOM_STATE = 42


def _shap_export_reason_suffix(exc: BaseException) -> str:
    msg = str(exc).strip().replace("\n", " ").replace(";", ",")
    if len(msg) > 180:
        msg = msg[:180] + "..."
    return msg


def _describe_raw_shap_values_for_debug(shap_vals: Any) -> str:
    if isinstance(shap_vals, list):
        shapes = [tuple(np.asarray(x).shape) for x in shap_vals]
        return f"list,len={len(shap_vals)},elem_shapes={shapes}"
    if hasattr(shap_vals, "shape"):
        try:
            return f"shape={tuple(shap_vals.shape)}"
        except (TypeError, ValueError):
            pass
    return f"type={type(shap_vals).__name__}"


def _shap_export_task_reason(
    base_reason: str,
    *,
    model_name: str,
    plot_type: str,
    shap_vals_raw: Any,
    normalized: Optional[np.ndarray],
    X_input: np.ndarray,
    feature_names_len: int,
) -> str:
    """Structured SHAP skip/failure line for task_repo.append_log (logs.jsonl)."""
    rt, rs = shap_raw_type_and_shape(shap_vals_raw)
    ns: Any = tuple(normalized.shape) if normalized is not None else "N/A"
    return (
        f"{base_reason}|model={model_name}|plot_type={plot_type}|raw_type={rt}|raw_shape={rs}|"
        f"normalized_shape={ns}|X_shape={tuple(X_input.shape)}|feature_names_len={feature_names_len}"
    )


def _log_shap_xgb_lgb_parse_debug(
    model_name: str,
    plot_kind: str,
    shap_vals_raw: Any,
    X_input: np.ndarray,
    n_feature_names: int,
    post_ensure: Optional[np.ndarray] = None,
) -> None:
    if model_name not in ("XGBoost", "LightGBM"):
        return
    line1 = (
        "SHAP parse debug [%s] %s: raw_type=%s raw_%s X_shape=%s feature_names=%s"
        % (
            model_name,
            plot_kind,
            type(shap_vals_raw).__name__,
            _describe_raw_shap_values_for_debug(shap_vals_raw),
            tuple(X_input.shape),
            n_feature_names,
        )
    )
    logger.debug(line1)
    if post_ensure is not None:
        logger.debug(
            "SHAP parse debug [%s] %s post_ensure: ndim=%s shape=%s",
            model_name,
            plot_kind,
            post_ensure.ndim,
            getattr(post_ensure, "shape", None),
        )


def _get_scale_pos_weight(y: pd.Series) -> float:
    """Compute scale_pos_weight for binary classification."""
    counts = y.value_counts()
    if len(counts) < 2:
        return 1.0
    neg, pos = counts.get(0, 0), counts.get(1, 0)
    if pos == 0:
        return 1.0
    return neg / pos


def _safe_binary_base_score(y: pd.Series) -> float:
    """Compute logistic base_score and clip to strict open interval (0,1)."""
    try:
        rate = float(pd.Series(y).mean())
    except Exception:
        rate = 0.5
    if not np.isfinite(rate):
        rate = 0.5
    eps = 1e-6
    return float(np.clip(rate, eps, 1.0 - eps))


def _get_optimal_n_splits(y: pd.Series, max_splits: int = 5, min_samples_per_class: int = 2) -> int:
    """
    Calculate optimal n_splits for StratifiedKFold based on class distribution.
    Ensures each class has at least min_samples_per_class samples in each fold.
    """
    if y is None or len(y) == 0:
        return max_splits
    counts = y.value_counts()
    if len(counts) == 0:
        return max_splits
    min_class_count = counts.min()
    # Each fold should have at least min_samples_per_class samples from the smallest class
    optimal_splits = min(max_splits, min_class_count // min_samples_per_class)
    return max(2, optimal_splits)  # At least 2 folds


def _get_models_binary(scale_pos_weight: float = 1.0, base_score: float = 0.5) -> Dict[str, Any]:
    """Binary classification models with class_weight/scale_pos_weight."""
    models = {}
    models["LogisticRegression"] = __import__("sklearn.linear_model", fromlist=["LogisticRegression"]).LogisticRegression(
        class_weight="balanced", random_state=RANDOM_STATE, max_iter=1000
    )
    models["RandomForest"] = __import__("sklearn.ensemble", fromlist=["RandomForestClassifier"]).RandomForestClassifier(
        class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1
    )
    models["KNN"] = __import__("sklearn.neighbors", fromlist=["KNeighborsClassifier"]).KNeighborsClassifier(n_jobs=1)
    models["SVM"] = __import__("sklearn.svm", fromlist=["SVC"]).SVC(
        class_weight="balanced", random_state=RANDOM_STATE, probability=True
    )
    try:
        models["XGBoost"] = __import__("xgboost", fromlist=["XGBClassifier"]).XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            base_score=base_score,
            objective="binary:logistic",
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
            random_state=RANDOM_STATE,
            n_jobs=1,
        )
    except ImportError:
        pass
    try:
        models["LightGBM"] = __import__("lightgbm", fromlist=["LGBMClassifier"]).LGBMClassifier(
            class_weight="balanced", verbosity=-1, random_state=RANDOM_STATE, n_jobs=1
        )
    except ImportError:
        pass
    try:
        models["CatBoost"] = __import__("catboost", fromlist=["CatBoostClassifier"]).CatBoostClassifier(
            auto_class_weights="Balanced", verbose=0, allow_writing_files=False, random_state=RANDOM_STATE, thread_count=1
        )
    except ImportError:
        pass
    return models


def _get_models_multiclass() -> Dict[str, Any]:
    """Multiclass classification models."""
    models = {}
    models["LogisticRegression"] = __import__("sklearn.linear_model", fromlist=["LogisticRegression"]).LogisticRegression(
        class_weight="balanced", random_state=RANDOM_STATE, max_iter=1000, multi_class="multinomial"
    )
    models["RandomForest"] = __import__("sklearn.ensemble", fromlist=["RandomForestClassifier"]).RandomForestClassifier(
        class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1
    )
    models["KNN"] = __import__("sklearn.neighbors", fromlist=["KNeighborsClassifier"]).KNeighborsClassifier(n_jobs=1)
    models["SVM"] = __import__("sklearn.svm", fromlist=["SVC"]).SVC(
        class_weight="balanced", random_state=RANDOM_STATE, probability=True
    )
    try:
        models["XGBoost"] = __import__("xgboost", fromlist=["XGBClassifier"]).XGBClassifier(
            eval_metric="mlogloss", verbosity=0, random_state=RANDOM_STATE, n_jobs=1
        )
    except ImportError:
        pass
    try:
        models["LightGBM"] = __import__("lightgbm", fromlist=["LGBMClassifier"]).LGBMClassifier(
            class_weight="balanced", verbosity=-1, random_state=RANDOM_STATE, n_jobs=1
        )
    except ImportError:
        pass
    try:
        models["CatBoost"] = __import__("catboost", fromlist=["CatBoostClassifier"]).CatBoostClassifier(
            auto_class_weights="Balanced", verbose=0, allow_writing_files=False, random_state=RANDOM_STATE, thread_count=1
        )
    except ImportError:
        pass
    return models


def _get_models_regression() -> Dict[str, Any]:
    """Regression models."""
    models = {}
    models["Ridge"] = __import__("sklearn.linear_model", fromlist=["Ridge"]).Ridge(random_state=RANDOM_STATE)
    models["RandomForest"] = __import__("sklearn.ensemble", fromlist=["RandomForestRegressor"]).RandomForestRegressor(
        random_state=RANDOM_STATE, n_jobs=1
    )
    models["KNN"] = __import__("sklearn.neighbors", fromlist=["KNeighborsRegressor"]).KNeighborsRegressor(n_jobs=1)
    models["SVR"] = __import__("sklearn.svm", fromlist=["SVR"]).SVR()
    try:
        models["XGBRegressor"] = __import__("xgboost", fromlist=["XGBRegressor"]).XGBRegressor(
            verbosity=0, random_state=RANDOM_STATE, n_jobs=1
        )
    except ImportError:
        pass
    try:
        models["LGBMRegressor"] = __import__("lightgbm", fromlist=["LGBMRegressor"]).LGBMRegressor(
            verbosity=-1, random_state=RANDOM_STATE, n_jobs=1
        )
    except ImportError:
        pass
    try:
        models["CatBoostRegressor"] = __import__("catboost", fromlist=["CatBoostRegressor"]).CatBoostRegressor(
            verbose=0, allow_writing_files=False, random_state=RANDOM_STATE, thread_count=1
        )
    except ImportError:
        pass
    return models


def _needs_scaler(model_name: str) -> bool:
    """
    Whether model needs StandardScaler.
    
    Tree models (XGBoost, LightGBM, CatBoost, RandomForest) do NOT need scaling.
    Only linear models and distance-based models need scaling.
    """
    # Tree models - no scaling needed
    tree_models = {"XGBoost", "LightGBM", "CatBoost", "RandomForest", 
                   "XGBRegressor", "LGBMRegressor", "CatBoostRegressor", "RandomForestRegressor"}
    if model_name in tree_models:
        return False
    # Linear and distance-based models - scaling needed
    return model_name in {"LogisticRegression", "KNN", "Ridge", "SVM", "SVR"}


def create_pipeline(model: Any, model_name: str) -> Pipeline:
    """Create sklearn Pipeline: imputer + optional scaler + model."""
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if _needs_scaler(model_name):
        steps.append(("scaler", StandardScaler()))
    steps.append(("clf", clone(model)))
    return Pipeline(steps)


def get_preprocess_transformer(pipe: Pipeline):
    """Get preprocessing transformer (all steps except the classifier)."""
    if "clf" not in pipe.named_steps:
        raise ValueError("Pipeline must have a 'clf' step.")
    return pipe[:-1]


def get_models_for_task(
    task_type: str,
    y: Optional[pd.Series] = None,
) -> Dict[str, Any]:
    """Get models dict for task type."""
    if task_type == "binary":
        sw = _get_scale_pos_weight(y) if y is not None else 1.0
        bs = _safe_binary_base_score(y) if y is not None else 0.5
        return _get_models_binary(sw, bs)
    if task_type == "multiclass":
        return _get_models_multiclass()
    return _get_models_regression()


class ProgrammerAgent:
    """Feature pre-study and model training."""

    def __init__(
        self,
        task_type: str = "binary",
        enable_search: bool = False,
        cv_folds: int = 5,
        random_state: int = RANDOM_STATE,
    ):
        self.task_type = task_type
        self.enable_search = enable_search
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.metrics_config = get_metrics_for_task(task_type)

    def run_global_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_names: Optional[List[str]] = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
        return_shap_data: bool = False,
        use_cv_shap: bool = False,
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Phase 2②: Global feature importance.
        
        Args:
            use_cv_shap: If True, use 5-fold CV SHAP mean (more robust but slower);
                        If False, use single 80/20 split (faster).
        
        Returns:
            If return_shap_data=False: {model_name: [(feature, importance), ...]}
            If return_shap_data=True: (importance_dict, shap_data_cache, stability_dict)
                where stability_dict = {model_name: {feature: stability_score}}
                and stability_score is the frequency (0-1) of entering top 10 across folds
        """
        models = get_models_for_task(self.task_type, y)
        if model_names:
            models = {k: v for k, v in models.items() if k in model_names}
        
        if use_cv_shap:
            return self._run_global_importance_cv(
                X, y, models, on_progress, return_shap_data
            )
        else:
            return self._run_global_importance_single(
                X, y, models, on_progress, return_shap_data
            )
    
    def _run_global_importance_single(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        models: Dict[str, Any],
        on_progress: Optional[Callable[[float, str], None]],
        return_shap_data: bool,
    ):
        """Single 80/20 split mode (original implementation)."""
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state, stratify=y if self.task_type != "regression" else None
        )
        result = {}
        shap_data_cache = {}
        stability = {}
        model_list = list(models.items())
        for i, (name, model) in enumerate(model_list):
            if on_progress:
                on_progress((i + 1) / len(model_list), f"Computing {name} importance ({i+1}/{len(model_list)})")
            try:
                pipe = create_pipeline(model, name)
                pipe.fit(X_tr, y_tr)
                clf = pipe.named_steps["clf"]
                preprocess = get_preprocess_transformer(pipe)
                X_tr_t = preprocess.transform(X_tr)
                X_tr_t_df = pd.DataFrame(X_tr_t, columns=X.columns)
                X_val_t = preprocess.transform(X_val)
                X_val_t_df = pd.DataFrame(X_val_t, columns=X.columns)
                imp = compute_global_importance(
                    clf, name, X_val_t_df, y_val, self.task_type, X_train=X_tr_t_df
                )
                # Check if importance is all zeros
                if imp and all(v == 0.0 for v in imp.values()):
                    logger.warning("%s: Computed importance is all zeros. This may indicate a model training issue.", name)
                result[name] = rank_features(imp)
                stability[name] = {}  # No stability data in single split mode
                
                # Compute SHAP data for visualization if requested
                if return_shap_data:
                    shap_data = self._compute_shap_data_for_model(
                        clf, name, X_val_t, X_val_t_df, X.columns, X_tr_t, X_tr_t_df
                    )
                    if shap_data is not None:
                        shap_data_cache[name] = shap_data
            except Exception as e:
                logger.warning("Importance failed for %s: %s", name, e)
                import traceback
                logger.debug("Traceback: %s", traceback.format_exc())
                # Still add this model so the UI shows all models; use zero importance
                result[name] = rank_features({f: 0.0 for f in X.columns})
                stability[name] = {}
        
        if return_shap_data:
            return result, shap_data_cache, stability
        return result
    
    def _run_global_importance_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        models: Dict[str, Any],
        on_progress: Optional[Callable[[float, str], None]],
        return_shap_data: bool,
    ):
        """5-fold CV SHAP mean mode (more robust)."""
        from sklearn.model_selection import StratifiedKFold, KFold
        
        if self.task_type == "regression":
            kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
            split_indices = list(kf.split(X, y))
        else:
            kf = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
            split_indices = list(kf.split(X, y))
        
        result = {}
        shap_data_cache = {}
        stability = {}
        
        model_list = list(models.items())
        total_models = len(model_list)
        total_folds = len(split_indices)
        
        for model_idx, (name, model) in enumerate(model_list):
            if on_progress:
                on_progress(
                    model_idx / total_models, 
                    f"Computing {name} importance (CV mode: {model_idx+1}/{total_models})"
                )
            
            # Store importance and SHAP values for each fold
            fold_importances = []
            fold_shap_data = []
            fold_top10_features = []  # Track features entering top 10 in each fold
            
            for fold_idx, (train_idx, val_idx) in enumerate(split_indices):
                if on_progress:
                    fold_pct = (model_idx + (fold_idx + 1) / total_folds) / total_models
                    on_progress(
                        fold_pct,
                        f"{name} - Fold {fold_idx+1}/{total_folds}"
                    )
                
                try:
                    X_tr_fold = X.iloc[train_idx]
                    X_val_fold = X.iloc[val_idx]
                    y_tr_fold = y.iloc[train_idx]
                    y_val_fold = y.iloc[val_idx]
                    
                    pipe = create_pipeline(model, name)
                    pipe.fit(X_tr_fold, y_tr_fold)
                    clf = pipe.named_steps["clf"]
                    preprocess = get_preprocess_transformer(pipe)
                    X_tr_t = preprocess.transform(X_tr_fold)
                    X_tr_t_df = pd.DataFrame(X_tr_t, columns=X.columns)
                    X_val_t = preprocess.transform(X_val_fold)
                    X_val_t_df = pd.DataFrame(X_val_t, columns=X.columns)
                    
                    # Compute importance for this fold
                    imp = compute_global_importance(
                        clf, name, X_val_t_df, y_val_fold, self.task_type, X_train=X_tr_t_df
                    )
                    if imp:
                        fold_importances.append(imp)
                        # Track top 10 features in this fold
                        ranked = rank_features(imp)
                        top10 = [feat for feat, _ in ranked[:10]]
                        fold_top10_features.append(set(top10))
                    
                    # Compute SHAP data for this fold if requested
                    if return_shap_data:
                        shap_data = self._compute_shap_data_for_model(
                            clf, name, X_val_t, X_val_t_df, X.columns, X_tr_t, X_tr_t_df
                        )
                        if shap_data is not None:
                            fold_shap_data.append(shap_data)
                            
                except Exception as e:
                    logger.warning("%s Fold %d failed: %s", name, fold_idx + 1, e)
                    continue
            
            # Aggregate results across folds
            if fold_importances:
                # Average importance across folds
                all_features = set()
                for imp_dict in fold_importances:
                    all_features.update(imp_dict.keys())
                
                avg_importance = {}
                for feat in all_features:
                    values = [imp_dict.get(feat, 0.0) for imp_dict in fold_importances]
                    avg_importance[feat] = np.mean(values)
                
                result[name] = rank_features(avg_importance)
                
                # Compute stability: frequency of entering top 10
                stability[name] = {}
                for feat in all_features:
                    count = sum(1 for top10_set in fold_top10_features if feat in top10_set)
                    stability[name][feat] = count / len(fold_top10_features) if fold_top10_features else 0.0
            else:
                # No fold succeeded; still show this model with zero importance so UI lists all models
                result[name] = rank_features({f: 0.0 for f in X.columns})
                stability[name] = {}
            
            # Aggregate SHAP data across folds
            # Reference: Use np.vstack to combine all fold SHAP values (similar to notebook implementation)
            if return_shap_data and fold_shap_data:
                try:
                    # Stack all SHAP matrices vertically (combining all validation sets)
                    # This approach is similar to the notebook: np.vstack(list_shap)
                    shap_matrices = [sd[0] for sd in fold_shap_data]
                    Xt_matrices = [sd[1] for sd in fold_shap_data]
                    
                    # Verify all matrices have the same number of features
                    n_features_list = [m.shape[1] if m.ndim == 2 else 0 for m in shap_matrices]
                    if len(set(n_features_list)) == 1 and n_features_list[0] > 0:
                        # All matrices have same number of features, can stack
                        stacked_shap = np.vstack(shap_matrices)
                        stacked_Xt = np.vstack(Xt_matrices)
                        
                        # Use feature names from first fold (should be consistent)
                        feature_names = fold_shap_data[0][2]
                        
                        shap_data_cache[name] = (stacked_shap, stacked_Xt, feature_names)
                    else:
                        # Fallback: use last fold's data if shapes don't match
                        logger.warning(f"{name}: SHAP matrices have inconsistent feature counts, using last fold")
                        shap_data_cache[name] = fold_shap_data[-1]
                except Exception as e:
                    logger.warning(f"Failed to aggregate SHAP data across folds for {name}: {e}. Using last fold's data.")
                    # Fallback: use last fold's data as-is
                    if fold_shap_data:
                        shap_data_cache[name] = fold_shap_data[-1]
        
        if return_shap_data:
            return result, shap_data_cache, stability
        return result
    
    def _compute_shap_data_for_model(
        self,
        clf: Any,
        model_name: str,
        X_val_t: np.ndarray,
        X_val_t_df: pd.DataFrame,
        feature_names: List[str],
        X_tr_t: np.ndarray,
        X_tr_t_df: pd.DataFrame,
    ) -> Optional[Tuple[np.ndarray, np.ndarray, List[str]]]:
        """Compute SHAP data for a model. Returns (shap_matrix, Xt, feature_names) or None."""
        try:
            import shap
        except ImportError:
            return None
        
        try:
            if model_name in TREE_MODELS:
                # For tree models
                if model_name in {"XGBoost", "LightGBM"} and self.task_type != "regression":
                    try:
                        explainer = shap.TreeExplainer(clf, model_output='probability')
                    except (TypeError, ValueError):
                        explainer = shap.TreeExplainer(clf)
                else:
                    explainer = shap.TreeExplainer(clf)
                X_input = np.asarray(X_val_t_df)
                shap_vals = explainer.shap_values(X_input)
                if isinstance(shap_vals, list) and len(shap_vals) == 2:
                    shap_vals = shap_vals[1]
                shap_vals = _ensure_shap_2d(shap_vals)
                if shap_vals.ndim != 2:
                    return None
                return shap_vals, X_val_t, feature_names
            elif model_name in {"LogisticRegression", "Ridge"}:
                # For linear models
                idx_bg = _sample_indices(len(X_tr_t_df), 100, seed=self.random_state)
                X_tr_t_subset = X_tr_t_df.iloc[idx_bg]
                explainer = shap.LinearExplainer(clf, X_tr_t_subset, feature_perturbation="interventional")
                shap_vals = explainer.shap_values(X_val_t_df)
                shap_vals = _ensure_shap_2d(shap_vals)
                if shap_vals.ndim != 2:
                    return None
                return shap_vals, X_val_t, feature_names
            else:
                # For kernel models (SVM/KNN)
                idx_bg = _sample_indices(len(X_tr_t), 50, seed=self.random_state)
                X_tr_t_subset = X_tr_t[idx_bg]
                idx_val = _sample_indices(len(X_val_t), 50, seed=self.random_state + 1000)
                X_val_use = X_val_t[idx_val]
                
                def predict_fn(z):
                    z = np.asarray(z)
                    if self.task_type == "regression":
                        return clf.predict(z)
                    if hasattr(clf, "predict_proba"):
                        proba = clf.predict_proba(z)
                        if proba.shape[1] == 2:
                            return proba[:, 1]
                        return proba
                    if hasattr(clf, "decision_function"):
                        s = clf.decision_function(z)
                        if s.ndim == 1:
                            return 1.0 / (1.0 + np.exp(-s))
                        return s
                    raise ValueError(f"{clf.__class__.__name__} lacks predict_proba and decision_function.")
                
                explainer = shap.KernelExplainer(predict_fn, X_tr_t_subset)
                shap_vals = explainer.shap_values(X_val_use, nsamples="auto", silent=True)
                shap_vals = _ensure_shap_2d(shap_vals)
                if shap_vals.ndim != 2:
                    return None
                return shap_vals, X_val_use, feature_names
        except Exception as e:
            logger.warning("SHAP data computation failed for %s: %s", model_name, e)
            return None

    def _enumerate_feature_sets(
        self,
        ranked: List[Tuple[str, float]],
        min_features: int,
        max_features: int,
        top_k: int = 10,
    ) -> List[Tuple[str, ...]]:
        """Enumerate combinations of top_k features, sizes in [min_features, max_features]."""
        top_features = [f for f, _ in ranked[:top_k]]
        out = []
        for s in range(min_features, min(max_features + 1, len(top_features) + 1)):
            for comb in combinations(top_features, s):
                out.append(comb)
        return out

    def run_feature_set_generation(
        self,
        importance_ranking: Dict[str, List[Tuple[str, float]]],
        non_med_cols: List[str],
        min_features: int = 1,
        max_features: int = 10,
        top_k: int = 10,
    ) -> Dict[str, List[Tuple[str, ...]]]:
        """
        Phase 2③: Generate candidate feature sets per model.
        Only uses non_med_cols; filters ranked to non_med only.
        """
        result = {}
        for model_name, ranking in importance_ranking.items():
            valid = [(f, v) for f, v in ranking if f in non_med_cols]
            sets = self._enumerate_feature_sets(valid, min_features, max_features, top_k)
            result[model_name] = sets
        return result

    def _cv_score_set(
        self,
        features: List[str],
        X: pd.DataFrame,
        y: pd.Series,
        models: Dict[str, Any],
        primary_metric: str,
    ) -> Dict[str, float]:
        """5-fold CV for a feature set, return mean metrics."""
        X_sub = X[features]
        eval_fn = self.metrics_config["evaluate_fn"]
        metric_names = self.metrics_config["metric_names"]
        if self.task_type == "regression":
            kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        else:
            n_splits = _get_optimal_n_splits(y, max_splits=self.cv_folds)
            kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)

        per_fold = {m: [] for m in metric_names}
        for tr_idx, val_idx in kf.split(X_sub, y if self.task_type != "regression" else None):
            X_tr, X_val = X_sub.iloc[tr_idx], X_sub.iloc[val_idx]
            y_tr, y_val = y.iloc[tr_idx], y.iloc[val_idx]
            for model_name, model in models.items():
                try:
                    pipe = create_pipeline(model, model_name)
                    pipe.fit(X_tr, y_tr)
                    if self.task_type == "regression":
                        y_pred = pipe.predict(X_val)
                        metrics = eval_fn(y_val.values, y_pred)
                    else:
                        y_pred = pipe.predict(X_val)
                        y_proba = pipe.predict_proba(X_val)
                        metrics = eval_fn(y_val.values, y_pred, y_proba)
                    for m in metric_names:
                        if m in metrics:
                            per_fold[m].append(metrics[m])
                    break
                except Exception:
                    continue
        return {m: float(np.mean(per_fold[m])) if per_fold[m] else 0.0 for m in metric_names}

    def run_candidate_screening(
        self,
        feature_sets_by_model: Dict[str, List[Tuple[str, ...]]],
        X: pd.DataFrame,
        y: pd.Series,
        top_n_sets: int = 5,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> List[List[str]]:
        """
        Phase 2④: For each model, 5-fold CV, take top_n_sets by primary metric.
        Deduplicate to get candidate pool.
        """
        scoring_key = "AUROC" if self.task_type != "regression" else "RMSE"
        models = get_models_for_task(self.task_type, y)
        seen = set()
        candidates = []
        total_sets = sum(len(s) for s in feature_sets_by_model.values())
        done = 0
        for model_name, sets in feature_sets_by_model.items():
            if model_name not in models or not sets:
                continue
            scored = []
            for feat_tuple in sets:
                feats = list(feat_tuple)
                key = tuple(sorted(feats))
                if key in seen:
                    continue
                try:
                    metrics = self._cv_score_set(feats, X, y, {model_name: models[model_name]}, "")
                    score = metrics.get(scoring_key, metrics.get("AUROC", metrics.get("RMSE", 0)))
                    if self.task_type == "regression":
                        score = -score
                    else:
                        score = score if scoring_key == "AUROC" else score
                    scored.append((feats, score))
                except Exception as e:
                    logger.debug("CV failed for set %s: %s", feats[:3], e)
                done += 1
                if on_progress and total_sets > 0:
                    on_progress(min(1.0, done / total_sets), f"Candidate screening {model_name} ({done}/{total_sets})")
            higher_better = scoring_key in ("AUROC", "AUPRC", "R2")
            scored.sort(key=lambda x: x[1], reverse=higher_better)
            for feats, _ in scored[:top_n_sets]:
                key = tuple(sorted(feats))
                if key not in seen:
                    seen.add(key)
                    candidates.append(feats)
        return candidates

    def _cv_score_set_all_models(
        self,
        features: List[str],
        X: pd.DataFrame,
        y: pd.Series,
        models: Dict[str, Any],
    ) -> Dict[str, float]:
        """5-fold CV with all models, aggregate mean metrics."""
        X_sub = X[features]
        eval_fn = self.metrics_config["evaluate_fn"]
        metric_names = self.metrics_config["metric_names"]
        if self.task_type == "regression":
            kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        else:
            n_splits = _get_optimal_n_splits(y, max_splits=self.cv_folds)
            kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)

        per_fold = {m: [] for m in metric_names}
        for tr_idx, val_idx in kf.split(X_sub, y if self.task_type != "regression" else None):
            X_tr, X_val = X_sub.iloc[tr_idx], X_sub.iloc[val_idx]
            y_tr, y_val = y.iloc[tr_idx], y.iloc[val_idx]
            for model_name, model in models.items():
                try:
                    pipe = create_pipeline(model, model_name)
                    pipe.fit(X_tr, y_tr)
                    if self.task_type == "regression":
                        y_pred = pipe.predict(X_val)
                        metrics = eval_fn(y_val.values, y_pred)
                    else:
                        y_pred = pipe.predict(X_val)
                        y_proba = pipe.predict_proba(X_val)
                        metrics = eval_fn(y_val.values, y_pred, y_proba)
                    for m in metric_names:
                        if m in metrics:
                            per_fold[m].append(metrics[m])
                    break
                except Exception:
                    continue
        return {m: float(np.mean(per_fold[m])) if per_fold[m] else 0.0 for m in metric_names}

    def run_final_recommendation(
        self,
        candidates: List[List[str]],
        X: pd.DataFrame,
        y: pd.Series,
        importance_ranking: Dict[str, List[Tuple[str, float]]],
        max_recommendations: int = 6,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[List[List[str]], Dict[str, List[str]]]:
        """
        Phase 2⑤: For each candidate, run all models 5-fold CV.
        Per metric take best set; max 6 unique.
        Returns (recommended_sets, recommended_by_metric).
        """
        rec_metrics = self.metrics_config.get("recommendation_metrics", ["AUROC", "AUPRC", "F1-score"])
        models = get_models_for_task(self.task_type, y)
        if not candidates:
            return [], {}

        all_scores = []
        for i, feats in enumerate(candidates):
            if on_progress:
                on_progress((i + 1) / len(candidates), f"Final recommendation eval ({i+1}/{len(candidates)})")
            try:
                metrics = self._cv_score_set_all_models(feats, X, y, models)
                all_scores.append((feats, metrics))
            except Exception:
                continue

        recommended = []
        recommended_by_metric: Dict[str, List[str]] = {}
        higher_better = {"AUROC", "AUPRC", "R2", "Accuracy", "Recall", "F1-score", "Precision", "macro_f1", "PCC"}
        seen: set = set()
        for metric in rec_metrics:
            key = metric
            if key not in (m for _, ms in all_scores for m in ms):
                continue
            reverse = key in higher_better
            sorted_sets = sorted(all_scores, key=lambda x: x[1].get(key, 0), reverse=reverse)
            best_feats = sorted_sets[0][0] if sorted_sets else []
            recommended_by_metric[key] = best_feats
            key_tuple = tuple(sorted(best_feats))
            if key_tuple not in seen:
                seen.add(key_tuple)
                recommended.append(best_feats)

        return recommended, recommended_by_metric

    def run_cv_all_models(
        self,
        features: List[str],
        X: pd.DataFrame,
        y: pd.Series,
        model_names: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """5-fold CV for all models on given features."""
        models = get_models_for_task(self.task_type, y)
        if model_names:
            models = {k: v for k, v in models.items() if k in model_names}
        metric_names = self.metrics_config["metric_names"]
        if self.task_type == "regression":
            kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        else:
            n_splits = _get_optimal_n_splits(y, max_splits=self.cv_folds)
            kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)

        result = {}
        eval_fn = self.metrics_config["evaluate_fn"]
        X_sub = X[features]

        for model_name, model in models.items():
            per_fold = {m: [] for m in metric_names}
            try:
                for tr_idx, val_idx in kf.split(X_sub, y if self.task_type != "regression" else None):
                    X_tr, X_val = X_sub.iloc[tr_idx], X_sub.iloc[val_idx]
                    y_tr, y_val = y.iloc[tr_idx], y.iloc[val_idx]
                    pipe = create_pipeline(model, model_name)
                    pipe.fit(X_tr, y_tr)
                    if self.task_type == "regression":
                        y_pred = pipe.predict(X_val)
                        metrics = eval_fn(y_val.values, y_pred)
                    else:
                        y_pred = pipe.predict(X_val)
                        y_proba = pipe.predict_proba(X_val)
                        metrics = eval_fn(y_val.values, y_pred, y_proba)
                    for m in metric_names:
                        if m in metrics:
                            per_fold[m].append(metrics[m])
                result[model_name] = {}
                for m in metric_names:
                    vals = per_fold[m]
                    if not vals:
                        continue
                    result[model_name][m] = {
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals)) if len(vals) > 1 else 0.0,
                        "folds": [float(x) for x in vals],
                    }
            except Exception as e:
                logger.warning("CV failed for %s: %s", model_name, e)
        return result

    def run_cv_single_model_with_best_params(
        self,
        features: List[str],
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        best_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        K-fold CV for a single model using optional fitted hyperparameters (scheme B).
        `best_params` uses sklearn Pipeline prefixes (e.g. clf__learning_rate) from RandomizedSearchCV.
        """
        models = get_models_for_task(self.task_type, y)
        if model_name not in models:
            return {}
        model = models[model_name]
        metric_names = self.metrics_config["metric_names"]
        eval_fn = self.metrics_config["evaluate_fn"]
        X_sub = X[features]
        if self.task_type == "regression":
            kf = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        else:
            n_splits = _get_optimal_n_splits(y, max_splits=self.cv_folds)
            kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)

        per_fold = {m: [] for m in metric_names}
        for tr_idx, val_idx in kf.split(X_sub, y if self.task_type != "regression" else None):
            X_tr, X_val = X_sub.iloc[tr_idx], X_sub.iloc[val_idx]
            y_tr, y_val = y.iloc[tr_idx], y.iloc[val_idx]
            pipe = create_pipeline(model, model_name)
            if best_params:
                pipe.set_params(**best_params)
            pipe.fit(X_tr, y_tr)
            if self.task_type == "regression":
                y_pred = pipe.predict(X_val)
                metrics = eval_fn(y_val.values, y_pred)
            else:
                y_pred = pipe.predict(X_val)
                y_proba = pipe.predict_proba(X_val)
                metrics = eval_fn(y_val.values, y_pred, y_proba)
            for m in metric_names:
                if m in metrics:
                    per_fold[m].append(metrics[m])

        result: Dict[str, Any] = {}
        for m in metric_names:
            vals = per_fold[m]
            if not vals:
                continue
            result[m] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)) if len(vals) > 1 else 0.0,
                "folds": [float(x) for x in vals],
            }
        return result

    def train_final_model(
        self,
        features: List[str],
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        use_search: bool = False,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Phase 4: Train final model on full data.
        Returns (fitted_pipeline, metadata).
        """
        models = get_models_for_task(self.task_type, y)
        if self.task_type != "regression":
            uniq = pd.Series(y).dropna().unique()
            if len(uniq) < 2:
                raise ValueError(
                    "The training subset has only one class; a classifier requires both positive and negative examples."
                )
        if model_name not in models:
            raise ValueError(f"Unknown model: {model_name}")
        model = models[model_name]
        X_sub = X[features]
        pipe = create_pipeline(model, model_name)

        if use_search and self.enable_search:
            scoring = get_scoring_string(self.task_type)
            param_distributions = self._get_param_dist(model_name)
            if param_distributions:
                # Adjust CV folds for RandomizedSearchCV based on class distribution
                if self.task_type == "regression":
                    cv_folds_search = min(3, self.cv_folds)
                else:
                    cv_folds_search = min(3, _get_optimal_n_splits(y, max_splits=self.cv_folds))
                search = RandomizedSearchCV(
                    pipe,
                    param_distributions,
                    n_iter=min(20, 2 ** min(5, len(str(param_distributions)))),
                    cv=cv_folds_search,
                    scoring=scoring,
                    random_state=self.random_state,
                    n_jobs=1,
                )
                search.fit(X_sub, y)
                pipe = search.best_estimator_
                metadata = {"best_params": search.best_params_, "best_score": float(search.best_score_)}
            else:
                pipe.fit(X_sub, y)
                metadata = {}
        else:
            pipe.fit(X_sub, y)
            metadata = {}

        metadata["features"] = features
        metadata["model_name"] = model_name
        metadata["task_type"] = self.task_type
        return pipe, metadata

    def compute_shap_for_visualization(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        shap_data_cache: Optional[Dict[str, Tuple[np.ndarray, np.ndarray, List[str]]]] = None,
    ) -> Optional[Tuple[np.ndarray, np.ndarray, List[str]]]:
        """
        Compute SHAP values and transformed features for visualization.
        If shap_data_cache is provided and contains model_name, returns cached data.
        Otherwise computes new SHAP values.
        Returns (shap_matrix, Xt, feature_names) or None if failed.
        """
        # Check cache first
        if shap_data_cache and model_name in shap_data_cache:
            logger.debug("Using cached SHAP data for %s", model_name)
            return shap_data_cache[model_name]
        try:
            import shap
        except ImportError:
            return None
        models = get_models_for_task(self.task_type, y)
        if model_name not in models:
            return None
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state,
            stratify=y if self.task_type != "regression" else None
        )
        pipe = create_pipeline(models[model_name], model_name)
        pipe.fit(X_tr, y_tr)
        preprocess = get_preprocess_transformer(pipe)
        X_val_t = preprocess.transform(X_val)
        X_val_t_df = pd.DataFrame(X_val_t, columns=X.columns)
        clf = pipe.named_steps["clf"]
        
        if model_name in TREE_MODELS:
            try:
                explainer = shap.TreeExplainer(clf)
                X_input = np.asarray(X_val_t_df)
                shap_vals = explainer.shap_values(X_input)
                # Simple handling: if list, take second element for binary classification
                if isinstance(shap_vals, list) and len(shap_vals) == 2:
                    shap_vals = shap_vals[1]
                shap_vals = _ensure_shap_2d(shap_vals)
                if shap_vals.ndim != 2:
                    return None
                return shap_vals, X_val_t, list(X.columns)
            except Exception as e:
                logger.warning("SHAP computation failed for %s: %s", model_name, e)
                return None
        else:
            # For non-tree models, try LinearExplainer or KernelExplainer
            try:
                if model_name in {"LogisticRegression", "Ridge"}:
                    # Use a subset for background
                    idx_bg = _sample_indices(len(X_tr), 100, seed=self.random_state)
                    X_tr_t = preprocess.transform(X_tr.iloc[idx_bg])
                    X_tr_t_df = pd.DataFrame(X_tr_t, columns=X.columns)
                    explainer = shap.LinearExplainer(clf, X_tr_t_df, feature_perturbation="interventional")
                    shap_vals = explainer.shap_values(X_val_t_df)
                    shap_vals = _ensure_shap_2d(shap_vals)
                    if shap_vals.ndim != 2:
                        return None
                    return shap_vals, X_val_t, list(X.columns)
                else:
                    # KernelExplainer for SVM/KNN - use subset
                    idx_bg = _sample_indices(len(X_tr), 50, seed=self.random_state)
                    X_tr_t = preprocess.transform(X_tr.iloc[idx_bg])
                    idx_val = _sample_indices(len(X_val), 50, seed=self.random_state + 1000)
                    X_val_use = X_val_t[idx_val]
                    
                    def predict_fn(z):
                        z = np.asarray(z)
                        if self.task_type == "regression":
                            return clf.predict(z)
                        if hasattr(clf, "predict_proba"):
                            proba = clf.predict_proba(z)
                            if proba.shape[1] == 2:
                                return proba[:, 1]
                            return proba
                        if hasattr(clf, "decision_function"):
                            s = clf.decision_function(z)
                            if s.ndim == 1:
                                return 1.0 / (1.0 + np.exp(-s))
                            return s
                        raise ValueError(f"{clf.__class__.__name__} lacks predict_proba and decision_function.")
                    
                    explainer = shap.KernelExplainer(predict_fn, X_tr_t)
                    shap_vals = explainer.shap_values(X_val_use, nsamples="auto", silent=True)
                    shap_vals = _ensure_shap_2d(shap_vals)
                    if shap_vals.ndim != 2:
                        return None
                    return shap_vals, X_val_use, list(X.columns)
            except Exception as e:
                logger.warning("SHAP computation failed for %s: %s", model_name, e)
                return None

    def compute_shap_beeswarm_with_reason(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        max_display: int = 15,
    ) -> Tuple[Optional[Any], str]:
        """Same as compute_shap_beeswarm but returns (figure_or_none, reason_code)."""
        _set_chart_font()
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        try:
            import shap
        except ImportError:
            return None, "shap_import_failed"
        models = get_models_for_task(self.task_type, y)
        if model_name not in models:
            return None, "model_not_found"
        X_tr, X_val, y_tr, y_val = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=self.random_state,
            stratify=y if self.task_type != "regression" else None,
        )
        pipe = create_pipeline(models[model_name], model_name)
        pipe.fit(X_tr, y_tr)
        X_val_t = pipe[:-1].transform(X_val)
        X_val_t = pd.DataFrame(X_val_t, columns=X.columns)
        clf = pipe.named_steps["clf"]
        if model_name not in TREE_MODELS:
            return None, "non_tree_model"
        X_input = np.asarray(X_val_t)
        feat_list = list(X_val_t.columns)
        feat_n = len(feat_list)
        shap_vals_raw: Optional[Any] = None
        try:
            explainer = shap.TreeExplainer(clf)
            shap_vals_raw = explainer.shap_values(X_input)
            _log_shap_xgb_lgb_parse_debug(
                model_name,
                "beeswarm",
                shap_vals_raw,
                X_input,
                feat_n,
                post_ensure=None,
            )
            shap_2d, nerr = _normalize_shap_values_2d(
                shap_vals_raw,
                X_input,
                feat_list,
                model_name,
                positive_class_index=1,
            )
            if nerr:
                return None, _shap_export_task_reason(
                    nerr,
                    model_name=model_name,
                    plot_type="beeswarm",
                    shap_vals_raw=shap_vals_raw,
                    normalized=None,
                    X_input=X_input,
                    feature_names_len=feat_n,
                )
            _log_shap_xgb_lgb_parse_debug(
                model_name,
                "beeswarm",
                shap_vals_raw,
                X_input,
                feat_n,
                post_ensure=shap_2d,
            )
            if np.all(shap_2d == 0):
                logger.warning(
                    "shap_values_all_zero: model=%s plot_type=beeswarm raw=%s",
                    model_name,
                    shap_raw_type_and_shape(shap_vals_raw),
                )
                return None, _shap_export_task_reason(
                    "shap_values_all_zero",
                    model_name=model_name,
                    plot_type="beeswarm",
                    shap_vals_raw=shap_vals_raw,
                    normalized=shap_2d,
                    X_input=X_input,
                    feature_names_len=feat_n,
                )
            plt.figure(figsize=(3.5, 2.5))
            matplotlib.rcParams["font.size"] = 6
            try:
                shap.summary_plot(shap_2d, X_val_t, max_display=max_display, show=False)
            except Exception as pe:
                suf = _shap_export_reason_suffix(pe)
                logger.warning("SHAP beeswarm plot failed for %s: %s", model_name, pe)
                return None, _shap_export_task_reason(
                    f"plot_exception:{suf}",
                    model_name=model_name,
                    plot_type="beeswarm",
                    shap_vals_raw=shap_vals_raw,
                    normalized=shap_2d,
                    X_input=X_input,
                    feature_names_len=feat_n,
                )
            fig = plt.gcf()
            fig.tight_layout()
            return fig, "success"
        except Exception as e:
            suf = _shap_export_reason_suffix(e)
            logger.warning("SHAP beeswarm failed for %s: %s.", model_name, e)
            return None, _shap_export_task_reason(
                f"tree_explainer_exception:{suf}",
                model_name=model_name,
                plot_type="beeswarm",
                shap_vals_raw=shap_vals_raw,
                normalized=None,
                X_input=X_input,
                feature_names_len=feat_n,
            )

    def compute_shap_beeswarm(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        max_display: int = 15,
    ) -> Optional[Any]:
        """Compute and return SHAP beeswarm/bar figure for tree model. For non-tree, try bar from importance."""
        fig, _reason = self.compute_shap_beeswarm_with_reason(X, y, model_name, max_display=max_display)
        return fig

    def compute_shap_bar_with_reason(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        max_display: int = 15,
    ) -> Tuple[Optional[Any], str]:
        """Same as compute_shap_bar but returns (figure_or_none, reason_code)."""
        _set_chart_font()
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        try:
            import shap
        except ImportError:
            return None, "shap_import_failed"
        models = get_models_for_task(self.task_type, y)
        if model_name not in models:
            return None, "model_not_found"
        X_tr, X_val, y_tr, y_val = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=self.random_state,
            stratify=y if self.task_type != "regression" else None,
        )
        pipe = create_pipeline(models[model_name], model_name)
        pipe.fit(X_tr, y_tr)
        X_val_t = pipe[:-1].transform(X_val)
        X_val_t = pd.DataFrame(X_val_t, columns=X.columns)
        clf = pipe.named_steps["clf"]
        if model_name not in TREE_MODELS:
            return None, "non_tree_model"
        X_input = np.asarray(X_val_t)
        feat_list = list(X_val_t.columns)
        feat_n = len(feat_list)
        shap_vals_raw: Optional[Any] = None
        try:
            explainer = shap.TreeExplainer(clf)
            shap_vals_raw = explainer.shap_values(X_input)
            _log_shap_xgb_lgb_parse_debug(
                model_name,
                "bar",
                shap_vals_raw,
                X_input,
                feat_n,
                post_ensure=None,
            )
            shap_2d, nerr = _normalize_shap_values_2d(
                shap_vals_raw,
                X_input,
                feat_list,
                model_name,
                positive_class_index=1,
            )
            if nerr:
                return None, _shap_export_task_reason(
                    nerr,
                    model_name=model_name,
                    plot_type="bar",
                    shap_vals_raw=shap_vals_raw,
                    normalized=None,
                    X_input=X_input,
                    feature_names_len=feat_n,
                )
            _log_shap_xgb_lgb_parse_debug(
                model_name,
                "bar",
                shap_vals_raw,
                X_input,
                feat_n,
                post_ensure=shap_2d,
            )
            if np.all(shap_2d == 0):
                logger.warning(
                    "shap_values_all_zero: model=%s plot_type=bar raw=%s",
                    model_name,
                    shap_raw_type_and_shape(shap_vals_raw),
                )
                return None, _shap_export_task_reason(
                    "shap_values_all_zero",
                    model_name=model_name,
                    plot_type="bar",
                    shap_vals_raw=shap_vals_raw,
                    normalized=shap_2d,
                    X_input=X_input,
                    feature_names_len=feat_n,
                )
            plt.figure(figsize=(3.5, 2.5))
            plt.rcParams["font.size"] = 6
            try:
                shap.summary_plot(
                    shap_2d,
                    X_val_t,
                    plot_type="bar",
                    max_display=max_display,
                    show=False,
                )
            except Exception as pe:
                suf = _shap_export_reason_suffix(pe)
                logger.warning("SHAP bar plot failed for %s: %s", model_name, pe)
                return None, _shap_export_task_reason(
                    f"plot_exception:{suf}",
                    model_name=model_name,
                    plot_type="bar",
                    shap_vals_raw=shap_vals_raw,
                    normalized=shap_2d,
                    X_input=X_input,
                    feature_names_len=feat_n,
                )
            fig = plt.gcf()
            fig.tight_layout()
            return fig, "success"
        except Exception as e:
            suf = _shap_export_reason_suffix(e)
            logger.warning("SHAP bar summary failed for %s: %s.", model_name, e)
            return None, _shap_export_task_reason(
                f"tree_explainer_exception:{suf}",
                model_name=model_name,
                plot_type="bar",
                shap_vals_raw=shap_vals_raw,
                normalized=None,
                X_input=X_input,
                feature_names_len=feat_n,
            )

    def compute_shap_bar(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        max_display: int = 15,
    ) -> Optional[Any]:
        """Compute SHAP summary bar plot for tree models (mirrors compute_shap_beeswarm)."""
        fig, _reason = self.compute_shap_bar_with_reason(X, y, model_name, max_display=max_display)
        return fig

    def compute_shap_interaction(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        max_display: int = 25,
        group_defs: Optional[Dict[str, List[str]]] = None,
        priority_features: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """
        Compute SHAP interaction values and return bubble heatmap for tree models only.
        
        Args:
            X: Feature dataframe
            y: Target series
            model_name: Model name
            max_display: Maximum features to display
            group_defs: Dict mapping group names to feature lists (e.g., {"Comorbidity": [...], "Immunosuppression": [...]})
            priority_features: List of features to prioritize in display order
        """
        _set_chart_font()
        import matplotlib
        matplotlib.use("Agg")
        try:
            import shap
        except ImportError:
            return None
        if model_name not in TREE_MODELS:
            return None
        models = get_models_for_task(self.task_type, y)
        if model_name not in models:
            return None
        X_tr, X_val, y_tr, _ = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state,
            stratify=y if self.task_type != "regression" else None
        )
        pipe = create_pipeline(models[model_name], model_name)
        pipe.fit(X_tr, y_tr)
        preprocess = get_preprocess_transformer(pipe)
        X_val_t = preprocess.transform(X_val)
        clf = pipe.named_steps["clf"]
        try:
            explainer = shap.TreeExplainer(clf)
            X_input = np.asarray(X_val_t)
            inter = explainer.shap_interaction_values(X_input)
            # Handle interaction values: list -> array, 4D -> 3D
            if isinstance(inter, list) and len(inter) == 2:
                inter = inter[1]
            inter = np.asarray(inter)
            if inter.ndim == 4:
                # (n_samples, n_features, n_features, n_classes) -> take positive class or mean
                if inter.shape[3] == 2:
                    inter = inter[:, :, :, 1]
                else:
                    inter = inter.mean(axis=3)
            # Check if interaction matrix shape is valid
            elif inter.ndim == 3 and inter.shape[-1] == 2:
                raise ValueError(
                    f"{model_name} SHAP interaction values shape is {inter.shape}, "
                    "appears to be non-interaction matrix. Try XGBoost/LightGBM/CatBoost only."
                )
            mean_inter = np.mean(np.abs(inter), axis=0)
            return plot_shap_interaction_heatmap(
                mean_inter, list(X.columns), max_display=max_display,
                title=f"{model_name} SHAP Interaction",
                model_name=model_name,
                group_defs=group_defs,
                priority_features=priority_features,
            )
        except Exception as e:
            logger.warning("SHAP interaction failed for %s: %s", model_name, e)
            return None

    def _get_param_dist(self, model_name: str) -> Dict:
        """Simple param distributions for RandomizedSearchCV."""
        if model_name == "LogisticRegression":
            return {"clf__C": [0.01, 0.1, 1, 10], "clf__penalty": ["l2"]}
        if model_name == "RandomForest":
            return {"clf__n_estimators": [100, 200], "clf__max_depth": [10, 20, None]}
        if model_name == "Ridge":
            return {"clf__alpha": [0.1, 1, 10]}
        return {}

    def predict(
        self,
        pipe: Any,
        X_new: pd.DataFrame,
        features: List[str],
    ) -> Tuple[np.ndarray, Optional[np.ndarray], str]:
        """
        Predict on new data. Returns (predictions, probabilities_or_None, uncertainty_note).
        """
        X_sub = X_new[features].copy()
        X_sub = X_sub.reindex(columns=features, fill_value=np.nan)
        pred = pipe.predict(X_sub)
        proba = None
        if hasattr(pipe, "predict_proba"):
            proba = pipe.predict_proba(X_sub)
        n_missing = X_sub.isnull().sum().sum()
        note = f"Missing values in input: {n_missing}" if n_missing > 0 else "OK"
        return pred, proba, note
