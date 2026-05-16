"""Workflow next-step suggestions: explicit rule table to avoid piling branches in the orchestrator."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons.zh_workflow_guidance_phrases import (
    DEFINITION_EXCLUDE_SUBSTRINGS,
    WORKFLOW_GUIDANCE_NEXT_STEP_PHRASES,
)
from backend.agent.workflow_context_contract import (
    KEY_WF_REC_ENABLED_REGIMEN_COUNT,
    KEY_WF_REC_FORM_READY,
    KEY_WF_REC_HAS_BOUND_PREDICTION,
    KEY_WF_REC_SCHEMA_READY,
)

NextKind = Literal["guide", "draft", "continue"]
WorkflowDomain = Literal["training", "prediction", "recommendation", "general"]
WorkflowStage = Literal[
    "idle",
    "configuring",
    "waiting_user",
    "ready_to_run",
    "running",
    "completed",
    "failed",
]


def wants_workflow_guidance_intent(message: str) -> bool:
    """
    Detect organizational phrasing like "next step / continue / what should I do".
    Intentionally excludes narrow progress phrasing (e.g. "which step am I on"); those stay in concise_progress.
    """
    m = (message or "").strip()
    if not m or len(m) > 160:
        return False
    low = m.lower()
    if any(p in m for p in DEFINITION_EXCLUDE_SUBSTRINGS):
        return False
    if any(p in m for p in WORKFLOW_GUIDANCE_NEXT_STEP_PHRASES):
        return True
    if re.search(r"\bnext step\b", low):
        return True
    return False


def _ctx_int(chat_context: Optional[Dict[str, Any]], key: str, default: int = 0) -> int:
    ctx = chat_context or {}
    v = ctx.get(key)
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ctx_int_optional(chat_context: Optional[Dict[str, Any]], key: str) -> Optional[int]:
    ctx = chat_context or {}
    if key not in ctx:
        return None
    v = ctx.get(key)
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _ctx_bool(chat_context: Optional[Dict[str, Any]], key: str) -> Optional[bool]:
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


def _ctx_str(chat_context: Optional[Dict[str, Any]], key: str) -> str:
    return str((chat_context or {}).get(key) or "").strip()


def training_stage_from_task(task: Optional[Dict[str, Any]]) -> WorkflowStage:
    if not task:
        return "idle"
    st = str(task.get("status") or "")
    if st == "waiting_user":
        return "waiting_user"
    if st == "queued":
        return "ready_to_run"
    if st == "running":
        return "running"
    if st == "completed":
        return "completed"
    if st in ("failed", "canceled"):
        return "failed"
    return "configuring"


def prediction_goal_from_task(task: Optional[Dict[str, Any]]) -> str:
    if not task or str(task.get("job_type") or "") != "predict_outcome":
        return "unknown"
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    mode = str(params.get("prediction_mode") or params.get("mode") or "").lower()
    if mode == "batch":
        return "batch_prediction"
    if mode == "single":
        return "single_prediction"
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    pt = str(rs.get("prediction_type") or "").lower()
    if pt == "batch":
        return "batch_prediction"
    return "single_prediction"


def batch_stage_from_signals(
    chat_context: Optional[Dict[str, Any]],
    task: Optional[Dict[str, Any]],
) -> str:
    """
    Batch prediction sub-stage (privacy: boolean/enum summary only; does not read uploaded file contents).
    Prefer chat_context['wf_batch_stage'] for tests/integration injection.
    """
    hint = _ctx_str(chat_context, "wf_batch_stage")
    if hint in ("missing_upload", "mapping_incomplete", "ready", "running", "completed"):
        return hint
    if not task or str(task.get("job_type") or "") != "predict_outcome":
        return "unknown"
    if prediction_goal_from_task(task) != "batch_prediction":
        return "unknown"
    st = str(task.get("status") or "")
    stage = str(task.get("current_stage") or "").lower()
    if st == "completed":
        return "completed"
    if st in ("running", "queued"):
        if any(x in stage for x in ("upload", "file", "read")):
            return "missing_upload"
        if any(x in stage for x in ("map", "mapping", "column")):
            return "mapping_incomplete"
        return "running"
    return "ready"


def rules_training_candidates(
    task: Optional[Dict[str, Any]],
    *,
    stage: WorkflowStage,
    locale: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    loc = locale
    blockers: List[Dict[str, Any]] = []
    cands: List[Dict[str, Any]] = []
    if not task:
        blockers.append(
            {"code": "no_training_task", "message": chat_msg(loc, "workflow_rules.training.blocker.no_training_task.message")}
        )
        cands.append(
            {
                "id": "start_or_open_training",
                "title": chat_msg(loc, "workflow_rules.training.candidate.start_or_open_training.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": True,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.start_or_open_training.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "draft_training_explore",
                "title": chat_msg(loc, "workflow_rules.training.candidate.draft_training_explore.title"),
                "kind": "draft",
                "priority": 40,
                "can_draft": True,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.draft_training_explore.reason"),
                "preconditions": [],
            }
        )
        cands.sort(key=lambda x: -int(x.get("priority") or 0))
        top = cands[0]
        return cands, blockers, {"id": str(top.get("id")), "kind": str(top.get("kind"))}

    st = str(task.get("status") or "")
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    wf = str(rs.get("train_workflow_phase") or "")

    if stage == "waiting_user":
        blockers.append(
            {"code": "waiting_confirm", "message": chat_msg(loc, "workflow_rules.training.blocker.waiting_confirm.message")}
        )
        cands.append(
            {
                "id": "confirm_training_card",
                "title": chat_msg(loc, "workflow_rules.training.candidate.confirm_training_card.title"),
                "kind": "continue",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.confirm_training_card.reason"),
                "preconditions": [chat_msg(loc, "workflow_rules.training.precondition.training_confirm_card.label")],
            }
        )
        if wf == "train_phase3_feature_confirm_pending" or "phase3" in wf or "feature" in wf:
            hint = chat_msg(loc, "workflow_rules.training.waiting_hint.feature_confirm")
        elif "phase4" in wf or "train_config" in wf:
            hint = chat_msg(loc, "workflow_rules.training.waiting_hint.train_config")
        elif "phase5" in wf or "publish" in wf:
            hint = chat_msg(loc, "workflow_rules.training.waiting_hint.release")
        else:
            hint = chat_msg(loc, "workflow_rules.training.waiting_hint.generic")
        cands.append(
            {
                "id": "review_then_confirm",
                "title": chat_msg(loc, "workflow_rules.training.candidate.review_then_confirm.title"),
                "kind": "guide",
                "priority": 85,
                "can_draft": False,
                "reason": hint,
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "draft_training_adjust",
                "title": chat_msg(loc, "workflow_rules.training.candidate.draft_training_adjust.title"),
                "kind": "draft",
                "priority": 35,
                "can_draft": True,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.draft_training_adjust.reason"),
                "preconditions": [],
            }
        )
    elif stage == "running":
        blockers.append(
            {"code": "task_running", "message": chat_msg(loc, "workflow_rules.training.blocker.task_running.message")}
        )
        cands.append(
            {
                "id": "wait_train",
                "title": chat_msg(loc, "workflow_rules.training.candidate.wait_train.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.wait_train.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "open_task_detail",
                "title": chat_msg(loc, "workflow_rules.training.candidate.open_task_detail.title"),
                "kind": "guide",
                "priority": 70,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.open_task_detail.reason"),
                "preconditions": [],
            }
        )
    elif stage == "completed":
        blockers.append(
            {"code": "none", "message": chat_msg(loc, "workflow_rules.training.blocker.completed.message")}
        )
        cands.append(
            {
                "id": "review_train_outcome",
                "title": chat_msg(loc, "workflow_rules.training.candidate.review_train_outcome.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.review_train_outcome.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "goto_prediction_or_rec",
                "title": chat_msg(loc, "workflow_rules.training.candidate.goto_prediction_or_rec.title"),
                "kind": "guide",
                "priority": 55,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.goto_prediction_or_rec.reason"),
                "preconditions": [],
            }
        )
    elif stage == "failed":
        err = str(task.get("error_message") or "")[:200]
        msg = chat_msg(loc, "workflow_rules.training.blocker.task_failed.message")
        if err:
            msg += chat_msg(loc, "workflow_rules.training.blocker.task_failed.err_suffix", err=err)
        blockers.append({"code": "task_failed", "message": msg})
        cands.append(
            {
                "id": "inspect_failure_train",
                "title": chat_msg(loc, "workflow_rules.training.candidate.inspect_failure_train.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.inspect_failure_train.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "draft_training_retry",
                "title": chat_msg(loc, "workflow_rules.training.candidate.draft_training_retry.title"),
                "kind": "draft",
                "priority": 50,
                "can_draft": True,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.draft_training_retry.reason"),
                "preconditions": [],
            }
        )
    elif stage == "ready_to_run":
        blockers.append(
            {"code": "queued", "message": chat_msg(loc, "workflow_rules.training.blocker.queued.message")}
        )
        cands.append(
            {
                "id": "wait_queue",
                "title": chat_msg(loc, "workflow_rules.training.candidate.wait_queue.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.wait_queue.reason"),
                "preconditions": [],
            }
        )
    else:
        blockers.append(
            {"code": "unknown_train_state", "message": chat_msg(loc, "workflow_rules.training.blocker.unknown_state.message", st=st)}
        )
        cands.append(
            {
                "id": "open_task_train",
                "title": chat_msg(loc, "workflow_rules.training.candidate.open_task_train.title"),
                "kind": "guide",
                "priority": 80,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.training.candidate.open_task_train.reason"),
                "preconditions": [],
            }
        )

    cands.sort(key=lambda x: -int(x.get("priority") or 0))
    top = cands[0] if cands else {}
    recommended = {"id": str(top.get("id") or "none"), "kind": str(top.get("kind") or "guide")}
    return cands, blockers, recommended


def rules_prediction_candidates(
    *,
    pred_state: str,
    has_model: bool,
    goal: str,
    batch_stage: str,
    task: Optional[Dict[str, Any]],
    locale: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    loc = locale
    blockers: List[Dict[str, Any]] = []
    cands: List[Dict[str, Any]] = []

    if not has_model:
        blockers.append(
            {"code": "missing_model", "message": chat_msg(loc, "workflow_rules.prediction.blocker.missing_model.message")}
        )
        cands.append(
            {
                "id": "pick_model",
                "title": chat_msg(loc, "workflow_rules.prediction.candidate.pick_model.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.prediction.candidate.pick_model.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "open_predict_entry",
                "title": chat_msg(loc, "workflow_rules.prediction.candidate.open_predict_entry.title"),
                "kind": "guide",
                "priority": 70,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.prediction.candidate.open_predict_entry.reason"),
                "preconditions": [],
            }
        )
    elif goal == "batch_prediction":
        if batch_stage == "missing_upload":
            blockers.append(
                {"code": "missing_dataset", "message": chat_msg(loc, "workflow_rules.prediction.blocker.missing_dataset.message")}
            )
            cands.append(
                {
                    "id": "upload_batch_file",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.upload_batch_file.title"),
                    "kind": "guide",
                    "priority": 100,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.upload_batch_file.reason"),
                    "preconditions": [],
                }
            )
        elif batch_stage == "mapping_incomplete":
            blockers.append(
                {
                    "code": "mapping_incomplete",
                    "message": chat_msg(loc, "workflow_rules.prediction.blocker.mapping_incomplete.message"),
                }
            )
            cands.append(
                {
                    "id": "finish_column_mapping",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.finish_column_mapping.title"),
                    "kind": "guide",
                    "priority": 100,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.finish_column_mapping.reason"),
                    "preconditions": [],
                }
            )
        elif batch_stage in ("running",) or (task and str(task.get("status") or "") == "running"):
            blockers.append(
                {"code": "task_running", "message": chat_msg(loc, "workflow_rules.prediction.blocker.task_running.message")}
            )
            cands.append(
                {
                    "id": "wait_batch",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.wait_batch.title"),
                    "kind": "guide",
                    "priority": 100,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.wait_batch.reason"),
                    "preconditions": [],
                }
            )
        elif batch_stage == "completed" or (task and str(task.get("status") or "") == "completed"):
            blockers.append(
                {"code": "none", "message": chat_msg(loc, "workflow_rules.prediction.blocker.batch_completed.message")}
            )
            cands.append(
                {
                    "id": "review_batch_summary",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.review_batch_summary.title"),
                    "kind": "guide",
                    "priority": 100,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.review_batch_summary.reason"),
                    "preconditions": [],
                }
            )
            cands.append(
                {
                    "id": "consider_rec",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.consider_rec.title"),
                    "kind": "guide",
                    "priority": 40,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.consider_rec.reason"),
                    "preconditions": [],
                }
            )
        else:
            blockers.append(
                {"code": "ready_batch", "message": chat_msg(loc, "workflow_rules.prediction.blocker.ready_batch.message")}
            )
            cands.append(
                {
                    "id": "confirm_batch_run",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.confirm_batch_run.title"),
                    "kind": "continue",
                    "priority": 100,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.confirm_batch_run.reason"),
                    "preconditions": [],
                }
            )
            cands.append(
                {
                    "id": "draft_batch_explainer",
                    "title": chat_msg(loc, "workflow_rules.prediction.candidate.draft_batch_explainer.title"),
                    "kind": "guide",
                    "priority": 40,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.prediction.candidate.draft_batch_explainer.reason"),
                    "preconditions": [],
                }
            )
    elif pred_state == "current_prediction_available":
        blockers.append(
            {
                "code": "none",
                "message": chat_msg(loc, "workflow_rules.prediction.blocker.current_prediction_available.message"),
            }
        )
        cands.append(
            {
                "id": "read_prediction_explanation",
                "title": chat_msg(loc, "workflow_rules.prediction.candidate.read_prediction_explanation.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.prediction.candidate.read_prediction_explanation.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "goto_rec_if_needed",
                "title": chat_msg(loc, "workflow_rules.prediction.candidate.goto_rec_if_needed.title"),
                "kind": "guide",
                "priority": 45,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.prediction.candidate.goto_rec_if_needed.reason"),
                "preconditions": [],
            }
        )
    else:
        blockers.append(
            {"code": "no_result_yet", "message": chat_msg(loc, "workflow_rules.prediction.blocker.no_result_yet.message")}
        )
        cands.append(
            {
                "id": "draft_single_prediction",
                "title": chat_msg(loc, "workflow_rules.prediction.candidate.draft_single_prediction.title"),
                "kind": "draft",
                "priority": 100,
                "can_draft": True,
                "reason": chat_msg(loc, "workflow_rules.prediction.candidate.draft_single_prediction.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "fill_single_or_batch",
                "title": chat_msg(loc, "workflow_rules.prediction.candidate.fill_single_or_batch.title"),
                "kind": "guide",
                "priority": 85,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.prediction.candidate.fill_single_or_batch.reason"),
                "preconditions": [],
            }
        )

    cands.sort(key=lambda x: -int(x.get("priority") or 0))
    top = cands[0] if cands else {}
    recommended = {"id": str(top.get("id") or "none"), "kind": str(top.get("kind") or "guide")}
    return cands, blockers, recommended


def build_recommendation_workflow_meta(
    task: Optional[Dict[str, Any]],
    chat_context: Optional[Dict[str, Any]],
    pred_state: str,
) -> Dict[str, Any]:
    """
    Regimen recommendation workflow meta: deterministic state and follow-up action lists (no patient tables, no execution).
    recommendation_state aligns with phase2.3 semantics.
    """
    ctx = chat_context or {}
    reg_n = _ctx_int_optional(ctx, KEY_WF_REC_ENABLED_REGIMEN_COUNT)
    schema_ok = _ctx_bool(ctx, KEY_WF_REC_SCHEMA_READY)
    form_ok = _ctx_bool(ctx, KEY_WF_REC_FORM_READY)

    pre_missing = bool(
        (reg_n is not None and reg_n < 1)
        or (schema_ok is False)
        or (form_ok is False)
    )

    has_bound = _ctx_bool(ctx, KEY_WF_REC_HAS_BOUND_PREDICTION)
    if has_bound is None and str(pred_state or "") == "current_prediction_available":
        has_bound = True
    has_bound_prediction_result = bool(has_bound)

    focus_jid = ""
    last_st = ""
    if task and str(task.get("job_type") or "") == "recommend_regimen":
        focus_jid = str(task.get("id") or "")
        last_st = str(task.get("status") or "")

    recommendation_state: str
    if pre_missing:
        recommendation_state = "precondition_missing"
    elif not task or str(task.get("job_type") or "") != "recommend_regimen":
        recommendation_state = "ready_to_run"
    else:
        st = last_st
        if st == "running":
            recommendation_state = "running"
        elif st == "queued":
            recommendation_state = "queued"
        elif st == "waiting_user":
            recommendation_state = "queued"
        elif st == "completed":
            recommendation_state = "completed"
        elif st in ("failed", "canceled"):
            recommendation_state = "failed"
        else:
            recommendation_state = "queued"

    followup_actions = _recommendation_followup_action_ids(
        recommendation_state=recommendation_state,
        reg_n=reg_n,
        schema_ok=schema_ok,
        form_ok=form_ok,
    )

    return {
        "recommendation_state": recommendation_state,
        "has_bound_prediction_result": has_bound_prediction_result,
        "enabled_regimen_count": reg_n,
        "schema_ready": True if schema_ok is True else (False if schema_ok is False else None),
        "form_ready": True if form_ok is True else (False if form_ok is False else None),
        "focus_recommendation_job_id": focus_jid,
        "last_recommendation_status": last_st,
        "followup_actions": followup_actions,
    }


def _recommendation_followup_action_ids(
    *,
    recommendation_state: str,
    reg_n: Optional[int],
    schema_ok: Optional[bool],
    form_ok: Optional[bool],
) -> List[str]:
    if recommendation_state == "precondition_missing":
        out: List[str] = []
        if reg_n is not None and reg_n < 1:
            out.append("enable_regimens")
        if schema_ok is False:
            out.append("load_rec_schema")
        if form_ok is False:
            out.append("complete_rec_form")
        return out or ["precondition_generic"]
    if recommendation_state == "ready_to_run":
        return [
            "view_ranked_regimens",
            "compare_original_vs_top1",
            "view_explanation",
            "draft_recommendation",
        ]
    if recommendation_state == "queued":
        return ["view_task_status", "wait_for_completion"]
    if recommendation_state == "running":
        return ["view_task_status", "wait_for_completion"]
    if recommendation_state == "completed":
        return [
            "view_ranked_regimens",
            "compare_original_vs_top1",
            "view_explanation",
            "return_to_prediction_or_next_step",
        ]
    if recommendation_state == "failed":
        return ["view_error", "fix_preconditions", "redraft_recommendation_if_applicable"]
    return []


def rules_recommendation_candidates(
    *,
    task: Optional[Dict[str, Any]],
    chat_context: Optional[Dict[str, Any]],
    snapshot: Dict[str, Any],
    locale: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    loc = locale
    blockers: List[Dict[str, Any]] = []
    cands: List[Dict[str, Any]] = []

    rec_state = str(snapshot.get("recommendation_state") or "precondition_missing")
    reg_n = _ctx_int_optional(chat_context, KEY_WF_REC_ENABLED_REGIMEN_COUNT)
    schema_ok = _ctx_bool(chat_context, KEY_WF_REC_SCHEMA_READY)
    form_ok = _ctx_bool(chat_context, KEY_WF_REC_FORM_READY)

    if rec_state == "precondition_missing":
        if reg_n is not None and reg_n < 1:
            blockers.append(
                {"code": "missing_regimens", "message": chat_msg(loc, "workflow_rules.recommendation.blocker.missing_regimens.message")}
            )
            cands.append(
                {
                    "id": "open_regimen_management",
                    "title": chat_msg(loc, "workflow_rules.recommendation.candidate.open_regimen_management.title"),
                    "kind": "guide",
                    "priority": 100,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.open_regimen_management.reason"),
                    "preconditions": [],
                }
            )
        if schema_ok is False:
            blockers.append(
                {"code": "missing_schema", "message": chat_msg(loc, "workflow_rules.recommendation.blocker.missing_schema.message")}
            )
            cands.append(
                {
                    "id": "load_rec_schema",
                    "title": chat_msg(loc, "workflow_rules.recommendation.candidate.load_rec_schema.title"),
                    "kind": "guide",
                    "priority": 95,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.load_rec_schema.reason"),
                    "preconditions": [],
                }
            )
        if form_ok is False:
            blockers.append(
                {
                    "code": "incomplete_features",
                    "message": chat_msg(loc, "workflow_rules.recommendation.blocker.incomplete_features.message"),
                }
            )
            cands.append(
                {
                    "id": "complete_rec_form",
                    "title": chat_msg(loc, "workflow_rules.recommendation.candidate.complete_rec_form.title"),
                    "kind": "guide",
                    "priority": 90,
                    "can_draft": False,
                    "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.complete_rec_form.reason"),
                    "preconditions": [],
                }
            )
    elif rec_state == "ready_to_run":
        blockers.append(
            {"code": "ready_to_run", "message": chat_msg(loc, "workflow_rules.recommendation.blocker.ready_to_run.message")}
        )
        cands.append(
            {
                "id": "submit_rec_when_ready",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.submit_rec_when_ready.title"),
                "kind": "continue",
                "priority": 100,
                "can_draft": True,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.submit_rec_when_ready.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "draft_rec_explore",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.draft_rec_explore.title"),
                "kind": "guide",
                "priority": 45,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.draft_rec_explore.reason"),
                "preconditions": [],
            }
        )
    elif rec_state == "queued":
        blockers.append(
            {"code": "task_queued", "message": chat_msg(loc, "workflow_rules.recommendation.blocker.task_queued.message")}
        )
        cands.append(
            {
                "id": "view_task_status",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.view_task_status.queued.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.view_task_status.queued.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "wait_for_completion",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.wait_for_completion.queued.title"),
                "kind": "guide",
                "priority": 80,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.wait_for_completion.queued.reason"),
                "preconditions": [],
            }
        )
    elif rec_state == "running":
        blockers.append(
            {"code": "task_running", "message": chat_msg(loc, "workflow_rules.recommendation.blocker.task_running.message")}
        )
        cands.append(
            {
                "id": "view_task_status",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.view_task_status.running.title"),
                "kind": "guide",
                "priority": 102,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.view_task_status.running.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "wait_for_completion",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.wait_for_completion.running.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.wait_for_completion.running.reason"),
                "preconditions": [],
            }
        )
    elif rec_state == "completed":
        blockers.append(
            {"code": "none", "message": chat_msg(loc, "workflow_rules.recommendation.blocker.completed.message")}
        )
        cands.append(
            {
                "id": "view_ranked_regimens",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.view_ranked_regimens.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.view_ranked_regimens.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "compare_original_vs_top1",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.compare_original_vs_top1.title"),
                "kind": "guide",
                "priority": 92,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.compare_original_vs_top1.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "view_explanation",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.view_explanation.title"),
                "kind": "guide",
                "priority": 75,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.view_explanation.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "return_to_prediction_or_next_step",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.return_to_prediction_or_next_step.title"),
                "kind": "guide",
                "priority": 50,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.return_to_prediction_or_next_step.reason"),
                "preconditions": [],
            }
        )
    elif rec_state == "failed":
        em = str(task.get("error_message") or "")[:200] if task else ""
        msg = chat_msg(loc, "workflow_rules.recommendation.blocker.task_failed.message")
        if em:
            msg += chat_msg(loc, "workflow_rules.recommendation.blocker.task_failed.err_suffix", em=em)
        blockers.append({"code": "task_failed", "message": msg})
        cands.append(
            {
                "id": "view_error",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.view_error.title"),
                "kind": "guide",
                "priority": 100,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.view_error.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "fix_preconditions",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.fix_preconditions.title"),
                "kind": "guide",
                "priority": 92,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.fix_preconditions.reason"),
                "preconditions": [],
            }
        )
        cands.append(
            {
                "id": "redraft_recommendation_if_applicable",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.redraft_recommendation_if_applicable.title"),
                "kind": "guide",
                "priority": 70,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.redraft_recommendation_if_applicable.reason"),
                "preconditions": [],
            }
        )

    if not cands:
        cands.append(
            {
                "id": "generic_rec",
                "title": chat_msg(loc, "workflow_rules.recommendation.candidate.generic_rec.title"),
                "kind": "guide",
                "priority": 50,
                "can_draft": False,
                "reason": chat_msg(loc, "workflow_rules.recommendation.candidate.generic_rec.reason"),
                "preconditions": [],
            }
        )

    cands.sort(key=lambda x: -int(x.get("priority") or 0))
    top = cands[0] if cands else {}
    recommended = {"id": str(top.get("id") or "none"), "kind": str(top.get("kind") or "guide")}
    return cands, blockers, recommended


def rules_general_candidates(
    *,
    locale: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    loc = locale
    blockers = [
        {
            "code": "insufficient_context",
            "message": chat_msg(loc, "workflow_rules.general.blocker.insufficient_context.message"),
        }
    ]
    cands = [
        {
            "id": "pick_workflow",
            "title": chat_msg(loc, "workflow_rules.general.candidate.pick_workflow.title"),
            "kind": "guide",
            "priority": 80,
            "can_draft": False,
            "reason": chat_msg(loc, "workflow_rules.general.candidate.pick_workflow.reason"),
            "preconditions": [],
        },
        {
            "id": "describe_goal",
            "title": chat_msg(loc, "workflow_rules.general.candidate.describe_goal.title"),
            "kind": "guide",
            "priority": 60,
            "can_draft": False,
            "reason": chat_msg(loc, "workflow_rules.general.candidate.describe_goal.reason"),
            "preconditions": [],
        },
    ]
    recommended = {"id": "pick_workflow", "kind": "guide"}
    return cands, blockers, recommended
