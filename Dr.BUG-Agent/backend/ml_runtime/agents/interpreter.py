"""Phase 3: Template-based medical interpretation (InterpreterAgent)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TEMPLATE_TOP = "Variable \"{feature}\" ranks #{rank} in model \"{model}\", suggesting possible association with the prediction target (not a causal conclusion)."
# Gentle, non-suggestive tone when user removes a statistically significant variable (Top 3 SHAP or stability>=0.6)
TEMPLATE_REMOVED_GENTLE = "**Observation**: Variable \"{feature}\" shows high statistical contribution. Please review if its exclusion aligns with your clinical study design."
TEMPLATE_ADDED_HIGH_MISSING = "**Observation**: Variable \"{feature}\" has a high missing rate ({missing_rate:.1%}). Please review if its inclusion aligns with your clinical study design."


class InterpreterAgent:
    """Template-based explanations for top features; alerts when important features are removed."""

    def __init__(self, importance_ranking: Optional[Dict[str, List[tuple]]] = None):
        self.importance_ranking = importance_ranking or {}
        self.feature_stability: Dict[str, Dict[str, float]] = {}  # {model_name: {feature: stability_score}}
        self.missing_stats: Dict[str, float] = {}  # {feature: missing_rate}

    def set_importance(self, importance_ranking: Dict[str, List[tuple]]) -> None:
        """Set importance ranking for interpretation."""
        self.importance_ranking = importance_ranking
    
    def set_feature_stability(self, stability: Dict[str, Dict[str, float]]) -> None:
        """Set feature stability scores from CV-SHAP."""
        self.feature_stability = stability
    
    def set_missing_stats(self, missing_stats: Dict[str, float]) -> None:
        """Set missing rate statistics for features."""
        self.missing_stats = missing_stats

    def explain_top_features(
        self,
        top_n: int = 5,
        model_name: Optional[str] = None,
    ) -> List[str]:
        """Generate template explanations for top features. No causal claims."""
        explanations = []
        models = list(self.importance_ranking.keys())[:1] if model_name is None else [model_name]
        for mn in models:
            if mn not in self.importance_ranking:
                continue
            ranking = self.importance_ranking[mn][:top_n]
            for rank, (feat, _) in enumerate(ranking, 1):
                explanations.append(TEMPLATE_TOP.format(feature=feat, model=mn, rank=rank))
        return explanations

    def check_removed_important(
        self,
        selected: List[str],
        top_k: int = 10,
    ) -> List[str]:
        """
        Check if doctor removed features that were in top_k importance.
        Returns list of warning messages.
        """
        warnings = []
        for model_name, ranking in self.importance_ranking.items():
            top_feats = {f for f, _ in ranking[:top_k]}
            removed = top_feats - set(selected)
            for feat in removed:
                rank = next((i + 1 for i, (f, _) in enumerate(ranking) if f == feat), 0)
                warnings.append(TEMPLATE_REMOVED_GENTLE.format(feature=feat))
        return warnings

    def _is_statistically_significant(self, feat: str, top_n_shap: int = 3, stability_threshold: float = 0.6) -> bool:
        """
        True if feature is "statistically significant": Top N (e.g. Top 3) SHAP in any model, or stability >= threshold.
        """
        best_rank = None
        for model_name, ranking in self.importance_ranking.items():
            for i, (f, _) in enumerate(ranking):
                if f == feat:
                    r = i + 1
                    if best_rank is None or r < best_rank:
                        best_rank = r
                    break
        if best_rank is not None and best_rank <= top_n_shap:
            return True
        max_stability = 0.0
        for model_name, stability_dict in self.feature_stability.items():
            if feat in stability_dict and stability_dict[feat] > max_stability:
                max_stability = stability_dict[feat]
        return max_stability >= stability_threshold

    def check_feature_changes(
        self,
        previous_selected: List[str],
        current_selected: List[str],
        stability_threshold: float = 0.6,  # Features with stability >= 0.6 are considered significant
        missing_threshold: float = 0.3,  # Features with missing rate >= 0.3 are considered "high missing"
        top_n_shap: int = 3,  # Top N SHAP (importance rank <= N) counts as statistically significant
    ) -> List[Dict[str, Any]]:
        """
        Check for problematic feature changes and return warnings.
        Important feature = Top 3 SHAP (rank in any model) OR stability >= 0.6.
        Uses gentle, non-suggestive language for observations.
        Returns:
            List of warning dicts with keys: 'type', 'feature', 'message', 'severity'
        """
        warnings = []
        prev_set = set(previous_selected)
        curr_set = set(current_selected)

        # Check removed statistically significant features (Top 3 SHAP or stability >= 0.6)
        removed = prev_set - curr_set
        for feat in removed:
            if self._is_statistically_significant(feat, top_n_shap=top_n_shap, stability_threshold=stability_threshold):
                warnings.append({
                    'type': 'removed_robust',
                    'feature': feat,
                    'message': TEMPLATE_REMOVED_GENTLE.format(feature=feat),
                    'severity': 'high'
                })
        
        # Check added high missing rate features
        added = curr_set - prev_set
        for feat in added:
            missing_rate = self.missing_stats.get(feat, 0.0)
            if missing_rate >= missing_threshold:
                warnings.append({
                    'type': 'added_high_missing',
                    'feature': feat,
                    'message': TEMPLATE_ADDED_HIGH_MISSING.format(
                        feature=feat,
                        missing_rate=missing_rate
                    ),
                    'severity': 'medium'
                })
        
        return warnings
