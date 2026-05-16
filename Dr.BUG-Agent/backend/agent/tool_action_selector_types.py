# backend/agent/tool_action_selector_types.py
"""
Types for the tool/action route selector.

The selector only emits route + audit metadata; it does not run training/prediction/MCP.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Aligns with external ChatTurn routes, including pending_confirm for gating.
SelectorRoute = Literal[
    "welcome_policy",
    "pending_confirm",
    "mcp_context_query",
    "mcp_latest_training_summary",
    "workflow_guidance",
    "deterministic_action",
    "llm_chat",
    "fallback_template",
    "concise_status",
]

ActionDomain = Literal["training", "prediction", "recommendation"]


class SelectorInput(BaseModel):
    """Minimal context: must not depend on full chat history or patient-level tables."""

    message: str = ""
    is_new_session: bool = False
    has_active_pending_registry: bool = False
    #: Focus task status (e.g. waiting_user); None when no focus
    focus_task_status: Optional[str] = None
    #: Minimal progress hit precomputed by orchestrator via task_repo (booleans only; no task body)
    has_concise_progress_hit: bool = False


class SelectorDecision(BaseModel):
    route: SelectorRoute
    reason_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    #: Meaningful only when route == deterministic_action
    action_domain: Optional[ActionDomain] = None
    #: Matched rule chain for audit; first entry is the adopted rule
    reason_codes: List[str] = Field(default_factory=list)
    rule_scores: Dict[str, float] = Field(default_factory=dict)

    def trace_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "reason_code": self.reason_code,
            "confidence": self.confidence,
            "action_domain": self.action_domain,
            "reason_codes": list(self.reason_codes),
            "rule_scores": dict(self.rule_scores),
        }
