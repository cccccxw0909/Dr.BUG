"""
Read-only workbench context summaries without patient-level raw data.

In-process calls use mcp_adapter to assemble a bundle and call build_current_context_snapshot_from_bundle.
The FastMCP server registers tools with the same names so the contract remains stable if transport changes later.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.agent.workflow_context_contract import get_focus_job_id, get_mode, get_workspace_model_id

_PENDING_ACTION_LABEL_ZH: Dict[str, str] = {
    "create_training_job": "Training task",
    "draft_training_job": "Training task",
    "create_prediction_job": "Prediction task",
    "draft_single_prediction": "Single-sample prediction",
    "create_recommendation_job": "Recommendation task",
    "create_report_job": "Report or release",
    "prediction_entry": "Prediction entry",
}

# task_counts buckets align with TaskStatus; canceled tasks count toward total but do not get a separate bucket.
_TASK_COUNT_BUCKETS = frozenset({"queued", "running", "waiting_user", "completed", "failed"})


def _map_pending_action_domain(action_type: str) -> Tuple[str, Optional[str]]:
    at = str(action_type or "").strip()
    label = _PENDING_ACTION_LABEL_ZH.get(at)
    if at in ("create_training_job", "draft_training_job"):
        return "training", label
    if at == "draft_single_prediction":
        return "single_prediction", label
    if at == "create_prediction_job":
        return "batch_prediction", label
    if at == "create_recommendation_job":
        return "recommendation", label
    if at == "create_report_job":
        return "publish", label
    return "unknown", label


def normalize_workbench_mode(chat_context: Dict[str, Any]) -> str:
    mode_raw = (get_mode(chat_context) or str(chat_context.get("mode") or "").strip() or "unknown")
    ml = mode_raw.lower()
    if ml in ("prediction", "predict", "predict_outcome"):
        return "predict"
    if ml in ("recommendation", "recommend", "recommend_regimen"):
        return "recommend"
    if ml in ("train", "training"):
        return "train"
    if ml == "home":
        return "home"
    if not ml or ml == "unknown":
        return "unknown"
    return "unknown"


def _task_counts(tasks_meta: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "total": len(tasks_meta),
        "queued": 0,
        "running": 0,
        "waiting_user": 0,
        "completed": 0,
        "failed": 0,
    }
    for t in tasks_meta:
        st = str(t.get("status") or "").strip()
        if st in _TASK_COUNT_BUCKETS:
            counts[st] += 1
    return counts


def _build_available_next_steps(
    *,
    mode: str,
    pending_exists: bool,
    selected_id: Optional[str],
) -> List[str]:
    out: List[str] = []
    if pending_exists:
        out.append("Continue the pending action after reviewing and confirming it in the interface")
    if mode == "train":
        out.append("Review training task status or progress")
    if mode == "predict" and selected_id:
        out.append("Continue the individualized prediction workflow")
    if mode == "recommend":
        out.append("Continue the regimen recommendation workflow")
    if mode == "home":
        out.append("Choose training, prediction, or recommendation from the home page")
    if not out:
        out.append("Select a workbench function to continue")
    return out[:4]


def build_current_context_snapshot_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bundle fields, all injected by the adapter so the tool layer does not depend directly on global runtime:
    - chat_context: dict
    - tasks_meta: [{id, job_type, status}, ...]
    - pending_exists: bool
    - pending_action_type: str | None  (raw ActionType)
    - pending_label: str | None
    - llm_chat_model: str | None
    """
    chat = dict(bundle.get("chat_context") or {})
    tasks_meta = [dict(x) for x in (bundle.get("tasks_meta") or []) if isinstance(x, dict)]
    pending_exists = bool(bundle.get("pending_exists"))
    pending_raw = bundle.get("pending_action_type")
    pending_raw_s = str(pending_raw).strip() if pending_raw else None
    pending_label_in = bundle.get("pending_label")
    llm_chat_model = bundle.get("llm_chat_model")
    llm_s = str(llm_chat_model).strip() if llm_chat_model is not None else ""

    mode = normalize_workbench_mode(chat)
    mid = (
        get_workspace_model_id(chat)
        or str(chat.get("selected_model_id") or chat.get("workspace_model_id") or "").strip()
        or None
    )
    display = (
        chat.get("selected_model_display_name")
        or chat.get("workspace_model_display_name")
        or chat.get("model_display_name")
    )
    display_s = str(display).strip() if display is not None else ""
    display_out = display_s or None

    focus_id = get_focus_job_id(chat) or None
    focus_job: Dict[str, Optional[str]] = {"id": None, "job_type": None, "status": None}
    if focus_id:
        focus_job["id"] = focus_id
        for row in tasks_meta:
            if str(row.get("id") or "") == focus_id:
                focus_job["job_type"] = str(row.get("job_type") or "") or None
                focus_job["status"] = str(row.get("status") or "") or None
                break

    if pending_exists and pending_raw_s:
        domain, lab = _map_pending_action_domain(pending_raw_s)
        label_out = str(pending_label_in).strip() if pending_label_in else lab
    elif pending_exists:
        domain, label_out = "unknown", str(pending_label_in).strip() if pending_label_in else None
    else:
        domain, label_out = "unknown", None

    pending_block = {
        "exists": pending_exists,
        "action_type": domain if pending_exists else "unknown",
        "label": label_out if pending_exists else None,
    }

    counts = _task_counts(tasks_meta)
    steps = _build_available_next_steps(
        mode=mode,
        pending_exists=pending_exists,
        selected_id=mid,
    )

    return {
        "mode": mode,
        "selected_model": {"id": mid, "display_name": display_out},
        "focus_job": focus_job,
        "pending_action": pending_block,
        "task_counts": {
            "total": counts["total"],
            "queued": counts["queued"],
            "running": counts["running"],
            "waiting_user": counts["waiting_user"],
            "completed": counts["completed"],
            "failed": counts["failed"],
        },
        "llm_chat_model": llm_s or None,
        "available_next_steps": steps,
    }


def pending_action_zh_label(action_type: str) -> Optional[str]:
    return _PENDING_ACTION_LABEL_ZH.get(str(action_type or "").strip()) or None


def tasks_meta_from_repo(task_repo: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
    """Extract the minimal public fields from task_repo, excluding params."""
    try:
        rows = task_repo.list()
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for t in rows or []:
        if not isinstance(t, dict):
            continue
        jid = str(t.get("id") or "").strip()
        if not jid.startswith("job_"):
            continue
        st = str(t.get("status") or "").strip()
        out.append(
            {
                "id": jid,
                "job_type": str(t.get("job_type") or "").strip() or None,
                "status": st or None,
            }
        )
    return out
