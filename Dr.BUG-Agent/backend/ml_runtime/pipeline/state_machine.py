"""State machine for clinical prediction pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from ..core.model_registry import ModelRegistry

import numpy as np
import pandas as pd

from ..agents.auditor import AuditorAgent
from ..agents.guardian import GuardianAgent
from ..agents.interpreter import InterpreterAgent
from ..agents.programmer import ProgrammerAgent
from ..agents.reporter import ReporterAgent
from ..core.model_publish import publish_from_pipeline_context
from ..utils.io import get_run_dir, RANDOM_STATE, save_artifact

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    """Pipeline phases."""
    INIT = "init"
    PHASE1_AUDIT = "phase1_audit"
    PHASE2_IMPORTANCE = "phase2_importance"
    PHASE2_FEATURE_SEARCH = "phase2_feature_search"
    PHASE3_NEGOTIATION = "phase3_negotiation"
    PHASE4_TRAIN = "phase4_train"
    PHASE5_REPORT = "phase5_report"
    DONE = "done"
    ERROR = "error"


@dataclass
class PipelineContext:
    """Shared context across pipeline phases."""

    # Input
    task_type: str = "binary"
    target_col: str = ""
    med_cols: List[str] = field(default_factory=list)
    selected_features: List[str] = field(default_factory=list)
    enable_feature_set_search: bool = False
    min_features: int = 1
    max_features: int = 10
    enable_search: bool = False
    use_cv_shap: bool = False  # If True, use 5-fold CV SHAP mean; if False, use single 80/20 split
    model_names: Optional[List[str]] = None
    index_time: Optional[str] = None
    label_time: Optional[str] = None
    sensitive_cols: Optional[List[str]] = None

    # Phase 1
    clean_df: Optional[pd.DataFrame] = None
    data_quality_report: Dict[str, Any] = field(default_factory=dict)
    leakage_report: Dict[str, Any] = field(default_factory=dict)

    # Phase 2
    importance_ranking: Dict[str, List[tuple]] = field(default_factory=dict)
    shap_data_cache: Dict[str, Tuple[np.ndarray, np.ndarray, List[str]]] = field(default_factory=dict)  # {model_name: (shap_matrix, Xt, feature_names)}
    feature_stability: Dict[str, Dict[str, float]] = field(default_factory=dict)  # {model_name: {feature: stability_score}} where stability_score is frequency of entering top 10
    candidate_sets: List[List[str]] = field(default_factory=list)
    recommended_sets: List[List[str]] = field(default_factory=list)
    recommended_sets_by_metric: Dict[str, List[str]] = field(default_factory=dict)
    cv_results: Dict[str, Any] = field(default_factory=dict)

    # Phase 3
    final_features: List[str] = field(default_factory=list)
    doctor_history: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 4
    trained_pipeline: Any = None
    train_metadata: Dict[str, Any] = field(default_factory=dict)

    # Phase 5
    run_dir: Optional[Path] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to JSON-serializable dict."""
        result = {}
        for key, value in asdict(self).items():
            if value is None:
                result[key] = None
            elif isinstance(value, pd.DataFrame):
                # Save DataFrame reference (will be saved separately)
                result[key] = f"__DATAFRAME__:{key}"
            elif isinstance(value, (np.ndarray, np.generic)):
                # Convert numpy arrays to lists
                result[key] = value.tolist() if hasattr(value, 'tolist') else value.item()
            elif isinstance(value, Path):
                result[key] = str(value)
            elif isinstance(value, dict):
                # Recursively handle dicts
                result[key] = self._serialize_dict(value)
            elif isinstance(value, list):
                # Recursively handle lists
                result[key] = self._serialize_list(value)
            elif isinstance(value, tuple):
                # Convert tuples to lists, handling numpy arrays inside
                result[key] = self._serialize_list(list(value))
            elif isinstance(value, (str, int, float, bool)):
                result[key] = value
            else:
                # Skip non-serializable objects (e.g., trained_pipeline)
                result[key] = None
                logger.debug(f"Skipping non-serializable field: {key} (type: {type(value)})")
        return result
    
    def _serialize_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively serialize dict values."""
        result = {}
        for k, v in d.items():
            if isinstance(v, pd.DataFrame):
                result[k] = f"__DATAFRAME__:{k}"
            elif isinstance(v, (np.ndarray, np.generic)):
                result[k] = v.tolist() if hasattr(v, 'tolist') else v.item()
            elif isinstance(v, dict):
                result[k] = self._serialize_dict(v)
            elif isinstance(v, list):
                result[k] = self._serialize_list(v)
            elif isinstance(v, tuple):
                result[k] = self._serialize_list(list(v))
            elif isinstance(v, (str, int, float, bool, type(None))):
                result[k] = v
            else:
                result[k] = None
        return result
    
    def _serialize_list(self, lst: List[Any]) -> List[Any]:
        """Recursively serialize list values."""
        result = []
        for item in lst:
            if isinstance(item, pd.DataFrame):
                result.append(f"__DATAFRAME__:list_item")
            elif isinstance(item, (np.ndarray, np.generic)):
                result.append(item.tolist() if hasattr(item, 'tolist') else item.item())
            elif isinstance(item, dict):
                result.append(self._serialize_dict(item))
            elif isinstance(item, list):
                result.append(self._serialize_list(item))
            elif isinstance(item, tuple):
                result.append(self._serialize_list(list(item)))
            elif isinstance(item, (str, int, float, bool, type(None))):
                result.append(item)
            else:
                result.append(None)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], run_dir: Optional[Path] = None) -> PipelineContext:
        """Reconstruct context from dict."""
        # Handle DataFrame references
        if run_dir:
            for key, value in data.items():
                if isinstance(value, str) and value.startswith("__DATAFRAME__:"):
                    df_path = run_dir / f"{key}.csv"
                    if df_path.exists():
                        data[key] = pd.read_csv(df_path)
                    else:
                        data[key] = None
        
        # Convert run_dir string back to Path
        if isinstance(data.get("run_dir"), str):
            data["run_dir"] = Path(data["run_dir"])
        
        # Reconstruct numpy arrays in shap_data_cache
        if "shap_data_cache" in data and isinstance(data["shap_data_cache"], dict):
            for model_name, cache_data in data["shap_data_cache"].items():
                if isinstance(cache_data, list) and len(cache_data) >= 2:
                    # Convert lists back to numpy arrays
                    data["shap_data_cache"][model_name] = (
                        np.array(cache_data[0]) if isinstance(cache_data[0], list) else cache_data[0],
                        np.array(cache_data[1]) if isinstance(cache_data[1], list) else cache_data[1],
                        cache_data[2] if len(cache_data) > 2 else []
                    )
        
        return cls(**data)


class StateMachine:
    """Orchestrates the 5-phase pipeline."""

    def __init__(self, run_dir: Optional[Path] = None):
        self.ctx = PipelineContext()
        self.run_dir = run_dir or get_run_dir()
        self.ctx.run_dir = self.run_dir

        self.auditor = AuditorAgent()
        self.programmer = ProgrammerAgent()
        self.guardian = GuardianAgent()
        self.interpreter = InterpreterAgent()
        self.reporter = ReporterAgent(self.run_dir)
    
    def _save_state(self, phase: str) -> None:
        """Save PipelineContext to JSON after each phase."""
        try:
            state_dir = self.run_dir / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            
            # Save DataFrames separately
            ctx_dict = self.ctx.to_dict()
            if self.ctx.clean_df is not None:
                clean_df_path = state_dir / "clean_df.csv"
                self.ctx.clean_df.to_csv(clean_df_path, index=False)
            
            # Save context JSON
            state_path = state_dir / f"{phase}_context.json"
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(ctx_dict, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"State saved after {phase} to {state_path}")
        except Exception as e:
            logger.warning(f"Failed to save state after {phase}: {e}")
    
    @classmethod
    def load_state(cls, run_dir: Path, phase: str = "phase3") -> Optional[StateMachine]:
        """Load StateMachine from saved state."""
        try:
            state_dir = run_dir / "state"
            state_path = state_dir / f"{phase}_context.json"
            
            if not state_path.exists():
                logger.warning(f"State file not found: {state_path}")
                return None
            
            with open(state_path, "r", encoding="utf-8") as f:
                ctx_dict = json.load(f)
            
            # Reconstruct context
            ctx = PipelineContext.from_dict(ctx_dict, run_dir=state_dir)
            
            # Create StateMachine with loaded context
            sm = cls(run_dir=run_dir)
            sm.ctx = ctx
            
            # Reinitialize agents with context values
            sm.auditor.index_time = ctx.index_time
            sm.auditor.label_time = ctx.label_time
            sm.auditor.sensitive_cols = ctx.sensitive_cols or []
            sm.programmer.task_type = ctx.task_type
            sm.programmer.enable_search = ctx.enable_search
            
            logger.info(f"State loaded from {state_path}")
            return sm
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def configure(self, **kwargs) -> None:
        """Update context from kwargs."""
        for k, v in kwargs.items():
            if hasattr(self.ctx, k):
                setattr(self.ctx, k, v)

    def run_phase1(self, df: pd.DataFrame) -> pd.DataFrame:
        """Phase 1: Data Audit."""
        self.auditor.index_time = self.ctx.index_time
        self.auditor.label_time = self.ctx.label_time
        self.auditor.sensitive_cols = self.ctx.sensitive_cols or []
        clean_df, report = self.auditor.run(df)
        self.ctx.clean_df = clean_df
        self.ctx.data_quality_report = report
        self.ctx.leakage_report = report.get("leakage", {})
        # Save state after Phase 1
        self._save_state("phase1")
        return clean_df

    def run_phase2(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Phase 2: Feature pre-study. Branch on enable_feature_set_search.
        on_progress(pct, message) with pct in [0, 1].
        """
        self.programmer.task_type = self.ctx.task_type
        self.programmer.enable_search = self.ctx.enable_search
        all_features = [c for c in X.columns if c != self.ctx.target_col]
        non_med = [f for f in all_features if f not in self.ctx.med_cols]
        features_for_importance = self.ctx.selected_features or all_features
        features_for_importance = [f for f in features_for_importance if f in X.columns]

        def _prog(pct, msg):
            if on_progress:
                on_progress(pct, msg)

        # ② Global importance (always) 0-40%
        def imp_cb(p, m):
            if on_progress:
                on_progress(p * 0.4, m)

        importance, shap_data_cache, stability = self.programmer.run_global_importance(
            X[features_for_importance], y, self.ctx.model_names, 
            on_progress=imp_cb, 
            return_shap_data=True,
            use_cv_shap=self.ctx.use_cv_shap
        )
        self.ctx.importance_ranking = importance
        self.ctx.shap_data_cache = shap_data_cache
        self.ctx.feature_stability = stability

        if not self.ctx.enable_feature_set_search:
            self.ctx.candidate_sets = []
            self.ctx.recommended_sets = []
            _prog(1.0, "Done")
            return {"importance_ranking": importance, "candidate_sets": [], "recommended_sets": []}

        # ③④⑤ Feature set generation (40-50%), screening (50-80%), recommendation (80-100%)
        if not non_med:
            self.ctx.candidate_sets = []
            self.ctx.recommended_sets = []
            _prog(1.0, "Done")
            return {"importance_ranking": importance, "candidate_sets": [], "recommended_sets": []}

        _prog(0.42, "Generating feature sets...")
        sets_by_model = self.programmer.run_feature_set_generation(
            importance,
            non_med,
            self.ctx.min_features,
            self.ctx.max_features,
        )

        def screen_cb(p, m):
            if on_progress:
                on_progress(0.5 + p * 0.3, m)

        candidates = self.programmer.run_candidate_screening(
            sets_by_model, X, y, top_n_sets=5, on_progress=screen_cb
        )

        def rec_cb(p, m):
            if on_progress:
                on_progress(0.8 + p * 0.2, m)

        recommended, by_metric = self.programmer.run_final_recommendation(
            candidates, X, y, importance, max_recommendations=6, on_progress=rec_cb
        )
        self.ctx.candidate_sets = candidates
        self.ctx.recommended_sets = recommended
        self.ctx.recommended_sets_by_metric = by_metric
        
        # Save state after Phase 2
        self._save_state("phase2")

        return {
            "importance_ranking": importance,
            "candidate_sets": candidates,
            "recommended_sets": recommended,
            "recommended_sets_by_metric": by_metric,
        }

    def run_phase3(
        self,
        selected_features: List[str],
        force_med_cols: bool = True,
    ) -> List[str]:
        """Phase 3: Human-AI negotiation. Doctor confirms final features."""
        avail = list(self.ctx.clean_df.columns) if self.ctx.clean_df is not None else []
        self.guardian.set_context(
            self.ctx.recommended_sets,
            self.ctx.importance_ranking,
            self.ctx.med_cols,
            available_columns=avail,
        )
        self.guardian.set_selection(selected_features, force_med_cols)
        ok, msg = self.guardian.validate()
        if not ok:
            raise ValueError(msg)
        self.ctx.final_features = self.guardian.get_final_features()
        # Get selection history (which now includes warnings)
        self.ctx.doctor_history = self.guardian.get_selection_history()
        self.interpreter.set_importance(self.ctx.importance_ranking)
        self.interpreter.set_feature_stability(self.ctx.feature_stability)
        # Set missing stats from Phase 1 report
        if self.ctx.data_quality_report.get("missing_stats"):
            missing_summary = {
                feat: stats.get("rate", 0.0) 
                for feat, stats in self.ctx.data_quality_report["missing_stats"].items()
            }
            self.interpreter.set_missing_stats(missing_summary)
        # Save state after Phase 3
        self._save_state("phase3")
        return self.ctx.final_features

    def compute_cv_for_phase4(self) -> None:
        """Compute CV for all models using final_features (called after Phase 3 confirm)."""
        features = self.ctx.final_features
        if not features:
            return
        X = self.ctx.clean_df[features].copy()
        y = self.ctx.clean_df[self.ctx.target_col]
        self.ctx.cv_results = self.programmer.run_cv_all_models(
            features, X, y, self.ctx.model_names
        )

    def run_phase4(
        self,
        model_name: str,
    ) -> tuple[Any, Dict[str, Any]]:
        """Phase 4: Train final model."""
        features = self.ctx.final_features
        if not features:
            raise ValueError("No final features; run Phase 3 first")
        X = self.ctx.clean_df[features].copy()
        y = self.ctx.clean_df[self.ctx.target_col]
        pipe, meta = self.programmer.train_final_model(
            features, X, y, model_name, use_search=self.ctx.enable_search
        )
        self.ctx.trained_pipeline = pipe
        self.ctx.train_metadata = meta
        self.ctx.cv_results = self.programmer.run_cv_all_models(
            features, X, y, self.ctx.model_names
        )
        # Save state after Phase 4
        self._save_state("phase4")
        return pipe, meta

    def run_phase5(
        self,
        registry: Optional["ModelRegistry"] = None,
        **publish_overrides: Any,
    ) -> Optional[Path]:
        """
        Phase 5: Generate report, save artifacts, then publish model to registry if provided.

        Flow: Train -> Evaluate -> Save run (here) -> Publish model -> Register model.
        If registry is not None, the trained model is copied to models/<model_id>/
        and registered so the prediction workflow can use it without manual edits.
        publish_overrides are passed to publish_from_pipeline_context (e.g. model_id, notes, version).
        """
        config = {
            "task_type": self.ctx.task_type,
            "target_col": self.ctx.target_col,
            "enable_feature_set_search": self.ctx.enable_feature_set_search,
            "min_features": self.ctx.min_features,
            "max_features": self.ctx.max_features,
            "random_state": RANDOM_STATE,
        }
        self.reporter.save_artifacts(
            self.ctx.data_quality_report,
            self.ctx.leakage_report,
            self.ctx.importance_ranking,
            self.ctx.candidate_sets,
            self.ctx.cv_results,
            self.ctx.final_features,
            self.ctx.doctor_history,
            self.ctx.trained_pipeline,
            config,
        )
        pdf_path = None
        try:
            pdf_path = self.reporter.generate_pdf(
                self.ctx.data_quality_report,
                self.ctx.leakage_report,
                self.ctx.importance_ranking,
                self.ctx.candidate_sets,
                self.ctx.cv_results,
                self.ctx.final_features,
                self.ctx.doctor_history,
                feature_stability=self.ctx.feature_stability,
            )
        except Exception as e:
            # Metrics and JSON artifacts have already been written; PDF failure should not fail the whole training task.
            logger.warning("PDF report generation failed (artifacts already saved): %s", e, exc_info=True)
            pdf_path = None
        if registry is not None and self.run_dir is not None:
            try:
                entry = publish_from_pipeline_context(
                    self.ctx, self.run_dir, registry, **publish_overrides
                )
                logger.info("Published and registered model: %s (task: %s)", entry.model_id, entry.task_name)
            except Exception as e:
                logger.warning("Model publish/register failed (run artifacts and PDF are saved): %s", e)
        return pdf_path

    def predict(self, X_new: pd.DataFrame) -> tuple[Any, Optional[Any], str]:
        """Predict on new data using trained pipeline."""
        if self.ctx.trained_pipeline is None:
            raise ValueError("No trained model; run Phase 4 first")
        return self.programmer.predict(
            self.ctx.trained_pipeline,
            X_new,
            self.ctx.final_features,
        )
