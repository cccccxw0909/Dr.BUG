/**
 * Assistant short messages for terminal task states in chat.
 */
import type { TaskDetailData } from "../types";
import {
  isBatchPredictionTaskRecord,
  isPredictionJobType,
  isRecommendationJobType,
  isReportGenerationJob,
  isShapGenerationJob,
  isTrainingJobType,
} from "./taskPresentation";

export type Translate = (key: string, values?: Record<string, unknown>) => string;

export function getTerminalCompletionAssistantMessage(detail: TaskDetailData, t: Translate): string {
  const jt = String(detail.task.job_type || "");
  const task = detail.task as unknown as Record<string, unknown>;

  if (isTrainingJobType(jt)) {
    return t("taskTerminal.completion.train");
  }
  if (isPredictionJobType(jt)) {
    if (isBatchPredictionTaskRecord(task)) {
      return t("taskTerminal.completion.predictBatch");
    }
    return t("taskTerminal.completion.predictSingle");
  }
  if (isRecommendationJobType(jt)) {
    return t("taskTerminal.completion.recommend");
  }
  if (isShapGenerationJob(jt)) {
    return t("taskTerminal.completion.shap");
  }
  if (isReportGenerationJob(jt)) {
    return t("taskTerminal.completion.report");
  }
  return t("taskTerminal.completion.generic");
}

export function getTerminalFailureAssistantPrefix(jobType: string, t: Translate): string {
  const jt = String(jobType || "");
  if (isPredictionJobType(jt)) return t("taskTerminal.failurePrefix.predict");
  if (isRecommendationJobType(jt)) return t("taskTerminal.failurePrefix.recommend");
  if (isShapGenerationJob(jt)) return t("taskTerminal.failurePrefix.shap");
  if (isReportGenerationJob(jt)) return t("taskTerminal.failurePrefix.report");
  if (isTrainingJobType(jt)) return t("taskTerminal.failurePrefix.train");
  return t("taskTerminal.failurePrefix.generic");
}

export function getTerminalCanceledAssistantMessage(jobType: string, t: Translate): string {
  const jt = String(jobType || "");
  if (isPredictionJobType(jt)) return t("taskTerminal.canceled.predict");
  if (isRecommendationJobType(jt)) return t("taskTerminal.canceled.recommend");
  if (isShapGenerationJob(jt)) return t("taskTerminal.canceled.shap");
  if (isReportGenerationJob(jt)) return t("taskTerminal.canceled.report");
  if (isTrainingJobType(jt)) return t("taskTerminal.canceled.train");
  return t("taskTerminal.canceled.generic");
}
