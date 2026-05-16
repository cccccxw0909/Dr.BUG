/**
 * Batch prediction APIs may return one warning string per affected row.
 * For English UI we surface an aggregated clinician-facing line instead of repeating row-level templates.
 */

/** Row-index prefix patterns in English warning lines (used only to aggregate row-level notices). */
const ROW_WARN_PATTERN = /row\s+\d+\s*:?/i;

/** True if the warning line looks like a per-row input correction notice (English patterns only). */
export function isRowLevelBatchInputWarning(line: string): boolean {
  const s = String(line || "").trim();
  if (!s) return false;
  if (ROW_WARN_PATTERN.test(s)) return true;
  if (/missing or corrected inputs/i.test(s)) return true;
  return false;
}

export function countRowLevelBatchInputWarnings(warnings: string[] | null | undefined): number {
  if (!warnings?.length) return 0;
  return warnings.reduce((n, w) => n + (isRowLevelBatchInputWarning(String(w)) ? 1 : 0), 0);
}
