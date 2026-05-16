import type { TaskDetailData, TaskItem, TrainingWorkflowPendingActionData, TrainingWorkflowPhase } from "../types";
import type { WorkflowPresentationTranslate } from "./trainingWorkflowPresentation";
import { workflowCardBusinessTitle } from "./trainingWorkflowPresentation";

/** Align with backend `Task.result_summary.train_workflow_phase` and workflow resume stages. */
export function normalizeTrainingWorkflowPhase(raw: string): TrainingWorkflowPhase | null {
  const phase = String(raw || "").trim();
  if (phase === "train_phase3_feature_confirm_pending") return "train_phase3_feature_confirm_pending";
  if (phase === "train_phase4_train_config_pending" || phase === "train_phase4_config_confirm_pending") {
    return "train_phase4_train_config_pending";
  }
  if (phase === "train_phase5_publish_pending" || phase === "train_phase5_publish_confirm_pending") {
    return "train_phase5_publish_pending";
  }
  return null;
}

/**
 * When `result_summary.train_workflow_phase` is missing or stale, infer the workflow step from
 * `task.current_stage` (present on task list rows and status polling).
 */
export function inferTrainingWorkflowPhaseFromStage(stageRaw: string): TrainingWorkflowPhase | null {
  const s0 = String(stageRaw || "").trim();
  if (!s0) return null;
  const direct = normalizeTrainingWorkflowPhase(s0);
  if (direct) return direct;
  const s = s0.toLowerCase();
  if (s.includes("phase3") && s.includes("feature") && (s.includes("confirm") || s.includes("pending"))) {
    return "train_phase3_feature_confirm_pending";
  }
  if (s.includes("phase4") && (s.includes("config") || s.includes("train_config"))) {
    return "train_phase4_train_config_pending";
  }
  if (s.includes("phase5") && s.includes("publish")) {
    return "train_phase5_publish_pending";
  }
  return null;
}

function workflowPhaseOrder(phase: TrainingWorkflowPhase): number {
  if (phase === "train_phase3_feature_confirm_pending") return 3;
  if (phase === "train_phase4_train_config_pending") return 4;
  return 5;
}

export function resolveTrainingWorkflowPhase(task: Record<string, unknown>): TrainingWorkflowPhase | null {
  const rs = (task.result_summary as Record<string, unknown>) || {};
  const wf = String(rs.train_workflow_phase || "").trim();
  const fromSummary = normalizeTrainingWorkflowPhase(wf);
  const fromStage = inferTrainingWorkflowPhaseFromStage(String(task.current_stage || ""));
  if (fromSummary && fromStage) {
    return workflowPhaseOrder(fromStage) >= workflowPhaseOrder(fromSummary) ? fromStage : fromSummary;
  }
  return fromSummary || fromStage;
}

/** Whether a task list row represents a training workflow step that needs an in-chat confirmation card. */
export function taskRowNeedsWorkflowConfirmation(task: TaskItem & Record<string, unknown>): boolean {
  if (String(task.status || "") !== "waiting_user") return false;
  if (String(task.job_type || "") !== "train_model") return false;
  return resolveTrainingWorkflowPhase(task as Record<string, unknown>) !== null;
}

/**
 * Normalized training workflow interpretation for UI panels (ContextPanel, etc.).
 * Single source of truth for phase resolution — do not re-parse `train_workflow_phase` / `current_stage` elsewhere.
 */
export type TrainingWorkflowPanelDisplayState = {
  isTrainingJob: boolean;
  resolvedPhase: TrainingWorkflowPhase | null;
  /** waiting_user + train_model + resolvable workflow phase */
  needsWorkflowConfirmation: boolean;
  /** Feature confirmation step (Phase 3 card) */
  needsFeatureConfirmation: boolean;
  /** Matches App.vue polling throttle for train_model tasks */
  shouldPollAggressively: boolean;
  /** Localized business title for the resolved phase (fallback title when phase unknown) */
  workflowBusinessTitle: string;
};

export function getTrainingWorkflowDisplayState(
  task: TaskItem & Record<string, unknown> | null | undefined,
  t: WorkflowPresentationTranslate,
): TrainingWorkflowPanelDisplayState {
  const empty: TrainingWorkflowPanelDisplayState = {
    isTrainingJob: false,
    resolvedPhase: null,
    needsWorkflowConfirmation: false,
    needsFeatureConfirmation: false,
    shouldPollAggressively: false,
    workflowBusinessTitle: "",
  };
  if (!task) return empty;
  const isTraining = String(task.job_type || "") === "train_model";
  if (!isTraining) return empty;

  const taskStatus = String(task.status || "").toLowerCase();
  const resolvedPhase = resolveTrainingWorkflowPhase(task as Record<string, unknown>);
  const needsWorkflowConfirmation = taskRowNeedsWorkflowConfirmation(task);
  const needsFeatureConfirmation =
    needsWorkflowConfirmation && resolvedPhase === "train_phase3_feature_confirm_pending";

  const terminal =
    taskStatus === "completed" ||
    taskStatus === "failed" ||
    taskStatus === "canceled" ||
    taskStatus === "cancelled" ||
    taskStatus === "success" ||
    taskStatus === "succeeded";
  const shouldPollAggressively = !terminal && taskStatus !== "waiting_user";

  const workflowBusinessTitle = workflowCardBusinessTitle(resolvedPhase ?? "", t);

  return {
    isTrainingJob: true,
    resolvedPhase,
    needsWorkflowConfirmation,
    needsFeatureConfirmation,
    shouldPollAggressively,
    workflowBusinessTitle,
  };
}

export function buildTrainingWorkflowPendingCard(
  jobId: string,
  detail: TaskDetailData | Record<string, unknown>,
): TrainingWorkflowPendingActionData | null {
  try {
    const root = detail as TaskDetailData;
    const task = (root.task || (detail as { task?: unknown }).task) as Record<string, unknown>;
    if (!task || typeof task !== "object") return null;
    if (String(task.status || "") !== "waiting_user") return null;

    const phase = resolveTrainingWorkflowPhase(task);
    if (!phase) return null;

    const params = (task.params as Record<string, unknown>) || {};
    const rs = (task.result_summary as Record<string, unknown>) || {};
    const cardId = `${jobId}:${phase}`;
    const suggested = Array.isArray(rs.suggested_final_features)
      ? (rs.suggested_final_features as unknown[]).map((x) => String(x))
      : [];
    const med = Array.isArray(params.med_cols) ? (params.med_cols as unknown[]).map((x) => String(x)) : [];
    const pool = Array.isArray(rs.candidate_pool_columns)
      ? (rs.candidate_pool_columns as unknown[]).map((x) => String(x))
      : [];

    const keyMetrics =
      rs.key_metrics && typeof rs.key_metrics === "object" ? (rs.key_metrics as Record<string, unknown>) : undefined;
    const taskArts =
      task.artifacts && typeof task.artifacts === "object" ? (task.artifacts as Record<string, string>) : {};
    const detailArts =
      (detail as Record<string, unknown>).artifacts &&
      typeof (detail as Record<string, unknown>).artifacts === "object"
        ? ((detail as Record<string, unknown>).artifacts as Record<string, string>)
        : {};
    const artifacts: Record<string, string> = { ...taskArts, ...detailArts };

    return {
      kind: "training_workflow_pending_action",
      card_id: cardId,
      job_id: jobId,
      phase,
      status: "pending",
      created_at_iso: new Date().toISOString(),
      params_snapshot: params,
      result_summary: rs,
      suggested_final_features: suggested,
      med_cols: med,
      candidate_pool_columns: pool,
      ml_task_type: String(params.ml_task_type || ""),
      model_id: (() => {
        const raw = rs.model_id_draft ?? rs.model_id ?? params.model_id;
        const s = raw != null ? String(raw).trim() : "";
        return s ? s : null;
      })(),
      key_metrics: keyMetrics,
      artifacts,
    };
  } catch (err) {
    if (import.meta.env.DEV) console.warn("[buildTrainingWorkflowPendingCard]", jobId, err);
    return null;
  }
}
