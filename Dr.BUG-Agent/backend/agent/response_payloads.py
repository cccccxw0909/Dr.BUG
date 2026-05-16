"""
Structured reply payload: after deterministic core fixes facts/bounds, project into this shape for the verbalizer to phrase only.

- The selector picks the chain; deterministic core (MCP / workflow / prediction read-only facts) owns truth/state.
- This module + verbalizer handle wording only; must not rewrite route/metrics/ranking/pending truth.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from backend.agent.chat_output_locale import is_english_output_locale
from backend.agent.i18n import chat_msg
from backend.agent.i18n.lexicons.zh_agent_response import PARSED_VALID_INFO_SUMMARY_PREFIX_ZH
from backend.agent.i18n.lexicons.zh_typography import ZH_FULLWIDTH_COLON
from backend.agent.reply_semantics import AgentSemanticPayload
from backend.agent.result_presentation import (
    build_task_backed_prediction_failure_facts,
    build_task_backed_training_failure_facts,
    infer_predict_is_batch,
    resolve_latest_prediction_readonly_reply_mode,
)
from backend.prediction.prediction_factual_core import build_prediction_factual_bundle_from_task
from backend.schemas.task import JobType
from backend.tools.read_only_privacy import ReadonlyTruncateTracker
from backend.training.training_factual_core import build_training_factual_bundle

# answer_types that enable llm_polish by default (stable baseline)
DEFAULT_LLM_POLISH_ANSWER_TYPES: FrozenSet[str] = frozenset(
    {
        "latest_training_summary",
        "context_summary",
        "workflow_guidance",
    }
)

# Reserved extension names (documented / product alignment; off unless env explicitly enables)
_RESERVED_LLM_POLISH_EXTENSIONS: FrozenSet[str] = frozenset(
    {
        "prediction_result",
        "training_completed",
        # recommendation_result: fixed strict_template this release; do not enable polish via EXTRA.
    }
)

# Back-compat alias: legacy code may still reference the default-only set
LLM_POLISH_ANSWER_TYPES = DEFAULT_LLM_POLISH_ANSWER_TYPES

# Comma-separated, e.g. prediction_result or prediction_result,training_completed
_LLM_POLISH_EXTRA_ENV = "CLINICAL_VERBALIZER_LLM_POLISH_EXTRA"


def effective_llm_polish_answer_types() -> FrozenSet[str]:
    """Default set plus env-var extensions (lightweight gray release; no standalone feature-flag framework)."""
    raw = (os.environ.get(_LLM_POLISH_EXTRA_ENV) or "").strip()
    if not raw:
        return DEFAULT_LLM_POLISH_ANSWER_TYPES
    extra: set[str] = set()
    for part in raw.split(","):
        p = part.strip()
        if p and p in _RESERVED_LLM_POLISH_EXTENSIONS:
            extra.add(p)
    return frozenset(set(DEFAULT_LLM_POLISH_ANSWER_TYPES) | extra)


def is_llm_polish_answer_type(answer_type: str, *, maybe_error_state: bool = False) -> bool:
    if maybe_error_state:
        return False
    return str(answer_type or "").strip() in effective_llm_polish_answer_types()


@dataclass
class ResponsePayload:
    """Minimal response phrasing-layer payload (not a business-capability layer)."""

    answer_type: str
    verbalization_mode: str  # "strict_template" | "llm_polish"
    facts: Dict[str, Any] = field(default_factory=dict)
    summary_points: List[str] = field(default_factory=list)
    headline: Optional[str] = None
    next_action: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    strict_lines: List[str] = field(default_factory=list)
    ui_payload: Dict[str, Any] = field(default_factory=dict)
    trace: Dict[str, Any] = field(default_factory=dict)


def build_response_payload_from_semantic(
    sem: AgentSemanticPayload,
    *,
    answer_type: str,
    final_route: str,
    ui_payload: Optional[Dict[str, Any]] = None,
    waiting_user_confirm_hint: bool = False,
) -> ResponsePayload:
    """
    Project an existing AgentSemanticPayload into ResponsePayload (does not mutate sem; no patient tables).
    """
    ui: Dict[str, Any] = dict(ui_payload or {})
    ui.setdefault("route", final_route)

    bundles = sem.tool_fact_bundles or []
    facts: Dict[str, Any] = {
        "semantic_summary": (sem.summary or "").strip(),
        "user_intent": (sem.user_intent or "").strip(),
        "semantic_mode": sem.mode,
        "tool_fact_bundles": list(bundles),
    }

    summary_points: List[str] = [str(x).strip() for x in sem.key_points if str(x).strip()]
    for x in sem.observations:
        t = str(x).strip()
        if t and t not in summary_points:
            summary_points.append(t)

    warnings = [str(x).strip() for x in sem.safety_notes if str(x).strip()]
    boundary = chat_msg(sem.locale, "payload.semantic.boundary")
    for x in sem.blocked_actions:
        t = str(x).strip()
        if t:
            warnings.append(f"{boundary}{t}")

    strict_lines: List[str] = []
    if sem.verbatim_policy == "required" and (sem.verbatim_reply_to_paraphrase or "").strip():
        strict_lines.append(str(sem.verbatim_reply_to_paraphrase).strip())
    if waiting_user_confirm_hint and (sem.pending_action_preview or "").strip():
        pending_prefix = chat_msg(sem.locale, "payload.semantic.pending_prefix")
        strict_lines.append(f"{pending_prefix}{str(sem.pending_action_preview).strip()}")

    next_action: Optional[str] = None
    if sem.allowed_next_steps:
        next_action = str(sem.allowed_next_steps[0]).strip() or None

    headline = (sem.summary or "").strip()[:200] or None

    mode: str = "llm_polish" if is_llm_polish_answer_type(answer_type) else "strict_template"

    trace = {
        "payload_source": "agent_semantic",
        "answer_type": answer_type,
        "verbalization_mode": mode,
        "final_route": final_route,
    }
    return ResponsePayload(
        answer_type=answer_type,
        verbalization_mode=mode,
        headline=headline,
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=warnings,
        strict_lines=strict_lines,
        ui_payload=ui,
        trace=trace,
    )


def _format_probability_zh(prob: Any) -> str:
    try:
        v = float(prob)
    except (TypeError, ValueError):
        return str(prob)
    if 0.0 <= v <= 1.0:
        pct = f"{v * 100:.1f}"
        return chat_msg("zh", "payload.probability_pct_numeric", pct=pct, num=v)
    return chat_msg("zh", "payload.probability_plain", num=v)


def _format_probability_en(prob: Any) -> str:
    try:
        v = float(prob)
    except (TypeError, ValueError):
        return str(prob)
    if 0.0 <= v <= 1.0:
        return f"{v * 100:.1f}% (numeric value {v:g})"
    return f"{v:g}"


def _english_payload_copy(locale: Optional[str]) -> bool:
    """True for English user-visible copy; omitted/empty locale follows the product default (English)."""
    return is_english_output_locale(locale)


def try_extract_single_prediction_readonly_success(
    planned: List[Tuple[str, Dict[str, Any]]],
    tool_results: List[Dict[str, Any]],
    task_repo: Any,
) -> Optional[Dict[str, Any]]:
    """
    Extract a completed single-sample prediction fact bundle from planned read-only tool results; else None.

    Deterministic prediction core already chose tools/projections; this helper does not read raw patient tables.
    """
    if not planned or not tool_results:
        return None
    if str(planned[0][0] or "") != "get_latest_prediction_summary":
        return None
    b0 = tool_results[0]
    if not isinstance(b0, dict) or b0.get("ok") is not True:
        return None
    inner = b0.get("result") or {}
    if not isinstance(inner, dict):
        return None
    if resolve_latest_prediction_readonly_reply_mode(inner) != "task_deterministic":
        return None
    pred = inner.get("prediction")
    if not isinstance(pred, dict):
        return None
    if str(pred.get("kind") or "") == "batch":
        return None
    jid = str(pred.get("job_id") or "").strip()
    if not jid.startswith("job_"):
        return None
    if task_repo is None:
        return None
    full = task_repo.get(jid)
    if not isinstance(full, dict) or str(full.get("status") or "") != "completed":
        return None
    if infer_predict_is_batch(full) is True:
        return None
    lab = pred.get("predicted_label")
    prob = pred.get("predicted_probability")
    if lab is None and prob is None:
        return None
    if lab is None or prob is None:
        return None
    has_shap = False
    if (
        len(planned) >= 2
        and str(planned[1][0] or "") == "get_prediction_explanation_summary"
        and len(tool_results) >= 2
    ):
        b1 = tool_results[1]
        if isinstance(b1, dict) and b1.get("ok") is True:
            ex = (b1.get("result") or {}).get("explanation")
            if isinstance(ex, dict):
                has_shap = bool(ex.get("explanation_available"))
    return {
        "job_id": jid,
        "task_name": str(pred.get("task_name") or "").strip(),
        "model_name": str(pred.get("model_name") or pred.get("display_name") or "").strip(),
        "predicted_label": lab,
        "predicted_probability": prob,
        "prediction_status": "completed",
        "has_shap_explanation": has_shap,
    }


def try_extract_batch_prediction_readonly_success(
    planned: List[Tuple[str, Dict[str, Any]]],
    tool_results: List[Dict[str, Any]],
    task_repo: Any,
) -> Optional[Dict[str, Any]]:
    """
    When read-only get_latest_prediction_summary binds to a completed batch job, build the batch verbalization bundle from the task row.
    """
    if not planned or not tool_results:
        return None
    if str(planned[0][0] or "") != "get_latest_prediction_summary":
        return None
    b0 = tool_results[0]
    if not isinstance(b0, dict) or b0.get("ok") is not True:
        return None
    inner = b0.get("result") or {}
    if not isinstance(inner, dict):
        return None
    if resolve_latest_prediction_readonly_reply_mode(inner) != "task_deterministic":
        return None
    pred = inner.get("prediction")
    if not isinstance(pred, dict):
        return None
    jid = str(pred.get("job_id") or "").strip()
    if not jid.startswith("job_"):
        return None
    if task_repo is None:
        return None
    full = task_repo.get(jid)
    if not isinstance(full, dict) or str(full.get("status") or "") != "completed":
        return None
    return try_build_batch_prediction_completed_bundle_from_task(full)


def try_build_single_prediction_execution_bundle_from_task(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build a completed single-sample prediction fact bundle from a predict_outcome task row (no read-only tools; no raw patient tables).

    Selector is already bound to a concrete task; prediction deterministic core (summary + factual bundle) owns truth.
    This only projects into the verbalizer input shape reused by build_prediction_result_response_payload like the read-only chain.
    """
    if not isinstance(task, dict):
        return None
    if str(task.get("job_type") or "") != JobType.predict_outcome.value:
        return None
    if str(task.get("status") or "") != "completed":
        return None
    if infer_predict_is_batch(task) is True:
        return None
    fb = build_prediction_factual_bundle_from_task(task, ReadonlyTruncateTracker())
    if not isinstance(fb, dict):
        return None
    public = fb.get("public_summary")
    if not isinstance(public, dict):
        return None
    if str(public.get("kind") or "").lower() == "batch":
        return None
    lab = public.get("predicted_label")
    prob = public.get("predicted_probability")
    if lab is None or prob is None:
        return None
    if str(lab).strip() == "":
        return None
    jid = str(task.get("id") or "").strip()
    if not jid.startswith("job_"):
        return None
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    tn = str(public.get("task_name") or params.get("task_name") or "").strip()
    mn = str(
        public.get("display_name")
        or public.get("model_name")
        or public.get("model_id")
        or params.get("model_id")
        or ""
    ).strip()
    has_shap = bool(public.get("explanation_supported"))
    return {
        "job_id": jid,
        "task_name": tn,
        "model_name": mn,
        "predicted_label": lab,
        "predicted_probability": prob,
        "prediction_status": "completed",
        "has_shap_explanation": has_shap,
    }


def _batch_output_filename_from_download_url(url: str) -> str:
    u = str(url or "").strip().replace("\\", "/")
    if not u:
        return ""
    seg = u.rstrip("/").split("/")[-1]
    return seg or ""


def try_build_batch_prediction_completed_bundle_from_task(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build a completed batch-prediction fact bundle from a predict_outcome task row (no results CSV reads; no eval metrics).

    Truth comes primarily from task.result_summary, with batch inferred via params; job_id/status from the task row.
    """
    if not isinstance(task, dict):
        return None
    if str(task.get("job_type") or "") != JobType.predict_outcome.value:
        return None
    if str(task.get("status") or "") != "completed":
        return None
    jid = str(task.get("id") or "").strip()
    if not jid.startswith("job_"):
        return None
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    is_batch = str(rs.get("prediction_type") or "").strip().lower() == "batch" or infer_predict_is_batch(task) is True
    if not is_batch:
        return None
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    task_name = str(rs.get("task_name") or params.get("task_name") or "").strip()
    model_name = str(rs.get("display_name") or rs.get("model_id") or params.get("model_id") or "").strip()
    tr = int(rs.get("total_rows") or 0)
    sr = int(rs.get("succeeded_rows") or 0)
    fr = int(rs.get("failed_rows") or 0)
    durl = str(rs.get("download_url") or "").strip()
    ofn = _batch_output_filename_from_download_url(durl)
    raw_warn = rs.get("warnings")
    warnings_list: List[str] = []
    if isinstance(raw_warn, list):
        warnings_list = [str(x).strip() for x in raw_warn if str(x).strip()]
    headline = str(rs.get("headline") or rs.get("summary_text") or "").strip() or chat_msg(
        "zh", "payload.batch_bundle.headline_counts", tr=tr, sr=sr, fr=fr
    )
    return {
        "job_id": jid,
        "task_name": task_name,
        "model_name": model_name,
        "total_records": tr,
        "successful_records": sr,
        "failed_records": fr,
        "download_url": durl,
        "output_filename": ofn,
        "warnings": warnings_list[:20],
        "headline": headline,
    }


def build_batch_prediction_result_response_payload(
    bundle: Dict[str, Any],
    *,
    final_route: str,
    payload_source: str,
    locale: Optional[str] = None,
) -> ResponsePayload:
    """
    Successful batch prediction (task-level aggregate) → batch_prediction_result; fixed strict_template, no LLM polish.
    """
    enp = _english_payload_copy(locale)
    tr = int(bundle.get("total_records") or 0)
    sr = int(bundle.get("successful_records") or 0)
    fr = int(bundle.get("failed_records") or 0)
    durl = str(bundle.get("download_url") or "").strip()
    ofn = str(bundle.get("output_filename") or "").strip() or _batch_output_filename_from_download_url(durl)
    has_dl = bool(durl)
    raw_head = str(bundle.get("headline") or "").strip()
    if enp:
        if raw_head and re.search(r"[\u4e00-\u9fff]", raw_head):
            headline = chat_msg(locale, "payload.batch_bundle.headline_counts", tr=tr, sr=sr, fr=fr)
        elif raw_head:
            headline = raw_head
        else:
            headline = chat_msg(locale, "payload.batch_result.headline_fallback")
    else:
        headline = raw_head or chat_msg(locale, "payload.batch_result.headline_fallback")

    sem_override = str(bundle.get("semantic_summary") or "").strip()
    facts: Dict[str, Any] = {
        "task_kind": "predict_outcome",
        "prediction_type": "batch",
        "job_id": bundle.get("job_id"),
        "task_name": str(bundle.get("task_name") or ""),
        "model_name": str(bundle.get("model_name") or ""),
        "total_records": tr,
        "successful_records": sr,
        "failed_records": fr,
        "download_url": durl,
        "output_filename": ofn,
        "has_download_url": has_dl,
        "aggregate_execution_note": chat_msg(locale, "payload.batch_result.aggregate_note_zh"),
    }
    if sem_override:
        facts["semantic_summary"] = sem_override

    summary_points = [
        chat_msg(locale, "payload.batch_result.summary_zh_1"),
        chat_msg(locale, "payload.batch_result.summary_zh_2", tr=tr, sr=sr, fr=fr),
    ]
    if tr > 0 and fr > 0:
        summary_points.append(chat_msg(locale, "payload.batch_result.summary_zh_partial_fail"))
    if has_dl and ofn:
        summary_points.append(chat_msg(locale, "payload.batch_result.summary_zh_filename", ofn=ofn))
    elif has_dl:
        summary_points.append(chat_msg(locale, "payload.batch_result.summary_zh_has_dl"))
    else:
        summary_points.append(chat_msg(locale, "payload.batch_result.summary_zh_no_dl"))

    strict_lines = [
        "Batch prediction (aggregate): task completed.",
        f"Row totals — total: {tr}, succeeded: {sr}, failed: {fr}.",
        "Do not claim offline evaluation metrics, confusion tables, calibration, or per-row agreement with any reference labels.",
        "Do not headline single-sample predicted label/probability as the primary outcome.",
    ]
    if has_dl:
        strict_lines.append(f"Download URL (verbatim): {durl}")
    else:
        strict_lines.append("No download URL present in locked facts; do not imply a downloadable aggregate file.")

    na_override = str(bundle.get("next_action") or "").strip()
    if na_override:
        next_action = na_override
    else:
        next_action = chat_msg(locale, "payload.batch_result.next_action_zh")

    truth_warnings = [str(x).strip() for x in (bundle.get("warnings") or []) if str(x).strip()]

    trace = {
        "payload_source": payload_source,
        "answer_type": "batch_prediction_result",
        "verbalization_mode": "strict_template",
        "final_route": final_route,
        "job_id": bundle.get("job_id"),
    }
    return ResponsePayload(
        answer_type="batch_prediction_result",
        verbalization_mode="strict_template",
        headline=headline,
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=truth_warnings[:12],
        strict_lines=strict_lines,
        ui_payload={"route": final_route},
        trace=trace,
    )


def build_prediction_result_response_payload(
    bundle: Dict[str, Any],
    *,
    final_route: str,
    payload_source: str = "single_prediction_readonly_success",
    locale: Optional[str] = None,
) -> ResponsePayload:
    """
    Successful single-sample prediction → prediction_result payload (shared by read-only chain or terminal task binding).

    predicted_label / predicted_probability are hard fields in facts; strict_lines pin English factual sentences.
    """
    enp = _english_payload_copy(locale)
    tn = str(bundle.get("task_name") or "").strip()
    mn = str(bundle.get("model_name") or "").strip()
    if not tn:
        tn = chat_msg(locale, "payload.pred_result.unnamed_task")
    if not mn:
        mn = chat_msg(locale, "payload.pred_result.unnamed_model")
    lab = bundle.get("predicted_label")
    prob = bundle.get("predicted_probability")
    has_shap = bool(bundle.get("has_shap_explanation"))
    prob_txt = _format_probability_en(prob) if enp else _format_probability_zh(prob)

    sem_override = str(bundle.get("semantic_summary") or "").strip()
    facts: Dict[str, Any] = {
        "task_name": tn,
        "model_name": mn,
        "predicted_label": lab,
        "predicted_probability": prob,
        "prediction_status": "completed",
        "has_shap_explanation": has_shap,
        "semantic_summary": sem_override or chat_msg(locale, "payload.pred_result.semantic_summary", tn=tn, lab=lab),
    }

    summary_points = [
        chat_msg(locale, "payload.pred_result.summary_zh_1", tn=tn),
        chat_msg(locale, "payload.pred_result.summary_zh_2", lab=lab, prob_txt=prob_txt),
        chat_msg(locale, "payload.pred_result.summary_zh_3"),
    ]
    if has_shap:
        summary_points.append(chat_msg(locale, "payload.pred_result.summary_zh_shap_yes"))
    else:
        summary_points.append(chat_msg(locale, "payload.pred_result.summary_zh_shap_no"))

    strict_lines = [
        "Prediction status: completed",
        f"Predicted label: {lab!s}",
        f"Predicted probability: {prob!s}",
    ]
    if has_shap:
        strict_lines.append(
            "Explanation / SHAP summary may be available in the workbench UI; availability does not mean exhaustive analysis was already performed."
        )
    strict_lines.append(
        "Model output is not a substitute for individualized clinical judgment; keep wording as model estimate or model display."
    )

    na_override = str(bundle.get("next_action") or "").strip()
    if na_override:
        next_action = na_override
    else:
        if has_shap:
            next_action = chat_msg(locale, "payload.pred_result.next_zh_shap")
        else:
            next_action = chat_msg(locale, "payload.pred_result.next_zh_no_shap")

    warnings = [
        chat_msg(locale, "payload.pred_result.warning_zh_1"),
        chat_msg(locale, "payload.pred_result.warning_zh_2"),
        chat_msg(locale, "payload.pred_result.warning_zh_3"),
    ]

    mode: str = "llm_polish" if is_llm_polish_answer_type("prediction_result") else "strict_template"
    trace = {
        "payload_source": payload_source,
        "answer_type": "prediction_result",
        "verbalization_mode": mode,
        "final_route": final_route,
        "job_id": bundle.get("job_id"),
        "truth_has_shap_explanation": has_shap,
    }
    headline = chat_msg(locale, "payload.pred_result.headline_zh")
    return ResponsePayload(
        answer_type="prediction_result",
        verbalization_mode=mode,
        headline=headline,
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=warnings,
        strict_lines=strict_lines,
        ui_payload={"route": final_route},
        trace=trace,
    )


def _primary_metric_pair_from_train_summary(
    public: Optional[Dict[str, Any]],
    rs: Dict[str, Any],
) -> Tuple[Optional[str], Any]:
    """Pick one headline metric from public key_metrics or raw rs (aligned with result_presentation; no invented fields)."""
    km = None
    if isinstance(public, dict) and isinstance(public.get("key_metrics"), dict):
        km = public.get("key_metrics")
    if km is None and isinstance(rs.get("key_metrics"), dict):
        km = rs.get("key_metrics")
    if not isinstance(km, dict) or not km:
        return None, None
    for key in ("auc", "AUC", "c_index", "C_index", "accuracy", "Accuracy"):
        v = km.get(key)
        if isinstance(v, (int, float)):
            return str(key), v
    for _k, v in list(km.items())[:6]:
        if isinstance(v, (int, float)):
            return str(_k), v
    return None, None


def _training_release_state_fields(rs: Dict[str, Any]) -> Tuple[Any, Any, str]:
    """
    Returns (model_registered_raw, is_published_raw, release_state).
    release_state: released | not_released | unknown (unknown means summary lacked registration/publish booleans).
    """
    has_mr = "model_registered" in rs
    has_ip = "is_published" in rs
    if not has_mr and not has_ip:
        return rs.get("model_registered"), rs.get("is_published"), "unknown"
    released = (bool(rs.get("model_registered")) if has_mr else False) or (
        bool(rs.get("is_published")) if has_ip else False
    )
    return rs.get("model_registered"), rs.get("is_published"), "released" if released else "not_released"


def try_build_training_completed_bundle_from_task(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build a completed-training fact bundle from a train_model task row (no patient tables; no NL parsing).

    Deterministic training core (task status + result_summary + training factual bundle) owns truth;
    this only projects into the verbalizer input shape.
    """
    if not isinstance(task, dict):
        return None
    if str(task.get("job_type") or "") != JobType.train_model.value:
        return None
    if str(task.get("status") or "") != "completed":
        return None
    jid = str(task.get("id") or "").strip()
    if not jid.startswith("job_"):
        return None
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    fb = build_training_factual_bundle(task, None)
    public = fb.get("public_summary") if isinstance(fb, dict) else None
    if not rs and not public:
        return None
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    task_name = str(params.get("task_name") or rs.get("headline") or "").strip()
    pub_d = public if isinstance(public, dict) else {}
    mid = str(pub_d.get("model_id") or rs.get("model_id") or params.get("model_id") or "").strip()
    mname = str(rs.get("display_name") or pub_d.get("trained_model_programmer_name") or mid or "").strip()
    if not mname and mid:
        mname = mid
    pm_n, pm_v = _primary_metric_pair_from_train_summary(public if isinstance(public, dict) else None, rs)
    mr_raw, ip_raw, rel_state = _training_release_state_fields(rs)
    target_task = str(rs.get("task_kind") or params.get("task_kind") or pub_d.get("task_kind") or "").strip() or None

    dataset_disp = str(
        params.get("dataset_display_name")
        or params.get("upload_filename")
        or params.get("original_filename")
        or ""
    ).strip()[:200]
    algo_line = str(rs.get("trained_model_programmer_name") or params.get("model_type") or "").strip()[:120]
    metrics_flat: Dict[str, str] = {}
    if isinstance(pub_d, dict):
        km = pub_d.get("key_metrics")
        if isinstance(km, dict):
            for kk, vv in list(km.items())[:16]:
                metrics_flat[str(kk)[:64]] = str(vv)[:64]
        fmm = pub_d.get("final_model_metrics")
        if isinstance(fmm, dict):
            for kk, vv in list(fmm.items())[:16]:
                if len(metrics_flat) >= 24:
                    break
                k2 = str(kk)[:64]
                if k2 not in metrics_flat:
                    metrics_flat[k2] = str(vv)[:64]
    artifacts = task.get("artifacts") if isinstance(task.get("artifacts"), dict) else {}
    narrative_has_shap = any(
        ("shap" in k.lower() and "beeswarm" in k.lower()) for k in artifacts.keys()
    )

    narrative_feature_count: Optional[int] = None
    narrative_feature_names: Optional[List[str]] = None
    locked = rs.get("final_features_locked")
    if isinstance(locked, list) and locked:
        narrative_feature_names = [str(x).strip() for x in locked if str(x).strip()][:64]
        narrative_feature_count = len(locked)
    else:
        ffc = rs.get("final_feature_count")
        if ffc is not None:
            try:
                narrative_feature_count = int(ffc)
            except (TypeError, ValueError):
                narrative_feature_count = None

    return {
        "job_id": jid,
        "task_name": task_name,
        "target_task": target_task,
        "model_id": mid or None,
        "model_name": mname,
        "training_status": "completed",
        "primary_metric_name": pm_n,
        "primary_metric_value": pm_v,
        "model_registered": mr_raw,
        "is_published": ip_raw,
        "release_state": rel_state,
        "narrative_dataset_display": dataset_disp or None,
        "narrative_algorithm": algo_line or None,
        "narrative_metrics_flat": metrics_flat,
        "narrative_has_shap_beeswarm": narrative_has_shap,
        "narrative_feature_count": narrative_feature_count,
        "narrative_feature_names": narrative_feature_names,
    }


def try_extract_training_completed_readonly_success(
    planned: List[Tuple[str, Dict[str, Any]]],
    tool_results: List[Dict[str, Any]],
    task_repo: Any,
) -> Optional[Dict[str, Any]]:
    """When read-only get_latest_training_summary points at a completed train task in the repo, reuse the row fact bundle."""
    if not planned or not tool_results:
        return None
    if str(planned[0][0] or "") != "get_latest_training_summary":
        return None
    b0 = tool_results[0]
    if not isinstance(b0, dict) or b0.get("ok") is not True:
        return None
    inner = b0.get("result") or {}
    if not isinstance(inner, dict):
        return None
    tpub = inner.get("task")
    if not isinstance(tpub, dict):
        return None
    jid = str(tpub.get("id") or "").strip()
    if not jid.startswith("job_") or task_repo is None:
        return None
    full = task_repo.get(jid)
    if not isinstance(full, dict) or str(full.get("job_type") or "") != JobType.train_model.value:
        return None
    if str(full.get("status") or "") != "completed":
        return None
    return try_build_training_completed_bundle_from_task(full)


def build_training_completed_response_payload(
    bundle: Dict[str, Any],
    *,
    final_route: str,
    payload_source: str,
    locale: Optional[str] = None,
) -> ResponsePayload:
    """
    Completed training job → training_completed payload (read-only chain or terminal binding).

    model_registered / is_published / release_state are hard fields; verbalizer must not infer opposite values.
    """
    tn = str(bundle.get("task_name") or "").strip()
    tt = bundle.get("target_task")
    mid = bundle.get("model_id")
    mname = str(bundle.get("model_name") or "").strip()
    if not mname and mid is not None and str(mid).strip():
        mname = str(mid).strip()
    if not tn:
        tn = chat_msg(locale, "payload.train_completed.unnamed_task")
    if not mname:
        mname = chat_msg(locale, "payload.train_completed.unnamed_model")
    pm_n = bundle.get("primary_metric_name")
    pm_v = bundle.get("primary_metric_value")
    mr = bundle.get("model_registered")
    ip = bundle.get("is_published")
    rel = str(bundle.get("release_state") or "unknown")
    jid = bundle.get("job_id")

    pm_txt = ""
    if pm_n is not None and pm_v is not None:
        pm_txt = f"{pm_n}={pm_v!s}"

    sem_override = str(bundle.get("semantic_summary") or "").strip()
    facts: Dict[str, Any] = {
        "training_status": "completed",
        "task_name": tn,
        "target_task": tt,
        "model_id": mid,
        "model_name": mname,
        "primary_metric_name": pm_n,
        "primary_metric_value": pm_v,
        "model_registered": mr,
        "is_published": ip,
        "release_state": rel,
        "job_id": jid,
        "narrative_dataset_display": bundle.get("narrative_dataset_display"),
        "narrative_algorithm": bundle.get("narrative_algorithm"),
        "narrative_metrics_flat": bundle.get("narrative_metrics_flat") or {},
        "narrative_has_shap_beeswarm": bundle.get("narrative_has_shap_beeswarm"),
        "narrative_feature_count": bundle.get("narrative_feature_count"),
        "narrative_feature_names": bundle.get("narrative_feature_names"),
        "semantic_summary": sem_override or chat_msg(locale, "payload.train_completed.semantic_summary", tn=tn),
    }

    summary_points = [chat_msg(locale, "payload.train_completed.summary_zh_1", tn=tn)]
    if pm_txt:
        summary_points.append(chat_msg(locale, "payload.train_completed.summary_zh_metric", pm_txt=pm_txt))
    else:
        summary_points.append(chat_msg(locale, "payload.train_completed.summary_zh_no_metric"))
    if rel == "released":
        summary_points.append(chat_msg(locale, "payload.train_completed.summary_zh_released"))
    elif rel == "not_released":
        summary_points.append(chat_msg(locale, "payload.train_completed.summary_zh_not_released"))
    else:
        summary_points.append(chat_msg(locale, "payload.train_completed.summary_zh_unknown_1"))
        summary_points.append(chat_msg(locale, "payload.train_completed.summary_zh_unknown_2"))

    strict_lines: List[str] = ["Training status: completed"]
    if mid:
        strict_lines.append(f"Model identifier: {mid!s}")
    elif mname:
        strict_lines.append(f"Model display name: {mname!s}")
    else:
        strict_lines.append("Model identifier: (not stated in summary)")
    if pm_txt:
        strict_lines.append(f"Primary metric: {pm_txt}")
    strict_lines.append(f"Registration / release state: {rel} (model_registered={mr!s}, is_published={ip!s})")
    if rel == "unknown":
        strict_lines.append(
            "When release_state is unknown: do not assert published or unpublished; direct the user to task detail and model registry UI."
        )

    na_override = str(bundle.get("next_action") or "").strip()
    if na_override:
        next_action = na_override
    else:
        next_action = chat_msg(locale, "payload.train_completed.next_action_zh")

    warnings = [
        chat_msg(locale, "payload.train_completed.warning_zh_1"),
        chat_msg(locale, "payload.train_completed.warning_zh_2"),
        chat_msg(locale, "payload.train_completed.warning_zh_3"),
    ]
    if rel == "unknown":
        warnings.append(chat_msg(locale, "payload.train_completed.warning_zh_unknown"))

    mode: str = "llm_polish" if is_llm_polish_answer_type("training_completed") else "strict_template"
    trace = {
        "payload_source": payload_source,
        "answer_type": "training_completed",
        "verbalization_mode": mode,
        "final_route": final_route,
        "job_id": jid,
        "truth_release_state": rel,
    }
    headline = chat_msg(locale, "payload.train_completed.headline_zh")
    return ResponsePayload(
        answer_type="training_completed",
        verbalization_mode=mode,
        headline=headline,
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=warnings,
        strict_lines=strict_lines,
        ui_payload={"route": final_route},
        trace=trace,
    )


def _failure_reply_variant_from_intent(intent: str) -> str:
    return "fail_check_first" if str(intent or "").strip() == "fail_check_first" else "default"


def build_training_failed_response_payload(
    task: Dict[str, Any],
    *,
    intent: str,
    final_route: str,
    payload_source: str,
    locale: Optional[str] = None,
) -> ResponsePayload:
    """task-backed training failure → training_failed; fixed strict_template."""
    ff = build_task_backed_training_failure_facts(task, locale)
    variant = _failure_reply_variant_from_intent(intent)
    jid = str(task.get("id") or "").strip()
    facts: Dict[str, Any] = {
        "task_kind": JobType.train_model.value,
        "job_id": jid or None,
        "task_status": "failed",
        "failure_reply_variant": variant,
        "failure_stage_bucket": ff["failure_stage_bucket"],
        "current_stage": ff["current_stage"],
        "message": ff["message"],
        "error_hint": ff["error_hint"],
        "completed_at": task.get("completed_at"),
        "started_at": task.get("started_at"),
        "created_at": task.get("created_at"),
    }
    next_action = str(ff.get("next_action") or "").strip() or None
    summary_points = [
        chat_msg(locale, "payload.train_failed.summary_bucket_zh", bucket=ff["failure_stage_bucket"]),
        chat_msg(locale, "payload.train_failed.summary_hint_zh", hint=ff["error_hint"]),
    ]
    warnings = [
        chat_msg(locale, "payload.train_failed.warning_zh_1"),
        chat_msg(locale, "payload.train_failed.warning_zh_2"),
        chat_msg(locale, "payload.train_failed.warning_zh_3"),
    ]
    headline = chat_msg(locale, "payload.train_failed.headline_zh")
    strict_lines: List[str] = [
        "Task status: failed (training).",
        f"failure_stage_bucket verbatim: {ff['failure_stage_bucket']}",
        f"current_stage verbatim: {ff['current_stage']}",
        f"error_hint verbatim: {ff['error_hint']}",
        "Do not describe training as completed, released, metrics-ready, or model-published.",
    ]
    trace = {
        "payload_source": payload_source,
        "answer_type": "training_failed",
        "verbalization_mode": "strict_template",
        "final_route": final_route,
        "job_id": jid,
    }
    return ResponsePayload(
        answer_type="training_failed",
        verbalization_mode="strict_template",
        headline=headline,
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=warnings,
        strict_lines=strict_lines,
        ui_payload={"route": final_route, "job_id": jid},
        trace=trace,
    )


def build_prediction_failed_response_payload(
    task: Dict[str, Any],
    *,
    intent: str,
    final_route: str,
    payload_source: str,
    locale: Optional[str] = None,
) -> ResponsePayload:
    """task-backed predict_outcome failure → prediction_failed; fixed strict_template."""
    ff = build_task_backed_prediction_failure_facts(task, locale)
    variant = _failure_reply_variant_from_intent(intent)
    jid = str(task.get("id") or "").strip()
    facts: Dict[str, Any] = {
        "task_kind": JobType.predict_outcome.value,
        "job_id": jid or None,
        "task_status": "failed",
        "failure_reply_variant": variant,
        "failure_stage_bucket": ff["failure_stage_bucket"],
        "current_stage": ff["current_stage"],
        "message": ff["message"],
        "error_hint": ff["error_hint"],
        "completed_at": task.get("completed_at"),
        "started_at": task.get("started_at"),
        "created_at": task.get("created_at"),
    }
    next_action = str(ff.get("next_action") or "").strip() or None
    summary_points = [
        chat_msg(locale, "payload.pred_failed.summary_bucket_zh", bucket=ff["failure_stage_bucket"]),
        chat_msg(locale, "payload.pred_failed.summary_hint_zh", hint=ff["error_hint"]),
    ]
    warnings = [
        chat_msg(locale, "payload.pred_failed.warning_zh_1"),
        chat_msg(locale, "payload.pred_failed.warning_zh_2"),
        chat_msg(locale, "payload.pred_failed.warning_zh_3"),
    ]
    headline = chat_msg(locale, "payload.pred_failed.headline_zh")
    strict_lines: List[str] = [
        "Task status: failed (prediction, task-backed only).",
        f"failure_stage_bucket verbatim: {ff['failure_stage_bucket']}",
        f"current_stage verbatim: {ff['current_stage']}",
        f"error_hint verbatim: {ff['error_hint']}",
        "Do not describe prediction label, probability, batch row outcomes, or SHAP as available.",
    ]
    trace = {
        "payload_source": payload_source,
        "answer_type": "prediction_failed",
        "verbalization_mode": "strict_template",
        "final_route": final_route,
        "job_id": jid,
    }
    return ResponsePayload(
        answer_type="prediction_failed",
        verbalization_mode="strict_template",
        headline=headline,
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=warnings,
        strict_lines=strict_lines,
        ui_payload={"route": final_route, "job_id": jid},
        trace=trace,
    )


# Dedicated payload builder for training_draft_created.
# This answer type currently bypasses the generic semantic-to-payload projection
# to keep draft semantics isolated and strict. Revisit if dedicated builders
# become the common pattern for more answer types.
def build_training_draft_created_response_payload(
    sem: AgentSemanticPayload,
    *,
    final_route: str,
    can_confirm: bool,
    pending_action_id: Optional[str] = None,
    completed_summary: Optional[str] = None,
    missing_field_keys: Optional[List[str]] = None,
    draft_context: str = "standard",
) -> ResponsePayload:

    ui: Dict[str, Any] = {"route": final_route}
    if pending_action_id:
        ui["pending_action_id"] = str(pending_action_id).strip()

    missing_zh = [str(x).strip() for x in (sem.missing_fields or []) if str(x).strip()]
    cs = (completed_summary or "").strip()
    if not cs:
        for x in sem.key_points or []:
            t = str(x).strip()
            if t.startswith(PARSED_VALID_INFO_SUMMARY_PREFIX_ZH):
                cs = t.split(ZH_FULLWIDTH_COLON, 1)[-1].strip()
                break
            if t.startswith("Parsed valid information summary:"):
                cs = t.split(":", 1)[-1].strip()
                break

    if missing_field_keys is not None:
        keys = [str(x).strip() for x in missing_field_keys if str(x).strip()]
    else:
        keys = list(missing_zh)

    primary_next_zh = ""
    if sem.allowed_next_steps:
        primary_next_zh = str(sem.allowed_next_steps[0]).strip()

    facts: Dict[str, Any] = {
        "action_domain": "training",
        "draft_lifecycle": "created_pending_user",
        "can_confirm_in_ui": bool(can_confirm),
        "awaiting_explicit_user_confirm_before_run": bool(can_confirm),
        "awaiting_field_completion_before_confirm": not bool(can_confirm),
        "missing_fields_zh": missing_zh,
        "missing_field_keys": keys,
        "completed_summary": cs,
        "draft_context": str(draft_context or "standard").strip(),
        "primary_next_step_zh": primary_next_zh,
        "user_intent": (sem.user_intent or "").strip(),
        "semantic_headline": (sem.summary or "").strip(),
    }

    trace = {
        "payload_source": "training_draft_created_semantic",
        "answer_type": "training_draft_created",
        "verbalization_mode": "strict_template",
        "final_route": final_route,
        "can_confirm": bool(can_confirm),
    }
    return ResponsePayload(
        answer_type="training_draft_created",
        verbalization_mode="strict_template",
        headline=None,
        facts=facts,
        summary_points=[],
        next_action=None,
        warnings=[],
        strict_lines=[],
        ui_payload=ui,
        trace=trace,
    )


def _load_recommendation_artifact_dict(task_repo: Any, job_id: str) -> Optional[Dict[str, Any]]:
    """Read recommendation.json from the artifact dir only; return None on failure (no deep scans or multi-file walks)."""
    fn = getattr(task_repo, "artifacts_dir", None)
    if not callable(fn):
        return None
    try:
        p = Path(fn(job_id)) / "recommendation.json"
    except (TypeError, ValueError):
        return None
    if not p.is_file():
        return None
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


def try_build_recommendation_completed_bundle_from_task(
    task: Dict[str, Any],
    task_repo: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:

    if not isinstance(task, dict):
        return None
    if str(task.get("job_type") or "") != JobType.recommend_regimen.value:
        return None
    if str(task.get("status") or "") != "completed":
        return None
    jid = str(task.get("id") or "").strip()
    if not jid.startswith("job_"):
        return None
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    top1 = rs.get("recommended_top1_regimen")
    if not isinstance(top1, dict):
        return None
    rtp = rs.get("recommended_top1_probability")
    if rtp is None:
        return None

    art: Optional[Dict[str, Any]] = None
    if task_repo is not None:
        art = _load_recommendation_artifact_dict(task_repo, jid)

    obs = rs.get("observed_prediction_probability")
    sd = rs.get("score_direction")
    delta = rs.get("delta_probability_top1")
    if isinstance(art, dict):
        if obs is None:
            obs = art.get("observed_prediction_probability")
        if sd is None:
            sd = art.get("score_direction")
        if delta is None:
            delta = art.get("delta_probability_top1")

    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    model_id = str(rs.get("model_id") or params.get("model_id") or "").strip() or None
    task_kind = str(rs.get("task_kind") or JobType.recommend_regimen.value).strip()
    headline = str(rs.get("headline") or "").strip()
    mode = str(rs.get("mode") or params.get("mode") or "").strip() or None

    top_preview: Optional[List[Dict[str, Any]]] = None
    if isinstance(art, dict) and isinstance(art.get("top_candidates"), list):
        top_preview = []
        for c in art["top_candidates"][:8]:
            if not isinstance(c, dict):
                continue
            top_preview.append(
                {
                    "regimen_id": c.get("regimen_id"),
                    "regimen_name": c.get("regimen_name"),
                    "rank": c.get("rank"),
                    "predicted_probability": c.get("predicted_probability"),
                }
            )
        if not top_preview:
            top_preview = None

    return {
        "job_id": jid,
        "task_kind": task_kind,
        "model_id": model_id,
        "headline": headline,
        "mode": mode,
        "score_direction": sd,
        "observed_prediction_probability": obs,
        "recommended_top1_probability": rtp,
        "delta_probability_top1": delta,
        "recommended_top1_regimen": dict(top1),
        "top_candidates_preview": top_preview,
    }


def build_recommendation_result_response_payload(
    bundle: Dict[str, Any],
    *,
    final_route: str,
    payload_source: str,
) -> ResponsePayload:

    top1 = bundle.get("recommended_top1_regimen")
    if not isinstance(top1, dict):
        top1 = {}
    obs = bundle.get("observed_prediction_probability")
    rtp = bundle.get("recommended_top1_probability")
    delta = bundle.get("delta_probability_top1")
    sd = bundle.get("score_direction")
    tn = str(bundle.get("headline") or "").strip()
    task_kind = str(bundle.get("task_kind") or JobType.recommend_regimen.value)
    mode = bundle.get("mode")
    mid = bundle.get("model_id")
    preview = bundle.get("top_candidates_preview")

    facts: Dict[str, Any] = {
        "task_kind": task_kind,
        "mode": mode,
        "model_id": mid,
        "score_direction": sd,
        "observed_prediction_probability": obs,
        "recommended_top1_probability": rtp,
        "delta_probability_top1": delta,
        "recommended_top1_regimen": dict(top1),
        "job_id": bundle.get("job_id"),
    }
    if isinstance(preview, list) and preview:
        facts["top_candidates_preview"] = list(preview)

    # User-visible copy is rendered solely by verbalize_recommendation_result from structured facts
    # (no summary_points / strict_lines / warnings — those previously leaked internal constraints into chat).
    summary_points: List[str] = []
    strict_lines: List[str] = []

    na_override = str(bundle.get("next_action") or "").strip()
    next_action: Optional[str] = na_override or None

    warnings: List[str] = []

    trace = {
        "payload_source": payload_source,
        "answer_type": "recommendation_result",
        "verbalization_mode": "strict_template",
        "final_route": final_route,
        "job_id": bundle.get("job_id"),
    }
    return ResponsePayload(
        answer_type="recommendation_result",
        verbalization_mode="strict_template",
        headline=tn or "",
        facts=facts,
        summary_points=summary_points,
        next_action=next_action,
        warnings=warnings,
        strict_lines=strict_lines,
        ui_payload={"route": final_route, "job_id": bundle.get("job_id")},
        trace=trace,
    )
