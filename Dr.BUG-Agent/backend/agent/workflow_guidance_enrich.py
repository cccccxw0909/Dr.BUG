"""workflow_guidance bundle enrichment: fingerprint + draft handoff metadata (separate module to avoid import cycles)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.prediction_answerability import workspace_model_id
from backend.agent.workflow_context_contract import (
    KEY_WF_PREDICTION_KIND,
    get_focus_job_id,
)


def focus_job_id_from_context(chat_context: Optional[Dict[str, Any]]) -> str:
    return get_focus_job_id(chat_context)


def _ctx_int_optional(chat_context: Optional[Dict[str, Any]], key: str) -> Optional[int]:
    ctx = chat_context or {}
    if key not in ctx:
        return None
    v = ctx.get(key)
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _ctx_bool_optional(chat_context: Optional[Dict[str, Any]], key: str) -> Optional[bool]:
    ctx = chat_context or {}
    if key not in ctx:
        return None
    v = ctx.get(key)
    if isinstance(v, bool):
        return v
    if v in (1, "1", "true", "True"):
        return True
    if v in (0, "0", "false", "False"):
        return False
    return None


def _prediction_kind_from_context_and_wf(
    chat_context: Optional[Dict[str, Any]],
    wf: Dict[str, Any],
) -> str:
    ctx = chat_context or {}
    pk = str(ctx.get("wf_prediction_kind") or "").strip().lower()
    if pk:
        return pk
    goal = str(wf.get("workflow_goal") or "")
    if goal == "batch_prediction":
        return "batch"
    if goal == "single_prediction":
        return "single"
    return ""


def build_extended_fingerprint(
    chat_context: Optional[Dict[str, Any]],
    wf: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Key workbench + workflow snapshot signals for continue drift detection.
    wf: may be compose output dict, or snapshot from build_workflow_snapshot.
    """
    ctx = chat_context or {}
    wf = wf or {}
    batch_stage = str(ctx.get("wf_batch_stage") or wf.get("batch_stage") or "").strip()
    out: Dict[str, Any] = {
        "focus_job_id": focus_job_id_from_context(ctx),
        "model": workspace_model_id(ctx),
        "mode": str(ctx.get("mode") or "").strip(),
        "workflow_domain": str(wf.get("workflow_domain") or ""),
        "workflow_stage": str(wf.get("workflow_stage") or ""),
        "workflow_goal": str(wf.get("workflow_goal") or ""),
        "prediction_kind": _prediction_kind_from_context_and_wf(ctx, wf),
        "batch_stage": batch_stage,
    }
    if KEY_WF_PREDICTION_KIND in ctx:
        out[KEY_WF_PREDICTION_KIND] = str(ctx.get(KEY_WF_PREDICTION_KIND) or "").strip().lower()
    n = _ctx_int_optional(ctx, "wf_rec_enabled_regimen_count")
    if n is not None:
        out["rec_enabled_regimen_count"] = n
    rs = _ctx_bool_optional(ctx, "wf_rec_schema_ready")
    if rs is not None:
        out["rec_schema_ready"] = rs
    rf = _ctx_bool_optional(ctx, "wf_rec_form_ready")
    if rf is not None:
        out["rec_form_ready"] = rf
    rs_rec = str(wf.get("recommendation_state") or "").strip()
    if rs_rec:
        out["recommendation_state"] = rs_rec
    return out


def merged_fingerprint_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Merge top-level domain/stage fields from bundle; tolerates older files with partial context_fingerprint."""
    fp = dict(bundle.get("context_fingerprint") or {})
    for k in (
        "workflow_domain",
        "workflow_stage",
        "workflow_goal",
        "batch_stage",
        "recommendation_state",
        KEY_WF_PREDICTION_KIND,
    ):
        v = bundle.get(k)
        if v is not None and str(v).strip() != "":
            fp.setdefault(k, str(v).strip())
    return fp


_REC_OPTIONAL_FP_KEYS = frozenset({"rec_enabled_regimen_count", "rec_schema_ready", "rec_form_ready"})


def _nz(v: Any) -> str:
    return str(v or "").strip()


def classify_continue_drift(stored_bundle: Dict[str, Any], current_fp: Dict[str, Any]) -> Optional[str]:
    """
    If continue handoff is unsafe, return a stable reason subcode; otherwise None.
    Priority: domain > focus job > recommendation lifecycle > single/batch prediction signals > workbench model > mode > remaining keys.
    """
    s = merged_fingerprint_from_bundle(stored_bundle)
    c = current_fp or {}
    sk, ck = _nz(s.get("workflow_domain")), _nz(c.get("workflow_domain"))
    if sk and ck and sk != ck:
        return "drift_workflow_domain"
    sf, cf = _nz(s.get("focus_job_id")), _nz(c.get("focus_job_id"))
    if sf and cf and sf != cf:
        return "drift_focus_job"
    srs, crs = _nz(s.get("recommendation_state")), _nz(c.get("recommendation_state"))
    if srs and crs and srs != crs:
        return "drift_recommendation_state"
    for pk in ("prediction_kind", KEY_WF_PREDICTION_KIND, "batch_stage"):
        sv, cv = _nz(s.get(pk)), _nz(c.get(pk))
        if not sv:
            continue
        if sv != cv:
            return "drift_prediction_context"
    sm, cm = _nz(s.get("model")), _nz(c.get("model"))
    if sm and sm != cm:
        return "drift_workspace_model"
    smd, cmd = _nz(s.get("mode")), _nz(c.get("mode"))
    if smd and smd != cmd:
        return "drift_workspace_mode"
    swg, cwg = _nz(s.get("workflow_goal")), _nz(c.get("workflow_goal"))
    if swg and cwg and swg != cwg:
        return "drift_workflow_goal"
    swst, cwst = _nz(s.get("workflow_stage")), _nz(c.get("workflow_stage"))
    if swst and cwst and swst != cwst:
        return "drift_workflow_stage"
    for k, v in s.items():
        if k.startswith("_"):
            continue
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if k in _REC_OPTIONAL_FP_KEYS and (k not in c or c.get(k) is None):
            continue
        if k in (
            "workflow_domain",
            "focus_job_id",
            "recommendation_state",
            "prediction_kind",
            KEY_WF_PREDICTION_KIND,
            "batch_stage",
            "model",
            "mode",
            "workflow_goal",
            "workflow_stage",
        ):
            continue
        if str(c.get(k)) != str(v):
            return "drift_generic"
    return None


def fingerprints_compatible_for_continue(stored_bundle: Dict[str, Any], current_fp: Dict[str, Any]) -> bool:
    return classify_continue_drift(stored_bundle, current_fp) is None


def attach_fingerprint_to_bundle(bundle: Dict[str, Any], chat_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    bundle["context_fingerprint"] = build_extended_fingerprint(chat_context, bundle)
    return bundle


def enrich_recommended_with_draft(bundle: Dict[str, Any]) -> Dict[str, Any]:
    cands = list(bundle.get("next_step_candidates") or [])
    rec = dict(bundle.get("recommended_action") or {})
    rid = str(rec.get("id") or "")
    hit = next((c for c in cands if isinstance(c, dict) and str(c.get("id") or "") == rid), None)
    if not hit and cands and isinstance(cands[0], dict):
        hit = cands[0]
    domain = str(bundle.get("workflow_domain") or "")
    stage = str(bundle.get("workflow_stage") or "")
    cand_id = str(hit.get("id") or "") if hit else rid
    rec_state = str(bundle.get("recommendation_state") or "")

    draft_type: Optional[str] = None
    if domain == "training" and stage == "waiting_user" and cand_id in (
        "confirm_training_card",
        "review_then_confirm",
        "draft_training_adjust",
    ):
        draft_type = "draft_training_job"
    elif domain == "prediction" and cand_id == "draft_single_prediction":
        draft_type = "draft_single_prediction"
    elif domain == "prediction" and cand_id == "confirm_batch_run":
        draft_type = "create_prediction_job"
    elif (
        domain == "recommendation"
        and rec_state == "ready_to_run"
        and cand_id == "submit_rec_when_ready"
    ):
        draft_type = "create_recommendation_job"

    can_draft = bool(draft_type) or bool(hit and hit.get("can_draft"))
    if draft_type:
        can_draft = True
    rec["can_draft"] = can_draft
    if draft_type:
        rec["draft_action_type"] = draft_type
    elif hit and hit.get("draft_action_type"):
        rec["draft_action_type"] = str(hit.get("draft_action_type"))
        rec["can_draft"] = True
    bundle["recommended_action"] = rec
    return bundle


def enrich_guidance_bundle_for_storage(bundle: Dict[str, Any], chat_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    attach_fingerprint_to_bundle(bundle, chat_context)
    enrich_recommended_with_draft(bundle)
    return bundle
