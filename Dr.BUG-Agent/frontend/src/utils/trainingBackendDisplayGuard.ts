/**
 * Maps known backend training headlines to localized UI copy when the UI locale expects English strings.
 */
import type { Translate } from "./messageSanitizer";
import { englishUiLocalizedFallback, resolveUiLocale } from "./localeTextGuard";

export function localizeTrainingResultHeadlineForEnUi(raw: string | null | undefined, t: Translate): string {
  const s = String(raw || "").trim();
  if (!s) return "";
  const loc = resolveUiLocale().toLowerCase();

  if (loc.startsWith("zh")) {
    const norm = s.replace(/\s+/g, " ").trim();
    const englishDone = /^training\s+workflow\s+completed\.?\s*$/i.test(norm);
    if (englishDone) {
      return t("chat.trainingWorkflow.backendCopy.headlineWorkflowCompleted");
    }
    return s;
  }

  if (!loc.startsWith("en")) return s;

  return englishUiLocalizedFallback(s, t, "chat.statusMessages.completion.backendHeadlineUiMismatch");
}

export function localizeTrainingFilterSummaryForEnUi(raw: string | null | undefined, t: Translate): string {
  const s = String(raw || "").trim();
  if (!s) return "";
  const loc = resolveUiLocale().toLowerCase();
  if (!loc.startsWith("en")) return s;

  return englishUiLocalizedFallback(s, t, "chat.trainingWorkflow.backendCopy.filterSummaryGenericEnFallback");
}

/** Removes internal workflow wording sometimes echoed from backend screening summaries (any locale). */
export function sanitizeTrainingSummaryInternalPhrases(raw: string | null | undefined): string {
  let s = String(raw || "");
  s = s
    .replace(/\u53ef\u5728\s*Phase\s*3\s*\u8986\u76d6/gi, "")
    .replace(/Phase\s*3\s*\u8986\u76d6/gi, "")
    .replace(/override\s+in\s+Phase\s*3/gi, "")
    .replace(/\(\s*\)/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  return s;
}
