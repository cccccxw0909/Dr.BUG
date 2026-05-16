/**
 * Task status narrative utilities for user-facing UI text.
 *
 * Notes:
 * - Do not change backend status values or any task logic; this module only formats display text.
 * - Do not call useI18n() here. Call sites must pass a lightweight translator.
 */
import type { Translate } from "./messageSanitizer";
import { sanitizeUserFacingLine } from "./messageSanitizer";
import {
  formatJobTypeLabel,
  formatPredictionTaskListTitle,
  formatTaskStatusLabel,
  isBatchPredictionTaskRecord,
  isPredictionJobType,
  isRecommendationJobType,
  isReportGenerationJob,
  isShapGenerationJob,
  isTrainingJobType,
} from "./taskPresentation";
import { localizeTrainingResultHeadlineForEnUi } from "./trainingBackendDisplayGuard";
import { normalizeWorkflowPhase, workflowCardBusinessTitle } from "./trainingWorkflowPresentation";

export type { Translate };

const MUTED_MESSAGES = new Set(
  ["training completed", "prediction completed", "recommendation completed", "completed", "success", "succeeded"].map((s) =>
    s.toLowerCase(),
  ),
);

/** Training: convert current_stage into a user-facing step (without queue/running prefixes). */
export function formatTrainingStageUserLine(stage: string | null | undefined, t: Translate): string {
  const s = String(stage || "").trim().toLowerCase();
  if (!s) return "";
  if (s.includes("dataset_validation")) return t("taskNarrative.trainingStage.datasetValidation");
  if (s.includes("train_phase2")) return t("taskNarrative.trainingStage.phase2");
  if (s.includes("train_phase3")) return t("taskNarrative.trainingStage.phase3");
  if (s.includes("train_phase4")) return t("taskNarrative.trainingStage.phase4");
  if (s.includes("train_phase5")) return t("taskNarrative.trainingStage.phase5");
  if (s === "model_training") return t("taskNarrative.trainingStage.modelTraining");
  if (s === "evaluation") return t("taskNarrative.trainingStage.evaluation");
  return s.replace(/_/g, " ");
}

/** Task list / card primary label: what this task is. */
export function formatTaskWhatItIs(task: Record<string, unknown>, t: Translate): string {
  const jt = String(task.job_type || "");
  if (isPredictionJobType(jt)) return formatPredictionTaskListTitle(task, t);
  if (isTrainingJobType(jt)) return t("taskNarrative.whatItIs.training");
  const lab = formatJobTypeLabel(jt, t);
  return lab !== "-" ? lab : t("taskNarrative.whatItIs.generic");
}

function nonTrainRunningCompanion(jt: string, task: Record<string, unknown>, t: Translate): string {
  if (isPredictionJobType(jt)) {
    if (isBatchPredictionTaskRecord(task)) return t("taskNarrative.companion.predictBatch.running");
    return t("taskNarrative.companion.predictSingle.running");
  }
  if (isRecommendationJobType(jt)) return t("taskNarrative.companion.recommend.running");
  if (isShapGenerationJob(jt)) return t("taskNarrative.companion.shap.running");
  if (isReportGenerationJob(jt)) return t("taskNarrative.companion.report.running");
  return t("taskNarrative.companion.generic.running");
}

function nonTrainCompletedCompanion(jt: string, task: Record<string, unknown>, t: Translate): string {
  if (isPredictionJobType(jt)) {
    if (isBatchPredictionTaskRecord(task)) {
      return t("taskNarrative.companion.predictBatch.completed");
    }
    return t("taskNarrative.companion.predictSingle.completed");
  }
  if (isRecommendationJobType(jt)) return t("taskNarrative.companion.recommend.completed");
  if (isShapGenerationJob(jt)) return t("taskNarrative.companion.shap.completed");
  if (isReportGenerationJob(jt)) return t("taskNarrative.companion.report.completed");
  return t("taskNarrative.companion.generic.completed");
}

function nonTrainWaitingCompanion(jt: string, t: Translate): string {
  if (isPredictionJobType(jt)) return t("taskNarrative.companion.predict.waitingUser");
  if (isRecommendationJobType(jt)) return t("taskNarrative.companion.recommend.waitingUser");
  if (isShapGenerationJob(jt) || isReportGenerationJob(jt)) return t("taskNarrative.companion.generic.waitingUser");
  return t("taskNarrative.companion.generic.waitingUser");
}

function nonTrainFailedCompanion(jt: string, t: Translate): string {
  if (isPredictionJobType(jt)) return t("taskNarrative.companion.predict.failed");
  if (isRecommendationJobType(jt)) return t("taskNarrative.companion.recommend.failed");
  if (isShapGenerationJob(jt)) return t("taskNarrative.companion.shap.failed");
  if (isReportGenerationJob(jt)) return t("taskNarrative.companion.report.failed");
  return t("taskNarrative.companion.generic.failed");
}

/** Task list / card: where it stands now (includes the status pill for full-sentence contexts). */
export function formatTaskWhereItStands(task: Record<string, unknown>, t: Translate): string {
  const st = String(task.status || "").toLowerCase();
  const jt = String(task.job_type || "");
  const pill = formatTaskStatusLabel(String(task.status || ""), t);

  if (st === "waiting_user") {
    if (isTrainingJobType(jt))
      return `${pill} · ${formatTaskStatusCompanionLine(task, t) || t("taskNarrative.whereItStands.waitingUserFallback")}`;
    return `${pill} · ${nonTrainWaitingCompanion(jt, t)}`;
  }
  if (st === "queued") return `${pill} · ${t("taskNarrative.whereItStands.queued")}`;
  if (st === "running") {
    if (isTrainingJobType(jt)) {
      const line = formatTrainingStageUserLine(String(task.current_stage || ""), t);
      return line ? `${pill} · ${line}` : `${pill} · ${t("taskNarrative.whereItStands.runningFallback")}`;
    }
    const sub = nonTrainRunningCompanion(jt, task, t);
    return `${pill} · ${sub}`;
  }
  if (st === "completed" || st === "success" || st === "succeeded") {
    if (isTrainingJobType(jt)) return `${pill} · ${t("taskNarrative.whereItStands.trainingCompleted")}`;
    const sub = nonTrainCompletedCompanion(jt, task, t);
    return `${pill} · ${sub}`;
  }
  if (st === "failed") return `${pill} · ${nonTrainFailedCompanion(jt, t)}`;
  if (st === "canceled" || st === "cancelled") return `${pill} · ${t("taskNarrative.whereItStands.canceled")}`;
  return pill;
}

/**
 * A companion line used with the status pill (no repeated status word).
 * Used in the task list "progress note", right panel, etc., to avoid duplicating the pill text.
 */
export function formatTaskStatusCompanionLine(task: Record<string, unknown>, t: Translate): string {
  const st = String(task.status || "").toLowerCase();
  const jt = String(task.job_type || "");
  if (st === "waiting_user") {
    if (isTrainingJobType(jt)) {
      const rs = (task.result_summary as Record<string, unknown>) || {};
      const ph = normalizeWorkflowPhase(String(rs.train_workflow_phase || String(task.current_stage || "")));
      const title = workflowCardBusinessTitle(ph, t);
      return t("taskNarrative.companion.trainingWaitingConfirm", { title });
    }
    return nonTrainWaitingCompanion(jt, t);
  }
  if (st === "queued") return t("taskNarrative.companion.queued");
  if (st === "running") {
    if (isTrainingJobType(jt)) {
      const line = formatTrainingStageUserLine(String(task.current_stage || ""), t);
      return line ? t("taskNarrative.companion.trainingRunningWithStage", { stage: line }) : t("taskNarrative.companion.trainingRunning");
    }
    return nonTrainRunningCompanion(jt, task, t);
  }
  if (st === "completed" || st === "success" || st === "succeeded") {
    if (isTrainingJobType(jt)) {
      const rs = (task.result_summary as Record<string, unknown>) || {};
      let headline = sanitizeUserFacingLine(String(rs.headline || ""), t) || String(rs.headline || "").trim();
      headline = localizeTrainingResultHeadlineForEnUi(headline, t);
      const released = Boolean(rs.model_registered) || Boolean(rs.is_published);
      const rel = released ? t("taskNarrative.companion.trainingReleased") : t("taskNarrative.companion.trainingNotReleased");
      if (headline) {
        const clip = headline.length > 90 ? `${headline.slice(0, 89)}…` : headline;
        return t("taskNarrative.companion.trainingCompletedHeadline", { headline: clip, release: rel });
      }
      return t("taskNarrative.companion.trainingCompletedFallback", { release: rel });
    }
    return nonTrainCompletedCompanion(jt, task, t);
  }
  if (st === "failed") return nonTrainFailedCompanion(jt, t);
  if (st === "canceled" || st === "cancelled") return t("taskNarrative.companion.canceled");
  return "";
}

/** Task list "progress note" only: conservative fallback when no companion line is available. */
export function formatTaskListProgressLine(task: Record<string, unknown>, t: Translate): string {
  const c = formatTaskStatusCompanionLine(task, t);
  if (c) return c;
  const st = String(task.status || "").toLowerCase();
  if (st === "completed" || st === "success" || st === "succeeded") return t("taskNarrative.progress.completedFallback");
  if (st === "running") return t("taskNarrative.progress.runningFallback");
  if (st === "queued") return t("taskNarrative.progress.queuedFallback");
  return "";
}

/** Task list / right panel: primary line from a long message (truncate; de-dup against headline). */
export function formatTaskMessagePrimaryForList(
  message: string | null | undefined,
  headline: string | null | undefined,
  opts?: { maxLen?: number },
  t?: Translate,
): string {
  const maxLen = opts?.maxLen ?? 80;
  const h = String(headline || "").trim();
  const m0 = String(message || "").trim();
  const m = sanitizeUserFacingLine(m0, t) || m0;
  const low = m.toLowerCase();
  if (!m || MUTED_MESSAGES.has(low)) {
    if (h) return h.length > maxLen ? `${h.slice(0, maxLen)}…` : h;
    return "";
  }
  if (h && m === h) return m.length > maxLen ? `${m.slice(0, maxLen)}…` : m;
  const first = m.split(/\r?\n/)[0].trim();
  if (first.length <= maxLen) return first;
  return `${first.slice(0, maxLen)}…`;
}
