/**
 * Pre-submit training validation aligned with trainingPayloadBuilder and backend DomainTrainingPayload semantics.
 * Distinguishes blocking errors from non-blocking warnings.
 */

import type { TrainingFieldGroup } from "../config/trainingSchemas";
import type { Translate } from "./messageSanitizer";
import {
  isNonEmptyString,
  mergeLegacyTrainingAliases,
  missingTrainingParameterKeys,
  missingTrainingPhase1ParameterKeys,
} from "./trainingPayloadBuilder";

export type SchemaValidationMode = "none" | "loading" | "ok" | "fail";

export type TrainingValidationGroupStatus = "ok" | "error" | "warn" | "optional";

export type TrainingValidationInput = {
  /** Normalized payload aligned with backend validation; preferably output from normalizeTrainingPayloadForSubmit. */
  normalizedPayload: Record<string, unknown>;
  /** User-entered original primary_metric before merge; used for empty-value warnings. */
  rawPrimaryMetric?: string;
  /** Raw model_name string entered by the user in the form. */
  rawModelName?: string;
  schemaMode: SchemaValidationMode;
  /** Valid column set when schema mode is ok; used to validate target and feature columns in ok mode. */
  validColumns: Set<string> | null;
  /** Validate Phase 1 only (initial chat card), without requiring model/objective/final_features. */
  phase1Only?: boolean;
  /** When set, user-facing strings use i18n; otherwise English fallbacks are used. */
  t?: Translate;
};

export type TrainingValidationIssue = {
  id: string;
  message: string;
  group?: TrainingFieldGroup;
  fields?: string[];
};

export type TrainingValidationResult = {
  errors: TrainingValidationIssue[];
  warnings: TrainingValidationIssue[];
  fieldErrors: Record<string, string>;
  groupStatus: Record<TrainingFieldGroup, TrainingValidationGroupStatus>;
  canSubmit: boolean;
};

const FIELD_LABEL_EN: Record<string, string> = {
  dataset_id: "Dataset",
  clinical_task_id: "Clinical task",
  ml_task_type: "Machine learning task type",
  target_column: "Target column",
  model_type: "Model type",
  objective_metric: "Primary metric",
  feature_source: "Feature configuration (pool, search, or explanation options)",
  feature_set: "Named feature group",
  selected_features: "Candidate feature pool",
  final_features: "Final modeling columns",
  med_cols: "Locked variables",
  min_features: "Minimum features",
  max_features: "Maximum features",
};

function loc(t: Translate | undefined, key: string, values: Record<string, unknown> | undefined, enFallback: string): string {
  if (t) return t(key, values);
  return enFallback;
}

function fieldDisplayLabel(key: string, t?: Translate): string {
  const i18nKey = `training.validation.fieldLabels.${key}`;
  return loc(t, i18nKey, undefined, FIELD_LABEL_EN[key] || key);
}

export function analyzeTrainingSubmission(input: TrainingValidationInput): TrainingValidationResult {
  const p = mergeLegacyTrainingAliases(input.normalizedPayload);
  const errors: TrainingValidationIssue[] = [];
  const warnings: TrainingValidationIssue[] = [];
  const fieldErrors: Record<string, string> = {};
  const tt = input.t;

  const pushError = (id: string, message: string, group?: TrainingFieldGroup, fields?: string[]) => {
    errors.push({ id, message, group, fields });
    if (fields) {
      for (const f of fields) {
        if (!fieldErrors[f]) fieldErrors[f] = message;
      }
    }
  };
  const pushWarn = (id: string, message: string, group?: TrainingFieldGroup) => {
    warnings.push({ id, message, group });
  };

  const miss = input.phase1Only ? missingTrainingPhase1ParameterKeys(p, true) : missingTrainingParameterKeys(p, true);
  for (const k of miss) {
    const msg =
      k === "feature_source"
        ? loc(
            tt,
            "training.validation.errors.featureSourceRequired",
            undefined,
            "Insufficient feature source: provide final_features, selected_features, or feature_set, or enable feature-set search or use_cv_shap (med_cols alone does not count).",
          )
        : loc(tt, "training.validation.errors.missingRequired", { field: fieldDisplayLabel(k, tt) }, `Missing required: ${fieldDisplayLabel(k, undefined)}`);
    const group: TrainingFieldGroup =
      k === "dataset_id" || k === "clinical_task_id" || k === "ml_task_type" || k === "target_column"
        ? "data_task"
        : k === "feature_source"
          ? "feature_columns"
          : "advanced";
    const fields =
      k === "feature_source"
        ? ["feature_set", "selected_features", "final_features", "enable_feature_set_search", "use_cv_shap"]
        : [k];
    pushError(`req_${k}`, msg, group, fields);
  }

  const enableFs = Boolean(p.enable_feature_set_search);
  const minF = Number(p.min_features ?? 1);
  const maxF = Number(p.max_features ?? 10);
  if (enableFs && minF > maxF) {
    pushError(
      "min_max_feat",
      loc(
        tt,
        "training.validation.errors.minMaxFeatureOrder",
        undefined,
        "Feature-set search is on: minimum features cannot exceed maximum features (min_features / max_features).",
      ),
      "advanced",
      ["min_features", "max_features"],
    );
  } else if (enableFs && (minF < 1 || maxF > 20 || minF > 20 || maxF < 1)) {
    pushWarn(
      "feat_bounds",
      loc(
        tt,
        "training.validation.warnings.featBounds",
        undefined,
        "Feature counts are near or outside the usual contract range (1–20); please confirm this is intended.",
      ),
      "advanced",
    );
  }

  const tc = String(p.target_column || "").trim();
  const valid = input.validColumns;

  if (input.schemaMode === "fail") {
    pushWarn(
      "schema_fail",
      loc(
        tt,
        "training.validation.warnings.schemaFail",
        undefined,
        "Dataset columns failed to load: target and feature columns cannot be validated against the schema automatically—manual entry errors are possible.",
      ),
      "feature_columns",
    );
  } else if (input.schemaMode === "loading" && isNonEmptyString(p.dataset_id) && tc) {
    pushWarn(
      "schema_loading",
      loc(
        tt,
        "training.validation.warnings.schemaLoading",
        undefined,
        "Columns are loading: once ready, target and selected features will be checked against the dataset.",
      ),
      "data_task",
    );
  } else if (input.schemaMode === "ok" && valid && valid.size > 0) {
    if (tc && !valid.has(tc)) {
      pushError(
        "target_not_in_schema",
        loc(
          tt,
          "training.validation.errors.targetNotInSchema",
          undefined,
          "Target column is not in the current dataset schema—please pick again (target_column).",
        ),
        "data_task",
        ["target_column"],
      );
    }
    const colKeys = input.phase1Only
      ? (["selected_features", "med_cols"] as const)
      : (["selected_features", "final_features", "med_cols"] as const);
    for (const key of colKeys) {
      const arr = Array.isArray(p[key]) ? (p[key] as string[]) : [];
      const bad = arr.filter((c) => !valid.has(String(c)));
      if (bad.length) {
        const colsPreview = `${bad.slice(0, 5).join(", ")}${bad.length > 5 ? "…" : ""}`;
        const message = loc(
          tt,
          "training.validation.errors.columnsNotInSchema",
          { fieldLabel: fieldDisplayLabel(key, tt), columns: colsPreview },
          `${fieldDisplayLabel(key, undefined)} lists columns not present in the current schema: ${colsPreview}`,
        );
        pushError(`bad_${key}`, message, "feature_columns", [key]);
      }
    }
  }

  const fs = isNonEmptyString(p.feature_set);
  const fin = Array.isArray(p.final_features) && (p.final_features as unknown[]).length > 0;
  const sel = Array.isArray(p.selected_features) && (p.selected_features as unknown[]).length > 0;

  if (!input.phase1Only) {
    if (fin && fs) {
      pushWarn(
        "feat_priority",
        loc(
          tt,
          "training.validation.warnings.featPriority",
          undefined,
          "Both final modeling columns (final_features) and a named feature group (feature_set) are set: semantics prefer final columns; execution order follows the backend.",
        ),
        "feature_columns",
      );
    }
    if (sel && !fin) {
      pushWarn(
        "pool_only",
        loc(
          tt,
          "training.validation.warnings.poolOnly",
          undefined,
          "Candidate pool (selected_features) is set but final modeling columns are empty: this reflects a pool only, not the final training column plan.",
        ),
        "feature_columns",
      );
    }
  } else if (sel) {
    pushWarn(
      "pool_only_phase1",
      loc(
        tt,
        "training.validation.warnings.poolOnlyPhase1",
        undefined,
        "Candidate pool is filled; the system will recommend final modeling columns after screening, and you will confirm them in chat before training.",
      ),
      "feature_columns",
    );
  }

  if (!input.phase1Only) {
    const rpm = String(input.rawPrimaryMetric ?? "").trim();
    if (!rpm && isNonEmptyString(p.objective_metric)) {
      pushWarn(
        "primary_default",
        loc(
          tt,
          "training.validation.warnings.primaryDefault",
          undefined,
          "Primary metric override (primary_metric) is blank: after submit it aligns with objective_metric (per current contract).",
        ),
        "advanced",
      );
    }

    const rmn = String(input.rawModelName ?? "").trim();
    if (!rmn) {
      pushWarn(
        "model_name_empty",
        loc(
          tt,
          "training.validation.warnings.modelNameEmpty",
          undefined,
          "Model display name (model_name) is empty: the executor may map from model_type.",
        ),
        "advanced",
      );
    }

    const po = p.publish_overrides;
    const hasPublish =
      (po &&
        typeof po === "object" &&
        (isNonEmptyString((po as Record<string, unknown>).model_id) ||
          isNonEmptyString((po as Record<string, unknown>).notes))) ||
      false;
    if (!hasPublish) {
      pushWarn(
        "publish_skip",
        loc(
          tt,
          "training.validation.warnings.publishSkip",
          undefined,
          "No publish overrides (publish_overrides): this does not block submitting the training job.",
        ),
      );
    }
  }

  const groupStatus: Record<TrainingFieldGroup, TrainingValidationGroupStatus> = {
    data_task: "ok",
    feature_columns: "ok",
    advanced: "ok",
    publish: "optional",
  };

  const bump = (g: TrainingFieldGroup, kind: "error" | "warn") => {
    const cur = groupStatus[g];
    if (kind === "error") groupStatus[g] = "error";
    else if (cur !== "error") groupStatus[g] = "warn";
  };

  for (const e of errors) {
    if (e.group) bump(e.group, "error");
  }
  for (const w of warnings) {
    if (w.group) bump(w.group, "warn");
  }
  groupStatus.publish = "optional";

  const canSubmit = errors.length === 0;

  return { errors, warnings, fieldErrors, groupStatus, canSubmit };
}

export function groupStatusShort(st: TrainingValidationGroupStatus, t?: Translate): string {
  if (st === "error") return loc(t, "training.validation.groupStatus.error", undefined, "[Missing/errors]");
  if (st === "warn") return loc(t, "training.validation.groupStatus.warn", undefined, "[Warnings]");
  if (st === "optional") return loc(t, "training.validation.groupStatus.optional", undefined, "[Optional]");
  return loc(t, "training.validation.groupStatus.ok", undefined, "[Done]");
}
