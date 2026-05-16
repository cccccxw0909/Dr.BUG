/**
 * Frontend training-contract normalization aligned with backend `training_contract.normalize_training_payload` semantics.
 * Chat cards and dataset entry points should merge legacy fields through this module instead of assembling payloads independently.
 */

export const CLINICAL_TASK_IDS = [
  "clinical_efficacy",
  "mortality_28d",
  "polymyxin_resistance",
  "treatment_duration",
] as const;

export type ClinicalTaskId = (typeof CLINICAL_TASK_IDS)[number];

export const ML_TASK_TYPES = ["binary", "multiclass", "regression"] as const;
export type MlTaskType = (typeof ML_TASK_TYPES)[number];

/** Default ML task type from clinical task when the user has not set one (demo inference). */
export function inferMlTaskTypeFromClinicalTaskId(clinicalTaskId: string): string | null {
  const id = String(clinicalTaskId ?? "").trim();
  if (!id) return null;
  if (id === "treatment_duration") return "regression";
  if (id === "mortality_28d" || id === "clinical_efficacy" || id === "polymyxin_resistance") return "binary";
  return null;
}

/** Keep the same order as backend/agent/training_contract.REQUIRED_TRAINING_FIELD_KEYS. */
export const REQUIRED_TRAINING_PARAMETER_KEYS = [
  "dataset_id",
  "clinical_task_id",
  "ml_task_type",
  "target_column",
  "model_type",
  "objective_metric",
] as const;

export function isNonEmptyString(v: unknown): boolean {
  return typeof v === "string" && v.trim().length > 0;
}

/**
 * Convert legacy/mixed payloads to new contract keys without relying on the overloaded task_type semantics.
 * - If only `task_type` is present: split it by enum into clinical_task_id or ml_task_type.
 */
export function mergeLegacyTrainingAliases(raw: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...raw };
  const legacy = out.task_type;
  if (legacy !== undefined && legacy !== null && String(legacy).trim() !== "") {
    if (!out.clinical_task_id && !out.ml_task_type) {
      const t = String(legacy).trim();
      const clinicalSet = new Set<string>(CLINICAL_TASK_IDS as unknown as string[]);
      const mlSet = new Set<string>(ML_TASK_TYPES as unknown as string[]);
      if (clinicalSet.has(t)) out.clinical_task_id = t;
      else if (mlSet.has(t)) out.ml_task_type = t;
      else out.clinical_task_id = t;
    }
    delete out.task_type;
  }
  return out;
}

function normalizeList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of value) {
    const v = String(item ?? "").trim();
    if (!v || seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

function normalizeNullableText(value: unknown): string | null {
  const v = String(value ?? "").trim();
  return v ? v : null;
}

/** Build an editable draft from chat-completed parameters, including defaults. */
export function trainingDraftFromCompletedParams(completed: Record<string, unknown>): {
  dataset_id: string;
  clinical_task_id: string;
  ml_task_type: string;
  target_column: string;
  selected_features: string[];
  final_features: string[];
  med_cols: string[];
  enable_feature_set_search: boolean;
  min_features: number;
  max_features: number;
  enable_search: boolean;
  use_cv_shap: boolean;
  model_type: string;
  model_name: string;
  feature_set: string;
  objective_metric: string;
  primary_metric: string;
  index_time: string;
  label_time: string;
  publish_model_id: string;
  publish_notes: string;
} {
  const m = mergeLegacyTrainingAliases(completed);
  const publishOverrides =
    m.publish_overrides && typeof m.publish_overrides === "object"
      ? (m.publish_overrides as Record<string, unknown>)
      : {};
  const clinicalId = String(m.clinical_task_id ?? "mortality_28d").trim();
  let mlTaskType = String(m.ml_task_type ?? "").trim();
  if (!mlTaskType) {
    mlTaskType = inferMlTaskTypeFromClinicalTaskId(clinicalId) ?? "";
  }
  let objectiveMetric = String(m.objective_metric ?? "").trim();
  if (!objectiveMetric) {
    objectiveMetric = mlTaskType === "regression" ? "mse" : "auroc";
  }
  return {
    dataset_id: String(m.dataset_id ?? ""),
    clinical_task_id: clinicalId || "mortality_28d",
    ml_task_type: mlTaskType,
    target_column: String(m.target_column ?? ""),
    selected_features: normalizeList(m.selected_features),
    final_features: normalizeList(m.final_features),
    med_cols: normalizeList(m.med_cols),
    enable_feature_set_search: Boolean(m.enable_feature_set_search ?? false),
    min_features: Number(m.min_features ?? 1),
    max_features: Number(m.max_features ?? 10),
    enable_search: Boolean(m.enable_search ?? false),
    use_cv_shap: Boolean(m.use_cv_shap ?? false),
    model_type: String(m.model_type ?? "xgboost"),
    model_name: String(m.model_name ?? ""),
    feature_set: String(m.feature_set ?? ""),
    objective_metric: objectiveMetric,
    primary_metric: String(m.primary_metric ?? ""),
    index_time: String(m.index_time ?? ""),
    label_time: String(m.label_time ?? ""),
    publish_model_id: String(publishOverrides.model_id ?? ""),
    publish_notes: String(publishOverrides.notes ?? ""),
  };
}

/** Generate a patch from the draft for completed_params using new contract fields, excluding dataset_id. */
export function patchFromTrainingDraft(draft: ReturnType<typeof trainingDraftFromCompletedParams>): Record<string, unknown> {
  const primaryMetric = String(draft.primary_metric ?? "").trim();
  const objectiveMetric = String(draft.objective_metric ?? "").trim();
  const publishModelId = normalizeNullableText(draft.publish_model_id);
  const publishNotes = normalizeNullableText(draft.publish_notes);
  let mlTaskType = String(draft.ml_task_type ?? "").trim();
  if (!mlTaskType) {
    mlTaskType = inferMlTaskTypeFromClinicalTaskId(String(draft.clinical_task_id ?? "")) ?? "";
  }
  const out: Record<string, unknown> = {
    dataset_id: String(draft.dataset_id ?? "").trim(),
    clinical_task_id: draft.clinical_task_id,
    ml_task_type: mlTaskType,
    target_column: draft.target_column.trim(),
    selected_features: normalizeList(draft.selected_features),
    final_features: normalizeList(draft.final_features),
    med_cols: normalizeList(draft.med_cols),
    enable_feature_set_search: Boolean(draft.enable_feature_set_search),
    min_features: Number(draft.min_features ?? 1),
    max_features: Number(draft.max_features ?? 10),
    enable_search: Boolean(draft.enable_search),
    use_cv_shap: Boolean(draft.use_cv_shap),
    model_type: draft.model_type,
    model_name: normalizeNullableText(draft.model_name),
    feature_set: normalizeNullableText(draft.feature_set),
    objective_metric: objectiveMetric,
    primary_metric: primaryMetric || objectiveMetric,
    index_time: normalizeNullableText(draft.index_time),
    label_time: normalizeNullableText(draft.label_time),
  };
  if (publishModelId || publishNotes) {
    out.publish_overrides = { model_id: publishModelId, notes: publishNotes };
  }
  return out;
}

export function missingTrainingParameterKeys(completed: Record<string, unknown>, requireDataset = true): string[] {
  const m = mergeLegacyTrainingAliases(completed);
  const miss: string[] = [];
  if (requireDataset && !isNonEmptyString(m.dataset_id)) miss.push("dataset_id");
  if (!isNonEmptyString(m.clinical_task_id)) miss.push("clinical_task_id");
  let mlType = String(m.ml_task_type ?? "").trim();
  if (!mlType && isNonEmptyString(m.clinical_task_id)) {
    mlType = inferMlTaskTypeFromClinicalTaskId(String(m.clinical_task_id)) ?? "";
  }
  if (!isNonEmptyString(mlType)) miss.push("ml_task_type");
  if (!isNonEmptyString(m.target_column)) miss.push("target_column");
  if (!isNonEmptyString(m.model_type)) miss.push("model_type");
  if (!isNonEmptyString(m.objective_metric)) miss.push("objective_metric");
  const hasFeatureSource =
    isNonEmptyString(m.feature_set) ||
    (Array.isArray(m.selected_features) && (m.selected_features as unknown[]).length > 0) ||
    (Array.isArray(m.final_features) && (m.final_features as unknown[]).length > 0) ||
    Boolean(m.enable_feature_set_search) ||
    Boolean(m.use_cv_shap);
  if (!hasFeatureSource) miss.push("feature_source");
  return miss;
}

export function normalizeTrainingPayloadForSubmit(completed: Record<string, unknown>): Record<string, unknown> {
  const draft = trainingDraftFromCompletedParams(completed);
  return patchFromTrainingDraft(draft);
}

/** Phase 1 confirmation aligned with backend TrainingPhase1Payload, excluding final_features / model / publish. */
export function normalizePhase1TrainingPayloadForSubmit(completed: Record<string, unknown>): Record<string, unknown> {
  const m = mergeLegacyTrainingAliases(completed);
  const clinicalId = String(m.clinical_task_id ?? "mortality_28d").trim();
  let mlType = String(m.ml_task_type ?? "").trim();
  if (!mlType) {
    mlType = inferMlTaskTypeFromClinicalTaskId(clinicalId) ?? "";
  }
  const out: Record<string, unknown> = {
    dataset_id: String(m.dataset_id ?? "").trim(),
    clinical_task_id: clinicalId || "mortality_28d",
    ml_task_type: mlType,
    target_column: String(m.target_column ?? "").trim(),
    selected_features: normalizeList(m.selected_features),
    med_cols: normalizeList(m.med_cols),
    enable_feature_set_search: Boolean(m.enable_feature_set_search ?? false),
    min_features: Number(m.min_features ?? 1),
    max_features: Number(m.max_features ?? 10),
    use_cv_shap: Boolean(m.use_cv_shap ?? false),
    feature_set: normalizeNullableText(m.feature_set),
    index_time: normalizeNullableText(m.index_time),
    label_time: normalizeNullableText(m.label_time),
  };
  const finals = normalizeList(m.final_features);
  if (finals.length > 0) out.final_features = finals;
  return out;
}

export function missingTrainingPhase1ParameterKeys(completed: Record<string, unknown>, requireDataset = true): string[] {
  const p = normalizePhase1TrainingPayloadForSubmit(mergeLegacyTrainingAliases(completed));
  const miss: string[] = [];
  if (requireDataset && !isNonEmptyString(p.dataset_id)) miss.push("dataset_id");
  if (!isNonEmptyString(p.clinical_task_id)) miss.push("clinical_task_id");
  if (!isNonEmptyString(p.ml_task_type)) miss.push("ml_task_type");
  if (!isNonEmptyString(p.target_column)) miss.push("target_column");
  const hasFeatureSource =
    isNonEmptyString(p.feature_set) ||
    (Array.isArray(p.selected_features) && p.selected_features.length > 0) ||
    Boolean(p.enable_feature_set_search) ||
    Boolean(p.use_cv_shap);
  if (!hasFeatureSource) miss.push("feature_source");
  return miss;
}
