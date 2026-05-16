import type { PredictionSingleResponse, TaskDetailData, TaskResultCardData, TaskStatusData } from "../types";
import { clinicalTaskIdDisplayLabel, modelTypeDisplayLabel } from "../config/trainingSchemas";
import type { Translate } from "./messageSanitizer";
import { sanitizeUserFacingLine } from "./messageSanitizer";
import { englishUiLocalizedFallback } from "./localeTextGuard";
import { clinicalizeExplanationFeatureNames } from "./featureDisplayName";
import { trainingFeaturePrimaryLabel, trainingMetricLabel } from "./trainingWorkflowPresentation";
import { isBatchPredictionTaskRecord, isReportGenerationJob, isShapGenerationJob } from "./taskPresentation";
import { pickFinalModelShapBeeswarmFromArtifacts } from "./trainingShapArtifacts";

const TRAINING_RECEIPT_FEATURE_PREVIEW_MAX = 8;

function escapeHtmlUserText(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeMetricKeyMap(src: unknown): Record<string, unknown> {
  if (!src || typeof src !== "object") return {};
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(src as Record<string, unknown>)) {
    if (v === undefined || v === null) continue;
    out[String(k).toLowerCase().replace(/-/g, "_")] = v;
  }
  return out;
}

function primaryMetricLookupKeys(primaryNormalized: string): string[] {
  const pk = primaryNormalized;
  if (pk === "f1" || pk === "f1_score") return ["f1", "f1_score"];
  if (pk === "pcc" || pk === "pearson") return ["pcc", "pearson"];
  return [pk];
}

function pickPrimaryMetricRawValue(
  primaryRaw: string,
  finalMetrics: Record<string, unknown>,
  keyMetrics: Record<string, unknown>,
): unknown {
  const pk = primaryRaw.toLowerCase().trim().replace(/-/g, "_");
  if (!pk) return undefined;
  const keys = primaryMetricLookupKeys(pk);
  for (const bucket of [finalMetrics, keyMetrics]) {
    for (const key of keys) {
      const v = bucket[key];
      if (v !== undefined && v !== null && String(v).trim() !== "") return v;
    }
  }
  return undefined;
}

function formatReceiptMetricValue(v: unknown): string {
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : String(v);
  const n = Number(v);
  if (!Number.isNaN(n) && v !== "" && v !== null && v !== undefined && /^-?\d/.test(String(v).trim())) {
    return n.toFixed(3);
  }
  return String(v ?? "");
}

function isBlankOrSentinel(s: string): boolean {
  const x = s.trim().toLowerCase();
  if (!x) return true;
  return x === "none" || x === "null" || x === "undefined";
}

function firstNonEmptyScalar(...candidates: unknown[]): string {
  for (const c of candidates) {
    if (c === undefined || c === null) continue;
    const s = String(c).trim();
    if (!isBlankOrSentinel(s)) return s;
  }
  return "";
}

function normalizeClinicalTaskToken(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/-/g, "_")
    .replace(/\s+/g, "_");
}

function resolveReceiptClinicalTaskReadableName(clinicalTaskId: unknown, t?: Translate): string {
  const raw = String(clinicalTaskId ?? "").trim();
  if (!raw || isBlankOrSentinel(raw)) return "";
  const norm = normalizeClinicalTaskToken(raw);
  if (
    norm === "clinical_efficacy" ||
    norm === "clinical_outcome" ||
    norm === "clinical_outcomes" ||
    norm === "clinical_efficacy_prediction"
  ) {
    return loc(t, "task.resultCard.trainingReceipt.clinicalEfficacyTaskName", {}, "clinical efficacy prediction");
  }
  const fromSchema = clinicalTaskIdDisplayLabel(raw, t);
  if (fromSchema && !isBlankOrSentinel(fromSchema)) return fromSchema;
  return "";
}

function resolveTrainingReceiptTaskName(
  summary: Record<string, unknown>,
  params: Record<string, unknown>,
  mlTaskTypeLabel: string,
  t?: Translate,
): string {
  const fromLabels = firstNonEmptyScalar(
    summary.training_task_display_name,
    summary.task_display_name,
    summary.clinical_task_label,
    params.training_task_display_name,
    params.task_display_name,
    params.clinical_task_label,
  );
  if (fromLabels) return fromLabels;

  const clinicalReadable = resolveReceiptClinicalTaskReadableName(
    summary.clinical_task_id ?? params.clinical_task_id,
    t,
  );
  if (clinicalReadable) return clinicalReadable;

  if (mlTaskTypeLabel && !isBlankOrSentinel(mlTaskTypeLabel)) return mlTaskTypeLabel;

  return loc(t, "task.resultCard.trainingReceipt.taskNameFallback", {}, "this training task");
}

function resolveReceiptDatasetLabel(summary: Record<string, unknown>, params: Record<string, unknown>, t?: Translate): string {
  const d = firstNonEmptyScalar(
    summary.dataset_display_name,
    summary.dataset_name,
    params.dataset_display_name,
    params.dataset_name,
    summary.upload_filename,
    summary.uploaded_filename,
    summary.source_filename,
    params.upload_filename,
    params.uploaded_filename,
    params.original_filename,
    params.file_name,
    params.filename,
  );
  if (d) return d;
  return loc(t, "task.resultCard.trainingReceipt.datasetFallback", {}, "the selected dataset");
}

function resolveReceiptAlgorithmLabel(
  summary: Record<string, unknown>,
  params: Record<string, unknown>,
  t?: Translate,
): string {
  const direct = firstNonEmptyScalar(summary.trained_model_programmer_name, summary.programmer_model);
  if (direct) return direct;
  const mt = params.model_type ?? summary.model_type;
  const mapped = modelTypeDisplayLabel(mt, t);
  if (mapped && !isBlankOrSentinel(mapped)) return mapped;
  const rawMt = String(mt ?? "").trim();
  if (rawMt && !isBlankOrSentinel(rawMt)) return rawMt;
  return loc(t, "task.resultCard.trainingReceipt.algorithmFallback", {}, "the selected model");
}

/** Display label for the final trained model on training receipts (matches narrative body). */
export function trainingReceiptFinalModelDisplayName(
  summary: Record<string, unknown>,
  params: Record<string, unknown> | undefined,
  t?: Translate,
): string {
  return resolveReceiptAlgorithmLabel(summary, params ?? {}, t);
}

function trainingHasCandidateCvSource(
  summary: Record<string, unknown>,
  artifacts: Record<string, string> | undefined,
): boolean {
  const rows = summary.all_model_metrics_rows;
  if (Array.isArray(rows) && rows.length > 0) return true;
  if (!artifacts) return false;
  return Object.keys(artifacts).some((k) => {
    const b = k.replace(/\\/g, "/").toLowerCase();
    return b.includes("all_model_metrics") && b.endsWith(".json");
  });
}

function receiptSecondaryMetricLabel(metricKey: string, t?: Translate): string {
  if (metricKey === "f1") return loc(t, "task.resultCard.trainingReceipt.metricNameF1", {}, "F1-score");
  return trainingMetricLabel(metricKey);
}

function metricSlotIsPrimary(metricKey: string, primaryNorm: string): boolean {
  if (!primaryNorm) return false;
  if (primaryNorm === metricKey) return true;
  if (metricKey === "f1" && (primaryNorm === "f1" || primaryNorm === "f1_score")) return true;
  if (metricKey === "pcc" && (primaryNorm === "pcc" || primaryNorm === "pearson")) return true;
  if (metricKey === "auroc" && (primaryNorm === "auroc" || primaryNorm === "auc" || primaryNorm === "roc_auc")) return true;
  if (
    metricKey === "auprc" &&
    (primaryNorm === "auprc" || primaryNorm === "pr_auc" || primaryNorm === "average_precision")
  )
    return true;
  return false;
}

function hasSecondaryMetricsForReceipt(
  regression: boolean,
  primaryMetricRaw: string,
  m: Record<string, string | number>,
): boolean {
  const primaryNorm = primaryMetricRaw.toLowerCase().trim().replace(/-/g, "_");
  const order = regression
    ? (["mse", "pcc"] as const)
    : (["accuracy", "precision", "recall", "f1", "auroc", "auprc"] as const);
  for (const k of order) {
    if (metricSlotIsPrimary(k, primaryNorm)) continue;
    const raw =
      k === "f1"
        ? m.f1 ?? m.f1_score
        : k === "pcc"
          ? m.pcc ?? m.pearson
          : m[k];
    if (raw !== undefined && raw !== null && String(raw).trim() !== "") return true;
  }
  return false;
}

function buildOtherMetricListForReceipt(
  regression: boolean,
  primaryMetricRaw: string,
  m: Record<string, string | number>,
  t?: Translate,
): string {
  const primaryNorm = primaryMetricRaw.toLowerCase().trim().replace(/-/g, "_");
  const order = regression
    ? (["mse", "pcc"] as const)
    : (["accuracy", "precision", "recall", "f1", "auroc", "auprc"] as const);
  const parts: string[] = [];
  for (const k of order) {
    if (metricSlotIsPrimary(k, primaryNorm)) continue;
    const raw =
      k === "f1"
        ? m.f1 ?? m.f1_score
        : k === "pcc"
          ? m.pcc ?? m.pearson
          : m[k];
    if (raw === undefined || raw === null || String(raw).trim() === "") continue;
    parts.push(`${receiptSecondaryMetricLabel(k, t)} ${formatReceiptMetricValue(raw)}`);
  }
  if (parts.length === 0) {
    return loc(t, "task.resultCard.trainingReceipt.otherMetricsUnavailable", {}, "Other final metrics were not available");
  }
  return parts.join(loc(t, "task.resultCard.trainingReceipt.metricListJoiner", {}, "; "));
}

export type AnnounceState = {
  lastStatus?: string;
  lastStage?: string;
  isTerminalAnnounced?: boolean;
};

function loc(t: Translate | undefined, key: string, values?: Record<string, unknown>, en?: string): string {
  if (t) return values ? String(t(key, values)) : String(t(key));
  return en ?? "";
}

function naDisplay(t?: Translate): string {
  return loc(t, "common.na", {}, "—");
}

/** Route by job_type; prediction jobs must not reuse training-in-progress wording. */
export function getJobProgressMessage(task: TaskStatusData["task"], t?: Translate): string | null {
  const jt = String((task as { job_type?: string }).job_type || "");
  if (jt === "predict_outcome") {
    const status = String(task.status || "");
    const trec = task as unknown as Record<string, unknown>;
    const isBatch = isBatchPredictionTaskRecord(trec);
    if (status === "queued") {
      return isBatch
        ? loc(t, "chat.statusMessages.predict.batchQueued", {}, "Batch prediction submitted; your table is queued for processing.")
        : loc(t, "chat.statusMessages.predict.singleQueued", {}, "Single-patient prediction submitted and queued.");
    }
    if (status === "running") {
      return isBatch
        ? loc(t, "chat.statusMessages.predict.batchRunning", {}, "Computing predictions row-by-row for the uploaded table.")
        : loc(t, "chat.statusMessages.predict.singleRunning", {}, "Computing the single-patient prediction.");
    }
    if (status === "waiting_user") return null;
    if (status === "completed" || status === "failed" || status === "canceled" || status === "cancelled") return null;
    return null;
  }
  if (jt === "recommend_regimen") {
    const status = String(task.status || "");
    if (status === "queued") return loc(t, "chat.statusMessages.recommend.queued", {}, "Regimen recommendation submitted; queued by the system.");
    if (status === "running") return loc(t, "chat.statusMessages.recommend.running", {}, "Computing candidate regimens and survival probabilities.");
    if (status === "waiting_user") return null;
    if (status === "completed" || status === "failed" || status === "canceled" || status === "cancelled") return null;
    return null;
  }
  if (isShapGenerationJob(jt)) {
    const status = String(task.status || "");
    if (status === "queued") return loc(t, "chat.statusMessages.shap.queued", {}, "Explanation job submitted and queued.");
    if (status === "running") return loc(t, "chat.statusMessages.shap.running", {}, "Generating explanation figures and related outputs.");
    if (status === "waiting_user") return null;
    if (status === "completed" || status === "failed" || status === "canceled" || status === "cancelled") return null;
    return null;
  }
  if (isReportGenerationJob(jt)) {
    const status = String(task.status || "");
    if (status === "queued") return loc(t, "chat.statusMessages.report.queued", {}, "Report job submitted and queued.");
    if (status === "running") return loc(t, "chat.statusMessages.report.running", {}, "Generating report content or attachments.");
    if (status === "waiting_user") return null;
    if (status === "completed" || status === "failed" || status === "canceled" || status === "cancelled") return null;
    return null;
  }
  if (jt && jt !== "train_model") {
    const status = String(task.status || "");
    if (status === "queued") return loc(t, "chat.statusMessages.genericJob.queued", {}, "Task submitted and queued.");
    if (status === "running") return loc(t, "chat.statusMessages.genericJob.running", {}, "Task is processing.");
    if (status === "waiting_user") return null;
    if (status === "completed" || status === "failed" || status === "canceled" || status === "cancelled") return null;
    return null;
  }
  return getTrainingProgressMessage(task, t);
}

export function getTrainingProgressMessage(task: TaskStatusData["task"], t?: Translate): string | null {
  const status = String(task.status || "");
  const stage = String(task.current_stage || "");

  if (status === "queued") {
    return loc(t, "chat.statusMessages.training.featureScreeningInProgress", {}, "Feature screening is in progress.");
  }
  if (status === "running" && stage === "dataset_validation")
    return loc(t, "chat.statusMessages.training.datasetValidation", {}, "Validating dataset and training parameters.");
  if (status === "running" && (stage.includes("train_phase2") || stage.includes("feature_search"))) {
    return loc(t, "chat.statusMessages.training.featureScreeningInProgress", {}, "Feature screening is in progress.");
  }
  if (status === "running" && stage.includes("train_phase3"))
    return loc(t, "chat.statusMessages.training.phase3Features", {}, "Preparing final features and training configuration in the background.");
  if (status === "running" && stage.includes("train_phase4"))
    return loc(t, "chat.statusMessages.training.phase4Training", {}, "Training the model and generating reports in the background.");
  if (status === "running" && stage.includes("train_phase5"))
    return loc(t, "chat.statusMessages.training.phase5Release", {}, "Processing release-related steps in the background.");
  if (status === "running" && stage === "model_training")
    return loc(t, "chat.statusMessages.training.modelTrainingStarting", {}, "Starting model training.");
  if (status === "running" && stage === "evaluation")
    return loc(t, "chat.statusMessages.training.evaluation", {}, "Summarizing training results.");
  if (status === "running") return loc(t, "chat.statusMessages.training.runningFallback", {}, "Training job in progress.");
  if (status === "waiting_user" && stage === "train_phase3_feature_confirm_pending") {
    return null;
  }
  if (status === "waiting_user" && (stage === "train_phase4_train_config_pending" || stage === "train_phase4_config_confirm_pending")) {
    return null;
  }
  if (status === "waiting_user" && (stage === "train_phase5_publish_pending" || stage === "train_phase5_publish_confirm_pending")) {
    return null;
  }
  if (status === "waiting_user") return null;
  if (status === "completed" || status === "failed" || status === "canceled" || status === "cancelled") return null;
  return null;
}

export function shouldAnnounceTransition(prev: AnnounceState, nextStatus: string, nextStage: string): boolean {
  return prev.lastStatus !== nextStatus || prev.lastStage !== nextStage;
}

export function buildCompletionSummary(detail: TaskDetailData, t?: Translate): string[] {
  const summary = (detail.task.result_summary || {}) as Record<string, unknown>;
  const lines: string[] = [];
  const headlineRaw = summary.headline
    ? String(summary.headline)
    : loc(t, "chat.statusMessages.completion.headlineDefault", {}, "Training finished.");
  let headlineLine = sanitizeUserFacingLine(headlineRaw, t) || headlineRaw;
  headlineLine = englishUiLocalizedFallback(headlineLine, t, "chat.statusMessages.completion.backendHeadlineUiMismatch");
  lines.push(headlineLine);

  const metrics = (summary.key_metrics || {}) as Record<string, unknown>;
  const metricEntries = Object.entries(metrics);
  if (metricEntries.length > 0) {
    lines.push(loc(t, "chat.statusMessages.completion.keyMetricsHeading", {}, "Key metrics this run:"));
    for (const [k, v] of metricEntries) {
      lines.push(
        loc(
          t,
          "chat.statusMessages.completion.metricBullet",
          { label: metricLabel(k), value: String(v) },
          `- ${metricLabel(k)}: ${String(v)}`,
        ),
      );
    }
  }

  lines.push(
    loc(
      t,
      "chat.statusMessages.completion.tailHint",
      {},
      "Use the task panel to review performance and outputs; released models are ready for prediction.",
    ),
  );
  return lines;
}

export function buildCompletionCard(detail: TaskDetailData, t?: Translate): TaskResultCardData {
  const summary = (detail.task.result_summary || {}) as Record<string, unknown>;
  const headlineRaw = summary.headline
    ? String(summary.headline)
    : loc(t, "chat.statusMessages.completion.cardTitleFallbackTrainingDone", {}, "Training complete");
  const metricsRaw = (summary.key_metrics || {}) as Record<string, unknown>;
  const metrics: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(metricsRaw)) {
    if (v === undefined || v === null) continue;
    metrics[String(k).toLowerCase().replace(/-/g, "_")] = v as string | number;
  }
  const fmMerge = summary.final_model_metrics;
  if (fmMerge && typeof fmMerge === "object") {
    for (const [k, v] of Object.entries(fmMerge as Record<string, unknown>)) {
      if (v === undefined || v === null) continue;
      const nk = String(k).toLowerCase().replace(/-/g, "_");
      if (metrics[nk] == null) metrics[nk] = v as string | number;
    }
  }
  if (metrics.f1 == null && metrics.f1_score != null) metrics.f1 = metrics.f1_score;
  if (metrics.pcc == null && metrics.pearson != null) metrics.pcc = metrics.pearson as number;
  const modelId = summary.model_id != null && String(summary.model_id).trim() ? String(summary.model_id).trim() : undefined;
  const released = Boolean(summary.model_registered) || Boolean(summary.is_published);
  const jobType = String(detail.task.job_type || "");
  const isTrain = jobType === "train_model";
  const trainRegisteredTrue = loc(
    t,
    "chat.statusMessages.completion.trainCompletedModelRegistered",
    {},
    "The model is published and registered. You can select it for single-patient or batch prediction and for regimen recommendation.",
  );
  const trainRegisteredFalse = loc(
    t,
    "chat.statusMessages.completion.trainCompletedModelNotRegistered",
    {},
    "Training finished without publishing this run to the registry. It will not appear in prediction or regimen-comparison model lists; you can still review reports and artifacts under Tasks.",
  );
  const trainRegistryUnknown = loc(
    t,
    "chat.statusMessages.completion.trainCompletedRegistryUnknown",
    {},
    "Training finished. Open Tasks for the authoritative summary, outputs, and publication status.",
  );
  const nextStepOtherReleased = loc(
    t,
    "chat.statusMessages.completion.nextStepReleased",
    {},
    "This model has been released and can be used for prediction. Review charts and metrics in Tasks when you are ready.",
  );
  const nextStepOtherNotReleased = loc(
    t,
    "chat.statusMessages.completion.nextStepNotReleased",
    {},
    "Training finished. Release the model when you want to run predictions; until then you can still review outputs in Tasks.",
  );
  const taskStatus = String(detail.task.status || "");
  const trainCompletionReceiptMode = isTrain && taskStatus === "completed";

  let nextStep: string | undefined;
  if (trainCompletionReceiptMode) {
    nextStep = undefined;
  } else if (isTrain) {
    const mr = summary.model_registered;
    if (mr === true) {
      nextStep = trainRegisteredTrue;
    } else if (mr === false) {
      nextStep = trainRegisteredFalse;
    } else {
      nextStep = trainRegistryUnknown;
    }
  } else if (released) {
    nextStep = nextStepOtherReleased;
  } else {
    nextStep = nextStepOtherNotReleased;
  }
  let titleLine = sanitizeUserFacingLine(headlineRaw, t) || headlineRaw;
  titleLine = englishUiLocalizedFallback(titleLine, t, "chat.statusMessages.completion.backendHeadlineUiMismatch");
  if (isTrain) {
    if (taskStatus === "completed") {
      const reg = summary.model_registered;
      const pub = Boolean(summary.is_published);
      if (reg === true || pub) {
        titleLine = loc(t, "chat.statusMessages.completion.modelReleasedCardTitle", {}, "Model released");
      } else if (reg === false && !pub) {
        titleLine = loc(
          t,
          "chat.statusMessages.completion.trainingCompletedNotReleasedCardTitle",
          {},
          "Training completed, model not released",
        );
      } else {
        titleLine = loc(t, "chat.statusMessages.completion.trainingDoneCardTitle", {}, "Training completed");
      }
    } else {
      titleLine = loc(t, "chat.statusMessages.completion.trainingDoneCardTitle", {}, "Training completed");
    }
  }

  let trainingCompletedPresentation: TaskResultCardData["trainingCompletedPresentation"];
  if (isTrain && taskStatus === "completed") {
    const params = (detail.task.params || {}) as Record<string, unknown>;
    const mlRaw = String(summary.ml_task_type || params.ml_task_type || "binary").toLowerCase();
    let mlLabel = loc(t, "task.resultCard.presentation.mlBinary", {}, "Binary classification");
    if (mlRaw === "multiclass") {
      mlLabel = loc(t, "task.resultCard.presentation.mlMulticlass", {}, "Multiclass classification");
    } else if (mlRaw === "regression") {
      mlLabel = loc(t, "task.resultCard.presentation.mlRegression", {}, "Regression");
    }

    const taskName = resolveTrainingReceiptTaskName(summary, params, mlLabel, t);
    const datasetLabel = resolveReceiptDatasetLabel(summary, params, t);
    const modelLabel = resolveReceiptAlgorithmLabel(summary, params, t);

    const fcRaw = summary.final_feature_count;
    let fc: number | "" = "";
    if (typeof fcRaw === "number" && Number.isFinite(fcRaw)) fc = fcRaw;
    else if (Array.isArray(summary.final_features_locked)) fc = summary.final_features_locked.length;
    else if (Array.isArray(summary.final_feature_preview)) fc = summary.final_feature_preview.length;

    const primaryMetricRaw = String(summary.primary_metric_requested || params.objective_metric || "").trim();
    const primaryMetricLabel = primaryMetricRaw ? trainingMetricLabel(primaryMetricRaw) : naDisplay(t);

    const lockedRaw = summary.final_features_locked;
    const lockedFeatures = Array.isArray(lockedRaw)
      ? lockedRaw.map((x) => String(x)).filter((s) => s.trim())
      : [];
    const previewRawList = summary.final_feature_preview;
    const previewFeatures = Array.isArray(previewRawList)
      ? previewRawList.map((x) => String(x)).filter((s) => s.trim())
      : [];
    const featureNamesForSection = lockedFeatures.length > 0 ? lockedFeatures : previewFeatures;

    let nFeaturesNum: number | null = null;
    if (typeof fcRaw === "number" && Number.isFinite(fcRaw)) nFeaturesNum = fcRaw;
    else if (lockedFeatures.length > 0) nFeaturesNum = lockedFeatures.length;
    else if (previewFeatures.length > 0) nFeaturesNum = previewFeatures.length;

    const fmNorm = normalizeMetricKeyMap(summary.final_model_metrics);
    const kmNorm = normalizeMetricKeyMap(summary.key_metrics);
    const primaryValRaw = pickPrimaryMetricRawValue(primaryMetricRaw, fmNorm, kmNorm);
    const primaryMetricValue =
      primaryValRaw !== undefined ? formatReceiptMetricValue(primaryValRaw) : naDisplay(t);

    const previewSlice = featureNamesForSection.slice(0, TRAINING_RECEIPT_FEATURE_PREVIEW_MAX);
    const featurePreviewParts = previewSlice.map((raw) =>
      clinicalizeExplanationFeatureNames(trainingFeaturePrimaryLabel(raw)),
    );
    let featurePreviewStr = featurePreviewParts.join(
      loc(t, "task.resultCard.trainingReceipt.featureJoiner", {}, ", "),
    );
    if (featureNamesForSection.length > TRAINING_RECEIPT_FEATURE_PREVIEW_MAX) {
      featurePreviewStr += loc(t, "task.resultCard.trainingReceipt.featureAmongOthersSuffix", {}, ", among others");
    }

    const mr = summary.model_registered;
    const algoForSentence = modelLabel;
    const nFeatDisplay = nFeaturesNum !== null ? String(nFeaturesNum) : naDisplay(t);
    const featureListDisplay = featurePreviewStr.trim() ? featurePreviewStr : naDisplay(t);
    const otherMetricList = buildOtherMetricListForReceipt(mlRaw === "regression", primaryMetricRaw, metrics, t);
    const hasOthers = hasSecondaryMetricsForReceipt(mlRaw === "regression", primaryMetricRaw, metrics);
    const matchingShapArtifact = pickFinalModelShapBeeswarmFromArtifacts(
      detail.artifacts as Record<string, string> | undefined,
      modelLabel,
    );
    const hasShapBeeswarm = matchingShapArtifact != null;
    const showCandidateModelComparison = trainingHasCandidateCvSource(summary, detail.artifacts as Record<string, string> | undefined);

    const receiptVarsBase = {
      algorithm: algoForSentence,
      task_name: taskName,
      dataset_name: datasetLabel,
      feature_count: nFeatDisplay,
      feature_list: featureListDisplay,
    };

    let receiptP1: string;
    if (mr === true) {
      receiptP1 = loc(
        t,
        "task.resultCard.trainingReceipt.bodyP1Published",
        receiptVarsBase,
        `Training was completed successfully. Using the dataset ${datasetLabel}, Dr.BUG trained and published a ${algoForSentence} model for ${taskName}. During feature selection, a compact ${nFeatDisplay}-feature set was used for final modelling, consisting of ${featureListDisplay}.`,
      );
    } else if (mr === false) {
      receiptP1 = loc(
        t,
        "task.resultCard.trainingReceipt.bodyP1NotPublished",
        receiptVarsBase,
        `Training was completed successfully. Using the dataset ${datasetLabel}, Dr.BUG trained and saved without publishing a ${algoForSentence} model for ${taskName}. During feature selection, a compact ${nFeatDisplay}-feature set was used for final modelling, consisting of ${featureListDisplay}.`,
      );
    } else {
      receiptP1 = loc(
        t,
        "task.resultCard.trainingReceipt.bodyP1Unknown",
        receiptVarsBase,
        `Training was completed successfully. Using the dataset ${datasetLabel}, Dr.BUG finished training a ${algoForSentence} model for ${taskName}. During feature selection, a compact ${nFeatDisplay}-feature set was used for final modelling, consisting of ${featureListDisplay}.`,
      );
    }

    const p2PrimaryBefore = loc(
      t,
      "task.resultCard.trainingReceipt.bodyP2PrimaryEvalBefore",
      {},
      "In the final evaluation, ",
    );
    const p2PrimaryBetween = loc(
      t,
      "task.resultCard.trainingReceipt.bodyP2PrimaryEvalBetween",
      {},
      " was the primary metric and reached ",
    );
    const p2PrimaryAfter = loc(t, "task.resultCard.trainingReceipt.bodyP2PrimaryEvalAfter", {}, ".");
    const p2PrimaryHtml =
      escapeHtmlUserText(p2PrimaryBefore) +
      `<strong>${escapeHtmlUserText(primaryMetricLabel)}</strong>` +
      escapeHtmlUserText(p2PrimaryBetween) +
      `<strong>${escapeHtmlUserText(primaryMetricValue)}</strong>` +
      escapeHtmlUserText(p2PrimaryAfter);

    const p2Other = hasOthers
      ? loc(
          t,
          "task.resultCard.trainingReceipt.bodyP2OtherAchieved",
          { other_metric_list: otherMetricList },
          ` The model also achieved ${otherMetricList}.`,
        )
      : loc(
          t,
          "task.resultCard.trainingReceipt.bodyP2OtherNone",
          {},
          " No additional final metrics were reported beyond the primary metric.",
        );

    const shapClause = hasShapBeeswarm
      ? loc(
          t,
          "task.resultCard.trainingReceipt.shapAttributionSentence",
          {},
          "The SHAP beeswarm plot below provides a model-based view of how the selected features contributed to the prediction output; it should not be interpreted as causal evidence.",
        ).trim()
      : "";

    let tailClause: string;
    if (mr === true) {
      tailClause = loc(
        t,
        "task.resultCard.trainingReceipt.bodyP2TailPublished",
        {},
        "The published model is now available for downstream prediction and regimen recommendation.",
      ).trim();
    } else if (mr === false) {
      tailClause = loc(
        t,
        "task.resultCard.trainingReceipt.bodyP2TailNotPublished",
        {},
        "The trained model was saved as training output and will not appear in the prediction model list.",
      ).trim();
    } else {
      tailClause = loc(
        t,
        "task.resultCard.trainingReceipt.bodyP2TailUnknown",
        {},
        "Open Tasks to confirm publication status and review saved outputs.",
      ).trim();
    }

    const evalPlain = `${p2PrimaryBefore}${primaryMetricLabel}${p2PrimaryBetween}${primaryMetricValue}${p2PrimaryAfter}${p2Other}`.trim();
    const receiptParagraphs: string[] = [receiptP1, evalPlain];
    if (shapClause) receiptParagraphs.push(shapClause);
    receiptParagraphs.push(tailClause);

    const receiptParagraphsHtml: string[] = [
      escapeHtmlUserText(receiptP1),
      p2PrimaryHtml + escapeHtmlUserText(p2Other),
    ];
    if (shapClause) receiptParagraphsHtml.push(escapeHtmlUserText(shapClause));
    receiptParagraphsHtml.push(escapeHtmlUserText(tailClause));

    trainingCompletedPresentation = {
      receiptParagraphs,
      receiptParagraphsHtml,
      showCandidateModelComparison,
      summaryRows: [],
      featureSection: undefined,
    };
  }

  return {
    variant: "completed",
    status: String(detail.task.status || "completed"),
    title: titleLine || (t ? t("pages.history.warnings.completionCardTitleFallback") : "Training complete"),
    metrics: Object.keys(metrics).length > 0 ? metrics : undefined,
    nextStep,
    jobId: String(detail.task.id || ""),
    jobType,
    modelId,
    modelPublished: Boolean(modelId) && released,
    artifacts: detail.artifacts || {},
    resultSummary: summary,
    trainingCompletedPresentation,
  };
}

export function buildFailureCard(task: TaskStatusData["task"], t?: Translate): TaskResultCardData {
  const reasonRaw = String(task.error_message || task.message || "");
  const reason = sanitizeFailureReason(reasonRaw, t);
  return {
    variant: "failed",
    status: String(task.status || "failed"),
    title: loc(t, "chat.statusMessages.failure.cardTitle", {}, "Training did not complete"),
    errorReason: reason
      ? loc(t, "chat.statusMessages.failure.errorReasonLine", { reason }, `Details: ${reason}`)
      : undefined,
    nextStep: loc(
      t,
      "chat.statusMessages.failure.nextStepCard",
      {},
      "Open Tasks and review the summary; expand Technical details if you need diagnostics.",
    ),
    jobId: String(task.id || ""),
    jobType: String(task.job_type || ""),
  };
}

/** Map a completed predict_outcome async task into the single-patient prediction result-card structure. */
export function taskDetailToPredictionSingleResponse(detail: TaskDetailData, t?: Translate): PredictionSingleResponse {
  const task = detail.task;
  const rs = (task.result_summary || {}) as Record<string, unknown>;
  const params = (task.params || {}) as Record<string, unknown>;
  const mid = String(params.model_id || "").trim() || naDisplay(t);
  const rawLabel = rs.predicted_label != null ? String(rs.predicted_label).trim() : "";
  let pRaw = rs.probability != null ? Number(rs.probability) : rs.predicted_probability != null ? Number(rs.predicted_probability) : NaN;
  if (Number.isNaN(pRaw)) pRaw = NaN;
  let p01 = Number.isNaN(pRaw) ? null : pRaw > 1 ? pRaw / 100 : pRaw;

  const low = rawLabel.toLowerCase();
  let labelDisplay = rawLabel;
  if (low.includes("death") || low.includes("mortality"))
    labelDisplay = loc(t, "chat.statusMessages.predictionOutcome.labelMortality28d", {}, "28-day mortality");
  else if (low.includes("surviv"))
    labelDisplay = loc(t, "chat.statusMessages.predictionOutcome.labelSurvival28d", {}, "28-day survival");
  else if (low.includes("improv"))
    labelDisplay = loc(t, "chat.statusMessages.predictionOutcome.labelTreatmentImproved", {}, "Treatment improved");
  else if (low.includes("fail"))
    labelDisplay = loc(t, "chat.statusMessages.predictionOutcome.labelTreatmentFailed", {}, "Treatment failed");

  const pct = p01 != null && !Number.isNaN(p01) ? (p01 * 100).toFixed(1) : "";
  const pctToken = pct ? `${pct}%` : naDisplay(t);
  const probLine = loc(t, "chat.statusMessages.predictionOutcome.probabilityLine", { pct: pctToken }, `Predicted probability: ${pctToken}`);
  const labelForLine = labelDisplay || naDisplay(t);
  const labelLine = loc(t, "chat.statusMessages.predictionOutcome.labelLine", { label: labelForLine }, `Predicted label: ${labelForLine}`);

  return {
    ok: true,
    model_id: mid,
    display_name: mid,
    task_name: loc(t, "chat.statusMessages.predictionOutcome.taskNameSingle", {}, "Single-patient prediction job"),
    prediction_type: "classification",
    predicted_label: rawLabel || null,
    predicted_probability: p01,
    label_display: labelDisplay || rawLabel || naDisplay(t),
    outcome_display: labelDisplay || rawLabel || naDisplay(t),
    probability_display_line: probLine,
    label_display_line: labelLine,
    feature_values_used: {},
    warnings: [],
    timestamp: String(task.completed_at || ""),
    explanation: null,
    ui_headline: loc(t, "chat.statusMessages.predictionOutcome.uiHeadline", {}, "Prediction complete"),
    ui_subheadline: loc(t, "chat.statusMessages.predictionOutcome.uiSubheadline", {}, "Single-patient prediction result"),
  };
}

function sanitizeFailureReason(reason: string, t?: Translate): string {
  const txt = String(reason || "");
  if (!txt) return "";
  // StateMachine / legacy CJK diagnostics are normalized in `sanitizeUserFacingLine` when present.
  return sanitizeUserFacingLine(txt, t) || txt;
}

export function buildFailureSummary(task: TaskStatusData["task"], t?: Translate): string[] {
  const lines = [loc(t, "chat.statusMessages.failure.summaryLead", {}, "Training did not complete.")];
  const reason = sanitizeFailureReason(String(task.error_message || task.message || ""), t);
  if (reason) lines.push(loc(t, "chat.statusMessages.failure.errorReasonLine", { reason }, `Details: ${reason}`));
  lines.push(
    loc(t, "chat.statusMessages.failure.nextStepSummary", {}, "Open this task under Tasks to review the error summary."),
  );
  return lines;
}

function metricLabel(key: string): string {
  return trainingMetricLabel(key);
}
