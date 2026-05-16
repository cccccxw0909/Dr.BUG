"""Workflow next-step guidance: build deterministic snapshots/candidates before natural-language organization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.agent.chat_output_locale import is_english_output_locale, normalize_chat_output_locale
from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons.zh_typography import ZH_FULLWIDTH_SEMICOLON
from backend.agent.i18n.lexicons.zh_workflow_guidance_phrases import (
    WORKFLOW_DOMAIN_INFERENCE_MSG_MARKER,
    WORKFLOW_DOMAIN_PREDICTION_MSG_MARKER,
    WORKFLOW_DOMAIN_RECOMMENDATION_MSG_MARKERS,
    WORKFLOW_DOMAIN_TRAINING_MSG_MARKER,
)
from backend.agent.concise_progress import _get_focus_task, _resolve_train_task_for_status
from backend.agent.prediction_answerability import (
    in_prediction_like_workspace,
    resolve_current_prediction_followup_state,
    workspace_model_id,
)
from backend.agent.reply_semantics import (
    AgentSemanticPayload,
    build_workflow_guidance_payload,
    clone_workflow_guidance_bundle_for_locale,
    workflow_guidance_english_blocker_message,
    workflow_guidance_english_candidate_title_reason,
    _followup_actions_display_en,
)
from backend.agent.result_presentation import infer_predict_is_batch
from backend.agent.pending_scope import resolve_pending_scope_key
from backend.agent.workflow_guidance_enrich import enrich_guidance_bundle_for_storage
from backend.agent.workflow_guidance_storage import save_last_guidance
from backend.agent.workflow_rules import (
    batch_stage_from_signals,
    build_recommendation_workflow_meta,
    prediction_goal_from_task,
    rules_general_candidates,
    rules_prediction_candidates,
    rules_recommendation_candidates,
    rules_training_candidates,
    training_stage_from_task,
    wants_workflow_guidance_intent,
)
from backend.schemas.agent import ChatTurnRequest
from backend.utils.time_utils import now_iso


def _pick_training_task(task_repo: Any, chat_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    raw = task_repo.list()
    focus = _get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("job_type") or "") == "train_model":
        return focus
    return _resolve_train_task_for_status(task_repo, raw, chat_context)


def _pick_predict_task(task_repo: Any, chat_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    focus = _get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("job_type") or "") == "predict_outcome":
        return focus
    return None


def _pick_recommend_task(task_repo: Any, chat_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    focus = _get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("job_type") or "") == "recommend_regimen":
        return focus
    raw = task_repo.list()
    rows = [t for t in raw if str(t.get("job_type") or "") == "recommend_regimen"]
    if not rows:
        return None
    rows.sort(key=lambda t: str(t.get("created_at") or ""), reverse=True)
    return rows[0]


def resolve_workflow_domain(
    message: str,
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    msg = (message or "").strip()
    focus = _get_focus_task(task_repo, chat_context)

    if focus:
        jt = str(focus.get("job_type") or "")
        if jt == "recommend_regimen":
            return "recommendation", focus
        if jt == "train_model":
            return "training", focus
        if jt == "predict_outcome":
            return "prediction", focus

    if any(k in msg for k in WORKFLOW_DOMAIN_RECOMMENDATION_MSG_MARKERS):
        return "recommendation", None
    if WORKFLOW_DOMAIN_TRAINING_MSG_MARKER in msg and WORKFLOW_DOMAIN_PREDICTION_MSG_MARKER not in msg:
        return "training", _pick_training_task(task_repo, chat_context)
    if WORKFLOW_DOMAIN_PREDICTION_MSG_MARKER in msg or WORKFLOW_DOMAIN_INFERENCE_MSG_MARKER in msg:
        return "prediction", _pick_predict_task(task_repo, chat_context)

    ctx = chat_context or {}
    mode = str(ctx.get("mode") or "").lower()
    # Recommendation pages often carry a selected model; detect before prediction_like to avoid short continuations being misclassified as prediction.
    if mode in ("recommend", "recommendation", "regimen", "rec"):
        return "recommendation", _pick_recommend_task(task_repo, chat_context)

    if in_prediction_like_workspace(ctx):
        return "prediction", _pick_predict_task(task_repo, chat_context)

    if mode in ("train", "training"):
        t = _pick_training_task(task_repo, chat_context)
        if t:
            return "training", t

    t2 = _pick_training_task(task_repo, chat_context)
    if t2 and str(t2.get("status") or "") in ("running", "waiting_user", "queued"):
        return "training", t2

    return "general", None


def build_workflow_snapshot(
    message: str,
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
    *,
    pred_state: str,
) -> Dict[str, Any]:
    domain, anchor_task = resolve_workflow_domain(message, task_repo, chat_context)
    ctx = chat_context or {}

    workflow_goal = "unknown"
    workflow_stage: str = "idle"
    task_row: Optional[Dict[str, Any]] = None

    if domain == "training":
        task_row = anchor_task or _pick_training_task(task_repo, chat_context)
        workflow_goal = "train_model"
        workflow_stage = training_stage_from_task(task_row)
    elif domain == "prediction":
        task_row = anchor_task or _pick_predict_task(task_repo, chat_context)
        wf_kind = str(ctx.get("wf_prediction_kind") or "").strip().lower()
        if wf_kind == "batch":
            workflow_goal = "batch_prediction"
        elif wf_kind == "single":
            workflow_goal = "single_prediction"
        else:
            workflow_goal = prediction_goal_from_task(task_row) if task_row else "unknown"
        if not workspace_model_id(ctx):
            workflow_stage = "configuring"
        elif pred_state == "current_prediction_available":
            workflow_stage = "completed"
        elif task_row and str(task_row.get("status") or "") == "running":
            workflow_stage = "running"
        elif task_row and str(task_row.get("status") or "") == "waiting_user":
            workflow_stage = "waiting_user"
        elif task_row and str(task_row.get("status") or "") == "queued":
            workflow_stage = "ready_to_run"
        elif task_row and str(task_row.get("status") or "") == "completed":
            workflow_stage = "completed"
        elif task_row and str(task_row.get("status") or "") in ("failed", "canceled"):
            workflow_stage = "failed"
        else:
            workflow_stage = "configuring" if workspace_model_id(ctx) else "idle"
    elif domain == "recommendation":
        task_row = anchor_task or _pick_recommend_task(task_repo, chat_context)
        workflow_goal = "regimen_recommendation"
        if task_row:
            st = str(task_row.get("status") or "")
            if st in ("running", "queued"):
                workflow_stage = "running"
            elif st == "completed":
                workflow_stage = "completed"
            elif st in ("failed", "canceled"):
                workflow_stage = "failed"
            else:
                workflow_stage = "ready_to_run"
        else:
            workflow_stage = "configuring"
    else:
        workflow_stage = "idle"

    batch_stage = batch_stage_from_signals(chat_context, task_row)
    ib = infer_predict_is_batch(task_row) if task_row else None
    prediction_is_batch = bool(ib) if ib is not None else (workflow_goal == "batch_prediction")

    snap: Dict[str, Any] = {
        "workflow_domain": domain,
        "workflow_stage": workflow_stage,
        "workflow_goal": workflow_goal,
        "task_id": str(task_row.get("id") or "") if task_row else "",
        "task_status": str(task_row.get("status") or "") if task_row else "",
        "prediction_followup_state": pred_state,
        "workspace_has_model": bool(workspace_model_id(ctx)),
        "batch_stage": batch_stage,
        "prediction_is_batch": prediction_is_batch,
    }
    if domain == "recommendation":
        snap.update(build_recommendation_workflow_meta(task_row, chat_context, pred_state))
    return snap


def resolve_blockers(
    snapshot: Dict[str, Any],
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
    message: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _, blockers, _ = resolve_blockers_and_plan(snapshot, task_repo, chat_context, message=message)
    return blockers


def plan_next_steps(
    snapshot: Dict[str, Any],
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
    message: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    cands, _, rec = resolve_blockers_and_plan(snapshot, task_repo, chat_context, message=message)
    return cands, rec


def resolve_blockers_and_plan(
    snapshot: Dict[str, Any],
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
    message: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    domain = str(snapshot.get("workflow_domain") or "general")
    pred_state = str(snapshot.get("prediction_followup_state") or "")
    has_model = bool(snapshot.get("workspace_has_model"))
    goal = str(snapshot.get("workflow_goal") or "unknown")
    batch_stage = str(snapshot.get("batch_stage") or "unknown")
    tid = str(snapshot.get("task_id") or "").strip()
    task_row = task_repo.get(tid) if tid.startswith("job_") else None

    if domain == "training":
        stage = str(snapshot.get("workflow_stage") or "idle")
        return rules_training_candidates(
            task_row,
            stage=stage,  # type: ignore[arg-type]
            locale=normalize_chat_output_locale(chat_context=chat_context, message=message),
        )
    if domain == "prediction":
        cands, blockers, rec = rules_prediction_candidates(
            pred_state=pred_state,
            has_model=has_model,
            goal=goal,
            batch_stage=batch_stage,
            task=task_row,
            locale=normalize_chat_output_locale(chat_context=chat_context, message=message),
        )
        return cands, blockers, rec
    if domain == "recommendation":
        return rules_recommendation_candidates(
            task=task_row,
            chat_context=chat_context,
            snapshot=snapshot,
            locale=normalize_chat_output_locale(chat_context=chat_context, message=message),
        )
    cands, blockers, rec = rules_general_candidates(
        locale=normalize_chat_output_locale(chat_context=chat_context, message=message),
    )
    return cands, blockers, rec


def _deterministic_summary(
    snapshot: Dict[str, Any],
    blockers: List[Dict[str, Any]],
    recommended: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    *,
    locale: Optional[str] = None,
) -> str:
    dom = str(snapshot.get("workflow_domain") or "general")
    stage = str(snapshot.get("workflow_stage") or "")
    goal = str(snapshot.get("workflow_goal") or "unknown")
    if is_english_output_locale(locale):
        parts: List[str] = [f"Workflow domain: {dom}; stage: {stage}; goal: {goal}."]
        if dom == "recommendation":
            rs = str(snapshot.get("recommendation_state") or "")
            if rs:
                parts.append(f"Recommendation workflow state: {rs}.")
            fa = snapshot.get("followup_actions")
            if isinstance(fa, list) and fa:
                parts.append("Available follow-up actions: " + _followup_actions_display_en(fa) + ".")
        if blockers:
            parts.append(
                "Blocking points: "
                + "; ".join(
                    f"{b.get('code')}:{workflow_guidance_english_blocker_message(str(b.get('code') or ''))}"
                    for b in blockers[:3]
                    if isinstance(b, dict)
                )
                + "."
            )
        rid = str(recommended.get("id") or "")
        hit = next((c for c in candidates if str(c.get("id")) == rid), None)
        if hit and isinstance(hit, dict):
            t_en, r_en = workflow_guidance_english_candidate_title_reason(hit)
            parts.append(f"Preferred next step: {t_en} ({r_en})")
        draft_hint = any(c.get("kind") == "draft" and c.get("can_draft") for c in candidates)
        if draft_hint:
            parts.append(
                "You can describe changes in chat to regenerate a draft, but execution still requires confirmation in the UI."
            )
        return "".join(parts)

    parts_zh: List[str] = [
        chat_msg(locale, "workflow_guidance.summary.header", domain=dom, stage=stage, goal=goal),
    ]
    if dom == "recommendation":
        rs = str(snapshot.get("recommendation_state") or "")
        if rs:
            parts_zh.append(chat_msg(locale, "workflow_guidance.summary.recommendation_state", state=rs))
        fa = snapshot.get("followup_actions")
        if isinstance(fa, list) and fa:
            actions = ",".join(str(x) for x in fa[:8])
            parts_zh.append(chat_msg(locale, "workflow_guidance.summary.followup_actions", actions=actions))
    if blockers:
        blockers_s = ZH_FULLWIDTH_SEMICOLON.join(f"{b.get('code')}:{b.get('message')}" for b in blockers[:3])
        parts_zh.append(chat_msg(locale, "workflow_guidance.summary.blockers", blockers=blockers_s))
    rid = str(recommended.get("id") or "")
    hit = next((c for c in candidates if str(c.get("id")) == rid), None)
    if hit:
        parts_zh.append(
            chat_msg(
                locale,
                "workflow_guidance.summary.preferred_next",
                title=hit.get("title"),
                reason=hit.get("reason"),
            )
        )
    draft_hint = any(c.get("kind") == "draft" and c.get("can_draft") for c in candidates)
    if draft_hint:
        parts_zh.append(chat_msg(locale, "workflow_guidance.summary.draft_hint"))
    return "".join(parts_zh)


def compose_guidance_reply(
    req: ChatTurnRequest,
    task_repo: Any,
    *,
    pred_state: str,
) -> str:
    """Deterministic string join only (fallback when tests or LLM are unavailable; main path uses semantic finalization)."""
    _, _, sem = compose_guidance_reply_bundle(req, task_repo, pred_state=pred_state)
    base = (sem.summary or "").strip()
    if sem.allowed_next_steps:
        base = f"{base} {sem.allowed_next_steps[0]}".strip()
    return base


def compose_guidance_reply_bundle(
    req: ChatTurnRequest,
    task_repo: Any,
    *,
    pred_state: str,
) -> Tuple[Dict[str, Any], Dict[str, Any], AgentSemanticPayload]:
    snap = build_workflow_snapshot(req.message or "", task_repo, req.chat_context, pred_state=pred_state)
    cands, blockers, rec = resolve_blockers_and_plan(
        snap, task_repo, req.chat_context, message=req.message or None
    )
    out = {
        "workflow_domain": snap["workflow_domain"],
        "workflow_stage": snap["workflow_stage"],
        "workflow_goal": snap["workflow_goal"],
        "task_id": str(snap.get("task_id") or ""),
        "batch_stage": str(snap.get("batch_stage") or ""),
        "blocking_reasons": blockers,
        "next_step_candidates": cands,
        "recommended_action": rec,
    }
    for _rk in (
        "recommendation_state",
        "has_bound_prediction_result",
        "enabled_regimen_count",
        "schema_ready",
        "form_ready",
        "focus_recommendation_job_id",
        "last_recommendation_status",
        "followup_actions",
    ):
        if _rk in snap:
            out[_rk] = snap[_rk]
    enrich_guidance_bundle_for_storage(out, req.chat_context)
    loc = normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    verbatim = _deterministic_summary(snap, blockers, rec, cands, locale=loc)
    sem = build_workflow_guidance_payload(
        user_message=req.message or "",
        workflow_bundle=out,
        deterministic_summary=verbatim,
        locale=loc,
    )
    api_bundle = clone_workflow_guidance_bundle_for_locale(out, loc)
    return out, api_bundle, sem


def maybe_workflow_guidance_turn(
    req: ChatTurnRequest,
    task_repo: Any,
    *,
    pred_state: str,
) -> Optional[Dict[str, Any]]:
    if not wants_workflow_guidance_intent(req.message or ""):
        return None
    storage_bundle, api_bundle, sem = compose_guidance_reply_bundle(req, task_repo, pred_state=pred_state)
    scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
    save_last_guidance(
        scope_key,
        {
            "saved_at": now_iso(),
            "bundle": storage_bundle,
            "user_id": req.user_id,
            "session_id": req.session_id,
        },
    )
    return {"semantic": sem, "workflow_guidance": api_bundle}


__all__ = [
    "build_workflow_snapshot",
    "compose_guidance_reply",
    "compose_guidance_reply_bundle",
    "maybe_workflow_guidance_turn",
    "plan_next_steps",
    "resolve_blockers",
    "resolve_blockers_and_plan",
    "resolve_workflow_domain",
    "wants_workflow_guidance_intent",
]
