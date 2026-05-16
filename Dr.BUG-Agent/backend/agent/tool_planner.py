"""
LLM-assisted planning for read-only workbench tools (Stage 4B).

On any parse/validation failure, returns None so orchestrator can fall back to plan_readonly_tools.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.agent.tool_registry import get_public_tool_specs, get_registered_tool, is_registered_readonly_tool
from backend.llm.base import LLMProviderError
from backend.llm.qwen_provider import QwenProvider
from backend.schemas.agent import ChatTurnRequest

_MAX_TOOL_CALLS = 5
_MAX_USER_MESSAGE_CHARS = 4000
_JOB_ID_RE = re.compile(r"^job_[0-9a-f]{10}$", re.IGNORECASE)

_ALLOWED_TASK_STATUSES = frozenset(
    {"queued", "running", "completed", "failed", "canceled", "waiting_user", "pending"}
)

_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "create_training_job",
        "draft_training_job",
        "create_prediction_job",
        "draft_single_prediction",
        "create_recommendation_job",
        "create_report_job",
        "get_job_detail",
        "cancel_job",
        "list_datasets",
        "get_dataset_detail",
        "list_models",
    }
)


def _extract_json_object(text: str) -> Optional[Any]:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _coerce_int(v: Any, default: int, *, min_v: int, max_v: int) -> int:
    try:
        i = int(v)
    except (TypeError, ValueError):
        i = default
    return max(min_v, min(max_v, i))


def _normalize_tool_arguments(name: str, arguments: Any) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Validate and normalize arguments for a registered read-only tool.
    Returns (error_code, args) where error_code is set on failure.
    """
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return ("invalid_arguments_type", {})

    entry = get_registered_tool(name)
    if entry is None:
        return ("unknown_tool", {})

    if name == "get_current_context":
        if arguments:
            return ("unexpected_arguments", {})
        return (None, {})

    if name == "get_latest_failure":
        if arguments:
            return ("unexpected_arguments", {})
        return (None, {})

    if name == "get_latest_training_summary":
        if arguments:
            return ("unexpected_arguments", {})
        return (None, {})

    if name == "get_latest_prediction_summary":
        if arguments:
            return ("unexpected_arguments", {})
        return (None, {})

    if name == "get_prediction_explanation_summary":
        if arguments:
            return ("unexpected_arguments", {})
        return (None, {})

    if name == "get_task_status":
        job_id = str(arguments.get("job_id") or "").strip()
        if not job_id or not _JOB_ID_RE.match(job_id):
            return ("invalid_job_id", {})
        extra = set(arguments.keys()) - {"job_id"}
        if extra:
            return ("unexpected_argument_keys", {})
        return (None, {"job_id": job_id})

    if name == "list_tasks":
        allowed_keys = {"status", "job_type", "limit"}
        extra = set(arguments.keys()) - allowed_keys
        if extra:
            return ("unexpected_argument_keys", {})
        out: Dict[str, Any] = {}
        if "status" in arguments and arguments["status"] is not None:
            st = str(arguments["status"]).strip()
            if st and st not in _ALLOWED_TASK_STATUSES:
                return ("invalid_status_filter", {})
            if st:
                out["status"] = st
        if "job_type" in arguments and arguments["job_type"] is not None:
            jt = str(arguments["job_type"]).strip()
            if jt:
                if len(jt) > 64 or not re.match(r"^[a-zA-Z0-9_]+$", jt):
                    return ("invalid_job_type", {})
                out["job_type"] = jt
        if "limit" in arguments and arguments["limit"] is not None:
            out["limit"] = _coerce_int(arguments["limit"], 50, min_v=1, max_v=200)
        elif "limit" not in out:
            out["limit"] = 50
        return (None, out)

    return ("unhandled_tool", {})


def _validate_planned_calls(
    tool_calls: Any,
) -> Tuple[Optional[str], List[Tuple[str, Dict[str, Any]]]]:
    if tool_calls is None:
        return ("missing_tool_calls", [])
    if not isinstance(tool_calls, list):
        return ("tool_calls_not_list", [])
    if len(tool_calls) > _MAX_TOOL_CALLS:
        return ("too_many_tool_calls", [])

    planned: List[Tuple[str, Dict[str, Any]]] = []
    for i, call in enumerate(tool_calls):
        if not isinstance(call, dict):
            return ("call_not_object", [])
        name = str(call.get("name") or "").strip()
        if not name:
            return ("missing_tool_name", [])
        if name in _FORBIDDEN_TOOL_NAMES:
            return ("forbidden_tool_name", [])
        if not is_registered_readonly_tool(name):
            return ("unknown_tool_name", [])
        args = call.get("arguments")
        err, normalized = _normalize_tool_arguments(name, args)
        if err:
            return (f"{err}:{name}", [])
        planned.append((name, normalized))

    return (None, planned)


def _build_planner_system_prompt() -> str:
    specs = json.dumps(get_public_tool_specs(), ensure_ascii=False, indent=2)
    return (
        "You are a read-only tool router for a clinical AI workbench assistant.\n"
        "Your ONLY job is to output JSON describing which privacy-safe read-only tools to run.\n\n"
        "Output format — return ONLY this JSON object (no markdown fences, no commentary):\n"
        '{"tool_calls":[{"name":"<tool_name>","arguments":{}}]}\n\n'
        "Rules:\n"
        "- Use an empty tool_calls array if the user is not asking for workspace/task status, lists, failures, "
        "training summaries, prediction summaries, or prediction explanations.\n"
        "- You must ONLY use tool names from the allowed list below.\n"
        "- You must NEVER output: create_training_job, draft_training_job, create_prediction_job, "
        "draft_single_prediction, create_recommendation_job, create_report_job, get_job_detail, cancel_job, "
        "list_datasets, get_dataset_detail, list_models, or any tool name not in the allowed list.\n"
        "- For get_task_status, arguments.job_id is required and must look like job_ followed by 10 hex chars.\n"
        "- For list_tasks, optional filters: status (queued|running|completed|failed|canceled|waiting_user|pending), "
        "job_type (alphanumeric/underscore, max 64 chars), limit (1-200).\n"
        "- For tools with empty parameter objects, use {}.\n\n"
        "Allowed tools (JSON):\n"
        f"{specs}\n"
    )


def plan_readonly_tools_with_llm(
    req: ChatTurnRequest,
    llm_provider: QwenProvider,
    route_trace: Dict[str, Any],
) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
    """
    Ask the LLM for a strict JSON plan of read-only tool calls.

    Returns a non-empty list of (name, args) on success, or None to signal fallback to rule-based plan_readonly_tools.
    """
    msg = str(req.message or "").strip()
    if not msg:
        route_trace["readonly_llm_planner"] = {"used": False, "reason": "empty_message"}
        return None
    if len(msg) > _MAX_USER_MESSAGE_CHARS:
        route_trace["readonly_llm_planner"] = {"used": False, "reason": "message_too_long"}
        return None

    system_prompt = _build_planner_system_prompt()
    try:
        raw = llm_provider.chat(
            messages=[{"role": "user", "content": msg}],
            system_prompt=system_prompt,
            temperature=0.1,
            stream=False,
        )
    except LLMProviderError as exc:
        route_trace["readonly_llm_planner"] = {
            "used": False,
            "reason": "llm_provider_error",
            "error_code": getattr(exc, "error_code", None),
        }
        return None

    parsed = _extract_json_object(raw)
    if parsed is None or not isinstance(parsed, dict):
        route_trace["readonly_llm_planner"] = {
            "used": False,
            "reason": "json_parse_failed",
            "raw_preview": (raw or "")[:240],
        }
        return None

    err, planned = _validate_planned_calls(parsed.get("tool_calls"))
    if err:
        route_trace["readonly_llm_planner"] = {
            "used": False,
            "reason": "validation_failed",
            "detail": err,
            "raw_preview": (raw or "")[:240],
        }
        return None

    if not planned:
        route_trace["readonly_llm_planner"] = {"used": False, "reason": "empty_tool_calls"}
        return None

    route_trace["readonly_llm_planner"] = {"used": True, "tools": [p[0] for p in planned]}
    return planned
