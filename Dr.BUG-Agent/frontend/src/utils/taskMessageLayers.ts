/**
 * Split task.message vs result_summary.headline into primary / supplement layers (sanitize first).
 */
import type { Translate } from "./messageSanitizer";
import { sanitizeUserFacingLine } from "./messageSanitizer";
import { englishUiLocalizedFallback } from "./localeTextGuard";
import { localizeTrainingResultHeadlineForEnUi } from "./trainingBackendDisplayGuard";

function guardBackendTaskLine(s: string, t?: Translate): string {
  if (!s.trim()) return s;
  return englishUiLocalizedFallback(s, t, "chat.statusMessages.layers.backendTaskMessageUiMismatch");
}

const GENERIC_STATUS_MESSAGES = new Set(
  ["recommendation completed", "prediction completed", "training completed", "completed", "success", "succeeded"].map((s) =>
    s.toLowerCase(),
  ),
);

const HEAD_MAX = 96;

function isMutedWholeMessage(msg: string, summaryHeadline: string): boolean {
  const low = msg.toLowerCase().trim();
  if (!msg) return true;
  if (GENERIC_STATUS_MESSAGES.has(low)) return true;
  if (/^recommendation completed\b/i.test(msg)) return true;
  if (/^prediction completed\b/i.test(msg)) return true;
  if (/^training completed\b/i.test(msg)) return true;
  const head = String(summaryHeadline || "").trim();
  return Boolean(head && msg.trim() === head);
}

export type TaskMessageLayers = {
  headLine: string;
  tailText: string;
  showSupplement: boolean;
  headlineSanitized: string;
};

/**
 * Split task.message and result_summary.headline; truncate long primary and move overflow to tail.
 */
export function buildTaskMessageLayers(task: Record<string, unknown>, t?: Translate): TaskMessageLayers {
  const rs = (task.result_summary || {}) as Record<string, unknown>;
  const hl0 = String(rs.headline || "").trim();
  let hlNorm = hl0 ? sanitizeUserFacingLine(hl0, t) || hl0 : "";
  if (hlNorm && t) hlNorm = localizeTrainingResultHeadlineForEnUi(hlNorm, t);
  const headlineSanitized = hlNorm ? guardBackendTaskLine(hlNorm, t) : "";

  const msg0 = String(task.message || "").trim();
  const msg = msg0 ? guardBackendTaskLine(sanitizeUserFacingLine(msg0, t) || msg0, t) : "";

  if (!msg || isMutedWholeMessage(msg, hl0)) {
    const show = Boolean(headlineSanitized && headlineSanitized !== msg);
    return {
      headLine: "",
      tailText: show ? headlineSanitized : "",
      showSupplement: show,
      headlineSanitized,
    };
  }

  const lines = msg.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  let first = lines[0] || msg;
  let rest = lines.length > 1 ? lines.slice(1).join("\n") : "";

  if (first.length > HEAD_MAX) {
    rest = first.slice(HEAD_MAX) + (rest ? `\n${rest}` : "");
    first = `${first.slice(0, HEAD_MAX)}…`;
  }

  const tailParts: string[] = [];
  if (rest) tailParts.push(rest);
  if (headlineSanitized && headlineSanitized !== msg && !msg.includes(headlineSanitized)) {
    const prefix = t ? t("pages.history.detail.resultSummaryTailPrefix") : "Result summary: ";
    tailParts.push(`${prefix}${headlineSanitized}`);
  }
  const tailText = tailParts.join("\n").trim();

  return {
    headLine: first,
    tailText,
    showSupplement: tailText.length > 0,
    headlineSanitized,
  };
}
