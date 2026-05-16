"""Publish a trained model into the model registry after training completes.

Copies the run's model artifact to a stable path under models/<model_id>/
and registers a ModelEntry in models/registry.json so the prediction workflow
can load it without manual edits.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .schemas import ModelEntry

logger = logging.getLogger(__name__)

MODEL_ARTIFACT_NAME = "model.joblib"
DEFAULT_TASK_NAME = "clinical_outcome"
DEFAULT_VERSION = "1.0.0"
DEFAULT_THRESHOLD = 0.5
DEFAULT_BINARY_LABEL_MAPPING = {"0": "Low risk", "1": "High risk"}


def _default_task_name(target_col: str) -> str:
    """Derive task_name from target column or use default."""
    return (target_col or "").strip() or DEFAULT_TASK_NAME


def _default_label_mapping(task_type: str) -> Dict[str, str]:
    """Default label_mapping for binary; empty for regression/multiclass unless provided."""
    if task_type == "binary":
        return dict(DEFAULT_BINARY_LABEL_MAPPING)
    return {}


def publish_trained_model(
    run_dir: Path,
    task_type: str,
    target_col: str,
    final_features: list[str],
    train_metadata: Optional[Dict[str, Any]] = None,
    registry: Optional[Any] = None,
    registry_path: Optional[Path] = None,
    *,
    model_id: Optional[str] = None,
    task_name: Optional[str] = None,
    version: Optional[str] = None,
    threshold: Optional[float] = None,
    label_mapping: Optional[Dict[str, str]] = None,
    train_cohort: Optional[str] = None,
    notes: Optional[str] = None,
) -> ModelEntry:
    """
    Copy the trained model from run_dir to models/<model_id>/model.joblib and
    register it. If registry is provided, use it (and update its cache); otherwise
    create a ModelRegistry from registry_path (default models/registry.json).

    Uses run_dir, task_type, target_col, final_features, and optional train_metadata
    to build a ModelEntry. If model_id is not provided, it is set to
    {task_name}_{run_dir.name} so each run gets a unique id by default.

    If a model with the same model_id already exists in the registry, it is
    replaced (overwrite). All user-facing text is in English.

    Returns the registered ModelEntry.
    """
    from .model_registry import ModelRegistry

    run_dir = Path(run_dir)
    model_file = run_dir / MODEL_ARTIFACT_NAME
    if not model_file.exists():
        raise FileNotFoundError(
            f"Model artifact not found: {model_file}. Complete Phase 5 (Save run) first."
        )

    task_name = (task_name or _default_task_name(target_col)).strip() or DEFAULT_TASK_NAME
    if model_id is None or not str(model_id).strip():
        model_id = f"{task_name}_{run_dir.name}"
    else:
        model_id = str(model_id).strip()

    if registry is None:
        registry = ModelRegistry(registry_path=registry_path)
    existing = registry.get(model_id)
    if existing is not None:
        logger.info(
            "Model with model_id '%s' already exists in registry; replacing with new version.",
            model_id,
        )

    models_root = registry._path.parent
    model_dest_dir = models_root / model_id
    model_dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = model_dest_dir / MODEL_ARTIFACT_NAME
    shutil.copy2(model_file, dest_file)
    logger.info("Copied model to %s", dest_file)

    relative_path = f"{model_id}/{MODEL_ARTIFACT_NAME}"
    version = version or DEFAULT_VERSION
    threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
    label_mapping = label_mapping if label_mapping is not None else _default_label_mapping(task_type)
    train_cohort = train_cohort if train_cohort is not None else run_dir.name
    notes = notes if notes is not None else f"Published from training run {run_dir.name}."

    entry = ModelEntry(
        model_id=model_id,
        task_name=task_name,
        task_type=task_type if task_type in ("binary", "multiclass", "regression") else "binary",
        model_path=relative_path,
        required_features=list(final_features),
        feature_order=list(final_features),
        preprocess_config={},
        threshold=float(threshold),
        label_mapping=label_mapping,
        version=version,
        train_cohort=train_cohort,
        notes=notes,
    )
    registry.register(entry)
    return entry


def publish_from_pipeline_context(
    ctx: Any,
    run_dir: Path,
    registry: Any,
    **overrides: Any,
) -> ModelEntry:
    """
    Publish a trained model using PipelineContext fields.

    ctx must have: task_type, target_col, final_features, train_metadata (optional).
    run_dir is the pipeline run directory containing model.joblib.
    registry is a ModelRegistry instance.
    overrides are passed to publish_trained_model (model_id, task_name, version, etc.).
    """
    entry = publish_trained_model(
        run_dir=run_dir,
        task_type=getattr(ctx, "task_type", "binary"),
        target_col=getattr(ctx, "target_col", "") or "",
        final_features=getattr(ctx, "final_features", []) or [],
        train_metadata=getattr(ctx, "train_metadata", None),
        registry=registry,
        **overrides,
    )

    # Self-check: immediately after publishing, verify PredictionAgent can load the model (at least joblib.load succeeds).
    try:
        from .model_registry import ModelRegistry  # avoid circular at import time
        from backend.ml_runtime.agents.prediction import _load_pipeline  # type: ignore

        # Use registry resolution logic to stay consistent with the prediction path.
        resolved = registry.resolve_model_path(entry.model_id) if isinstance(registry, ModelRegistry) else None
        if resolved is None:
            raise FileNotFoundError(
                f"Published model {entry.model_id} has no resolvable path from registry (model_path={entry.model_path!r})."
            )
        _ = _load_pipeline(resolved)
    except Exception as verify_err:
        logger.warning(
            "Model %s was published but failed post-publish load verification: %r",
            entry.model_id,
            verify_err,
        )
        # Raise to callers so the UI can expose the publish-failure/path issue reason.
        raise

    return entry
