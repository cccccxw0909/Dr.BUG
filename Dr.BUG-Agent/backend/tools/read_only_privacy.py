from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

# --- Unified budgets for read-only summaries before LLM (observable truncation) ---
MAX_SUMMARY_TEXT_LEN = 800
MAX_FILTER_SUMMARY_LEN = 1200
MAX_WARNINGS_COUNT = 12
MAX_WARNING_ITEM_LEN = 500
MAX_TOP_FEATURES_COUNT = 10
MAX_FIELD_CHECK_LIST_ITEMS = 24

MAX_METRICS_DEPTH = 3
MAX_METRICS_DICT_KEYS = 32
MAX_METRICS_LIST_ITEMS = 20
MAX_METRICS_STRING_LEN = 2000


@dataclass
class ReadonlyTruncateTracker:
    """Records truncation paths when limits are exceeded; written into tool results for LLM/audit visibility."""

    paths: List[str] = field(default_factory=list)

    def add(self, path: str) -> None:
        if path not in self.paths:
            self.paths.append(path)


def clip_str(value: str, max_len: int, path: str, tracker: Optional[ReadonlyTruncateTracker]) -> str:
    if len(value) <= max_len:
        return value
    if tracker:
        tracker.add(path)
    return value[:max_len] + "…"


# Keys allowed from training task result_summary into the "summary" view (no column pools or per-column lists)
TRAINING_SUMMARY_ALLOWED_KEYS: Set[str] = {
    "headline",
    "train_workflow_phase",
    "task_kind",
    "next_action",
    "model_id",
    "model_registered",
    "model_id_draft",
    "primary_metric_requested",
    "trained_model_programmer_name",
    "feature_set_search_executed",
    "filter_summary",
    # Phase4 model-selection CV table (safe aggregates; no row-level patient data)
    "all_model_metrics_rows",
    # Phase5 final vs candidate semantics (aggregates only)
    "metrics_protocol",
    "enable_search_applied",
}

# Training summary keys explicitly stripped before LLM (even if present in result_summary)
TRAINING_SUMMARY_FORBIDDEN_KEYS: Set[str] = {
    "params",
    "candidate_pool_columns",
    "med_cols",
    "recommended_features",
    "suggested_final_features",
    "final_features_locked",
    "final_features",
    "selected_features",
    "artifacts",
    "programmer_model",
}

# Task fields safe to expose to LLM (excludes params / result_summary / artifacts, etc.)
TASK_PUBLIC_FIELDS: Set[str] = {
    "id",
    "job_type",
    "status",
    "progress",
    "current_stage",
    "message",
    "error_message",
    "created_at",
    "started_at",
    "completed_at",
}


def task_public_view(task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not task:
        return None
    return {k: task.get(k) for k in TASK_PUBLIC_FIELDS if k in task}


def task_list_public_view(tasks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [task_public_view(t) or {} for t in tasks if t]


def metrics_blob_public_view(
    obj: Any,
    depth: int = 0,
    path: str = "key_metrics",
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Any:
    """
    Shallow projection of aggregated metrics JSON; records truncated paths when depth/key/list/string caps are hit.
    """
    if depth > MAX_METRICS_DEPTH:
        if tracker:
            tracker.add(f"{path}.depth>{MAX_METRICS_DEPTH}")
        return None
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return clip_str(obj, MAX_METRICS_STRING_LEN, f"{path}.string", tracker)
    if isinstance(obj, list):
        if len(obj) > MAX_METRICS_LIST_ITEMS and tracker:
            tracker.add(f"{path}.list_len>{MAX_METRICS_LIST_ITEMS}")
        return [
            metrics_blob_public_view(x, depth + 1, f"{path}[{i}]", tracker)
            for i, x in enumerate(obj[:MAX_METRICS_LIST_ITEMS])
        ]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= MAX_METRICS_DICT_KEYS:
                if tracker:
                    tracker.add(f"{path}.dict_keys>{MAX_METRICS_DICT_KEYS}")
                break
            key = str(k)
            if key in TRAINING_SUMMARY_FORBIDDEN_KEYS:
                continue
            out[key] = metrics_blob_public_view(v, depth + 1, f"{path}.{key}", tracker)
        return out
    return None


def training_result_summary_public_view(
    rs: Optional[Dict[str, Any]],
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Optional[Dict[str, Any]]:
    """
    Allowlisted projection of training-side result_summary.
    Does not return: params, feature column lists, full artifacts, raw samples, etc.
    """
    if not rs or not isinstance(rs, dict):
        return None
    out: Dict[str, Any] = {}
    for k in TRAINING_SUMMARY_ALLOWED_KEYS:
        if k in rs and k not in TRAINING_SUMMARY_FORBIDDEN_KEYS:
            if k == "filter_summary":
                raw = rs[k]
                if isinstance(raw, str):
                    out[k] = clip_str(raw, MAX_FILTER_SUMMARY_LEN, "training_summary.filter_summary", tracker)
                else:
                    out[k] = raw
            else:
                out[k] = rs[k]
    km = rs.get("key_metrics")
    if km is not None:
        out["key_metrics"] = metrics_blob_public_view(km, 0, "training_summary.key_metrics", tracker)
    fm = rs.get("final_model_metrics")
    if fm is not None:
        out["final_model_metrics"] = metrics_blob_public_view(fm, 0, "training_summary.final_model_metrics", tracker)
    return out if out else None


def prediction_history_record_public_view(
    rec: Optional[Dict[str, Any]],
    tracker: Optional[ReadonlyTruncateTracker] = None,
) -> Optional[Dict[str, Any]]:
    """
    Summary view for a single prediction history record.
    Forbidden: input_summary, feature_values_used, full result payloads, per-feature values, etc.
    """
    if not rec or not isinstance(rec, dict):
        return None
    base: Dict[str, Any] = {
        "record_id": rec.get("record_id"),
        "type": rec.get("type"),
        "timestamp": rec.get("timestamp"),
        "task_name": rec.get("task_name"),
        "model_id": rec.get("model_id"),
        "display_name": rec.get("display_name"),
    }
    ptype = str(rec.get("type") or "")
    if ptype == "single":
        base["predicted_label"] = rec.get("predicted_label")
        base["predicted_value"] = rec.get("predicted_value")
        base["predicted_probability"] = rec.get("predicted_probability")
        st = rec.get("summary_text")
        st_str = str(st) if st is not None else ""
        base["summary_text"] = clip_str(st_str, MAX_SUMMARY_TEXT_LEN, "prediction.summary_text", tracker)
        base["explanation_supported"] = rec.get("explanation_supported")
        tf = rec.get("top_features")
        if isinstance(tf, list):
            if len(tf) > MAX_TOP_FEATURES_COUNT and tracker:
                tracker.add(f"prediction.top_features>{MAX_TOP_FEATURES_COUNT}")
            slim = []
            for item in tf[:MAX_TOP_FEATURES_COUNT]:
                if isinstance(item, dict):
                    slim.append(
                        {
                            "name": item.get("name"),
                            "direction": item.get("direction"),
                        }
                    )
            base["top_features"] = slim
    elif ptype == "batch":
        base["total_rows"] = rec.get("total_rows")
        base["succeeded_rows"] = rec.get("succeeded_rows")
        base["failed_rows"] = rec.get("failed_rows")
        fcs = rec.get("field_check_summary")
        if isinstance(fcs, dict):
            rmf = fcs.get("required_missing_fields")
            if isinstance(rmf, list) and len(rmf) > MAX_FIELD_CHECK_LIST_ITEMS and tracker:
                tracker.add("prediction.field_check.required_missing_fields>cap")
            base["field_check_summary"] = {}
            for kk in ("matched_count", "missing_count", "extra_count", "required_missing_fields"):
                if kk not in fcs:
                    continue
                if kk == "required_missing_fields" and isinstance(fcs[kk], list):
                    base["field_check_summary"][kk] = list(fcs[kk])[:MAX_FIELD_CHECK_LIST_ITEMS]
                else:
                    base["field_check_summary"][kk] = fcs[kk]
    w = rec.get("warnings")
    if isinstance(w, list):
        if len(w) > MAX_WARNINGS_COUNT and tracker:
            tracker.add(f"prediction.warnings>{MAX_WARNINGS_COUNT}")
        lines = []
        for i, x in enumerate(w[:MAX_WARNINGS_COUNT]):
            item = clip_str(str(x), MAX_WARNING_ITEM_LEN, f"prediction.warnings[{i}]", tracker)
            lines.append(item)
        base["warnings"] = lines
    return base


def attach_truncated_marker(target: Dict[str, Any], tracker: ReadonlyTruncateTracker) -> None:
    if tracker.paths:
        target["truncated"] = True
        target["truncated_paths"] = list(tracker.paths)
