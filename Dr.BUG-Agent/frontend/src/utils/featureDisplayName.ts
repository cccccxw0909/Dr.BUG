/**
 * UI display names for fields/features. Prefer English and do not introduce clinical Chinese translations here.
 * - Use schema.label only when it is a trustworthy English label.
 * - Otherwise lightly humanize the raw key (snake_case → Title Case) or use common lab/test acronyms.
 * - Do not add a second naming file; localized workflow copy belongs at the call site/i18n layer.
 */
import type { PredictionFieldSchema } from "../types";

/** Common lab/test and score acronyms; keep concise English abbreviations rather than long medical phrases. */
const ACRONYM_LABELS: Record<string, string> = {
  sofa: "SOFA",
  apache: "APACHE",
  gcs: "GCS",
  wbc: "WBC",
  plt: "PLT",
  crp: "CRP",
  pct: "PCT",
  egfr: "eGFR",
  bmi: "BMI",
  spo2: "SpO2",
  inr: "INR",
  mic: "MIC",
  alt: "ALT",
  ast: "AST",
  bun: "BUN",
  map: "MAP",
  hr: "HR",
  rr: "RR",
  sbp: "SBP",
  dbp: "DBP",
  lac: "Lactate",
  cr: "Cr",
  na: "Na",
  k: "K",
  ph: "pH",
  hco3: "HCO3",
  tbil: "T.Bil",
  alb: "Alb",
  glu: "Glu",
};

export function humanizeSnakeCaseLabel(s: string): string {
  return s
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function normalizeFieldKey(name: string): string {
  return name.replace(/\s+/g, "_").toLowerCase();
}

/** Whether schema.label is a usable English label; reject placeholders and non-English UI copy. */
function isUsableEnglishSchemaLabel(s: string): boolean {
  const t = s.trim();
  if (!t) return false;
  if (/^col\d+|x\d+|f\d+$/i.test(t)) return false;
  if (/[\u4e00-\u9fff]/.test(t)) return false;
  return true;
}

/**
 * Derive a display label from a variable name only: acronym table → Title Case humanization.
 * The historical function name is retained; the semantics are English display labels.
 */
export function resolveClinicalFeatureDisplayName(rawKey: string): string {
  const key = normalizeFieldKey(rawKey);
  if (ACRONYM_LABELS[key]) return ACRONYM_LABELS[key];
  return humanizeSnakeCaseLabel(rawKey);
}

/** Single field: prefer an English schema.label, otherwise use resolveClinicalFeatureDisplayName(name). */
export function doctorFacingFeatureLabel(field: PredictionFieldSchema): string {
  const raw = (field.label || "").trim();
  if (raw && isUsableEnglishSchemaLabel(raw)) return raw;
  return resolveClinicalFeatureDisplayName(field.name);
}

/** Batch column names / missing columns as an English display-label list. */
export function formatClinicalFeatureNameList(rawKeys: string[], schemaFields?: PredictionFieldSchema[] | null): string {
  return rawKeys
    .map((k) => {
      const f = schemaFields?.find((x) => x.name === k);
      return f ? doctorFacingFeatureLabel(f) : resolveClinicalFeatureDisplayName(k);
    })
    .join(", ");
}

/** Explanation charts / reference tables: one English display label per item; raw is only a Vue key. */
export function buildFeatureAliasRows(
  rawKeys: string[],
  schemaFields?: PredictionFieldSchema[] | null,
): Array<{ raw: string; display: string }> {
  const out: Array<{ raw: string; display: string }> = [];
  const seen = new Set<string>();
  for (const raw0 of rawKeys) {
    const raw = String(raw0 || "").trim();
    if (!raw || seen.has(raw)) continue;
    seen.add(raw);
    const f = schemaFields?.find((x) => x.name === raw);
    const display = f ? doctorFacingFeatureLabel(f) : resolveClinicalFeatureDisplayName(raw);
    out.push({ raw, display });
  }
  return out;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Replace variable names in free text with English display labels. Prefer longer keys; humanize standalone
 * snake_case tokens that are not explicitly mapped.
 */
export function clinicalizeExplanationFeatureNames(
  text: string,
  opts?: { schemaFields?: PredictionFieldSchema[] | null; extraKeys?: string[] | null },
): string {
  if (!text) return "";
  const pairMap = new Map<string, string>();
  const put = (key: string, label: string) => {
    const k = key.trim();
    if (!k || !label || k === label) return;
    if (!pairMap.has(k)) pairMap.set(k, label);
  };
  for (const f of opts?.schemaFields || []) {
    put(f.name, doctorFacingFeatureLabel(f));
  }
  for (const k of opts?.extraKeys || []) {
    put(k, resolveClinicalFeatureDisplayName(k));
  }
  for (const [k, v] of Object.entries(ACRONYM_LABELS)) {
    put(k, v);
  }
  const pairs = [...pairMap.entries()].sort((a, b) => b[0].length - a[0].length);
  let s = text;
  for (const [key, label] of pairs) {
    const esc = escapeRegExp(key);
    try {
      s = s.replace(new RegExp(`(?<![a-zA-Z0-9_])${esc}(?![a-zA-Z0-9_])`, "g"), label);
    } catch {
      /* ignore bad patterns */
    }
  }
  const snakeRe = /(?<![a-zA-Z0-9_])([a-z][a-z0-9]*(?:_[a-z][a-z0-9]*)+)(?![a-zA-Z0-9_])/g;
  return s.replace(snakeRe, (m) => resolveClinicalFeatureDisplayName(m));
}
