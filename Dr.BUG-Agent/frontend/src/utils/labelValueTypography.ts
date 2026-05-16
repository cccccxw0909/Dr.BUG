/**
 * Locale-aware separators between labels and values in UI copy (avoid "Progress:Task" / "col:9").
 */

export function localeUsesZhColon(locale: string): boolean {
  return String(locale || "").toLowerCase().startsWith("zh");
}

/** Pair separator between label and value: English ": ", full-width colon for zh UI locale. */
export function uiLabelValueColon(locale: string): string {
  return localeUsesZhColon(locale) ? "\uFF1A" : ": ";
}

/**
 * Format missing-column overview for dataset preview (comma-separated pairs; colon style follows locale).
 */
export function formatMissingOverviewPairs(
  entries: ReadonlyArray<{ column?: string; missing_count?: number }>,
  locale: string,
): string {
  if (!entries.length) return "";
  const betweenPairs = localeUsesZhColon(locale) ? "\u3001" : ", ";
  const c = uiLabelValueColon(locale);
  return entries
    .map((x) => `${String(x.column ?? "")}${c}${Number(x.missing_count ?? 0)}`)
    .join(betweenPairs);
}
