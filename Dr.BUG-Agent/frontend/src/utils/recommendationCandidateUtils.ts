import type { RecommendationRegimenResultRow } from "../types";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "../types";

/** Stable non-zero treatment fingerprint using the same treatment-field order as recommendation display. */
export function treatmentContentFingerprint(
  raw: Record<string, unknown> | null | undefined,
): string {
  if (!raw || typeof raw !== "object") return "";
  const parts: string[] = [];
  for (const key of REGIMEN_TREATMENT_FIELD_KEYS) {
    const v = raw[key];
    const n = typeof v === "number" ? v : parseFloat(String(v));
    if (!Number.isFinite(n) || Math.abs(n) <= 1e-9) continue;
    parts.push(`${key}=${n}`);
  }
  return parts.join("|");
}

/**
 * Deduplication rules aligned with the UI:
 * - Group by treatment-content fingerprint + predicted probability. The fingerprint contains all non-zero
 *   treatment_values entries in REGIMEN_TREATMENT_FIELD_KEYS order, formatted as key=value and joined by |.
 *   If there are no non-zero values, the fingerprint is an empty string.
 * - Rows with the same fingerprint and exactly equal numeric predicted_probability values are duplicates;
 *   keep the first row from the original list to preserve ordering.
 */
export function dedupeTopCandidates(
  rows: RecommendationRegimenResultRow[] | null | undefined,
): RecommendationRegimenResultRow[] {
  if (!rows?.length) return [];
  const seen = new Set<string>();
  const out: RecommendationRegimenResultRow[] = [];
  for (const c of rows) {
    const fp = treatmentContentFingerprint(c.treatment_values);
    const p = c.predicted_probability;
    const probPart =
      p === undefined || p === null || Number.isNaN(Number(p)) ? "na" : String(Number(p));
    const key = `${fp}@@${probPart}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(c);
  }
  return out;
}
