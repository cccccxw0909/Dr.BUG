"""Continue-to-act after workflow_guidance: maps onto existing pending/draft actions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.agent.chat_output_locale import normalize_chat_output_locale
from backend.agent.continue_intent import wants_continue_to_act, wants_continue_to_explain
from backend.agent.i18n import chat_msg
from backend.agent.prediction_answerability import workspace_model_id
from backend.agent.reply_semantics import build_status_payload
from backend.agent.workflow_guidance import build_workflow_snapshot
from backend.agent.workflow_guidance_enrich import (
    build_extended_fingerprint,
    classify_continue_drift,
    focus_job_id_from_context,
)
from backend.agent.workflow_guidance_storage import load_last_guidance_record
from backend.recommendation.regimen_repo import FileRegimenRepo
from backend.schemas.agent import ChatTurnRequest

_DRIFT_MSG_KEY: Dict[str, str] = {
    "drift_workflow_domain": "workflow_continue.drift_label.workflow_domain",
    "drift_focus_job": "workflow_continue.drift_label.focus_job",
    "drift_recommendation_state": "workflow_continue.drift_label.recommendation_state",
    "drift_prediction_context": "workflow_continue.drift_label.prediction_context",
    "drift_workspace_model": "workflow_continue.drift_label.workspace_model",
    "drift_workspace_mode": "workflow_continue.drift_label.workspace_mode",
    "drift_workflow_goal": "workflow_continue.drift_label.workflow_goal",
    "drift_workflow_stage": "workflow_continue.drift_label.workflow_stage",
    "drift_generic": "workflow_continue.drift_label.generic",
}


def build_training_draft_payload_from_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelist training-contract fields from task params only; no patient tables."""
    p = task.get("params") if isinstance(task.get("params"), dict) else {}
    out: Dict[str, Any] = {}
    for k in (
        "dataset_id",
        "clinical_task_id",
        "ml_task_type",
        "target_column",
        "med_cols",
        "selected_features",
        "feature_set",
        "enable_feature_set_search",
        "min_features",
        "max_features",
        "use_cv_shap",
        "index_time",
        "label_time",
        "model_type",
        "objective_metric",
        "publish_overrides",
        "enable_search",
        "model_name",
        "final_features",
    ):
        if k in p:
            out[k] = p[k]
    if not out.get("selected_features") and not out.get("feature_set"):
        if not out.get("enable_feature_set_search") and not out.get("use_cv_shap"):
            out["enable_feature_set_search"] = bool(p.get("enable_feature_set_search", True))
            out["use_cv_shap"] = bool(p.get("use_cv_shap", True))
    return out


def _enabled_regimen_refs() -> List[Dict[str, Any]]:
    repo = FileRegimenRepo()
    out: List[Dict[str, Any]] = []
    for item in repo.list():
        if not item.get("enabled", True):
            continue
        rid = str(item.get("regimen_id") or "").strip()
        if not rid:
            continue
        out.append({"regimen_id": rid, "regimen_name": str(item.get("regimen_name") or rid)})
    return out[:12]


def resolve_continue_target_from_guidance(
    *,
    stored_bundle: Dict[str, Any],
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
    pred_state: str,
) -> Tuple[Optional[str], Dict[str, Any], str]:
    """
    Returns (draft_action_type, payload, reason_code).
    reason_code: ok | no_draft | drift | explain
    """
    from backend.agent.workflow_guidance_enrich import enrich_recommended_with_draft

    b = enrich_recommended_with_draft(dict(stored_bundle))
    rec = b.get("recommended_action") or {}
    draft_type = str(rec.get("draft_action_type") or "").strip()
    domain_b = str(b.get("workflow_domain") or "")
    rs_b = str(b.get("recommendation_state") or "")
    if domain_b == "recommendation" and rs_b in ("completed", "failed", "running", "queued"):
        bad = (not draft_type or draft_type != "create_recommendation_job") or not bool(rec.get("can_draft"))
        if bad:
            if rs_b == "completed":
                return None, {}, "rec_completed_no_redraft"
            if rs_b == "failed":
                return None, {}, "rec_failed_no_redraft"
            return None, {}, "rec_running_no_redraft"
    if not draft_type:
        return None, {}, "no_draft"
    if not bool(rec.get("can_draft")):
        return None, {}, "no_draft"

    snap = build_workflow_snapshot("continue", task_repo, chat_context, pred_state=pred_state)
    cur_fp = build_extended_fingerprint(chat_context, snap)
    drift = classify_continue_drift(b, cur_fp)
    if drift:
        return None, {}, drift

    tid = str(b.get("task_id") or "").strip()
    task_row = task_repo.get(tid) if tid.startswith("job_") else None
    domain = str(b.get("workflow_domain") or "")

    if draft_type == "draft_training_job":
        if not task_row or str(task_row.get("job_type") or "") != "train_model":
            return None, {}, "no_draft"
        if str(task_row.get("status") or "") != "waiting_user":
            return None, {}, "no_draft"
        cur_focus = focus_job_id_from_context(chat_context or {})
        if tid and cur_focus and tid != cur_focus:
            return None, {}, "drift"
        return draft_type, build_training_draft_payload_from_task(task_row), "ok"

    if draft_type == "draft_single_prediction":
        mid = workspace_model_id(chat_context or {})
        if not mid:
            return None, {}, "no_draft"
        if str(snap.get("workflow_domain") or "") != "prediction":
            return None, {}, "drift"
        return draft_type, {"model_id": mid, "patient_features": {}}, "ok"

    if draft_type == "create_prediction_job":
        mid = workspace_model_id(chat_context or {})
        if not mid:
            return None, {}, "no_draft"
        pl: Dict[str, Any] = {"model_id": mid, "patient_features": {}, "prediction_mode": "batch"}
        return draft_type, pl, "ok"

    if draft_type == "create_recommendation_job":
        if str(b.get("recommendation_state") or "") != "ready_to_run":
            return None, {}, "rec_state_not_ready"
        mid = workspace_model_id(chat_context or {})
        if not mid:
            return None, {}, "no_draft"
        regn = _enabled_regimen_refs()
        if not regn:
            return None, {}, "no_draft"
        pl = {
            "model_id": mid,
            "patient_features": {},
            "candidate_regimens": regn,
            "mode": "survival_only",
        }
        return draft_type, pl, "ok"

    return None, {}, "no_draft"


def maybe_continue_from_guidance_turn(
    req: ChatTurnRequest,
    task_repo: Any,
    *,
    pred_state: str,
    registry: Any,
) -> Optional[Dict[str, Any]]:
    """
    Returns None when not handled; otherwise a dict:
    - kind explain / reject → semantic
    - kind handoff → action_type + payload
    """
    loc = normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    if wants_continue_to_explain(req.message or ""):
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.explain.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.explain.bullet_clarify"),
                chat_msg(loc, "workflow_continue.explain.bullet_no_draft"),
            ],
            summary=chat_msg(loc, "workflow_continue.explain.summary"),
            locale=loc,
        )
        return {"kind": "explain", "semantic": sem}

    if not wants_continue_to_act(req.message or ""):
        return None

    from backend.agent.pending_scope import resolve_pending_scope_key

    scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
    if registry.has_active_pending(scope_key):
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.pending_conflict.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.pending_conflict.bullet"),
            ],
            summary=chat_msg(loc, "workflow_continue.pending_conflict.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "pending_conflict"}

    rec, guidance_status = load_last_guidance_record(scope_key)
    if guidance_status == "expired":
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.guidance_expired.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.guidance_expired.bullet"),
            ],
            summary=chat_msg(loc, "workflow_continue.guidance_expired.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "guidance_expired"}

    if guidance_status != "ok" or not rec or not isinstance(rec.get("bundle"), dict):
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.no_stored_guidance.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.no_stored_guidance.bullet"),
            ],
            summary=chat_msg(loc, "workflow_continue.no_stored_guidance.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "no_stored_guidance"}

    bundle = dict(rec["bundle"])
    action_type, payload, code = resolve_continue_target_from_guidance(
        stored_bundle=bundle,
        task_repo=task_repo,
        chat_context=req.chat_context,
        pred_state=pred_state,
    )
    if isinstance(code, str) and code.startswith("drift_"):
        lab = chat_msg(loc, _DRIFT_MSG_KEY.get(code, "workflow_continue.drift_label.fallback"))
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.drift.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.drift.bullet_detail", lab=lab, code=code),
                chat_msg(loc, "workflow_continue.drift.bullet_refresh"),
            ],
            summary=chat_msg(loc, "workflow_continue.drift.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": code}

    if code == "rec_completed_no_redraft":
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.rec_completed.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.rec_completed.bullet_review"),
                chat_msg(loc, "workflow_continue.rec_completed.bullet_no_redraft"),
            ],
            summary=chat_msg(loc, "workflow_continue.rec_completed.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "recommendation_completed_no_redraft"}

    if code == "rec_failed_no_redraft":
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.rec_failed.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.rec_failed.bullet_recover"),
                chat_msg(loc, "workflow_continue.rec_failed.bullet_no_retry"),
            ],
            summary=chat_msg(loc, "workflow_continue.rec_failed.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "recommendation_failed_no_redraft"}

    if code == "rec_running_no_redraft":
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.rec_running.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.rec_running.bullet_wait"),
                chat_msg(loc, "workflow_continue.rec_running.bullet_no_draft"),
            ],
            summary=chat_msg(loc, "workflow_continue.rec_running.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "recommendation_running_no_redraft"}

    if code == "rec_state_not_ready":
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.rec_state_not_ready.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.rec_state_not_ready.bullet"),
            ],
            summary=chat_msg(loc, "workflow_continue.rec_state_not_ready.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "recommendation_state_not_ready"}

    if not action_type or code != "ok":
        sem = build_status_payload(
            user_message=req.message or "",
            user_intent=chat_msg(loc, "workflow_continue.precondition_failed.user_intent"),
            status_bullets=[
                chat_msg(loc, "workflow_continue.precondition_failed.bullet"),
            ],
            summary=chat_msg(loc, "workflow_continue.precondition_failed.summary"),
            locale=loc,
        )
        return {"kind": "reject", "semantic": sem, "reason": "precondition_failed"}

    return {"kind": "handoff", "action_type": action_type, "payload": payload}


