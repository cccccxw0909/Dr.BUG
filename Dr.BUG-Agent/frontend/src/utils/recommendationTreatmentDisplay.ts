import { REGIMEN_TREATMENT_FIELD_KEYS, type RegimenTreatmentFieldKey } from "../types";
import type { Translate } from "./messageSanitizer";

/** Polymyxin-class fields: shown as daily frequency (not daily dose). */
const DAILY_FREQ_FIELD_KEYS = new Set<string>([
  "colistin_cms_daily_freq",
  "polymyxin_b_daily_freq",
  "colistin_sulfate_daily_freq",
]);

const FIELD_SHORT_LABEL_EN: Record<RegimenTreatmentFieldKey, string> = {
  colistin_cms_daily_freq: "CMS",
  polymyxin_b_daily_freq: "Polymyxin B",
  colistin_sulfate_daily_freq: "Colistin sulfate",
  carbapenem_daily_dose: "Carbapenem",
  sulbactam_daily_dose: "Sulbactam",
  tigecycline_daily_dose: "Tigecycline",
  minocycline_daily_dose: "Minocycline",
  vancomycin_daily_dose: "Vancomycin",
  eravacycline_daily_dose: "Eravacycline",
  aminoglycoside_daily_dose: "Aminoglycoside",
};

function loc(t: Translate | undefined, key: string, values: Record<string, unknown> | undefined, enFallback: string): string {
  if (t) return t(key, values);
  return enFallback;
}

function shortFieldLabel(key: RegimenTreatmentFieldKey, t?: Translate): string {
  const i18nKey = `regimen.treatmentDisplay.fields.${key}.shortLabel`;
  return loc(t, i18nKey, undefined, FIELD_SHORT_LABEL_EN[key]);
}

function isNonZero(v: unknown): boolean {
  const n = typeof v === "number" ? v : parseFloat(String(v));
  if (!Number.isFinite(n)) return false;
  return Math.abs(n) > 1e-9;
}

function fmtNum(n: number): string {
  if (Number.isInteger(n)) return String(n);
  const s = n.toFixed(4).replace(/\.?0+$/, "");
  return s || "0";
}

/**
 * Convert treatment_values to readable lines for non-zero entries only (frequency vs daily dose).
 * Order follows REGIMEN_TREATMENT_FIELD_KEYS for stable display.
 */
export function formatTreatmentValueLines(
  raw: Record<string, unknown> | null | undefined,
  t?: Translate,
): string[] {
  if (!raw || typeof raw !== "object") return [];
  const lines: string[] = [];
  for (const key of REGIMEN_TREATMENT_FIELD_KEYS) {
    const v = raw[key];
    if (!isNonZero(v)) continue;
    const n = typeof v === "number" ? v : parseFloat(String(v));
    const label = shortFieldLabel(key, t);
    const value = fmtNum(n);
    if (DAILY_FREQ_FIELD_KEYS.has(key)) {
      lines.push(
        loc(
          t,
          "regimen.treatmentDisplay.clinicalFreqLine",
          { label, value },
          `${label}: frequency ${value} times/day`,
        ),
      );
    } else {
      lines.push(
        loc(
          t,
          "regimen.treatmentDisplay.clinicalDoseGLine",
          { label, value },
          `${label}: dose ${value} g/day`,
        ),
      );
    }
  }
  return lines;
}
