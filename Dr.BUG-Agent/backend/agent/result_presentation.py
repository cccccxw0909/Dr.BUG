"""Result summaries for completed/failed tasks: consumes existing task fields only; no routing or task selection."""

from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional, Tuple

from backend.prediction.prediction_factual_core import build_prediction_factual_bundle_from_task
from backend.tools.read_only_privacy import ReadonlyTruncateTracker
from backend.training.training_factual_core import (
    best_model_evidence_line,
    build_training_factual_bundle,
    can_claim_best_model,
    can_claim_notable_from_filter_summary,
)

from backend.agent.chat_output_locale import is_english_output_locale
from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons import zh_result_presentation_heuristics as zrph
from backend.agent.i18n.lexicons.zh_typography import ZH_FULLWIDTH_PERIOD, ZH_SENTENCE_TERMINATORS

ObjectType = Literal["train", "predict"]


def _rp_t(locale: Optional[str], zh: str, en: str) -> str:
    return en if is_english_output_locale(locale) else zh


PredictMode = Literal["batch", "single", "unknown"]

# Read-only chat deterministic policy aligned with get_latest_prediction_summary top-level source (task|history|none)
LatestPredictionReadonlyReplyMode = Literal["task_deterministic", "history_summary_only", "none"]


def _first_line(text: str, max_len: int = 100) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    line = t.splitlines()[0].strip()
    if len(line) > max_len:
        return line[: max_len - 1] + "…"
    return line


def _strip_exception_type(line: str) -> str:
    m = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception|Warning))\s*:\s*(.+)$", line)
    if m:
        return m.group(2).strip()
    return line


def _scrub_paths(s: str, locale: Optional[str] = None) -> str:
    rep = chat_msg(locale, "result_presentation.scrub.local_path_placeholder")
    s = re.sub(r"[A-Za-z]:\\[^\s]+", rep, s)
    s = re.sub(r"/(?:home|Users|var)[^\s]+", rep, s)
    return s


def humanize_error_hint(err: Optional[str], object_type: ObjectType, locale: Optional[str] = None) -> str:
    """Summarize error_message into one short user-facing line without stack traces or internal object names."""
    if not err or not str(err).strip():
        if object_type == "train":
            return chat_msg(locale, "result_presentation.error_hint.default_train")
        return chat_msg(locale, "result_presentation.error_hint.default_predict")
    raw = _first_line(str(err), 160)
    raw = _strip_exception_type(raw)
    raw = _scrub_paths(raw, locale)
    raw = re.sub(
        r"job_[a-z0-9_]+",
        chat_msg(locale, "result_presentation.error_hint.job_placeholder"),
        raw,
        flags=re.I,
    )
    if len(raw) > 80:
        raw = raw[:79] + "…"
    return raw


def infer_predict_is_batch(task: Dict[str, Any]) -> Optional[bool]:
    """
    Infer batch vs single from task params/result_summary.
    Return None when structurally ambiguous; callers may disambiguate using the user's wording (e.g. batch cues).
    """
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}

    if params.get("batch") is True or params.get("is_batch") is True:
        return True
    mode = str(params.get("mode") or params.get("prediction_mode") or "").lower()
    if mode in ("batch", "bulk", "file", "table"):
        return True
    if any(str(params.get(k) or "").strip() for k in ("input_file", "batch_file", "upload_file", "csv_path")):
        return True

    pf = params.get("patient_features")
    if isinstance(pf, list):
        return True if len(pf) > 1 else (False if len(pf) == 1 else None)
    if isinstance(pf, dict):
        return False

    for key in ("total_rows", "succeeded_rows", "row_count", "n_rows"):
        v = rs.get(key)
        if isinstance(v, int) and v > 1:
            return True
    if rs.get("batch") is True:
        return True
    if str(rs.get("run_kind") or "").lower() == "batch":
        return True

    if params.get("patient_features") is None and str(task.get("job_type") or "") == "predict_outcome":
        return False

    return None


def _predict_run_mode(task: Dict[str, Any], batch_hint: bool) -> PredictMode:
    ib = infer_predict_is_batch(task)
    if ib is True:
        return "batch"
    if ib is False:
        return "single"
    return "batch" if batch_hint else "unknown"


def _normalize_probability(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n > 1:
        n = n / 100.0
    if n < 0 or n > 1:
        return None
    return n


def _format_prob_phrase(p: Optional[float]) -> str:
    if p is None:
        return ""
    pct = round(p * 100.0, 2)
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct}%"


def _try_train_metric_sentence(
    rs: Dict[str, Any],
    *,
    public_summary: Optional[Dict[str, Any]] = None,
    locale: Optional[str] = None,
) -> Optional[str]:
    """
    Pull one readable sentence from key_metrics; prefer the same public projection as read-only tools,
    avoiding raw result_summary drift vs LLM-visible summaries.
    """
    km = None
    if public_summary and isinstance(public_summary.get("key_metrics"), dict):
        km = public_summary.get("key_metrics")
    if km is None:
        km = rs.get("key_metrics")
    if km is None:
        return None
    if isinstance(km, dict):
        for key in ("auc", "AUC", "c_index", "C_index", "accuracy", "Accuracy"):
            v = km.get(key)
            if isinstance(v, (int, float)):
                if "auc" in key.lower():
                    label_disp = "AUC"
                elif "c_index" in key.lower():
                    label_disp = "C-index"
                else:
                    label_disp = chat_msg(locale, "result_presentation.metric_label.accuracy")
                value_str = f"{v:.4g}"
                return chat_msg(
                    locale,
                    "result_presentation.train_metric.primary_metric_sentence",
                    label=label_disp,
                    value=value_str,
                )
        # First shallow numeric hit
        for _k, v in list(km.items())[:6]:
            if isinstance(v, (int, float)):
                return chat_msg(locale, "result_presentation.train_metric.metrics_available")
    return None


def _append_next_step(body: str, step: str, locale: Optional[str] = None) -> str:
    """Append a minimal next-step hint after terminal summary without repeating the same action as the body."""
    b = (body or "").rstrip()
    s = (step or "").strip()
    if not s:
        return b
    if is_english_output_locale(locale):
        if not b.endswith((".", "!", "?")):
            b = f"{b}."
        return f"{b} Next step: {s}"
    if not b.endswith(ZH_SENTENCE_TERMINATORS):
        b = f"{b}{ZH_FULLWIDTH_PERIOD}"
    return chat_msg(locale, "result_presentation.append_next_step.zh_appended", body=b, step=s)


def _train_failure_bucket(stage: str, message: str) -> str:
    sl = (stage or "").lower()
    msg_l = (message or "").lower()
    if (
        "phase1" in sl
        or "data_check" in sl
        or "valid" in sl
        or zrph.TRAIN_MSG_VALIDATION_CUE in msg_l
        or "validation" in msg_l
    ):
        return "data_validation_prep"
    if "phase2" in sl or "feature" in sl:
        return "feature_screening"
    if "phase3" in sl:
        return "feature_confirmation"
    if "phase4" in sl or "train" in sl or "model" in sl:
        return "model_training_eval"
    if "phase5" in sl or "publish" in sl:
        return "wrap_up_publish"
    return "generic"


def _next_step_train_completed(_task: Dict[str, Any], locale: Optional[str] = None) -> str:
    return chat_msg(locale, "result_presentation.next_step.train_completed")


def compose_train_completed_standard(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    """P8: unified factual core for training completed (independent of phrasing/entry path)."""
    bundle = build_training_factual_bundle(task, None)
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    public = bundle.get("public_summary")
    parts: list[str] = [chat_msg(locale, "result_presentation.train_completed.opening")]
    metric_line = _try_train_metric_sentence(
        rs, public_summary=public if isinstance(public, dict) else None, locale=locale
    )
    if metric_line:
        parts.append(metric_line)
    parts.append(chat_msg(locale, "result_presentation.train_completed.fact_tail"))
    return "".join(parts)


def format_train_completed_presentation(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    core = compose_train_completed_standard(task, locale)
    return _append_next_step(core, _next_step_train_completed(task, locale), locale)


def format_train_canceled_presentation(_task: Dict[str, Any], locale: Optional[str] = None) -> str:
    return chat_msg(locale, "result_presentation.train_canceled.body")


def format_predict_canceled_presentation(_task: Dict[str, Any], locale: Optional[str] = None) -> str:
    return chat_msg(locale, "result_presentation.predict_canceled.body")


def _next_step_train_failed(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    stage = str(task.get("current_stage") or "")
    msg = str(task.get("message") or "")
    bucket = _train_failure_bucket(stage, msg)
    return chat_msg(locale, f"result_presentation.train_failure.next_step.{bucket}")


def format_train_failed_presentation(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    stage = str(task.get("current_stage") or "")
    msg = str(task.get("message") or "")
    err = task.get("error_message")
    hint = humanize_error_hint(err if isinstance(err, str) else None, "train", locale)
    bucket = _train_failure_bucket(stage, msg)
    rough = chat_msg(locale, f"result_presentation.train_failure.rough.{bucket}")
    core = chat_msg(locale, "result_presentation.train_failure.core", rough=rough, hint=hint)
    return _append_next_step(core, _next_step_train_failed(task, locale), locale)


def _predict_label_prob_phrases_from_public(public: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Use only prediction factual core single public_summary (same as read-only tools); do not fall back to raw display lines."""
    plab = public.get("predicted_label")
    label_phrase = str(plab).strip() if plab is not None and str(plab).strip() != "" else None
    prob_phrase: Optional[str] = None
    if public.get("predicted_probability") is not None:
        prob_phrase = _format_prob_phrase(_normalize_probability(public.get("predicted_probability")))
    return label_phrase, prob_phrase


def _label_prob_for_completed_predict_task(task: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    bundle = build_prediction_factual_bundle_from_task(task, ReadonlyTruncateTracker())
    public = bundle.get("public_summary") if bundle else None
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    if isinstance(public, dict) and public.get("kind") == "single":
        return _predict_label_prob_phrases_from_public(public)
    return _predict_label_prob_phrases(rs)


def _predict_label_prob_phrases(rs: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Return (label phrase, probability phrase) using existing display fields or normalized numbers."""
    ld = str(rs.get("label_display_line") or "").strip()
    pd = str(rs.get("probability_display_line") or "").strip()
    if ld:
        label_phrase = ld
    else:
        lo = rs.get("label_display") or rs.get("outcome_display") or rs.get("predicted_label")
        if lo is None or str(lo).strip() == "":
            label_phrase = None
        else:
            label_phrase = str(lo).strip()

    if pd:
        prob_phrase = pd
    else:
        p = _normalize_probability(rs.get("predicted_probability") or rs.get("probability"))
        if p is None:
            prob_phrase = None
        else:
            prob_phrase = _format_prob_phrase(p)
    return label_phrase, prob_phrase


def _next_step_predict_completed_single(_task: Dict[str, Any], locale: Optional[str] = None) -> str:
    return chat_msg(locale, "result_presentation.next_step.predict_completed_single")


def _next_step_predict_completed_batch(_task: Dict[str, Any], locale: Optional[str] = None) -> str:
    return chat_msg(locale, "result_presentation.next_step.predict_completed_batch")


def _next_step_predict_completed_unknown(_task: Dict[str, Any], locale: Optional[str] = None) -> str:
    return chat_msg(locale, "result_presentation.next_step.predict_completed_unknown")


def compose_predict_batch_completed_aggregate_factual(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    """Batch predict_outcome completed: restate row-level execution aggregates from task summary only; no evaluation claims."""
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    tr = int(rs.get("total_rows") or 0)
    sr = int(rs.get("succeeded_rows") or 0)
    fr = int(rs.get("failed_rows") or 0)
    return chat_msg(locale, "result_presentation.predict_completed.batch_aggregate", tr=tr, sr=sr, fr=fr)


def compose_predict_single_completed_factual(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    """P8: unified factual core for single prediction completed (independent of phrasing/entry path)."""
    label_p, prob_p = _label_prob_for_completed_predict_task(task)
    if is_english_output_locale(locale):
        parts: list[str] = [chat_msg(locale, "result_presentation.predict_completed.single_head")]
        if label_p and prob_p:
            parts.append(
                chat_msg(locale, "result_presentation.predict_completed.single_label_prob", label_p=label_p, prob_p=prob_p)
            )
        elif label_p:
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_only_line", label_p=label_p))
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_extra"))
        elif prob_p:
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_only_line", prob_p=prob_p))
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_extra"))
        else:
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_no_label_prob"))
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_interpretation_note"))
        return "".join(parts)
    parts = [chat_msg(locale, "result_presentation.predict_completed.single_head")]
    if label_p and prob_p:
        parts.append(
            chat_msg(locale, "result_presentation.predict_completed.single_label_prob", label_p=label_p, prob_p=prob_p)
        )
    elif label_p:
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_only_line", label_p=label_p))
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_extra"))
    elif prob_p:
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_only_line", prob_p=prob_p))
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_extra"))
    else:
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_no_label_prob"))
    parts.append(chat_msg(locale, "result_presentation.predict_completed.single_interpretation_note"))
    return "".join(parts)


def compose_predict_single_risk(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    """Restate label/probability only and disclaim medical risk stratification (distinct from pred_meaning factual core)."""
    label_p, prob_p = _label_prob_for_completed_predict_task(task)
    if is_english_output_locale(locale):
        parts: list[str] = [chat_msg(locale, "result_presentation.predict_completed.single_head")]
        if label_p and prob_p:
            parts.append(
                chat_msg(locale, "result_presentation.predict_completed.single_label_prob", label_p=label_p, prob_p=prob_p)
            )
        elif label_p:
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_only_line", label_p=label_p))
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_extra"))
        elif prob_p:
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_only_line", prob_p=prob_p))
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_extra"))
        else:
            parts.append(chat_msg(locale, "result_presentation.predict_completed.single_no_label_prob"))
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_risk_note"))
        return "".join(parts)
    parts = [chat_msg(locale, "result_presentation.predict_completed.single_head")]
    if label_p and prob_p:
        parts.append(
            chat_msg(locale, "result_presentation.predict_completed.single_label_prob", label_p=label_p, prob_p=prob_p)
        )
    elif label_p:
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_only_line", label_p=label_p))
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_extra"))
    elif prob_p:
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_prob_only_line", prob_p=prob_p))
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_label_extra"))
    else:
        parts.append(chat_msg(locale, "result_presentation.predict_completed.single_no_label_prob"))
    parts.append(chat_msg(locale, "result_presentation.predict_completed.single_risk_note"))
    return "".join(parts)


def format_predict_completed_presentation(
    task: Dict[str, Any], *, batch_hint: bool, locale: Optional[str] = None
) -> str:
    mode = _predict_run_mode(task, batch_hint)
    if mode == "batch":
        core = chat_msg(locale, "result_presentation.predict_completed.batch_done_download")
        return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)

    core = compose_predict_single_completed_factual(task, locale)
    return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)


def format_predict_completed_presentation_unknown_batch(
    task: Dict[str, Any], locale: Optional[str] = None
) -> str:
    """Completed copy when batch intent cannot be inferred from the question and task structure is ambiguous."""
    core = chat_msg(locale, "result_presentation.predict_completed.unknown_batch_done")
    return _append_next_step(core, _next_step_predict_completed_unknown(task, locale), locale)


def _predict_failure_bucket(stage: str, err_hint: str) -> str:
    sl = (stage or "").lower()
    eh = str(err_hint or "")
    eh_lower = eh.lower()
    if "upload" in sl or zrph.PREDICT_HINT_READ_CUE in eh or "read" in eh_lower:
        return "read_input"
    if (
        "map" in sl
        or zrph.PREDICT_HINT_FIELD_CUE in eh
        or zrph.PREDICT_HINT_MAP_CUE in eh
        or "column" in eh_lower
        or "field" in eh_lower
    ):
        return "field_mapping"
    if "load" in sl or zrph.PREDICT_HINT_MODEL_CUE in eh or "model" in eh_lower:
        return "load_model_env"
    if "predict" in sl:
        return "generating"
    return "generic"


def _next_step_predict_failed(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    stage = str(task.get("current_stage") or "")
    err = task.get("error_message")
    hint = humanize_error_hint(err if isinstance(err, str) else None, "predict", locale)
    bucket = _predict_failure_bucket(stage, hint)
    return chat_msg(locale, f"result_presentation.predict_failure.next_step.{bucket}")


def format_predict_failed_presentation(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    stage = str(task.get("current_stage") or "")
    err = task.get("error_message")
    hint = humanize_error_hint(err if isinstance(err, str) else None, "predict", locale)
    bucket = _predict_failure_bucket(stage, hint)
    rough = chat_msg(locale, f"result_presentation.predict_failure.rough.{bucket}")
    core = chat_msg(locale, "result_presentation.predict_failure.core", rough=rough, hint=hint)
    return _append_next_step(core, _next_step_predict_failed(task, locale), locale)


def _batch_has_aggregate_risk_stats(rs: Dict[str, Any]) -> bool:
    for key in ("high_risk_count", "high_risk_rows", "risk_high_count", "n_high_risk"):
        v = rs.get(key)
        if isinstance(v, int) and v >= 0:
            return True
    return False


def format_train_release_status_reply(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    """
    Answer release status for the currently bound training task only; do not conflate with workbench current_model registration.

    Consumes only booleans/flags already present in task.result_summary; never fabricates.
    """
    st = str(task.get("status") or "")
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    mid = str(rs.get("model_id") or "").strip()

    if st in ("failed", "canceled", "cancelled"):
        return chat_msg(locale, "result_presentation.train_release.failed_or_canceled")
    if st != "completed":
        status_display = st if st else chat_msg(locale, "result_presentation.common.status_unknown")
        return chat_msg(locale, "result_presentation.train_release.not_completed", status=status_display)
    has_mr = "model_registered" in rs
    has_ip = "is_published" in rs
    if not has_mr and not has_ip:
        base = chat_msg(locale, "result_presentation.train_release.no_verifiable_fields")
        mid_part = (
            chat_msg(locale, "result_presentation.train_release.mid_phrase_model_id", mid=mid) if mid else ""
        )
        return base + mid_part
    released = (bool(rs.get("model_registered")) if has_mr else False) or (
        bool(rs.get("is_published")) if has_ip else False
    )
    if released:
        base = chat_msg(locale, "result_presentation.train_release.released")
        mid_part = (
            chat_msg(locale, "result_presentation.train_release.mid_phrase_model_id", mid=mid) if mid else ""
        )
        suffix = chat_msg(locale, "result_presentation.train_release.released_suffix_compare")
        return base + mid_part + suffix
    return chat_msg(locale, "result_presentation.train_release.not_released")


def _train_completed_by_intent(
    task: Dict[str, Any], intent: str, locale: Optional[str] = None
) -> str:
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    if intent in ("default", ""):
        return format_train_completed_presentation(task, locale)

    if intent == "train_performance":
        core = compose_train_completed_standard(task, locale)
        return _append_next_step(core, _next_step_train_completed(task, locale), locale)

    if intent == "train_good_bad":
        core = chat_msg(locale, "result_presentation.train_completed.good_bad_unified")
        return _append_next_step(core, _next_step_train_completed(task, locale), locale)

    if intent == "train_best_model":
        if can_claim_best_model(rs):
            ev = best_model_evidence_line(rs)
            if ev:
                core = chat_msg(locale, "result_presentation.train_intent.best_model_marked", ev=ev)
            else:
                core = chat_msg(locale, "result_presentation.train_completed.best_model_degrade")
        else:
            core = chat_msg(locale, "result_presentation.train_completed.best_model_degrade")
        return _append_next_step(core, _next_step_train_completed(task, locale), locale)

    if intent == "train_notable":
        if can_claim_notable_from_filter_summary(rs):
            fs = str(rs.get("filter_summary") or "").strip()
            clip = fs[:119] + "…" if len(fs) > 120 else fs
            core = chat_msg(locale, "result_presentation.train_intent.filter_summary_excerpt", clip=clip)
        else:
            core = chat_msg(locale, "result_presentation.train_completed.notable_degrade")
        return _append_next_step(core, _next_step_train_completed(task, locale), locale)

    return format_train_completed_presentation(task, locale)


def _train_failed_by_intent(task: Dict[str, Any], intent: str, locale: Optional[str] = None) -> str:
    if intent == "fail_check_first":
        stage = str(task.get("current_stage") or "")
        msg = str(task.get("message") or "")
        err = task.get("error_message")
        hint = humanize_error_hint(err if isinstance(err, str) else None, "train", locale)
        bucket = _train_failure_bucket(stage, msg)
        rough = chat_msg(locale, f"result_presentation.train_failure.rough.{bucket}")
        core = chat_msg(locale, "result_presentation.train_failure.fail_check_first", hint=hint, rough=rough)
        return _append_next_step(core, _next_step_train_failed(task, locale), locale)
    return format_train_failed_presentation(task, locale)


def _predict_completed_by_intent(
    task: Dict[str, Any], intent: str, batch_hint: bool, locale: Optional[str] = None
) -> str:
    if intent in ("default", ""):
        return format_predict_completed_presentation(task, batch_hint=batch_hint, locale=locale)

    mode = _predict_run_mode(task, batch_hint)
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    label_p, prob_p = _label_prob_for_completed_predict_task(task)

    if intent == "pred_ask_label":
        if mode == "batch":
            core = chat_msg(locale, "result_presentation.predict_intent.batch_no_single_label")
            return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)
        if label_p:
            core = chat_msg(locale, "result_presentation.predict_intent.single_label", label_p=label_p)
        else:
            core = chat_msg(locale, "result_presentation.predict_intent.single_label_missing")
        return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)

    if intent == "pred_ask_prob":
        if mode == "batch":
            core = chat_msg(locale, "result_presentation.predict_intent.batch_no_single_prob")
            return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)
        if prob_p:
            core = chat_msg(locale, "result_presentation.predict_intent.single_prob", prob_p=prob_p)
        else:
            core = chat_msg(locale, "result_presentation.predict_intent.single_prob_missing")
        return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)

    if intent.startswith("pred_batch"):
        if mode != "batch":
            core = chat_msg(locale, "result_presentation.predict_intent.single_without_batch_stats")
            return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)
        batch_tail = chat_msg(locale, "result_presentation.predict_completed.batch_no_aggregate_stats")
        short = chat_msg(locale, "result_presentation.predict_intent.batch_done_short")
        if intent == "pred_batch_overview":
            core = short + batch_tail
            return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)
        if intent == "pred_batch_anomaly":
            core = short + batch_tail
            return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)
        if intent == "pred_batch_high_risk":
            if _batch_has_aggregate_risk_stats(rs):
                n = rs.get("high_risk_count") or rs.get("high_risk_rows") or rs.get("n_high_risk")
                core = chat_msg(locale, "result_presentation.predict_intent.batch_count_stat", n=n)
            else:
                core = short + batch_tail
            return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)
        if intent == "pred_batch_next":
            core = short + batch_tail
            return _append_next_step(core, _next_step_predict_completed_batch(task, locale), locale)
        return format_predict_completed_presentation(task, batch_hint=batch_hint, locale=locale)

    # --- Single-record style intents ---
    if intent == "pred_meaning":
        return format_predict_completed_presentation(task, batch_hint=batch_hint, locale=locale)

    if intent == "pred_risk":
        core = compose_predict_single_risk(task, locale)
        return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)

    if intent == "pred_why":
        core = chat_msg(locale, "result_presentation.predict_intent.pred_why")
        return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)

    if intent == "pred_caution":
        core = compose_predict_single_completed_factual(task, locale)
        core += chat_msg(locale, "result_presentation.predict_intent.pred_caution_suffix")
        return _append_next_step(core, _next_step_predict_completed_single(task, locale), locale)

    return format_predict_completed_presentation(task, batch_hint=batch_hint, locale=locale)


def _predict_failed_by_intent(task: Dict[str, Any], intent: str, locale: Optional[str] = None) -> str:
    if intent == "fail_check_first":
        stage = str(task.get("current_stage") or "")
        err = task.get("error_message")
        hint = humanize_error_hint(err if isinstance(err, str) else None, "predict", locale)
        bucket = _predict_failure_bucket(stage, hint)
        rough = chat_msg(locale, f"result_presentation.predict_failure.rough.{bucket}")
        core = chat_msg(locale, "result_presentation.predict_failure.fail_check_first", hint=hint, rough=rough)
        return _append_next_step(core, _next_step_predict_failed(task, locale), locale)
    return format_predict_failed_presentation(task, locale)


def compose_disclaimed_latest_prediction_when_workspace_not_run(
    inner: Dict[str, Any],
    *,
    workspace_model_id: str = "",
    locale: Optional[str] = None,
) -> str:
    """
    When the workbench has no bindable completed prediction but the user explicitly asks for global/historical latest:
    state there is no current run, optionally echo the tool-projected historic summary, and avoid conflating page context
    (e.g. survival_28d) with unrelated history.
    """
    wm = str(workspace_model_id or "").strip()
    head = chat_msg(locale, "result_presentation.latest_prediction_disclaimer.no_current_run")
    pred = inner.get("prediction") if isinstance(inner.get("prediction"), dict) else None
    if not pred:
        tail = chat_msg(locale, "result_presentation.latest_prediction_disclaimer.no_history_summary")
        return head + tail

    tn = str(pred.get("task_name") or "").strip() or "—"
    mn = str(pred.get("model_name") or pred.get("model_id") or pred.get("display_name") or "").strip() or "—"
    kind = str(pred.get("kind") or "").lower()
    lines = [
        head,
        chat_msg(locale, "result_presentation.latest_prediction_disclaimer.history_intro"),
    ]

    mid = str(pred.get("model_id") or pred.get("model_name") or "").strip()
    if wm and mid and wm != mid:
        lines.append(
            chat_msg(
                locale,
                "result_presentation.latest_prediction_disclaimer.model_mismatch_note",
                mid=mid,
                wm=wm,
            )
        )

    summary_text = str(pred.get("summary_text") or "").strip()
    if kind == "batch":
        lines.append(
            chat_msg(
                locale,
                "result_presentation.latest_prediction_disclaimer.batch_record",
                tn=tn,
                mn=mn,
                summary_text=summary_text,
            )
        )
    else:
        lab = pred.get("predicted_label")
        prob = pred.get("predicted_probability")
        lab_s = str(lab).strip() if lab is not None and str(lab).strip() != "" else "—"
        ptxt = ""
        if isinstance(prob, (int, float)):
            ptxt = f"{round(float(prob) * 100.0, 2)}%"
        if ptxt:
            lines.append(
                chat_msg(
                    locale,
                    "result_presentation.latest_prediction_disclaimer.single_record_label_prob",
                    tn=tn,
                    mn=mn,
                    lab_s=lab_s,
                    ptxt=ptxt,
                )
            )
        else:
            lines.append(
                chat_msg(
                    locale,
                    "result_presentation.latest_prediction_disclaimer.single_record_label_only",
                    tn=tn,
                    mn=mn,
                    lab_s=lab_s,
                )
            )

    src = str(inner.get("source") or "").lower()
    if src == "task":
        lines.append(chat_msg(locale, "result_presentation.latest_prediction_disclaimer.task_source_note"))
    return "\n".join(lines)


def resolve_latest_prediction_readonly_reply_mode(inner: Dict[str, Any]) -> LatestPredictionReadonlyReplyMode:
    """
    Decide which deterministic chat exit is allowed for read-only "latest prediction" results (explicit rules for orchestrator).

    Aligns with the top-level ``source`` from read-only tools (see read_only_tools._get_latest_prediction_summary):

    - **task_deterministic**: payload merged from a task row and ``prediction`` carries ``predict_outcome_task``
      with a valid ``job_id``. Allows ``terminal_reply_for_task_and_intent`` and other task-bound deterministic copy;
      body still comes from the factual bundle (compose path), not raw display lines.

    - **history_summary_only**: payload from prediction history index/records — **not** equivalent to a deterministic
      "current task" result. Skip task-bound terminal and fixed summary+explanation blocks (avoid template tone posing
      as task details); let the LLM answer under tool JSON constraints or use another safe downgrade.

    - **none**: no latest prediction summary; do not claim a result; skip task-bound deterministic.

    Preserves the fork between read-only global latest vs "fetch job then terminal": when history is newer, chat must
    not reuse a task's terminal phrasing to impersonate that global summary.
    """
    src = str(inner.get("source") or "none").strip().lower()
    if src not in ("task", "history", "none"):
        src = "none"
    pred = inner.get("prediction")
    if src == "none" or not isinstance(pred, dict):
        return "none"
    if src == "history":
        return "history_summary_only"
    # src == "task"
    if str(pred.get("source") or "") != "predict_outcome_task":
        return "none"
    jid = str(pred.get("job_id") or "").strip()
    if not jid.startswith("job_"):
        return "none"
    return "task_deterministic"


def build_task_backed_training_failure_facts(
    task: Dict[str, Any], locale: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract task-backed training failure facts from a task row (for ResponsePayload); do not assemble final user prose here.
    """
    stage = str(task.get("current_stage") or "")
    msg = str(task.get("message") or "")
    err = task.get("error_message")
    hint = humanize_error_hint(err if isinstance(err, str) else None, "train", locale)
    bucket = _train_failure_bucket(stage, msg)
    rough_display = chat_msg(locale, f"result_presentation.train_failure.rough.{bucket}")
    return {
        "failure_stage_bucket": rough_display,
        "current_stage": stage,
        "message": msg,
        "error_hint": hint,
        "next_action": _next_step_train_failed(task, locale),
    }


def build_task_backed_prediction_failure_facts(
    task: Dict[str, Any], locale: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract task-backed prediction failure facts from a predict_outcome task row (for ResponsePayload); do not assemble final user prose here.
    """
    stage = str(task.get("current_stage") or "")
    msg = str(task.get("message") or "")
    err = task.get("error_message")
    hint = humanize_error_hint(err if isinstance(err, str) else None, "predict", locale)
    bucket = _predict_failure_bucket(stage, hint)
    rough_display = chat_msg(locale, f"result_presentation.predict_failure.rough.{bucket}")
    return {
        "failure_stage_bucket": rough_display,
        "current_stage": stage,
        "message": msg,
        "error_hint": hint,
        "next_action": _next_step_predict_failed(task, locale),
    }


def terminal_reply_for_task_and_intent(
    task: Dict[str, Any],
    kind: str,
    intent: str,
    *,
    batch_hint: bool = False,
    locale: Optional[str] = None,
) -> Optional[str]:
    """
    Deterministic reply on a resolved terminal task for a result-style question.
    kind: 'train' | 'predict'; intent from classify_terminal_result_intent or 'default'.
    """
    st = str(task.get("status") or "")
    if kind == "train":
        if intent == "train_release_status":
            return format_train_release_status_reply(task, locale)
        if st == "completed":
            return _train_completed_by_intent(task, intent, locale)
        if st == "canceled":
            return format_train_canceled_presentation(task, locale)
        if st == "failed":
            return _train_failed_by_intent(task, intent, locale)
        return None
    if kind == "predict":
        if st == "completed":
            return _predict_completed_by_intent(task, intent, batch_hint, locale)
        if st == "canceled":
            return format_predict_canceled_presentation(task, locale)
        if st == "failed":
            return _predict_failed_by_intent(task, intent, locale)
        return None
    return None

