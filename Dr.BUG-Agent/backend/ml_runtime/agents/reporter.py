"""Phase 5: Synthesis & Report (ReporterAgent)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.io import get_run_dir, save_config, save_artifact
from ..utils.report import build_pdf

logger = logging.getLogger(__name__)


class ReporterAgent:
    """Generate local PDF report and save all artifacts."""

    def __init__(self, run_dir: Optional[Path] = None):
        self.run_dir = run_dir or get_run_dir()

    def save_config(self, config: Dict[str, Any]) -> Path:
        """Save config.yaml."""
        return save_config(self.run_dir, config)

    def save_artifacts(
        self,
        data_quality_report: Dict[str, Any],
        leakage_report: Dict[str, Any],
        importance_ranking: Dict[str, List[tuple]],
        candidate_sets: List[List[str]],
        cv_results: Dict[str, Any],
        final_features: List[str],
        doctor_history: List[Dict[str, Any]],
        pipeline: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Path]:
        """Save all artifacts to run directory."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        paths = {}

        paths["data_quality"] = save_artifact(self.run_dir, "data_quality_report.json", data_quality_report)
        paths["leakage"] = save_artifact(self.run_dir, "leakage_report.json", leakage_report)
        paths["importance"] = save_artifact(
            self.run_dir,
            "importance_ranking.json",
            {k: [[f, float(v)] for f, v in ranking] for k, ranking in importance_ranking.items()},
        )
        paths["candidates"] = save_artifact(self.run_dir, "candidate_sets.json", [list(s) for s in candidate_sets])
        paths["cv_results"] = save_artifact(self.run_dir, "cv_results.json", cv_results)
        paths["final_features"] = save_artifact(self.run_dir, "final_features.json", final_features)
        paths["doctor_history"] = save_artifact(self.run_dir, "doctor_history.json", doctor_history)

        if pipeline is not None:
            paths["model"] = save_artifact(self.run_dir, "model.joblib", pipeline)

        if config:
            self.save_config(config)

        return paths

    def generate_pdf(
        self,
        data_quality_report: Dict[str, Any],
        leakage_report: Dict[str, Any],
        importance_ranking: Dict[str, List[tuple]],
        candidate_sets: List[List[str]],
        cv_results: Dict[str, Any],
        final_features: List[str],
        doctor_history: List[Dict[str, Any]],
        feature_stability: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Path:
        """Generate PDF report."""
        pdf_path = build_pdf(
            self.run_dir,
            data_quality_report,
            leakage_report,
            importance_ranking,
            candidate_sets,
            cv_results,
            final_features,
            doctor_history,
            feature_stability=feature_stability,
        )
        return pdf_path
