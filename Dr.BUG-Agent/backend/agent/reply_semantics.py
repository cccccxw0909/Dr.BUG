"""Structured semantic payloads: rule-layer facts and boundaries for natural-language finalization."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons.zh_followup_action_labels import FOLLOWUP_ACTION_LABEL_ZH_TO_EN
from backend.agent.i18n.lexicons.zh_reply_semantics_action_titles import (
    ACTION_TITLE_ZH_TO_EN,
    CANONICAL_ACTION_TITLE_PREDICTION,
    CANONICAL_ACTION_TITLE_TRAINING,
    REASON_SKIP_APPEND_TAIL_IF_CONTAINS,
)
from backend.agent.i18n.lexicons.zh_typography import ZH_FULLWIDTH_PERIOD, ZH_IDEOGRAPHIC_COMMA

SemanticMode = Literal[
    "tool_result",
    "draft_created",
    "missing_info",
    "cannot_execute",
    "status",
    "terminal_result",
    "sticky_no_prediction",
    "workflow_guidance",
]

# Verbatim policy for finalization/fallback; explicit levels prevent legacy templates from dominating lower-risk cases.
VerbatimPolicy = Literal["required", "allowed", "forbidden"]


@dataclass
class AgentSemanticPayload:
    mode: SemanticMode
    user_intent: str
    summary: str
    key_points: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    allowed_next_steps: List[str] = field(default_factory=list)
    blocked_actions: List[str] = field(default_factory=list)
    safety_notes: List[str] = field(default_factory=list)
    pending_action_preview: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    response_tone: str = "calm"
    #: required: high-risk/strict facts, fallback may use verbatim; allowed: transitional, facts first; forbidden: do not prompt or fallback with verbatim.
    verbatim_policy: VerbatimPolicy = "required"
    #: Rule-layer long-form copy; ignored by the composer when verbatim_policy is forbidden.
    verbatim_reply_to_paraphrase: Optional[str] = None
    #: Sanitized tool results for finalization prompts; not returned to the frontend.
    tool_fact_bundles: Optional[List[Dict[str, Any]]] = field(default=None, repr=False)
    locale: Optional[str] = None


def _en(locale: Optional[str]) -> bool:
    from backend.agent.chat_output_locale import is_english_output_locale

    return is_english_output_locale(locale)


def _join_items(items: List[str], locale: Optional[str]) -> str:
    return ", ".join(items) if _en(locale) else ZH_IDEOGRAPHIC_COMMA.join(items)



def _action_title(title: str, locale: Optional[str]) -> str:
    if not _en(locale):
        return title
    return ACTION_TITLE_ZH_TO_EN.get(str(title), str(title))

def terminal_result_verbatim_policy(intent: str) -> VerbatimPolicy:
    """
    Terminal-result replies: failure-cause and explanation follow-ups have low wording tolerance, so keep required;
    other metric/label/batch-summary queries can be supported by facts plus an allowed draft.
    """
    i = str(intent or "").strip()
    if i in ("fail_where", "fail_check_first", "pred_why"):
        return "required"
    return "allowed"


def build_tool_result_payload(
    *,
    user_message: str,
    user_intent: str,
    tool_names: List[str],
    readonly_query_labels: List[str],
    sanitized_tool_bundles: List[Dict[str, Any]],
    verbatim_reply_to_paraphrase: Optional[str] = None,
    verbatim_policy: VerbatimPolicy = "forbidden",
    mixed_action_note: bool = False,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """General read-only tool summary: prioritize sanitized tool facts over deterministic long-form copy."""
    notes: List[str] = []
    if mixed_action_note:
        notes.append(chat_msg(locale, "reply_semantics.tool_result.mixed_action_note"))
    kp: List[str] = []
    if readonly_query_labels:
        kp.append(
            chat_msg(locale, "reply_semantics.tool_result.label_queried")
            + _join_items(readonly_query_labels, locale)
        )
    if tool_names:
        kp.append(
            chat_msg(locale, "reply_semantics.tool_result.label_query_types")
            + _join_items(tool_names, locale)
        )
    if verbatim_policy == "allowed" and verbatim_reply_to_paraphrase:
        kp.append(chat_msg(locale, "reply_semantics.tool_result.boundary_draft_note"))
    return AgentSemanticPayload(
        mode="tool_result",
        user_intent=user_intent,
        summary=chat_msg(locale, "reply_semantics.tool_result.summary"),
        key_points=kp,
        observations=[
            chat_msg(locale, "reply_semantics.tool_result.obs_focus_relevant"),
        ],
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.tool_result.next_train_predict_confirm"),
            chat_msg(locale, "reply_semantics.tool_result.next_task_panel"),
        ],
        blocked_actions=[
            chat_msg(locale, "reply_semantics.tool_result.block_no_claim_execution"),
            chat_msg(locale, "reply_semantics.tool_result.block_no_fabricate_ids"),
        ],
        safety_notes=notes,
        missing_fields=[],
        response_tone="calm",
        locale=locale,
        verbatim_policy=verbatim_policy,
        verbatim_reply_to_paraphrase=(
            verbatim_reply_to_paraphrase.strip() if verbatim_policy != "forbidden" and verbatim_reply_to_paraphrase else None
        ),
        tool_fact_bundles=list(sanitized_tool_bundles),
    )


def build_draft_created_payload(
    *,
    user_message: str,
    action_title: str,
    can_confirm: bool,
    missing_fields_zh: List[str],
    completed_summary: str,
    pending_action_preview: str,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """Draft-created semantics; the action remains pending until explicit user confirmation."""
    display_title = _action_title(action_title, locale)
    none_p = chat_msg(locale, "reply_semantics.placeholder.none")
    stage = (
        chat_msg(locale, "reply_semantics.draft_created.stage_ready_confirm")
        if can_confirm
        else chat_msg(locale, "reply_semantics.draft_created.stage_need_fields")
    )
    miss_txt = _join_items(missing_fields_zh, locale) if missing_fields_zh else none_p
    completed_text = completed_summary or none_p
    kp: List[str] = [
        chat_msg(locale, "reply_semantics.draft_created.parsed_summary_line", summary=completed_text),
        chat_msg(locale, "reply_semantics.draft_created.missing_fields_line", fields=miss_txt),
    ]

    if action_title == CANONICAL_ACTION_TITLE_TRAINING:
        kp.append(chat_msg(locale, "reply_semantics.draft_created.train_not_started"))
        if not can_confirm:
            kp.append(chat_msg(locale, "reply_semantics.draft_created.train_wait_required_fields"))
        else:
            kp.append(chat_msg(locale, "reply_semantics.draft_created.train_after_confirm"))
    elif action_title == CANONICAL_ACTION_TITLE_PREDICTION:
        kp.append(chat_msg(locale, "reply_semantics.draft_created.pred_no_inference"))
        if not can_confirm:
            kp.append(chat_msg(locale, "reply_semantics.draft_created.pred_wait_no_autofill"))
        else:
            kp.append(chat_msg(locale, "reply_semantics.draft_created.pred_after_confirm_task"))
    else:
        stage2 = (
            chat_msg(locale, "reply_semantics.draft_created.other_stage_ready_confirm")
            if can_confirm
            else chat_msg(locale, "reply_semantics.draft_created.other_stage_complete_first")
        )
        kp.append(chat_msg(locale, "reply_semantics.draft_created.interface_stage_hint", hint=stage2))

    title_for_summary = display_title if _en(locale) else action_title
    return AgentSemanticPayload(
        mode="draft_created",
        user_intent=chat_msg(locale, "reply_semantics.draft_created.user_intent"),
        summary=chat_msg(locale, "reply_semantics.draft_created.summary_prepared", title=title_for_summary, stage=stage),
        key_points=kp,
        observations=[
            chat_msg(locale, "reply_semantics.draft_created.obs_draft_pending"),
        ],
        allowed_next_steps=(
            [
                chat_msg(locale, "reply_semantics.draft_created.next_review_params"),
                chat_msg(locale, "reply_semantics.draft_created.next_complete_then_confirm"),
            ]
            if not can_confirm
            else [chat_msg(locale, "reply_semantics.draft_created.next_review_confirm_execute")]
        ),
        blocked_actions=[chat_msg(locale, "reply_semantics.draft_created.block_no_claim_started")],
        safety_notes=[chat_msg(locale, "reply_semantics.draft_created.safety_execution_after_confirm")],
        pending_action_preview=pending_action_preview,
        missing_fields=list(missing_fields_zh),
        response_tone="direct",
        locale=locale,
        verbatim_policy="forbidden",
        verbatim_reply_to_paraphrase=None,
    )


def build_missing_info_payload(
    *,
    user_message: str,
    action_title: str,
    missing_fields_zh: List[str],
    context_note: str = "",
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """Missing-parameter semantics: allowed keeps a short verbatim fallback while prompts prioritize facts."""
    display_title = _action_title(action_title, locale)
    miss_join = _join_items(missing_fields_zh, locale) if missing_fields_zh else chat_msg(locale, "reply_semantics.placeholder.see_contract")
    verbatim: Optional[str] = None
    if action_title == CANONICAL_ACTION_TITLE_PREDICTION:
        verbatim = (
            chat_msg(locale, "reply_semantics.missing_info.prediction_entry_ready")
            + chat_msg(locale, "reply_semantics.missing_info.still_required_items", items=miss_join)
            + chat_msg(locale, "reply_semantics.missing_info.prediction_complete_form_before_confirm")
        )
    kp = [
        chat_msg(locale, "reply_semantics.missing_info.key_missing_fields", items=miss_join),
        chat_msg(locale, "reply_semantics.missing_info.not_executable_yet"),
    ]
    if action_title == CANONICAL_ACTION_TITLE_PREDICTION:
        kp.append(chat_msg(locale, "reply_semantics.missing_info.pred_no_history_before_confirm"))
    return AgentSemanticPayload(
        mode="missing_info",
        user_intent=chat_msg(locale, "reply_semantics.missing_info.user_intent"),
        summary=chat_msg(
            locale,
            "reply_semantics.missing_info.summary_missing_items",
            title=(display_title if _en(locale) else action_title),
        ),
        key_points=kp,
        observations=[context_note] if context_note else [],
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.missing_info.next_complete_fields"),
            chat_msg(locale, "reply_semantics.missing_info.next_start_again"),
        ],
        blocked_actions=[chat_msg(locale, "reply_semantics.missing_info.block_no_fake_job")],
        safety_notes=[],
        pending_action_preview=None,
        missing_fields=list(missing_fields_zh),
        response_tone="calm",
        locale=locale,
        verbatim_policy="allowed",
        verbatim_reply_to_paraphrase=verbatim,
    )


def build_cannot_execute_payload(
    *,
    user_message: str,
    action_title: str,
    reason: str,
    missing_fields_zh: Optional[List[str]] = None,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """Cannot enter pending state: strict factual boundary, verbatim_required."""
    display_title = _action_title(action_title, locale)
    tail = "" if (REASON_SKIP_APPEND_TAIL_IF_CONTAINS in reason or _en(locale)) else chat_msg(locale, "reply_semantics.cannot_execute.append_complete_info_tail")
    verbatim = (
        reason.rstrip(ZH_FULLWIDTH_PERIOD) + ZH_FULLWIDTH_PERIOD + tail
    ).replace(ZH_FULLWIDTH_PERIOD + ZH_FULLWIDTH_PERIOD, ZH_FULLWIDTH_PERIOD)
    return AgentSemanticPayload(
        mode="cannot_execute",
        user_intent=chat_msg(locale, "reply_semantics.cannot_execute.user_intent"),
        summary=reason,
        key_points=[
            chat_msg(
                locale,
                "reply_semantics.cannot_execute.key_relevant_capability",
                title=(display_title if _en(locale) else action_title),
            )
        ],
        observations=[],
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.cannot_execute.next_check_page_mode"),
            chat_msg(locale, "reply_semantics.cannot_execute.next_complete_contract_fields"),
        ],
        blocked_actions=[chat_msg(locale, "reply_semantics.cannot_execute.block_no_bypass_pending")],
        safety_notes=[],
        missing_fields=list(missing_fields_zh or []),
        response_tone="calm",
        locale=locale,
        verbatim_policy="required",
        verbatim_reply_to_paraphrase=verbatim,
    )


def build_status_payload(
    *,
    user_message: str,
    user_intent: str,
    status_bullets: List[str],
    summary: Optional[str] = None,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """
    Progress/status semantics: verbatim_forbidden.
    The orchestrator may pass a one-sentence factual anchor aligned with the previous concise path.
    """
    sm = summary if summary is not None else chat_msg(locale, "reply_semantics.status.default_summary")
    return AgentSemanticPayload(
        mode="status",
        user_intent=user_intent,
        summary=sm,
        key_points=list(status_bullets),
        observations=[
            chat_msg(locale, "reply_semantics.status.obs_public_fields_only"),
            chat_msg(locale, "reply_semantics.status.obs_explain_stuck_and_next"),
        ],
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.status.next_open_task_details"),
            chat_msg(locale, "reply_semantics.status.next_prediction_explanation_entry"),
        ],
        blocked_actions=[chat_msg(locale, "reply_semantics.status.block_no_fabricate_or_rows")],
        safety_notes=[],
        missing_fields=[],
        response_tone="calm",
        locale=locale,
        verbatim_policy="forbidden",
        verbatim_reply_to_paraphrase=None,
    )


def build_terminal_result_payload(
    *,
    user_message: str,
    object_kind: str,
    intent: str,
    fallback_deterministic_reply: str,
    verbatim_policy: Optional[VerbatimPolicy] = None,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    pol = verbatim_policy if verbatim_policy is not None else terminal_result_verbatim_policy(intent)
    obs = [chat_msg(locale, "reply_semantics.terminal_result.obs_bind_selected_facts")]
    if str(object_kind) == "train" and str(intent) in ("train_good_bad", "train_performance", "default", ""):
        obs.append(chat_msg(locale, "reply_semantics.terminal_result.obs_train_metric_interpretation"))
    obj_label = chat_msg(
        locale,
        (
            "reply_semantics.terminal_result.object_kind.training"
            if str(object_kind) == "train"
            else "reply_semantics.terminal_result.object_kind.prediction"
        ),
    )
    return AgentSemanticPayload(
        mode="terminal_result",
        user_intent=chat_msg(locale, "reply_semantics.terminal_result.user_intent"),
        summary=chat_msg(locale, "reply_semantics.terminal_result.summary_for_task", label=obj_label),
        key_points=[
            chat_msg(locale, "reply_semantics.terminal_result.key_intent_label", intent=intent),
            chat_msg(locale, "reply_semantics.terminal_result.key_stay_on_facts"),
        ],
        observations=obs,
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.terminal_result.next_review_metrics"),
            chat_msg(locale, "reply_semantics.terminal_result.next_retry_after_fix"),
        ],
        blocked_actions=[chat_msg(locale, "reply_semantics.terminal_result.block_no_fake_current")],
        safety_notes=[],
        missing_fields=[],
        response_tone="calm",
        locale=locale,
        verbatim_policy=pol,
        verbatim_reply_to_paraphrase=fallback_deterministic_reply,
    )


def build_sticky_no_prediction_payload(*, user_message: str, fallback_deterministic_reply: str, locale: Optional[str] = None) -> AgentSemanticPayload:
    """No current prediction is readable; keep a strict deterministic fallback."""
    return AgentSemanticPayload(
        mode="sticky_no_prediction",
        user_intent=chat_msg(locale, "reply_semantics.sticky_no_prediction.user_intent"),
        summary=chat_msg(locale, "reply_semantics.sticky_no_prediction.summary"),
        key_points=[chat_msg(locale, "reply_semantics.sticky_no_prediction.key_no_bound_record")],
        observations=[chat_msg(locale, "reply_semantics.sticky_no_prediction.obs_complete_flow_first")],
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.sticky_no_prediction.next_configure_prediction"),
            chat_msg(locale, "reply_semantics.sticky_no_prediction.next_then_ask_label_prob"),
        ],
        blocked_actions=[chat_msg(locale, "reply_semantics.sticky_no_prediction.block_no_guess_from_model")],
        safety_notes=[],
        missing_fields=[],
        response_tone="calm",
        locale=locale,
        verbatim_policy="required",
        verbatim_reply_to_paraphrase=fallback_deterministic_reply,
    )


def build_disclaimed_latest_prediction_payload(
    *,
    user_message: str,
    fallback_deterministic_reply: str,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """History vs current workspace: strong disclaimer, verbatim_required."""
    return AgentSemanticPayload(
        mode="tool_result",
        user_intent=chat_msg(locale, "reply_semantics.disclaimed_prediction.user_intent"),
        summary=chat_msg(locale, "reply_semantics.disclaimed_prediction.summary"),
        key_points=[chat_msg(locale, "reply_semantics.disclaimed_prediction.key_historical_index")],
        observations=[],
        allowed_next_steps=[
            chat_msg(locale, "reply_semantics.disclaimed_prediction.next_run_prediction_first"),
            chat_msg(locale, "reply_semantics.disclaimed_prediction.next_check_history"),
        ],
        blocked_actions=[chat_msg(locale, "reply_semantics.disclaimed_prediction.block_no_equate_history")],
        safety_notes=[],
        missing_fields=[],
        response_tone="calm",
        locale=locale,
        verbatim_policy="required",
        verbatim_reply_to_paraphrase=fallback_deterministic_reply,
    )


def status_bullets_from_concise_hit(
    task_public: Dict[str, Any], scene: str, *, locale: Optional[str] = None
) -> List[str]:
    """Build bullet points from sanitized public task fields."""
    if not task_public:
        return []
    jid = str(task_public.get("id") or "").strip()
    jt = str(task_public.get("job_type") or "")
    st = str(task_public.get("status") or "")
    prog = task_public.get("progress")
    stage = str(task_public.get("current_stage") or "").strip()
    if jt == "train_model":
        jt_disp = chat_msg(locale, "reply_semantics.status_bullet.job_type.training")
    elif jt == "predict_outcome":
        jt_disp = chat_msg(locale, "reply_semantics.status_bullet.job_type.prediction")
    else:
        jt_disp = chat_msg(locale, "reply_semantics.status_bullet.job_type.unknown")
    unk = chat_msg(locale, "reply_semantics.status_bullet.job_type.unknown")
    st_disp = st or unk
    lines = [
        chat_msg(locale, "reply_semantics.status_bullet.job_type_line", value=jt_disp),
        chat_msg(locale, "reply_semantics.status_bullet.status_line", value=st_disp),
    ]
    if prog is not None:
        lines.append(chat_msg(locale, "reply_semantics.status_bullet.progress_line", value=prog))
    if stage:
        lines.append(chat_msg(locale, "reply_semantics.status_bullet.stage_line", snippet=stage[:120]))
    if jid.startswith("job_"):
        lines.append(chat_msg(locale, "reply_semantics.status_bullet.internal_job_hint"))
    lines.append(chat_msg(locale, "reply_semantics.status_bullet.matched_scene", scene=scene))
    return lines


# --- workflow_guidance: English display for locale=en (rules layer stays Chinese in workflow_rules) ---

WORKFLOW_GUIDANCE_EN_FALLBACK_STEP = "Review the current workflow state in the workspace."

_WORKFLOW_BLOCKER_MESSAGE_EN: Dict[str, str] = {
    "no_training_task": "No training task is bound to the current workspace context.",
    "waiting_confirm": "The workflow is waiting for you to confirm the current step in the UI.",
    "task_running": "A workflow task is running in the background; check the task panel for progress.",
    "none": "No blocking issue for this workflow snapshot.",
    "task_failed": "The task failed or was interrupted; open task details for logs and the error summary.",
    "queued": "The task is queued and has not started executing yet.",
    "unknown_train_state": "Training status is unclear from this snapshot; open task details to verify the current stage.",
    "missing_model": "No prediction model is selected in the workspace yet.",
    "missing_dataset": "Batch prediction still needs an uploaded file or equivalent input.",
    "mapping_incomplete": "Column mapping is incomplete or some fields are still unresolved.",
    "ready_batch": "Batch prediction is ready to submit or waiting for you to confirm execution.",
    "no_result_yet": "No completed prediction result is available to bind yet, or the focus task is still in progress.",
    "missing_regimens": "No enabled candidate regimens are available in the regimen library.",
    "missing_schema": "The patient feature schema for recommendations has not been loaded yet.",
    "incomplete_features": "Patient features are not yet complete per the form requirements.",
    "ready_to_run": "The recommendation flow is ready to draft; execution only starts after you confirm.",
    "task_queued": "The recommendation task is queued or waiting to start; it is not computing yet.",
    "insufficient_context": "There is no clear workflow anchor in the current context.",
}


_WORKFLOW_CANDIDATE_TITLE_REASON_EN: Dict[str, Tuple[str, str]] = {
    "start_or_open_training": (
        "Start training from the workbench or select an in-progress training task",
        "A training task context is required before discussing confirmation steps and follow-up configuration.",
    ),
    "draft_training_explore": (
        "Describe your training goal in chat to generate a training configuration draft",
        "If you have not started yet, describe requirements in natural language; the workbench will prepare a card to confirm, not start training directly in chat.",
    ),
    "confirm_training_card": (
        "Review the training confirmation card and click confirm",
        "The current step is ready; explicit confirmation in the UI is required before the backend continues.",
    ),
    "review_then_confirm": (
        "Review the summary quickly, then confirm",
        "This step usually involves reviewing the confirmation card content (features, configuration, or release) before you continue.",
    ),
    "draft_training_adjust": (
        "If you need to change conditions, describe them in chat to regenerate a training draft",
        "Major parameter changes should still go through draft and confirmation; the system will not silently change a running job.",
    ),
    "wait_train": (
        "Wait for the current stage to finish and watch progress in the task panel",
        "While compute is running, UI confirmation may need to wait until this stage ends or the system asks again.",
    ),
    "open_task_detail": (
        "Open task details to review logs and stage hints",
        "Use the task detail page when you need finer-grained execution information.",
    ),
    "review_train_outcome": (
        "Review metrics and artifacts in task details",
        "Check the headline and metric blocks first, then decide whether to publish or use the model downstream.",
    ),
    "goto_prediction_or_rec": (
        "If the model is ready, move on to prediction or regimen comparison",
        "Downstream actions still require their own confirmations; nothing auto-runs from chat.",
    ),
    "inspect_failure_train": (
        "Review failure details and logs in task details",
        "Identify the failed stage first, then decide whether to retry or adjust data or configuration.",
    ),
    "draft_training_retry": (
        "After fixes, start a new training configuration draft",
        "Retraining still goes through confirmation cards; chat will not directly restart training.",
    ),
    "wait_queue": (
        "Wait in the queue and watch the task panel",
        "Execution will move to running automatically when it is this task's turn.",
    ),
    "open_task_train": (
        "Open task details to verify the current stage",
        "Use the task repository state as the source of truth.",
    ),
    "pick_model": (
        "Select a target model in the model list first",
        "Prediction entry depends on a model id; without a model, feature schema alignment is not available.",
    ),
    "open_predict_entry": (
        "Open the unified prediction entry (single-sample or batch)",
        "Complete inputs and confirm execution inside the card after you enter.",
    ),
    "upload_batch_file": (
        "Upload the data file in the batch prediction card",
        "Without an input file, columns cannot be aligned and mapping cannot finish.",
    ),
    "finish_column_mapping": (
        "Finish field mapping and save",
        "Mapping defines which inputs the model can read; do not submit before it is complete.",
    ),
    "wait_batch": (
        "Wait for the batch job to finish and check status in the task list",
        "Batch duration scales with row count; use task details as the source of truth.",
    ),
    "review_batch_summary": (
        "Review aggregate row counts and download entry in task details or history",
        "Check success and failure counts first, then decide whether to rerun or sample-check rows.",
    ),
    "consider_rec": (
        "If clinically needed, switch to medication recommendation (survival benefit)",
        "Recommendation still requires separate confirmation; it will not auto-trigger from chat.",
    ),
    "confirm_batch_run": (
        "Review mapping in the batch prediction card, then confirm execution",
        "Execution follows the main confirmation chain; chat will not write results directly.",
    ),
    "draft_batch_explainer": (
        "Optionally adjust task name or notes in the card before confirming",
        "Small edits reduce accidental runs.",
    ),
    "read_prediction_explanation": (
        "Review the prediction summary and explanation (if available)",
        "Understand label, probability, and explanation framing before moving to recommendation or other flows.",
    ),
    "goto_rec_if_needed": (
        "If regimen-level comparison is needed, use the medication recommendation workflow",
        "Recommendation and prediction use different confirmation chains; they do not auto-chain.",
    ),
    "draft_single_prediction": (
        "Generate a pending single-sample prediction draft (preferred when a model is selected)",
        "The draft only frames model and fields; a prediction task is created only after confirmation, not inferred directly in chat.",
    ),
    "fill_single_or_batch": (
        "Complete inputs in the prediction workspace (single-sample form or batch file and mapping)",
        "Execution must be confirmed in the card; the system will not fill real patient values for you.",
    ),
    "open_regimen_management": (
        "Enable at least one candidate regimen in regimen management first",
        "Expand the enabled regimen list before drafting a recommendation task.",
    ),
    "load_rec_schema": (
        "Select a survival model in the recommendation card and load the feature table",
        "Field definitions must be aligned before safely collecting non-treatment features.",
    ),
    "complete_rec_form": (
        "Complete non-treatment features per the form and resolve validation prompts",
        "Scoring depends on complete input; drafting may be blocked until the form is complete.",
    ),
    "submit_rec_when_ready": (
        "Generate a pending recommendation draft (review and confirm execution in the UI)",
        "The best next step is to create a pending draft first; chat will not directly create a recommendation task.",
    ),
    "draft_rec_explore": (
        "If parameters are uncertain, adjust them in the workbench before asking for a draft",
        "Reduces accidental submission; pending confirmation is still required.",
    ),
    "view_task_status": (
        "Check recommendation task status and stage in the task list",
        "At this stage, avoid drafting another recommendation; focus on queue position and timing.",
    ),
    "wait_for_completion": (
        "Wait until the task completes, then review ranking and explanation entry points",
        "Do not draft another pending recommendation while compute is still running.",
    ),
    "view_ranked_regimens": (
        "Review regimen ranking and probability summary in the recommendation result card",
        "After completion, prefer understanding ranking and confidence before submitting another recommendation.",
    ),
    "compare_original_vs_top1": (
        "Compare the current regimen with the top-1 recommended regimen",
        "Side-by-side comparison helps assess clinical acceptability and benefit signals.",
    ),
    "view_explanation": (
        "If the UI offers an explanation entry, review feature contributions or notes",
        "Explanations follow de-identified workbench presentation rules.",
    ),
    "return_to_prediction_or_next_step": (
        "To refresh inputs, re-check prediction, or continue another workflow, return to the relevant workbench page",
        "Prediction and recommendation confirmation paths are separate; they do not auto-continue.",
    ),
    "view_error": (
        "Read the full error message and stage in task details",
        "Understand the failure reason before retrying blindly.",
    ),
    "fix_preconditions": (
        "Check model, regimen library, and required fields based on the error summary",
        "Restore preconditions before asking for next-step guidance again; this path does not directly retry execution.",
    ),
    "redraft_recommendation_if_applicable": (
        "After recovery, ask for next steps again to generate a new pending recommendation draft",
        "Retry only through the main pending chain when workbench conditions are satisfied; chat does not execute on your behalf.",
    ),
    "generic_rec": (
        "Open the medication recommendation card in the workbench and complete each guided step",
        "The recommendation chain has many steps; follow UI validation as the source of truth.",
    ),
    "pick_workflow": (
        "Select a training, prediction, or recommendation related page in the workbench first",
        "With a page mode or focus task, the system can align suggestions reliably.",
    ),
    "describe_goal": (
        "State in one sentence whether you want training, prediction, or recommendation",
        "This reduces mistaking configuration actions for general Q&A.",
    ),
}


def workflow_guidance_english_blocker_message(code: Optional[str]) -> str:
    c = str(code or "").strip()
    return _WORKFLOW_BLOCKER_MESSAGE_EN.get(c, WORKFLOW_GUIDANCE_EN_FALLBACK_STEP)


def workflow_guidance_english_candidate_title_reason(cand: Dict[str, Any]) -> Tuple[str, str]:
    cid = str(cand.get("id") or "").strip()
    pair = _WORKFLOW_CANDIDATE_TITLE_REASON_EN.get(cid)
    if pair:
        return pair
    return (WORKFLOW_GUIDANCE_EN_FALLBACK_STEP, WORKFLOW_GUIDANCE_EN_FALLBACK_STEP)


def _followup_actions_display_en(actions: List[Any]) -> str:
    """Map known Chinese follow-up labels to English tokens for key_points; keep ASCII tokens as-is."""
    label_map = FOLLOWUP_ACTION_LABEL_ZH_TO_EN
    out: List[str] = []
    for x in actions[:10]:
        s = str(x).strip()
        if not s:
            continue
        if re.search(r"[\u4e00-\u9fff]", s):
            out.append(label_map.get(s, "follow_up_action"))
        else:
            out.append(s)
    return ",".join(out)


def clone_workflow_guidance_bundle_for_locale(bundle: Dict[str, Any], locale: Optional[str]) -> Dict[str, Any]:
    """Return API-facing bundle: English fields when locale is English; otherwise the original object."""
    if not _en(locale):
        return bundle
    out = copy.deepcopy(bundle)
    brs = out.get("blocking_reasons")
    if isinstance(brs, list):
        for b in brs:
            if isinstance(b, dict):
                code = str(b.get("code") or "").strip()
                b["message"] = workflow_guidance_english_blocker_message(code or None)
    cands = out.get("next_step_candidates")
    rec = out.get("recommended_action")
    if isinstance(rec, dict):
        cid = str(rec.get("id") or "").strip()
        if cid:
            t, r = workflow_guidance_english_candidate_title_reason({"id": cid})
            if "title" in rec:
                rec["title"] = t
            if "reason" in rec:
                rec["reason"] = r
        if "message" in rec:
            code = str(rec.get("code") or "").strip()
            rec["message"] = workflow_guidance_english_blocker_message(code or None)
    if isinstance(cands, list):
        for c in cands:
            if isinstance(c, dict):
                t, r = workflow_guidance_english_candidate_title_reason(c)
                c["title"] = t
                c["reason"] = r
    return out


def build_workflow_guidance_payload(
    *,
    user_message: str,
    workflow_bundle: Dict[str, Any],
    deterministic_summary: str,
    locale: Optional[str] = None,
) -> AgentSemanticPayload:
    """Workflow guidance semantics; the structured snapshot is already locked by rules."""
    cands = workflow_bundle.get("next_step_candidates") or []
    cands_list = [c for c in cands if isinstance(c, dict)]
    titles = [str(c.get("title") or "").strip() for c in cands_list][:6]
    en_titles = [workflow_guidance_english_candidate_title_reason(c)[0] for c in cands_list][:6]
    rec = workflow_bundle.get("recommended_action") or {}
    rid = str(rec.get("id") or "")
    rkind = str(rec.get("kind") or "guide")
    kp = [
        chat_msg(locale, "reply_semantics.workflow_guidance.key_domain", domain=workflow_bundle.get("workflow_domain")),
        chat_msg(locale, "reply_semantics.workflow_guidance.key_stage", stage=workflow_bundle.get("workflow_stage")),
        chat_msg(locale, "reply_semantics.workflow_guidance.key_goal", goal=workflow_bundle.get("workflow_goal")),
    ]
    if str(workflow_bundle.get("workflow_domain") or "") == "recommendation":
        rs = str(workflow_bundle.get("recommendation_state") or "")
        if rs:
            kp.append(chat_msg(locale, "reply_semantics.workflow_guidance.key_rec_state", state=rs))
        hbp = workflow_bundle.get("has_bound_prediction_result")
        if hbp is not None:
            kp.append(chat_msg(locale, "reply_semantics.workflow_guidance.key_prediction_bind_signal", flag=hbp))
        fa = workflow_bundle.get("followup_actions")
        if isinstance(fa, list) and fa:
            if _en(locale):
                kp.append(
                    "Follow-up actions to organize (guidance only, not execution): " + _followup_actions_display_en(fa)
                )
            else:
                kp.append(
                    chat_msg(locale, "reply_semantics.workflow_guidance.followup_actions_prefix")
                    + ",".join(str(x) for x in fa[:10])
                )
    br = workflow_bundle.get("blocking_reasons") or []
    if isinstance(br, list) and br:
        if _en(locale):
            seg = "; ".join(
                f"{b.get('code')}:{workflow_guidance_english_blocker_message(str(b.get('code') or ''))}"
                for b in br[:4]
                if isinstance(b, dict)
            )
            kp.append("Blocking points (code: guidance): " + seg)
        else:
            kp.append(
                chat_msg(locale, "reply_semantics.workflow_guidance.blocking_points_prefix")
                + "; ".join(f"{b.get('code')}:{b.get('message')}" for b in br[:4] if isinstance(b, dict))
            )
    display_titles = en_titles if _en(locale) else titles
    if display_titles:
        kp.append(chat_msg(locale, "reply_semantics.workflow_guidance.candidate_next_steps_prefix") + " | ".join(display_titles))
    kp.append(chat_msg(locale, "reply_semantics.workflow_guidance.key_system_recommended_action", rid=rid, kind=rkind))
    obs = [
        chat_msg(locale, "reply_semantics.workflow_guidance.obs_three_part_reply"),
        chat_msg(locale, "reply_semantics.workflow_guidance.obs_no_claim_execution_or_tables"),
        chat_msg(locale, "reply_semantics.workflow_guidance.obs_draft_requires_confirm"),
    ]
    if str(workflow_bundle.get("workflow_domain") or "") == "recommendation":
        obs.append(chat_msg(locale, "reply_semantics.workflow_guidance.obs_recommendation_organizer_tone"))
    if _en(locale):
        if en_titles:
            primary_next = str(en_titles[0]).strip()
        else:
            primary_next = WORKFLOW_GUIDANCE_EN_FALLBACK_STEP
    elif titles:
        primary_next = str(titles[0]).strip()
    else:
        primary_next = chat_msg(locale, "reply_semantics.workflow_guidance.primary_next_fallback")
    return AgentSemanticPayload(
        mode="workflow_guidance",
        user_intent=chat_msg(locale, "reply_semantics.workflow_guidance.user_intent"),
        summary=deterministic_summary.strip(),
        key_points=kp,
        observations=obs,
        allowed_next_steps=[primary_next],
        blocked_actions=[
            chat_msg(locale, "reply_semantics.workflow_guidance.block_no_bypass_pending"),
            chat_msg(locale, "reply_semantics.workflow_guidance.block_no_patient_feature_table"),
        ],
        safety_notes=[chat_msg(locale, "reply_semantics.workflow_guidance.safety_execution_after_ui_confirm")],
        missing_fields=[],
        response_tone="direct",
        locale=locale,
        verbatim_policy="allowed",
        verbatim_reply_to_paraphrase=deterministic_summary.strip() or None,
    )
