# backend/agent/tool_action_selector.py
"""
Minimal rule-based tool/action router.

Selects routes only; does not execute MCP, pending cards, or final LLM replies.
Rules are independent hit functions + fixed-priority aggregation to avoid a giant orchestrator if-else.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from backend.agent.context_query_detector import is_narrow_mcp_context_query
from backend.agent.intent_parser import parse_intent
from backend.agent.latest_training_query_detector import is_narrow_mcp_latest_training_summary_query
from backend.agent.tool_action_selector_types import ActionDomain, SelectorDecision, SelectorInput, SelectorRoute
from backend.agent.welcome_policy import WelcomeContext, should_handle_as_welcome
from backend.agent.workflow_rules import wants_workflow_guidance_intent
from backend.agent.i18n.lexicons.zh_tool_action_selector import (
    ZH_CURRENT_FLOW,
    ZH_FLOW_PROGRESS_A,
    ZH_FLOW_PROGRESS_B,
    ZH_PENDING_CANCEL_PHRASES,
    ZH_PENDING_CONFIRM_PHRASES,
    ZH_PENDING_CONTINUE_PHRASES,
    ZH_STUCK_POINT,
    ZH_TRAINING_RECENCY_ANCHOR_RE,
    ZH_TRAINING_RESULT_QUALITY_RE,
    ZH_WORKFLOW_QUESTION_MARKERS,
)
@dataclass(frozen=True)
class _RuleHit:
    route: SelectorRoute
    reason_code: str
    confidence: float
    action_domain: Optional[ActionDomain] = None


def _norm_msg(message: str) -> str:
    return re.sub(r"\s+", "", (message or "").strip())


def _is_explicit_pending_dialog_control(message: str) -> bool:
    """Narrow confirm/continue/cancel phrases under a pending card or waiting_user latch."""
    s = _norm_msg(message)
    if not s or len(s) > 24:
        return False
    if s in ZH_PENDING_CONFIRM_PHRASES:
        return True
    if s in ZH_PENDING_CONTINUE_PHRASES:
        return True
    if s in ZH_PENDING_CANCEL_PHRASES:
        return True
    return False


def _has_training_recency_anchor(message: str) -> bool:
    """Explicit recency anchors like "latest/last time…": prefer MCP training summary bundle."""
    return bool(re.search(ZH_TRAINING_RECENCY_ANCHOR_RE, message or ""))


def _training_result_summary_phrase(message: str) -> bool:
    """Training result/effect phrasing without explicit time words still routes to MCP summary (distinct from generic tool_query)."""
    m = message or ""
    if re.search(ZH_TRAINING_RESULT_QUALITY_RE, m):
        return True
    return False


def _allow_mcp_latest_training_route(message: str) -> bool:
    return _has_training_recency_anchor(message) or _training_result_summary_phrase(message)


def _wants_workflow_guidance_selector(message: str) -> bool:
    if wants_workflow_guidance_intent(message):
        return True
    m = (message or "").strip()
    if not m or len(m) > 200:
        return False
    if ZH_STUCK_POINT in m:
        return True
    if ZH_CURRENT_FLOW in m or ZH_FLOW_PROGRESS_A in m or ZH_FLOW_PROGRESS_B in m:
        if any(k in m for k in ZH_WORKFLOW_QUESTION_MARKERS):
            return True
    return False


def _deterministic_domain_from_intent(message: str) -> Optional[Tuple[ActionDomain, str]]:
    intent = parse_intent(message or "")
    at = intent.get("action_type")
    if at in ("create_training_job", "draft_training_job"):
        return ("training", "deterministic_training_intent")
    if at in ("draft_single_prediction", "create_prediction_job", "prediction_entry"):
        return ("prediction", "deterministic_prediction_intent")
    if at == "create_recommendation_job":
        return ("recommendation", "deterministic_recommendation_intent")
    return None


def _rule_pending_confirm(inp: SelectorInput) -> Optional[_RuleHit]:
    st = (inp.focus_task_status or "").strip()
    waiting = st == "waiting_user"
    if not (inp.has_active_pending_registry or waiting):
        return None
    if not _is_explicit_pending_dialog_control(inp.message):
        return None
    return _RuleHit("pending_confirm", "pending_confirm_waiting_user_or_registry", 0.92)


def _rule_mcp_latest_training(inp: SelectorInput) -> Optional[_RuleHit]:
    m = inp.message or ""
    if not is_narrow_mcp_latest_training_summary_query(m):
        return None
    if not _allow_mcp_latest_training_route(m):
        return None
    return _RuleHit("mcp_latest_training_summary", "narrow_mcp_latest_training_summary_query", 0.9)


def _rule_mcp_context(inp: SelectorInput) -> Optional[_RuleHit]:
    if is_narrow_mcp_context_query(inp.message):
        return _RuleHit("mcp_context_query", "narrow_mcp_context_query", 0.9)
    return None


def _rule_workflow(inp: SelectorInput) -> Optional[_RuleHit]:
    if _wants_workflow_guidance_selector(inp.message or ""):
        return _RuleHit("workflow_guidance", "workflow_guidance_intent", 0.85)
    return None


def _rule_concise(inp: SelectorInput) -> Optional[_RuleHit]:
    if not inp.has_concise_progress_hit:
        return None
    if _wants_workflow_guidance_selector(inp.message or ""):
        return None
    m = inp.message or ""
    if is_narrow_mcp_latest_training_summary_query(m) and _allow_mcp_latest_training_route(m):
        return None
    if is_narrow_mcp_context_query(m):
        return None
    return _RuleHit("concise_status", "concise_progress_hit_resolved", 0.88)


def _rule_deterministic(inp: SelectorInput) -> Optional[_RuleHit]:
    dom = _deterministic_domain_from_intent(inp.message or "")
    if not dom:
        return None
    domain, code = dom
    return _RuleHit("deterministic_action", code, 0.82, action_domain=domain)


def _rule_welcome(inp: SelectorInput, welcome_ctx: WelcomeContext) -> Optional[_RuleHit]:
    if _deterministic_domain_from_intent(inp.message or "") is not None:
        return None
    if is_narrow_mcp_context_query(inp.message) or is_narrow_mcp_latest_training_summary_query(inp.message):
        return None
    if _wants_workflow_guidance_selector(inp.message or ""):
        return None
    if not should_handle_as_welcome(welcome_ctx, inp.message):
        return None
    return _RuleHit("welcome_policy", "welcome_policy_first_turn_or_greeting", 0.8)


def _rule_fallback(inp: SelectorInput) -> Optional[_RuleHit]:
    if not (inp.message or "").strip():
        return _RuleHit("fallback_template", "empty_message_fallback", 0.99)
    return None


# Note: concise must precede mcp_latest_training_summary so training-completion questions
# are not captured by the narrow training-summary regex.
_PRIORITY_RULES: List[Callable[[SelectorInput, WelcomeContext], Optional[_RuleHit]]] = [
    lambda inp, _ctx: _rule_pending_confirm(inp),
    lambda inp, _ctx: _rule_concise(inp),
    lambda inp, _ctx: _rule_mcp_latest_training(inp),
    lambda inp, _ctx: _rule_mcp_context(inp),
    lambda inp, _ctx: _rule_workflow(inp),
    lambda inp, _ctx: _rule_deterministic(inp),
    lambda inp, ctx: _rule_welcome(inp, ctx),
    lambda inp, _ctx: _rule_fallback(inp),
]


def select_tool_or_action(
    inp: SelectorInput,
    *,
    welcome_context: WelcomeContext,
) -> SelectorDecision:
    scores: dict[str, float] = {}
    chain: List[str] = []
    for i, rule_fn in enumerate(_PRIORITY_RULES):
        hit = rule_fn(inp, welcome_context)
        key = f"rule_{i}"
        if hit:
            scores[key] = hit.confidence
            chain.append(f"{key}:{hit.reason_code}")
            return SelectorDecision(
                route=hit.route,
                reason_code=hit.reason_code,
                confidence=hit.confidence,
                action_domain=hit.action_domain,
                reason_codes=[chain[-1]],
                rule_scores=scores,
            )
    scores["default"] = 0.55
    return SelectorDecision(
        route="llm_chat",
        reason_code="default_llm_chat",
        confidence=0.55,
        action_domain=None,
        reason_codes=["default:llm_chat"],
        rule_scores=scores,
    )
