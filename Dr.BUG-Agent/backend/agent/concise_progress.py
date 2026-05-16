"""Minimal progress/ETA questions: no LLM, no chatContext stitching—one or two sentences from the task repo only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from backend.agent.chat_output_locale import infer_batch_hint, normalize_chat_output_locale
from backend.agent.status_presentation import (
    format_no_active_tasks_reply,
    format_predict_status_reply,
    format_train_status_reply,
    train_running_duration_supplement,
)
from backend.agent.status_query_router import (
    _normalize,
    _wants_context,
    _wants_failure,
    _wants_prediction_summary,
    _wants_training_summary,
)
from backend.agent.i18n.lexicons.zh_concise_progress import (
    ZH_BATCH_PREDICT_PHRASE,
    ZH_FILTER,
    ZH_PRED_QUALITY_PHRASES,
    ZH_PRED_RESULT_PHRASE,
    ZH_RESULT_OUTCOME_HINTS,
    ZH_TRAIN_QUALITY_PHRASES,
    ZH_TRAIN_RESULT_PHRASE,
)
from backend.agent.i18n.lexicons.zh_routing_core_tokens import (
    ZH_AND,
    ZH_MODEL,
    ZH_MODEL_TRAIN_PHRASE,
    ZH_PREDICT,
    ZH_RESULT,
    ZH_TRAIN,
)
from backend.agent.i18n.lexicons.zh_typography import (
    ZH_FULLWIDTH_COMMA,
    ZH_FULLWIDTH_EXCLAMATION,
    ZH_FULLWIDTH_QUESTION_MARK,
)
from backend.agent.zh_intent_lexicon import (
    ZH_COMPLETION_CONJUNCTION_BLOCKERS,
    ZH_COMPLETION_QUERY_HINTS,
    ZH_CONCISE_PLAIN_STATUS_LONG,
    ZH_CONCISE_PLAIN_STATUS_SHORT,
    ZH_CONCISE_PROGRESS_BLOCK_TERMS,
    ZH_CONCISE_PROGRESS_TRIGGER_TERMS,
    ZH_FILTER_STAGE_TIME_HINT_TERMS,
    ZH_TRAIN_DEMONSTRATIVE_PREFIX_RE,
    ZH_TRAIN_ETA_KEYWORDS,
    ZH_TRAIN_PHASE_PROGRESS_KEYWORDS,
    ZH_TRAIN_PIPELINE_SURFACE_TERMS,
)

_ACTIVE = frozenset({"queued", "running", "waiting_user"})

# Possible focus-job keys in chat_context (workbench focus job; prefer focus_job_id)
_FOCUS_JOB_KEYS = (
    "focus_job_id",
    "current_job_id",
    "active_job_id",
    "task_id",
    "selected_job_id",
)

_MAX_COMPLETION_QUERY_LEN = 120


def _normalize_for_match(text: str) -> str:
    """Normalize whitespace/full-width punctuation before completion/anchor matching."""
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace(ZH_FULLWIDTH_QUESTION_MARK, "?").replace(ZH_FULLWIDTH_EXCLAMATION, "!").replace(ZH_FULLWIDTH_COMMA, ",")
    return t.strip()


def _has_completion_shape(msg: str) -> bool:
    return any(h in msg for h in ZH_COMPLETION_QUERY_HINTS)


def _train_anchor_present(norm: str) -> bool:
    """Training-side anchors for completion questions (not a bare generic 'model' mention)."""
    if ZH_TRAIN in norm:
        return True
    if ZH_MODEL_TRAIN_PHRASE in norm:
        return True
    if ZH_TRAIN_DEMONSTRATIVE_PREFIX_RE.search(norm):
        return True
    return False


def _train_pipeline_surface_hit(norm: str) -> bool:
    """Surface phrases that point at the training pipeline UI without explicitly saying 'training' (same family as stage toasts)."""
    return any(
        k in norm
        for k in ZH_TRAIN_PIPELINE_SURFACE_TERMS
    ) or (ZH_FILTER in norm and any(x in norm for x in ZH_FILTER_STAGE_TIME_HINT_TERMS))


def _wants_train_runtime_surface_query(message: str) -> bool:
    """
    Duration/phase/progress questions that should still bind to the current training job when wants_concise_progress_only misses,
    avoiding generic LLM + pending boilerplate.
    """
    norm = _normalize_for_match(_normalize(message))
    if not norm or len(norm) > 96:
        return False
    if _wants_failure(norm) or _wants_context(norm):
        return False
    if ZH_PREDICT in norm and ZH_TRAIN not in norm:
        return False
    eta_like = any(
        k in norm
        for k in ZH_TRAIN_ETA_KEYWORDS
    )
    phase_like = any(
        k in norm
        for k in ZH_TRAIN_PHASE_PROGRESS_KEYWORDS
    )
    if not (eta_like or phase_like):
        return False
    return _train_anchor_present(norm) or _train_pipeline_surface_hit(norm)


def _resolve_train_task_for_eta_binding(
    task_repo: Any, raw: List[Dict[str, Any]], chat_context: Optional[Dict[str, Any]], message: str
) -> Optional[Dict[str, Any]]:
    focus = _get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("job_type") or "") == "train_model":
        return focus
    norm = _normalize_for_match(_normalize(message))
    if ZH_PREDICT in norm and ZH_TRAIN not in norm:
        return None
    active = _pick_active_tasks(raw)
    trains = [t for t in active if str(t.get("job_type") or "") == "train_model"]
    preds = [t for t in active if str(t.get("job_type") or "") == "predict_outcome"]
    if not trains:
        return None
    if _train_anchor_present(norm) or _train_pipeline_surface_hit(norm):
        return sorted(trains, key=_recency_key, reverse=True)[0]
    # "How much longer?" style without explicit anchors: bind to train only when no active prediction competes
    if trains and not preds:
        return sorted(trains, key=_recency_key, reverse=True)[0]
    return None


def _message_asks_duration_or_eta(message: str) -> bool:
    norm = _normalize_for_match(_normalize(message))
    return any(
        k in norm for k in ZH_TRAIN_ETA_KEYWORDS
    )


def _predict_anchor_present(norm: str) -> bool:
    return ZH_PREDICT in norm or ZH_BATCH_PREDICT_PHRASE in norm


def _looks_like_training_result_concept_question(msg: str) -> bool:
    from backend.agent.status_query_router import _looks_like_training_result_concept_question as _impl

    return _impl(msg)


def _looks_like_prediction_result_concept_question(msg: str) -> bool:
    from backend.agent.prediction_followup import looks_like_prediction_result_concept_question

    return looks_like_prediction_result_concept_question(msg)


def _wants_training_completion_query(msg: str) -> bool:
    """Training anchor + completion semantics; does not call _wants_training_summary."""
    norm = _normalize_for_match(_normalize(msg))
    if not norm or len(norm) > _MAX_COMPLETION_QUERY_LEN:
        return False
    if _wants_failure(norm) or _wants_context(norm):
        return False
    if _looks_like_training_result_concept_question(norm):
        return False
    if any(x in norm for x in ZH_COMPLETION_CONJUNCTION_BLOCKERS):
        return False
    if ZH_AND in norm and ZH_TRAIN in norm:
        return False
    if ZH_TRAIN_RESULT_PHRASE in norm:
        return False
    if any(x in norm for x in ZH_TRAIN_QUALITY_PHRASES):
        return False
    if ZH_PREDICT in norm:
        return False
    if not _has_completion_shape(norm):
        return False
    if not _train_anchor_present(norm):
        return False
    return True


def _wants_prediction_completion_query(msg: str) -> bool:
    norm = _normalize_for_match(_normalize(msg))
    if not norm or len(norm) > _MAX_COMPLETION_QUERY_LEN:
        return False
    if _wants_failure(norm) or _wants_context(norm):
        return False
    if _looks_like_prediction_result_concept_question(norm):
        return False
    if any(x in norm for x in ZH_COMPLETION_CONJUNCTION_BLOCKERS):
        return False
    if ZH_AND in norm and ZH_PREDICT in norm:
        return False
    if ZH_PRED_RESULT_PHRASE in norm:
        return False
    if any(x in norm for x in ZH_PRED_QUALITY_PHRASES):
        return False
    if ZH_TRAIN in norm and ZH_PREDICT not in norm:
        return False
    if not _has_completion_shape(norm) and not (
        ZH_RESULT in norm and any(h in norm for h in ZH_RESULT_OUTCOME_HINTS)
    ):
        return False
    return _predict_anchor_present(norm)


def _wants_generic_completion_query(msg: str) -> bool:
    """Completion-shaped short asks without explicit train/predict anchors; disambiguate via active tasks."""
    norm = _normalize_for_match(_normalize(msg))
    if not norm or len(norm) > _MAX_COMPLETION_QUERY_LEN:
        return False
    if _wants_failure(norm) or _wants_context(norm):
        return False
    if any(x in norm for x in ZH_COMPLETION_CONJUNCTION_BLOCKERS):
        return False
    if not _has_completion_shape(norm):
        return False
    if _wants_training_completion_query(msg) or _wants_prediction_completion_query(msg):
        return False
    if ZH_TRAIN in norm or ZH_PREDICT in norm or ZH_MODEL in norm:
        return False
    return True


def wants_concise_progress_only(message: str) -> bool:
    msg = _normalize(message)
    if not msg or len(msg) > 80:
        return False
    if _wants_failure(msg) or _wants_context(msg) or _wants_training_summary(msg) or _wants_prediction_summary(msg):
        return False
    if any(x in msg for x in ZH_COMPLETION_CONJUNCTION_BLOCKERS):
        return False
    # Combined "check progress and go train/predict" sentences keep the original read-only tool chain + LLM
    if ZH_AND in msg and (ZH_TRAIN in msg or ZH_PREDICT in msg):
        return False
    if any(
        x in msg
        for x in ZH_CONCISE_PROGRESS_BLOCK_TERMS
    ):
        return False
    if any(
        k in msg
        for k in ZH_CONCISE_PROGRESS_TRIGGER_TERMS
    ):
        return True
    plain = msg.rstrip(f"{ZH_FULLWIDTH_QUESTION_MARK}?")
    if plain in ZH_CONCISE_PLAIN_STATUS_SHORT:
        return True
    if any(k in plain for k in ZH_CONCISE_PLAIN_STATUS_LONG):
        return True
    return False


def _recency_key(t: Dict[str, Any]) -> str:
    return str(t.get("started_at") or t.get("created_at") or "")


def _pick_active_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    act = [t for t in tasks if str(t.get("status") or "") in _ACTIVE]
    return sorted(act, key=_recency_key, reverse=True)


def _latest_by_job_type(raw: List[Dict[str, Any]], job_type: str) -> Optional[Dict[str, Any]]:
    rows = [t for t in raw if str(t.get("job_type") or "") == job_type]
    if not rows:
        return None
    rows.sort(key=lambda t: str(t.get("created_at") or ""), reverse=True)
    return rows[0]


def _get_focus_task(task_repo: Any, chat_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Workbench focus task: any job_type, first valid job_ id found via _FOCUS_JOB_KEYS order."""
    ctx = chat_context or {}
    for key in _FOCUS_JOB_KEYS:
        jid = str(ctx.get(key) or "").strip()
        if jid.startswith("job_"):
            got = task_repo.get(jid)
            if got:
                return got
    return None


def _resolve_train_task_for_status(
    task_repo: Any, raw: List[Dict[str, Any]], chat_context: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Prefer focused train_model > newest active train_model > latest train_model row (includes completed)."""
    focus = _get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("job_type") or "") == "train_model":
        return focus
    active = _pick_active_tasks(raw)
    trains = [t for t in active if str(t.get("job_type") or "") == "train_model"]
    if trains:
        return sorted(trains, key=_recency_key, reverse=True)[0]
    return _latest_by_job_type(raw, "train_model")


def _resolve_predict_task_for_status(
    task_repo: Any, raw: List[Dict[str, Any]], chat_context: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Prefer focused predict_outcome > newest active predict_outcome > latest predict_outcome row (includes completed)."""
    focus = _get_focus_task(task_repo, chat_context)
    if focus and str(focus.get("job_type") or "") == "predict_outcome":
        return focus
    active = _pick_active_tasks(raw)
    preds = [t for t in active if str(t.get("job_type") or "") == "predict_outcome"]
    if preds:
        return sorted(preds, key=_recency_key, reverse=True)[0]
    return _latest_by_job_type(raw, "predict_outcome")


def _resolve_target_task_for_generic_completion(
    task_repo: Any, raw: List[Dict[str, Any]], chat_context: Optional[Dict[str, Any]]
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Generic completion disambiguation: any focused type > active train > active pred > newest train vs pred."""
    focus = _get_focus_task(task_repo, chat_context)
    if focus:
        jt = str(focus.get("job_type") or "")
        if jt == "train_model":
            return ("train", focus)
        if jt == "predict_outcome":
            return ("predict", focus)
    active = _pick_active_tasks(raw)
    trains = [t for t in active if str(t.get("job_type") or "") == "train_model"]
    preds = [t for t in active if str(t.get("job_type") or "") == "predict_outcome"]
    if trains:
        return ("train", sorted(trains, key=_recency_key, reverse=True)[0])
    if preds:
        return ("predict", sorted(preds, key=_recency_key, reverse=True)[0])
    lt = _latest_by_job_type(raw, "train_model")
    lp = _latest_by_job_type(raw, "predict_outcome")
    if lt is None and lp is None:
        return None
    if lp is None:
        assert lt is not None
        return ("train", lt)
    if lt is None:
        assert lp is not None
        return ("predict", lp)
    if str(lt.get("created_at") or "") >= str(lp.get("created_at") or ""):
        return ("train", lt)
    return ("predict", lp)


def _train_task_sentence_for_done_query(task: Dict[str, Any], locale: str) -> str:
    return format_train_status_reply(task, locale)


def _train_sentence_for_progress_query(task: Dict[str, Any], locale: str) -> str:
    """Progress asks including completed/failed terminal states (copy comes from presentation helpers)."""
    return format_train_status_reply(task, locale)


def _predict_sentence_for_progress_query(task: Dict[str, Any], message: str, locale: str) -> str:
    batch = infer_batch_hint(_normalize(message), locale)
    return format_predict_status_reply(task, batch=batch, locale=locale)


def _predict_task_sentence_for_done_query(task: Dict[str, Any], message: str, locale: str) -> str:
    batch = infer_batch_hint(_normalize(message), locale)
    return format_predict_status_reply(task, batch=batch, locale=locale)


ProgressStylePick = Union[Tuple[Literal["train", "predict"], Dict[str, Any]], Literal["no_active_tasks"]]


def _resolve_progress_style_pick(
    message: str,
    raw: List[Dict[str, Any]],
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> Optional[ProgressStylePick]:
    if not wants_concise_progress_only(message):
        return None
    focus = _get_focus_task(task_repo, chat_context)
    if focus:
        jt = str(focus.get("job_type") or "")
        if jt == "train_model":
            return ("train", focus)
        if jt == "predict_outcome":
            return ("predict", focus)

    active = _pick_active_tasks(raw)
    trains = [t for t in active if str(t.get("job_type") or "") == "train_model"]
    preds = [t for t in active if str(t.get("job_type") or "") == "predict_outcome"]
    if trains:
        pick = sorted(trains, key=_recency_key, reverse=True)[0]
        return ("train", pick)
    if preds:
        pickp = sorted(preds, key=_recency_key, reverse=True)[0]
        return ("predict", pickp)

    lt = _latest_by_job_type(raw, "train_model")
    lp = _latest_by_job_type(raw, "predict_outcome")
    if lt is None and lp is None:
        return "no_active_tasks"
    if lp is None:
        assert lt is not None
        return ("train", lt)
    if lt is None:
        assert lp is not None
        return ("predict", lp)
    if str(lt.get("created_at") or "") >= str(lp.get("created_at") or ""):
        return ("train", lt)
    return ("predict", lp)


def _reply_progress_style(
    message: str,
    raw: List[Dict[str, Any]],
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]],
) -> Optional[str]:
    loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
    pick = _resolve_progress_style_pick(message, raw, task_repo, chat_context)
    if pick is None:
        return None
    if pick == "no_active_tasks":
        return format_no_active_tasks_reply(loc)
    kind, task = pick
    if kind == "train":
        return _train_sentence_for_progress_query(task, loc)
    return _predict_sentence_for_progress_query(task, message, loc)


def _reply_training_completion(
    message: str,
    task_repo: Any,
    raw: List[Dict[str, Any]],
    chat_context: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not _wants_training_completion_query(message):
        return None
    latest = _resolve_train_task_for_status(task_repo, raw, chat_context)
    if latest is None:
        return None
    loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
    return _train_task_sentence_for_done_query(latest, loc)


def _reply_prediction_completion(
    message: str,
    task_repo: Any,
    raw: List[Dict[str, Any]],
    chat_context: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not _wants_prediction_completion_query(message):
        return None
    latest = _resolve_predict_task_for_status(task_repo, raw, chat_context)
    if latest is None:
        return None
    loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
    return _predict_task_sentence_for_done_query(latest, message, loc)


def _reply_generic_completion(
    message: str,
    task_repo: Any,
    raw: List[Dict[str, Any]],
    chat_context: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not _wants_generic_completion_query(message):
        return None
    pair = _resolve_target_task_for_generic_completion(task_repo, raw, chat_context)
    if pair is None:
        return None
    kind, task = pair
    loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
    if kind == "train":
        return _train_task_sentence_for_done_query(task, loc)
    return _predict_task_sentence_for_done_query(task, message, loc)


def build_concise_progress_reply(
    message: str,
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    hit = resolve_concise_progress_hit(message, task_repo, chat_context)
    if hit is None:
        return None
    loc = normalize_chat_output_locale(chat_context=chat_context, message=message)
    return format_concise_progress_hit(hit, locale=loc)


ConciseProgressScene = Literal[
    "progress_style_train",
    "progress_style_predict",
    "training_completion",
    "prediction_completion",
    "generic_train_completion",
    "generic_predict_completion",
    "no_active_tasks",
]


@dataclass(frozen=True)
class ConciseProgressHit:
    """Same resolution as build_concise_progress_reply; exposed for semantics/finalization layers."""

    scene: ConciseProgressScene
    task: Optional[Dict[str, Any]]
    message: str


def resolve_concise_progress_hit(
    message: str,
    task_repo: Any,
    chat_context: Optional[Dict[str, Any]] = None,
) -> Optional[ConciseProgressHit]:
    msg_norm = _normalize(message)
    if not msg_norm:
        return None
    raw = task_repo.list()

    # Long asks or feature-screening + duration phrasing: still prefer binding to the current training job if narrow concise matcher misses.
    if _wants_train_runtime_surface_query(message):
        bind = _resolve_train_task_for_eta_binding(task_repo, raw, chat_context, message)
        if bind is not None:
            return ConciseProgressHit(scene="progress_style_train", task=bind, message=message)

    pick = _resolve_progress_style_pick(message, raw, task_repo, chat_context)
    if pick is not None:
        if pick == "no_active_tasks":
            return ConciseProgressHit(scene="no_active_tasks", task=None, message=message)
        kind, task = pick
        if kind == "train":
            return ConciseProgressHit(scene="progress_style_train", task=task, message=message)
        return ConciseProgressHit(scene="progress_style_predict", task=task, message=message)

    if _wants_training_completion_query(message):
        latest = _resolve_train_task_for_status(task_repo, raw, chat_context)
        if latest is not None:
            return ConciseProgressHit(scene="training_completion", task=latest, message=message)

    if _wants_prediction_completion_query(message):
        latestp = _resolve_predict_task_for_status(task_repo, raw, chat_context)
        if latestp is not None:
            return ConciseProgressHit(scene="prediction_completion", task=latestp, message=message)

    if _wants_generic_completion_query(message):
        pair = _resolve_target_task_for_generic_completion(task_repo, raw, chat_context)
        if pair is not None:
            gkind, gtask = pair
            if gkind == "train":
                return ConciseProgressHit(scene="generic_train_completion", task=gtask, message=message)
            return ConciseProgressHit(scene="generic_predict_completion", task=gtask, message=message)

    return None


def format_concise_progress_hit(hit: ConciseProgressHit, *, locale: Optional[str] = None) -> str:
    """Deterministic status wording (fallback when finalization fails)."""
    loc = locale if (locale is not None and str(locale).strip()) else normalize_chat_output_locale()
    if hit.scene == "no_active_tasks":
        return format_no_active_tasks_reply(loc)
    assert hit.task is not None
    if hit.scene == "progress_style_train":
        base = _train_sentence_for_progress_query(hit.task, loc)
        if _message_asks_duration_or_eta(hit.message) and str(hit.task.get("status") or "") == "running":
            sup = train_running_duration_supplement(hit.task, loc)
            return f"{base} {sup}".strip()
        return base
    if hit.scene == "progress_style_predict":
        return _predict_sentence_for_progress_query(hit.task, hit.message, loc)
    if hit.scene == "training_completion":
        return _train_task_sentence_for_done_query(hit.task, loc)
    if hit.scene == "prediction_completion":
        return _predict_task_sentence_for_done_query(hit.task, hit.message, loc)
    if hit.scene == "generic_train_completion":
        return _train_task_sentence_for_done_query(hit.task, loc)
    return _predict_task_sentence_for_done_query(hit.task, hit.message, loc)
