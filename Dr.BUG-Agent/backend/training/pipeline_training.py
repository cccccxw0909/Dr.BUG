"""Multi-stage training: StateMachine phases 1-4 plus Reporter phase 5, mapped from the Streamlit training workflow.

A single task uses params.train_workflow_step and status=waiting_user to coordinate human confirmation gates.
"""

from __future__ import annotations

import json
import logging
import math
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

from backend.config import STATIC_BASE_URL
from backend.runtime import dataset_repo, model_repo, task_repo
from backend.agent.training_contract import normalize_training_payload
from backend.training.feature_source import FeatureStrategy, ResolvedFeaturePlan, resolve_feature_strategy
from backend.training.objective_metric_map import map_to_recommendation_metric, validate_objective_supported
from backend.utils.time_utils import now_iso

logger = logging.getLogger(__name__)


def _registry_publish_labels(
    params: Dict[str, Any],
    publish_overrides: Optional[Dict[str, Any]],
    clinical_task_id_resolved: Optional[str],
    model_id: str,
) -> Dict[str, Any]:
    """
    User-facing names for model_repo (GET /models + prediction pickers).
    Release-step overrides (display_name / model_name) win over training-time model_name.
    """
    po = publish_overrides if isinstance(publish_overrides, dict) else {}
    release_label = str(po.get("display_name") or po.get("model_name") or "").strip()
    training_model_name = str(params.get("model_name") or "").strip()
    primary = release_label or training_model_name
    ct = str(clinical_task_id_resolved or "").strip()
    task_name = primary or ct or model_id
    return {
        "display_name": primary or None,
        "model_name": primary or training_model_name or None,
        "name": primary or training_model_name or None,
        "task_name": task_name,
    }


from backend.ml_runtime.agents.programmer import get_models_for_task
from backend.ml_runtime.pipeline.state_machine import StateMachine
from backend.ml_runtime.utils.shap_utils import TREE_MODELS

# ---- Workflow steps written to task.params.train_workflow_step; worker advances only after submit. ----
STEP_PHASE2 = "phase2"
STEP_PHASE3 = "phase3"
STEP_PHASE4 = "phase4"
STEP_PHASE5 = "phase5"

# result_summary.train_workflow_phase, aligned with requirements semantics.
PHASE3_PENDING = "train_phase3_feature_confirm_pending"
PHASE4_PENDING = "train_phase4_train_config_pending"
PHASE5_PENDING = "train_phase5_publish_pending"
PHASE5_DONE = "train_phase5_done"


def _load_dataframe(dataset_meta: Dict[str, Any]) -> pd.DataFrame:
    path = Path(str(dataset_meta.get("file_path", "")))
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported data file type: {suffix}")


def map_programmer_model_name(model_type: str, ml_task_type: str) -> str:
    """Map workbench `model_type` (snake_case family) to Programmer registry keys."""
    mt = str(model_type).strip().lower()
    if ml_task_type == "regression":
        table = {
            "xgboost": "XGBRegressor",
            "lightgbm": "LGBMRegressor",
            "catboost": "CatBoostRegressor",
            "random_forest": "RandomForest",
            "logistic_regression": "Ridge",
            "svm": "SVR",
            "knn": "KNN",
        }
    else:
        table = {
            "xgboost": "XGBoost",
            "lightgbm": "LightGBM",
            "catboost": "CatBoost",
            "random_forest": "RandomForest",
            "logistic_regression": "LogisticRegression",
            "svm": "SVM",
            "knn": "KNN",
        }
    name = table.get(mt)
    if not name:
        raise ValueError(f"Unsupported model_type: {model_type!r} (ml_task_type={ml_task_type})")
    return name


def resolve_programmer_model_for_final_training(
    params: Dict[str, Any],
    ml_task_type: str,
    y_clean: Any,
) -> str:
    """
    Resolve the Programmer model key for Phase-4 final training.

    `params.model_name` is optional and must be a real programmer model name (e.g. RandomForest).
    Registry numeric IDs or other mistaken values are ignored so `model_type` mapping wins.
    """
    model_type = str(params.get("model_type", "xgboost")).strip()
    default_from_type = map_programmer_model_name(model_type, ml_task_type)
    raw_override = params.get("model_name")
    if not isinstance(raw_override, str):
        return default_from_type
    override = raw_override.strip()
    if not override:
        return default_from_type
    if override.isdigit():
        return default_from_type

    models_dict = get_models_for_task(ml_task_type, y_clean)
    allowed = set(models_dict.keys())
    if override in allowed:
        return override
    by_lower = {k.lower(): k for k in allowed}
    if override.lower() in by_lower:
        return by_lower[override.lower()]

    normalized_token = override.lower().replace(" ", "_").replace("-", "_")
    try:
        candidate = map_programmer_model_name(normalized_token, ml_task_type)
        if candidate in allowed:
            return candidate
    except ValueError:
        pass

    return default_from_type


def _default_ranking_objective(ml_task_type: str) -> str:
    return "mse" if ml_task_type == "regression" else "auroc"


def _pick_best_recommended(sm: StateMachine, objective_metric: str, ml_task_type: str) -> List[str]:
    by_metric = sm.ctx.recommended_sets_by_metric or {}
    key = map_to_recommendation_metric(objective_metric, ml_task_type)
    best = by_metric.get(key)
    if best:
        return list(best)
    if sm.ctx.recommended_sets:
        return list(sm.ctx.recommended_sets[0])
    return []


def _cv_metrics_for_model(cv_results: Dict[str, Any], model_name: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    block = cv_results.get(model_name) if isinstance(cv_results, dict) else None
    if not isinstance(block, dict):
        return out
    for mk, mv in block.items():
        if isinstance(mv, dict) and "mean" in mv:
            out[str(mk)] = float(mv["mean"])
    return out


def _normalize_metrics_payload(src: Dict[str, float]) -> Dict[str, float]:
    return {str(k).lower().replace("-", "_"): float(v) for k, v in src.items() if v == v and math.isfinite(float(v))}


_CLASS_FINAL_METRIC_KEYS: Tuple[Tuple[str, str], ...] = (
    ("Accuracy", "accuracy"),
    ("Precision", "precision"),
    ("Recall", "recall"),
    ("F1-score", "f1"),
    ("AUROC", "auroc"),
    ("AUPRC", "auprc"),
)
_REG_FINAL_METRIC_KEYS: Tuple[Tuple[str, str], ...] = (("MSE", "mse"), ("PCC", "pcc"))


def _final_metrics_flat_from_cv_block(block: Any, ml_task_type: str) -> Dict[str, float]:
    """Build Phase5/registry metric dict (lowercase keys) from one programmer CV block."""
    if not isinstance(block, dict):
        return {}
    out: Dict[str, float] = {}
    pairs = _REG_FINAL_METRIC_KEYS if str(ml_task_type).strip().lower() == "regression" else _CLASS_FINAL_METRIC_KEYS
    for src_k, dst_k in pairs:
        mv = block.get(src_k)
        if isinstance(mv, dict) and mv.get("mean") is not None:
            try:
                val = float(mv["mean"])
                if math.isfinite(val):
                    out[dst_k] = val
            except (TypeError, ValueError):
                continue
    return out


def _best_score_fallback_flat(meta: Dict[str, Any], ml_task_type: str, objective_metric: str) -> Dict[str, float]:
    """When full CV-with-best-params fails; align keys with RandomizedSearchCV scoring."""
    bs = meta.get("best_score")
    if bs is None:
        return {}
    try:
        bsf = float(bs)
    except (TypeError, ValueError):
        return {}
    if not math.isfinite(bsf):
        return {}
    ml = str(ml_task_type or "").strip().lower()
    if ml == "regression":
        return {"mse": float(-bsf)}
    if ml == "multiclass":
        return {"f1": bsf}
    return {"auroc": bsf}


def _derive_final_model_metrics_bundle(
    sm: StateMachine,
    programmer_model: str,
    ml_task_type: str,
    objective_metric: str,
    enable_search_requested: bool,
) -> Tuple[Dict[str, float], str]:
    """
    Final release metrics for the selected algorithm — never copied from multi-model default CV
    when hyperparameter search produced usable best_params (scheme B).
    """
    meta = sm.ctx.train_metadata if isinstance(sm.ctx.train_metadata, dict) else {}
    candidate = sm.ctx.cv_results if isinstance(sm.ctx.cv_results, dict) else {}
    cand_block = candidate.get(programmer_model)
    best_params = meta.get("best_params")
    if not isinstance(best_params, dict):
        best_params = {}

    if enable_search_requested:
        if best_params:
            try:
                features = list(sm.ctx.final_features or [])
                if features and sm.ctx.clean_df is not None:
                    X = sm.ctx.clean_df[features].copy()
                    y = sm.ctx.clean_df[sm.ctx.target_col]
                    final_block = sm.programmer.run_cv_single_model_with_best_params(
                        features, X, y, programmer_model, best_params
                    )
                    flat = _final_metrics_flat_from_cv_block(final_block, ml_task_type)
                    if flat:
                        return _normalize_metrics_payload(flat), "selected_model_cv_with_best_params"
            except Exception:
                logger.exception(
                    "final_model_metrics: CV with best_params failed "
                    "(job will fall back to best_score-only if possible)",
                )
            fb = _best_score_fallback_flat(meta, ml_task_type, objective_metric)
            if fb:
                return _normalize_metrics_payload(fb), "selected_model_search_best_score_only"
            return {}, "selected_model_search_best_score_only"

        # Search was requested but no recorded best_params — never use multi-model default CV here.
        fb = _best_score_fallback_flat(meta, ml_task_type, objective_metric)
        if fb:
            return _normalize_metrics_payload(fb), "selected_model_search_best_score_only"
        return {}, "selected_model_search_best_score_only"

    flat = _final_metrics_flat_from_cv_block(cand_block, ml_task_type)
    return _normalize_metrics_payload(flat), "selected_model_cv_default"


def _normalize_cv_metric_key(mk: str) -> str:
    return str(mk).lower().replace("-", "_")


def _all_model_metrics_from_cv_results(cv_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten programmer CV blocks into API/frontend rows (means + optional std + fold_metrics)."""
    rows: List[Dict[str, Any]] = []
    if not isinstance(cv_results, dict):
        return rows
    for model_name, block in cv_results.items():
        if not isinstance(block, dict):
            continue
        row: Dict[str, Any] = {"model": str(model_name)}
        has_metric = False
        n_folds = 0
        for mk, mv in block.items():
            if isinstance(mv, dict) and isinstance(mv.get("folds"), list):
                n_folds = max(n_folds, len(mv["folds"]))
        fold_metric_rows: List[Dict[str, Any]] = []
        for fi in range(n_folds):
            fd: Dict[str, Any] = {"fold": fi + 1}
            for mk, mv in block.items():
                if not isinstance(mv, dict):
                    continue
                folds = mv.get("folds")
                key = _normalize_cv_metric_key(str(mk))
                if isinstance(folds, list) and fi < len(folds):
                    try:
                        fd[key] = float(folds[fi])
                    except (TypeError, ValueError):
                        fd[key] = folds[fi]
            fold_metric_rows.append(fd)
        for mk, mv in block.items():
            if not isinstance(mv, dict) or "mean" not in mv:
                continue
            try:
                mean_v = mv.get("mean")
                if mean_v is None:
                    continue
                key = _normalize_cv_metric_key(str(mk))
                row[key] = float(mean_v)
                std_v = mv.get("std")
                if std_v is not None:
                    row[f"{key}_std"] = float(std_v)
                has_metric = True
            except (TypeError, ValueError):
                continue
        if fold_metric_rows:
            row["fold_metrics"] = fold_metric_rows
        if has_metric:
            rows.append(row)
    return rows


def _attach_training_display_fields(params: Dict[str, Any], result_summary: Dict[str, Any]) -> None:
    """Human-facing labels for UI (no raw ids required on the client)."""
    did = str(params.get("dataset_id", "")).strip()
    if did:
        try:
            dm = dataset_repo.get(did)
        except Exception:  # noqa: BLE001
            dm = None
        if isinstance(dm, dict):
            name = str(dm.get("name") or "").strip()
            if name:
                result_summary["dataset_display_name"] = name
    ml_tt = str(params.get("ml_task_type", "")).strip()
    if ml_tt:
        result_summary["ml_task_type"] = ml_tt
    mname = str(params.get("model_name", "")).strip()
    if mname:
        result_summary["training_task_display_name"] = mname


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _pipeline_dir(job_id: str) -> Path:
    return task_repo.task_dir(job_id) / "pipeline"


def _try_export_shap_figure_job(job_id: str, sm: StateMachine, feat_cols: List[str], target: str) -> None:
    art_dir = task_repo.artifacts_dir(job_id)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        X = sm.ctx.clean_df[feat_cols]
        y = sm.ctx.clean_df[target]
        models = get_models_for_task(sm.ctx.task_type, y)
        for mn in models:
            task_repo.append_log(job_id, f"SHAP export started: {mn}")
            if mn not in TREE_MODELS:
                task_repo.append_log(job_id, f"SHAP skipped non-tree model: {mn}")
                continue
            max_disp = min(min(12, len(feat_cols)), 15)
            fig, bee_reason = sm.programmer.compute_shap_beeswarm_with_reason(X, y, mn, max_display=max_disp)
            if fig is not None:
                out = art_dir / f"shap_beeswarm_{mn}.png"
                fig.savefig(out, dpi=120, bbox_inches="tight")
                plt.close(fig)
                task_repo.append_log(job_id, f"Wrote SHAP beeswarm (feature screening): {out.name}")
            else:
                task_repo.append_log(job_id, f"SHAP beeswarm skipped: {mn}; reason={bee_reason}")
            fig_bar, bar_reason = sm.programmer.compute_shap_bar_with_reason(X, y, mn, max_display=max_disp)
            if fig_bar is not None:
                out_bar = art_dir / f"shap_bar_{mn}.png"
                fig_bar.savefig(out_bar, dpi=120, bbox_inches="tight")
                plt.close(fig_bar)
                task_repo.append_log(job_id, f"Wrote SHAP bar summary (feature screening): {out_bar.name}")
            else:
                task_repo.append_log(job_id, f"SHAP bar skipped: {mn}; reason={bar_reason}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("SHAP figure export skipped: %s", exc)


def _try_export_shap_for_final_programmer_model(
    job_id: str,
    sm: StateMachine,
    programmer_model: str,
    feat_cols: List[str],
    target: str,
) -> None:
    """SHAP beeswarm for the selected final tree model (final feature columns). Separate from Phase2 screening figures."""
    if programmer_model not in TREE_MODELS:
        task_repo.append_log(
            job_id,
            f"Final-model SHAP skipped: {programmer_model!r} is not in TREE_MODELS.",
        )
        return
    art_dir = task_repo.artifacts_dir(job_id)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        X = sm.ctx.clean_df[feat_cols]
        y = sm.ctx.clean_df[target]
        task_repo.append_log(job_id, f"SHAP export started (final model): {programmer_model}")
        max_disp = min(min(12, len(feat_cols)), 15)
        fig, bee_reason = sm.programmer.compute_shap_beeswarm_with_reason(X, y, programmer_model, max_display=max_disp)
        if fig is not None:
            out = art_dir / f"shap_beeswarm_{programmer_model}.png"
            fig.savefig(out, dpi=120, bbox_inches="tight")
            plt.close(fig)
            task_repo.append_log(job_id, f"Wrote final-model SHAP beeswarm: {out.name}")
        else:
            task_repo.append_log(job_id, f"SHAP beeswarm skipped (final model): {programmer_model}; reason={bee_reason}")
        fig_bar, bar_reason = sm.programmer.compute_shap_bar_with_reason(X, y, programmer_model, max_display=max_disp)
        if fig_bar is not None:
            out_bar = art_dir / f"shap_bar_{programmer_model}.png"
            fig_bar.savefig(out_bar, dpi=120, bbox_inches="tight")
            plt.close(fig_bar)
            task_repo.append_log(job_id, f"Wrote final-model SHAP bar summary: {out_bar.name}")
        else:
            task_repo.append_log(job_id, f"SHAP bar skipped (final model): {programmer_model}; reason={bar_reason}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Final-model SHAP export skipped: %s", exc)


def _copy_pipeline_reports_to_task(run_dir: Path, art_dir: Path) -> None:
    art_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "report.pdf",
        "data_quality_report.json",
        "leakage_report.json",
        "importance_ranking.json",
        "candidate_sets.json",
        "cv_results.json",
        "final_features.json",
        "doctor_history.json",
        "config.yaml",
    ):
        p = run_dir / name
        if p.is_file():
            shutil.copy2(p, art_dir / name)
    for png in run_dir.glob("*.png"):
        shutil.copy2(png, art_dir / png.name)


def _sm_load(job_id: str, phase_file: str) -> Tuple[StateMachine, Path]:
    run_dir = _pipeline_dir(job_id)
    state_path = run_dir / "state" / f"{phase_file}_context.json"
    task_repo.append_log(
        job_id,
        "[workflow-state-restore] "
        + json.dumps(
            {
                "job_id": job_id,
                "expected_restore_phase": phase_file,
                "restore_path": str(state_path),
                "file_exists": bool(state_path.exists()),
            },
            ensure_ascii=False,
        ),
    )
    sm = StateMachine.load_state(run_dir, phase=phase_file)
    if not sm:
        task_repo.append_log(
            job_id,
            "[workflow-state-restore] "
            + json.dumps(
                {
                    "job_id": job_id,
                    "expected_restore_phase": phase_file,
                    "restore_path": str(state_path),
                    "file_exists": bool(state_path.exists()),
                    "actual_error": "load_state returned None",
                },
                ensure_ascii=False,
            ),
        )
        raise ValueError("Workflow state restore failed; check task details for logs")
    return sm, run_dir


def _prepare_sm_phase1_2(
    job_id: str, params: Dict[str, Any]
) -> Tuple[StateMachine, ResolvedFeaturePlan, pd.DataFrame, List[str], str, str]:
    target = str(params.get("target_column", "")).strip()
    dataset_id = str(params.get("dataset_id", "")).strip()
    ml_task_type = str(params.get("ml_task_type", "binary"))

    if bool(params.get("enable_feature_set_search")):
        min_f = int(params.get("min_features", 1))
        max_f = int(params.get("max_features", 10))
        if min_f > max_f:
            raise ValueError("min_features cannot be greater than max_features")

    ds = dataset_repo.get(dataset_id)
    if not ds:
        raise ValueError(f"Dataset not found: {dataset_id}")
    df_raw = _load_dataframe(ds)
    if target not in df_raw.columns:
        raise ValueError(f"Target column is not present in the dataset: {target!r}")

    plan = resolve_feature_strategy(params, list(df_raw.columns), target)

    run_dir = _pipeline_dir(job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    sm = StateMachine(run_dir=run_dir)

    med = [str(x).strip() for x in (params.get("med_cols") or []) if str(x).strip()]
    sm.configure(
        task_type=ml_task_type,
        target_col=target,
        med_cols=med,
        selected_features=plan.candidate_pool_columns,
        enable_feature_set_search=bool(params.get("enable_feature_set_search"))
        and plan.strategy
        not in (FeatureStrategy.FINAL_FEATURES_DIRECT, FeatureStrategy.SELECTED_DIRECT),
        min_features=int(params.get("min_features", 1)),
        max_features=int(params.get("max_features", 10)),
        enable_search=bool(params.get("enable_search")),
        use_cv_shap=bool(params.get("use_cv_shap")),
        index_time=params.get("index_time") or None,
        label_time=params.get("label_time") or None,
    )

    return sm, plan, df_raw, med, target, ml_task_type


def _wf_run_phase2(job_id: str, params: Dict[str, Any]) -> None:
    task_repo.update(
        job_id,
        status="running",
        started_at=now_iso(),
        progress=5,
        current_stage="train_phase2_feature_search_running",
        message="Feature screening (StateMachine Phase 2)",
    )
    task_repo.append_log(job_id, "Starting Phase 2: data audit and feature analysis.")

    sm, plan, df_raw, med, target, ml_task_type = _prepare_sm_phase1_2(job_id, params)

    task_repo.update(job_id, progress=12, current_stage="train_phase2_feature_search_running", message="Phase 1 data audit")
    sm.run_phase1(df_raw)

    if plan.strategy == FeatureStrategy.FINAL_FEATURES_DIRECT:
        raise ValueError(
            "This is a multi-stage workflow: final_features must not be locked in Phase 1; remove final_features and retry."
        )

    feat_cols = plan.candidate_pool_columns
    X = sm.ctx.clean_df[feat_cols]
    y = sm.ctx.clean_df[target]

    use_search = bool(params.get("enable_feature_set_search")) and plan.strategy in (
        FeatureStrategy.SELECTED_WITH_SEARCH,
        FeatureStrategy.DEFAULT_POOL_SEARCH,
    )
    sm.ctx.enable_feature_set_search = use_search

    task_repo.update(job_id, progress=30, current_stage="train_phase2_feature_search_running", message="Phase 2 feature analysis / search")
    sm.run_phase2(X, y, on_progress=None)
    phase2_state_path = _pipeline_dir(job_id) / "state" / "phase2_context.json"
    if not phase2_state_path.exists():
        # Retry state persistence once to avoid Phase 3 restore failures from transient I/O issues.
        sm._save_state("phase2")
    if not phase2_state_path.exists():
        task_repo.append_log(
            job_id,
            "[workflow-state-restore] "
            + json.dumps(
                {
                    "job_id": job_id,
                    "current_phase": "phase2",
                    "transition_from": "phase2_running",
                    "transition_to": "phase3_pending",
                    "expected_restore_phase_next": "phase2",
                    "restore_path": str(phase2_state_path),
                    "file_exists": False,
                    "actual_error": "phase2 state file missing after phase2 run",
                },
                ensure_ascii=False,
            ),
        )
        raise ValueError("Workflow state write failed; retry the training task")

    ranking_objective = _default_ranking_objective(ml_task_type)
    suggested: List[str] = []
    filter_summary = ""
    if use_search:
        best = _pick_best_recommended(sm, ranking_objective, ml_task_type)
        if not best:
            raise ValueError(
                "Feature search did not produce a usable recommended subset; adjust the candidate pool, min/max features, or disable enable_feature_set_search."
            )
        suggested = list(best)
        filter_summary = (
            f"Subset search is enabled; recommended columns were selected by the default ranking metric {ranking_objective!r} and can be overridden in Phase 3."
        )
    else:
        suggested = list(feat_cols)
        filter_summary = "Subset search is disabled; recommended modeling columns are the current candidate pool, including forced-inclusion semantics, and can be edited in Phase 3."

    merged_suggested: List[str] = []
    for c in suggested:
        if c not in merged_suggested:
            merged_suggested.append(c)
    for c in med:
        if c in sm.ctx.clean_df.columns and c not in merged_suggested:
            merged_suggested.append(c)

    _try_export_shap_figure_job(job_id, sm, feat_cols, target)

    _write_json(
        task_repo.artifacts_dir(job_id) / "phase2_feature_summary.json",
        {
            "candidate_pool_columns": feat_cols,
            "med_cols": med,
            "enable_feature_set_search_executed": use_search,
            "suggested_final_features": merged_suggested,
            "recommended_core": suggested,
            "ranking_objective_default": ranking_objective,
            "filter_summary": filter_summary,
        },
    )

    artifact_urls = task_repo.list_artifacts(job_id)
    result_summary: Dict[str, Any] = {
        "headline": "Feature screening completed",
        "train_workflow_phase": PHASE3_PENDING,
        "task_kind": "train_model",
        "candidate_pool_columns": feat_cols,
        "med_cols": med,
        "recommended_features": suggested,
        "suggested_final_features": merged_suggested,
        "feature_set_search_executed": use_search,
        "ranking_objective_used_for_suggestion": ranking_objective,
        "filter_summary": filter_summary,
        "artifacts": {
            "phase2_summary": artifact_urls.get("phase2_feature_summary.json"),
        },
        "next_action": "Confirm final_features below the chat area (Phase 3).",
    }

    new_params = dict(params)
    new_params["train_workflow_step"] = None

    task_repo.update(
        job_id,
        status="waiting_user",
        progress=40,
        current_stage=PHASE3_PENDING,
        message="Waiting for final modeling feature confirmation (Phase 3)",
        params=new_params,
        result_summary=result_summary,
        artifacts=artifact_urls,
    )
    task_repo.append_log(
        job_id,
        f"Phase 2 completed. Recommended {len(suggested)} core features; {len(merged_suggested)} features are recommended after merging forced-inclusion columns.",
    )


def _wf_run_phase3(job_id: str, params: Dict[str, Any]) -> None:
    finals = [str(x).strip() for x in (params.get("final_features") or []) if str(x).strip()]
    if not finals:
        raise ValueError("Phase 3 requires non-empty final_features")

    task_repo.update(
        job_id,
        status="running",
        progress=42,
        current_stage="train_phase3_apply_final_features",
        message="Writing final features and estimating CV (Phase 3)",
    )
    task_repo.append_log(
        job_id,
        "[workflow-state-restore] "
        + json.dumps(
            {
                "job_id": job_id,
                "current_phase": "phase3",
                "transition_from": "phase3_confirm",
                "transition_to": "phase4_pending",
                "expected_restore_phase": "phase2",
            },
            ensure_ascii=False,
        ),
    )
    sm, run_dir = _sm_load(job_id, "phase2")
    sm.run_phase3(finals, force_med_cols=True)
    sm.compute_cv_for_phase4()
    phase3_state_path = run_dir / "state" / "phase3_context.json"
    if not phase3_state_path.exists():
        sm._save_state("phase3")
    if not phase3_state_path.exists():
        task_repo.append_log(
            job_id,
            "[workflow-state-restore] "
            + json.dumps(
                {
                    "job_id": job_id,
                    "current_phase": "phase3",
                    "expected_restore_phase_next": "phase3",
                    "restore_path": str(phase3_state_path),
                    "file_exists": False,
                    "actual_error": "phase3 state file missing after phase3 run",
                },
                ensure_ascii=False,
            ),
        )
        raise ValueError("Workflow state write failed; check task details for logs")

    new_params = dict(params)
    new_params["train_workflow_step"] = None

    ml_task_type = str(params.get("ml_task_type", "binary"))
    objective_metric = str(params.get("objective_metric") or "").strip() or _default_ranking_objective(ml_task_type)
    all_model_rows = _all_model_metrics_from_cv_results(sm.ctx.cv_results or {})
    art_dir = task_repo.artifacts_dir(job_id)
    art_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        art_dir / "all_model_metrics.json",
        {
            "task_type": "regression" if ml_task_type == "regression" else "classification",
            "objective_metric": objective_metric,
            "final_model": "",
            "rows": all_model_rows,
        },
    )

    result_summary = dict(task_repo.get(job_id).get("result_summary") or {})
    result_summary.update(
        {
            "headline": "Final features locked",
            "train_workflow_phase": PHASE4_PENDING,
            "final_features_locked": list(sm.ctx.final_features),
            "next_action": "Confirm the model and objective_metric below the chat area (Phase 4).",
            "all_model_metrics_rows": all_model_rows,
        }
    )
    _attach_training_display_fields(new_params, result_summary)

    task_repo.update(
        job_id,
        status="waiting_user",
        progress=55,
        current_stage=PHASE4_PENDING,
        message="Waiting for training configuration (model / metric)",
        params=new_params,
        result_summary=result_summary,
        artifacts=task_repo.list_artifacts(job_id),
    )
    task_repo.append_log(job_id, f"Phase 3 completed; modeling feature count={len(sm.ctx.final_features)}.")


def _wf_run_phase4_and_report(job_id: str, params: Dict[str, Any]) -> None:
    ml_task_type = str(params.get("ml_task_type", "binary"))
    objective_metric = str(params.get("objective_metric", _default_ranking_objective(ml_task_type)))
    ok_om, om_err = validate_objective_supported(objective_metric, ml_task_type)
    if not ok_om:
        raise ValueError(om_err)

    task_repo.append_log(
        job_id,
        "[workflow-state-restore] "
        + json.dumps(
            {
                "job_id": job_id,
                "current_phase": "phase4",
                "transition_from": "phase4_confirm",
                "transition_to": "phase5_pending",
                "expected_restore_phase": "phase3",
            },
            ensure_ascii=False,
        ),
    )
    sm, run_dir = _sm_load(job_id, "phase3")
    y_clean = sm.ctx.clean_df[sm.ctx.target_col]
    programmer_model = resolve_programmer_model_for_final_training(params, ml_task_type, y_clean)
    # ---- preflight: split validity for classification ----
    if ml_task_type != "regression":
        y_series = pd.Series(y_clean).reset_index(drop=True)
        X_pre = sm.ctx.clean_df[sm.ctx.final_features].reset_index(drop=True)
        cls_counts = y_series.value_counts().to_dict()
        task_repo.append_log(
            job_id,
            "[training-split-check] "
            + json.dumps(
                {
                    "job_id": job_id,
                    "stage": "phase4_preflight",
                    "ml_task_type": ml_task_type,
                    "total_samples": int(len(y_series)),
                    "total_label_dist": {str(k): int(v) for k, v in cls_counts.items()},
                },
                ensure_ascii=False,
            ),
        )
        n_classes = len(cls_counts)
        if n_classes < 2:
            raise ValueError("The current data contains only one class, so classification training cannot run. Check the label distribution.")
        min_class = min(int(v) for v in cls_counts.values())
        if min_class < 2:
            raise ValueError("The smallest class has fewer than 2 samples, so stratified splitting cannot run. Add data or adjust labels.")
        cv_folds = min(5, min_class)
        if cv_folds < 5:
            task_repo.append_log(job_id, f"[training-split-check] Automatically reduced folds: 5 -> {cv_folds} (smallest class size={min_class})")
        try:
            _, _, y_tr_tmp, y_val_tmp = train_test_split(
                X_pre,
                y_series,
                test_size=0.2,
                random_state=42,
                stratify=y_series,
            )
            task_repo.append_log(
                job_id,
                "[training-split-check] "
                + json.dumps(
                    {
                        "job_id": job_id,
                        "stage": "phase4_preflight",
                        "ml_task_type": ml_task_type,
                        "total_label_dist": {str(k): int(v) for k, v in cls_counts.items()},
                        "holdout_train_dist": {str(k): int(v) for k, v in pd.Series(y_tr_tmp).value_counts().to_dict().items()},
                        "holdout_valid_dist": {str(k): int(v) for k, v in pd.Series(y_val_tmp).value_counts().to_dict().items()},
                        "cv_folds": cv_folds,
                    },
                    ensure_ascii=False,
                ),
            )
            skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            fold_stats = []
            for i, (tr_idx, va_idx) in enumerate(skf.split(X_pre, y_series), start=1):
                ytr = y_series.iloc[tr_idx]
                yva = y_series.iloc[va_idx]
                fold_stats.append(
                    {
                        "fold": i,
                        "train_dist": {str(k): int(v) for k, v in ytr.value_counts().to_dict().items()},
                        "valid_dist": {str(k): int(v) for k, v in yva.value_counts().to_dict().items()},
                    }
                )
            task_repo.append_log(job_id, "[training-split-check] " + json.dumps({"job_id": job_id, "cv_fold_dist": fold_stats}, ensure_ascii=False))
            sm.programmer.cv_folds = cv_folds
        except ValueError as exc:
            raise ValueError(f"The current split cannot satisfy classification training requirements. Adjust folds/validation strategy or check label distribution. Details: {exc}") from exc

    task_repo.update(
        job_id,
        status="running",
        progress=60,
        current_stage="train_phase4_training_running",
        message=f"Training final model: {programmer_model}",
    )
    n_samples = int(len(y_clean))
    n_pos = int((y_clean == 1).sum()) if ml_task_type != "regression" else None
    n_neg = int((y_clean == 0).sum()) if ml_task_type != "regression" else None
    base_score = None
    if ml_task_type == "binary":
        try:
            import numpy as np

            bs = float(pd.Series(y_clean).mean())
            base_score = float(np.clip(bs, 1e-6, 1 - 1e-6))
        except Exception:
            base_score = 0.5
    task_repo.append_log(
        job_id,
        "[training-finalize] "
        + json.dumps(
            {
                "job_id": job_id,
                "model_type": str(params.get("model_type", "xgboost")),
                "ml_task_type": ml_task_type,
                "target_column": sm.ctx.target_col,
                "objective": "binary:logistic"
                if ml_task_type == "binary" and str(params.get("model_type", "xgboost")).strip().lower() == "xgboost"
                else "auto",
                "eval_metric": "logloss"
                if ml_task_type == "binary" and str(params.get("model_type", "xgboost")).strip().lower() == "xgboost"
                else objective_metric,
                "base_score": base_score,
                "label_summary": {"n": n_samples, "pos": n_pos, "neg": n_neg},
            },
            ensure_ascii=False,
        ),
    )
    models_dict = get_models_for_task(ml_task_type, y_clean)
    if programmer_model not in models_dict:
        raise ValueError(
            "Training could not start because the selected algorithm is not available in this environment "
            f"(ml_task_type={ml_task_type}). "
            f"Please choose one of: {', '.join(models_dict.keys())}."
        )

    sm.programmer.task_type = ml_task_type
    sm.ctx.enable_search = bool(params.get("enable_search"))
    sm.programmer.enable_search = sm.ctx.enable_search
    task_repo.append_log(
        job_id,
        "[training-finalize] "
        + json.dumps(
            {
                "job_id": job_id,
                "final_training_params": {
                    "model_type": str(params.get("model_type", "xgboost")),
                    "programmer_model": programmer_model,
                    "ml_task_type": ml_task_type,
                    "objective_metric": objective_metric,
                    "enable_search": bool(params.get("enable_search")),
                    "final_feature_count": len(sm.ctx.final_features or []),
                },
            },
            ensure_ascii=False,
        ),
    )
    sm.run_phase4(programmer_model)

    art_dir = task_repo.artifacts_dir(job_id)
    model_path = art_dir / "model.joblib"
    joblib.dump(sm.ctx.trained_pipeline, model_path)
    task_repo.append_log(job_id, f"Saved model artifact: {model_path.name}")

    final_feats = list(sm.ctx.final_features or [])
    if final_feats and sm.ctx.target_col:
        _try_export_shap_for_final_programmer_model(
            job_id,
            sm,
            programmer_model,
            final_feats,
            str(sm.ctx.target_col),
        )

    all_model_rows = _all_model_metrics_from_cv_results(sm.ctx.cv_results or {})
    enable_search_requested = bool(params.get("enable_search"))
    metrics_payload, metrics_protocol = _derive_final_model_metrics_bundle(
        sm,
        programmer_model,
        ml_task_type,
        objective_metric,
        enable_search_requested,
    )
    if not metrics_payload:
        meta_fb = sm.ctx.train_metadata if isinstance(sm.ctx.train_metadata, dict) else {}
        fb = _best_score_fallback_flat(meta_fb, ml_task_type, objective_metric)
        if fb:
            metrics_payload = _normalize_metrics_payload(fb)
            metrics_protocol = "selected_model_search_best_score_only"
    final_model_metrics = dict(metrics_payload)
    _write_json(art_dir / "metrics.json", metrics_payload)
    _write_json(
        art_dir / "all_model_metrics.json",
        {
            "task_type": "regression" if ml_task_type == "regression" else "classification",
            "objective_metric": objective_metric,
            "final_model": programmer_model,
            "rows": all_model_rows,
        },
    )

    final_cols = list(sm.ctx.final_features)
    summary = {
        "job_id": job_id,
        "final_feature_columns": final_cols,
        "programmer_model": programmer_model,
        "objective_metric": objective_metric,
    }
    _write_json(art_dir / "summary.json", summary)

    task_repo.update(job_id, progress=85, current_stage="train_phase4_training_running", message="Generating report and artifacts (Phase 5 report core)")
    sm.run_phase5(registry=None)
    _copy_pipeline_reports_to_task(run_dir, art_dir)

    report_pdf_path = run_dir / "report.pdf"
    report_pdf_ok = report_pdf_path.is_file() and report_pdf_path.stat().st_size > 64

    po = params.get("publish_overrides") if isinstance(params.get("publish_overrides"), dict) else {}
    explicit_mid = po.get("model_id") if isinstance(po, dict) else None
    if explicit_mid and str(explicit_mid).strip():
        draft_model_id = str(explicit_mid).strip()
    else:
        mn = params.get("model_name")
        if mn and str(mn).strip():
            raw = str(mn).strip()[:48]
            safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in raw)
            draft_model_id = f"{safe}_{job_id[-8:]}"
        else:
            draft_model_id = f"trained_{job_id}"

    new_params = dict(params)
    new_params["train_workflow_step"] = None

    artifact_urls = task_repo.list_artifacts(job_id)
    result_summary = dict(task_repo.get(job_id).get("result_summary") or {})
    result_summary.update(
        {
            "headline": (
                "Model training completed and the training report was generated"
                if report_pdf_ok
                else "Model training completed; the PDF report was not generated, but metrics and JSON artifacts remain available"
            ),
            "train_workflow_phase": PHASE5_PENDING,
            "task_kind": "train_model",
            "model_id_draft": draft_model_id,
            "final_model_metrics": final_model_metrics,
            "key_metrics": metrics_payload,
            "metrics_protocol": metrics_protocol,
            "enable_search_applied": enable_search_requested,
            "all_model_metrics_rows": all_model_rows,
            "programmer_model": programmer_model,
            "primary_metric_requested": objective_metric,
            "final_feature_count": len(final_cols),
            "final_feature_preview": final_cols[:40],
            "next_action": "Use the card below to confirm whether to release the model to the model registry.",
            "training_core_status": "completed",
            "report_generation_status": "ok" if report_pdf_ok else "failed",
            "report_generation_error": None if report_pdf_ok else "Training report PDF generation failed or was not written; review task logs and JSON artifacts.",
        }
    )
    _attach_training_display_fields(new_params, result_summary)

    task_repo.update(
        job_id,
        status="waiting_user",
        progress=92,
        current_stage=PHASE5_PENDING,
        message="Waiting for release confirmation" if report_pdf_ok else "Training completed; report PDF was not generated, but the model can still be released",
        params=new_params,
        result_summary=result_summary,
        artifacts=artifact_urls,
    )
    task_repo.append_log(
        job_id,
        "Phase 4 and artifacts are complete; waiting for release confirmation."
        if report_pdf_ok
        else "Phase 4 and model artifacts are complete; the PDF report was not generated. Waiting for release confirmation; JSON and metrics are available.",
    )


def _wf_run_phase5_publish(job_id: str, params: Dict[str, Any]) -> None:
    task = task_repo.get(job_id)
    if not task:
        raise ValueError("Task not found")

    task_repo.update(
        job_id,
        status="running",
        progress=95,
        current_stage="train_phase5_publish_running",
        message="Writing model registry entry if release is selected",
    )

    do_publish = bool(params.get("do_publish", True))
    dataset_id = str(params.get("dataset_id", "")).strip()
    target = str(params.get("target_column", "")).strip()
    ml_task_type = str(params.get("ml_task_type", "binary"))
    objective_metric = str(params.get("objective_metric", ""))

    rs = task.get("result_summary") or {}
    final_cols = list(rs.get("final_features_locked") or [])
    if not final_cols:
        final_cols = [str(x) for x in (params.get("final_features") or []) if str(x).strip()]

    metrics_path = task_repo.artifacts_dir(job_id) / "metrics.json"
    metrics_payload: Dict[str, Any] = {}
    if metrics_path.exists():
        metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))

    metrics_protocol_rs = str(rs.get("metrics_protocol") or "").strip() or "unknown"
    _esa = rs.get("enable_search_applied")
    enable_applied_rs = bool(_esa) if _esa is not None else bool(params.get("enable_search"))

    programmer_model = str(rs.get("programmer_model") or params.get("model_type") or "xgboost")
    model_id = str(rs.get("model_id_draft") or f"trained_{job_id}")

    po = params.get("publish_overrides") if isinstance(params.get("publish_overrides"), dict) else {}
    explicit_mid = po.get("model_id") if isinstance(po, dict) else None
    if explicit_mid and str(explicit_mid).strip():
        model_id = str(explicit_mid).strip()

    artifact_urls = task_repo.list_artifacts(job_id)
    metrics_url = artifact_urls.get("metrics.json") or f"{STATIC_BASE_URL}/{job_id}/artifacts/metrics.json"

    finished_at = now_iso()
    base_task_params = task.get("params") if isinstance(task.get("params"), dict) else {}
    clinical_task_id_resolved = (
        params.get("clinical_task_id")
        or rs.get("clinical_task_id")
        or base_task_params.get("clinical_task_id")
    )
    if clinical_task_id_resolved is not None:
        clinical_task_id_resolved = str(clinical_task_id_resolved).strip() or None

    if do_publish:
        labels = _registry_publish_labels(params, po, clinical_task_id_resolved, model_id)
        model_repo.upsert(
            {
                "model_id": model_id,
                **labels,
                "task_type": ml_task_type,
                "model_type": params.get("model_type"),
                "model_path": f"{STATIC_BASE_URL}/{job_id}/artifacts/model.joblib",
                "version": "1.0",
                "required_features": final_cols,
                "feature_order": final_cols,
                "source_job_id": job_id,
                "dataset_id": dataset_id,
                "clinical_task_id": clinical_task_id_resolved,
                "ml_task_type": ml_task_type,
                "target_column": target,
                "objective_metric": objective_metric,
                "feature_set": params.get("feature_set"),
                "selected_features": params.get("selected_features")
                if isinstance(params.get("selected_features"), list)
                else [],
                "final_features": final_cols,
                "is_published": True,
                "published_at": finished_at,
                "created_at": finished_at,
                "key_metrics": metrics_payload,
                "notes": (po.get("notes") if isinstance(po, dict) else None),
                "metadata": {
                    "training_job_id": job_id,
                    "registered_from": "train_model",
                    "clinical_task_id": clinical_task_id_resolved,
                    "enable_search_applied": enable_applied_rs,
                    "metrics_protocol": metrics_protocol_rs,
                    "objective_metric": objective_metric,
                    "model_type": str(params.get("model_type") or ""),
                },
            },
        )

    new_params = dict(params)
    new_params["train_workflow_step"] = PHASE5_DONE

    result_summary = dict(rs)
    result_summary.update(
        {
            "headline": "Training workflow completed" if do_publish else "Training workflow completed (model not released)",
            "train_workflow_phase": PHASE5_DONE,
            "task_kind": "train_model",
            "model_id": model_id if do_publish else None,
            "model_registered": do_publish,
            "key_metrics": metrics_payload,
            "final_model_metrics": metrics_payload,
            "trained_model_programmer_name": programmer_model,
            "primary_metric_requested": objective_metric,
            "final_feature_count": len(final_cols),
            "final_features_locked": final_cols,
            "ml_task_type": ml_task_type,
        }
    )
    _attach_training_display_fields(new_params, result_summary)

    task_repo.update(
        job_id,
        status="completed",
        progress=100,
        current_stage=PHASE5_DONE,
        message="Training workflow completed",
        completed_at=finished_at,
        params=new_params,
        result_summary=result_summary,
        artifacts=artifact_urls,
    )
    task_repo.append_log(
        job_id,
        f"Phase 5 completed: do_publish={do_publish}, model_id={model_id if do_publish else '-'}.",
    )


def run_domain_training_job(job_id: str, params: Dict[str, Any]) -> None:
    step = params.get("train_workflow_step") or STEP_PHASE2
    if step == STEP_PHASE2:
        _wf_run_phase2(job_id, params)
    elif step == STEP_PHASE3:
        _wf_run_phase3(job_id, params)
    elif step == STEP_PHASE4:
        _wf_run_phase4_and_report(job_id, params)
    elif step == STEP_PHASE5:
        _wf_run_phase5_publish(job_id, params)
    else:
        raise ValueError(f"Unknown train_workflow_step: {step!r}")


def resume_training_workflow(
    job_id: str,
    action: str,
    body: Dict[str, Any],
) -> Dict[str, Any]:
    """API entry point: validate the gate, merge params, and enqueue the worker again."""
    from backend.workers.task_executor import submit_job

    task = task_repo.get(job_id)
    if not task:
        return {"status": "error", "message": f"job_id={job_id} not found"}
    if task.get("job_type") != "train_model":
        return {"status": "error", "message": "Not a training task"}
    if task.get("status") != "waiting_user":
        return {"status": "error", "message": f"Task status is {task.get('status')}; it is not waiting for user input"}

    rs = task.get("result_summary") or {}
    phase = str(rs.get("train_workflow_phase") or "")

    params = dict(task.get("params") or {})

    if action == "confirm_final_features":
        if phase != PHASE3_PENDING:
            return {"status": "error", "message": f"Current phase is {phase}; final_features cannot be confirmed"}
        finals = body.get("final_features")
        if not isinstance(finals, list) or not finals:
            return {"status": "error", "message": "final_features must be a non-empty array"}
        params["final_features"] = [str(x).strip() for x in finals if str(x).strip()]
        params["train_workflow_step"] = STEP_PHASE3
    elif action == "confirm_train_config":
        if phase != PHASE4_PENDING:
            return {"status": "error", "message": f"Current phase is {phase}; training configuration cannot be confirmed"}
        for key in ("model_type", "objective_metric"):
            if body.get(key) is None or (isinstance(body.get(key), str) and not str(body.get(key)).strip()):
                return {"status": "error", "message": f"Missing {key}"}
        params["model_type"] = str(body.get("model_type")).strip()
        params["objective_metric"] = str(body.get("objective_metric")).strip()
        if body.get("model_name") is not None:
            params["model_name"] = normalize_training_payload({"model_name": body.get("model_name")}).get("model_name")
        if body.get("enable_search") is not None:
            params["enable_search"] = bool(body.get("enable_search"))
        params["train_workflow_step"] = STEP_PHASE4
    elif action == "confirm_publish":
        if phase != PHASE5_PENDING:
            return {"status": "error", "message": f"Current phase is {phase}; release cannot be confirmed"}
        if "do_publish" in body:
            params["do_publish"] = bool(body.get("do_publish"))
        po = body.get("publish_overrides")
        if isinstance(po, dict):
            params["publish_overrides"] = po
        params["train_workflow_step"] = STEP_PHASE5
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}

    task_repo.update(job_id, params=params)
    submit_job("train_model", job_id)
    return {"status": "success", "message": "Next stage submitted", "job_id": job_id}
