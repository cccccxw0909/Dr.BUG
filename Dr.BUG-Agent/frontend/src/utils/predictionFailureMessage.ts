import { ApiError } from "../api";

/** Three user-facing categories aligned with canonical backend error codes (message text is not from the server). */
export type PredictionFailureKind = "invalid_input" | "model_task_mismatch" | "execution_failed";

/** Translator injected by callers (e.g. vue-i18n `t`); keeps this module free of `useI18n()`. */
export type Translate = (key: string, values?: Record<string, unknown>) => string;

const KIND_I18N_KEYS: Record<PredictionFailureKind, string> = {
  invalid_input: "predictionFailure.invalidInput",
  model_task_mismatch: "predictionFailure.modelTaskMismatch",
  execution_failed: "predictionFailure.executionFailed",
};

/** Maps backend or historical error_code to a kind (display only; branch logic unchanged). */
export function classifyPredictionFailureKind(code: string): PredictionFailureKind {
  if (code === "PREDICTION_INVALID_INPUT") return "invalid_input";
  if (code === "PREDICTION_MODEL_TASK_MISMATCH") return "model_task_mismatch";
  if (code === "PREDICTION_EXECUTION_FAILED") return "execution_failed";
  if (code === "PREDICTION_BATCH_CHECK_INVALID_INPUT" || code === "PREDICTION_BATCH_RUN_INVALID_INPUT") {
    return "invalid_input";
  }
  if (code === "PREDICTION_MODEL_NOT_FOUND") return "model_task_mismatch";
  if (code === "RECOMMENDATION_INVALID_INPUT" || code.startsWith("REC_")) return "invalid_input";
  return "execution_failed";
}

export function userFacingPredictionFailureMessage(kind: PredictionFailureKind, t: Translate): string {
  return t(KIND_I18N_KEYS[kind]);
}

/** Prediction-related API errors: map by code for ApiError; non-ApiError uses execution-failed copy. */
export function formatPredictionApiError(err: unknown, t: Translate): string {
  if (err instanceof ApiError) {
    return userFacingPredictionFailureMessage(classifyPredictionFailureKind(err.code), t);
  }
  return t(KIND_I18N_KEYS.execution_failed);
}
