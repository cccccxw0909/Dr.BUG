"""
chat_context contract for workflow helpers: central key names and light accessors to avoid magic strings.

Notes:
- Historically `model` is the current workbench model; `selected_model` is also accepted as an alias.
- "Required" here means: for the most precise organizer/drift behavior the frontend should send these keys; missing keys degrade rather than error.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

# --- Key names (shared by organizer / fingerprint) ---
KEY_MODE = "mode"
KEY_MODEL = "model"
KEY_SELECTED_MODEL = "selected_model"
KEY_FOCUS_JOB_ID = "focus_job_id"
KEY_CURRENT_JOB_ID = "current_job_id"

KEY_WF_PREDICTION_KIND = "wf_prediction_kind"
KEY_WF_BATCH_STAGE = "wf_batch_stage"
KEY_WF_REC_SCHEMA_READY = "wf_rec_schema_ready"
KEY_WF_REC_FORM_READY = "wf_rec_form_ready"
KEY_WF_REC_ENABLED_REGIMEN_COUNT = "wf_rec_enabled_regimen_count"

# Optional enrichment
KEY_WF_REC_FOCUS_JOB_ID = "wf_rec_focus_job_id"
KEY_WF_REC_LAST_STATUS = "wf_rec_last_status"
KEY_WF_TRAINING_STAGE_HINT = "wf_training_stage_hint"
KEY_WF_PREDICTION_HAS_BOUND_RESULT = "wf_prediction_has_bound_result"
KEY_WF_REC_HAS_BOUND_PREDICTION = "wf_rec_has_bound_prediction"

# Focus job id resolution order (matches legacy focus_job_id_from_context)
FOCUS_JOB_ID_KEYS: Sequence[str] = (
    KEY_FOCUS_JOB_ID,
    KEY_CURRENT_JOB_ID,
    "active_job_id",
    "task_id",
    "selected_job_id",
)

# Organizer "please provide when possible" signal keys (gap reporting only; never blocks requests)
ORGANIZER_CORE_SIGNAL_KEYS: Tuple[str, ...] = (
    KEY_MODE,
    KEY_FOCUS_JOB_ID,
    KEY_MODEL,
    KEY_SELECTED_MODEL,
    KEY_WF_PREDICTION_KIND,
    KEY_WF_BATCH_STAGE,
    KEY_WF_REC_SCHEMA_READY,
    KEY_WF_REC_FORM_READY,
    KEY_WF_REC_ENABLED_REGIMEN_COUNT,
)

ORGANIZER_OPTIONAL_KEYS: Tuple[str, ...] = (
    KEY_WF_REC_FOCUS_JOB_ID,
    KEY_WF_REC_LAST_STATUS,
    KEY_WF_TRAINING_STAGE_HINT,
    KEY_WF_PREDICTION_HAS_BOUND_RESULT,
    KEY_WF_REC_HAS_BOUND_PREDICTION,
)


def get_workspace_model_id(chat_context: Optional[Dict[str, Any]]) -> str:
    ctx = chat_context or {}
    for k in (KEY_MODEL, KEY_SELECTED_MODEL, "model_id", "selectedModel"):
        v = str(ctx.get(k) or "").strip()
        if v:
            return v
    return ""


def get_focus_job_id(chat_context: Optional[Dict[str, Any]]) -> str:
    ctx = chat_context or {}
    for k in FOCUS_JOB_ID_KEYS:
        v = str(ctx.get(k) or "").strip()
        if v.startswith("job_"):
            return v
    return ""


def get_mode(chat_context: Optional[Dict[str, Any]]) -> str:
    return str((chat_context or {}).get(KEY_MODE) or "").strip()


def organizer_core_gaps(chat_context: Optional[Dict[str, Any]]) -> List[str]:
    """List core-signal keys that are missing or empty strings (diagnostics/degradation only; never raises)."""
    ctx = chat_context or {}
    gaps: List[str] = []
    if not get_mode(ctx):
        gaps.append(KEY_MODE)
    if not get_focus_job_id(ctx):
        gaps.append(KEY_FOCUS_JOB_ID)
    if not get_workspace_model_id(ctx):
        gaps.append(KEY_MODEL)
    if KEY_WF_PREDICTION_KIND not in ctx or not str(ctx.get(KEY_WF_PREDICTION_KIND) or "").strip():
        gaps.append(KEY_WF_PREDICTION_KIND)
    if KEY_WF_BATCH_STAGE not in ctx or not str(ctx.get(KEY_WF_BATCH_STAGE) or "").strip():
        gaps.append(KEY_WF_BATCH_STAGE)
    for k in (KEY_WF_REC_SCHEMA_READY, KEY_WF_REC_FORM_READY, KEY_WF_REC_ENABLED_REGIMEN_COUNT):
        if k not in ctx:
            gaps.append(k)
    return gaps
