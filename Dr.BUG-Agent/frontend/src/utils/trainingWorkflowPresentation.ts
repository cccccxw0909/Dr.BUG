/**
 * Training workflow card: fixed vocabulary and presentation helpers (no network, no state machine).
 */
import { resolveClinicalFeatureDisplayName } from "./featureDisplayName";

export const WF_PHASE3 = "train_phase3_feature_confirm_pending";
export const WF_PHASE4 = "train_phase4_train_config_pending";
export const WF_PHASE5 = "train_phase5_publish_pending";
export const WF_PHASE4_ALIAS = "train_phase4_config_confirm_pending";
export const WF_PHASE5_ALIAS = "train_phase5_publish_confirm_pending";

/** Pass `t` from `useI18n()` for localized strings; omit `t` only for unmigrated callers (English fallback). */
export type WorkflowPresentationTranslate = (key: string, values?: Record<string, unknown>) => string;

export function normalizeWorkflowPhase(phase: string): string {
  if (phase === WF_PHASE4_ALIAS) return WF_PHASE4;
  if (phase === WF_PHASE5_ALIAS) return WF_PHASE5;
  return phase;
}

/** Short stage label (legacy; outer chat capsule removed, main title includes stage). */
export function workflowCardStageShortTitle(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.titles.stageShort.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.titles.stageShort.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.titles.stageShort.phase5");
    return t("chat.trainingWorkflow.titles.stageShort.fallback");
  }
  if (p === WF_PHASE3) return "Feature confirmation";
  if (p === WF_PHASE4) return "Model & training settings";
  if (p === WF_PHASE5) return "Release confirmation";
  return "Training workflow";
}

/** Card header: business step name (no Phase number as main title). */
export function workflowCardBusinessTitle(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.titles.business.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.titles.business.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.titles.business.phase5");
    return t("chat.trainingWorkflow.titles.business.fallback");
  }
  if (p === WF_PHASE3) return "Model training — feature confirmation";
  if (p === WF_PHASE4) return "Model training — model selection & training settings";
  if (p === WF_PHASE5) return "Model training — release confirmation";
  return "Model training — awaiting confirmation";
}

/** Header right: status label aligned with main flow. */
export function workflowCardStatusTag(status: string | undefined | null, t?: WorkflowPresentationTranslate): string {
  const s = String(status || "").toLowerCase();
  if (t) {
    if (s === "pending") return t("chat.trainingWorkflow.status.pending");
    if (s === "submitted") return t("chat.trainingWorkflow.status.submitted");
    if (s === "completed") return t("chat.trainingWorkflow.status.completed");
    if (s === "locked") return t("chat.trainingWorkflow.status.locked");
    return t("chat.trainingWorkflow.status.processed");
  }
  if (s === "pending") return "Awaiting confirmation";
  if (s === "submitted") return "Submitted";
  if (s === "completed") return "Completed";
  if (s === "locked") return "Locked";
  return "Processed";
}

/** @deprecated Use workflowCardStatusTag(status). */
export function workflowCardHeadHint(t?: WorkflowPresentationTranslate): string {
  return t ? t("chat.trainingWorkflow.status.pending") : "Awaiting confirmation";
}

/** What is happening now (lead sentence). */
export function workflowCurrentDoingLine(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.narrative.currentDoing.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.narrative.currentDoing.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.narrative.currentDoing.phase5");
    return t("chat.trainingWorkflow.narrative.currentDoing.fallback");
  }
  if (p === WF_PHASE3)
    return "Review the screening summary below and confirm the final feature set when ready.";
  if (p === WF_PHASE4)
    return "Modeling columns are set. Compare candidate models with cross-validation, choose an algorithm and primary metric, then start training.";
  if (p === WF_PHASE5)
    return "Training finished. Review charts and metrics, then decide whether to publish for prediction and regimen recommendation.";
  return "Follow the instructions below to confirm in this card.";
}

/** What the user must confirm (second line; may be empty). */
export function workflowUserMustConfirmLine(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.narrative.userMustConfirm.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.narrative.userMustConfirm.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.narrative.userMustConfirm.phase5");
    return t("chat.trainingWorkflow.narrative.userMustConfirm.fallback");
  }
  if (p === WF_PHASE3) return "";
  if (p === WF_PHASE4)
    return "Pick the model and metric you want to optimize for, choose training effort, then start training.";
  if (p === WF_PHASE5)
    return "Confirm whether to publish the model, and optionally edit the model identifier and release notes.";
  return "";
}

/** What happens after confirmation. */
export function workflowWhatHappensNextLine(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.narrative.whatNext.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.narrative.whatNext.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.narrative.whatNext.phase5");
    return t("chat.trainingWorkflow.narrative.whatNext.fallback");
  }
  if (p === WF_PHASE3)
    return "After confirmation, you will proceed to training configuration confirmation, then background training.";
  if (p === WF_PHASE4) return "After you confirm, training and reporting run in the background—check Tasks for status.";
  if (p === WF_PHASE5)
    return "If you publish, the model becomes selectable for prediction; if you skip, you can still review saved outputs.";
  return "";
}

/** Submitted: one-line summary inside the card (stage is already in the title). */
export function workflowSubmittedSummaryLine(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.narrative.submittedSummary.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.narrative.submittedSummary.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.narrative.submittedSummary.phase5");
    return t("chat.trainingWorkflow.narrative.submittedSummary.fallback");
  }
  if (p === WF_PHASE3) return "Submitted; follow the background task and detail page for status.";
  if (p === WF_PHASE4) return "Submitted; the task has entered training.";
  if (p === WF_PHASE5) return "Submitted; check the tasks page for the final release outcome.";
  return "This confirmation step has been handled.";
}

export function workflowSubmittedBadgeLabel(phase: string, t?: WorkflowPresentationTranslate): string {
  const p = normalizeWorkflowPhase(phase);
  if (t) {
    if (p === WF_PHASE3) return t("chat.trainingWorkflow.badges.phase3");
    if (p === WF_PHASE4) return t("chat.trainingWorkflow.badges.phase4");
    if (p === WF_PHASE5) return t("chat.trainingWorkflow.badges.phase5");
    return t("chat.trainingWorkflow.badges.fallback");
  }
  if (p === WF_PHASE3) return "Feature confirmation";
  if (p === WF_PHASE4) return "Training configuration";
  if (p === WF_PHASE5) return "Release (go-live)";
  return "Training workflow";
}

/**
 * Map SHAP artifact filename slug (e.g. randomforest) to a short UI label.
 * Clinical feature display names are not passed through here.
 */
export function formatShapScreeningModelDisplayName(slug: string): string {
  const k = String(slug || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
  const map: Record<string, string> = {
    default: "",
    randomforest: "RandomForest",
    randomforestregressor: "RandomForest",
    xgboost: "XGBoost",
    xgbregressor: "XGBoost",
    lightgbm: "LightGBM",
    lgbmregressor: "LightGBM",
    catboost: "CatBoost",
    catboostregressor: "CatBoost",
    logisticregression: "Logistic Regression",
    svm: "SVM",
    knn: "KNN",
  };
  if (k in map) return map[k]!;
  const raw = String(slug || "").trim();
  if (!raw) return "";
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

/** Algorithm enum → short readable name (unknown kept as-is). */
export function trainingModelTypeDisplay(raw: string): string {
  const k = String(raw || "").toLowerCase();
  const map: Record<string, string> = {
    xgboost: "XGBoost",
    lightgbm: "LightGBM",
    catboost: "CatBoost",
    random_forest: "Random Forest",
    logistic_regression: "Logistic Regression",
    svm: "SVM",
    knn: "KNN",
  };
  return map[k] || raw;
}

/** Phase 3 list: primary display label for a column name. */
export function trainingFeaturePrimaryLabel(col: string): string {
  return resolveClinicalFeatureDisplayName(String(col || "").trim());
}

/** Phase 2 explanation figures block title (avoid leading with “SHAP”). */
export function phase2ExplainFigureGroupTitle(t?: WorkflowPresentationTranslate): string {
  return t ? t("chat.trainingWorkflow.phase2.explainFiguresTitle") : "Explanation figures (feature importance context)";
}

/** Training metric key → display label (shared with task detail / result card). */
export function trainingMetricLabel(key: string): string {
  const k = String(key || "").trim();
  const map: Record<string, string> = {
    auroc: "AUROC",
    auprc: "AUPRC",
    accuracy: "Accuracy",
    precision: "Precision",
    recall: "Recall",
    f1_score: "F1",
    mse: "MSE",
    mae: "MAE",
    rmse: "RMSE",
    r2: "R²",
    pearson: "Pearson",
    pcc: "PCC",
    primary_metric_requested: "Primary metric",
    trained_model_programmer_name: "Trained model id",
  };
  if (map[k]) return map[k];
  return resolveClinicalFeatureDisplayName(k);
}
