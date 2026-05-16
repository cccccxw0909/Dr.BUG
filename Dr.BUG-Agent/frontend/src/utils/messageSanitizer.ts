/**
 * Lightweight normalization for backend messages / warnings / headlines.
 * Unknown text is returned unchanged.
 * When Translate is provided, mapped lines use i18n keys under pages.history.warnings.
 * This is not general free-text translation.
 */

import {
  RE_PREFIX_PREDICTION_COMPLETED,
  RE_PREFIX_RECOMMENDATION_COMPLETED,
  RE_PREFIX_TRAINING_COMPLETED,
  RE_STATE_MACHINE_RECOVERY,
  ZH_STATUS_ABORTED_EXACT,
  ZH_STATUS_CANCELED_EXACT,
  ZH_STATUS_COMPLETED_EXACT,
  ZH_STATUS_FAILED_EXACT,
} from "../i18n/lexicons/zhMessageSanitizer";

export type Translate = (key: string, values?: Record<string, unknown>) => string;

const EXACT_LOWER_TO_KEY: Record<string, string> = {
  "prediction completed": "pages.history.warnings.predictionCompleted",
  "training completed": "pages.history.warnings.trainingCompleted",
  "recommendation completed": "pages.history.warnings.recommendationCompleted",
  completed: "pages.history.warnings.statusCompleted",
  success: "pages.history.warnings.statusCompleted",
  succeeded: "pages.history.warnings.statusCompleted",
  failed: "pages.history.warnings.statusFailed",
  canceled: "pages.history.warnings.statusCanceled",
  cancelled: "pages.history.warnings.statusCanceled",
};

/** English fallbacks when no translator is passed (backward compatible call sites). */
const EN_FALLBACK: Record<string, string> = {
  "pages.history.warnings.predictionCompleted": "Prediction completed",
  "pages.history.warnings.trainingCompleted": "Training completed",
  "pages.history.warnings.recommendationCompleted": "Recommendation completed",
  "pages.history.warnings.statusCompleted": "Completed",
  "pages.history.warnings.statusFailed": "Failed",
  "pages.history.warnings.statusCanceled": "Canceled",
  "pages.history.warnings.predictionCompletedWithRest": "Prediction completed ({rest})",
  "pages.history.warnings.trainingCompletedWithRest": "Training completed ({rest})",
  "pages.history.warnings.recommendationCompletedWithRest": "Recommendation completed ({rest})",
  "pages.history.warnings.stateMachineRecoveryFailed":
    "State machine recovery failed. Please check logs in task details.",
  "pages.history.warnings.jobStatusUpdated": "Task status updated. Check the task list or details.",
};

function tr(t: Translate | undefined, key: string, values?: Record<string, unknown>): string {
  if (t) return t(key, values);
  if (values) {
    let s = EN_FALLBACK[key] ?? "";
    for (const [vk, vv] of Object.entries(values)) {
      s = s.replace(new RegExp(`\\{${vk}\\}`, "g"), String(vv));
    }
    return s;
  }
  return EN_FALLBACK[key] ?? "";
}

function trimOrEmpty(s: string): string {
  return s.trim();
}

/**
 * Legacy status tails often repeat brackets already present in i18n templates, e.g.
 * a Chinese "training completed (foo)" line or "Prediction completed (foo)" → rest should be "foo" not "(foo)".
 */
export function normalizeLegacyStatusRest(s: string): string {
  let x = trimOrEmpty(s).replace(/^[\uFF1A:]\s*/, "");
  for (;;) {
    x = trimOrEmpty(x);
    if (x.length >= 2 && ((x.startsWith("(") && x.endsWith(")")) || (x.startsWith("\uFF08") && x.endsWith("\uFF09")))) {
      x = x.slice(1, -1);
      continue;
    }
    break;
  }
  return trimOrEmpty(x);
}

/** Single-line or first-line: whole-string match or prefix rules for legacy backend status text. */
export function sanitizeUserFacingLine(input: string | null | undefined, t?: Translate): string {
  if (input == null) return "";
  const raw = String(input).trim();
  if (!raw) return "";

  const low = raw.toLowerCase();
  const exactKey = EXACT_LOWER_TO_KEY[low];
  if (exactKey) {
    return t ? t(exactKey) : tr(undefined, exactKey);
  }

  // Legacy backend status lines (Chinese). Match only; user-facing text comes from i18n / EN_FALLBACK.
  if (raw === ZH_STATUS_COMPLETED_EXACT) {
    return t ? t("pages.history.warnings.statusCompleted") : tr(undefined, "pages.history.warnings.statusCompleted");
  }
  if (raw === ZH_STATUS_FAILED_EXACT) {
    return t ? t("pages.history.warnings.statusFailed") : tr(undefined, "pages.history.warnings.statusFailed");
  }
  if (raw === ZH_STATUS_CANCELED_EXACT || raw === ZH_STATUS_ABORTED_EXACT) {
    return t ? t("pages.history.warnings.statusCanceled") : tr(undefined, "pages.history.warnings.statusCanceled");
  }
  if (RE_PREFIX_PREDICTION_COMPLETED.test(raw)) {
    const rest = normalizeLegacyStatusRest(raw.replace(RE_PREFIX_PREDICTION_COMPLETED, ""));
    return rest
      ? t
        ? t("pages.history.warnings.predictionCompletedWithRest", { rest })
        : tr(undefined, "pages.history.warnings.predictionCompletedWithRest", { rest })
      : t
        ? t("pages.history.warnings.predictionCompleted")
        : tr(undefined, "pages.history.warnings.predictionCompleted");
  }
  if (RE_PREFIX_TRAINING_COMPLETED.test(raw)) {
    const rest = normalizeLegacyStatusRest(raw.replace(RE_PREFIX_TRAINING_COMPLETED, ""));
    return rest
      ? t
        ? t("pages.history.warnings.trainingCompletedWithRest", { rest })
        : tr(undefined, "pages.history.warnings.trainingCompletedWithRest", { rest })
      : t
        ? t("pages.history.warnings.trainingCompleted")
        : tr(undefined, "pages.history.warnings.trainingCompleted");
  }
  if (RE_PREFIX_RECOMMENDATION_COMPLETED.test(raw)) {
    const rest = normalizeLegacyStatusRest(raw.replace(RE_PREFIX_RECOMMENDATION_COMPLETED, ""));
    return rest
      ? t
        ? t("pages.history.warnings.recommendationCompletedWithRest", { rest })
        : tr(undefined, "pages.history.warnings.recommendationCompletedWithRest", { rest })
      : t
        ? t("pages.history.warnings.recommendationCompleted")
        : tr(undefined, "pages.history.warnings.recommendationCompleted");
  }

  if (/^prediction completed\b/i.test(raw)) {
    const rest = normalizeLegacyStatusRest(raw.replace(/^prediction completed\b/i, ""));
    return rest
      ? t
        ? t("pages.history.warnings.predictionCompletedWithRest", { rest })
        : tr(undefined, "pages.history.warnings.predictionCompletedWithRest", { rest })
      : t
        ? t("pages.history.warnings.predictionCompleted")
        : tr(undefined, "pages.history.warnings.predictionCompleted");
  }
  if (/^training completed\b/i.test(raw)) {
    const rest = normalizeLegacyStatusRest(raw.replace(/^training completed\b/i, ""));
    return rest
      ? t
        ? t("pages.history.warnings.trainingCompletedWithRest", { rest })
        : tr(undefined, "pages.history.warnings.trainingCompletedWithRest", { rest })
      : t
        ? t("pages.history.warnings.trainingCompleted")
        : tr(undefined, "pages.history.warnings.trainingCompleted");
  }
  if (/^recommendation completed\b/i.test(raw)) {
    const rest = normalizeLegacyStatusRest(raw.replace(/^recommendation completed\b/i, ""));
    return rest
      ? t
        ? t("pages.history.warnings.recommendationCompletedWithRest", { rest })
        : tr(undefined, "pages.history.warnings.recommendationCompletedWithRest", { rest })
      : t
        ? t("pages.history.warnings.recommendationCompleted")
        : tr(undefined, "pages.history.warnings.recommendationCompleted");
  }

  // Legacy parsing tokens (archived / backend diagnostics; not UI copy): CJK phrases for matching only.
  if (RE_STATE_MACHINE_RECOVERY.test(raw)) {
    return t ? t("pages.history.warnings.stateMachineRecoveryFailed") : tr(undefined, "pages.history.warnings.stateMachineRecoveryFailed");
  }

  if (/^job\s+[\w-]+\s+(queued|running|completed|failed)/i.test(raw)) {
    return t ? t("pages.history.warnings.jobStatusUpdated") : tr(undefined, "pages.history.warnings.jobStatusUpdated");
  }

  return raw;
}

/** List items (warnings, log lines, etc.) */
export function sanitizeWarningLine(line: string | null | undefined, t?: Translate): string {
  return sanitizeUserFacingLine(line, t);
}

export function sanitizeWarningLines(lines: string[] | null | undefined, t?: Translate): string[] {
  if (!lines?.length) return [];
  return lines.map((x) => sanitizeUserFacingLine(x, t)).filter((x) => x.length > 0);
}

const PUBLISH_SNIPPET_KEYS = {
  modelId: "panels.taskDetail.tech.publishSnippetModelIdPrefix",
  notes: "panels.taskDetail.tech.publishSnippetNotesPrefix",
  config: "panels.taskDetail.tech.publishSnippetConfigLabel",
} as const;

const PUBLISH_SNIPPET_EN_FALLBACK: Record<string, string> = {
  [PUBLISH_SNIPPET_KEYS.modelId]: "Release model ID: ",
  [PUBLISH_SNIPPET_KEYS.notes]: "Notes: ",
  [PUBLISH_SNIPPET_KEYS.config]: "Release config",
};

function publishSnippetLabel(t: Translate | undefined, key: string): string {
  if (t) return t(key);
  return PUBLISH_SNIPPET_EN_FALLBACK[key] ?? "";
}

/** Publish overrides and similar engineering snippets (user-visible in task detail). */
export function humanizePublishSummarySnippet(s: string | null | undefined, t?: Translate): string {
  if (s == null || !String(s).trim()) return "";
  return String(s)
    .replace(/publish_overrides\.model_id\s*=\s*/gi, publishSnippetLabel(t, PUBLISH_SNIPPET_KEYS.modelId))
    .replace(/\bnotes\s*=\s*/gi, publishSnippetLabel(t, PUBLISH_SNIPPET_KEYS.notes))
    .replace(/\bpublish_overrides\b/gi, publishSnippetLabel(t, PUBLISH_SNIPPET_KEYS.config));
}
