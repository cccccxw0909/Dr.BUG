"""Natural-language status layer: renders copy from task dict only; no task selection or routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from backend.agent.i18n import chat_msg
from backend.agent.result_presentation import (
    format_predict_canceled_presentation,
    format_predict_completed_presentation,
    format_predict_completed_presentation_unknown_batch,
    format_predict_failed_presentation,
    format_train_canceled_presentation,
    format_train_completed_presentation,
    format_train_failed_presentation,
    humanize_error_hint,
    infer_predict_is_batch,
)

ObjectType = Literal["train", "predict"]


@dataclass(frozen=True)
class StatusSemantics:
    object_type: ObjectType
    status: str
    stage_label: Optional[str]
    blocker_label: Optional[str]
    error_hint: Optional[str]


def _train_wait_blocker_phrase(wf: str, stage: str, locale: Optional[str] = None) -> str:
    """What the user is waiting on (aligned with workflow stage)."""
    if wf == "train_phase3_feature_confirm_pending" or stage == "train_phase3_feature_confirm_pending":
        return chat_msg(locale, "status.train_wait.features")
    if wf in ("train_phase4_train_config_pending", "train_phase4_config_confirm_pending") or stage in (
        "train_phase4_train_config_pending",
        "train_phase4_config_confirm_pending",
    ):
        return chat_msg(locale, "status.train_wait.hyperparams")
    if wf in ("train_phase5_publish_pending", "train_phase5_publish_confirm_pending") or stage in (
        "train_phase5_publish_pending",
        "train_phase5_publish_confirm_pending",
    ):
        return chat_msg(locale, "status.train_wait.publish")
    return chat_msg(locale, "status.train_wait.next_step")


def _train_waiting_card_title(wf: str, stage: str, locale: Optional[str] = None) -> str:
    """Short title aligned with frontend workflowCardBusinessTitle (status phrasing; no Phase numbers)."""
    if wf == "train_phase3_feature_confirm_pending" or stage == "train_phase3_feature_confirm_pending":
        return chat_msg(locale, "status.card.feature_confirm")
    if wf in ("train_phase4_train_config_pending", "train_phase4_config_confirm_pending") or stage in (
        "train_phase4_train_config_pending",
        "train_phase4_config_confirm_pending",
    ):
        return chat_msg(locale, "status.card.train_config")
    if wf in ("train_phase5_publish_pending", "train_phase5_publish_confirm_pending") or stage in (
        "train_phase5_publish_pending",
        "train_phase5_publish_confirm_pending",
    ):
        return chat_msg(locale, "status.card.publish_confirm")
    return chat_msg(locale, "status.card.pending")


def naturalize_train_stage(stage: str, locale: Optional[str] = None) -> str:
    sl = (stage or "").lower()
    if not sl or sl == "failed":
        return chat_msg(locale, "status.stage.train_workflow")
    if "phase1" in sl or "data_check" in sl or ("dataset" in sl and "valid" in sl):
        return chat_msg(locale, "status.stage.data_checks")
    if "phase2" in sl or "feature_search" in sl:
        return chat_msg(locale, "status.stage.feature_search")
    if "phase3" in sl and "apply" in sl:
        return chat_msg(locale, "status.stage.apply_features")
    if "phase3" in sl:
        return chat_msg(locale, "status.stage.feature_confirm")
    if "phase4" in sl and "training" in sl:
        return chat_msg(locale, "status.stage.model_training")
    if "phase4" in sl:
        return chat_msg(locale, "status.stage.model_training")
    if "phase5" in sl or "publish" in sl:
        return chat_msg(locale, "status.stage.wrap_publish")
    if sl in ("model_training", "evaluation") or "dataset_validation" in sl:
        return chat_msg(locale, "status.stage.model_training")
    tail = stage.split("_")[-1] if stage else ""
    if len(tail) <= 12 and tail:
        return tail.replace("_", " ")
    return chat_msg(locale, "status.stage.current_step")


def naturalize_predict_stage(stage: str, locale: Optional[str] = None) -> str:
    sl = (stage or "").lower()
    if not sl or sl == "failed":
        return chat_msg(locale, "status.pred.prediction_workflow")
    if "upload" in sl:
        return chat_msg(locale, "status.pred.read_input")
    if "mapping" in sl or "map" in sl:
        return chat_msg(locale, "status.pred.field_mapping")
    if "predict" in sl or sl == "predicting":
        return chat_msg(locale, "status.pred.generating")
    if "postprocess" in sl or "post" in sl:
        return chat_msg(locale, "status.pred.postprocess")
    if "model_loading" in sl or "loading" in sl:
        return chat_msg(locale, "status.pred.loading_model")
    if "completed" in sl:
        return chat_msg(locale, "status.pred.completed")
    return chat_msg(locale, "status.pred.processing_samples")


def build_train_semantics(task: Dict[str, Any], locale: Optional[str] = None) -> StatusSemantics:
    st = str(task.get("status") or "")
    stage = str(task.get("current_stage") or "")
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    rs = dict(rs) if isinstance(rs, dict) else {}
    wf = str(rs.get("train_workflow_phase") or "")
    stage_label = naturalize_train_stage(stage, locale)
    blocker: Optional[str] = None
    if st == "waiting_user":
        blocker = _train_wait_blocker_phrase(wf, stage, locale)
    err = task.get("error_message")
    err_hint = None
    if st == "failed":
        err_hint = humanize_error_hint(err if isinstance(err, str) else None, "train", locale)
    return StatusSemantics(
        object_type="train",
        status=st,
        stage_label=stage_label,
        blocker_label=blocker,
        error_hint=err_hint,
    )


def build_predict_semantics(task: Dict[str, Any], locale: Optional[str] = None) -> StatusSemantics:
    st = str(task.get("status") or "")
    stage = str(task.get("current_stage") or "")
    stage_label = naturalize_predict_stage(stage, locale)
    err = task.get("error_message")
    err_hint = None
    if st == "failed":
        err_hint = humanize_error_hint(err if isinstance(err, str) else None, "predict", locale)
    return StatusSemantics(
        object_type="predict",
        status=st,
        stage_label=stage_label,
        blocker_label=None,
        error_hint=err_hint,
    )


def format_train_status_reply(task: Dict[str, Any], locale: Optional[str] = None) -> str:
    """Training task status (1–3 sentences)."""
    sem = build_train_semantics(task, locale)
    st = sem.status
    stage = sem.stage_label or chat_msg(locale, "status.train_reply.current_step_fallback")
    rs = task.get("result_summary") if isinstance(task.get("result_summary"), dict) else {}
    wf = str(rs.get("train_workflow_phase") or "")

    if st == "completed":
        return format_train_completed_presentation(task, locale)

    if st == "canceled":
        return format_train_canceled_presentation(task, locale)

    if st == "failed":
        return format_train_failed_presentation(task, locale)

    if st == "waiting_user":
        item = sem.blocker_label or chat_msg(locale, "status.train_reply.waiting_item_fallback")
        title = _train_waiting_card_title(wf, str(task.get("current_stage") or ""), locale)
        return chat_msg(locale, "status.train_reply.waiting_user", title=title, item=item)

    if st == "queued":
        return chat_msg(locale, "status.train_reply.queued")

    if st == "running":
        return chat_msg(locale, "status.train_reply.running", stage=stage)

    return chat_msg(locale, "status.train_reply.running", stage=stage)


def train_running_duration_supplement(task: Dict[str, Any], locale: Optional[str] = None) -> str:

    stage = str(task.get("current_stage") or "").lower()
    if "train_phase2" in stage or "feature_search" in stage:
        return chat_msg(locale, "status.train_duration.phase2")
    if "train_phase3" in stage and "pending" not in stage:
        return chat_msg(locale, "status.train_duration.phase3_running")
    if "train_phase4" in stage or stage in ("model_training", "evaluation"):
        return chat_msg(locale, "status.train_duration.phase4")
    if "train_phase5" in stage or "publish" in stage:
        return chat_msg(locale, "status.train_duration.phase5")
    return chat_msg(locale, "status.train_duration.default")


def _predict_run_mode(
    task: Dict[str, Any], batch_hint: bool
) -> Literal["batch", "single", "unknown"]:
    ib = infer_predict_is_batch(task)
    if ib is True:
        return "batch"
    if ib is False:
        return "single"
    return "batch" if batch_hint else "unknown"


def format_predict_status_reply(
    task: Dict[str, Any], *, batch: bool = False, locale: Optional[str] = None
) -> str:

    sem = build_predict_semantics(task, locale)
    st = sem.status
    stage = sem.stage_label or chat_msg(locale, "status.predict_reply.stage_fallback")
    mode = _predict_run_mode(task, batch)

    if st == "completed":
        if mode == "unknown":
            return format_predict_completed_presentation_unknown_batch(task, locale)
        return format_predict_completed_presentation(task, batch_hint=batch, locale=locale)

    if st == "canceled":
        return format_predict_canceled_presentation(task, locale)

    if st == "failed":
        return format_predict_failed_presentation(task, locale)

    if st == "queued":
        if mode == "batch":
            return chat_msg(locale, "status.predict_reply.queued_batch")
        if mode == "single":
            return chat_msg(locale, "status.predict_reply.queued_single")
        return chat_msg(locale, "status.predict_reply.queued_generic")

    if st == "running":
        if mode == "batch":
            return chat_msg(locale, "status.predict_reply.running_batch")
        if mode == "single":
            return chat_msg(locale, "status.predict_reply.running_single", stage=stage)
        return chat_msg(locale, "status.predict_reply.running_generic", stage=stage)

    return chat_msg(locale, "status.predict_reply.running_generic", stage=stage)


def format_no_active_tasks_reply(locale: Optional[str] = None) -> str:
    return chat_msg(locale, "status.no_active_tasks")
