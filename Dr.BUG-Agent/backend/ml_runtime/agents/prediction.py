"""PredictionAgent: validation, preprocessing, and local model inference.

Responsibilities: read model_path from ModelRegistry, load the joblib model, reorder input by feature_order,
run local inference, and write risk_score, predicted_label, and prediction_metadata.
All patient-level predictions are completed locally without calling an external LLM.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.ml_runtime.core.prediction_context import PredictionContext
from backend.ml_runtime.core.model_registry import ModelRegistry
from backend.ml_runtime.core.schemas import ModelEntry

logger = logging.getLogger(__name__)


def _load_pipeline(path: Path):
    """Load a joblib/pickle model from path; raise on failure."""
    import joblib
    return joblib.load(path)


class PredictionAgent:
    """
    Prediction pipeline: validation (handled by the state machine) -> normalize input -> load the local model -> infer.
    Writes normalized_input_payload, risk_score, predicted_label, and prediction_metadata to ctx.
    If the model is missing, required fields are incomplete, or inference fails, set ctx.error and do not write results.
    """

    def run(self, ctx: PredictionContext, registry: ModelRegistry) -> None:
        """
        Normalize input, load the model, run inference, and write results back to ctx.
        Use entry.model_path, feature_order, threshold, and label_mapping; configuration is not hard-coded in the agent.
        """
        ctx.error = None

        entry = registry.get(ctx.model_id)
        if not entry:
            ctx.error = f"Model not found: {ctx.model_id}"
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        model_path = registry.resolve_model_path(ctx.model_id)
        if model_path is None or not model_path.exists():
            ctx.error = (
                "Model file could not be loaded for prediction.\n\n"
                f"- model_id: {ctx.model_id}\n"
                f"- configured model_path: {entry.model_path or '(empty)'}\n"
                f"- resolved path: {str(model_path) if model_path is not None else '(unresolved)'}\n\n"
                "Please ensure the published model package exists and registry configuration is up to date."
            )
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        # Normalize: keep only required_features and convert values to model-compatible types.
        ctx.normalized_input_payload = self._normalize(
            ctx.raw_input_payload or {}, entry.required_features, entry.preprocess_config
        )

        # Build a single-row DataFrame by feature_order, filling missing features with NaN.
        order = list(entry.feature_order or entry.required_features)
        if not order:
            ctx.error = f"Model {ctx.model_id} has no feature_order or required_features."
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        X_row, missing = self._payload_to_row(ctx.normalized_input_payload, order)
        # Missing values are preserved as NaN in X_row and passed downstream; do not block prediction.
        # Downstream preprocessing / model logic may impute or handle missing as designed.

        try:
            pipe = _load_pipeline(model_path)
        except Exception as e:
            logger.exception("Failed to load model: %s", model_path)
            ctx.error = f"Failed to load model: {model_path}: {e!r}"
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        ctx.loaded_pipeline = pipe

        if not hasattr(pipe, "predict"):
            ctx.error = f"Loaded object at {model_path} has no predict method."
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        X_sub = pd.DataFrame([X_row], columns=order)
        X_sub = X_sub.reindex(columns=order, fill_value=np.nan)

        try:
            pred = pipe.predict(X_sub)
        except Exception as e:
            logger.exception("Inference failed: %s", e)
            ctx.error = f"Inference failed: {e!r}"
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        pred = np.atleast_1d(pred)
        if pred.size == 0:
            ctx.error = "Model returned empty prediction."
            ctx.risk_score = None
            ctx.predicted_label = None
            return

        pred_val = float(pred[0])
        proba = None
        if hasattr(pipe, "predict_proba"):
            try:
                proba = pipe.predict_proba(X_sub)
            except Exception:
                pass
            if proba is not None:
                proba = np.atleast_2d(proba)

        # risk_score: use positive-class probability for binary classification; use the prediction for regression.
        if entry.task_type == "binary" and proba is not None and proba.shape[1] >= 2:
            ctx.risk_score = float(proba[0][1])
        elif entry.task_type == "regression":
            ctx.risk_score = pred_val
        else:
            ctx.risk_score = pred_val

        # predicted_label: use label_mapping when available; otherwise use the prediction or a default.
        ctx.predicted_label = self._to_label(entry, pred_val, pred[0])
        ctx.prediction_metadata = {
            "model_id": ctx.model_id,
            "threshold": entry.threshold,
            "task_type": entry.task_type,
        }
        if proba is not None:
            ctx.prediction_metadata["probabilities"] = proba[0].tolist()

    def _normalize(
        self,
        payload: Dict[str, Any],
        required_features: List[str],
        preprocess_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert payload to model-ready key/value pairs. Keep only required_features and numeric-convert fields when possible.
        preprocess_config is reserved for future options such as feature_bounds or dtype; currently only basic type conversion is applied.
        """
        preprocess_config = preprocess_config or {}
        out: Dict[str, Any] = {}
        for f in required_features:
            v = payload.get(f)
            if v is None or v == "":
                out[f] = None
                continue
            if isinstance(v, (int, float)):
                out[f] = float(v)
            elif isinstance(v, str):
                s = v.strip()
                if not s:
                    out[f] = None
                else:
                    try:
                        out[f] = float(s)
                    except (ValueError, TypeError):
                        out[f] = v
            else:
                out[f] = v
        return out

    def _payload_to_row(
        self, payload: Dict[str, Any], order: List[str]
    ) -> tuple[List[float], List[str]]:
        """
        Convert the normalized payload into a single numeric row ordered by order; return missing required features separately.
        Returns (row, missing_names).
        """
        row: List[float] = []
        missing: List[str] = []
        for col in order:
            v = payload.get(col)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                missing.append(col)
                row.append(np.nan)
            else:
                try:
                    row.append(float(v))
                except (TypeError, ValueError):
                    missing.append(col)
                    row.append(np.nan)
        return row, missing

    def _to_label(self, entry: ModelEntry, pred_val: float, pred_raw: Any) -> str:
        """Resolve the display predicted_label from task_type and label_mapping."""
        if entry.task_type == "regression":
            return str(round(pred_val, 4))
        try:
            idx = int(np.round(float(pred_raw)))
        except (TypeError, ValueError):
            idx = int(np.round(pred_val))
        return entry.label_mapping.get(str(idx), str(idx))
