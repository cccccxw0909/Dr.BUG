"""
In-process MCP adapter: maps orchestrator dependencies to tool inputs so the orchestrator stays free of tool wiring.

If a real FastMCP transport is added later, prefer changing only this module and server registration, not the main route matrix.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.pending_scope import resolve_pending_scope_key
from backend.config import QWEN_MODEL
from backend.mcp.tools.context_tools import (
    build_current_context_snapshot_from_bundle,
    pending_action_zh_label,
    tasks_meta_from_repo,
)
from backend.mcp.tools.training_tools import build_latest_training_summary_mcp_result
from backend.schemas.agent import ChatTurnRequest


def _resolve_llm_chat_model(chat_context: Optional[Dict[str, Any]]) -> Optional[str]:
    c = dict(chat_context or {})
    for k in ("llm_chat_model", "chat_llm_model", "chat_model"):
        v = str(c.get(k) or "").strip()
        if v:
            return v
    return str(QWEN_MODEL or "").strip() or None


def get_current_context_via_mcp(
    req: ChatTurnRequest,
    *,
    task_repo: Any,
    pending_registry: Any,
) -> Dict[str, Any]:
    """
    In-process call: build bundle → same core as FastMCP tools (no network transport).
    """
    ctx = dict(req.chat_context or {})
    scope_key = resolve_pending_scope_key(req.user_id, req.session_id)
    pend = pending_registry.get_active_pending_for_scope(scope_key)
    pending_exists = pend is not None
    pending_type = str(pend.action_type) if pend is not None else None
    pending_label = pending_action_zh_label(str(pend.action_type)) if pend is not None else None

    bundle: Dict[str, Any] = {
        "chat_context": ctx,
        "tasks_meta": tasks_meta_from_repo(task_repo),
        "pending_exists": pending_exists,
        "pending_action_type": pending_type,
        "pending_label": pending_label,
        "llm_chat_model": _resolve_llm_chat_model(ctx),
    }
    return build_current_context_snapshot_from_bundle(bundle)


def get_latest_training_summary_via_mcp(
    req: ChatTurnRequest,
    *,
    task_repo: Any,
) -> Dict[str, Any]:
    """
    In-process: reuse training_factual_core + privacy projection; shares build_latest_training_summary_mcp_result with FastMCP server tools.
    """
    _ = req  # Reserved: may later bind focus training job from chat_context
    return build_latest_training_summary_mcp_result(task_repo)
