import { sanitizeUserFacingLine } from "./messageSanitizer";
import { englishUiLocalizedFallback } from "./localeTextGuard";

export type Translate = (key: string, values?: Record<string, unknown>) => string;

/** UI-only display labels for task status (do not change backend raw values). */
const STATUS_DISPLAY_FALLBACK_EN: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  waiting_user: "Waiting for input",
  completed: "Completed",
  succeeded: "Completed",
  success: "Completed",
  failed: "Failed",
  canceled: "Canceled",
  cancelled: "Canceled",
};

export function formatTaskStatusLabel(raw: string | null | undefined, t?: Translate): string {
  if (raw == null || raw === "") return "-";
  const key = String(raw).toLowerCase();
  if (!t) return STATUS_DISPLAY_FALLBACK_EN[key] ?? String(raw);
  if (key === "queued") return t("taskPresentation.status.queued");
  if (key === "running") return t("taskPresentation.status.running");
  if (key === "waiting_user") return t("taskPresentation.status.waitingUser");
  if (key === "completed" || key === "succeeded" || key === "success") return t("taskPresentation.status.completed");
  if (key === "failed") return t("taskPresentation.status.failed");
  if (key === "canceled" || key === "cancelled") return t("taskPresentation.status.canceled");
  return String(raw);
}

const JOB_TYPE_LABELS_FALLBACK_EN: Record<string, string> = {
  train_model: "Model training",
  predict_outcome: "Personalized prediction",
  generate_shap: "Model explanation",
  recommend_regimen: "Regimen recommendation",
  generate_report: "Report generation",
  publish_model: "Model release",
};

export function formatJobTypeLabel(jobType: string | null | undefined, t?: Translate): string {
  if (jobType == null || jobType === "") return "-";
  if (!t) return JOB_TYPE_LABELS_FALLBACK_EN[jobType] ?? String(jobType);
  if (jobType === "train_model") return t("taskPresentation.jobType.train");
  if (jobType === "predict_outcome") return t("taskPresentation.jobType.predict");
  if (jobType === "generate_shap") return t("taskPresentation.jobType.shap");
  if (jobType === "recommend_regimen") return t("taskPresentation.jobType.recommend");
  if (jobType === "generate_report") return t("taskPresentation.jobType.report");
  if (jobType === "publish_model") return t("taskPresentation.jobType.publish");
  return String(jobType);
}

export function isTrainingJobType(jobType: string | null | undefined): boolean {
  return jobType === "train_model";
}

/** Keep aligned with backend job_type values and historical aliases. */
const PREDICTION_JOB_TYPE_ALIASES = new Set([
  "predict_outcome",
  "prediction",
  "predict_single",
  "single_prediction",
  "batch_predict",
  "batch_prediction",
  "predict_batch",
  "inference",
]);

export function isPredictionJobType(jobType: string | null | undefined): boolean {
  const j = String(jobType || "").trim().toLowerCase();
  return PREDICTION_JOB_TYPE_ALIASES.has(j);
}

/** Used by the task list "Other" filter: job types that are already part of primary categories. */
export function isPrimaryTaskCategory(jobType: string | null | undefined): boolean {
  const j = String(jobType || "");
  return (
    isTrainingJobType(j) ||
    isPredictionJobType(j) ||
    isRecommendationJobType(j) ||
    isReportGenerationJob(j) ||
    isShapGenerationJob(j)
  );
}

/** Task list title: distinguish single vs batch prediction (from params/result_summary). */
export function formatPredictionTaskListTitle(
  task: Record<string, unknown> | null | undefined,
  t?: Translate,
): string {
  if (!task) return t ? t("taskPresentation.predictionTitle.single") : "Single prediction";
  const params = (task.params || {}) as Record<string, unknown>;
  const rs = (task.result_summary || {}) as Record<string, unknown>;
  const mode = String(params.prediction_mode || "").toLowerCase();
  const rsType = String(rs.prediction_type || "").toLowerCase();
  const isBatch = mode === "batch" || rsType === "batch";
  if (!t) return isBatch ? "Batch prediction" : "Single prediction";
  return isBatch ? t("taskPresentation.predictionTitle.batch") : t("taskPresentation.predictionTitle.single");
}

export function isRecommendationJobType(jobType: string | null | undefined): boolean {
  return jobType === "recommend_regimen";
}

export function isShapGenerationJob(jobType: string | null | undefined): boolean {
  return String(jobType || "").trim() === "generate_shap";
}

export function isReportGenerationJob(jobType: string | null | undefined): boolean {
  return String(jobType || "").trim() === "generate_report";
}

/** Whether this record represents a batch prediction (params/result_summary). */
export function isBatchPredictionTaskRecord(task: Record<string, unknown> | null | undefined): boolean {
  if (!task) return false;
  const params = (task.params || {}) as Record<string, unknown>;
  const rs = (task.result_summary || {}) as Record<string, unknown>;
  const mode = String(params.prediction_mode || "").toLowerCase();
  const rsType = String(rs.prediction_type || "").toLowerCase();
  return mode === "batch" || rsType === "batch";
}

const BATCH_PREDICTION_JOB_TYPES = new Set(["batch_predict", "batch_prediction", "predict_batch"]);
const SINGLE_PREDICTION_JOB_TYPES = new Set(["predict_single", "single_prediction"]);

/**
 * Classify a completed prediction task for compact Workbench “recently completed” row titles.
 * Prefer explicit job_type, then params/result_summary batch markers, then explicit single markers.
 * Falls back to single when job_type is a generic prediction alias without batch evidence (aligned with formatPredictionTaskListTitle).
 */
export function classifyPredictionRecentRowKind(
  task: Record<string, unknown> | null | undefined,
): "batch" | "single" | "unknown" {
  if (!task) return "unknown";
  const jt = String(task.job_type || "").trim().toLowerCase();
  if (BATCH_PREDICTION_JOB_TYPES.has(jt)) return "batch";
  if (SINGLE_PREDICTION_JOB_TYPES.has(jt)) return "single";
  if (isBatchPredictionTaskRecord(task)) return "batch";
  const params = (task.params || {}) as Record<string, unknown>;
  const rs = (task.result_summary || {}) as Record<string, unknown>;
  const mode = String(params.prediction_mode || "").toLowerCase();
  const rsType = String(rs.prediction_type || "").toLowerCase();
  if (mode === "single" || rsType === "single") return "single";
  if (!isPredictionJobType(jt)) return "unknown";
  return "single";
}

export type TrainingSummaryFields = {
  dataset_id?: string;
  clinical_task_id?: string;
  ml_task_type?: string;
  model_type?: string;
  target_column?: string;
  objective_metric?: string;
};

export function extractTrainingSummaryFromParams(
  params: Record<string, unknown> | null | undefined,
): TrainingSummaryFields | null {
  if (!params || typeof params !== "object") return null;
  const p = params as Record<string, unknown>;
  const out: TrainingSummaryFields = {};
  const set = (k: keyof TrainingSummaryFields, key: string) => {
    const v = p[key];
    if (v != null && String(v).trim() !== "") out[k] = String(v);
  };
  set("dataset_id", "dataset_id");
  set("clinical_task_id", "clinical_task_id");
  set("ml_task_type", "ml_task_type");
  set("model_type", "model_type");
  set("target_column", "target_column");
  set("objective_metric", "objective_metric");
  return Object.keys(out).length ? out : null;
}

/** Task list row helper: pick brief fields from params. */
export function listTrainingParamsRow(params: Record<string, unknown> | null | undefined): {
  dataset_id?: string;
  model_type?: string;
  target_column?: string;
} {
  const s = extractTrainingSummaryFromParams(params);
  if (!s) return {};
  return {
    dataset_id: s.dataset_id,
    model_type: s.model_type,
    target_column: s.target_column,
  };
}

export function summarizeFeatureSources(params: Record<string, unknown> | null | undefined, t?: Translate): string {
  if (!params || typeof params !== "object") return "";
  const p = params as Record<string, unknown>;
  const parts: string[] = [];
  const fs = p.feature_set;
  if (fs != null && String(fs).trim() !== "") parts.push(`feature_set: ${String(fs)}`);
  if (!t) {
    if (Array.isArray(p.final_features)) parts.push(`final_features: ${p.final_features.length} columns`);
    if (Array.isArray(p.selected_features)) parts.push(`selected_features: ${p.selected_features.length} columns`);
    return parts.join("; ");
  }
  if (Array.isArray(p.final_features)) parts.push(t("taskPresentation.featureSource.finalFeatures", { count: p.final_features.length }));
  if (Array.isArray(p.selected_features))
    parts.push(t("taskPresentation.featureSource.selectedFeatures", { count: p.selected_features.length }));
  return parts.join(t("taskPresentation.featureSource.separator"));
}

/** Task activity time: prefer completed/started time, otherwise created time. */
export function pickTaskActivityTime(task: Record<string, unknown>): {
  created?: string;
  updated?: string;
} {
  const created = task.created_at != null ? String(task.created_at) : undefined;
  const completed = task.completed_at != null ? String(task.completed_at) : undefined;
  const started = task.started_at != null ? String(task.started_at) : undefined;
  const updated = completed || started || undefined;
  return { created, updated };
}

/** Readable failure/cancellation reason for display. */
export function getReadableTaskFailureReason(task: Record<string, unknown>, t?: Translate): string | null {
  const status = String(task.status || "").toLowerCase();
  if (status !== "failed" && status !== "canceled" && status !== "cancelled") return null;
  const em = task.error_message;
  if (em != null && String(em).trim()) {
    const sanitized = sanitizeUserFacingLine(String(em), t) || String(em);
    return englishUiLocalizedFallback(sanitized, t, "chat.statusMessages.layers.backendTaskMessageUiMismatch");
  }
  const msg = task.message;
  if (msg != null && String(msg).trim()) {
    const sanitized = sanitizeUserFacingLine(String(msg), t) || String(msg);
    return englishUiLocalizedFallback(sanitized, t, "chat.statusMessages.layers.backendTaskMessageUiMismatch");
  }
  if (status !== "failed") return null;
  if (!t) return "Failed. No detailed reason was returned by the backend.";
  return t("taskPresentation.failureFallback.noBackendReason");
}

/** Try to pick model_id from result_summary/params. */
export function pickModelIdFromTask(task: Record<string, unknown>): string | undefined {
  const params = (task.params as Record<string, unknown> | undefined) || {};
  const po = params.publish_overrides as Record<string, unknown> | undefined;
  if (po?.model_id != null && String(po.model_id).trim()) return String(po.model_id);
  const rs = task.result_summary as Record<string, unknown> | undefined;
  if (rs?.model_id != null && String(rs.model_id).trim()) return String(rs.model_id);
  if (params.model_id != null && String(params.model_id).trim()) return String(params.model_id);
  return undefined;
}
