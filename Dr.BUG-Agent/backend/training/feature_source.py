"""Feature-source priority and execution strategy aligned with product behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.training.feature_set_registry import resolve_named_feature_set


class FeatureStrategy(str, Enum):
    FINAL_FEATURES_DIRECT = "final_features_direct"
    SELECTED_WITH_SEARCH = "selected_with_search"
    SELECTED_DIRECT = "selected_direct"
    FEATURE_SET = "feature_set"
    DEFAULT_POOL_SEARCH = "default_pool_search"


@dataclass
class ResolvedFeaturePlan:
    strategy: FeatureStrategy
    """Candidate columns for Phase 2 importance/search, excluding the target."""
    candidate_pool_columns: List[str]
    """When strategy is FINAL, these become Phase 4 modeling columns directly and already include med_cols merge semantics."""
    locked_final_columns: Optional[List[str]]
    """Original named feature-group key, if present."""
    feature_set_key: Optional[str] = None


def _uniq(cols: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for c in cols:
        s = str(c).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _merge_med(final_like: List[str], med_cols: List[str], all_cols: List[str]) -> List[str]:
    avail = set(all_cols)
    base = _uniq([c for c in final_like if c in avail])
    for m in med_cols:
        ms = str(m).strip()
        if ms and ms in avail and ms not in base:
            base.append(ms)
    return base


def resolve_feature_strategy(params: Dict[str, Any], dataframe_columns: List[str], target_col: str) -> ResolvedFeaturePlan:
    """
    Resolve the feature plan by priority. dataframe_columns are cleaned available columns, including the target.
    med_cols cannot be the only source.
    """
    target_col = str(target_col).strip()
    med = [str(x).strip() for x in (params.get("med_cols") or []) if str(x).strip()]
    fin = _uniq([str(x).strip() for x in (params.get("final_features") or []) if str(x).strip()])
    fin = [c for c in fin if c in dataframe_columns and c != target_col]
    sel = _uniq([str(x).strip() for x in (params.get("selected_features") or []) if str(x).strip()])
    sel = [c for c in sel if c in dataframe_columns and c != target_col]
    fs_raw = params.get("feature_set")
    fs_key = str(fs_raw).strip() if fs_raw else ""
    enable_search = bool(params.get("enable_feature_set_search"))

    # Named-group resolution.
    resolved_fs_cols: List[str] = []
    if fs_key:
        resolved_fs_cols = resolve_named_feature_set(fs_key)
        resolved_fs_cols = [c for c in resolved_fs_cols if c in dataframe_columns and c != target_col]

    if fin:
        locked = _merge_med(fin, med, dataframe_columns)
        if not locked:
            raise ValueError("All final_features columns are absent from the dataset or invalid")
        return ResolvedFeaturePlan(
            strategy=FeatureStrategy.FINAL_FEATURES_DIRECT,
            candidate_pool_columns=locked,
            locked_final_columns=locked,
            feature_set_key=fs_key or None,
        )

    if sel and enable_search:
        pool = _merge_med(sel, med, dataframe_columns)
        if not pool:
            raise ValueError("selected_features is used for search, but the candidate pool has no valid dataset columns")
        return ResolvedFeaturePlan(
            strategy=FeatureStrategy.SELECTED_WITH_SEARCH,
            candidate_pool_columns=pool,
            locked_final_columns=None,
            feature_set_key=fs_key or None,
        )

    if sel:
        pool = _merge_med(sel, med, dataframe_columns)
        if not pool:
            raise ValueError("selected_features is empty or has no valid columns")
        return ResolvedFeaturePlan(
            strategy=FeatureStrategy.SELECTED_DIRECT,
            candidate_pool_columns=pool,
            locked_final_columns=None,
            feature_set_key=fs_key or None,
        )

    if resolved_fs_cols:
        if enable_search:
            pool = _merge_med(resolved_fs_cols, med, dataframe_columns)
            return ResolvedFeaturePlan(
                strategy=FeatureStrategy.SELECTED_WITH_SEARCH,
                candidate_pool_columns=pool,
                locked_final_columns=None,
                feature_set_key=fs_key,
            )
        pool = _merge_med(resolved_fs_cols, med, dataframe_columns)
        return ResolvedFeaturePlan(
            strategy=FeatureStrategy.FEATURE_SET,
            candidate_pool_columns=pool,
            locked_final_columns=None,
            feature_set_key=fs_key,
        )

    if enable_search:
        pool = [c for c in dataframe_columns if c != target_col]
        if not pool:
            raise ValueError("Feature-set search is enabled without a candidate pool, but the dataset has no available feature columns")
        return ResolvedFeaturePlan(
            strategy=FeatureStrategy.DEFAULT_POOL_SEARCH,
            candidate_pool_columns=_uniq(pool),
            locked_final_columns=None,
            feature_set_key=None,
        )

    use_cv_shap = bool(params.get("use_cv_shap"))
    if use_cv_shap:
        pool = [c for c in dataframe_columns if c != target_col]
        if not pool:
            raise ValueError("use_cv_shap is enabled without feature columns, but the dataset has no candidate columns other than the target")
        return ResolvedFeaturePlan(
            strategy=FeatureStrategy.SELECTED_DIRECT,
            candidate_pool_columns=_uniq(pool),
            locked_final_columns=None,
            feature_set_key=None,
        )

    raise ValueError(
        "Missing a valid feature source: provide final_features, selected_features, or feature_set (configured in presets), "
        "or enable enable_feature_set_search to use the default full candidate pool. Note: med_cols cannot be the only source."
    )
