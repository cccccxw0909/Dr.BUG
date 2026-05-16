from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from backend import runtime
from backend.api.request_locale import api_locale_prefers_english, resolve_api_user_locale
from backend.agent.chat_output_locale import infer_batch_hint, is_english_output_locale, normalize_chat_output_locale
from backend.agent.i18n import chat_msg as _orch_msg
from backend.agent.i18n.lexicons.zh_orchestrator_routing import (
    BATCH_ENTRY_PREFIX_ZH,
    EXPLICIT_PREDICTION_SUMMARY_KEYWORDS,
    FALLBACK_CLASSIFIER_HINTS_EN,
    FALLBACK_CLASSIFIER_HINTS_ZH,
    FOCUS_PROBE_PRED_COMPLETION,
    FOCUS_PROBE_PRED_PROGRESS,
    FOCUS_PROBE_TRAIN_COMPLETION,
    FOCUS_PROBE_TRAIN_PROGRESS,
    GENERIC_FOCUS_PROBE,
    GENERIC_STATUS_QUERY_KEYWORDS,
    NEXT_STEP_PREFIX_ZH,
    PREDICTION_ENTRY_OPEN_BATCH_RE,
    READONLY_QUERY_ZH_TO_MSG_KEY,
    RECOMMENDATION_RESULT_NEEDLES,
)
from backend.agent.i18n.lexicons.zh_typography import ZH_IDEOGRAPHIC_COMMA
from backend.agent.payload_schemas import validate_action_payload
from backend.agent.parameter_completion import (
    complete_params,
    enrich_draft_single_prediction_payload,
    prediction_action_missing,
)
from backend.agent.pending_scope import resolve_pending_scope_key
from backend.agent.prompts.agent_instruction import (
    INTERNAL_RULE_LAYER_HEADER,
    build_orchestrator_runtime_agent_instruction,
)
from backend.agent.tool_action_selector import select_tool_or_action
from backend.agent.tool_action_selector_types import SelectorInput
from backend.agent.welcome_policy import build_welcome_context_from_dict, build_welcome_reply
from backend.agent.workflow_context_contract import (
    get_focus_job_id,
    get_mode,
    get_workspace_model_id,
)
from backend.agent.confirmation_state_machine import ConfirmationStateMachine
from backend.agent.training_contract import (
    is_training_payload_complete_for_pending,
    normalize_phase1_training_payload,
    validate_phase1_training_payload_to_dict,
)
from backend.agent.intent_parser import parse_intent
from backend.agent.pending_action_storage import FilePendingActionStorage
from backend.agent.pending_action_registry import PendingActionRegistry
from backend.agent.concise_progress import (
    format_concise_progress_hit,
    resolve_concise_progress_hit,
)
from backend.agent.status_presentation import format_no_active_tasks_reply
from backend.agent.prediction_answerability import (
    completed_workspace_predict_task,
    is_workspace_current_prediction_outcome_followup,
    resolve_current_prediction_followup_state,
    sticky_no_current_prediction_reply,
    targets_model_prediction_target_column_question,
    wants_explicit_global_latest_prediction_query,
    workspace_model_id,
)
from backend.agent.result_presentation import (
    compose_disclaimed_latest_prediction_when_workspace_not_run,
    compose_predict_batch_completed_aggregate_factual,
    compose_predict_single_completed_factual,
    compose_train_completed_standard,
    resolve_latest_prediction_readonly_reply_mode,
    terminal_reply_for_task_and_intent,
)
from backend.agent.reply_composer import compose_agent_reply_with_llm, sanitize_tool_bundles_for_finalization
from backend.agent.response_payloads import (
    build_batch_prediction_result_response_payload,
    build_prediction_failed_response_payload,
    build_prediction_result_response_payload,
    build_recommendation_result_response_payload,
    build_response_payload_from_semantic,
    build_training_completed_response_payload,
    build_training_draft_created_response_payload,
    build_training_failed_response_payload,
    is_llm_polish_answer_type,
    try_build_batch_prediction_completed_bundle_from_task,
    try_build_recommendation_completed_bundle_from_task,
    try_build_single_prediction_execution_bundle_from_task,
    try_build_training_completed_bundle_from_task,
    try_extract_batch_prediction_readonly_success,
    try_extract_single_prediction_readonly_success,
    try_extract_training_completed_readonly_success,
)
from backend.agent.response_verbalizer import verbalize_response
from backend.agent.reply_semantics import (
    AgentSemanticPayload,
    build_cannot_execute_payload,
    build_disclaimed_latest_prediction_payload,
    build_draft_created_payload,
    build_missing_info_payload,
    build_status_payload,
    build_sticky_no_prediction_payload,
    build_terminal_result_payload,
    build_tool_result_payload,
    status_bullets_from_concise_hit,
)
from backend.agent.terminal_result_query import (
    TerminalResultHit,
    classify_terminal_result_intent,
    resolve_terminal_result_when_no_tools,
)
from backend.agent.workflow_guidance import maybe_workflow_guidance_turn
from backend.agent.workflow_continue import maybe_continue_from_guidance_turn
from backend.agent.workflow_guidance_storage import clear_last_guidance
from backend.agent.mcp_adapter import (
    get_current_context_via_mcp,
    get_latest_training_summary_via_mcp,
)
from backend.agent.status_query_router import (
    plan_readonly_tools,
    readonly_query_overrides_action_intent,
)
from backend.agent.tool_executor import run_readonly_plan
from backend.agent.tool_planner import plan_readonly_tools_with_llm
from backend.agent.status_query_classifier import classify_status_query_with_llm
from backend.agent.query_normalization import normalize_query_for_routing
from backend.audit.hooks import audit_event
from backend.config import PENDING_ACTION_DIR
from backend.llm.base import LLMProviderError
from backend.llm.qwen_provider import QwenProvider
from backend.tools.read_only_privacy import task_public_view
from backend.tools.read_only_tools import (
    ReadonlyToolContext,
    friendly_readonly_query_labels,
)
from backend.schemas.agent import ActionConfirmRequest, ChatTurnRequest
from backend.schemas.task import JobType
from backend.tools.mcp_facade import (
    create_prediction_job,
    create_recommendation_job,
    create_report_job,
    create_training_job_from_contract,
)

registry = PendingActionRegistry(storage=FilePendingActionStorage(PENDING_ACTION_DIR))
confirm_sm = ConfirmationStateMachine()
qwen_provider = QwenProvider()


def _orch(locale: Optional[str], key: str, **kwargs: Any) -> str:
    return _orch_msg(locale, key, **kwargs)


def _chat_output_locale(req: ChatTurnRequest) -> str:
    return normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)


def _extract_next_step_from_verbatim(verbatim: Optional[str]) -> Optional[str]:
    t = str(verbatim or "")
    for sep in (NEXT_STEP_PREFIX_ZH, "Next step:"):
        if sep in t:
            return t.split(sep, 1)[1].strip()
    return None


def _compose_fin(
    req: ChatTurnRequest,
    payload: AgentSemanticPayload,
    route_trace: Dict[str, Any],
) -> str:
    """Central finalization exit that records lightweight trace metadata without patient details."""
    bucket = route_trace.setdefault("reply_finalization_trace", [])
    if payload.locale is None:
        payload.locale = _chat_output_locale(req)
    return compose_agent_reply_with_llm(req, payload, qwen_provider, trace_sink=bucket)


def _verbalize_from_semantic(
    req: ChatTurnRequest,
    sem: AgentSemanticPayload,
    route_trace: Dict[str, Any],
    *,
    answer_type: str,
    final_route: str,
    ui_extra: Optional[Dict[str, Any]] = None,
    waiting_user_confirm_hint: bool = False,
) -> str:
    """
    Selector already routed to MCP/workflow chains; deterministic core produced `sem`; this path only finalizes wording.
    """
    payload = build_response_payload_from_semantic(
        sem,
        answer_type=answer_type,
        final_route=final_route,
        ui_payload=ui_extra,
        waiting_user_confirm_hint=waiting_user_confirm_hint,
    )
    payload.trace["verbalization_mode"] = payload.verbalization_mode
    payload.trace["response_payload_type"] = payload.answer_type
    vb = route_trace.setdefault("response_verbalization_trace", [])
    return verbalize_response(payload, qwen_provider, req=req, trace_entries=vb)


def _verbalize_training_draft_created(
    req: ChatTurnRequest,
    sem: AgentSemanticPayload,
    route_trace: Dict[str, Any],
    *,
    can_confirm: bool,
    final_route: str,
    pending_action_id: Optional[str] = None,
    completed_summary: str,
    missing_field_keys: List[str],
    draft_context: str = "standard",
) -> str:
    """Training draft pending path: use ResponsePayload + verbalizer instead of reply finalization LLM."""
    payload = build_training_draft_created_response_payload(
        sem,
        final_route=final_route,
        can_confirm=can_confirm,
        pending_action_id=pending_action_id,
        completed_summary=completed_summary,
        missing_field_keys=list(missing_field_keys),
        draft_context=draft_context,
    )
    payload.trace["verbalization_mode"] = payload.verbalization_mode
    payload.trace["response_payload_type"] = payload.answer_type
    vb = route_trace.setdefault("response_verbalization_trace", [])
    return verbalize_response(payload, qwen_provider, req=req, trace_entries=vb)


def _message_seeks_completed_recommendation_result(message: str) -> bool:
    """Narrow latch: only explicit questions about a finished recommendation task's result summary route to recommendation_result (does not replace workflow navigation)."""
    m = (message or "").strip()
    if not m or len(m) > 240:
        return False
    if any(x in m for x in RECOMMENDATION_RESULT_NEEDLES):
        return True
    low = m.lower()
    needles_en = (
        "recommendation result",
        "result of the recommendation",
        "the recommendation outcome",
        "show me the recommendation",
        "what was recommended",
        "which regimen was recommended",
        "what regimen was recommended",
        "recommended regimen",
        "regimen recommendation result",
        "ranking of regimens",
        "ranked regimens",
        "top regimen",
        "what is the recommendation",
        "summary of the recommendation",
    )
    return any(x in low for x in needles_en)


class AgentFlowError(Exception):
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


def _tool_readonly_user_intent(*, locale: str, with_verbatim_terminal: bool) -> str:
    if is_english_output_locale(locale):
        return (
            "Read-only query: answer the user using the system summary together with tool facts."
            if with_verbatim_terminal
            else "Read-only query: explain the situation from sanitized tool outputs."
        )
    return _orch(
        locale,
        "orchestrator.tool_readonly.with_verbatim" if with_verbatim_terminal else "orchestrator.tool_readonly.without_verbatim",
    )


def _build_chat_system_prompt(req: ChatTurnRequest) -> str:
    ctx = req.chat_context or {}
    mode = str(ctx.get("mode") or "").strip() or "unknown"
    dataset = str(ctx.get("dataset") or "").strip() or "none"
    model = str(ctx.get("model") or "").strip() or "none"
    task_hint = str(ctx.get("model_task_hint") or "").strip()
    loc = _chat_output_locale(req)
    metric_hint = ""
    if task_hint:
        metric_hint = _orch(loc, "orchestrator.chat_system.metric_hint", task_hint=task_hint)
    return _orch(
        loc,
        "orchestrator.chat_system.body",
        mode=mode,
        dataset=dataset,
        model=model,
        metric_hint=metric_hint,
    )


def _compose_chat_system_prompt(req: ChatTurnRequest) -> str:

    return (
        f"{_build_chat_system_prompt(req)}"
        f"{INTERNAL_RULE_LAYER_HEADER}"
        f"{build_orchestrator_runtime_agent_instruction()}"
    )


_PENDING_WELCOME_ACTION_TYPES = frozenset(
    {
        "create_training_job",
        "draft_training_job",
        "create_prediction_job",
        "draft_single_prediction",
        "create_recommendation_job",
        "create_report_job",
        "prediction_entry",
    }
)


def _pending_action_domain_for_welcome(action_type: str, locale: Optional[str]) -> Tuple[str, Optional[str]]:
    """Map PendingAction.action_type to welcome_policy pending_action_type plus its short display label string."""
    at = str(action_type or "").strip()
    label = (
        _orch(locale, f"orchestrator.pending_welcome.{at}")
        if at in _PENDING_WELCOME_ACTION_TYPES
        else None
    )
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


def _welcome_policy_source_dict(req: ChatTurnRequest) -> Dict[str, Any]:

    ctx = dict(req.chat_context or {})
    scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
    pend = registry.get_active_pending_for_scope(scope_key)

    mid = (get_workspace_model_id(ctx) or str(ctx.get("selected_model_id") or ctx.get("workspace_model_id") or "").strip() or None)
    mode_raw = (get_mode(ctx) or str(ctx.get("mode") or "").strip() or "unknown")
    ml = mode_raw.lower()
    if ml in ("prediction", "predict", "predict_outcome"):
        mode_for_welcome = "predict"
    elif ml in ("recommendation", "recommend", "recommend_regimen"):
        mode_for_welcome = "recommend"
    elif ml in ("train", "training"):
        mode_for_welcome = "train"
    elif ml == "home":
        mode_for_welcome = "home"
    else:
        mode_for_welcome = mode_raw

    out: Dict[str, Any] = {
        "is_new_session": bool(ctx.get("is_new_session")),
        "mode": mode_for_welcome,
        "focus_job_id": get_focus_job_id(ctx) or None,
        "selected_model_id": mid,
        "selected_model_display_name": (
            ctx.get("selected_model_display_name")
            or ctx.get("workspace_model_display_name")
            or ctx.get("model_display_name")
        ),
        "locale": ctx.get("locale"),
        "dataset": ctx.get("dataset"),
        "focus_task_status": ctx.get("focus_task_status"),
        "focus_job_type": ctx.get("focus_job_type"),
    }
    if pend is not None:
        loc_w = _chat_output_locale(req)
        ptype, plab = _pending_action_domain_for_welcome(str(pend.action_type), loc_w)
        out["has_pending_action"] = True
        out["pending_action"] = {"type": ptype, "label": plab}
    return out


def _maybe_welcome_policy_turn(req: ChatTurnRequest, route_trace: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    src = _welcome_policy_source_dict(req)
    wctx = build_welcome_context_from_dict(src)
    reply = build_welcome_reply(wctx, req.message)
    if not (reply and str(reply).strip()):
        return None
    route_trace["welcome_policy_hit"] = True
    route_trace["final_route"] = "welcome_policy"
    return {
        "assistant_message": str(reply).strip(),
        "route": "welcome_policy",
        "recognized_action": None,
        "completed_params": {},
        "missing_fields": [],
        "can_confirm": False,
        "pending_confirmation": None,
        "tool_names": [],
        "readonly_query_labels": [],
        "route_decision_trace": route_trace,
    }


def _readonly_mixed_action_hint(req: ChatTurnRequest) -> str:
    loc = normalize_chat_output_locale(chat_context=req.chat_context or {}, message=req.message)
    return _orch(loc, "orchestrator.readonly_mixed_hint")


_FALLBACK_CLASSIFY_CONFIDENCE_THRESHOLD = 0.72
_FALLBACK_WHITELIST_HINTS = FALLBACK_CLASSIFIER_HINTS_ZH + FALLBACK_CLASSIFIER_HINTS_EN


def _should_try_fallback_classifier(message: str) -> bool:
    msg = str(message or "").strip()
    if not msg:
        return False
    if len(msg) > 80:
        return False
    low = msg.lower()
    return any(k in msg or k in low for k in _FALLBACK_WHITELIST_HINTS)


def _explicit_prediction_summary_query(message: str) -> bool:
    msg = str(message or "").strip()
    if not msg:
        return False
    from backend.agent.prediction_followup import is_prediction_combined_followup

    if is_prediction_combined_followup(msg):
        return True
    return any(k in msg for k in EXPLICIT_PREDICTION_SUMMARY_KEYWORDS)


def _generic_status_query_like(message: str) -> bool:
    msg = str(message or "").strip()
    if not msg:
        return False
    return any(k in msg for k in GENERIC_STATUS_QUERY_KEYWORDS)


def _resolve_status_target(chat_context: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    ctx = chat_context or {}
    focus_id = ""
    for k in ("focus_job_id", "current_job_id", "active_job_id", "task_id", "selected_job_id"):
        v = str(ctx.get(k) or "").strip()
        if v.startswith("job_"):
            focus_id = v
            break
    if focus_id:
        task = runtime.task_repo.get(focus_id)
        if task:
            return {
                "resolved_focus_task_id": str(task.get("id") or ""),
                "resolved_focus_task_type": str(task.get("job_type") or ""),
                "resolved_focus_source": "focus",
                "final_status_target_type": str(task.get("job_type") or ""),
                "has_active_or_waiting_task": "true",
            }

    active = [
        t
        for t in runtime.task_repo.list()
        if str(t.get("status") or "") in {"queued", "running", "waiting_user"}
    ]
    if active:
        active.sort(key=lambda t: str(t.get("started_at") or t.get("created_at") or ""), reverse=True)
        pick = active[0]
        return {
            "resolved_focus_task_id": str(pick.get("id") or ""),
            "resolved_focus_task_type": str(pick.get("job_type") or ""),
            "resolved_focus_source": "active",
            "final_status_target_type": str(pick.get("job_type") or ""),
            "has_active_or_waiting_task": "true",
        }

    latest = runtime.task_repo.list()
    if latest:
        pick = latest[0]
        return {
            "resolved_focus_task_id": str(pick.get("id") or ""),
            "resolved_focus_task_type": str(pick.get("job_type") or ""),
            "resolved_focus_source": "latest",
            "final_status_target_type": str(pick.get("job_type") or ""),
            "has_active_or_waiting_task": "false",
        }
    return {
        "resolved_focus_task_id": None,
        "resolved_focus_task_type": None,
        "resolved_focus_source": None,
        "final_status_target_type": None,
        "has_active_or_waiting_task": "false",
    }


def _focus_bound_probe_message(req: ChatTurnRequest, label: str) -> str:
    ctx = req.chat_context or {}
    focus_id = ""
    for k in ("focus_job_id", "current_job_id", "active_job_id", "task_id", "selected_job_id"):
        v = str(ctx.get(k) or "").strip()
        if v.startswith("job_"):
            focus_id = v
            break
    if not focus_id:
        return ""
    task = runtime.task_repo.get(focus_id)
    if not task:
        return ""
    jt = str(task.get("job_type") or "")
    if jt == "train_model":
        return FOCUS_PROBE_TRAIN_COMPLETION if label == "status_query_completion" else FOCUS_PROBE_TRAIN_PROGRESS
    if jt == "predict_outcome":
        return FOCUS_PROBE_PRED_COMPLETION if label == "status_query_completion" else FOCUS_PROBE_PRED_PROGRESS
    return ""


def _merge_dataset_from_chat_context(
    payload: Dict[str, Any],
    chat_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Inject dataset_id from chat_context (`id|name` only); never touches patient tables."""
    if not chat_context or payload.get("dataset_id"):
        return payload
    ds = str(chat_context.get("dataset") or "").strip()
    if "|" not in ds:
        return payload
    did = ds.split("|", 1)[0].strip()
    if did.startswith("ds_"):
        return {**payload, "dataset_id": did}
    return payload


def _merge_model_from_chat_context(
    payload: Dict[str, Any],
    chat_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Inject model_id summary from chat_context only; does not read patient features."""
    if not chat_context or (payload.get("model_id") or "").strip():
        return payload
    mid = str(chat_context.get("model") or "").strip()
    if mid:
        return {**payload, "model_id": mid}
    return payload


_TRAINING_ACTION_TYPES = frozenset({"create_training_job", "draft_training_job"})
_PREDICTIONISH_ACTION_TYPES = frozenset(
    {"create_prediction_job", "draft_single_prediction", "create_recommendation_job"}
)


def _prediction_entry_open_batch(message: str) -> bool:
    m = (message or "").strip()
    if not m:
        return False
    if m.startswith(BATCH_ENTRY_PREFIX_ZH):
        return True
    return bool(PREDICTION_ENTRY_OPEN_BATCH_RE.search(m))

_ACTION_TITLE_KEY: Dict[str, str] = {
    "create_training_job": "orchestrator.user_action_title.create_training_job",
    "draft_training_job": "orchestrator.user_action_title.draft_training_job",
    "create_prediction_job": "orchestrator.user_action_title.create_prediction_job",
    "draft_single_prediction": "orchestrator.user_action_title.draft_single_prediction",
    "create_recommendation_job": "orchestrator.user_action_title.create_recommendation_job",
    "create_report_job": "orchestrator.user_action_title.create_report_job",
}

_TRAINING_FIELD_KEYS: Tuple[str, ...] = (
    "dataset_id",
    "clinical_task_id",
    "ml_task_type",
    "target_column",
    "selected_features",
    "final_features",
    "med_cols",
    "model_type",
    "model_name",
    "feature_set",
    "objective_metric",
    "publish_overrides",
)

_PRED_DRAFT_FIELD_KEYS: Tuple[str, ...] = ("model_id", "patient_features", "prediction_mode", "task_name")


def _training_field_label_map(locale: Optional[str]) -> Dict[str, str]:
    return {k: _orch(locale, f"orchestrator.field.training.{k}") for k in _TRAINING_FIELD_KEYS}


def _prediction_field_label_map(locale: Optional[str]) -> Dict[str, str]:
    return {k: _orch(locale, f"orchestrator.field.prediction.{k}") for k in _PRED_DRAFT_FIELD_KEYS}


def _user_action_title_en(action_type: str) -> str:
    at = str(action_type or "").strip()
    key = _ACTION_TITLE_KEY.get(at, "orchestrator.user_action_title.default")
    return _orch("en", key)


def _user_action_title(action_type: str) -> str:
    at = str(action_type or "").strip()
    key = _ACTION_TITLE_KEY.get(at, "orchestrator.user_action_title.default")
    return _orch("zh", key)


def _user_action_title_for_locale(action_type: str, locale: Optional[str]) -> str:
    at = str(action_type or "").strip()
    key = _ACTION_TITLE_KEY.get(at, "orchestrator.user_action_title.default")
    return _orch(locale, key)


def _training_user_title_for_locale(action_type: str, locale: Optional[str]) -> str:
    return _orch(locale, "orchestrator.training_user_title")


def _field_labels_for_locale(missing: List[str], training: bool, locale: Optional[str]) -> List[str]:
    m = _training_field_label_map(locale) if training else _prediction_field_label_map(locale)
    return [m.get(str(x), str(x)) for x in missing]


def _training_missing_labels(missing: List[str], locale: Optional[str]) -> List[str]:
    return _field_labels_for_locale(missing, True, locale)


def _prediction_missing_labels(missing: List[str], locale: Optional[str]) -> List[str]:
    return _field_labels_for_locale(missing, False, locale)


def _missing_field_labels_for_action(action_type: str, missing: List[str], locale: Optional[str]) -> List[str]:
    if action_type in _TRAINING_ACTION_TYPES:
        return _training_missing_labels(missing, locale)
    if action_type in {"draft_single_prediction", "create_prediction_job"}:
        return _prediction_missing_labels(missing, locale)
    return [str(x) for x in missing]


def _join_missing_labels_for_action(action_type: str, missing: List[str], locale: Optional[str]) -> str:
    labels = _missing_field_labels_for_action(action_type, missing, locale)
    if labels:
        return ", ".join(labels) if is_english_output_locale(locale) else ZH_IDEOGRAPHIC_COMMA.join(labels)
    return _orch(locale, "orchestrator.missing_fields_contract_placeholder")


def _readonly_query_labels_for_locale(labels: List[str], locale: Optional[str]) -> List[str]:
    if not is_english_output_locale(locale):
        return labels
    out: List[str] = []
    for label in labels:
        mk = READONLY_QUERY_ZH_TO_MSG_KEY.get(label)
        out.append(_orch("en", mk) if mk else label)
    return out


def _deterministic_prediction_readonly_combo_reply(
    planned: List[Tuple[str, Dict[str, Any]]],
    tool_results: List[Dict[str, Any]],
    *,
    locale: Optional[str] = None,
) -> Optional[str]:
    """Result+explanation combo: fixed order summary→explanation via templates; must not hand off to free-form LLM."""
    if len(planned) != 2 or len(tool_results) != 2:
        return None
    if planned[0][0] != "get_latest_prediction_summary" or planned[1][0] != "get_prediction_explanation_summary":
        return None
    if any(b.get("ok") is not True for b in tool_results):
        return None
    inner0 = tool_results[0].get("result") or {}
    # history / none: skip deterministic combo blocks to avoid colliding with task-bound terminal semantics (see resolve_latest_prediction_readonly_reply_mode)
    if resolve_latest_prediction_readonly_reply_mode(inner0) != "task_deterministic":
        return None
    pred = inner0.get("prediction")
    exb = (tool_results[1].get("result") or {}).get("explanation")
    eff_loc = "en" if locale is None else locale
    if not isinstance(pred, dict):
        return _orch(eff_loc, "orchestrator.pred_readonly.no_recent")
    lines: List[str] = []
    k = str(pred.get("kind") or "")
    if k == "batch":
        lines.append(
            _orch(
                eff_loc,
                "orchestrator.pred_readonly.batch_first_line",
                task=pred.get("task_name") or "—",
                model=pred.get("model_name") or "—",
                tr=pred.get("total_rows", "—"),
                sr=pred.get("succeeded_rows", "—"),
                fr=pred.get("failed_rows", "—"),
                summary=pred.get("summary_text") or "",
            ).strip()
        )
    else:
        prob = pred.get("predicted_probability")
        ptxt = f"{float(prob) * 100:.1f}%" if isinstance(prob, (int, float)) else "—"
        summ = pred.get("summary_text") or _orch(eff_loc, "orchestrator.pred_readonly.summary_none")
        lines.append(
            _orch(
                eff_loc,
                "orchestrator.pred_readonly.single_first_line",
                task=pred.get("task_name") or "—",
                model=pred.get("model_name") or "—",
                label=pred.get("predicted_label") or "—",
                prob=ptxt,
                summary=summ,
            ).strip()
        )
    if not isinstance(exb, dict):
        lines.append(_orch(eff_loc, "orchestrator.pred_readonly.explain_none"))
    elif k == "batch" or not exb.get("explanation_available"):
        lines.append(_orch(eff_loc, "orchestrator.pred_readonly.explain_batch_no_shap"))
    else:
        etxt = exb.get("explanation_summary_text") or "—"
        lines.append(_orch(eff_loc, "orchestrator.pred_readonly.explain_line", text=etxt))
    return "\n".join(lines)


def _task_backed_failure_assistant_message(
    task: Dict[str, Any],
    *,
    object_kind: str,
    intent: str,
    batch_hint: bool,
    final_route: str,
    payload_source: str,
    req: ChatTurnRequest,
    llm_provider: Any,
    route_decision_trace: Optional[Dict[str, Any]],
) -> str:
    """task-backed failed → ResponsePayload → verbalize_response (strict; no LLM polish)."""
    loc = normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    if object_kind == "train":
        payload = build_training_failed_response_payload(
            task,
            intent=intent,
            final_route=final_route,
            payload_source=payload_source,
            locale=loc,
        )
    else:
        payload = build_prediction_failed_response_payload(
            task,
            intent=intent,
            final_route=final_route,
            payload_source=payload_source,
            locale=loc,
        )
    vb: Optional[List[Dict[str, Any]]] = None
    if route_decision_trace is not None:
        vb = route_decision_trace.setdefault("response_verbalization_trace", [])
    return verbalize_response(payload, llm_provider, req=req, trace_entries=vb)


def _deterministic_terminal_readonly_reply(
    message: str,
    planned: List[Tuple[str, Dict[str, Any]]],
    tool_results: List[Dict[str, Any]],
    task_repo: Any,
    *,
    req: Optional[ChatTurnRequest] = None,
    llm_provider: Any = None,
    route_decision_trace: Optional[Dict[str, Any]] = None,
) -> Optional[str]:

    if req is not None:
        loc_ro = normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    else:
        try:
            loc_ro = normalize_chat_output_locale(chat_context=None, message=message)
        except Exception:
            loc_ro = "en"
    combo = _deterministic_prediction_readonly_combo_reply(planned, tool_results, locale=loc_ro)
    if combo is not None:
        return combo
    if len(planned) != 1:
        return None
    name = str(planned[0][0] or "")
    bundle = tool_results[0] if tool_results else {}
    if bundle.get("ok") is not True:
        return None
    inner = bundle.get("result") or {}
    intent = classify_terminal_result_intent(message) or "default"
    batch_hint = infer_batch_hint(message or "", loc_ro)

    if name == "get_latest_training_summary":
        tpub = inner.get("task")
        if not isinstance(tpub, dict):
            return None
        jid = str(tpub.get("id") or "").strip()
        if not jid.startswith("job_"):
            return None
        full = task_repo.get(jid)
        if not full:
            return None
        st = str(full.get("status") or "")
        if st not in ("completed", "failed", "canceled"):
            return None
        if st == "failed":
            faux_req = req or ChatTurnRequest(message=message or "", user_id="anonymous")
            faux_llm = llm_provider if llm_provider is not None else object()
            return _task_backed_failure_assistant_message(
                full,
                object_kind="train",
                intent=intent,
                batch_hint=False,
                final_route="tool_query",
                payload_source="readonly_get_latest_training_summary_failed",
                req=faux_req,
                llm_provider=faux_llm,
                route_decision_trace=route_decision_trace,
            )
        return terminal_reply_for_task_and_intent(full, "train", intent, batch_hint=False, locale=loc_ro)

    if name == "get_latest_prediction_summary":
        if resolve_latest_prediction_readonly_reply_mode(inner) != "task_deterministic":
            return None
        pred = inner.get("prediction")
        if not isinstance(pred, dict):
            return None
        jid = str(pred.get("job_id") or "").strip()
        if not jid.startswith("job_"):
            return None
        full = task_repo.get(jid)
        if not full:
            return None
        st = str(full.get("status") or "")
        if st not in ("completed", "failed", "canceled"):
            return None
        if st == "failed":
            faux_req = req or ChatTurnRequest(message=message or "", user_id="anonymous")
            faux_llm = llm_provider if llm_provider is not None else object()
            return _task_backed_failure_assistant_message(
                full,
                object_kind="predict",
                intent=intent,
                batch_hint=batch_hint,
                final_route="tool_query",
                payload_source="readonly_get_latest_prediction_summary_failed",
                req=faux_req,
                llm_provider=faux_llm,
                route_decision_trace=route_decision_trace,
            )
        return terminal_reply_for_task_and_intent(full, "predict", intent, batch_hint=batch_hint, locale=loc_ro)

    if name == "get_latest_failure":
        fail = inner.get("failure")
        if not fail:
            return None
        jid = str(fail.get("id") or "").strip()
        if not jid.startswith("job_"):
            return None
        full = task_repo.get(jid)
        if not full:
            return None
        jt = str(full.get("job_type") or "")
        st = str(full.get("status") or "")
        if st not in ("failed", "canceled"):
            return None
        if st == "failed":
            faux_req = req or ChatTurnRequest(message=message or "", user_id="anonymous")
            faux_llm = llm_provider if llm_provider is not None else object()
            if jt == JobType.train_model.value:
                return _task_backed_failure_assistant_message(
                    full,
                    object_kind="train",
                    intent=intent,
                    batch_hint=False,
                    final_route="tool_query",
                    payload_source="readonly_get_latest_failure_train_failed",
                    req=faux_req,
                    llm_provider=faux_llm,
                    route_decision_trace=route_decision_trace,
                )
            if jt == JobType.predict_outcome.value:
                return _task_backed_failure_assistant_message(
                    full,
                    object_kind="predict",
                    intent=intent,
                    batch_hint=batch_hint,
                    final_route="tool_query",
                    payload_source="readonly_get_latest_failure_prediction_failed",
                    req=faux_req,
                    llm_provider=faux_llm,
                    route_decision_trace=route_decision_trace,
                )
            return None
        if jt == JobType.train_model.value:
            return terminal_reply_for_task_and_intent(full, "train", intent, batch_hint=False, locale=loc_ro)
        if jt == JobType.predict_outcome.value:
            return terminal_reply_for_task_and_intent(
                full, "predict", intent, batch_hint=batch_hint, locale=loc_ro
            )
        return None

    return None


def _run_readonly_tool_plan(
    req: ChatTurnRequest,
    planned: List[Tuple[str, Dict[str, Any]]],
    *,
    mixed_action_intent: bool = False,
    llm_provider: QwenProvider,
    trace_sink: Optional[List[Dict[str, Any]]] = None,
    route_decision_trace: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from backend.agent.reply_composer import sanitize_tool_bundles_for_finalization

    ctx = ReadonlyToolContext(
        chat_context=dict(req.chat_context or {}),
        user_id=str(req.user_id or "anonymous"),
        task_repo=runtime.task_repo,
    )
    tool_names, tool_results = run_readonly_plan(planned, ctx)
    tools_all_ok = all(x.get("ok") is True for x in tool_results)
    audit_event(
        "readonly_tools_invoked",
        {
            "user_id": req.user_id,
            "message_preview": (req.message or "")[:500],
            "tools": list(tool_names),
            "tools_all_ok": tools_all_ok,
        },
    )
    msg = str(req.message or "")
    loc_disc = _chat_output_locale(req)
    st = resolve_current_prediction_followup_state(ctx.task_repo, ctx.chat_context)
    explicit_latest_not_run = (
        st == "current_prediction_not_run"
        and wants_explicit_global_latest_prediction_query(msg)
        and any(str(name) == "get_latest_prediction_summary" for name, _ in planned)
    )
    sanitized_bundles = sanitize_tool_bundles_for_finalization(tool_results)
    labels = _readonly_query_labels_for_locale(friendly_readonly_query_labels(planned), loc_disc)
    verbatim: Optional[str] = None
    sem: AgentSemanticPayload

    # Explicit global latest with no bindable workbench result: prefer disclaimer; block deterministic "current task already finished" tone.
    if explicit_latest_not_run and len(planned) == 1 and str(planned[0][0]) == "get_latest_prediction_summary":
        inner = tool_results[0].get("result") if tool_results and tool_results[0].get("ok") is True else {}
        inner_d = inner if isinstance(inner, dict) else {}
        verbatim = compose_disclaimed_latest_prediction_when_workspace_not_run(
            inner_d,
            workspace_model_id=workspace_model_id(ctx.chat_context),
            locale=loc_disc,
        )
        sem = build_disclaimed_latest_prediction_payload(
            user_message=msg,
            fallback_deterministic_reply=verbatim,
            locale=loc_disc,
        )
    else:
        det = None if explicit_latest_not_run else _deterministic_terminal_readonly_reply(
            msg,
            planned,
            tool_results,
            ctx.task_repo,
            req=req,
            llm_provider=llm_provider,
            route_decision_trace=route_decision_trace,
        )
        if det is not None:
            verbatim = det
        if (
            len(planned) == 1
            and str(planned[0][0]) == "get_latest_prediction_summary"
            and len(tool_results) == 1
            and tool_results[0].get("ok") is True
        ):
            inner = tool_results[0].get("result") or {}
            if st == "current_prediction_not_run" and wants_explicit_global_latest_prediction_query(msg):
                verbatim = compose_disclaimed_latest_prediction_when_workspace_not_run(
                    inner,
                    workspace_model_id=workspace_model_id(ctx.chat_context),
                    locale=loc_disc,
                )
            elif st == "current_prediction_available" and not wants_explicit_global_latest_prediction_query(msg):
                ft = completed_workspace_predict_task(ctx.task_repo, ctx.chat_context)
                pred = inner.get("prediction") if isinstance(inner.get("prediction"), dict) else {}
                inner_jid = str(pred.get("job_id") or "").strip() if isinstance(pred, dict) else ""
                ft_id = str((ft or {}).get("id") or "").strip()
                mode_inner = resolve_latest_prediction_readonly_reply_mode(inner)
                if ft and ft_id and (inner_jid != ft_id or mode_inner != "task_deterministic"):
                    intent = classify_terminal_result_intent(msg) or "default"
                    loc_ft = _chat_output_locale(req)
                    batch_hint = infer_batch_hint(msg, loc_ft)
                    verbatim = terminal_reply_for_task_and_intent(
                        ft, "predict", intent, batch_hint=batch_hint, locale=loc_ft
                    )
        if verbatim:
            # Terminal-bound reply: facts stay strict, but long templates are not the sole input; allowed lines + tool facts co-drive wording.
            sem = build_tool_result_payload(
                user_message=msg,
                user_intent=_tool_readonly_user_intent(locale=loc_disc, with_verbatim_terminal=True),
                tool_names=tool_names,
                readonly_query_labels=labels,
                sanitized_tool_bundles=sanitized_bundles,
                verbatim_reply_to_paraphrase=verbatim,
                verbatim_policy="allowed",
                mixed_action_note=False,
                locale=loc_disc,
            )
        else:
            sem = build_tool_result_payload(
                user_message=msg,
                user_intent=_tool_readonly_user_intent(locale=loc_disc, with_verbatim_terminal=False),
                tool_names=tool_names,
                readonly_query_labels=labels,
                sanitized_tool_bundles=sanitized_bundles,
                verbatim_reply_to_paraphrase=None,
                verbatim_policy="forbidden",
                mixed_action_note=False,
                locale=loc_disc,
            )
    sem.tool_fact_bundles = sanitized_bundles

    batch_bundle_ro = (
        None
        if explicit_latest_not_run
        else try_extract_batch_prediction_readonly_success(planned, tool_results, ctx.task_repo)
    )
    pred_bundle = (
        None
        if explicit_latest_not_run
        else try_extract_single_prediction_readonly_success(planned, tool_results, ctx.task_repo)
    )
    train_bundle_ro = (
        None
        if explicit_latest_not_run
        else try_extract_training_completed_readonly_success(planned, tool_results, ctx.task_repo)
    )
    vb_out_locale = _chat_output_locale(req)
    if batch_bundle_ro:
        tv = str(verbatim or "")
        na_tv = _extract_next_step_from_verbatim(tv)
        if na_tv:
            batch_bundle_ro["next_action"] = na_tv
        jid_b = str(batch_bundle_ro.get("job_id") or "").strip()
        full_b = ctx.task_repo.get(jid_b) if jid_b.startswith("job_") else None
        if isinstance(full_b, dict):
            batch_bundle_ro["semantic_summary"] = compose_predict_batch_completed_aggregate_factual(
                full_b, vb_out_locale
            )
        payload_bb = build_batch_prediction_result_response_payload(
            batch_bundle_ro,
            final_route="tool_query",
            payload_source="batch_prediction_readonly_summary",
            locale=vb_out_locale,
        )
        vb = (
            route_decision_trace.setdefault("response_verbalization_trace", [])
            if route_decision_trace is not None
            else None
        )
        reply = verbalize_response(payload_bb, llm_provider, req=req, trace_entries=vb)
        if trace_sink is not None:
            trace_sink.append(
                {
                    "mode": sem.mode,
                    "batch_prediction_result_verbalization": True,
                    "answer_type": "batch_prediction_result",
                    "verbatim_policy": sem.verbatim_policy,
                    "used_tool_fact_bundles": bool(sanitized_bundles),
                    "assistant_message_via": "response_verbalizer",
                }
            )
    elif pred_bundle and is_llm_polish_answer_type("prediction_result"):
        # Selector / readonly plan is fixed; prediction factual core is already in tool results; hand only single-sample success to verbalizer polish.
        payload_pb = build_prediction_result_response_payload(
            pred_bundle, final_route="tool_query", locale=vb_out_locale
        )
        vb = (
            route_decision_trace.setdefault("response_verbalization_trace", [])
            if route_decision_trace is not None
            else None
        )
        reply = verbalize_response(payload_pb, llm_provider, req=req, trace_entries=vb)
        if trace_sink is not None:
            trace_sink.append(
                {
                    "mode": sem.mode,
                    "prediction_result_verbalization": True,
                    "answer_type": "prediction_result",
                    "verbatim_policy": sem.verbatim_policy,
                    "used_tool_fact_bundles": bool(sanitized_bundles),
                    "assistant_message_via": "response_verbalizer",
                }
            )
    elif train_bundle_ro and is_llm_polish_answer_type("training_completed"):
        # Read-only summary tool is bound to a concrete train row; training deterministic core lives in task results; this branch only phrases training_completed.
        tv = str(verbatim or "")
        na_tr = _extract_next_step_from_verbatim(tv)
        if na_tr:
            train_bundle_ro["next_action"] = na_tr
        tid_fix = str(train_bundle_ro.get("job_id") or "").strip()
        full_t = ctx.task_repo.get(tid_fix) if tid_fix.startswith("job_") else None
        if isinstance(full_t, dict):
            train_bundle_ro["semantic_summary"] = compose_train_completed_standard(full_t, vb_out_locale)
        payload_tb = build_training_completed_response_payload(
            train_bundle_ro,
            final_route="tool_query",
            payload_source="training_completed_readonly_summary",
            locale=vb_out_locale,
        )
        vb = (
            route_decision_trace.setdefault("response_verbalization_trace", [])
            if route_decision_trace is not None
            else None
        )
        reply = verbalize_response(payload_tb, llm_provider, req=req, trace_entries=vb)
        if trace_sink is not None:
            trace_sink.append(
                {
                    "mode": sem.mode,
                    "training_completed_verbalization": True,
                    "answer_type": "training_completed",
                    "verbatim_policy": sem.verbatim_policy,
                    "used_tool_fact_bundles": bool(sanitized_bundles),
                    "assistant_message_via": "response_verbalizer",
                }
            )
    else:
        reply = compose_agent_reply_with_llm(req, sem, llm_provider, trace_sink=trace_sink)
    if mixed_action_intent:
        reply = f"{reply.rstrip()}{_readonly_mixed_action_hint(req)}"
    return {
        "assistant_message": reply,
        "route": "tool_query",
        "recognized_action": None,
        "completed_params": {},
        "missing_fields": [],
        "can_confirm": False,
        "pending_confirmation": None,
        "tool_names": tool_names,
        "readonly_query_labels": labels,
    }


def _finalize_pending_action_from_handoff(
    req: ChatTurnRequest,
    action_type: str,
    payload: Dict[str, Any],
    route_trace: Dict[str, Any],
) -> Dict[str, Any]:
    """Continue-from-guidance handoff: payload assembled by rules; enter the same pending main chain as parse_intent."""
    if not str(action_type or "").strip():
        raise AgentFlowError(
            _orch(_chat_output_locale(req), "orchestrator.continue_handoff.missing_action_type"),
            "CONTINUE_HANDOFF_INVALID",
        )
    route_trace["continue_from_guidance"] = True
    route_trace["final_route"] = "deterministic_action"
    payload = dict(payload or {})
    completed = [k for k, v in payload.items() if v not in (None, "", [], {})]

    if action_type in _PREDICTIONISH_ACTION_TYPES:
        if action_type != "draft_single_prediction":
            payload = _merge_model_from_chat_context(payload, req.chat_context)
        if req.client_completed_params:
            payload = {**payload, **req.client_completed_params}
        pf = payload.get("patient_features")
        if not isinstance(pf, dict):
            payload["patient_features"] = {}
        if action_type == "draft_single_prediction":
            payload = enrich_draft_single_prediction_payload(payload)
            payload = validate_action_payload("draft_single_prediction", payload)
            missing = prediction_action_missing(action_type, payload)
        else:
            missing = prediction_action_missing(action_type, payload)

    elif action_type in ("create_training_job", "draft_training_job"):
        payload = _merge_dataset_from_chat_context(payload, req.chat_context)
        if req.client_completed_params:
            payload = {**payload, **req.client_completed_params}
        ok, pend_errors = is_training_payload_complete_for_pending(payload)
        missing = pend_errors if not ok else []
        if ok:
            payload = validate_phase1_training_payload_to_dict(payload)
        else:
            payload = normalize_phase1_training_payload(payload)
    else:
        missing = []

    needs_confirm = confirm_sm.requires_confirmation(action_type)
    can_confirm = needs_confirm and len(missing) == 0

    if not needs_confirm:
        loc_act = _chat_output_locale(req)
        sem_ce = build_cannot_execute_payload(
            user_message=req.message or "",
            action_title=_user_action_title_for_locale(action_type, loc_act),
            reason="This action type cannot be handed off through chat confirmation.",
            missing_fields_zh=None,
            locale=loc_act,
        )
        assistant_message = _compose_fin(req, sem_ce, route_trace)
        return {
            "assistant_message": assistant_message,
            "route": "deterministic_action",
            "recognized_action": action_type,
            "completed_params": payload,
            "missing_fields": missing,
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
    pending = registry.create(action_type=action_type, payload=payload, scope_key=scope_key)
    clear_last_guidance(scope_key)
    audit_event(
        "pending_action_created",
        {
            "action_type": action_type,
            "pending_action_id": pending.pending_action_id,
            "user_id": req.user_id,
            "scope_key": scope_key,
            "source": "continue_from_workflow_guidance",
        },
    )
    loc_act = _chat_output_locale(req)
    completed_summary = ", ".join(completed[:12]) if completed else _orch(loc_act, "orchestrator.continue.completed_summary_carryover")
    pending_preview = _orch(loc_act, "orchestrator.continue.pending_preview_workflow")
    if action_type == "draft_single_prediction" and missing:
        miss_labels = _prediction_missing_labels(missing, loc_act)
        sem_act = build_missing_info_payload(
            user_message=req.message or "",
            action_title=_user_action_title_for_locale(action_type, loc_act),
            missing_fields_zh=miss_labels,
            context_note=_orch(loc_act, "orchestrator.context_note.single_prediction_form"),
            locale=loc_act,
        )
        assistant_message = _compose_fin(req, sem_act, route_trace)
    elif action_type in _TRAINING_ACTION_TYPES:
        miss_labels = _training_missing_labels(missing, loc_act)
        sem_act = build_draft_created_payload(
            user_message=req.message or "",
            action_title=_training_user_title_for_locale(action_type, loc_act),
            can_confirm=can_confirm,
            missing_fields_zh=miss_labels,
            completed_summary=completed_summary,
            pending_action_preview=pending_preview,
            locale=loc_act,
        )
        assistant_message = _verbalize_training_draft_created(
            req,
            sem_act,
            route_trace,
            can_confirm=can_confirm,
            final_route="deterministic_action",
            pending_action_id=pending.pending_action_id,
            completed_summary=completed_summary,
            missing_field_keys=list(missing),
            draft_context="workflow_continue",
        )
    elif action_type == "draft_single_prediction":
        sem_act = build_draft_created_payload(
            user_message=req.message or "",
            action_title=_user_action_title_for_locale(action_type, loc_act),
            can_confirm=can_confirm,
            missing_fields_zh=[],
            completed_summary=completed_summary,
            pending_action_preview=pending_preview,
            locale=loc_act,
        )
        assistant_message = _compose_fin(req, sem_act, route_trace)
    else:
        title = _user_action_title_for_locale(action_type, loc_act)
        miss_other = [str(x) for x in missing] if missing else []
        sem_act = build_draft_created_payload(
            user_message=req.message or "",
            action_title=title,
            can_confirm=can_confirm,
            missing_fields_zh=miss_other,
            completed_summary=completed_summary,
            pending_action_preview=pending_preview,
            locale=loc_act,
        )
        assistant_message = _compose_fin(req, sem_act, route_trace)

    return {
        "assistant_message": assistant_message,
        "route": "deterministic_action",
        "recognized_action": action_type,
        "completed_params": payload,
        "missing_fields": missing,
        "can_confirm": can_confirm,
        "pending_confirmation": pending.model_dump(mode="json"),
        "tool_names": [],
        "readonly_query_labels": [],
        "route_decision_trace": {**route_trace, "final_route": "deterministic_action"},
    }


def _focus_task_status_for_selector(route_trace: Dict[str, Any]) -> Optional[str]:
    tid = route_trace.get("resolved_focus_task_id")
    if not tid:
        return None
    row = runtime.task_repo.get(str(tid))
    if not row:
        return None
    st = str(row.get("status") or "").strip()
    return st or None


def _route_pending_confirm_turn(req: ChatTurnRequest, route_trace: Dict[str, Any]) -> Dict[str, Any]:
    route_trace["final_route"] = "pending_confirm"
    route_trace["selector_applied_route"] = "pending_confirm"
    loc = _chat_output_locale(req)
    bullets = [
        _orch(loc, "orchestrator.pending_confirm.bullet_a"),
        _orch(loc, "orchestrator.pending_confirm.bullet_b"),
    ]
    summary = _orch(loc, "orchestrator.pending_confirm.summary")
    sem = build_status_payload(
        user_message=req.message or "",
        user_intent="pending confirmation short utterance",
        status_bullets=bullets,
        summary=summary,
        locale=loc,
    )
    assistant_message = _compose_fin(req, sem, route_trace)
    return {
        "assistant_message": assistant_message,
        "route": "pending_confirm",
        "recognized_action": None,
        "completed_params": {},
        "missing_fields": [],
        "can_confirm": False,
        "pending_confirmation": None,
        "tool_names": [],
        "readonly_query_labels": [],
        "route_decision_trace": route_trace,
    }


def _route_fallback_template_turn(req: ChatTurnRequest, route_trace: Dict[str, Any]) -> Dict[str, Any]:
    route_trace["final_route"] = "fallback_template"
    route_trace["selector_applied_route"] = "fallback_template"
    loc = _chat_output_locale(req)
    bullets = [
        _orch(loc, "orchestrator.fallback_template.bullet_a"),
        _orch(loc, "orchestrator.fallback_template.bullet_b"),
    ]
    summary = _orch(loc, "orchestrator.fallback_template.summary")
    sem = build_status_payload(
        user_message=req.message or "",
        user_intent="fallback for empty input or unmatched route",
        status_bullets=bullets,
        summary=summary,
        locale=loc,
    )
    assistant_message = _compose_fin(req, sem, route_trace)
    return {
        "assistant_message": assistant_message,
        "route": "fallback_template",
        "recognized_action": None,
        "completed_params": {},
        "missing_fields": [],
        "can_confirm": False,
        "pending_confirmation": None,
        "tool_names": [],
        "readonly_query_labels": [],
        "route_decision_trace": route_trace,
    }


def _maybe_route_by_tool_action_selector(
    req: ChatTurnRequest,
    *,
    route_trace: Dict[str, Any],
    concise_hit: Any,
    pred_state_early: str,
) -> Optional[Dict[str, Any]]:
    """Route natural language to existing subchains; None falls through to the intent tail chain."""
    scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
    has_active = registry.has_active_pending(scope_key)
    focus_status = _focus_task_status_for_selector(route_trace)
    wsrc = _welcome_policy_source_dict(req)
    welcome_ctx = build_welcome_context_from_dict(wsrc)
    sel_in = SelectorInput(
        message=req.message or "",
        is_new_session=bool((req.chat_context or {}).get("is_new_session")),
        has_active_pending_registry=has_active,
        focus_task_status=focus_status,
        has_concise_progress_hit=concise_hit is not None,
    )
    dec = select_tool_or_action(sel_in, welcome_context=welcome_ctx)
    route_trace["selector_decision"] = dec.trace_dict()
    route_trace["selector_reason_codes"] = list(dec.reason_codes)
    route_trace["selector_confidence"] = dec.confidence
    if dec.action_domain:
        route_trace["selector_action_domain"] = dec.action_domain

    if dec.route in ("llm_chat", "deterministic_action"):
        route_trace["selector_deferred_route"] = dec.route
        if dec.action_domain:
            route_trace["selector_deferred_action_domain"] = dec.action_domain
        return None

    if dec.route == "pending_confirm":
        return _route_pending_confirm_turn(req, route_trace)

    if dec.route == "mcp_context_query":
        route_trace["mcp_context_query_hit"] = True
        route_trace["final_route"] = "mcp_context_query"
        route_trace["selector_applied_route"] = "mcp_context_query"
        snapshot = get_current_context_via_mcp(req, task_repo=runtime.task_repo, pending_registry=registry)
        route_trace["mcp_context_snapshot"] = snapshot
        sanitized = sanitize_tool_bundles_for_finalization(
            [{"ok": True, "tool": "get_current_context", "result": snapshot}]
        )
        loc = _chat_output_locale(req)
        sem = build_tool_result_payload(
            user_message=req.message or "",
            user_intent="current workbench context query",
            tool_names=["get_current_context"],
            readonly_query_labels=[_orch(loc, "orchestrator.readonly_label.workspace_context")],
            sanitized_tool_bundles=sanitized,
            locale=loc,
        )
        assistant_message = _verbalize_from_semantic(
            req,
            sem,
            route_trace,
            answer_type="context_summary",
            final_route="mcp_context_query",
        )
        audit_event(
            "mcp_context_tool_invoked",
            {
                "user_id": req.user_id,
                "session_id": req.session_id,
                "message_preview": (req.message or "")[:500],
                "mode": snapshot.get("mode"),
                "pending_exists": (snapshot.get("pending_action") or {}).get("exists"),
            },
        )
        return {
            "assistant_message": assistant_message,
            "route": "mcp_context_query",
            "recognized_action": None,
            "completed_params": {},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": ["get_current_context"],
            "readonly_query_labels": [_orch(loc, "orchestrator.readonly_label.workspace_context")],
            "route_decision_trace": route_trace,
        }

    if dec.route == "mcp_latest_training_summary":
        route_trace["mcp_latest_training_summary_hit"] = True
        route_trace["final_route"] = "mcp_latest_training_summary"
        route_trace["selector_applied_route"] = "mcp_latest_training_summary"
        train_snap = get_latest_training_summary_via_mcp(req, task_repo=runtime.task_repo)
        route_trace["mcp_latest_training_summary_snapshot"] = train_snap
        sanitized = sanitize_tool_bundles_for_finalization(
            [{"ok": True, "tool": "get_latest_training_summary", "result": train_snap}]
        )
        loc = _chat_output_locale(req)
        sem = build_tool_result_payload(
            user_message=req.message or "",
            user_intent="latest training summary read-only query",
            tool_names=["get_latest_training_summary"],
            readonly_query_labels=[_orch(loc, "orchestrator.readonly_label.latest_training")],
            sanitized_tool_bundles=sanitized,
            locale=loc,
        )
        assistant_message = _verbalize_from_semantic(
            req,
            sem,
            route_trace,
            answer_type="latest_training_summary",
            final_route="mcp_latest_training_summary",
        )
        audit_event(
            "mcp_latest_training_summary_invoked",
            {
                "user_id": req.user_id,
                "session_id": req.session_id,
                "message_preview": (req.message or "")[:500],
                "available": train_snap.get("available"),
                "task_id": (train_snap.get("task") or {}).get("id"),
            },
        )
        return {
            "assistant_message": assistant_message,
            "route": "mcp_latest_training_summary",
            "recognized_action": None,
            "completed_params": {},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": ["get_latest_training_summary"],
            "readonly_query_labels": [_orch(loc, "orchestrator.readonly_label.latest_training")],
            "route_decision_trace": route_trace,
        }

    if dec.route == "workflow_guidance":
        wg_turn = maybe_workflow_guidance_turn(req, runtime.task_repo, pred_state=pred_state_early)
        if wg_turn is None:
            return None
        route_trace["final_route"] = "workflow_guidance"
        route_trace["selector_applied_route"] = "workflow_guidance"
        route_trace["workflow_guidance"] = wg_turn.get("workflow_guidance")
        assistant_message = _verbalize_from_semantic(
            req,
            wg_turn["semantic"],
            route_trace,
            answer_type="workflow_guidance",
            final_route="workflow_guidance",
        )
        return {
            "assistant_message": assistant_message,
            "route": "workflow_guidance",
            "recognized_action": None,
            "completed_params": {"workflow_guidance": wg_turn.get("workflow_guidance")},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    if dec.route == "concise_status":
        if concise_hit is None:
            return None
        route_trace["concise_progress_hit"] = True
        route_trace["final_route"] = "concise_status"
        route_trace["selector_applied_route"] = "concise_status"
        loc_cs = _chat_output_locale(req)
        fb = format_concise_progress_hit(concise_hit, locale=loc_cs)
        if concise_hit.scene == "no_active_tasks":
            summ_cs = format_no_active_tasks_reply(loc_cs)
            bullets = [summ_cs]
            sem = build_status_payload(
                user_message=req.message or "",
                user_intent=_orch(loc_cs, "orchestrator.status_payload.intent_progress"),
                status_bullets=bullets,
                summary=summ_cs,
                locale=loc_cs,
            )
        else:
            pub = task_public_view(concise_hit.task) or {}
            bullets = status_bullets_from_concise_hit(pub, concise_hit.scene, locale=loc_cs)
            sem = build_status_payload(
                user_message=req.message or "",
                user_intent=_orch(loc_cs, "orchestrator.status_payload.intent_progress"),
                status_bullets=bullets,
                summary=fb,
                locale=loc_cs,
            )
        assistant_message = _compose_fin(req, sem, route_trace)
        return {
            "assistant_message": assistant_message,
            "route": "concise_status",
            "recognized_action": None,
            "completed_params": {},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    if dec.route == "welcome_policy":
        welcome_out = _maybe_welcome_policy_turn(req, route_trace)
        if welcome_out is not None:
            welcome_out.setdefault("route_decision_trace", route_trace)
            if isinstance(welcome_out.get("route_decision_trace"), dict):
                welcome_out["route_decision_trace"]["selector_applied_route"] = "welcome_policy"
            return welcome_out
        return None

    if dec.route == "fallback_template":
        return _route_fallback_template_turn(req, route_trace)

    return None


def handle_chat_turn(req: ChatTurnRequest) -> Dict[str, Any]:

    target_info = _resolve_status_target(req.chat_context)
    route_trace: Dict[str, Any] = {
        "concise_progress_hit": False,
        "readonly_tools_hit": False,
        "terminal_result_query_hit": False,
        "normalization": None,
        "classifier": None,
        "final_route": "",
        "reply_finalization_trace": [],
        **target_info,
    }
    pred_state_early = resolve_current_prediction_followup_state(runtime.task_repo, req.chat_context)
    route_trace["prediction_followup_state"] = pred_state_early

    cont = maybe_continue_from_guidance_turn(
        req, runtime.task_repo, pred_state=pred_state_early, registry=registry
    )
    if cont is not None:
        if cont.get("kind") in ("explain", "reject"):
            route_trace["final_route"] = "workflow_guidance"
            route_trace["continue_followup"] = cont.get("kind")
            route_trace["continue_followup_reason"] = cont.get("reason")
            assistant_message = _verbalize_from_semantic(
                req,
                cont["semantic"],
                route_trace,
                answer_type="workflow_guidance",
                final_route="workflow_guidance",
            )
            return {
                "assistant_message": assistant_message,
                "route": "workflow_guidance",
                "recognized_action": None,
                "completed_params": {"continue_followup": cont.get("kind"), "reason": cont.get("reason")},
                "missing_fields": [],
                "can_confirm": False,
                "pending_confirmation": None,
                "tool_names": [],
                "readonly_query_labels": [],
                "route_decision_trace": route_trace,
            }
        if cont.get("kind") == "handoff":
            return _finalize_pending_action_from_handoff(
                req, str(cont.get("action_type") or ""), dict(cont.get("payload") or {}), route_trace
            )

    # tool_action_selector: consolidates NL routing for welcome / MCP / workflow / concise / pending_confirm, etc.
    concise_hit = resolve_concise_progress_hit(req.message or "", runtime.task_repo, req.chat_context)
    sel_early = _maybe_route_by_tool_action_selector(
        req, route_trace=route_trace, concise_hit=concise_hit, pred_state_early=pred_state_early
    )
    if sel_early is not None:
        return sel_early

    pred_state = pred_state_early

    if (
        pred_state == "current_prediction_not_run"
        and is_workspace_current_prediction_outcome_followup(req.message or "")
        and not wants_explicit_global_latest_prediction_query(req.message or "")
        and not targets_model_prediction_target_column_question(req.message or "")
    ):
        route_trace["final_route"] = "concise_status"
        loc_sticky = _chat_output_locale(req)
        sfb = sticky_no_current_prediction_reply(req.message or "", locale=loc_sticky)
        ssem = build_sticky_no_prediction_payload(
            user_message=req.message or "",
            fallback_deterministic_reply=sfb,
        )
        assistant_message = _compose_fin(req, ssem, route_trace)
        return {
            "assistant_message": assistant_message,
            "route": "concise_status",
            "recognized_action": None,
            "completed_params": {},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    # Protective finalization: when a focus/active task exists, generic status questions bind to task state.
    # Failure-location/debugging questions are handled by terminal_result and task-backed failure verbalization below.
    _term_intent_early = classify_terminal_result_intent(req.message or "")
    if (
        _generic_status_query_like(req.message or "")
        and _term_intent_early not in ("fail_where", "fail_check_first")
        and not _explicit_prediction_summary_query(req.message or "")
        and str(route_trace.get("has_active_or_waiting_task") or "") == "true"
    ):
        jt = str(route_trace.get("final_status_target_type") or "")
        probe = GENERIC_FOCUS_PROBE
        if jt == "train_model":
            probe = FOCUS_PROBE_TRAIN_PROGRESS
        elif jt == "predict_outcome":
            probe = FOCUS_PROBE_PRED_PROGRESS
        forced_hit = resolve_concise_progress_hit(probe, runtime.task_repo, req.chat_context)
        if forced_hit is not None:
            route_trace["final_route"] = "concise_status"
            loc_f = _chat_output_locale(req)
            fbf = format_concise_progress_hit(forced_hit, locale=loc_f)
            if forced_hit.scene == "no_active_tasks":
                summ_f = format_no_active_tasks_reply(loc_f)
                fbullets = [summ_f]
                fsem = build_status_payload(
                    user_message=req.message or "",
                    user_intent=_orch(loc_f, "orchestrator.status_payload.intent_generic_bind"),
                    status_bullets=fbullets,
                    summary=summ_f,
                    locale=loc_f,
                )
            else:
                fpub = task_public_view(forced_hit.task) or {}
                fbullets = status_bullets_from_concise_hit(fpub, forced_hit.scene, locale=loc_f)
                fsem = build_status_payload(
                    user_message=req.message or "",
                    user_intent=_orch(loc_f, "orchestrator.status_payload.intent_generic_bind"),
                    status_bullets=fbullets,
                    summary=fbf,
                    locale=loc_f,
                )
            assistant_message = _compose_fin(req, fsem, route_trace)
            return {
                "assistant_message": assistant_message,
                "route": "concise_status",
                "recognized_action": None,
                "completed_params": {},
                "missing_fields": [],
                "can_confirm": False,
                "pending_confirmation": None,
                "tool_names": [],
                "readonly_query_labels": [],
                "route_decision_trace": route_trace,
            }

    # --- Stage 4 read-only planning handoff (planner → parse_intent → pending policy) ---
    # The LLM read-only planner runs *before* parse_intent so we can surface workspace/task facts
    # (tool_query) without first committing to a high-risk action_type. parse_intent only decides
    # whether a *separate* training/prediction/report draft might also apply; if both exist,
    # readonly_query_overrides_action_intent() keeps the read-only plan when the utterance clearly
    # asks for status/results/failure/context (mixed "train + query" → answer read-only first, no
    # pending in the same turn). High-risk execution still always goes through pending_confirmation +
    # POST /actions/confirm — the LLM planner cannot call create_* or get_job_detail.
    llm_planned = plan_readonly_tools_with_llm(req, qwen_provider, route_trace)
    planned = llm_planned if llm_planned is not None else plan_readonly_tools(req.message)
    if planned is None and pred_state == "current_prediction_available":
        if is_workspace_current_prediction_outcome_followup(
            req.message or ""
        ) and not targets_model_prediction_target_column_question(req.message or ""):
            planned = [("get_latest_prediction_summary", {})]
    intent = parse_intent(req.message)
    action_type = intent.get("action_type")
    planned_before_action_override = planned
    if planned and action_type and not readonly_query_overrides_action_intent(req.message):
        planned = None
    if planned and str(route_trace.get("resolved_focus_task_type") or "") == "train_model":
        # Training focus + generic status phrasing: do not let latest prediction summary preempt.
        if _generic_status_query_like(req.message or "") and any(
            name in ("get_latest_prediction_summary", "get_prediction_explanation_summary") for name, _ in planned
        ):
            planned = None

    # Completed recommend_regimen focused in chat_context: explicit result questions override readonly tool plans.
    foc_jid_rec = get_focus_job_id(req.chat_context or {})
    rec_row_focus = runtime.task_repo.get(foc_jid_rec) if foc_jid_rec else None
    rec_bundle_focus = (
        try_build_recommendation_completed_bundle_from_task(rec_row_focus, runtime.task_repo)
        if isinstance(rec_row_focus, dict)
        else None
    )
    if rec_bundle_focus is not None and _message_seeks_completed_recommendation_result(req.message or ""):
        route_trace["final_route"] = "concise_status"
        route_trace["recommendation_result_hit"] = True
        if planned:
            route_trace["recommendation_result_overrides_readonly_plan"] = True
        payload_rr = build_recommendation_result_response_payload(
            rec_bundle_focus,
            final_route="concise_status",
            payload_source="recommendation_completed_focus_execution",
        )
        vb = route_trace.setdefault("response_verbalization_trace", [])
        assistant_message = verbalize_response(payload_rr, qwen_provider, req=req, trace_entries=vb)
        fin = route_trace.setdefault("reply_finalization_trace", [])
        fin.append(
            {
                "mode": "recommendation_result",
                "recommendation_result_verbalization": True,
                "recommendation_result_path": "focus_execution",
                "answer_type": "recommendation_result",
                "assistant_message_via": "response_verbalizer",
            }
        )
        return {
            "assistant_message": assistant_message,
            "route": "concise_status",
            "recognized_action": None,
            "completed_params": {},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    if planned is None and planned_before_action_override is None:
        tq_hit = resolve_terminal_result_when_no_tools(
            req.message or "", runtime.task_repo, req.chat_context
        )
        if tq_hit is not None:
            route_trace["final_route"] = "concise_status"
            route_trace["terminal_result_query_hit"] = True
            loc_tq = _chat_output_locale(req)
            if tq_hit == "sticky_no_prediction":
                tfb = sticky_no_current_prediction_reply(req.message or "", locale=loc_tq)
                tsem = build_sticky_no_prediction_payload(
                    user_message=req.message or "",
                    fallback_deterministic_reply=tfb,
                    locale=loc_tq,
                )
                assistant_message = _compose_fin(req, tsem, route_trace)
            else:
                assert isinstance(tq_hit, TerminalResultHit)
                st_task = str(tq_hit.task.get("status") or "")
                if st_task == "failed":
                    assistant_message = _task_backed_failure_assistant_message(
                        tq_hit.task,
                        object_kind=tq_hit.object_kind,
                        intent=tq_hit.intent,
                        batch_hint=tq_hit.batch_hint,
                        final_route="concise_status",
                        payload_source=(
                            "terminal_execution_train_failed"
                            if tq_hit.object_kind == "train"
                            else "terminal_execution_prediction_failed"
                        ),
                        req=req,
                        llm_provider=qwen_provider,
                        route_decision_trace=route_trace,
                    )
                    tsem = build_terminal_result_payload(
                        user_message=req.message or "",
                        object_kind=tq_hit.object_kind,
                        intent=tq_hit.intent,
                        fallback_deterministic_reply=assistant_message,
                        locale=loc_tq,
                    )
                    fin = route_trace.setdefault("reply_finalization_trace", [])
                    fin.append(
                        {
                            "mode": tsem.mode,
                            "task_backed_failure_verbalization": True,
                            "execution_chain": True,
                            "answer_type": (
                                "training_failed" if tq_hit.object_kind == "train" else "prediction_failed"
                            ),
                            "verbatim_policy": tsem.verbatim_policy,
                            "assistant_message_via": "response_verbalizer",
                        }
                    )
                else:
                    tfb = terminal_reply_for_task_and_intent(
                        tq_hit.task,
                        tq_hit.object_kind,
                        tq_hit.intent,
                        batch_hint=tq_hit.batch_hint,
                        locale=loc_tq,
                    )
                    tsem = build_terminal_result_payload(
                        user_message=req.message or "",
                        object_kind=tq_hit.object_kind,
                        intent=tq_hit.intent,
                        fallback_deterministic_reply=tfb,
                        locale=loc_tq,
                    )
                    batch_ex = None
                    exec_bundle = None
                    train_bundle_ex = None
                    if tq_hit.object_kind == "predict":
                        batch_ex = try_build_batch_prediction_completed_bundle_from_task(tq_hit.task)
                        if batch_ex is None:
                            exec_bundle = try_build_single_prediction_execution_bundle_from_task(tq_hit.task)
                    elif tq_hit.object_kind == "train":
                        train_bundle_ex = try_build_training_completed_bundle_from_task(tq_hit.task)
                    if batch_ex is not None:
                        na_b = _extract_next_step_from_verbatim(tfb)
                        if na_b:
                            batch_ex["next_action"] = na_b
                        batch_ex["semantic_summary"] = compose_predict_batch_completed_aggregate_factual(
                            tq_hit.task, loc_tq
                        )
                        payload_bb = build_batch_prediction_result_response_payload(
                            batch_ex,
                            final_route="concise_status",
                            payload_source="batch_prediction_execution_chain",
                            locale=loc_tq,
                        )
                        vb = route_trace.setdefault("response_verbalization_trace", [])
                        assistant_message = verbalize_response(
                            payload_bb, qwen_provider, req=req, trace_entries=vb
                        )
                        fin = route_trace.setdefault("reply_finalization_trace", [])
                        fin.append(
                            {
                                "mode": tsem.mode,
                                "batch_prediction_result_verbalization": True,
                                "batch_prediction_result_path": "execution_chain",
                                "answer_type": "batch_prediction_result",
                                "verbatim_policy": tsem.verbatim_policy,
                                "assistant_message_via": "response_verbalizer",
                            }
                        )
                    elif exec_bundle is not None and is_llm_polish_answer_type("prediction_result"):
                        # Selector + terminal resolution bound to a concrete task; prediction deterministic core locked by task row + factual bundle;
                        # hand only single-sample completion phrasing to prediction_result verbalizer (data source differs from read-only latest-summary chain).
                        na_e = _extract_next_step_from_verbatim(tfb)
                        if na_e:
                            exec_bundle["next_action"] = na_e
                        exec_bundle["semantic_summary"] = compose_predict_single_completed_factual(
                            tq_hit.task, loc_tq
                        )
                        payload_pb = build_prediction_result_response_payload(
                            exec_bundle,
                            final_route="concise_status",
                            payload_source="single_prediction_execution_chain",
                            locale=loc_tq,
                        )
                        vb = route_trace.setdefault("response_verbalization_trace", [])
                        assistant_message = verbalize_response(
                            payload_pb, qwen_provider, req=req, trace_entries=vb
                        )
                        fin = route_trace.setdefault("reply_finalization_trace", [])
                        fin.append(
                            {
                                "mode": tsem.mode,
                                "prediction_result_verbalization": True,
                                "prediction_result_path": "execution_chain",
                                "answer_type": "prediction_result",
                                "verbatim_policy": tsem.verbatim_policy,
                                "assistant_message_via": "response_verbalizer",
                            }
                        )
                    elif train_bundle_ex is not None and is_llm_polish_answer_type("training_completed"):
                        # Terminal resolution bound to a concrete training task; training deterministic core locked by task row + factual bundle;
                        # hand only training-completed phrasing to training_completed verbalizer (differs from MCP latest_training_summary data source).
                        na_trn = _extract_next_step_from_verbatim(tfb)
                        if na_trn:
                            train_bundle_ex["next_action"] = na_trn
                        train_bundle_ex["semantic_summary"] = compose_train_completed_standard(tq_hit.task, loc_tq)
                        payload_tb = build_training_completed_response_payload(
                            train_bundle_ex,
                            final_route="concise_status",
                            payload_source="training_completed_execution_chain",
                            locale=loc_tq,
                        )
                        vb = route_trace.setdefault("response_verbalization_trace", [])
                        assistant_message = verbalize_response(
                            payload_tb, qwen_provider, req=req, trace_entries=vb
                        )
                        fin = route_trace.setdefault("reply_finalization_trace", [])
                        fin.append(
                            {
                                "mode": tsem.mode,
                                "training_completed_verbalization": True,
                                "training_completed_path": "execution_chain",
                                "answer_type": "training_completed",
                                "verbatim_policy": tsem.verbatim_policy,
                                "assistant_message_via": "response_verbalizer",
                            }
                        )
                    else:
                        assistant_message = _compose_fin(req, tsem, route_trace)
            return {
                "assistant_message": assistant_message,
                "route": "concise_status",
                "recognized_action": None,
                "completed_params": {},
                "missing_fields": [],
                "can_confirm": False,
                "pending_confirmation": None,
                "tool_names": [],
                "readonly_query_labels": [],
                "route_decision_trace": route_trace,
            }
    if planned:
        route_trace["readonly_tools_hit"] = True
        route_trace["final_route"] = "tool_query"
        data = _run_readonly_tool_plan(
            req,
            planned,
            mixed_action_intent=bool(action_type),
            llm_provider=qwen_provider,
            trace_sink=route_trace.get("reply_finalization_trace"),
            route_decision_trace=route_trace,
        )
        data["route_decision_trace"] = route_trace
        return data

    if action_type == "prediction_entry":
        open_batch = _prediction_entry_open_batch(req.message or "")
        route_trace["final_route"] = "prediction_entry"
        route_trace["prediction_entry_open_batch"] = open_batch
        return {
            "assistant_message": "",
            "route": "prediction_entry",
            "recognized_action": "prediction_entry",
            "completed_params": {"prediction_entry_open_batch": open_batch},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    if not action_type and _should_try_fallback_classifier(req.message):
        norm = normalize_query_for_routing(req.message or "", req.chat_context)
        route_trace["normalization"] = norm
        clf = classify_status_query_with_llm(req.message or "", qwen_provider)
        used = bool(
            clf.get("confidence", 0.0) >= _FALLBACK_CLASSIFY_CONFIDENCE_THRESHOLD
            and clf.get("label") in {"status_query_progress", "status_query_completion"}
        )
        clf["used"] = used
        route_trace["classifier"] = clf
        if used:
            status_msg = req.message or ""
            fb_hit = resolve_concise_progress_hit(status_msg, runtime.task_repo, req.chat_context)
            if fb_hit is None:
                probe = _focus_bound_probe_message(req, str(clf.get("label") or ""))
                if probe:
                    fb_hit = resolve_concise_progress_hit(probe, runtime.task_repo, req.chat_context)
            if fb_hit is not None:
                route_trace["final_route"] = "concise_status"
                loc_fb = _chat_output_locale(req)
                fbf = format_concise_progress_hit(fb_hit, locale=loc_fb)
                if fb_hit.scene == "no_active_tasks":
                    summ_fb = format_no_active_tasks_reply(loc_fb)
                    bbul = [summ_fb]
                    fb_sem = build_status_payload(
                        user_message=req.message or "",
                        user_intent=_orch(loc_fb, "orchestrator.status_payload.intent_classifier_fallback"),
                        status_bullets=bbul,
                        summary=summ_fb,
                        locale=loc_fb,
                    )
                else:
                    bpub = task_public_view(fb_hit.task) or {}
                    bbul = status_bullets_from_concise_hit(bpub, fb_hit.scene, locale=loc_fb)
                    fb_sem = build_status_payload(
                        user_message=req.message or "",
                        user_intent=_orch(loc_fb, "orchestrator.status_payload.intent_classifier_fallback"),
                        status_bullets=bbul,
                        summary=fbf,
                        locale=loc_fb,
                    )
                fb_msg = _compose_fin(req, fb_sem, route_trace)
                return {
                    "assistant_message": fb_msg,
                    "route": "concise_status",
                    "recognized_action": None,
                    "completed_params": {},
                    "missing_fields": [],
                    "can_confirm": False,
                    "pending_confirmation": None,
                    "tool_names": [],
                    "readonly_query_labels": [],
                    "route_decision_trace": route_trace,
                }

    if not action_type:
        try:
            reply = qwen_provider.chat(
                messages=[{"role": "user", "content": req.message}],
                system_prompt=_compose_chat_system_prompt(req),
                temperature=0.3,
                stream=False,
            )
        except LLMProviderError as exc:
            raise AgentFlowError(exc.user_message, exc.error_code) from exc
        route_trace["final_route"] = "llm_chat"
        return {
            "assistant_message": reply,
            "route": "llm_chat",
            "recognized_action": None,
            "completed_params": {},
            "missing_fields": [],
            "can_confirm": False,
            "pending_confirmation": None,
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": route_trace,
        }

    payload, completed, missing = complete_params(action_type, req.message)

    if action_type in _PREDICTIONISH_ACTION_TYPES:
        # Prediction drafts must not silently merge workbench current model into a confirmed model_id; only explicit utterances or card confirmation qualify.
        if action_type != "draft_single_prediction":
            payload = _merge_model_from_chat_context(payload, req.chat_context)
        if req.client_completed_params:
            payload = {**payload, **req.client_completed_params}
        pf = payload.get("patient_features")
        if not isinstance(pf, dict):
            payload["patient_features"] = {}
        if action_type == "draft_single_prediction":
            payload = enrich_draft_single_prediction_payload(payload)
            payload = validate_action_payload("draft_single_prediction", payload)
            missing = prediction_action_missing(action_type, payload)
        else:
            missing = prediction_action_missing(action_type, payload)

    if action_type in ("create_training_job", "draft_training_job"):
        payload = _merge_dataset_from_chat_context(payload, req.chat_context)
        if req.client_completed_params:
            payload = {**payload, **req.client_completed_params}
        ok, pend_errors = is_training_payload_complete_for_pending(payload)
        missing = pend_errors if not ok else []
        if ok:
            payload = validate_phase1_training_payload_to_dict(payload)
        else:
            payload = normalize_phase1_training_payload(payload)
    needs_confirm = confirm_sm.requires_confirmation(action_type)
    can_confirm = needs_confirm and len(missing) == 0

    if needs_confirm:
        scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
        pending = registry.create(action_type=action_type, payload=payload, scope_key=scope_key)
        audit_event(
            "pending_action_created",
            {
                "action_type": action_type,
                "pending_action_id": pending.pending_action_id,
                "user_id": req.user_id,
                "scope_key": scope_key,
            },
        )
        loc_act = _chat_output_locale(req)
        completed_summary = ", ".join(completed[:12]) if completed else _orch(loc_act, "orchestrator.pending.standard_completed_none")
        pending_preview = _orch(loc_act, "orchestrator.pending.standard_preview")
        if action_type == "draft_single_prediction" and missing:
            miss_labels = _prediction_missing_labels(missing, loc_act)
            sem_act = build_missing_info_payload(
                user_message=req.message or "",
                action_title=_user_action_title_for_locale(action_type, loc_act),
                missing_fields_zh=miss_labels,
                context_note=_orch(loc_act, "orchestrator.context_note.single_prediction_form"),
                locale=loc_act,
            )
            assistant_message = _compose_fin(req, sem_act, route_trace)
        elif action_type in _TRAINING_ACTION_TYPES:
            miss_labels = _training_missing_labels(missing, loc_act)
            sem_act = build_draft_created_payload(
                user_message=req.message or "",
                action_title=_training_user_title_for_locale(action_type, loc_act),
                can_confirm=can_confirm,
                missing_fields_zh=miss_labels,
                completed_summary=completed_summary,
                pending_action_preview=pending_preview,
                locale=loc_act,
            )
            assistant_message = _verbalize_training_draft_created(
                req,
                sem_act,
                route_trace,
                can_confirm=can_confirm,
                final_route="deterministic_action",
                pending_action_id=pending.pending_action_id,
                completed_summary=completed_summary,
                missing_field_keys=list(missing),
                draft_context="standard",
            )
        elif action_type == "draft_single_prediction":
            sem_act = build_draft_created_payload(
                user_message=req.message or "",
                action_title=_user_action_title_for_locale(action_type, loc_act),
                can_confirm=can_confirm,
                missing_fields_zh=[],
                completed_summary=completed_summary,
                pending_action_preview=pending_preview,
                locale=loc_act,
            )
            assistant_message = _compose_fin(req, sem_act, route_trace)
        else:
            title = _user_action_title_for_locale(action_type, loc_act)
            miss_other = [str(x) for x in missing] if missing else []
            sem_act = build_draft_created_payload(
                user_message=req.message or "",
                action_title=title,
                can_confirm=can_confirm,
                missing_fields_zh=miss_other,
                completed_summary=completed_summary,
                pending_action_preview=pending_preview,
                locale=loc_act,
            )
            assistant_message = _compose_fin(req, sem_act, route_trace)
        return {
            "assistant_message": assistant_message,
            "route": "deterministic_action",
            "recognized_action": action_type,
            "completed_params": payload,
            "missing_fields": missing,
            "can_confirm": can_confirm,
            "pending_confirmation": pending.model_dump(mode="json"),
            "tool_names": [],
            "readonly_query_labels": [],
            "route_decision_trace": {**route_trace, "final_route": "deterministic_action"},
        }

    route_trace["final_route"] = "deterministic_action"
    loc_ce = _chat_output_locale(req)
    miss_line = _join_missing_labels_for_action(action_type, missing, loc_ce)
    missing_labels: Optional[List[str]] = None
    if missing:
        missing_labels = _missing_field_labels_for_action(action_type, missing, loc_ce)
    reason_ce = _orch(
        loc_ce,
        "orchestrator.cannot_enter_pending",
        action=_user_action_title_for_locale(action_type, loc_ce),
        missing=miss_line,
    )
    sem_ce = build_cannot_execute_payload(
        user_message=req.message or "",
        action_title=_user_action_title_for_locale(action_type, loc_ce),
        reason=reason_ce,
        missing_fields_zh=missing_labels,
        locale=loc_ce,
    )
    assistant_message = _compose_fin(req, sem_ce, route_trace)
    return {
        "assistant_message": assistant_message,
        "route": "deterministic_action",
        "recognized_action": action_type,
        "completed_params": payload,
        "missing_fields": missing,
        "can_confirm": False,
        "pending_confirmation": None,
        "tool_names": [],
        "readonly_query_labels": [],
        "route_decision_trace": route_trace,
    }


_CJK_CONFIRM_RE = re.compile(r"[\u4e00-\u9fff]")


def _action_confirm_lang(req: ActionConfirmRequest) -> Tuple[str, bool]:
    loc = resolve_api_user_locale(req.locale, accept_language=None, default="en")
    return loc, api_locale_prefers_english(loc)


def _cfm(en: bool, key: str, **kwargs: Any) -> str:
    return _orch_msg("en" if en else "zh", key, **kwargs)


def _sanitize_confirm_detail_for_en(msg: str, en: bool) -> str:
    s = str(msg or "").strip()
    if not en:
        return s
    if not s:
        return "Validation failed."
    if _CJK_CONFIRM_RE.search(s):
        return "Validation failed; check pending payload and retry."
    return s


def _sanitize_tool_failure_message_for_en(msg: Any, en: bool) -> str:
    s = str(msg or "").strip()
    if not en:
        return s or _orch("zh", "orchestrator.tool_failure_default")
    if not s:
        return "Operation failed."
    if _CJK_CONFIRM_RE.search(s):
        return "Operation failed; check inputs or logs and retry."
    return s


def handle_action_confirm(req: ActionConfirmRequest) -> Dict[str, Any]:
    _, en = _action_confirm_lang(req)
    pending = registry.get(req.pending_action_id)
    if not pending:
        raise AgentFlowError(_cfm(en, "orchestrator.confirm.pending_not_found"), "PENDING_ACTION_NOT_FOUND")
    if pending.status == "expired":
        raise AgentFlowError(_cfm(en, "orchestrator.confirm.pending_expired"), "PENDING_ACTION_EXPIRED")
    if pending.status == "superseded":
        raise AgentFlowError(
            _cfm(en, "orchestrator.confirm.pending_superseded"),
            "PENDING_ACTION_SUPERSEDED",
        )
    if pending.executed_job_id:
        return {
            "assistant_message": _cfm(en, "orchestrator.confirm.already_executed"),
            "job_id": pending.executed_job_id,
            "task": None,
        }
    if pending.status != "pending":
        raise AgentFlowError(
            _cfm(en, "orchestrator.confirm.invalid_status", status=pending.status),
            "PENDING_ACTION_INVALID_STATUS",
        )

    if not req.confirmed:
        registry.cancel(req.pending_action_id)
        audit_event("pending_action_canceled", {"pending_action_id": req.pending_action_id})
        return {"assistant_message": _cfm(en, "orchestrator.confirm.canceled"), "job_id": None, "task": None}

    confirmed_item = registry.confirm(req.pending_action_id)
    if not confirmed_item:
        raise AgentFlowError(_cfm(en, "orchestrator.confirm.confirm_failed"), "PENDING_ACTION_CONFIRM_FAILED")
    payload = dict(pending.payload)
    if req.completed_params:
        payload.update(req.completed_params)
    validation_type = (
        "create_prediction_job" if pending.action_type == "draft_single_prediction" else pending.action_type
    )
    try:
        payload = validate_action_payload(validation_type, payload)
    except ValidationError as exc:
        detail = _sanitize_confirm_detail_for_en(str(exc.errors()), en)
        raise AgentFlowError(
            _cfm(
                en,
                "orchestrator.confirm.payload_validation_failed",
                detail=str(exc.errors()) if not en else detail,
            ),
            "PAYLOAD_VALIDATION_FAILED",
        )
    except ValueError as exc:
        raise AgentFlowError(_sanitize_confirm_detail_for_en(str(exc), en), "PAYLOAD_VALIDATION_FAILED")

    audit_event("tool_call_start", {"action_type": pending.action_type, "pending_action_id": pending.pending_action_id})
    if pending.action_type in ("create_training_job", "draft_training_job"):
        result = create_training_job_from_contract(payload)
    elif pending.action_type in ("create_prediction_job", "draft_single_prediction"):
        result = create_prediction_job(**payload)
    elif pending.action_type == "create_recommendation_job":
        result = create_recommendation_job(**payload)
    elif pending.action_type == "create_report_job":
        result = create_report_job(**payload)
    else:
        raise AgentFlowError(
            _cfm(en, "orchestrator.confirm.unsupported_action_type", action=pending.action_type),
            "ACTION_TYPE_UNSUPPORTED",
        )

    if result["status"] != "success":
        audit_event("tool_call_failed", {"pending_action_id": pending.pending_action_id, "result": result})
        raw_m = result.get("message", _cfm(en, "orchestrator.tool_failure_default"))
        raise AgentFlowError(_sanitize_tool_failure_message_for_en(raw_m, en), "TOOL_CALL_FAILED")
    if not result.get("job_id"):
        raise AgentFlowError(
            _cfm(en, "orchestrator.confirm.job_id_missing"),
            "JOB_CREATION_FAILED",
        )
    registry.mark_job_created(req.pending_action_id, result["job_id"])
    audit_event("tool_call_succeeded", {"pending_action_id": pending.pending_action_id, "job_id": result.get("job_id")})
    asst = _cfm(en, "orchestrator.confirm.success_generic")
    if pending.action_type in ("create_training_job", "draft_training_job"):
        asst = _cfm(en, "orchestrator.confirm.success_training")
    elif pending.action_type == "draft_single_prediction":
        asst = _cfm(en, "orchestrator.confirm.success_draft_prediction")
    elif pending.action_type == "create_prediction_job":
        asst = _cfm(en, "orchestrator.confirm.success_batch_prediction")
    elif pending.action_type == "create_recommendation_job":
        asst = _cfm(en, "orchestrator.confirm.success_recommendation")
    elif pending.action_type == "create_report_job":
        asst = _cfm(en, "orchestrator.confirm.success_report")
    return {
        "assistant_message": asst,
        "job_id": result.get("job_id"),
        "task": result.get("job"),
    }


def health_check_chat_provider() -> Dict[str, Any]:
    try:
        return qwen_provider.health_check()
    except LLMProviderError as exc:
        raise AgentFlowError(exc.user_message, exc.error_code) from exc

