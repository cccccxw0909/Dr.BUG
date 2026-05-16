"""
Response verbalizer: turns ResponsePayload into a natural-language assistant_message.

- Not a planner/executor; must not invent facts or change numeric/state semantics.
- On LLM failure, empty reply, or exceptions, fall back to render_strict_template.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, MutableSequence, Optional, Tuple

from backend.agent.prompts.agent_instruction import (
    INTERNAL_RULE_LAYER_HEADER,
    build_orchestrator_runtime_agent_instruction,
)
from backend.agent.chat_output_locale import normalize_chat_output_locale
from backend.agent.i18n import chat_msg
from backend.agent.i18n.lexicons.zh_prediction_label_display import PREDICTED_LABEL_ZH_TO_EN
from backend.agent.i18n.lexicons.zh_typography import (
    ZH_FULLWIDTH_PERIOD,
    ZH_FULLWIDTH_SEMICOLON,
    ZH_IDEOGRAPHIC_COMMA,
    ZH_SENTENCE_TERMINATORS,
)
from backend.agent.response_payloads import ResponsePayload, is_llm_polish_answer_type
from backend.llm.base import LLMProviderError
from backend.schemas.agent import ChatTurnRequest


def _rv_msg(locale: str, key: str, **kwargs: Any) -> str:
    """Deterministic strict-template line from the response verbalizer message catalog."""
    return chat_msg(locale, key, **kwargs)


_WS = re.compile(r"\s+")
_HAN = re.compile(r"[\u4e00-\u9fff]")


def _chat_output_locale(req: Optional[ChatTurnRequest]) -> str:
    """en vs zh for deterministic user-facing copy (locale hint + message inference)."""
    if req is None:
        return "en"
    return normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)


def _contains_han(text: Any) -> bool:
    return bool(_HAN.search(str(text or "")))


def _fmt_probability_pct(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if 0 <= x <= 1:
        return f"{x * 100:.1f}%"
    return f"{x:.1f}%"


def _fmt_delta_pp(v: Any) -> Optional[Tuple[str, str]]:
    """(sign, magnitude) for percentage-point delta text."""
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    pts = x * 100 if abs(x) <= 1 else x
    if pts >= 0:
        return "+", f"{abs(pts):.1f}"
    return "−", f"{abs(pts):.1f}"


def _regimen_row_display_name(row: Dict[str, Any]) -> str:
    name = str(row.get("regimen_name") or "").strip()
    if name:
        return name
    rid = str(row.get("regimen_id") or "").strip()
    return rid or "—"

VERBALIZER_SYSTEM_EN = (
    "You are the clinical AI workbench response verbalizer (polisher), not a task planner or tool executor.\n"
    "You may ONLY reorganize the user's message together with the locked factual materials below into clear, "
    "professional English. Do not add conclusions, numbers, probabilities, labels, task states, routing, "
    "or execution outcomes that are not explicitly supported by the materials.\n"
    "Do not change the meaning of the 'next step' sentence; do not claim training/prediction/recommendation "
    "already ran; do not output JSON; do not explain these rules; do not expose internal field names or raw "
    "English API keys to the user.\n"
    "If materials indicate the user still must confirm in the UI, preserve that meaning (not executed yet).\n"
    "If materials list sentences that must be preserved, keep their meaning (light wording edits allowed; "
    "do not weaken or contradict).\n"
    "Tone: concise, professional, trustworthy; do not fabricate patient-level tables or row-level data.\n"
    "Write the final user-visible reply in English."
)

VERBALIZER_INTERNAL_RULES_EN = (
    "\n\n---\n[Internal policy — do not repeat this header to the user]\n"
    "Respect tool boundaries; do not fabricate task states; prefer calm clinical workbench language.\n"
    "When a welcome/onboarding path already answered the user, do not assume a free-form chat chain continues.\n"
    "If a high-risk pending confirmation exists, remind the user to review the pending card before confirming.\n"
)


def should_use_llm_verbalizer(
    *,
    answer_type: str,
    route: Optional[str] = None,
    maybe_error_state: bool = False,
) -> bool:
    """
    Gradual rollout: llm_polish only for selected answer_types; high-risk/short/error paths stay strict.
    route / maybe_error_state are reserved hooks aligned with the orchestrator.
    """
    _ = route
    at = str(answer_type or "").strip()
    if at in (
        "pending_confirm",
        "fallback_template",
        "error",
        "strict_status",
        "empty",
        "recommendation_result",
        "batch_prediction_result",
        "training_failed",
        "prediction_failed",
    ):
        return False
    return is_llm_polish_answer_type(at, maybe_error_state=maybe_error_state)


def _facts_block(payload: ResponsePayload) -> str:
    slim = dict(payload.facts or {})
    bundles = slim.get("tool_fact_bundles")
    if bundles is not None:
        try:
            raw = json.dumps(bundles, ensure_ascii=False)
        except (TypeError, ValueError):
            raw = str(bundles)
        if len(raw) > 14000:
            raw = raw[:13999] + "…"
        slim = {k: v for k, v in slim.items() if k != "tool_fact_bundles"}
        slim["tool_fact_bundles_json"] = raw
    try:
        dumped = json.dumps(slim, ensure_ascii=False)
    except (TypeError, ValueError):
        dumped = str(slim)
    if len(dumped) > 16000:
        dumped = dumped[:15999] + "…"
    return dumped


def build_verbalizer_messages(
    payload: ResponsePayload,
    req: ChatTurnRequest,
) -> List[Dict[str, str]]:
    """Build verbalizer chat messages (single user turn) matching the existing provider.chat contract."""
    loc = normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    ctx = req.chat_context or {}
    mode = str(ctx.get("mode") or "").strip() or "unknown"
    brief = _rv_msg(loc, "response_verbalizer.llm_polish.user_brief_zh", mode=mode)
    points = "\n".join(f"- {x}" for x in payload.summary_points[:40]) or _rv_msg(
        loc, "response_verbalizer.llm_polish.user_points_empty_zh"
    )
    strict = "\n".join(f"- {x}" for x in payload.strict_lines[:20]) or _rv_msg(
        loc, "response_verbalizer.llm_polish.user_strict_empty_zh"
    )
    warns = "\n".join(f"- {x}" for x in payload.warnings[:20]) or _rv_msg(
        loc, "response_verbalizer.llm_polish.user_warns_empty_zh"
    )
    na = payload.next_action or _rv_msg(loc, "response_verbalizer.llm_polish.user_next_action_empty_zh")
    batch_extra = (
        _rv_msg(loc, "response_verbalizer.llm_polish.constraints.batch_prediction_zh")
        if payload.answer_type == "batch_prediction_result"
        else ""
    )
    pred_extra = (
        _rv_msg(loc, "response_verbalizer.llm_polish.constraints.prediction_result_zh")
        if payload.answer_type == "prediction_result"
        else ""
    )
    train_extra = (
        _rv_msg(loc, "response_verbalizer.llm_polish.constraints.training_completed_zh")
        if payload.answer_type == "training_completed"
        else ""
    )
    draft_train_extra = (
        _rv_msg(loc, "response_verbalizer.llm_polish.constraints.training_draft_created_zh")
        if payload.answer_type == "training_draft_created"
        else ""
    )
    train_fail_extra = (
        _rv_msg(loc, "response_verbalizer.llm_polish.constraints.training_failed_zh")
        if payload.answer_type == "training_failed"
        else ""
    )
    pred_fail_extra = (
        _rv_msg(loc, "response_verbalizer.llm_polish.constraints.prediction_failed_zh")
        if payload.answer_type == "prediction_failed"
        else ""
    )
    extras = batch_extra + pred_extra + train_extra + draft_train_extra + train_fail_extra + pred_fail_extra
    msg_t = (req.message or "").strip()
    user = "\n".join(
        [
            _rv_msg(loc, "response_verbalizer.llm_polish.user_original_zh", text=msg_t),
            brief,
            "",
            _rv_msg(loc, "response_verbalizer.llm_polish.user_answer_type_zh", answer_type=payload.answer_type),
            extras,
            "",
            _rv_msg(loc, "response_verbalizer.llm_polish.user_facts_header_zh"),
            _facts_block(payload),
            "",
            _rv_msg(loc, "response_verbalizer.llm_polish.user_points_header_zh"),
            points,
            "",
            _rv_msg(loc, "response_verbalizer.llm_polish.user_strict_header_zh"),
            strict,
            "",
            _rv_msg(loc, "response_verbalizer.llm_polish.user_warns_header_zh"),
            warns,
            "",
            _rv_msg(loc, "response_verbalizer.llm_polish.user_next_header_zh", na=na),
        ]
    )
    if loc == "en":
        system = f"{VERBALIZER_SYSTEM_EN}{VERBALIZER_INTERNAL_RULES_EN}"
    else:
        system = (
            f"{_rv_msg(loc, 'response_verbalizer.llm_polish.system_zh')}"
            f"{INTERNAL_RULE_LAYER_HEADER}"
            f"{build_orchestrator_runtime_agent_instruction()}"
        )
    user = re.sub(r"\n{3,}", "\n\n", user).strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def verbalize_training_draft_created(
    payload: ResponsePayload,
    req: Optional[ChatTurnRequest] = None,
) -> str:
    """
    training_draft_created: render from structured facts (zh/en) only; do not splice legacy summary_points / warning
    templates so en-US UI does not pick up stray Chinese bullets.
    """
    loc = "en" if req is None else _chat_output_locale(req)
    facts = dict(payload.facts or {})
    can_confirm = bool(facts.get("can_confirm_in_ui"))
    draft_context = str(facts.get("draft_context") or "standard").strip()
    raw_cs = str(facts.get("completed_summary") or "").strip()
    keys_raw = facts.get("missing_field_keys")
    keys: List[str] = []
    if isinstance(keys_raw, list):
        keys = [str(k).strip() for k in keys_raw if str(k).strip()]

    completed_zh = raw_cs or _rv_msg("zh", "response_verbalizer.training_draft.placeholder_none")
    completed_en = raw_cs or _rv_msg("en", "response_verbalizer.training_draft.placeholder_none")
    miss_join_zh = ZH_IDEOGRAPHIC_COMMA.join(keys) if keys else _rv_msg("zh", "response_verbalizer.training_draft.placeholder_none")
    miss_join_en = ", ".join(keys) if keys else _rv_msg("en", "response_verbalizer.training_draft.placeholder_none")

    primary_next_zh = str(facts.get("primary_next_step_zh") or "").strip()

    if loc == "en":
        lines_en: List[str] = []
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.headline"))
        if can_confirm:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.card_ready"))
        else:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.card_incomplete"))
        lines_en.append("")
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.parsed_summary", summary=completed_en))
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.missing_fields", missing=miss_join_en))
        lines_en.append("")
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.not_started"))
        if not can_confirm:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.no_job_until_filled"))
        else:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.no_job_until_ui_confirm"))
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.draft_only_backend"))
        lines_en.append("")
        if draft_context == "workflow_continue":
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.after_intro_workflow"))
        else:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.after_intro_standard"))
        lines_en.append("")
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.execution_after_confirm"))
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.do_not_claim_started"))
        lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.do_not_invent_metrics"))
        lines_en.append("")
        if can_confirm:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.next_review_card"))
        else:
            lines_en.append(_rv_msg("en", "response_verbalizer.training_draft.next_complete_fields"))
        return "\n".join(lines_en).strip()

    lines: List[str] = []
    stage = (
        _rv_msg(loc, "response_verbalizer.training_draft.stage_can_confirm")
        if can_confirm
        else _rv_msg(loc, "response_verbalizer.training_draft.stage_need_fill")
    )
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.opening", stage=stage))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_parsed", summary=completed_zh))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_missing", missing=miss_join_zh))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_not_started"))
    if not can_confirm:
        lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_wait_fill"))
    else:
        lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_after_confirm"))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_draft_state"))
    if primary_next_zh:
        lines.append(_rv_msg(loc, "response_verbalizer.common.next_step", action=primary_next_zh))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_round_is_draft"))
    if can_confirm:
        lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_pending_confirm"))
    else:
        lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_pending_incomplete"))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_execution_rights"))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_no_false_claims"))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_no_false_state"))
    lines.append(_rv_msg(loc, "response_verbalizer.training_draft.line_no_invent_metrics"))
    out = "\n".join(lines).strip()
    return out or chat_msg("zh", "response_verbalizer.training_draft.fallback_when_empty")


def verbalize_training_failed(
    payload: ResponsePayload,
    req: Optional[ChatTurnRequest] = None,
) -> str:
    """training_failed: template organizes bucket/hint/next_action already locked in facts; adds no new truth."""
    loc = "en" if req is None else _chat_output_locale(req)
    facts = payload.facts or {}
    if req is None and any(
        _contains_han(facts.get(k)) for k in ("failure_stage_bucket", "error_hint")
    ):
        loc = "zh"
    variant = str(facts.get("failure_reply_variant") or "default")
    na = (payload.next_action or "").strip()
    if loc == "en":
        bucket = str(facts.get("failure_stage_bucket") or "").strip() or _rv_msg(
            loc, "response_verbalizer.training_failed.default_bucket"
        )
        hint = str(facts.get("error_hint") or "").strip() or _rv_msg(loc, "response_verbalizer.training_failed.default_hint")
        if variant == "fail_check_first":
            core = _rv_msg(loc, "response_verbalizer.training_failed.core_fail_check_first", bucket=bucket, hint=hint)
        else:
            core = _rv_msg(loc, "response_verbalizer.training_failed.core_default", bucket=bucket, hint=hint)
        if not na:
            return core.strip()
        return f"{core.rstrip()}{_rv_msg(loc, 'response_verbalizer.training_failed.next_step_with_na', na=na)}"
    bucket = str(facts.get("failure_stage_bucket") or "").strip() or _rv_msg(
        loc, "response_verbalizer.training_failed.default_bucket"
    )
    hint = str(facts.get("error_hint") or "").strip() or _rv_msg(loc, "response_verbalizer.training_failed.default_hint")
    if variant == "fail_check_first":
        core = _rv_msg(loc, "response_verbalizer.training_failed.core_fail_check_first", bucket=bucket, hint=hint)
    else:
        core = _rv_msg(loc, "response_verbalizer.training_failed.core_default", bucket=bucket, hint=hint)
    if not na:
        return core.strip()
    b = core.rstrip()
    if not b.endswith(ZH_SENTENCE_TERMINATORS):
        b = f"{b}{ZH_FULLWIDTH_PERIOD}"
    return f"{b}{_rv_msg(loc, 'response_verbalizer.training_failed.next_step_with_na', na=na)}"


def verbalize_prediction_failed(
    payload: ResponsePayload,
    req: Optional[ChatTurnRequest] = None,
) -> str:
    """prediction_failed: template organizes bucket/hint/next_action already locked in facts."""
    loc = "en" if req is None else _chat_output_locale(req)
    facts = payload.facts or {}
    if req is None and any(
        _contains_han(facts.get(k)) for k in ("failure_stage_bucket", "error_hint")
    ):
        loc = "zh"
    variant = str(facts.get("failure_reply_variant") or "default")
    na = (payload.next_action or "").strip()
    if loc == "en":
        bucket = str(facts.get("failure_stage_bucket") or "").strip() or _rv_msg(
            loc, "response_verbalizer.prediction_failed.default_bucket"
        )
        hint = str(facts.get("error_hint") or "").strip() or _rv_msg(
            loc, "response_verbalizer.prediction_failed.default_hint"
        )
        if variant == "fail_check_first":
            core = _rv_msg(loc, "response_verbalizer.prediction_failed.core_fail_check_first", bucket=bucket, hint=hint)
        else:
            core = _rv_msg(loc, "response_verbalizer.prediction_failed.core_default", bucket=bucket, hint=hint)
        if not na:
            return core.strip()
        return f"{core.rstrip()}{_rv_msg(loc, 'response_verbalizer.prediction_failed.next_step_with_na', na=na)}"
    bucket = str(facts.get("failure_stage_bucket") or "").strip() or _rv_msg(
        loc, "response_verbalizer.prediction_failed.default_bucket"
    )
    hint = str(facts.get("error_hint") or "").strip() or _rv_msg(loc, "response_verbalizer.prediction_failed.default_hint")
    if variant == "fail_check_first":
        core = _rv_msg(loc, "response_verbalizer.prediction_failed.core_fail_check_first", bucket=bucket, hint=hint)
    else:
        core = _rv_msg(loc, "response_verbalizer.prediction_failed.core_default", bucket=bucket, hint=hint)
    if not na:
        return core.strip()
    b = core.rstrip()
    if not b.endswith(ZH_SENTENCE_TERMINATORS):
        b = f"{b}{ZH_FULLWIDTH_PERIOD}"
    return f"{b}{_rv_msg(loc, 'response_verbalizer.prediction_failed.next_step_with_na', na=na)}"


def _localized_prediction_label(label: Any, loc: str) -> str:
    raw = str(label if label is not None else "").strip()
    if not raw:
        return "—"
    if loc != "en" or not _contains_han(raw):
        return raw
    mapping = PREDICTED_LABEL_ZH_TO_EN
    return mapping.get(raw, "non-English class label")


def verbalize_prediction_result(
    payload: ResponsePayload,
    req: Optional[ChatTurnRequest] = None,
) -> str:
    """
    prediction_result: deterministic localized copy from structured facts only.

    English/default deliberately ignores legacy Chinese headline, summary_points, next_action, and
    warnings so stale payload copy cannot leak into English UI or LLM-polish fallback paths.
    """
    loc = _chat_output_locale(req)
    facts = dict(payload.facts or {})
    label = _localized_prediction_label(facts.get("predicted_label"), loc)
    prob = _fmt_probability_pct(facts.get("predicted_probability")) or "—"
    status = str(facts.get("prediction_status") or "completed").strip() or "completed"
    has_shap = bool(facts.get("has_shap_explanation"))
    task_name = str(facts.get("task_name") or "").strip()
    model_name = str(facts.get("model_name") or "").strip()

    if loc == "en":
        lines: List[str] = [_rv_msg(loc, "response_verbalizer.prediction_result.headline")]
        details: List[str] = []
        if task_name and not _contains_han(task_name):
            details.append(f"task: {task_name}")
        if model_name and not _contains_han(model_name):
            details.append(f"model: {model_name}")
        if details:
            lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.context", details="; ".join(details)))
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.line_status", status=status))
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.line_label", label=label))
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.line_prob", prob=prob))
        if has_shap:
            lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_yes_a"))
            lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_yes_b"))
        else:
            lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_no_a"))
            lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_no_b"))
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.clinical_boundary"))
        return "\n".join(lines).strip()

    lines = [_rv_msg(loc, "response_verbalizer.prediction_result.headline")]
    if task_name or model_name:
        parts: List[str] = []
        if task_name:
            parts.append(_rv_msg(loc, "response_verbalizer.prediction_result.task_line", name=task_name))
        if model_name:
            parts.append(_rv_msg(loc, "response_verbalizer.prediction_result.model_line", name=model_name))
        lines.append(ZH_FULLWIDTH_SEMICOLON.join(parts) + ZH_FULLWIDTH_PERIOD)
    lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.line_status", status=status))
    lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.line_label", label=label))
    lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.line_prob", prob=prob))
    if has_shap:
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_yes_a"))
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_yes_b"))
    else:
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_no_a"))
        lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.explain_shap_no_b"))
    lines.append(_rv_msg(loc, "response_verbalizer.prediction_result.clinical_boundary"))
    return "\n".join(lines).strip()

def verbalize_batch_prediction_result(
    payload: ResponsePayload,
    req: Optional[ChatTurnRequest] = None,
) -> str:
    """
    batch_prediction_result: restate aggregate execution counts and download availability only; do not re-parse CSV or add evaluation semantics.
    """
    loc = "en" if req is None else _chat_output_locale(req)
    lines: List[str] = []
    raw_head = (payload.headline or "").strip()
    if loc == "en" and _contains_han(raw_head):
        head = _rv_msg("en", "response_verbalizer.batch_prediction.headline_default")
    else:
        head = raw_head or _rv_msg(loc, "response_verbalizer.batch_prediction.headline_default")
    lines.append(head)
    facts = payload.facts or {}
    tr = facts.get("total_records")
    sr = facts.get("successful_records")
    fr = facts.get("failed_records")
    lines.append(_rv_msg(loc, "response_verbalizer.batch_prediction.aggregate", tr=tr, sr=sr, fr=fr))
    if bool(facts.get("has_download_url")):
        ofn = str(facts.get("output_filename") or "").strip()
        if ofn:
            lines.append(_rv_msg(loc, "response_verbalizer.batch_prediction.download_with_suffix", ofn=ofn))
        else:
            lines.append(_rv_msg(loc, "response_verbalizer.batch_prediction.download_path_only"))
    else:
        lines.append(_rv_msg(loc, "response_verbalizer.batch_prediction.no_download_path"))
    for x in (payload.summary_points or [])[:10]:
        t = str(x).strip()
        if t:
            if loc != "en" or not _contains_han(t):
                lines.append(_rv_msg(loc, "response_verbalizer.batch_prediction.summary_point_line", t=t))
    if payload.next_action:
        na = payload.next_action.strip()
        if loc == "en" and _contains_han(na):
            na = _rv_msg("en", "response_verbalizer.batch_prediction.next_action_fallback")
        lines.append(_rv_msg(loc, "response_verbalizer.common.next_step", action=na))
    for s in payload.strict_lines or []:
        t = str(s).strip()
        if t:
            lines.append(t)
    for w in (payload.warnings or [])[:12]:
        t = str(w).strip()
        if t:
            if loc != "en" or not _contains_han(t):
                lines.append(t)
    out = "\n".join(lines).strip()
    return out or _rv_msg(loc, "response_verbalizer.batch_prediction.empty_fallback")


def verbalize_recommendation_result(
    payload: ResponsePayload,
    req: Optional[ChatTurnRequest] = None,
) -> str:
    """
    Deterministic user-facing summary from structured facts only.
    Preserves rank order and numeric values; does not emit internal constraints or raw JSON.
    """
    facts = dict(payload.facts or {})
    loc = _chat_output_locale(req)
    top1 = facts.get("recommended_top1_regimen")
    if not isinstance(top1, dict):
        top1 = {}
    top_name = _regimen_row_display_name(top1)
    rank_raw = top1.get("rank")
    try:
        rank1_i = int(rank_raw) if rank_raw is not None else 1
    except (TypeError, ValueError):
        rank1_i = 1

    rtp_s = _fmt_probability_pct(facts.get("recommended_top1_probability"))
    obs_s = _fmt_probability_pct(facts.get("observed_prediction_probability"))
    delta_pp = _fmt_delta_pp(facts.get("delta_probability_top1"))

    preview_raw = facts.get("top_candidates_preview")
    preview: List[Dict[str, Any]] = []
    if isinstance(preview_raw, list):
        for c in preview_raw:
            if isinstance(c, dict):
                preview.append(dict(c))
        preview.sort(key=lambda d: int(d.get("rank") or 999))

    lines: List[str] = []

    if loc == "en":
        lines.append(_rv_msg(loc, "response_verbalizer.recommendation.intro"))
        lines.append("")
        lines.append(_rv_msg(loc, "response_verbalizer.recommendation.section_top_regimen"))
        prob_tail = _rv_msg(loc, "response_verbalizer.recommendation.top_line_prob_suffix", rtp=rtp_s) if rtp_s else ""
        lines.append(f"{rank1_i}. {top_name}{prob_tail}")
        lines.append("")
        if obs_s:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.observed_prob", obs=obs_s))
        else:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.observed_prob_missing"))
        if rtp_s:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.top_prob_line", rtp=rtp_s))
        if delta_pp:
            sign, mag = delta_pp
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.delta_pp", sign=sign, mag=mag))
        lines.append("")
        others = [c for c in preview if int(c.get("rank") or 0) != rank1_i]
        if others:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.section_other_candidates"))
            for c in others[:12]:
                try:
                    ri = int(c.get("rank") or 0)
                except (TypeError, ValueError):
                    ri = 0
                nm = _regimen_row_display_name(c)
                ps = _fmt_probability_pct(c.get("predicted_probability"))
                if ps:
                    lines.append(
                        _rv_msg(
                            loc,
                            "response_verbalizer.recommendation.candidate_line_with_prob",
                            rank=ri,
                            name=nm,
                            prob=ps,
                        )
                    )
                else:
                    lines.append(_rv_msg(loc, "response_verbalizer.recommendation.candidate_line_no_prob", rank=ri, name=nm))
            lines.append("")
        lines.append(_rv_msg(loc, "response_verbalizer.recommendation.footer"))
    else:
        lines.append(_rv_msg(loc, "response_verbalizer.recommendation.intro"))
        lines.append("")
        lines.append(_rv_msg(loc, "response_verbalizer.recommendation.section_top_regimen"))
        prob_tail = _rv_msg(loc, "response_verbalizer.recommendation.top_line_prob_suffix", rtp=rtp_s) if rtp_s else ""
        lines.append(f"{rank1_i}. {top_name}{prob_tail}")
        lines.append("")
        if obs_s:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.observed_prob", obs=obs_s))
        else:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.observed_prob_missing"))
        if rtp_s:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.top_prob_line", rtp=rtp_s))
        if delta_pp:
            sign, mag = delta_pp
            sym = "+" if sign == "+" else "−"
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.delta_pp", sign=sym, mag=mag))
        lines.append("")
        others = [c for c in preview if int(c.get("rank") or 0) != rank1_i]
        if others:
            lines.append(_rv_msg(loc, "response_verbalizer.recommendation.section_other_candidates"))
            for c in others[:12]:
                try:
                    ri = int(c.get("rank") or 0)
                except (TypeError, ValueError):
                    ri = 0
                nm = _regimen_row_display_name(c)
                ps = _fmt_probability_pct(c.get("predicted_probability"))
                if ps:
                    lines.append(
                        _rv_msg(
                            loc,
                            "response_verbalizer.recommendation.candidate_line_with_prob",
                            rank=ri,
                            name=nm,
                            prob=ps,
                        )
                    )
                else:
                    lines.append(_rv_msg(loc, "response_verbalizer.recommendation.candidate_line_no_prob", rank=ri, name=nm))
            lines.append("")
        lines.append(_rv_msg(loc, "response_verbalizer.recommendation.footer"))

    if payload.next_action:
        lines.append("")
        lines.append(_rv_msg(loc, "response_verbalizer.common.next_step", action=payload.next_action.strip()))

    out = "\n".join(lines).strip()
    return out or _rv_msg(loc, "response_verbalizer.recommendation.empty_fallback")


def render_strict_template(payload: ResponsePayload, req: Optional[ChatTurnRequest] = None) -> str:
    """Deterministic template fallback: stable, readable, no LLM."""
    at = str(payload.answer_type or "").strip()
    if at == "training_draft_created":
        return verbalize_training_draft_created(payload, req)
    if at == "training_failed":
        return verbalize_training_failed(payload, req)
    if at == "prediction_failed":
        return verbalize_prediction_failed(payload, req)
    if at == "batch_prediction_result":
        return verbalize_batch_prediction_result(payload, req)
    if at == "prediction_result":
        return verbalize_prediction_result(payload, req)
    if at == "recommendation_result":
        return verbalize_recommendation_result(payload, req)
    loc = _chat_output_locale(req)
    lines: List[str] = []
    head = (payload.headline or "").strip() or str(payload.facts.get("semantic_summary") or "").strip()
    if head:
        lines.append(head)
    for x in payload.summary_points[:12]:
        t = str(x).strip()
        if t:
            lines.append(_rv_msg(loc, "response_verbalizer.strict_template.bullet", t=t))
    if payload.next_action:
        lines.append(_rv_msg(loc, "response_verbalizer.common.next_step", action=payload.next_action.strip()))
    for s in payload.strict_lines:
        t = str(s).strip()
        if t:
            lines.append(t)
    for w in payload.warnings[:8]:
        t = str(w).strip()
        if t:
            lines.append(t)
    out = "\n".join(lines).strip()
    if out:
        return out
    loc = _chat_output_locale(req)
    return _rv_msg(loc, "response_verbalizer.strict_template.empty_fallback")


def verbalize_response(
    payload: ResponsePayload,
    llm_provider: Any,
    *,
    req: ChatTurnRequest,
    trace_entries: Optional[MutableSequence[Dict[str, Any]]] = None,
) -> str:
    """
    strict_template: template-only path; llm_polish: attempt LLM polish, fall back to template on failure or empty output.
    ui_payload truth is unchanged by this function (callers must not write this output back into ui_payload).
    """
    entry: Dict[str, Any] = {
        "answer_type": payload.answer_type,
        "verbalization_mode": payload.verbalization_mode,
        "verbalized_by": "template",
        "response_payload_type": payload.answer_type,
        "verbalizer_fallback_used": False,
        "fallback_reason": None,
    }
    # recommendation_result / batch_prediction_result always use strict templates; never call polish LLM (defensive guard).
    at0 = str(payload.answer_type or "").strip()
    if at0 == "recommendation_result":
        entry["verbalized_by"] = "strict_template"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return verbalize_recommendation_result(payload, req)
    if at0 == "prediction_result":
        entry["verbalized_by"] = "strict_template"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return verbalize_prediction_result(payload, req)
    if at0 in ("batch_prediction_result", "training_failed", "prediction_failed"):
        entry["verbalized_by"] = "strict_template"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return render_strict_template(payload, req)
    if at0 == "training_completed":
        from backend.agent.narrative_polish import maybe_polish_training_completed_narrative

        return maybe_polish_training_completed_narrative(
            payload,
            req,
            llm_provider,
            trace_entries=trace_entries,
        )
    if payload.verbalization_mode != "llm_polish":
        entry["verbalized_by"] = "strict_template"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return render_strict_template(payload, req)

    messages = build_verbalizer_messages(payload, req)
    system_prompt = messages[0]["content"]
    user_only = [{"role": "user", "content": messages[1]["content"]}]
    try:
        text = llm_provider.chat(
            user_only,
            system_prompt=system_prompt,
            temperature=0.25,
            stream=False,
        )
        cleaned = _WS.sub(" ", str(text or "").strip())
        if not cleaned:
            entry["verbalizer_fallback_used"] = True
            entry["fallback_reason"] = "empty_llm_response"
            entry["verbalized_by"] = "strict_template_fallback"
            if trace_entries is not None:
                trace_entries.append(dict(entry))
            return render_strict_template(payload, req)
        entry["verbalized_by"] = "llm_polish"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return cleaned
    except LLMProviderError as exc:
        entry["verbalizer_fallback_used"] = True
        entry["fallback_reason"] = f"llm_error:{getattr(exc, 'error_code', 'LLM_PROVIDER_ERROR')}"
        entry["verbalized_by"] = "strict_template_fallback"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return render_strict_template(payload, req)
    except Exception as exc:
        entry["verbalizer_fallback_used"] = True
        entry["fallback_reason"] = f"exception:{type(exc).__name__}"
        entry["verbalized_by"] = "strict_template_fallback"
        if trace_entries is not None:
            trace_entries.append(dict(entry))
        return render_strict_template(payload, req)
