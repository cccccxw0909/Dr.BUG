"""Locale-aware API user-visible messages (HTTP error/success copy)."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    # --- prediction ---
    "api.prediction.invalid_input": (
        "提交内容校验未通过，请检查表单或上传文件后重试。",
        "Validation failed; check the form or file and retry.",
    ),
    "api.prediction.model_task_mismatch": (
        "所选模型与任务不匹配或不可用，请更换模型后重试。",
        "Model/task mismatch or model unavailable; select a different model.",
    ),
    "api.prediction.execution_failed": (
        "预测执行失败，请稍后重试或联系管理员。",
        "Prediction failed; retry later or contact an administrator.",
    ),
    "api.prediction.history_not_found": (
        "未找到预测历史记录（record_id={record_id}）。",
        "Prediction history record not found (record_id={record_id}).",
    ),
    # --- tasks ---
    "api.tasks.not_found": (
        "未找到任务（job_id={job_id}）。",
        "Task not found (job_id={job_id}).",
    ),
    "api.tasks.artifact_not_found": (
        "未找到产物文件。",
        "Artifact not found.",
    ),
    "api.tasks.workflow_rejected": (
        "工作流更新被拒绝。请核对当前任务状态与必填项后重试。",
        "Workflow update was rejected. Review the current task state and required fields, then retry.",
    ),
    "api.tasks.delete_not_allowed": (
        "job_id={job_id} 当前为 {status}；请先取消任务再删除。",
        "job_id={job_id} is {status}; cancel the task before deleting.",
    ),
    "api.tasks.deleted": (
        "任务已删除。",
        "Task deleted.",
    ),
    "api.tasks.cancel_not_allowed": (
        "当前状态下无法取消该任务。",
        "The task cannot be canceled in its current status.",
    ),
    "api.tasks.cancel_succeeded": (
        "任务 {job_id} 已取消。",
        "Task {job_id} was canceled.",
    ),
    # --- recommendation: service error codes ---
    "api.recommendation.rec_job_mode_invalid": (
        "mode 必须为 survival_only。",
        "mode must be survival_only.",
    ),
    "api.recommendation.rec_job_model_id_required": (
        "必须提供 model_id。",
        "model_id is required.",
    ),
    "api.recommendation.rec_job_patient_features_empty": (
        "patient_features 不能为空。",
        "patient_features cannot be empty.",
    ),
    "api.recommendation.rec_model_id_required": (
        "必须提供 model_id。",
        "model_id is required.",
    ),
    "api.recommendation.rec_model_not_found": (
        "未找到模型或模型不可用。",
        "Model not found or unavailable.",
    ),
    "api.recommendation.rec_model_schema_unavailable": (
        "该模型没有已注册的预测 schema。",
        "No registered prediction schema for this model.",
    ),
    "api.recommendation.rec_model_survival_incompatible": (
        "该模型与仅生存结局的用药推荐流程不兼容。",
        "Model is not compatible with survival-only regimen recommendation.",
    ),
    "api.recommendation.rec_treatment_field_not_numeric": (
        "某个用药剂量字段不是数值，请检查输入。",
        "A treatment dosing field is not numeric; check numeric inputs.",
    ),
    "api.recommendation.rec_regimen_ids_not_found_or_disabled": (
        "部分 regimen_id 不存在或未启用。",
        "One or more regimen_id values are missing or not enabled.",
    ),
    "api.recommendation.rec_no_enabled_regimen_candidates": (
        "没有可用的已启用候选方案。",
        "No enabled regimen candidates are available.",
    ),
    "api.recommendation.rec_model_output_missing_probability": (
        "模型输出未包含可用的概率值。",
        "Model output did not include a usable probability.",
    ),
    "api.recommendation.rec_probability_out_of_range": (
        "模型输出的概率不在 [0,1] 范围内。",
        "Model probability output is outside [0,1].",
    ),
    "api.recommendation.rec_unknown_score_direction": (
        "无法确定该模型的分数方向语义。",
        "Unknown score direction for this model.",
    ),
    "api.recommendation.rec_patient_features_empty": (
        "patient_features 不能为空。",
        "patient_features cannot be empty.",
    ),
    "api.recommendation.rec_top_k_invalid": (
        "top_k 必须为正整数。",
        "top_k must be a positive integer.",
    ),
    "api.recommendation.rec_feature_order_missing": (
        "模型 schema 缺少规范 feature_order。",
        "Model schema is missing canonical feature_order.",
    ),
    "api.recommendation.generic_processing_failed": (
        "无法处理推荐请求；请检查模型、患者字段与方案配置后重试。",
        (
            "Recommendation request could not be processed; check the model, patient fields, "
            "and regimens, then retry."
        ),
    ),
    "api.recommendation.regimen_name_required": (
        "regimen_name 不能为空。",
        "regimen_name cannot be empty.",
    ),
    "api.recommendation.regimen_invalid_default": (
        "方案输入无效。",
        "Invalid regimen input.",
    ),
    "api.recommendation.model_unavailable_or_no_schema": (
        "该模型不可用或未注册预测 schema。",
        "This model is unavailable or has no registered prediction schema.",
    ),
    "api.recommendation.model_missing_feature_order": (
        "该模型缺少规范的 feature_order。",
        "The model is missing a canonical feature_order.",
    ),
    "api.recommendation.patient_features_too_few": (
        "已填写的患者特征过少；请先补全更多必填项再运行对比。",
        "Too few patient features are complete; finish more required fields before running comparison.",
    ),
    "api.recommendation.survival_semantics_unknown": (
        "无法确定生存概率语义；请补充明确的标签上下文（例如 clinical_task_id、task_name、target_outcome 或 label_mapping）后重试。",
        (
            "Cannot determine survival probability semantics; add explicit label context "
            "(for example clinical_task_id, task_name, target_outcome, or label_mapping), then retry."
        ),
    ),
    "api.recommendation.clinical_task_semantics_conflict": (
        "模型临床任务语义冲突：同时存在生存与死亡相关提示。",
        "Model clinical-task semantics conflict: both survival- and mortality-related hints are present.",
    ),
    "api.recommendation.regimen_not_found": (
        "未找到方案（regimen_id={regimen_id}）。",
        "Regimen not found (regimen_id={regimen_id}).",
    ),
    "api.recommendation.regimen_deleted": (
        "方案已删除。",
        "Regimen deleted.",
    ),
}

_REC_SERVICE_CODE_TO_KEY: Dict[str, str] = {
    "REC_JOB_MODE_INVALID": "api.recommendation.rec_job_mode_invalid",
    "REC_JOB_MODEL_ID_REQUIRED": "api.recommendation.rec_job_model_id_required",
    "REC_JOB_PATIENT_FEATURES_EMPTY": "api.recommendation.rec_job_patient_features_empty",
    "REC_MODEL_ID_REQUIRED": "api.recommendation.rec_model_id_required",
    "REC_MODEL_NOT_FOUND": "api.recommendation.rec_model_not_found",
    "REC_MODEL_SCHEMA_UNAVAILABLE": "api.recommendation.rec_model_schema_unavailable",
    "REC_MODEL_SURVIVAL_INCOMPATIBLE": "api.recommendation.rec_model_survival_incompatible",
    "REC_TREATMENT_FIELD_NOT_NUMERIC": "api.recommendation.rec_treatment_field_not_numeric",
    "REC_REGIMEN_IDS_NOT_FOUND_OR_DISABLED": "api.recommendation.rec_regimen_ids_not_found_or_disabled",
    "REC_NO_ENABLED_REGIMEN_CANDIDATES": "api.recommendation.rec_no_enabled_regimen_candidates",
    "REC_MODEL_OUTPUT_MISSING_PROBABILITY": "api.recommendation.rec_model_output_missing_probability",
    "REC_PROBABILITY_OUT_OF_RANGE": "api.recommendation.rec_probability_out_of_range",
    "REC_UNKNOWN_SCORE_DIRECTION": "api.recommendation.rec_unknown_score_direction",
    "REC_PATIENT_FEATURES_EMPTY": "api.recommendation.rec_patient_features_empty",
    "REC_TOP_K_INVALID": "api.recommendation.rec_top_k_invalid",
    "REC_FEATURE_ORDER_MISSING": "api.recommendation.rec_feature_order_missing",
}


def recommendation_service_message_key(code: str) -> str:
    """Map RecommendationServiceError.code to a catalog message key."""
    return _REC_SERVICE_CODE_TO_KEY.get(code, "api.recommendation.generic_processing_failed")
