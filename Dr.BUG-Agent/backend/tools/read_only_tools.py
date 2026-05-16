from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.config import QWEN_MODEL
from backend.prediction import factual_core
from backend.prediction import prediction_factual_core as pfc
from backend.schemas.task import JobType
from backend.training.training_factual_core import build_training_factual_bundle, select_latest_training_task_for_summary
from backend.tools.read_only_privacy import (
    TASK_PUBLIC_FIELDS,
    ReadonlyTruncateTracker,
    attach_truncated_marker,
    task_list_public_view,
    task_public_view,
)


@dataclass
class ReadonlyToolContext:
    """Read-only tool execution context: must not carry patient-level tables or raw samples."""

    chat_context: Dict[str, Any]
    user_id: str
    task_repo: Any


def _get_current_context(ctx: ReadonlyToolContext, _args: Dict[str, Any]) -> Dict[str, Any]:
    c = ctx.chat_context or {}
    mode = str(c.get("mode") or "").strip() or None
    dataset = str(c.get("dataset") or "").strip() or None
    model = str(c.get("model") or "").strip() or None
    all_tasks = ctx.task_repo.list()
    from collections import Counter

    by_status = dict(Counter(str(t.get("status") or "") for t in all_tasks))
    return {
        "mode": mode,
        "dataset": dataset,
        "model": model,
        "llm_chat_model": QWEN_MODEL,
        "task_counts_by_status": by_status,
        "task_total": len(all_tasks),
    }


def _list_tasks(ctx: ReadonlyToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    status = args.get("status")
    if status is not None:
        status = str(status).strip() or None
    job_type = args.get("job_type")
    if job_type is not None:
        job_type = str(job_type).strip() or None
    limit = int(args.get("limit") or 50)
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    raw = ctx.task_repo.list(status=status, job_type=job_type)
    slice_raw = raw[:limit]
    return {
        "tasks": task_list_public_view(slice_raw),
        "total_matched": len(raw),
        "returned": len(slice_raw),
    }


def _get_task_status(ctx: ReadonlyToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(args.get("job_id") or "").strip()
    if not job_id:
        return {"ok": False, "error": "missing_job_id", "task": None}
    task = ctx.task_repo.get(job_id)
    if not task:
        return {"ok": False, "error": "not_found", "task": None}
    return {"ok": True, "error": None, "task": task_public_view(task)}


def _get_latest_failure(ctx: ReadonlyToolContext, _args: Dict[str, Any]) -> Dict[str, Any]:
    failed = ctx.task_repo.list(status="failed")
    if not failed:
        return {"failure": None}
    # Sorted by created_at descending; when ties occur among failures, completed_at breaks ties.
    def sort_key(t: Dict[str, Any]) -> str:
        return str(t.get("completed_at") or t.get("created_at") or "")

    failed_sorted = sorted(failed, key=sort_key, reverse=True)
    return {"failure": task_public_view(failed_sorted[0])}


def _get_latest_training_summary(ctx: ReadonlyToolContext, _args: Dict[str, Any]) -> Dict[str, Any]:
    task = select_latest_training_task_for_summary(ctx.task_repo)
    if not task:
        return {"training": None}
    tracker = ReadonlyTruncateTracker()
    bundle = build_training_factual_bundle(task, tracker)
    out: Dict[str, Any] = {
        "task": task_public_view(task),
        "training_summary": bundle.get("public_summary"),
        "evidence": bundle.get("evidence"),
    }
    attach_truncated_marker(out, tracker)
    return out


def _get_latest_prediction_summary(ctx: ReadonlyToolContext, _args: Dict[str, Any]) -> Dict[str, Any]:
    resolved = pfc.resolve_latest_prediction_payload_source(ctx.task_repo)
    tracker = ReadonlyTruncateTracker()
    if resolved is None:
        return {
            "prediction": None,
            "evidence": None,
            "source": "none",
            "latest_prediction_task_id": None,
        }
    bundle = pfc.build_prediction_tool_payload(
        resolved.raw,
        source_kind=resolved.source_kind,
        task_row=resolved.task_row,
        tracker=tracker,
    )
    lid = None
    if isinstance(resolved.latest_task_row, dict):
        lid = resolved.latest_task_row.get("id")
    out = {
        "prediction": bundle["public_summary"],
        "evidence": bundle["evidence"],
        "source": resolved.payload_source,
        "latest_prediction_task_id": lid,
    }
    attach_truncated_marker(out, tracker)
    return out


def _get_prediction_explanation_summary(ctx: ReadonlyToolContext, _args: Dict[str, Any]) -> Dict[str, Any]:
    resolved = pfc.resolve_latest_prediction_payload_source(ctx.task_repo)
    tracker = ReadonlyTruncateTracker()
    raw = dict(resolved.raw) if resolved else {}
    sk = resolved.source_kind if resolved else "history_record"
    exp = factual_core.build_explanation_readonly_summary(raw, source_kind=sk, tracker=tracker)
    out = {"explanation": exp}
    attach_truncated_marker(out, tracker)
    return out


TOOL_HANDLERS: Dict[str, Callable[[ReadonlyToolContext, Dict[str, Any]], Dict[str, Any]]] = {
    "get_current_context": _get_current_context,
    "list_tasks": _list_tasks,
    "get_task_status": _get_task_status,
    "get_latest_failure": _get_latest_failure,
    "get_latest_training_summary": _get_latest_training_summary,
    "get_latest_prediction_summary": _get_latest_prediction_summary,
    "get_prediction_explanation_summary": _get_prediction_explanation_summary,
}


def friendly_readonly_query_labels(planned: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
    """User-facing labels for what was queried; excludes internal tool names."""
    out: List[str] = []
    for name, args in planned:
        if name == "list_tasks":
            st = args.get("status")
            if st == "running":
                lab = "Running tasks"
            elif st == "queued":
                lab = "Queued tasks"
            else:
                lab = "Recent task overview"
        elif name == "get_current_context":
            lab = "Workspace and model overview"
        elif name == "get_task_status":
            lab = "Specific task status"
        elif name == "get_latest_failure":
            lab = "Latest failure details"
        elif name == "get_latest_training_summary":
            lab = "Latest training summary"
        elif name == "get_latest_prediction_summary":
            lab = "Latest prediction summary"
        elif name == "get_prediction_explanation_summary":
            lab = "Prediction explanation summary"
        else:
            continue
        if lab not in out:
            out.append(lab)
    return out


def execute_readonly_tool(name: str, args: Dict[str, Any], ctx: ReadonlyToolContext) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"ok": False, "error": "unknown_tool", "tool": name}
    out = handler(ctx, dict(args or {}))
    return {"ok": True, "tool": name, "result": out}


def tool_registry_public_specs() -> List[Dict[str, Any]]:
    """Minimal specs for docs/tests"""
    return [
        {
            "name": "get_current_context",
            "input": {},
            "output_fields": ["mode", "dataset", "model", "llm_chat_model", "task_counts_by_status", "task_total"],
            "privacy": "P0",
            "data_source": "ChatTurnRequest.chat_context, config.QWEN_MODEL, task_repo.list() aggregates only",
        },
        {
            "name": "list_tasks",
            "input": {"status": "optional[str]", "job_type": "optional[str]", "limit": "optional[int]"},
            "output_fields": ["tasks[](" + ",".join(sorted(TASK_PUBLIC_FIELDS)) + ")", "total_matched", "returned"],
            "privacy": "P1",
            "data_source": "task_repo.list + field allowlist",
        },
        {
            "name": "get_task_status",
            "input": {"job_id": "str"},
            "output_fields": ["ok", "error", "task(" + ",".join(sorted(TASK_PUBLIC_FIELDS)) + ")"],
            "privacy": "P1",
            "data_source": "task_repo.get + field allowlist",
        },
        {
            "name": "get_latest_failure",
            "input": {},
            "output_fields": ["failure(null|" + ",".join(sorted(TASK_PUBLIC_FIELDS)) + ")"],
            "privacy": "P1",
            "data_source": "task_repo.list(status=failed) + field allowlist",
        },
        {
            "name": "get_latest_training_summary",
            "input": {},
            "output_fields": [
                "task(" + ",".join(sorted(TASK_PUBLIC_FIELDS)) + ")",
                "training_summary(dict|none)",
                "evidence(dict)",
            ],
            "privacy": "P1",
            "forbidden_to_llm": "params, feature column lists, non-allowlisted result_summary keys, artifacts",
            "data_source": "training_factual_core: latest training task + training_result_summary_public_view",
        },
        {
            "name": "get_latest_prediction_summary",
            "input": {},
            "output_fields": [
                "prediction(null|{kind,task_name,model_name,predicted_label,predicted_probability,"
                "explanation_supported,top_positive_drivers,top_negative_drivers,summary_text,next_action_hint,"
                "optional:total_rows,succeeded_rows,failed_rows,output_file_name,source,job_id})",
                "evidence(null|dict)",
                "source(task|history|none)",
                "latest_prediction_task_id(null|str)",
            ],
            "privacy": "P1",
            "forbidden_to_llm": "input_summary, feature_values_used, full result, full field_check, URLs, SHAP plots",
            "data_source": "prediction_factual_core: select_latest_prediction_task + resolve_latest_prediction_payload_source + factual_core projection",
        },
        {
            "name": "get_prediction_explanation_summary",
            "input": {},
            "output_fields": [
                "explanation({kind,explanation_available,explanation_summary_text,"
                "top_positive_drivers,top_negative_drivers})",
            ],
            "privacy": "P1",
            "forbidden_to_llm": "SHAP URLs, per-feature values, full explanation payloads",
            "data_source": "factual_core.build_explanation_readonly_summary",
        },
    ]
