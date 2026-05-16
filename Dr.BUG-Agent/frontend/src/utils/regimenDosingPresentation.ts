import type { RegimenTreatmentFieldKey, RegimenTreatmentValues } from "../types";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "../types";

/** Two-group layout: polymyxins vs all other regimen dose fields. */
export const REGIMEN_DOSE_FIELD_GROUPS: {
  key: "polymyxins" | "combination";
  fields: readonly RegimenTreatmentFieldKey[];
}[] = [
  {
    key: "polymyxins",
    fields: ["colistin_cms_daily_freq", "polymyxin_b_daily_freq", "colistin_sulfate_daily_freq"],
  },
  {
    key: "combination",
    fields: [
      "carbapenem_daily_dose",
      "sulbactam_daily_dose",
      "tigecycline_daily_dose",
      "minocycline_daily_dose",
      "vancomycin_daily_dose",
      "eravacycline_daily_dose",
      "aminoglycoside_daily_dose",
    ],
  },
];

export function isDailyFreqField(k: RegimenTreatmentFieldKey): boolean {
  return k.endsWith("_daily_freq");
}

/**
 * Compact single-line summary for list cards: non-zero fields only, explicit units (times/day, g/day).
 */
export function formatRegimenDoseSummaryLine(
  tv: RegimenTreatmentValues | undefined,
  t: (key: string, values?: Record<string, string | number>) => string,
): string {
  if (!tv) return "";
  const parts: string[] = [];
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    const raw = tv[k];
    const n = typeof raw === "number" ? raw : Number(raw);
    if (!Number.isFinite(n) || n === 0) continue;
    const label = String(t(`regimen.treatmentDisplay.fields.${k}.shortLabel`) || k);
    if (isDailyFreqField(k)) {
      parts.push(String(t("regimen.treatmentDisplay.compactFreq", { label, value: n })));
    } else {
      parts.push(String(t("regimen.treatmentDisplay.compactDose", { label, value: n })));
    }
  }
  const sep = String(t("regimen.treatmentDisplay.compactSep"));
  return parts.join(sep);
}
