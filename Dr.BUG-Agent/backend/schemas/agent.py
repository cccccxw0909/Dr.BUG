from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


ActionType = Literal[
    "create_training_job",
    "draft_training_job",
    "create_prediction_job",
    "draft_single_prediction",
    "prediction_entry",
    "create_recommendation_job",
    "create_report_job",
]


class PendingAction(BaseModel):
    pending_action_id: str
    action_type: ActionType
    risk_level: Literal["high"] = "high"
    payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: str
    created_at: str
    status: Literal["pending", "confirmed", "expired", "canceled", "superseded"] = "pending"
    superseded_by: Optional[str] = None
    executed_job_id: Optional[str] = None
    #: Isolation bucket: supersede only within the same scope_key; legacy data defaults to legacy:global
    scope_key: str = Field(default="legacy:global")


class ChatTurnRequest(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"
    #: Session isolation for anonymous/weak auth (prefer user_id when both exist)
    session_id: Optional[str] = None
    #: Optional: last training card saved completed_params for "continue training" merges with short messages
    client_completed_params: Optional[Dict[str, Any]] = None
    #: Lightweight chat context summary (e.g. page mode / current dataset / current model)
    chat_context: Optional[Dict[str, Any]] = None


class ChatTurnData(BaseModel):
    assistant_message: str
    route: Literal[
        "llm_chat",
        "deterministic_action",
        "tool_query",
        "concise_status",
        "fallback_template",
        "prediction_entry",
        "workflow_guidance",
        "welcome_policy",
        "mcp_context_query",
        "mcp_latest_training_summary",
        "pending_confirm",
    ] = "fallback_template"
    recognized_action: Optional[ActionType] = None
    completed_params: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    can_confirm: bool = False
    pending_confirmation: Optional[PendingAction] = None
    #: Read-only tools invoked this turn (audit/debug; excludes raw task params; hidden from UI by default)
    tool_names: list[str] = Field(default_factory=list)
    #: User-readable labels for what was queried (excludes internal tool names)
    readonly_query_labels: list[str] = Field(default_factory=list)
    #: Route decision debug trace (first round may use constrained LLM augmentation)
    route_decision_trace: Dict[str, Any] = Field(default_factory=dict)


class ActionConfirmRequest(BaseModel):
    pending_action_id: str
    confirmed: bool = True
    #: Merge with pending.payload before validation (Phase 1: preserves frontend draft edits).
    completed_params: Optional[Dict[str, Any]] = None
    #: Optional UI locale selected by the app (for example, en-US or zh-CN); omitted values default to English user-facing copy.
    locale: Optional[str] = None


class ActionConfirmData(BaseModel):
    assistant_message: str
    job_id: Optional[str] = None
    task: Optional[Dict[str, Any]] = None

