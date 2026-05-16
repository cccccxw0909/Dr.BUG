export type PendingAction = {
  pending_action_id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: string;
  expires_at: string;
  superseded_by?: string | null;
  executed_job_id?: string | null;
  /** Backend pending isolation bucket; supersede occurs only within the same bucket. */
  scope_key?: string;
};

export type ChatTurnData = {
  assistant_message: string;
  route:
    | "llm_chat"
    | "deterministic_action"
    | "tool_query"
    | "concise_status"
    | "fallback_template"
    | "prediction_entry"
    | "workflow_guidance"
    | "welcome_policy"
    | "mcp_context_query"
    | "mcp_latest_training_summary"
    | "pending_confirm";
  recognized_action: string | null;
  completed_params: Record<string, unknown>;
  missing_fields: string[];
  can_confirm: boolean;
  pending_confirmation: PendingAction | null;
  /** Internal tool names, hidden from the UI by default. */
  tool_names?: string[];
  /** User-readable categories of system information queried in this turn. */
  readonly_query_labels?: string[];
  /** Backend routing decision trace for debugging and observability. */
  route_decision_trace?: Record<string, unknown>;
  /**
   * Session-local message copy: set by the frontend only after postConfirm succeeds and this card is updated.
   * Do not infer success from whether pending is empty.
   */
  confirmation_outcome?: "success" | null;
  confirmed_pending_action_id?: string | null;
};

export type TrainingWorkflowPhase =
  | "train_phase3_feature_confirm_pending"
  | "train_phase4_train_config_pending"
  | "train_phase5_publish_pending";

export type TrainingWorkflowActionStatus = "pending" | "submitted" | "superseded";

/**
 * Pending confirmation card data for Phase 3/4/5 in chat; must be bound to job_id.
 * This structure is a frontend mapping of task status, not a new state machine.
 */
export type TrainingWorkflowPendingActionData = {
  kind: "training_workflow_pending_action";
  /** Unique identifier used to avoid inserting duplicate cards. */
  card_id: string; // `${job_id}:${phase}`
  job_id: string;
  phase: TrainingWorkflowPhase;
  status: TrainingWorkflowActionStatus;
  created_at_iso: string;

  /** Read-only snapshot from task.params / task.result_summary for display. */
  params_snapshot?: Record<string, unknown>;
  result_summary?: Record<string, unknown>;

  /** Phase3 */
  suggested_final_features?: string[];
  med_cols?: string[];
  candidate_pool_columns?: string[];

  /** Phase4 */
  ml_task_type?: string;

  /** Phase5 */
  model_id?: string | null;
  key_metrics?: Record<string, unknown>;
  artifacts?: Record<string, string>;
};

export type TaskStatusData = {
  task: {
    id: string;
    status: string;
    progress: number;
    current_stage: string;
    message: string;
    error_message?: string | null;
    /** Aligns with backend TaskStatusView.job_type for routing training/prediction copy and cards during polling. */
    job_type?: string;
    created_at?: string;
    started_at?: string | null;
    completed_at?: string | null;
  };
};

export type TaskItem = {
  id: string;
  status: string;
  progress: number;
  current_stage: string;
  message?: string;
  /** Backend JobType, such as train_model. */
  job_type?: string;
  params?: Record<string, unknown>;
  error_message?: string | null;
  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  result_summary?: Record<string, unknown> | null;
  artifacts?: Record<string, string>;
};

export type TaskDetailData = {
  task: TaskItem & Record<string, unknown>;
  task_summary?: Record<string, unknown> | null;
  logs: Array<Record<string, unknown>>;
  artifacts: Record<string, string>;
};

export type ApiErrorPayload = {
  status: "error";
  message: string;
  error_code: string;
};

export type DatasetMeta = {
  id: string;
  name: string;
  file_name: string;
  file_type: string;
  created_at: string;
  description?: string;
  available_tasks?: string[];
};

/** Keep the same order as backend TREATMENT_FIELD_NAMES for regimen-library form iteration. */
export const REGIMEN_TREATMENT_FIELD_KEYS = [
  "colistin_cms_daily_freq",
  "polymyxin_b_daily_freq",
  "colistin_sulfate_daily_freq",
  "carbapenem_daily_dose",
  "sulbactam_daily_dose",
  "tigecycline_daily_dose",
  "minocycline_daily_dose",
  "vancomycin_daily_dose",
  "eravacycline_daily_dose",
  "aminoglycoside_daily_dose",
] as const;

export type RegimenTreatmentFieldKey = (typeof REGIMEN_TREATMENT_FIELD_KEYS)[number];

export type RegimenTreatmentValues = Record<RegimenTreatmentFieldKey, number>;

export type RegimenRecord = {
  regimen_id: string;
  regimen_name: string;
  enabled: boolean;
  notes: string | null;
  treatment_values: RegimenTreatmentValues;
  created_at?: string;
  updated_at?: string;
};

export type DatasetColumnInfo = {
  name: string;
  dtype: string;
  is_numeric: boolean;
};

export type DatasetSchemaInfo = {
  dataset_id: string;
  columns: DatasetColumnInfo[];
};

export type DatasetPreviewInfo = {
  dataset_id: string;
  row_count: number;
  column_count: number;
  full_column_count?: number;
  column_subset_applied?: boolean;
  target_column?: string | null;
  numeric_column_count?: number;
  categorical_column_count?: number;
  missing_overview?: Array<{ column: string; missing_count: number }>;
  label_distribution?: Record<string, number>;
  rows: Array<Record<string, unknown>>;
};

export type ModelMeta = {
  model_id: string;
  /** User-facing name from registry (release/training); matches prediction picker. */
  display_name?: string;
  model_name?: string;
  name?: string;
  task_name?: string;
  task_type?: string;
  version?: string;
  model_path?: string;
  required_features?: string[];
  feature_order?: string[];
  notes?: string;
  /** Extension fields for training registration and related data, aligned with backend ModelItem extras. */
  source_job_id?: string;
  dataset_id?: string;
  clinical_task_id?: string;
  ml_task_type?: string;
  target_column?: string;
  objective_metric?: string;
  model_type?: string;
  feature_set?: string;
  is_published?: boolean;
  published_at?: string;
  created_at?: string;
  updated_at?: string;
  key_metrics?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  preprocess_config?: Record<string, unknown>;
  selected_features?: unknown[];
  final_features?: unknown[];
};

/** Aligns with backend DomainTrainingPayload JSON; nested publish_overrides is optional. */
export type DomainTrainingParams = {
  dataset_id: string;
  clinical_task_id: string;
  ml_task_type: string;
  target_column: string;
  med_cols?: string[];
  selected_features?: string[];
  final_features?: string[];
  enable_feature_set_search?: boolean;
  min_features?: number;
  max_features?: number;
  enable_search?: boolean;
  use_cv_shap?: boolean;
  index_time?: string | null;
  label_time?: string | null;
  model_type: string;
  model_name?: string | null;
  feature_set?: string | null;
  objective_metric: string;
  primary_metric?: string | null;
  publish_overrides?: { model_id?: string | null; notes?: string | null };
};

export type NavKey = "workbench" | "tasks" | "datasets" | "models" | "history";

export type SessionItem = {
  id: string;
  created_at: string;
  /** Ordinal used with `app.session.newSessionTitle` when `customTitle` is unset. */
  defaultSlot?: number;
  /** Optional user-defined session label (persisted). */
  customTitle?: string;
  /**
   * When true, Workbench keeps the static welcome intro (title, capabilities, boundaries) below the first user turn.
   * Not part of session messages; set on the first user message from an empty session.
   */
  workbenchWelcomeIntroPinned?: boolean;
};

export type TaskResultCardData = {
  /** When set, drives failure vs success actions; legacy cards may omit and rely on title heuristics. */
  variant?: "completed" | "failed";
  /** Backend job status when known (preferred over parsing titles for failure). */
  status?: string;
  title: string;
  metrics?: Record<string, string | number>;
  nextStep?: string;
  errorReason?: string;
  jobId?: string;
  /** Backend job_type (e.g. train_model); drives primary action labels only. */
  jobType?: string;
  modelId?: string;
  modelPublished?: boolean;
  artifacts?: Record<string, string>;
  resultSummary?: Record<string, unknown>;
  /** Train-model completion: human-readable summary rows (no raw backend field names). */
  trainingCompletedPresentation?: {
    /** Deterministic receipt paragraphs shown by default (no LLM). Optional LLM polish may replace later with same fact bounds + deterministic fallback. */
    receiptParagraphs?: string[];
    /** Same paragraphs as `receiptParagraphs`, with safe HTML (e.g. primary metric in &lt;strong&gt;) for chat receipt rendering. */
    receiptParagraphsHtml?: string[];
    /** @deprecated Primary metric highlight is embedded in `receiptParagraphsHtml` paragraph 2. */
    receiptPrimaryHighlight?: { label: string; value: string };
    /** When true, show Phase4 candidate-model CV table after narrative (not final model metrics). */
    showCandidateModelComparison?: boolean;
    /** Legacy structured card rows; unused for modern training receipt (prefer narrative + task page). */
    summaryRows?: Array<{ label: string; value: string }>;
    /** Legacy feature chips; unused for modern training receipt. */
    featureSection?: {
      title: string;
      chips: Array<{ display: string; raw: string }>;
      previewLimit: number;
    };
  };
};

/** Training job creation receipt shown in chat (frontend session only; not persisted). */
export type TrainingJobReceiptData = {
  /** pending_action_id associated with this successful confirm. */
  pending_action_id: string;
  title: string;
  job_id: string;
  task_kind_label: string;
  backend_assistant_message?: string;
  task_status?: string;
  task_message?: string;
  summary_lines: string[];
  merged_payload_snapshot: Record<string, unknown>;
  next_hint?: string;
};

/** Registry model summary (/prediction/models), used by the workbench prediction flow. */
export type PredictionModelListItem = {
  model_id: string;
  /** Human-readable name; aligns with Models page Basic info (display_name / model_name / task_name / model_id). */
  display_name: string;
  model_name?: string | null;
  /** Registry name alias when present (optional duplicate of display). */
  name?: string | null;
  task_name: string;
  /** Estimator only (e.g. lightgbm); never ML problem type like binary. */
  algorithm?: string | null;
  /** Legacy field: same as algorithm when set; empty when unknown (not ML task kind). */
  model_type: string;
  clinical_task_id?: string;
  /** Canonical backend task key (clinical_efficacy, survival_outcome, …). Prefer over string heuristics. */
  task_key?: string;
  model_kind?: string;
  model_family?: string | null;
  version?: string | null;
  published_at?: string | null;
  registered_at?: string | null;
  released_at?: string | null;
  feature_count?: number;
  required_features?: string[];
  status?: string;
  /** When false, hide from “released model” pickers; omit/true treated as published (API backward compatibility). */
  is_published?: boolean;
  metadata?: Record<string, unknown>;
  package_path?: string;
  registry_path?: string;
  has_schema: boolean;
  has_metadata: boolean;
  supports_shap: boolean;
  summary?: string | null;
};

/** Single-field schema aligned with the fields item from backend /prediction/models/{id}/schema. */
export type PredictionFieldSchema = {
  name: string;
  /** Readable name from the backend or registry; when empty or placeholder, frontend `featureDisplayName` infers an English-first display name. */
  label: string;
  type: "float" | "int" | "binary" | "categorical" | "string";
  required: boolean;
  default?: unknown;
  options?: unknown[] | null;
  unit?: string | null;
  reference_range?: string | null;
  min?: unknown;
  max?: unknown;
  description?: string | null;
  group?: string | null;
};

export type PredictionSchemaPayload = {
  model_id: string;
  display_name: string;
  task_name: string;
  model_type: string;
  feature_order: string[];
  fields: PredictionFieldSchema[];
  metadata: Record<string, unknown>;
};

export type PredictionFlowStep = "idle" | "select_model" | "fill_features";

/** SHAP explanation attached to single-sample prediction as an extension field of POST /prediction/single. */
export type PredictionExplanationBlock = {
  supported: boolean;
  summary_text: string;
  top_features: Array<{ name: string; direction: "increase" | "decrease" }>;
  waterfall_image_url: string | null;
  force_image_url: string | null;
  warnings: string[];
};

/** Successful POST /prediction/single response aligned with backend inference. */
export type PredictionSingleResponse = {
  ok: boolean;
  model_id: string;
  display_name: string;
  task_name: string;
  prediction_type: "classification" | "regression";
  predicted_label?: string | null;
  predicted_probability?: number | null;
  predicted_value?: number | null;
  label_display: string;
  outcome_display: string;
  /** Main workbench copy: probability line as a short English sentence for label-aligned display. */
  probability_display_line?: string;
  /** Main workbench copy: label line. */
  label_display_line?: string;
  feature_values_used: Record<string, unknown>;
  /**
   * Optional: attached client-side when embedding chat results so preprocessing notes can show schema labels.
   */
  feature_schema_fields?: PredictionFieldSchema[];
  warnings: string[];
  timestamp: string;
  session_id?: string | null;
  risk_score?: number | null;
  /** Generated by the backend after successful prediction; when generation fails, supported=false and the main result is unaffected. */
  explanation?: PredictionExplanationBlock | null;
  /** Optional backend value returned after writing history, used for technical traceability. */
  history_record_id?: string | null;
  job_id?: string | null;
  task_id?: string | null;
  /**
   * Compatibility whitelist below, redundant with explanation. Presentation code must prefer `explanation`; do not treat these as a second formal contract.
   */
  explanation_supported?: boolean | null;
  shap_supported?: boolean | null;
  waterfall_plot_url?: string | null;
  force_plot_url?: string | null;
  top_positive_drivers?: Array<{ name: string }>;
  top_negative_drivers?: Array<{ name: string }>;
  /** Optional frontend title for the asynchronous prediction task completion card. */
  ui_headline?: string;
  ui_subheadline?: string;
};

/** Single-sample prediction form card in the chat stream. */
export type PredictionFormCardStatus = "editing" | "submitted" | "cancelled";

export type PredictionFormSubmittedSummary = {
  displayName: string;
  modelId: string;
  fieldCount: number;
  filledCount: number;
  previewFields: Array<{ name: string; label: string; value: string }>;
  /** Clinician-readable indicator that this is a single-sample prediction. */
  mode?: "single";
  taskName?: string;
};

/** Chat: inserted after confirm, before the result message (submission details card). */
export type PredictionSubmittedSummaryPayload = {
  summary_id: string;
  status: "pending" | "done" | "failed";
  model_display_name: string;
  model_id: string;
  task_name: string;
  mode: "single";
  submitted_at: string;
  /** Current workbench dataset name or related context; may be empty. */
  workspace_context?: string | null;
  /** Schema order, including empty values displayed as —. */
  field_rows: Array<{ name: string; label: string; value: string }>;
  error_message?: string | null;
};

/** Prediction workspace task bucket (UI labels map via i18n). */
export type PredictionTaskKey = "survival" | "efficacy" | "resistance" | "duration";

export type PredictionFormCardData = {
  kind: "prediction_form_card";
  card_id: string;
  status: PredictionFormCardStatus;
  models: PredictionModelListItem[];
  modelsLoading: boolean;
  modelsError: string;
  /** null = user must choose a prediction task */
  selectedPredictionTaskKey: PredictionTaskKey | null;
  selectedModelId: string | null;
  schema: PredictionSchemaPayload | null;
  schemaLoading: boolean;
  schemaError: string;
  formValues: Record<string, unknown>;
  predictRunning: boolean;
  submitError?: string;
  closedAt?: string;
  submittedSummary?: PredictionFormSubmittedSummary;
  /** Retained with the card after success for summary display. */
  result?: PredictionSingleResponse | null;
  /** Current workbench model for recommendation display only; must not be treated as the selected model_id. */
  recommendedModelId?: string | null;
  recommendedModelLabel?: string | null;
  /** Form entry or batch upload. */
  active_panel?: "form" | "batch";
  batch?: {
    status: "editing" | "checked" | "submitted" | "finished" | "cancelled";
    fileName: string;
    checkRunning: boolean;
    runRunning: boolean;
    runStartedAt?: string | null;
    checkError?: string;
    runError?: string;
    checkResult?: BatchFieldCheckResponse | null;
    submittedSummary?: {
      modelId: string;
      modelName: string;
      fileName: string;
      canRun: boolean;
      matchedCount: number;
      missingCount: number;
      extraCount: number;
    };
    result?: BatchPredictionRunResponse | null;
    closedAt?: string;
  };
};

/** Actions sent from the form card to App. */
export type PredictionFormChatAction =
  | { action: "selectPredictionTask"; cardId: string; taskKey: PredictionTaskKey | null }
  | { action: "selectModel"; cardId: string; modelId: string | null }
  | { action: "loadSchema"; cardId: string }
  | { action: "updateValue"; cardId: string; name: string; value: unknown }
  | { action: "submit"; cardId: string }
  | { action: "cancel"; cardId: string }
  | { action: "setActivePanel"; cardId: string; panel: "form" | "batch" }
  | { action: "batchSelectModel"; cardId: string; modelId: string | null }
  | { action: "batchSetFile"; cardId: string; file: File | null }
  | { action: "batchCheck"; cardId: string }
  | { action: "batchRun"; cardId: string }
  | { action: "batchCancel"; cardId: string };

/** recommendation.json artifact produced by POST /recommendation/jobs for single-patient survival-benefit recommendation. */
/** Regimen fragment in recommendation results, including regimen-library treatment_values written by the backend artifact. */
export type RecommendationRegimenResultRow = {
  regimen_id?: string;
  regimen_name?: string;
  rank?: number;
  predicted_probability?: number;
  treatment_values?: Record<string, number> | null;
};

export type SurvivalRecommendationResult = {
  /** Task row id (`job_*`) for navigation to Tasks / context binding; not part of artifact JSON. */
  job_id?: string;
  task?: string;
  mode?: string;
  score_direction?: string;
  model_id: string;
  /** Non-empty when observed_regimen is provided in the request; null when no comparison was run. */
  observed_regimen?: Record<string, number> | null;
  observed_prediction_probability?: number;
  recommended_top1_regimen?: RecommendationRegimenResultRow;
  recommended_top1_probability?: number;
  delta_probability_top1?: number;
  top_candidates?: RecommendationRegimenResultRow[];
  disclaimer?: string;
};

export type RecommendationWorkflowCardStatus =
  | "editing"
  | "submitting"
  | "polling"
  | "completed"
  | "failed"
  | "cancelled";

export type RecommendationWorkflowCardData = {
  kind: "recommendation_workflow_card";
  card_id: string;
  status: RecommendationWorkflowCardStatus;
  models: PredictionModelListItem[];
  modelsLoading: boolean;
  modelsError: string;
  selectedModelId: string | null;
  schema: PredictionSchemaPayload | null;
  schemaLoading: boolean;
  schemaError: string;
  formValues: Record<string, unknown>;
  /** Advanced option filled when comparing with current therapy; observed_regimen is not submitted by default. */
  observedTreatmentValues: RegimenTreatmentValues;
  /** Whether the compare-with-current-therapy section is expanded; submit observed_regimen only when true. */
  observedCompareExpanded: boolean;
  predictRunning: boolean;
  submitError?: string;
  jobId?: string | null;
  pollError?: string;
  closedAt?: string;
  recommendedModelId?: string | null;
  recommendedModelLabel?: string | null;
  enabledRegimenCount: number;
  regimensLoading: boolean;
  regimensError: string;
};

export type RecommendationWorkflowChatAction =
  | { action: "selectModel"; cardId: string; modelId: string | null }
  | { action: "loadSchema"; cardId: string }
  | { action: "updateValue"; cardId: string; name: string; value: unknown }
  | { action: "updateObservedTreatment"; cardId: string; key: RegimenTreatmentFieldKey; value: number }
  | { action: "setObservedCompareExpanded"; cardId: string; expanded: boolean }
  | { action: "submit"; cardId: string }
  | { action: "cancel"; cardId: string }
  | { action: "openRegimenManagement" };

export type BatchFieldCheckResponse = {
  model_id: string;
  file_name: string;
  total_columns: number;
  matched_fields: string[];
  missing_fields: string[];
  extra_fields: string[];
  required_missing_fields: string[];
  can_run: boolean;
  warnings: string[];
};

export type BatchPredictionRunResponse = {
  model_id: string;
  display_name?: string;
  task_name: string;
  file_name: string;
  total_rows: number;
  succeeded_rows: number;
  failed_rows: number;
  download_url: string;
  timestamp: string;
  warnings: string[];
  field_check: BatchFieldCheckResponse;
  /** One-line summary that takes precedence over frontend fallback; do not mix it with structured result_summary. */
  summary_text?: string;
};

export type PredictionHistoryListItem = {
  record_id: string;
  type: "single" | "batch";
  timestamp: string;
  task_name: string;
  model_id: string;
  display_name: string;
  summary: string;
};

export type PredictionHistorySingleRecord = {
  record_id: string;
  type: "single";
  timestamp: string;
  session_id?: string | null;
  task_name: string;
  model_id: string;
  display_name: string;
  predicted_label?: string | null;
  predicted_value?: number | null;
  predicted_probability?: number | null;
  summary_text: string;
  top_features: Array<{ name: string; direction: "increase" | "decrease" }>;
  explanation_supported: boolean;
  waterfall_image_url?: string | null;
  force_image_url?: string | null;
  input_summary?: Record<string, unknown>;
  warnings: string[];
};

export type PredictionHistoryBatchRecord = {
  record_id: string;
  type: "batch";
  timestamp: string;
  session_id?: string | null;
  task_name: string;
  model_id: string;
  display_name: string;
  file_name: string;
  total_rows: number;
  succeeded_rows: number;
  failed_rows: number;
  download_url: string;
  warnings: string[];
  field_check_summary?: {
    matched_count: number;
    missing_count: number;
    extra_count: number;
    required_missing_fields: string[];
  };
};

export type PredictionHistoryRecord = PredictionHistorySingleRecord | PredictionHistoryBatchRecord;

export type BatchPredictionCardStatus = "editing" | "checked" | "submitted" | "finished" | "cancelled";

export type BatchPredictionCardData = {
  kind: "batch_prediction_card";
  card_id: string;
  status: BatchPredictionCardStatus;
  models: PredictionModelListItem[];
  modelsLoading: boolean;
  modelsError: string;
  selectedModelId: string | null;
  fileName: string;
  checkRunning: boolean;
  runRunning: boolean;
  runStartedAt?: string | null;
  checkError?: string;
  runError?: string;
  checkResult?: BatchFieldCheckResponse | null;
  submittedSummary?: {
    modelId: string;
    modelName: string;
    fileName: string;
    canRun: boolean;
    matchedCount: number;
    missingCount: number;
    extraCount: number;
  };
  result?: BatchPredictionRunResponse | null;
  closedAt?: string;
};

export type BatchPredictionChatAction =
  | { action: "selectModel"; cardId: string; modelId: string | null }
  | { action: "setFile"; cardId: string; file: File | null }
  | { action: "check"; cardId: string }
  | { action: "run"; cardId: string }
  | { action: "cancel"; cardId: string };

/** @deprecated Prediction forms have moved into the predictionFormCard chat message. */
export type PredictionWorkbenchState = {
  active: boolean;
  step: PredictionFlowStep;
  models: PredictionModelListItem[];
  modelsLoading: boolean;
  modelsError: string;
  selectedModelId: string | null;
  schema: PredictionSchemaPayload | null;
  schemaLoading: boolean;
  schemaError: string;
  formValues: Record<string, unknown>;
  predictRunning: boolean;
  lastResult: PredictionSingleResponse | null;
};

