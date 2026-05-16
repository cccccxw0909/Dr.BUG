"""SHAP and permutation importance utilities."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _set_chart_font():
    """Set Arial font for charts; fallback to CJK font if Arial not available for Chinese feature names."""
    import matplotlib
    import matplotlib.font_manager as fm
    matplotlib.use("Agg")
    candidates = ["Arial", "DejaVu Sans", "SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Arial Unicode MS"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            import matplotlib.pyplot as plt
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            plt.rcParams["font.size"] = 8
            plt.rcParams["axes.titlesize"] = 9
            plt.rcParams["axes.labelsize"] = 8
            return
from sklearn.inspection import permutation_importance

logger = logging.getLogger(__name__)

TREE_MODELS = {"XGBoost", "LightGBM", "CatBoost", "RandomForest", "XGBRegressor", "LGBMRegressor", "CatBoostRegressor", "RandomForestRegressor"}
LINEAR_MODELS = {"LogisticRegression", "Ridge", "ElasticNet"}


def _is_tree(model_name: str) -> bool:
    return model_name in TREE_MODELS


def _is_linear(model_name: str) -> bool:
    return model_name in LINEAR_MODELS


def _sample_indices(n: int, k: Optional[int], seed: int) -> np.ndarray:
    """Sample k indices from n without replacement. If k is None or >= n, return all indices."""
    if k is None or k <= 0 or k >= n:
        return np.arange(n)
    rng = np.random.RandomState(seed)
    return rng.choice(n, size=k, replace=False)


def shap_raw_type_and_shape(shap_values: Any) -> Tuple[str, str]:
    """Best-effort raw SHAP payload description for task logs (before normalization)."""
    if shap_values is None:
        return "None", "None"
    tname = type(shap_values).__name__
    mod = getattr(type(shap_values), "__module__", "") or ""
    if mod.startswith("shap."):
        tname = f"{mod.rsplit('.', 1)[-1]}.{tname}"
    try:
        import shap as _shap

        if isinstance(shap_values, _shap.Explanation):
            v = shap_values.values
            return tname, _raw_array_shape_str(v)
    except Exception:
        pass
    if isinstance(shap_values, (list, tuple)):
        parts = []
        for i, x in enumerate(shap_values):
            parts.append(f"[{i}]={_raw_array_shape_str(x)}")
        return tname, "list=(" + ",".join(parts) + ")"
    return tname, _raw_array_shape_str(shap_values)


def _raw_array_shape_str(x: Any) -> str:
    a = np.asarray(x)
    try:
        return str(tuple(a.shape))
    except Exception:
        return type(x).__name__


def _unwrap_shap_explanation(shap_values: Any) -> Any:
    """If value is shap.Explanation, return its `.values`; else unchanged."""
    try:
        import shap as _shap

        if isinstance(shap_values, _shap.Explanation):
            return shap_values.values
    except Exception:
        pass
    return shap_values


def _select_output_axis_3d(
    arr: np.ndarray,
    n_samples: int,
    n_features: int,
    positive_class_index: int,
) -> Optional[np.ndarray]:
    """
    Collapse trailing/leading output dimension for 3D SHAP tensors.
    Layouts:
      (n_samples, n_features, n_outputs)
      (n_outputs, n_samples, n_features)
      (n_samples, n_outputs, n_features)
    """
    if arr.ndim != 3:
        return None
    d0, d1, d2 = arr.shape

    # (ns, nf, k)
    if d0 == n_samples and d1 == n_features:
        k = d2
        if k == 1:
            return np.asarray(arr[:, :, 0])
        if k >= 2:
            pi = positive_class_index if positive_class_index < k else k - 1
            return np.asarray(arr[:, :, pi])
        return None

    # (k, ns, nf)
    if d1 == n_samples and d2 == n_features:
        k = d0
        if k == 1:
            return np.asarray(arr[0, :, :])
        if k >= 2:
            pi = positive_class_index if positive_class_index < k else k - 1
            return np.asarray(arr[pi, :, :])
        return None

    # (ns, k, nf)
    if d0 == n_samples and d2 == n_features:
        k = d1
        if k == 1:
            return np.asarray(arr[:, 0, :])
        if k >= 2:
            pi = positive_class_index if positive_class_index < k else k - 1
            return np.asarray(arr[:, pi, :])
        return None

    return None


def _normalize_shap_values_2d(
    shap_values: Any,
    X: Any,
    feature_names: Any,
    model_name: str,
    positive_class_index: int = 1,
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Normalize TreeExplainer SHAP outputs to (n_samples, n_features).

    Returns (matrix, None) on success; (None, error_reason) on failure.

    ``model_name`` is reserved for callers / future diagnostics.
    """
    _ = model_name
    X_arr = np.asarray(X)
    if X_arr.ndim != 2:
        try:
            fcl = len(feature_names)  # type: ignore[arg-type]
        except TypeError:
            fcl = "unknown"
        return None, (
            f"feature_shape_mismatch:X_shape={getattr(X_arr, 'shape', None)},feature_count={fcl}"
        )
    n_samples, n_features = int(X_arr.shape[0]), int(X_arr.shape[1])
    try:
        feature_count = len(feature_names) if feature_names is not None else n_features  # type: ignore[arg-type]
    except TypeError:
        feature_count = n_features

    raw_type, raw_shape_desc = shap_raw_type_and_shape(shap_values)

    if feature_count != n_features:
        return None, (
            f"feature_shape_mismatch:X_shape={tuple(X_arr.shape)},feature_count={feature_count}"
        )

    shap_values = _unwrap_shap_explanation(shap_values)

    if isinstance(shap_values, (list, tuple)):
        if len(shap_values) >= 2:
            pi = positive_class_index
            if pi >= len(shap_values):
                pi = len(shap_values) - 1
            shap_values = shap_values[pi]
        elif len(shap_values) == 1:
            shap_values = shap_values[0]
        else:
            return None, (
                f"shap_values_invalid_shape: raw_type={raw_type},raw_shape={raw_shape_desc},"
                f"normalized_shape=N/A,X_shape={tuple(X_arr.shape)},feature_count={feature_count}"
            )
        shap_values = _unwrap_shap_explanation(shap_values)

    arr = np.asarray(shap_values)
    norm_shape_repr: Optional[Tuple[int, ...]] = None

    while arr.ndim > 2:
        nxt = _select_output_axis_3d(arr, n_samples, n_features, positive_class_index)
        if nxt is None:
            return None, (
                f"shap_values_invalid_shape: raw_type={raw_type},raw_shape={raw_shape_desc},"
                f"normalized_shape=N/A,intermediate_ndim={arr.ndim},intermediate_shape={tuple(arr.shape)},"
                f"X_shape={tuple(X_arr.shape)},feature_count={feature_count}"
            )
        arr = np.asarray(nxt)

    if arr.ndim == 1:
        if arr.size == n_samples * n_features:
            arr = arr.reshape(n_samples, n_features)
        else:
            return None, (
                f"shap_values_invalid_shape: raw_type={raw_type},raw_shape={raw_shape_desc},"
                f"normalized_shape=N/A,1d_size={arr.size},X_shape={tuple(X_arr.shape)},feature_count={feature_count}"
            )

    if arr.ndim != 2:
        return None, (
            f"shap_values_invalid_shape: raw_type={raw_type},raw_shape={raw_shape_desc},"
            f"normalized_shape=N/A,ndim={arr.ndim},shape={tuple(arr.shape)},"
            f"X_shape={tuple(X_arr.shape)},feature_count={feature_count}"
        )

    norm_shape_repr = tuple(arr.shape)
    if arr.shape[0] != n_samples or arr.shape[1] != n_features:
        return None, (
            f"shap_values_invalid_shape: raw_type={raw_type},raw_shape={raw_shape_desc},"
            f"normalized_shape={norm_shape_repr},X_shape={tuple(X_arr.shape)},feature_count={feature_count}"
        )

    return arr, None


def _ensure_shap_2d(shap_vals) -> np.ndarray:
    """
    Normalize SHAP values to 2D array (n_samples, n_features). 
    Handle list, 3D, etc. Supports LightGBM's new format (list of ndarray).
    Simplified version: if list, take second element (positive class for binary classification).
    """
    # Simple handling: if list, take second element (for binary classification)
    # This matches the recommended approach for LightGBM's new format
    if isinstance(shap_vals, list):
        if len(shap_vals) >= 2:
            shap_vals = shap_vals[1]  # Binary classification: take positive class
        elif len(shap_vals) == 1:
            shap_vals = shap_vals[0]
        else:
            shap_vals = np.array([])
    
    # Convert to numpy array
    shap_vals = np.asarray(shap_vals)
    
    # Handle empty array
    if shap_vals.size == 0:
        return np.array([]).reshape(0, 0)
    
    # Handle 3D arrays: (n_samples, n_features, n_classes)
    if shap_vals.ndim == 3:
        if shap_vals.shape[2] == 2:
            shap_vals = shap_vals[:, :, 1]  # Binary: take positive class
        else:
            shap_vals = shap_vals.mean(axis=2)  # Multi-class: average
    
    # Ensure 2D
    if shap_vals.ndim == 1:
        shap_vals = shap_vals.reshape(1, -1)
    elif shap_vals.ndim == 0:
        shap_vals = np.array([[shap_vals]])
    
    return shap_vals


def compute_importance_tree(
    model: object,
    X: pd.DataFrame,
    model_name: str,
    y: Optional[pd.Series] = None,
    task_type: str = "binary",
    X_train: Optional[pd.DataFrame] = None,
) -> Dict[str, float]:
    """TreeExplainer for tree models."""
    try:
        import shap
    except ImportError:
        logger.warning("SHAP not available for %s. Using permutation.", model_name)
        return _permutation_fallback(model, X, y, task_type)

    try:
        # For XGBoost and LightGBM, use model_output='probability' for classification
        # This ensures SHAP values are computed correctly
        if model_name in {"XGBoost", "LightGBM"} and task_type != "regression":
            try:
                explainer = shap.TreeExplainer(model, model_output='probability')
            except (TypeError, ValueError):
                # Fallback to default if model_output not supported
                explainer = shap.TreeExplainer(model)
        else:
            explainer = shap.TreeExplainer(model)
        
        # For LightGBM, use numpy array to avoid feature name mismatch
        # The model was trained with numpy arrays from pipeline transform
        # Using DataFrame causes warning about feature name mismatch
        X_input = np.asarray(X)  # Use numpy array for all models to be consistent
        
        shap_vals = explainer.shap_values(X_input)
        
        # Store raw shap_vals for logging (before processing)
        raw_shap_type = type(shap_vals)
        
        # Simple handling: if list, take second element for binary classification
        if isinstance(shap_vals, list) and len(shap_vals) == 2:
            shap_vals = shap_vals[1]
            logger.debug("%s: SHAP values returned as list, using second element (positive class)", model_name)
        elif isinstance(shap_vals, list) and len(shap_vals) > 2:
            # Multi-class: will be handled by _ensure_shap_2d
            logger.debug("%s: SHAP values returned as list of length %d (multi-class)", model_name, len(shap_vals))
        
        # Debug: log SHAP values shape before processing
        if isinstance(shap_vals, list):
            logger.debug("%s: Raw SHAP values: list of length %d", model_name, len(shap_vals))
            if len(shap_vals) > 0:
                for idx, elem in enumerate(shap_vals):
                    if isinstance(elem, np.ndarray):
                        elem_min = float(np.min(elem)) if elem.size > 0 else 0.0
                        elem_max = float(np.max(elem)) if elem.size > 0 else 0.0
                        logger.debug("  Element %d: shape %s, dtype %s, min=%.6f, max=%.6f", 
                                    idx, elem.shape, elem.dtype, elem_min, elem_max)
                    else:
                        logger.debug("  Element %d: type %s, value: %s", idx, type(elem), str(elem)[:100])
        else:
            logger.debug("%s: Raw SHAP values shape: %s, type: %s, dtype: %s", 
                        model_name, 
                        getattr(shap_vals, 'shape', 'N/A'), 
                        type(shap_vals),
                        getattr(shap_vals, 'dtype', 'N/A'))
            if isinstance(shap_vals, np.ndarray) and shap_vals.size > 0:
                logger.debug("  Min=%.6f, Max=%.6f, Mean=%.6f", 
                            float(np.min(shap_vals)), float(np.max(shap_vals)), float(np.mean(shap_vals)))
        
        shap_vals = _ensure_shap_2d(shap_vals)
        if shap_vals.ndim != 2:
            raise ValueError(f"SHAP values shape {shap_vals.shape} is not 2D after normalization")
        
        # Additional check: ensure we have valid values
        if shap_vals.size == 0:
            raise ValueError(f"SHAP values array is empty for {model_name}")
        
        # Log processed values
        logger.debug("%s: Processed SHAP values shape: %s, min=%.6f, max=%.6f, mean_abs=%.6f", 
                    model_name, shap_vals.shape, 
                    float(np.min(shap_vals)), float(np.max(shap_vals)), 
                    float(np.abs(shap_vals).mean()))
        
        # Check if all values are zero
        mean_abs = np.abs(shap_vals).mean(axis=0)
        if np.allclose(mean_abs, 0.0, atol=1e-10):
            logger.warning("%s: All SHAP values are zero after processing. Raw type: %s. Using permutation fallback.", 
                          model_name, raw_shap_type)
            if isinstance(raw_shap_type(), list):
                logger.warning("%s: SHAP returned list format. Check if _ensure_shap_2d processed it correctly.", model_name)
            fallback = _permutation_fallback(model, X, y, task_type)
            if all(v == 0 for v in fallback.values()) and y is not None:
                tree_imp = _tree_feature_importances_fallback(model, X, model_name)
                if tree_imp:
                    logger.info("%s: Using native feature_importances_ (SHAP and permutation were zero).", model_name)
                    return tree_imp
                logger.warning("Permutation fallback also returned all zeros for %s. This may indicate a model training issue.", model_name)
            return fallback
        
        result = {f: float(np.mean(np.abs(shap_vals[:, i]))) for i, f in enumerate(X.columns)}
        logger.debug("%s: Computed importance range: [%.6f, %.6f]", model_name, 
                    min(result.values()), max(result.values()))
        return result
    except Exception as e:
        logger.warning("TreeExplainer failed for %s: %s. Using permutation.", model_name, e)
        import traceback
        logger.debug("Traceback: %s", traceback.format_exc())
        fallback = _permutation_fallback(model, X, y, task_type)
        if all(v == 0 for v in fallback.values()) and y is not None:
            tree_imp = _tree_feature_importances_fallback(model, X, model_name)
            if tree_imp:
                logger.info("%s: Using native feature_importances_ (SHAP/permutation failed or zero).", model_name)
                return tree_imp
            logger.warning("Permutation fallback returned all zeros for %s.", model_name)
        return fallback


def compute_importance_linear(
    model: object,
    X: pd.DataFrame,
    model_name: str,
    y: Optional[pd.Series] = None,
    task_type: str = "binary",
    X_train: Optional[pd.DataFrame] = None,
    linear_background_samples: int = 100,
) -> Dict[str, float]:
    """LinearExplainer for linear models. Uses background samples from X_train if provided."""
    try:
        import shap
    except ImportError:
        return _permutation_fallback(model, X, y, task_type)

    try:
        # Use background samples from training data if available
        if X_train is not None and len(X_train) > 0:
            idx_bg = _sample_indices(len(X_train), linear_background_samples, seed=42)
            X_bg = X_train.iloc[idx_bg] if isinstance(X_train, pd.DataFrame) else X_train[idx_bg]
        else:
            X_bg = X
        explainer = shap.LinearExplainer(model, X_bg, feature_perturbation="interventional")
        shap_vals = explainer.shap_values(X)
        shap_vals = _ensure_shap_2d(shap_vals)
        if shap_vals.ndim == 1:
            shap_vals = shap_vals.reshape(-1, 1)
        if shap_vals.ndim != 2:
            raise ValueError(f"SHAP values shape {shap_vals.shape} is not 2D after normalization")
        return {f: float(np.mean(np.abs(shap_vals[:, i]))) for i, f in enumerate(X.columns)}
    except Exception as e:
        logger.warning("LinearExplainer failed for %s: %s. Using permutation.", model_name, e)
        return _permutation_fallback(model, X, y, task_type)


def _tree_feature_importances_fallback(model: object, X: pd.DataFrame, model_name: str) -> Optional[Dict[str, float]]:
    """Use tree model's native feature_importances_ when SHAP/permutation are all zero."""
    if not _is_tree(model_name):
        return None
    try:
        imp = getattr(model, "feature_importances_", None)
        if imp is None:
            return None
        imp = np.asarray(imp)
        n = min(len(imp), len(X.columns))
        if n == 0:
            return None
        # Align by position (pipeline keeps column order); fill missing with 0
        out = {f: 0.0 for f in X.columns}
        for i in range(n):
            if i < len(X.columns):
                out[X.columns[i]] = float(imp[i])
        return out
    except Exception as e:
        logger.debug("feature_importances_ fallback failed for %s: %s", model_name, e)
        return None


def _permutation_fallback(
    model: object,
    X: pd.DataFrame,
    y: Optional[pd.Series] = None,
    task_type: str = "binary",
) -> Dict[str, float]:
    """Permutation importance fallback. Pass numpy to avoid feature_names mismatch with KNN/SVM."""
    if y is None:
        return {f: 1.0 / len(X.columns) for f in X.columns}
    try:
        scoring = "neg_mean_squared_error" if task_type == "regression" else "accuracy"
        X_arr = np.asarray(X)  # KNN/SVM fitted with numpy from pipeline
        r = permutation_importance(model, X_arr, y, n_repeats=5, random_state=42, scoring=scoring)
        return {f: float(np.abs(r.importances_mean[i])) for i, f in enumerate(X.columns)}
    except Exception as e:
        logger.warning("Permutation importance failed: %s", e)
        return {f: 0.0 for f in X.columns}


def compute_importance_kernel(
    model: object,
    X: pd.DataFrame,
    model_name: str,
    y: Optional[pd.Series] = None,
    task_type: str = "binary",
    X_train: Optional[pd.DataFrame] = None,
    kernel_background_samples: int = 100,
    kernel_val_samples: int = 50,
) -> Dict[str, float]:
    """
    KernelExplainer for KNN, SVM and other non-tree/non-linear models.
    Uses subsampled background and validation data for efficiency.
    """
    try:
        import shap
    except ImportError:
        return _permutation_fallback(model, X, y, task_type)
    try:
        X_arr = np.asarray(X)
        
        # Sample background from training data if available, otherwise from X
        if X_train is not None and len(X_train) > 0:
            X_train_arr = np.asarray(X_train)
            idx_bg = _sample_indices(len(X_train_arr), kernel_background_samples, seed=42)
            bg = X_train_arr[idx_bg]
        else:
            idx_bg = _sample_indices(len(X_arr), kernel_background_samples, seed=42)
            bg = X_arr[idx_bg]
        
        # Sample validation data for efficiency
        idx_val = _sample_indices(len(X_arr), kernel_val_samples, seed=1000)
        X_val_use = X_arr[idx_val]
        
        # Create predict function that handles different model types
        def predict_fn(z):
            z = np.asarray(z)
            if task_type == "regression":
                return model.predict(z)
            # Classification: prefer predict_proba, fallback to decision_function
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(z)
                if proba.shape[1] == 2:
                    return proba[:, 1]  # Binary: return positive class probability
                return proba  # Multi-class: return all probabilities
            if hasattr(model, "decision_function"):
                s = model.decision_function(z)
                if s.ndim == 1:
                    # Binary: convert to probability
                    return 1.0 / (1.0 + np.exp(-s))
                # Multi-class: return as-is (scores)
                return s
            raise ValueError(f"{model.__class__.__name__} lacks predict_proba and decision_function.")
        
        explainer = shap.KernelExplainer(predict_fn, bg)
        shap_vals = explainer.shap_values(X_val_use, nsamples="auto", silent=True)
        shap_vals = _ensure_shap_2d(shap_vals)
        if shap_vals.ndim != 2:
            raise ValueError(f"SHAP values shape {shap_vals.shape} is not 2D after normalization")
        if shap_vals.shape[1] != X.shape[1]:
            raise ValueError(f"SHAP shape {shap_vals.shape} doesn't match X columns {X.shape[1]}")
        return {f: float(np.mean(np.abs(shap_vals[:, i]))) for i, f in enumerate(X.columns)}
    except Exception as e:
        logger.warning("KernelExplainer failed for %s: %s. Using permutation.", model_name, e)
        return _permutation_fallback(model, X, y, task_type)


def compute_global_importance(
    model: object,
    model_name: str,
    X: pd.DataFrame,
    y: Optional[pd.Series] = None,
    task_type: str = "binary",
    X_train: Optional[pd.DataFrame] = None,
    linear_background_samples: int = 100,
    kernel_background_samples: int = 100,
    kernel_val_samples: int = 50,
) -> Dict[str, float]:
    """
    Unified importance: TreeExplainer (tree) / LinearExplainer (linear) / KernelExplainer (KNN,SVM).
    Tree: CatBoost, RandomForest, XGBoost, LightGBM. Linear: LogisticRegression, Ridge, ElasticNet.
    Other (KNN, SVM): KernelExplainer.
    
    Args:
        model: Fitted model
        model_name: Model name
        X: Validation data (transformed space)
        y: Target (optional, for fallback)
        task_type: Task type
        X_train: Training data (transformed space) for background samples
        linear_background_samples: Background samples for LinearExplainer
        kernel_background_samples: Background samples for KernelExplainer
        kernel_val_samples: Validation samples for KernelExplainer
    """
    if _is_tree(model_name):
        return compute_importance_tree(model, X, model_name, y, task_type, X_train)
    if _is_linear(model_name):
        return compute_importance_linear(
            model, X, model_name, y, task_type, X_train, linear_background_samples
        )
    return compute_importance_kernel(
        model, X, model_name, y, task_type, X_train, kernel_background_samples, kernel_val_samples
    )


def rank_features(importance: Dict[str, float]) -> List[Tuple[str, float]]:
    """Sort features by importance descending."""
    return sorted(importance.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------------------
# Individual-level (single-sample) SHAP explanation for the prediction ExplainerAgent; separate from training-time global SHAP.
# ---------------------------------------------------------------------------

def _pipeline_transform_row(pipe, X_row_df: pd.DataFrame) -> np.ndarray:
    """Apply the pipeline preprocessing steps to a single-row DataFrame and return a (1, n_features) array."""
    if not hasattr(pipe, "steps"):
        return np.asarray(X_row_df).reshape(1, -1)
    steps = list(pipe.steps)
    if len(steps) <= 1:
        return np.asarray(X_row_df).reshape(1, -1)
    preprocessor = pipe[:-1]
    X_t = preprocessor.transform(X_row_df)
    if hasattr(X_t, "toarray"):
        X_t = X_t.toarray()
    X_t = np.asarray(X_t)
    if X_t.ndim == 1:
        X_t = X_t.reshape(1, -1)
    return X_t


def _model_name_from_estimator(est) -> str:
    """Infer the shap_utils model name from the estimator type (TREE_MODELS / LINEAR_MODELS)."""
    name = type(est).__name__
    mapping = {
        "XGBClassifier": "XGBoost", "XGBRegressor": "XGBRegressor",
        "LGBMClassifier": "LightGBM", "LGBMRegressor": "LGBMRegressor",
        "CatBoostClassifier": "CatBoost", "CatBoostRegressor": "CatBoostRegressor",
        "RandomForestClassifier": "RandomForest", "RandomForestRegressor": "RandomForestRegressor",
    }
    return mapping.get(name, name)


def compute_single_sample_shap(
    pipe: object,
    X_row: pd.DataFrame,
    task_type: str = "binary",
    feature_names: Optional[List[str]] = None,
    save_dir: Optional["Path"] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Single-sample SHAP explanation: generate top_positive_drivers, top_negative_drivers, and force/waterfall plot paths for one prediction.
    This is distinct from training-time global SHAP (compute_global_importance) and is used only for individual prediction explanations.
    If the model is unsupported or computation fails, return a non-empty error so callers can use a graceful fallback.

    Returns:
        dict: top_positive_drivers (list[str]), top_negative_drivers (list[str]),
        force_plot_path, waterfall_plot_path (str or None), error (str or None).
    """
    from pathlib import Path
    res: Dict[str, Any] = {
        "top_positive_drivers": [],
        "top_negative_drivers": [],
        "force_plot_path": None,
        "waterfall_plot_path": None,
        "error": None,
    }
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    try:
        import shap
    except ImportError as e:
        res["error"] = "SHAP not installed; individual explanation unavailable."
        return res

    # Single-row input: the pipeline may include a preprocessor, so transform before passing data to the final step.
    try:
        if hasattr(pipe, "steps") and len(pipe.steps) > 1:
            X_transformed = _pipeline_transform_row(pipe, X_row)
        else:
            X_transformed = np.asarray(X_row).reshape(1, -1)
        if X_transformed.size == 0:
            res["error"] = "Empty input row."
            return res
        feature_names_in = feature_names or list(X_row.columns) if hasattr(X_row, "columns") else [str(i) for i in range(X_transformed.shape[1])]
        if len(feature_names_in) != X_transformed.shape[1]:
            feature_names_in = [str(i) for i in range(X_transformed.shape[1])]
    except Exception as e:
        res["error"] = f"Input transform failed: {e!r}"
        return res

    estimator = pipe[-1] if hasattr(pipe, "__getitem__") else pipe
    model_name = _model_name_from_estimator(estimator)

    # Use TreeExplainer only for tree models (no background needed); return an error for unsupported models so callers can fall back.
    if not _is_tree(model_name):
        res["error"] = f"Individual SHAP only supported for tree models (got {model_name}); use fallback."
        return res

    try:
        if task_type != "regression" and model_name in {"XGBoost", "LightGBM"}:
            try:
                explainer = shap.TreeExplainer(estimator, model_output="probability")
            except (ValueError, TypeError) as ve:
                if "model_output" in str(ve) or "probability" in str(ve).lower():
                    explainer = shap.TreeExplainer(estimator, model_output="raw")
                else:
                    raise
        else:
            explainer = shap.TreeExplainer(estimator)
        shap_vals = explainer.shap_values(X_transformed)
        expected = explainer.expected_value
    except Exception as e:
        logger.warning("TreeExplainer failed for single sample: %s", e)
        res["error"] = f"SHAP computation failed: {e!r}"
        return res

    try:
        shap_vals = _ensure_shap_2d(shap_vals)
        if shap_vals.size == 0 or shap_vals.shape[0] < 1:
            res["error"] = "SHAP values empty."
            return res
        sv_row = shap_vals[0]
        base_val = expected
        if isinstance(expected, (list, np.ndarray)) and len(expected) > 1:
            base_val = float(expected[1])
        else:
            base_val = float(expected) if expected is not None else 0.0
    except Exception as e:
        res["error"] = f"SHAP value processing failed: {e!r}"
        return res

    # Drivers: positive SHAP values increase the prediction and negative values decrease it; sort by absolute value and take top_n.
    order_desc = np.argsort(-sv_row)
    order_asc = np.argsort(sv_row)
    top_pos = [feature_names_in[i] for i in order_desc if i < len(feature_names_in) and float(sv_row[i]) > 1e-9][:top_n]
    top_neg = [feature_names_in[i] for i in order_asc if i < len(feature_names_in) and float(sv_row[i]) < -1e-9][:top_n]
    res["top_positive_drivers"] = top_pos
    res["top_negative_drivers"] = top_neg

    # Save force/waterfall plots by writing renderable objects to PNG paths.
    if save_dir:
        try:
            _set_chart_font()
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig_path = save_dir / "shap_force_plot.png"
            try:
                shap.force_plot(
                    base_val,
                    sv_row,
                    X_transformed[0],
                    feature_names=feature_names_in,
                    show=False,
                    matplotlib=True,
                )
                plt.savefig(fig_path, bbox_inches="tight", dpi=100)
                plt.close()
                res["force_plot_path"] = str(fig_path)
            except Exception as e1:
                logger.debug("Force plot failed: %s", e1)
                try:
                    plt.close()
                except Exception:
                    pass

            wf_path = save_dir / "shap_waterfall_plot.png"
            try:
                if hasattr(shap, "Explanation") and hasattr(shap, "plots"):
                    expl = shap.Explanation(
                        values=sv_row,
                        base_values=base_val,
                        data=X_transformed[0],
                        feature_names=feature_names_in,
                    )
                    shap.plots.waterfall(expl, show=False)
                    plt.savefig(wf_path, bbox_inches="tight", dpi=100)
                    plt.close()
                    res["waterfall_plot_path"] = str(wf_path)
                else:
                    raise AttributeError("shap.Explanation or plots not available")
            except Exception as e2:
                logger.debug("Waterfall plot failed: %s", e2)
                try:
                    plt.close()
                except Exception:
                    pass
                try:
                    plt.figure(figsize=(8, 6))
                    plt.barh(range(len(feature_names_in)), sv_row, color=["#ff0051" if x > 0 else "#008bfb" for x in sv_row])
                    plt.yticks(range(len(feature_names_in)), feature_names_in, fontsize=8)
                    plt.xlabel("SHAP value")
                    plt.tight_layout()
                    plt.savefig(wf_path, bbox_inches="tight", dpi=100)
                    plt.close()
                    res["waterfall_plot_path"] = str(wf_path)
                except Exception as e3:
                    logger.debug("Simple waterfall fallback failed: %s", e3)
        except Exception as e0:
            logger.debug("Plot save failed: %s", e0)

    return res


def plot_shap_interaction_heatmap(
    interaction_matrix: np.ndarray,
    feature_names: List[str],
    max_display: int = 25,
    title: str = "Mean |SHAP interaction|",
    group_defs: Optional[Dict[str, List[str]]] = None,
    priority_features: Optional[List[str]] = None,
    fig_w_in: float = 12.0,
    cmap: str = "PuOr_r",
    model_name: Optional[str] = None,
) -> "matplotlib.figure.Figure":
    """
    Square bubble heatmap for SHAP interaction values with group support.
    Lower triangle shows bubbles, upper triangle shows colorbar legend.
    
    Args:
        interaction_matrix: Mean absolute interaction matrix (n_features, n_features)
        feature_names: List of feature names
        max_display: Maximum number of features to display
        title: Plot title
        group_defs: Dict mapping group names to feature lists (e.g., {"Comorbidity": [...], "Immunosuppression": [...]})
        priority_features: List of features to prioritize in display order
        fig_w_in: Figure width in inches
        cmap: Colormap name
    """
    _set_chart_font()
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    from matplotlib.patches import FancyBboxPatch

    def bubble_area(values, *, vmin, vmax, min_area, max_area):
        if vmax <= vmin:
            return np.full_like(values, min_area, dtype=float)
        scaled = (values - vmin) / (vmax - vmin)
        scaled = np.clip(scaled, 0.0, 1.0)
        return min_area + scaled * (max_area - min_area)

    def max_bubble_area_fit(fig_w_in, *, m, fill=0.72):
        if m <= 0:
            return 800.0
        cell_pt = fig_w_in * 72.0 / float(m)
        max_diameter_pt = max(6.0, cell_pt * float(fill))
        return float(((max_diameter_pt / 2.0) ** 2) * np.pi)

    def add_inplot_legends(fig, ax, sc, *, tick_vals, vmin, vmax, bubble_max_area):
        box_ax = ax.inset_axes([0.64, 0.54, 0.33, 0.44])
        box_ax.set_facecolor("none")
        box_ax.axis("off")
        box_ax.add_patch(
            FancyBboxPatch(
                (0.0, 0.0), 1.0, 1.0,
                transform=box_ax.transAxes,
                boxstyle="round,pad=0.012,rounding_size=0.012",
                facecolor="white", edgecolor="#DDDDDD", linewidth=0.8, alpha=0.90, zorder=1,
            )
        )
        box_ax.text(0.5, 0.90, "Mean |SHAP interaction|", ha="center", va="center", fontsize=12, zorder=2)
        cax = box_ax.inset_axes([0.06, 0.16, 0.18, 0.62])
        cb = fig.colorbar(sc, cax=cax, orientation="vertical")
        cb.set_ticks([vmin, (vmin + vmax) / 2.0, vmax])
        cb.set_ticklabels([f"{float(tick_vals[0]):.3f}", f"{float(tick_vals[1]):.3f}", f"{float(tick_vals[2]):.3f}"])
        cb.ax.tick_params(labelsize=9.5, length=2.5, width=0.8)
        cb.outline.set_linewidth(0.6)
        lax = box_ax.inset_axes([0.36, 0.08, 0.60, 0.78])
        lax.set_xlim(-0.25, 1.2)
        lax.set_ylim(0, 1)
        lax.axis("off")
        for y0, v in zip([0.82, 0.50, 0.18], [tick_vals[2], tick_vals[1], tick_vals[0]]):
            s0 = bubble_area(np.array([float(v)]), vmin=vmin, vmax=vmax, min_area=10.0, max_area=bubble_max_area)[0]
            lax.scatter([0.20], [y0], s=s0, facecolors="none", edgecolors="#666666", linewidths=1.0, clip_on=False)
            lax.text(0.72, y0, f"{float(v):.3f}", ha="left", va="center", fontsize=9.5)

    group_defs = group_defs or {}
    comorb_cols = group_defs.get("Comorbidity", [])
    immuno_cols = group_defs.get("Immunosuppression", [])

    # Determine features to use
    n_raw = min(len(feature_names), max_display, interaction_matrix.shape[0])
    feature_names_raw = feature_names[:n_raw]
    interaction_matrix = interaction_matrix[:n_raw, :n_raw]

    # Build display groups (consistent with bar/beeswarm/rose plot)
    feats_in_data = set(feature_names_raw)
    comorb_in = [f for f in comorb_cols if f in feats_in_data]
    immuno_in = [f for f in immuno_cols if f in feats_in_data]
    other_features = [f for f in feature_names_raw if f not in comorb_cols and f not in immuno_cols]

    display_items = []
    if comorb_in:
        display_items.append("Comorbidity")
    if immuno_in:
        display_items.append("Immunosuppression")
    display_items.extend(other_features)

    if priority_features is not None:
        priority_set = set(priority_features)
        ordered_first = [x for x in priority_features if x in display_items]
        remaining = [x for x in display_items if x not in priority_set]
        display_items = ordered_first + remaining

    # Group indices: display_name -> original feature index list
    name_to_raw_idx = {f: i for i, f in enumerate(feature_names_raw)}
    group_to_indices = {}
    if comorb_in:
        group_to_indices["Comorbidity"] = [name_to_raw_idx[f] for f in comorb_in if f in name_to_raw_idx]
    if immuno_in:
        group_to_indices["Immunosuppression"] = [name_to_raw_idx[f] for f in immuno_in if f in name_to_raw_idx]
    for f in other_features:
        if f in name_to_raw_idx:
            group_to_indices[f] = [name_to_raw_idx[f]]

    n_disp = len(display_items)

    # Aggregate interaction matrix
    agg_interaction = np.zeros((n_disp, n_disp))
    for ii in range(n_disp):
        for jj in range(n_disp):
            I1 = group_to_indices.get(display_items[ii], [])
            I2 = group_to_indices.get(display_items[jj], [])
            if ii != jj:
                if I1 and I2:
                    agg_interaction[ii, jj] = float(np.sum(interaction_matrix[np.ix_(I1, I2)]))
                else:
                    agg_interaction[ii, jj] = 0.0
            else:
                idx_pairs = [(i, j) for i in I1 for j in I2 if i < j]
                if idx_pairs:
                    rows, cols = zip(*idx_pairs)
                    agg_interaction[ii, jj] = float(np.sum(interaction_matrix[rows, cols]))
                else:
                    agg_interaction[ii, jj] = 0.0

    mean_abs_interaction = agg_interaction
    feature_names_display = display_items
    m = n_disp

    records = []
    for i in range(m):
        for j in range(m):
            if i <= j:
                continue
            records.append((j, m - 1 - i, float(mean_abs_interaction[i, j])))

    df_plot = pd.DataFrame(records, columns=["x", "y", "value"])
    vmin = float(df_plot["value"].min())
    vmax = float(df_plot["value"].max())
    tick_vals = np.array([vmin, (vmin + vmax) / 2.0, vmax], dtype=float)
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

    bubble_max_area = max_bubble_area_fit(fig_w_in, m=m, fill=0.72)
    areas = bubble_area(df_plot["value"].values, vmin=vmin, vmax=vmax, min_area=10.0, max_area=bubble_max_area)

    fig, ax = plt.subplots(figsize=(fig_w_in, fig_w_in * 0.85))
    
    # Adjust ylim to leave space for model name above the first row of bubbles
    # Reserve space at the top: if model_name exists, add extra space (0.8 units)
    top_margin = 0.8 if model_name else 0.5
    ax.set_xlim(-0.5, m - 0.5)
    ax.set_ylim(-0.5 - top_margin, m - 0.5)
    
    sc = ax.scatter(
        df_plot["x"], df_plot["y"],
        s=areas, c=df_plot["value"], cmap=cmap, norm=norm,
        alpha=0.85, edgecolors="#333333", linewidths=0.4,
    )
    ax.set_xticks(np.arange(m))
    ax.set_yticks(np.arange(m))
    ax.set_xticklabels(feature_names_display, rotation=90, ha="center", fontsize=12)
    ax.set_yticklabels(feature_names_display[::-1], fontsize=12)
    # ax.set_xlabel("Driving factors")
    # ax.set_ylabel("Driving factors")
    ax.set_aspect("equal")
    
    # Add model name inside the plot, above the first row of bubbles
    if model_name:
        # Position model name at the top-left, within the plot area
        # Use data coordinates: x=-0.5 (left edge), y=m-0.5+0.4 (above first row, in the reserved space)
        ax.text(-0.5, m - 0.5 + 0.4, model_name, 
                fontsize=16, fontweight="bold", ha="left", va="bottom")
    
    add_inplot_legends(fig, ax, sc, tick_vals=tick_vals, vmin=vmin, vmax=vmax, bubble_max_area=bubble_max_area)
    plt.tight_layout()
    return fig


def plot_shap_bar(ranking: List[Tuple[str, float]], top_n: int = 15, title: str = "SHAP importance") -> "matplotlib.figure.Figure":
    """Create horizontal bar chart from importance ranking (4x3 size)."""
    _set_chart_font()
    import matplotlib.pyplot as plt

    top = ranking[:top_n]
    if not top:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return fig
    names = [x[0] for x in reversed(top)]
    vals = [x[1] for x in reversed(top)]
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.barh(range(len(names)), vals, height=0.7)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7)
    ax.set_xlabel("Mean |SHAP|", fontsize=8)
    ax.set_title(title, fontsize=9)
    plt.tight_layout()
    return fig


def plot_shap_bar_native(
    shap_matrix: np.ndarray,
    X_for_plot: np.ndarray,
    feature_names: List[str],
    top_n: int = 15,
) -> "matplotlib.figure.Figure":
    """SHAP-native bar plot (mean |SHAP|) so it visually pairs with the beeswarm plot."""
    try:
        import shap
    except ImportError:
        import matplotlib.pyplot as plt
        _set_chart_font()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "SHAP not available", ha="center", va="center")
        return fig
    _set_chart_font()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if shap_matrix.size == 0 or shap_matrix.shape[1] != len(feature_names):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No SHAP data", ha="center", va="center")
        return fig
    X_df = pd.DataFrame(X_for_plot, columns=feature_names)
    shap.summary_plot(shap_matrix, X_df, max_display=top_n, plot_type="bar", show=False)
    fig = plt.gcf()
    plt.tight_layout()
    return fig


def plot_shap_beeswarm(
    shap_matrix: np.ndarray,
    X_for_plot: np.ndarray,
    feature_names: List[str],
    top_n: int = 15,
) -> "matplotlib.figure.Figure":
    """Standalone SHAP beeswarm plot. Uses current figure from shap.summary_plot and returns it."""
    try:
        import shap
    except ImportError:
        import matplotlib.pyplot as plt
        _set_chart_font()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "SHAP not available", ha="center", va="center")
        return fig
    _set_chart_font()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if shap_matrix.size == 0 or shap_matrix.shape[1] != len(feature_names):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No SHAP data", ha="center", va="center")
        return fig
    X_df = pd.DataFrame(X_for_plot, columns=feature_names)
    shap.summary_plot(shap_matrix, X_df, max_display=top_n, show=False)
    fig = plt.gcf()
    plt.tight_layout()
    return fig


def plot_shap_bar_beeswarm_rose(
    importance_df: pd.DataFrame,
    shap_matrix: np.ndarray,
    X_for_plot: np.ndarray,
    feature_names: List[str],
    group_defs: Optional[Dict[str, List[str]]] = None,
    top_k: int = 15,
    figsize: Tuple[float, float] = (16, 10),
    cmap_name: str = "PuOr_r",
    random_state: int = 42,
    subplot_label: str = "(a)",
    show: bool = True,
) -> "matplotlib.figure.Figure":
    """
    Combined plot: horizontal bar chart (left), beeswarm plot (right), and rose chart (inset).
    Supports feature grouping (Comorbidity, Immunosuppression).
    
    Args:
        importance_df: DataFrame with columns ['feature', 'mean_abs_shap']
        shap_matrix: SHAP values matrix (n_samples, n_features)
        X_for_plot: Feature values matrix (n_samples, n_features) for coloring beeswarm
        feature_names: List of feature names matching columns
        group_defs: Dict mapping group names to feature lists
        top_k: Number of top features to display
        figsize: Figure size (width, height)
        cmap_name: Colormap name
        random_state: Random seed for jitter
        subplot_label: Label for subplot (e.g., "(a)")
        show: Whether to show the plot
    """
    _set_chart_font()
    import matplotlib.pyplot as plt

    group_defs = group_defs or {}
    comorb_cols = group_defs.get("Comorbidity", [])
    immuno_cols = group_defs.get("Immunosuppression", [])

    feats_in_df = set(importance_df["feature"].values)
    comorb_in = [f for f in comorb_cols if f in feats_in_df]
    immuno_in = [f for f in immuno_cols if f in feats_in_df]
    other_features = [
        f for f in importance_df["feature"].values
        if f not in comorb_cols and f not in immuno_cols
    ]

    def _sum_imp(feats):
        return float(importance_df.loc[importance_df["feature"].isin(feats), "mean_abs_shap"].sum())

    imp_comorb = _sum_imp(comorb_in) if comorb_in else 0.0
    imp_immuno = _sum_imp(immuno_in) if immuno_in else 0.0
    imp_others = importance_df.set_index("feature").loc[other_features, "mean_abs_shap"].to_dict()

    display_items = []
    if comorb_cols:
        display_items.append(("Comorbidity", imp_comorb))
    if immuno_cols:
        display_items.append(("Immunosuppression", imp_immuno))
    for f in other_features:
        display_items.append((f, imp_others.get(f, 0.0)))
    display_items.sort(key=lambda x: x[1], reverse=True)
    display_items = display_items[:top_k]
    sorted_display_names = np.array([x[0] for x in display_items])
    sorted_importance = np.array([x[1] for x in display_items])
    n_features = len(sorted_display_names)
    n_samples = shap_matrix.shape[0]

    name_to_idx = {f: i for i, f in enumerate(feature_names)}
    shap_by_feature = np.zeros((n_samples, n_features))
    feature_values = np.zeros((n_samples, n_features))
    X_min = X_for_plot.min(axis=0)
    X_max = X_for_plot.max(axis=0)
    X_range = np.where(X_max > X_min, X_max - X_min, 1.0)
    X_norm = (X_for_plot - X_min) / X_range

    for j, name in enumerate(sorted_display_names):
        if name == "Comorbidity":
            cols = [name_to_idx[f] for f in comorb_in if f in name_to_idx]
            if cols:
                shap_by_feature[:, j] = shap_matrix[:, cols].sum(axis=1)
                feature_values[:, j] = X_norm[:, cols].mean(axis=1)
            else:
                feature_values[:, j] = 0.5
        elif name == "Immunosuppression":
            cols = [name_to_idx[f] for f in immuno_in if f in name_to_idx]
            if cols:
                shap_by_feature[:, j] = shap_matrix[:, cols].sum(axis=1)
                feature_values[:, j] = X_norm[:, cols].mean(axis=1)
            else:
                feature_values[:, j] = 0.5
        else:
            if name in name_to_idx:
                idx = name_to_idx[name]
                shap_by_feature[:, j] = shap_matrix[:, idx]
                feature_values[:, j] = X_norm[:, idx]

    vmax_imp = float(sorted_importance.max()) if n_features else 1.0
    cmap = plt.get_cmap(cmap_name)
    norm_imp = plt.Normalize(vmin=0, vmax=vmax_imp)
    norm_feat = plt.Normalize(vmin=0, vmax=1)

    # Set DPI to at least 300 for high resolution
    fig = plt.figure(figsize=figsize, constrained_layout=False, dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2], wspace=0.0)
    ax_bar = fig.add_subplot(gs[0])
    ax_shap = fig.add_subplot(gs[1])

    y_pos = np.arange(n_features)
    ax_bar.barh(y_pos, sorted_importance, height=0.65,
                color=cmap(norm_imp(sorted_importance)), edgecolor="none")
    ax_bar.set_xlim(vmax_imp, 0)
    for i in range(n_features):
        ax_bar.text(0, y_pos[i], sorted_display_names[i], ha='right', va='center', fontsize=15, color='black')
    ax_bar.set_ylim(-0.5, n_features - 0.5)
    ax_bar.invert_yaxis()
    ax_bar.yaxis.tick_right()
    ax_bar.set_yticks(y_pos)
    ax_bar.set_yticklabels([])
    ax_bar.tick_params(axis="y", length=0, pad=10)
    ax_bar.set_xlabel("Mean |SHAP| (contribution)", fontsize=15)
    ax_bar.tick_params(axis='x', labelsize=15)
    ax_bar.spines["left"].set_visible(False)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)
    ax_bar.spines["bottom"].set_visible(True)

    cax1 = ax_bar.inset_axes([-0.1, 0, 0.02, 1])
    cb1 = plt.colorbar(plt.cm.ScalarMappable(norm=norm_imp, cmap=cmap), cax=cax1)
    cb1.set_ticks([])
    cb1.outline.set_visible(False)
    cax1.text(0.5, 1.02, "High", ha="center", va="bottom", transform=cax1.transAxes, fontsize=15)
    cax1.text(0.5, -0.02, "Low", ha="center", va="top", transform=cax1.transAxes, fontsize=15)

    # Beeswarm plot: Reference implementation from notebook
    # Points are distributed along x-axis (SHAP values), with y-axis jitter to avoid overlap
    np.random.seed(random_state)
    for i in range(n_features):
        y_jitter = np.random.normal(loc=i, scale=0.08, size=n_samples)
        ax_shap.scatter(shap_by_feature[:, i], y_jitter,
                        c=feature_values[:, i], cmap=cmap, s=10,
                        alpha=0.8, edgecolors="none", norm=norm_feat)
    ax_shap.axvline(0, color="grey", linewidth=0.5, alpha=0.5)
    ax_shap.set_ylim(-0.5, n_features - 0.5)
    ax_shap.invert_yaxis()
    ax_shap.set_yticks([])
    ax_shap.set_xlabel("SHAP Value (impact on model output)", fontsize=15)
    ax_shap.tick_params(axis='x', labelsize=15)
    ax_shap.spines["top"].set_visible(False)
    ax_shap.spines["right"].set_visible(False)
    ax_shap.spines["left"].set_visible(False)

    cax2 = ax_shap.inset_axes([1.05, 0, 0.02, 1])
    cb2 = plt.colorbar(plt.cm.ScalarMappable(norm=norm_feat, cmap=cmap), cax=cax2)
    cb2.set_ticks([])
    cb2.set_label("Feature Value", rotation=270, labelpad=15, fontsize=15)
    cb2.outline.set_visible(False)
    cax2.text(0.5, 1.02, "High", ha="center", va="bottom", transform=cax2.transAxes, fontsize=15)
    cax2.text(0.5, -0.02, "Low", ha="center", va="top", transform=cax2.transAxes, fontsize=15)

    # Enlarge rose chart: increase size from [0.10, 0.12, 0.25, 0.38] to [0.10, 0.10, 0.30, 0.45]
    inset_ax_rect = [0.10, 0.10, 0.30, 0.45]
    ax_rose = fig.add_axes(inset_ax_rect, projection='polar')
    ax_rose.patch.set_alpha(0)
    num_vars = n_features
    widths = (sorted_importance / np.maximum(sorted_importance.sum(), 1e-12)) * 2 * np.pi
    widths = np.asarray(widths)
    base_length, fixed_increment, colored_ring_width = 3.0, 0.5, 2.0
    total_lengths = np.array([base_length + i * fixed_increment for i in range(num_vars)])
    inner_heights = np.maximum(0, total_lengths - colored_ring_width)
    inner_colors = ['#EAEAEA', '#FFFFFF'] * (num_vars // 2 + 1)
    inner_colors = inner_colors[:num_vars]
    one_oclock_offset = np.pi / 21
    thetas = np.asarray(np.cumsum([0] + widths[:-1].tolist()) - one_oclock_offset)

    ax_rose.bar(x=thetas, height=inner_heights, width=widths, color=inner_colors,
                align='edge', edgecolor='white', linewidth=1.5)
    ax_rose.bar(x=thetas, height=[colored_ring_width] * num_vars, width=widths, bottom=inner_heights,
                color=cmap(norm_imp(sorted_importance)), align='edge', edgecolor='white', linewidth=1.5)
    ax_rose.set_yticklabels([])
    ax_rose.set_xticklabels([])
    ax_rose.spines['polar'].set_visible(False)
    ax_rose.grid(False)
    ax_rose.set_theta_zero_location('N')
    ax_rose.set_theta_direction(-1)
    ax_rose.set_ylim(0, max(total_lengths) + 2)

    total_imp = float(np.sum(sorted_importance))
    thresh = float(np.max(sorted_importance) * 0.1) if n_features else 0
    outer_radii = inner_heights + colored_ring_width
    for i in range(num_vars):
        if sorted_importance[i] >= thresh and total_imp > 0:
            pct = sorted_importance[i] / total_imp * 100
            theta_center = thetas[i] + widths[i] / 2
            label_r = outer_radii[i] * 1.2
            ax_rose.text(theta_center, label_r, f"{pct:.1f}%", ha="center", va="center", fontsize=14, rotation=0)

    # Add model name inside the plot (without parentheses, without subplot label)
    if subplot_label and subplot_label.startswith("(") and subplot_label.endswith(")"):
        # Extract model name from subplot_label like "(LogisticRegression)"
        model_name = subplot_label[1:-1]
        ax_bar.text(0.0, 1.02, model_name, transform=ax_bar.transAxes, fontsize=20, fontweight="bold")
    elif subplot_label:
        # If subplot_label doesn't have parentheses, use it as is
        ax_bar.text(0.0, 1.02, subplot_label, transform=ax_bar.transAxes, fontsize=20, fontweight="bold")
    if show:
        plt.show()
    return fig