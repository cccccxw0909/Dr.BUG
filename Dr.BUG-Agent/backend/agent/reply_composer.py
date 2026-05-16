"""Use the LLM for final natural-language phrasing; fall back to deterministic copy on failure."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, MutableSequence, Optional, Set

from backend.agent.chat_output_locale import is_english_output_locale, normalize_chat_output_locale
from backend.agent.i18n import chat_msg
from backend.agent.prompts.agent_instruction import (
    INTERNAL_RULE_LAYER_HEADER,
    build_orchestrator_runtime_agent_instruction,
)
from backend.agent.reply_semantics import AgentSemanticPayload, VerbatimPolicy
from backend.llm.base import LLMProviderError
from backend.schemas.agent import ChatTurnRequest

# Patient-level or large parameter fields must not enter finalization prompts.
_FINALIZATION_DROP_KEYS: Set[str] = {
    "patient_features",
    "params",
    "row_samples",
    "raw_values",
    "feature_values_used",
    "input_summary",
    "candidate_pool_columns",
    "med_cols",
    "recommended_features",
    "suggested_final_features",
    "final_features",
    "selected_features",
    "artifacts",
    "programmer_model",
    "notes",
    "history",
    "raw",
    "rows",
    "table",
    "csv",
    "upload",
}


REPLY_FINALIZATION_SYSTEM_ZH = (
    "You are a clinical-workbench assistant. Your only role here is to polish an explanation of the current situation. "
    "What the system can or cannot do, and whether a task has actually executed, has already been determined by backend rules. "
    "Do not make decisions for the user or suggest bypassing confirmation. "
    "Use only the user message and the facts in the situation summary below; do not invent task results, execution states, job ids, metrics, or capabilities. "
    "If the situation says the action is still a draft, pending confirmation, or not yet executed, clearly state that the high-risk operation has not really started. "
    "Answer the most relevant point first in one or two sentences, then add brief context if needed. "
    "Do not output JSON, internal field names, or table-like row data. Do not fabricate patient-level values. "
    "For training or model-evaluation metrics, be cautious and layered; do not treat a single scalar as sufficient cause. "
    "Unless the situation summary provides explicit support, avoid strong conclusions such as systemic error, far worse than random guessing, or absolutely unusable for decision support. "
    "Reply in professional Simplified Chinese."
)

REPLY_FINALIZATION_SYSTEM_EN = (
    "You are a clinical-workbench assistant. Your only role here is to polish an explanation of the current situation. "
    "What the system can or cannot do, and whether a task has actually executed, has already been determined by backend rules. "
    "Do not make decisions for the user or suggest bypassing confirmation. "
    "Use only the user message and the facts in the situation summary below; do not invent task results, execution states, job ids, metrics, or capabilities. "
    "If the situation says the action is still a draft, pending confirmation, or not yet executed, clearly state that the high-risk operation has not really started. "
    "Answer the most relevant point first in one or two sentences, then add brief context if needed. "
    "Do not output JSON, internal field names, or table-like row data. Do not fabricate patient-level values. "
    "For training or model-evaluation metrics, be cautious and layered; do not treat a single scalar as sufficient cause. "
    "Unless the situation summary provides explicit support, avoid strong conclusions such as systemic error, far worse than random guessing, or absolutely unusable for decision support. "
    "Reply in professional English."
)

# Backward-compatible name for tests/imports; runtime selection is locale-aware.
REPLY_FINALIZATION_SYSTEM = REPLY_FINALIZATION_SYSTEM_EN


def _chat_context_brief(ctx: Optional[Dict[str, Any]], locale: Optional[str] = None) -> str:
    if not ctx:
        return "No page summary."
    mode = str(ctx.get("mode") or "").strip() or "unknown"
    dataset = str(ctx.get("dataset") or "").strip() or "none"
    model = str(ctx.get("model") or "").strip() or "none"
    return f"Page summary (not patient data): mode={mode}; dataset summary={dataset}; current model summary={model}"


def sanitize_value_for_finalization(obj: Any, depth: int = 0) -> Any:
    if depth > 10:
        return None
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        if len(obj) > 4000:
            return obj[:3999] + "…"
        return obj
    if isinstance(obj, list):
        return [sanitize_value_for_finalization(x, depth + 1) for x in obj[:80]]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= 64:
                break
            key = str(k)
            lk = key.lower()
            if key in _FINALIZATION_DROP_KEYS or lk in {x.lower() for x in _FINALIZATION_DROP_KEYS}:
                continue
            if lk.endswith("_table") or "patient" in lk and "id" in lk:
                continue
            out[key] = sanitize_value_for_finalization(v, depth + 1)
        return out
    return None


def sanitize_tool_bundles_for_finalization(bundles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for b in bundles:
        if not isinstance(b, dict):
            continue
        slim: Dict[str, Any] = {"ok": b.get("ok"), "tool": b.get("tool"), "error": b.get("error")}
        if b.get("ok") is True and "result" in b:
            slim["result"] = sanitize_value_for_finalization(b.get("result"))
        out.append(slim)
    return out


def _bullet_block(title: str, lines: List[str]) -> str:
    if not lines:
        return ""
    body = "\n".join(f"- {x}" for x in lines if str(x).strip())
    return f"{title}\n{body}" if body else ""


def _policy_instruction_block(policy: VerbatimPolicy, mode: str, locale: Optional[str] = None) -> str:
    if policy == "forbidden":
        extra = (
            "[Style] Answer the user's main concern first in one sentence, then briefly explain what it means and transition naturally to the next step. "
            "Do not enumerate every point or write JSON-like bullets."
        )
        if mode == "draft_created":
            extra += " State clearly that the interface has prepared a draft but nothing has executed yet; identify what the user should confirm or complete in the card."
        if mode == "terminal_result":
            extra += " For training-result interpretation, remain cautious and avoid strong causal or clinical judgments unless facts support them."
        if mode == "workflow_guidance":
            extra += " This is workflow navigation: summarize the situation, then highlight the preferred next step and why."
        body = extra
    elif policy == "allowed":
        base = (
            "[Style] Use the key points and structured facts first; if a rule-layer draft is present, use it only to check boundaries. "
            "Do not rewrite it sentence-by-sentence into a long template."
        )
        if mode == "terminal_result":
            base += " For completed training metrics, use cautious layered wording and avoid prohibited strong conclusions."
        body = base
    else:
        body = "[Style] Preserve the rule-layer factual reply accurately; you may make it more natural but must not add or contradict facts."
    if not is_english_output_locale(locale):
        body += "\n\n(Output language: professional Simplified Chinese.)"
    return body


def build_finalization_user_content(req: ChatTurnRequest, payload: AgentSemanticPayload) -> tuple[str, bool]:
    """Return (user_content, used_verbatim_in_prompt).

    forbidden: never place verbatim text in the prompt, even if present.
    """
    pol: VerbatimPolicy = payload.verbatim_policy
    locale = payload.locale or normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    ctx_line = _chat_context_brief(req.chat_context, locale)
    verbatim = (payload.verbatim_reply_to_paraphrase or "").strip()
    used_verbatim = False
    parts: List[str] = [
        f"User message: {req.message.strip()}",
        ctx_line,
        "",
        f"[Verbatim policy] {pol} (required=stay close to rule facts; allowed=facts first, draft secondary; forbidden=use only key points and structured facts)",
        _policy_instruction_block(pol, payload.mode, locale),
        "",
        "[Situation — explain only from these facts; do not extrapolate]",
        f"Summary: {payload.summary}",
        _bullet_block("Key points", payload.key_points),
        _bullet_block("Additional observations", payload.observations),
        _bullet_block("User-available next steps", payload.allowed_next_steps),
        _bullet_block("Actions that must not be implied as already done", payload.blocked_actions),
        _bullet_block("Safety and process notes", payload.safety_notes),
    ]
    if payload.pending_action_preview:
        parts.append(f"Pending confirmation card note: {payload.pending_action_preview}")
    if payload.missing_fields:
        parts.append("Missing fields (names only): " + ", ".join(payload.missing_fields))
    if pol in ("required", "allowed") and verbatim:
        parts.append("")
        parts.append(
            "[Rule-layer factual reply — make it natural without adding or contradicting facts]"
            if pol == "required"
            else "[Rule-layer factual draft (secondary reference; yield to key points and structured facts)]"
        )
        parts.append(verbatim)
        used_verbatim = True
    if payload.tool_fact_bundles:
        slim = sanitize_tool_bundles_for_finalization(payload.tool_fact_bundles)
        raw = json.dumps(slim, ensure_ascii=False)
        if len(raw) > 12000:
            raw = raw[:11999] + "…"
        parts.append("")
        parts.append("[Structured facts returned by read-only queries (sanitized, not raw patient tables)]")
        parts.append(raw)
    return "\n".join(p for p in parts if p is not None), used_verbatim


def _fallback_from_facts(payload: AgentSemanticPayload) -> str:
    chunks: List[str] = []
    if payload.summary:
        chunks.append(str(payload.summary).strip())
    for x in payload.key_points[:5]:
        if str(x).strip():
            chunks.append(str(x).strip())
    if payload.allowed_next_steps:
        chunks.append(str(payload.allowed_next_steps[0]).strip())
    return " ".join(chunks).strip()


def compose_agent_reply_fallback(payload: AgentSemanticPayload) -> str:
    """Return deterministic fallback text according to the verbatim policy, without calling an LLM."""
    pol: VerbatimPolicy = payload.verbatim_policy
    loc = payload.locale
    generic = chat_msg(loc, "reply_composer.fallback_generic")
    v = (payload.verbatim_reply_to_paraphrase or "").strip()
    facts = _fallback_from_facts(payload)

    if pol == "required" and v:
        return v
    if pol == "allowed":
        # missing_info: key points are reusable facts, so fallback prefers facts
        if payload.mode == "missing_info" and len(facts) >= 24:
            return facts
        # tool_result / terminal_result: verbatim often carries rule-locked terminal conclusion sentences;
        # test stubs and weak-network fallbacks must keep those sentences; do not replace with generic "writing guidance" bullets only.
        if v and payload.mode in ("tool_result", "terminal_result"):
            return v
        if len(facts) >= 24:
            return facts
        if v:
            return v
        return facts or generic
    # forbidden: status anchors live in summary; fallback returns only the main sentence to avoid noise.
    if pol == "forbidden" and payload.mode == "status":
        s = (payload.summary or "").strip()
        if s:
            return s
    if facts:
        return facts
    return generic


_WS = re.compile(r"\s+")


def _append_finalization_trace(
    sink: Optional[MutableSequence[Dict[str, Any]]],
    entry: Dict[str, Any],
) -> None:
    if sink is not None:
        sink.append(entry)


def compose_agent_reply_with_llm(
    req: ChatTurnRequest,
    payload: AgentSemanticPayload,
    provider: Any,
    trace_sink: Optional[MutableSequence[Dict[str, Any]]] = None,
) -> str:
    """
    Call the provider for final phrasing; any failure falls back to compose_agent_reply_fallback.
    trace_sink optionally receives lightweight metadata without patient details.
    """
    used_tools = bool(payload.tool_fact_bundles)
    user_content, used_verbatim = build_finalization_user_content(req, payload)
    entry: Dict[str, Any] = {
        "mode": payload.mode,
        "user_intent": (payload.user_intent or "")[:240],
        "verbatim_policy": payload.verbatim_policy,
        "used_verbatim_in_prompt": used_verbatim,
        "used_tool_fact_bundles": used_tools,
        "finalization_success": False,
        "fallback_used": False,
        "fallback_reason": None,
        "output_length": 0,
    }
    # Finalization LLM: append the internal rule layer to the locale-specific phrasing system prompt.
    locale = payload.locale or normalize_chat_output_locale(chat_context=req.chat_context, message=req.message)
    system_base = REPLY_FINALIZATION_SYSTEM_EN if is_english_output_locale(locale) else REPLY_FINALIZATION_SYSTEM_ZH
    finalization_system = f"{system_base}{INTERNAL_RULE_LAYER_HEADER}{build_orchestrator_runtime_agent_instruction()}"
    try:
        text = provider.chat(
            [{"role": "user", "content": user_content}],
            system_prompt=finalization_system,
            temperature=0.25,
            stream=False,
        )
        cleaned = _WS.sub(" ", str(text or "").strip())
        if not cleaned:
            entry["fallback_used"] = True
            entry["fallback_reason"] = "empty_llm_response"
            fb = compose_agent_reply_fallback(payload)
            entry["output_length"] = len(fb)
            entry["finalization_success"] = False
            _append_finalization_trace(trace_sink, dict(entry))
            return fb
        entry["finalization_success"] = True
        entry["output_length"] = len(cleaned)
        _append_finalization_trace(trace_sink, dict(entry))
        return cleaned
    except LLMProviderError as exc:
        entry["fallback_used"] = True
        entry["fallback_reason"] = f"llm_error:{getattr(exc, 'error_code', 'LLM_PROVIDER_ERROR')}"
        fb = compose_agent_reply_fallback(payload)
        entry["output_length"] = len(fb)
        _append_finalization_trace(trace_sink, dict(entry))
        return fb
    except Exception as exc:
        entry["fallback_used"] = True
        entry["fallback_reason"] = f"exception:{type(exc).__name__}"
        fb = compose_agent_reply_fallback(payload)
        entry["output_length"] = len(fb)
        _append_finalization_trace(trace_sink, dict(entry))
        return fb
