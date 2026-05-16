"""
Registry of read-only tools callable by the chat agent LLM planner (Stage 4B).

Only tools backed by backend.tools.read_only_tools.TOOL_HANDLERS are registered here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional

READONLY_TOOL_NAMES: FrozenSet[str] = frozenset(
    {
        "get_current_context",
        "list_tasks",
        "get_task_status",
        "get_latest_failure",
        "get_latest_training_summary",
        "get_latest_prediction_summary",
        "get_prediction_explanation_summary",
    }
)


@dataclass(frozen=True)
class ReadonlyToolRegistryEntry:
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    handler_name: str
    risk_level: str = "read_only"


_REGISTRY: Dict[str, ReadonlyToolRegistryEntry] = {
    "get_current_context": ReadonlyToolRegistryEntry(
        name="get_current_context",
        description=(
            "Return a privacy-safe summary of the current workbench context: page mode, "
            "selected dataset/model identifiers (not raw rows), chat LLM model id, and task counts by status."
        ),
        parameters_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler_name="get_current_context",
    ),
    "list_tasks": ReadonlyToolRegistryEntry(
        name="list_tasks",
        description=(
            "List recent tasks from the task repository with optional filters. "
            "Outputs only public task fields (no params, patient data, or artifacts)."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional filter: queued, running, completed, failed, canceled, waiting_user.",
                },
                "job_type": {
                    "type": "string",
                    "description": "Optional job_type filter (e.g. train_model, predict_outcome).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (1-200, default 50).",
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "additionalProperties": False,
        },
        handler_name="list_tasks",
    ),
    "get_task_status": ReadonlyToolRegistryEntry(
        name="get_task_status",
        description="Return public fields for a single task by job_id (e.g. job_0123456789).",
        parameters_schema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Task id starting with job_.",
                },
            },
            "required": ["job_id"],
            "additionalProperties": False,
        },
        handler_name="get_task_status",
    ),
    "get_latest_failure": ReadonlyToolRegistryEntry(
        name="get_latest_failure",
        description="Return the most recent failed task as a public-view summary (no stack traces from raw params).",
        parameters_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler_name="get_latest_failure",
    ),
    "get_latest_training_summary": ReadonlyToolRegistryEntry(
        name="get_latest_training_summary",
        description=(
            "Summarize the latest training job relevant for the workbench: status, headline metrics evidence flags, "
            "and registration hints. Does not expose feature lists or candidate pool columns."
        ),
        parameters_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler_name="get_latest_training_summary",
    ),
    "get_latest_prediction_summary": ReadonlyToolRegistryEntry(
        name="get_latest_prediction_summary",
        description=(
            "Privacy-filtered summary of the latest prediction (single or batch): labels, probabilities or row counts, "
            "and high-level text. No per-patient feature tables."
        ),
        parameters_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler_name="get_latest_prediction_summary",
    ),
    "get_prediction_explanation_summary": ReadonlyToolRegistryEntry(
        name="get_prediction_explanation_summary",
        description=(
            "High-level explanation summary for the latest prediction when available (e.g. driver features at aggregate level). "
            "Batch predictions may report explanation unavailable."
        ),
        parameters_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler_name="get_prediction_explanation_summary",
    ),
}


def get_public_tool_specs() -> List[Dict[str, Any]]:
    """Specs safe to embed in an LLM system prompt (names, descriptions, parameter JSON schemas)."""
    out: List[Dict[str, Any]] = []
    for name in sorted(READONLY_TOOL_NAMES):
        e = _REGISTRY[name]
        out.append(
            {
                "name": e.name,
                "description": e.description,
                "parameters": e.parameters_schema,
                "risk_level": e.risk_level,
            }
        )
    return out


def get_registered_tool(name: str) -> Optional[ReadonlyToolRegistryEntry]:
    key = str(name or "").strip()
    return _REGISTRY.get(key)


def is_registered_readonly_tool(name: str) -> bool:
    return str(name or "").strip() in READONLY_TOOL_NAMES
