/**
 * User-facing model line for prediction submission summary (no raw registry IDs in the primary row).
 */

export type SubmittedSummaryModelKind =
  | "survival"
  | "mortality"
  | "survival_benefit"
  | "resistance"
  | "treatment_duration"
  | "clinical_outcome"
  | "generic";

function haystack(taskName: string, displayName: string, modelId: string): string {
  return `${taskName} ${displayName} ${modelId}`.toLowerCase();
}

/** Infer a coarse model category for friendly labels only (not training semantics). */
export function inferSubmittedSummaryModelKind(payload: {
  task_name?: string | null;
  model_display_name?: string | null;
  model_id?: string | null;
}): SubmittedSummaryModelKind {
  const h = haystack(
    String(payload.task_name || ""),
    String(payload.model_display_name || ""),
    String(payload.model_id || ""),
  );
  if (/polymyxin|resistan|mic/i.test(h)) return "resistance";
  if (/duration|days_on/i.test(h)) return "treatment_duration";
  if (/survival/i.test(h) && /benefit|improv|efficacy/i.test(h)) return "survival_benefit";
  if (/mortality|28d|28-day|death/i.test(h)) return "mortality";
  if (/survival/i.test(h)) return "survival";
  if (/clinical_outcome|clinical outcome|efficacy|response|outcome|clinical/i.test(h)) return "clinical_outcome";
  return "generic";
}

/**
 * Best-effort algorithm token from display name / model id (well-known learners only).
 * Returns null when nothing matches — callers must not invent labels.
 */
export function extractKnownAlgorithmName(rawDisplay: string, rawModelId: string): string | null {
  const blob = `${rawDisplay} ${rawModelId}`;
  const patterns: Array<[RegExp, string]> = [
    [/CatBoost/i, "CatBoost"],
    [/LightGBM|LGBM/i, "LightGBM"],
    [/XGBoost|\bXGB\b/i, "XGBoost"],
    [/RandomForest|Random Forest/i, "Random Forest"],
    [/GradientBoosting|Gradient Boosting|GBDT/i, "Gradient boosting"],
    [/ExtraTrees|Extra Trees/i, "Extra trees"],
    [/AdaBoost/i, "AdaBoost"],
    [/LogisticRegression|Logistic Regression/i, "Logistic regression"],
    [/\bSVC\b|Support Vector/i, "SVC"],
    [/\bMLP\b|MLPClassifier/i, "MLP"],
    [/DecisionTree|Decision Tree/i, "Decision tree"],
  ];
  for (const [re, label] of patterns) {
    if (re.test(blob)) return label;
  }
  return null;
}
