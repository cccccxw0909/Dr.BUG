"""
Training-side unified factual core: builds read-only projections and evidence markers from task.result_summary,
shared by get_latest_training_summary, task-summary projection, and dialogue composition to avoid wording drift.
"""

from __future__ import annotations

from typing import Any, Dict, Optional  # tracker uses ReadonlyTruncateTracker | None to avoid top-level tools package imports.

from backend.schemas.task import JobType

# Do not import backend.tools.read_only_privacy at module top level; tools/__init__ would import
# read_only_tools, which imports this module again and creates a circular import.


def _task_recency_key(t: Dict[str, Any]) -> str:
    return str(t.get("completed_at") or t.get("started_at") or t.get("created_at") or "")


def select_latest_training_task_for_summary(task_repo: Any) -> Optional[Dict[str, Any]]:
    """
    Latest-training selection aligned with read-only tools: train_model only.
    Prefer the completed subset; otherwise use all training tasks. Within the chosen pool, select the max completed/started/created time.
    """
    rows = task_repo.list(job_type=JobType.train_model.value)
    if not rows:
        return None
    completed = [t for t in rows if str(t.get("status") or "") == "completed"]
    pool = completed if completed else rows
    try:
        return max(pool, key=_task_recency_key)
    except ValueError:
        return None


def can_claim_best_model(rs: Dict[str, Any]) -> bool:
    """Allow best/optimal conclusions only when explicit best/winner fields are present."""
    if rs.get("best_model_id") or rs.get("best_model_name"):
        return True
    mc = rs.get("model_comparison")
    if isinstance(mc, dict) and (mc.get("winner") or mc.get("best")):
        return True
    return False


def best_model_evidence_line(rs: Dict[str, Any]) -> Optional[str]:
    """Return one repeatable evidence line when can_claim_best_model is true; otherwise return None."""
    if not can_claim_best_model(rs):
        return None
    w = rs.get("best_model_name") or rs.get("best_model_id")
    if isinstance(w, str) and w.strip():
        return w.strip()
    mc = rs.get("model_comparison")
    if isinstance(mc, dict):
        w2 = mc.get("winner") or mc.get("best")
        if isinstance(w2, str) and w2.strip():
            return w2.strip()
    return None


def can_claim_notable_from_filter_summary(rs: Dict[str, Any]) -> bool:
    fs = rs.get("filter_summary")
    return isinstance(fs, str) and bool(fs.strip())


def build_training_factual_bundle(
    task: Dict[str, Any],
    tracker: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Build the factual core from one training task row:
    - public_summary: training_result_summary_public_view using a whitelist plus key_metrics projection
    - evidence: conservative evidence fields for dialogue/tool alignment, excluding full raw result_summary
    """
    from backend.tools.read_only_privacy import training_result_summary_public_view

    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    public = training_result_summary_public_view(rs if rs else None, tracker)
    st = str(task.get("status") or "")
    km = public.get("key_metrics") if isinstance(public, dict) else None
    has_km = isinstance(km, dict) and len(km) > 0
    evidence: Dict[str, Any] = {
        "task_status": st,
        "has_completed_training_task": st == "completed",
        "has_raw_summary": bool(rs),
        "has_projected_summary": bool(public),
        "has_key_metrics": has_km,
        "best_model_claimable": bool(rs) and can_claim_best_model(rs),
        # This project does not introduce external benchmarks; dialogue uses TRAIN_GOOD_OR_BAD_UNIFIED and the factual core does not claim good/bad quality.
        "good_or_bad_claimable": False,
        "notable_from_filter_claimable": bool(rs) and can_claim_notable_from_filter_summary(rs),
    }
    return {"public_summary": public, "evidence": evidence}
