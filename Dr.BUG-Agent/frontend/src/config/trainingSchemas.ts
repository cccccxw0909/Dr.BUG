export type SelectOption = { label: string; value: string };
export type TrainingFieldGroup = "data_task" | "feature_columns" | "advanced" | "publish";
export type TrainingInputType = "select" | "text" | "textarea" | "multiselect" | "switch" | "number";

/** Optional translator from vue-i18n or tests; when omitted, English fallbacks are used. */
export type TrainingSchemaTranslate = (key: string, values?: Record<string, unknown>) => string;

export type TrainingFieldKey =
  | "dataset_id"
  | "clinical_task_id"
  | "ml_task_type"
  | "target_column"
  | "feature_set"
  | "selected_features"
  | "final_features"
  | "med_cols"
  | "model_type"
  | "model_name"
  | "objective_metric"
  | "primary_metric"
  | "enable_feature_set_search"
  | "min_features"
  | "max_features"
  | "enable_search"
  | "use_cv_shap"
  | "index_time"
  | "label_time"
  | "publish_overrides.model_id"
  | "publish_overrides.notes";

/**
 * Demo-facing editor sections (Phase 1 chat card).
 * Hidden fields (feature_set, index_time, label_time, publish) still merge via payload helpers with null/empty defaults.
 */
export const TRAINING_PHASE1_SETUP_KEYS: readonly TrainingFieldKey[] = [
  "dataset_id",
  "clinical_task_id",
  "ml_task_type",
  "target_column",
] as const;

export const TRAINING_PHASE1_FEATURE_KEYS: readonly TrainingFieldKey[] = ["selected_features", "med_cols"] as const;

export const TRAINING_PHASE1_ADVANCED_PARAM_KEYS: readonly TrainingFieldKey[] = [
  "enable_feature_set_search",
  "min_features",
  "max_features",
  "use_cv_shap",
] as const;

/** @deprecated Use section constants above; kept for imports that expect a flat Phase1 list */
export const TRAINING_PHASE1_FIELD_KEYS: readonly TrainingFieldKey[] = [
  ...TRAINING_PHASE1_SETUP_KEYS,
  ...TRAINING_PHASE1_FEATURE_KEYS,
  ...TRAINING_PHASE1_ADVANCED_PARAM_KEYS,
] as const;

/** Legacy advanced slot — no longer rendered in the demo UI */
export const TRAINING_PHASE1_ADVANCED_FIELD_KEYS: readonly TrainingFieldKey[] = [] as const;

export const TRAINING_PHASE1_ALL_FIELD_KEYS: readonly TrainingFieldKey[] = [...TRAINING_PHASE1_FIELD_KEYS] as const;

export type TrainingFieldSchema = {
  key: TrainingFieldKey;
  label: string;
  type: TrainingInputType;
  group: TrainingFieldGroup;
  required?: boolean;
  description?: string;
  placeholder?: string;
  defaultValue?: string | number | boolean | string[] | null;
  options?: SelectOption[];
  min?: number;
  max?: number;
  step?: number;
};

function tr(t: TrainingSchemaTranslate | undefined, key: string, enFallback: string): string {
  return t ? t(key) : enFallback;
}

export function createTrainingFieldGroups(t?: TrainingSchemaTranslate): Array<{ key: TrainingFieldGroup; title: string }> {
  return [
    { key: "data_task", title: tr(t, "training.schemas.groups.data_task", "Training setup") },
    { key: "feature_columns", title: tr(t, "training.schemas.groups.feature_columns", "Feature and column configuration") },
    { key: "advanced", title: tr(t, "training.schemas.groups.advanced", "Training advanced parameters") },
    { key: "publish", title: tr(t, "training.schemas.groups.publish", "Model release") },
  ];
}

export const CLASSIFICATION_METRIC_OPTIONS: SelectOption[] = [
  { label: "AUROC", value: "auroc" },
  { label: "AUPRC", value: "auprc" },
  { label: "F1-score", value: "f1_score" },
  { label: "Accuracy", value: "accuracy" },
  { label: "Precision", value: "precision" },
  { label: "Recall", value: "recall" },
];
export const REGRESSION_METRIC_OPTIONS: SelectOption[] = [
  { label: "MSE", value: "mse" },
  { label: "RMSE", value: "rmse" },
  { label: "MAE", value: "mae" },
  { label: "R2", value: "r2" },
  { label: "PCC", value: "pcc" },
];

export function objectiveMetricOptionsForMlTaskType(mlTaskType: string): SelectOption[] {
  return mlTaskType === "regression" ? REGRESSION_METRIC_OPTIONS : CLASSIFICATION_METRIC_OPTIONS;
}

export function createTrainingFieldSchemas(t?: TrainingSchemaTranslate): TrainingFieldSchema[] {
  return [
    {
      key: "dataset_id",
      label: tr(t, "training.schemas.fields.dataset_id.label", "Dataset"),
      type: "select",
      group: "data_task",
      required: true,
      description: "",
      options: [],
    },
    {
      key: "clinical_task_id",
      label: tr(t, "training.schemas.fields.clinical_task_id.label", "Clinical task"),
      type: "select",
      group: "data_task",
      required: true,
      defaultValue: "mortality_28d",
      description: "",
      options: [
        { label: tr(t, "training.schemas.options.clinical_task.mortality_28d", "Survival outcome"), value: "mortality_28d" },
        { label: tr(t, "training.schemas.options.clinical_task.clinical_efficacy", "Clinical efficacy"), value: "clinical_efficacy" },
        {
          label: tr(t, "training.schemas.options.clinical_task.polymyxin_resistance", "Polymyxin resistance"),
          value: "polymyxin_resistance",
        },
        { label: tr(t, "training.schemas.options.clinical_task.treatment_duration", "Treatment duration"), value: "treatment_duration" },
      ],
    },
    {
      key: "ml_task_type",
      label: tr(t, "training.schemas.fields.ml_task_type.label", "Machine learning task type"),
      type: "select",
      group: "data_task",
      required: true,
      defaultValue: "binary",
      options: [
        { label: tr(t, "training.schemas.options.ml_task_type.binary", "Binary classification"), value: "binary" },
        { label: tr(t, "training.schemas.options.ml_task_type.multiclass", "Multiclass classification"), value: "multiclass" },
        { label: tr(t, "training.schemas.options.ml_task_type.regression", "Regression"), value: "regression" },
      ],
    },
    {
      key: "target_column",
      label: tr(t, "training.schemas.fields.target_column.label", "Target column"),
      type: "select",
      group: "data_task",
      required: true,
      description: "",
    },

    {
      key: "feature_set",
      label: tr(t, "training.schemas.fields.feature_set.label", "Named feature group (optional)"),
      type: "text",
      group: "advanced",
      description: "",
      placeholder: tr(t, "training.schemas.placeholders.feature_set", ""),
    },
    {
      key: "selected_features",
      label: tr(t, "training.schemas.fields.selected_features.label", "Candidate feature pool"),
      type: "multiselect",
      group: "feature_columns",
      description: tr(
        t,
        "training.schemas.fields.selected_features.description",
        "Select variables to enter the feature-screening pool.",
      ),
    },
    {
      key: "final_features",
      label: tr(t, "training.schemas.fields.final_features.label", "Final modeling columns"),
      type: "multiselect",
      group: "feature_columns",
      description: "",
    },
    {
      key: "med_cols",
      label: tr(t, "training.schemas.fields.med_cols.label", "Locked variables"),
      type: "multiselect",
      group: "feature_columns",
      description: tr(
        t,
        "training.schemas.fields.med_cols.description",
        "Locked variables are always included in model training.",
      ),
    },

    {
      key: "model_type",
      label: tr(t, "training.schemas.fields.model_type.label", "Model type"),
      type: "select",
      group: "advanced",
      required: true,
      defaultValue: "xgboost",
      options: [
        { label: tr(t, "training.schemas.options.model_type.xgboost", "XGBoost"), value: "xgboost" },
        { label: tr(t, "training.schemas.options.model_type.lightgbm", "LightGBM"), value: "lightgbm" },
        { label: tr(t, "training.schemas.options.model_type.catboost", "CatBoost"), value: "catboost" },
        { label: tr(t, "training.schemas.options.model_type.random_forest", "Random Forest"), value: "random_forest" },
        { label: tr(t, "training.schemas.options.model_type.logistic_regression", "Logistic Regression"), value: "logistic_regression" },
        { label: tr(t, "training.schemas.options.model_type.svm", "SVM"), value: "svm" },
        { label: tr(t, "training.schemas.options.model_type.knn", "KNN"), value: "knn" },
      ],
    },
    {
      key: "model_name",
      label: tr(t, "training.schemas.fields.model_name.label", "Model display name"),
      type: "text",
      group: "advanced",
      description: "",
    },
    {
      key: "objective_metric",
      label: tr(t, "training.schemas.fields.objective_metric.label", "Primary metric"),
      type: "select",
      group: "advanced",
      required: true,
      defaultValue: "auroc",
      options: CLASSIFICATION_METRIC_OPTIONS,
    },
    {
      key: "primary_metric",
      label: tr(t, "training.schemas.fields.primary_metric.label", "Primary metric (override)"),
      type: "text",
      group: "advanced",
      description: tr(t, "training.schemas.fields.primary_metric.description", "Optional; when blank it aligns with objective_metric"),
    },
    {
      key: "enable_feature_set_search",
      label: tr(t, "training.schemas.fields.enable_feature_set_search.label", "Enable feature-set search"),
      type: "switch",
      group: "advanced",
      defaultValue: false,
      description: "",
    },
    {
      key: "min_features",
      label: tr(t, "training.schemas.fields.min_features.label", "Minimum features"),
      type: "number",
      group: "advanced",
      defaultValue: 1,
      min: 1,
      max: 20,
      step: 1,
    },
    {
      key: "max_features",
      label: tr(t, "training.schemas.fields.max_features.label", "Maximum features"),
      type: "number",
      group: "advanced",
      defaultValue: 10,
      min: 1,
      max: 20,
      step: 1,
    },
    {
      key: "enable_search",
      label: tr(t, "training.schemas.fields.enable_search.label", "Enable hyperparameter search"),
      type: "switch",
      group: "advanced",
      defaultValue: false,
    },
    {
      key: "use_cv_shap",
      label: tr(t, "training.schemas.fields.use_cv_shap.label", "CV-SHAP"),
      type: "switch",
      group: "advanced",
      defaultValue: false,
      description: "",
    },
    {
      key: "index_time",
      label: tr(t, "training.schemas.fields.index_time.label", "Index time"),
      type: "text",
      group: "advanced",
      placeholder: tr(t, "training.schemas.placeholders.index_time", "Optional; blank becomes null"),
      description: tr(t, "training.schemas.fields.index_time.description", "Optional cohort indexing timestamp column name."),
    },
    {
      key: "label_time",
      label: tr(t, "training.schemas.fields.label_time.label", "Label time"),
      type: "text",
      group: "advanced",
      placeholder: tr(t, "training.schemas.placeholders.label_time", "Optional; blank becomes null"),
      description: tr(t, "training.schemas.fields.label_time.description", "Optional outcome labeling timestamp column name."),
    },

    {
      key: "publish_overrides.model_id",
      label: tr(t, "training.schemas.fields.publish_overrides_model_id.label", "Release model ID"),
      type: "text",
      group: "publish",
      placeholder: tr(t, "training.schemas.placeholders.publish_model_id", "Optional"),
    },
    {
      key: "publish_overrides.notes",
      label: tr(t, "training.schemas.fields.publish_overrides_notes.label", "Release notes"),
      type: "textarea",
      group: "publish",
      placeholder: tr(t, "training.schemas.placeholders.publish_notes", "Optional; multi-line notes supported"),
    },
  ];
}

/** Resolved label for `clinical_task_id` using the same option list as the training setup form. */
export function clinicalTaskIdDisplayLabel(
  clinicalTaskId: unknown,
  t?: TrainingSchemaTranslate,
): string {
  const id = String(clinicalTaskId ?? "").trim();
  if (!id) return "";
  for (const schema of createTrainingFieldSchemas(t)) {
    if (schema.key !== "clinical_task_id") continue;
    const opt = schema.options?.find((o) => String(o.value) === id);
    if (opt?.label) return String(opt.label);
  }
  return id;
}

/** Resolved label for `model_type` / algorithm select value (e.g. xgboost → XGBoost). */
export function modelTypeDisplayLabel(modelType: unknown, t?: TrainingSchemaTranslate): string {
  const id = String(modelType ?? "").trim();
  if (!id) return "";
  for (const schema of createTrainingFieldSchemas(t)) {
    if (schema.key !== "model_type") continue;
    const opt = schema.options?.find((o) => String(o.value) === id);
    if (opt?.label) return String(opt.label);
  }
  return id;
}

/** English-resolved defaults for non-Vue callers (e.g. tests). Prefer createTrainingFieldGroups(i18nT) in UI. */
export const TRAINING_FIELD_GROUPS = createTrainingFieldGroups(undefined);

/** English-resolved defaults for non-Vue callers (e.g. tests). Prefer createTrainingFieldSchemas(i18nT) in UI. */
export const TRAINING_FIELD_SCHEMAS = createTrainingFieldSchemas(undefined);
