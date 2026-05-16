/**
 * Doctor-facing presentation helpers for prediction results and forms.
 *
 * Important:
 * - This module must not contain Chinese UI copy. Localized UI strings must live in i18n locale files.
 * - Legacy Chinese archive parse patterns live in `i18n/lexicons/zhPredictionPresentation.ts`.
 * - Some patterns keep ASCII-only legacy parsing for older English archive strings.
 */
import type { PredictionFieldSchema, PredictionHistoryListItem, PredictionSingleResponse } from "../types";
import {
  RE_HISTORY_LINE_PROB_ONLY,
  RE_HISTORY_LINE_RESULT_AND_PROB,
  RE_LEGACY_BATCH_SUMMARY_COUNTS_ZH,
} from "../i18n/lexicons/zhPredictionPresentation";
import { resolveUiLocale, textLooksPrimarilyCjk } from "./localeTextGuard";
import {
  clinicalizeExplanationFeatureNames,
  doctorFacingFeatureLabel,
  formatClinicalFeatureNameList,
} from "./featureDisplayName";

export { doctorFacingFeatureLabel, formatClinicalFeatureNameList };

export type Translate = (key: string, values?: Record<string, unknown>) => string;

function pp(t: Translate | undefined, key: string, fallback: string, values?: Record<string, unknown>): string {
  return t ? t(key, values) : fallback;
}

/** Map canonical / API outcome tokens to locale strings (ContextPanel, shared surfaces). */
export function formatPredictionOutcomeTagForDisplay(tag: string, t?: Translate): string {
  if (!t) return tag;
  const trimmed = String(tag || "").trim();
  if (!trimmed || trimmed === "—") return trimmed;

  const compact = trimmed.toLowerCase().replace(/\s+/g, " ");

  if (compact === "survival" || compact === "alive") {
    return t("predictionPresentation.outcomeLabels.mortalitySurvival");
  }
  if (
    compact === "death" ||
    compact === "mortality" ||
    compact === "dead" ||
    compact === "nonsurvival" ||
    compact === "non-survival" ||
    compact === "non survival"
  ) {
    return t("predictionPresentation.outcomeLabels.mortalityNonSurvival");
  }
  if (compact === "improvement" || compact === "success") {
    return t("predictionPresentation.outcomeLabels.clinicalImprovement");
  }
  if (compact === "failure" || compact === "failed") {
    return t("predictionPresentation.outcomeLabels.clinicalFailure");
  }
  if (compact === "resistant" || compact === "resistance") {
    return t("predictionPresentation.outcomeLabels.resistanceResistant");
  }
  if (compact === "sensitive" || compact === "susceptible" || compact === "susceptibility") {
    return t("predictionPresentation.outcomeLabels.resistanceSusceptible");
  }

  return trimmed;
}

function normalizeProbability01(v: unknown): number | null {
  if (v == null || v === "") return null;
  let n = Number(v);
  if (Number.isNaN(n)) return null;
  if (n > 1) n = n / 100;
  if (n < 0 || n > 1) return null;
  return n;
}

export type PredictionTaskFamily =
  | "mortality"
  | "survival_benefit"
  | "clinical_outcome"
  | "resistance"
  | "treatment_duration"
  | "generic";

function haystack(taskName: string, displayName: string, modelId: string): string {
  return `${taskName} ${displayName} ${modelId}`.toLowerCase();
}

export function inferPredictionTaskFamily(data: {
  task_name?: string | null;
  display_name?: string | null;
  model_id?: string | null;
}): PredictionTaskFamily {
  const h = haystack(String(data.task_name || ""), String(data.display_name || ""), String(data.model_id || ""));
  if (/polymyxin|resistan|mic/i.test(h)) return "resistance";
  if (/duration|days_on/i.test(h)) return "treatment_duration";
  if (/mortality|28d|28-day|death/i.test(h)) return "mortality";
  if (/survival/i.test(h) && /benefit|improv|efficacy/i.test(h)) return "survival_benefit";
  if (/clinical_outcome|clinical outcome|clinical_efficacy|efficacy|response|outcome/i.test(h)) return "clinical_outcome";
  if (/clinical|outcome/i.test(h)) return "clinical_outcome";
  if (/survival/i.test(h)) return "mortality";
  return "generic";
}

/** Map legacy labels (e.g. High risk/Low risk) to task-family-specific wording when probability is absent. */
function mapLegacyOutcomeLabelWhenNoProbability(raw: string, family: PredictionTaskFamily): string {
  const t = raw.trim();
  if (!t || t === "—") return "—";
  if (/^high\s*risk$/i.test(t)) {
    if (family === "clinical_outcome" || family === "survival_benefit") return "Failure";
    if (family === "mortality") return "Death";
    if (family === "resistance") return "Resistant";
    return "Failure";
  }
  if (/^low\s*risk$/i.test(t)) {
    if (family === "clinical_outcome" || family === "survival_benefit") return "Improvement";
    if (family === "mortality") return "Survival";
    if (family === "resistance") return "Sensitive";
    return "Improvement";
  }
  if (family === "generic") {
    if (/^positive$/i.test(t)) return "Likely higher-probability outcome";
    if (/^negative$/i.test(t)) return "Likely lower-probability outcome";
  }
  return t;
}

/** Infer a clinical grouping label when the backend does not provide one. */
export function inferClinicalFieldGroup(fieldName: string): string {
  const n = fieldName.toLowerCase();
  if (/sofa|apache|gcs|map|hr|rr|temp|spo2|sbp|dbp|pulse|oxygen|score/i.test(n)) return "Scores & vitals";
  if (/lab|wbc|plt|crp|pct|lac|tbil|alb|inr|crea|bun|alt|ast|glu|na|^k$|ph|hco3|anion|egfr|cr_|plt|pct|n_percent/i.test(n))
    return "Labs & inflammation";
  if (/drug|abx|antibiotic|colistin|polymyxin|dose|daily|cms|tigecycline|carbapenem|vancomycin|aminoglycoside|minocycline|eravacycline|sulbactam/i.test(n))
    return "Medications";
  if (/comorb|chf|copd|dm|hiv|immun|cancer|renal|liver|history|prior|stroke|malignant|hypertension|diabetes|disease/i.test(n))
    return "Comorbidities & history";
  return "Basic info & others";
}

export function formatFormValueForDoctor(v: unknown, t?: Translate): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? pp(t, "predictionPresentation.boolean.yes", "Yes") : pp(t, "predictionPresentation.boolean.no", "No");
  if (v === 1 || v === "1" || v === "true") return pp(t, "predictionPresentation.boolean.yes", "Yes");
  if (v === 0 || v === "0" || v === "false") return pp(t, "predictionPresentation.boolean.no", "No");
  return String(v);
}

/** For numeric-semantics fields, keep numeric display even if schema says binary. */
export function isSubmitSummaryNumericSemantic(field: PredictionFieldSchema): boolean {
  if (field.type === "float" || field.type === "int") return true;
  const k = field.name.replace(/\s+/g, "_").toLowerCase();
  if (
    /(?:^|_)(daily_)?(freq|dose)|_freq$|_dose$|comorb_count|oxygen_concentration|cr_baseline|days_on|duration|mic\b|cms\b/.test(k)
  )
    return true;
  if (
    /\b(age|plt|wbc|pct|lac|glu|egfr|crp|tbil|alb|inr|creat|bun|sofa|apache|gcs|map|spo2|temp|hr|rr|sbp|dbp|height|weight|bmi|na\b|k\b|ph|hco3)\d*\b/.test(
      k,
    )
  )
    return true;
  if (
    /colistin|polymyxin|carbapenem|tigecycline|vancomycin|minocycline|eravacycline|sulbactam|aminoglycoside|antibiotic|daptomycin|linezolid/.test(
      k,
    )
  )
    return true;
  return false;
}

function formatSubmitSummaryNumericRaw(v: unknown): string {
  if (typeof v === "boolean") return v ? "1" : "0";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return String(v);
    return Number.isInteger(v) ? String(v) : String(v);
  }
  const s = String(v).trim();
  const n = Number(s);
  if (s !== "" && !Number.isNaN(n)) return s;
  return String(v);
}

/**
 * Submission summary only:
 * - numeric-semantics → keep numeric string
 * - categorical/string → keep raw text
 * - other/binary → use formatFormValueForDoctor (Yes/No)
 */
export function formatSubmitSummaryFieldValue(field: PredictionFieldSchema, v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (isSubmitSummaryNumericSemantic(field)) return formatSubmitSummaryNumericRaw(v);
  if (field.type === "categorical" || field.type === "string") return String(v);
  return formatFormValueForDoctor(v);
}

/** Submission summary: keep schema order; missing values shown as —. */
export function buildPredictionSubmitSummaryRows(
  fields: PredictionFieldSchema[],
  formValues: Record<string, unknown>,
): Array<{ name: string; label: string; value: string }> {
  return fields.map((f) => {
    const raw = formValues[f.name];
    const empty = raw === null || raw === undefined || raw === "";
    return {
      name: f.name,
      label: doctorFacingFeatureLabel(f),
      value: empty ? "—" : formatSubmitSummaryFieldValue(f, raw),
    };
  });
}

/** Context panel: compact 2-line display for the latest single prediction. */
export function formatPredictionContextLastSingleLines(
  data: PredictionSingleResponse,
  t?: Translate,
): {
  line1: string;
  line2: string | null;
} {
  const s = formatClinicalPredictionSurface(data, t);
  if (data.prediction_type === "classification") {
    const labelPrefix = pp(t, "predictionPresentation.labels.predictedLabel", "Predicted label");
    const conclusion = formatPredictionOutcomeTagForDisplay(s.conclusionPrimary, t);
    return {
      line1: `${labelPrefix}: ${conclusion}`,
      line2: s.probabilityLine,
    };
  }
  return {
    line1: s.conclusionPrimary,
    line2: s.showProbability ? s.probabilityLine : null,
  };
}

export function formatPredictionProbabilityLine(p: number | null | undefined, t?: Translate): string {
  const label = pp(t, "predictionPresentation.labels.predictedProbability", "Predicted probability");
  if (p == null || Number.isNaN(Number(p))) return `${label}: ${pp(t, "predictionPresentation.labels.na", "—")}`;
  return `${label}: ${(Number(p) * 100).toFixed(2)}%`;
}

export type ClinicalPredictionSurface = {
  family: PredictionTaskFamily;
  heroCaption: string;
  conclusionPrimary: string;
  probabilityLine: string;
  showProbability: boolean;
  /** Primary scan line: classification shows label + probability; regression shows a single conclusion line (optional prob). */
  primaryScanLine: string;
};

/** Shared by result cards, history, and right-side panels. */
export function formatClinicalPredictionSurface(data: PredictionSingleResponse, t?: Translate): ClinicalPredictionSurface {
  const family = inferPredictionTaskFamily(data);
  const p = data.predicted_probability;

  if (data.prediction_type === "regression") {
    const v = data.predicted_value ?? data.risk_score;
    const hasProb = p != null && !Number.isNaN(Number(p));
    if (family === "treatment_duration") {
      let days = "—";
      if (v != null && !Number.isNaN(Number(v))) {
        const n = Number(v);
        days = Number.isInteger(n) ? String(n) : n.toFixed(1);
      }
      const conclusionPrimary = t
        ? t("predictionPresentation.labels.predictedTreatmentDuration", { days })
        : `Predicted treatment duration: ${days} days`;
      const probabilityLine = formatPredictionProbabilityLine(hasProb ? p : null, t);
      const primaryScanLine = hasProb ? `${conclusionPrimary}; ${probabilityLine}` : conclusionPrimary;
      return {
        family,
        heroCaption: pp(t, "predictionPresentation.labels.clinicalConclusion", "Clinical conclusion"),
        conclusionPrimary,
        probabilityLine,
        showProbability: hasProb,
        primaryScanLine,
      };
    }
    const val =
      v != null && !Number.isNaN(Number(v)) ? (Number.isInteger(Number(v)) ? String(v) : Number(v).toFixed(4)) : "—";
    const conclusionPrimary = t ? t("predictionPresentation.labels.predictedValueLine", { value: val }) : `Predicted value: ${val}`;
    const probabilityLine = formatPredictionProbabilityLine(hasProb ? p : null, t);
    const primaryScanLine = hasProb ? `${conclusionPrimary}; ${probabilityLine}` : conclusionPrimary;
    return {
      family,
      heroCaption: pp(t, "predictionPresentation.labels.clinicalConclusion", "Clinical conclusion"),
      conclusionPrimary,
      probabilityLine,
      showProbability: hasProb,
      primaryScanLine,
    };
  }

  const pNum = p != null && !Number.isNaN(Number(p)) ? Number(p) : null;
  let tag = "—";
  if (pNum != null) {
    if (family === "mortality") {
      tag = pNum > 0.5 ? "Survival" : "Death";
    } else if (family === "clinical_outcome" || family === "survival_benefit") {
      tag = pNum > 0.5 ? "Improvement" : "Failure";
    } else if (family === "resistance") {
      tag = pNum > 0.5 ? "Resistant" : "Sensitive";
    } else {
      tag = pNum > 0.5 ? pp(t, "predictionPresentation.labels.likelyHigherOutcome", "Likely higher-probability outcome") : pp(t, "predictionPresentation.labels.likelyLowerOutcome", "Likely lower-probability outcome");
    }
  } else {
    const raw = String(data.predicted_label ?? data.outcome_display ?? data.label_display ?? "").trim();
    tag = mapLegacyOutcomeLabelWhenNoProbability(raw || "—", family);
  }

  const probabilityLine = formatPredictionProbabilityLine(p ?? null, t);
  const hasProb = p != null && !Number.isNaN(Number(p));
  const labelPrefix = pp(t, "predictionPresentation.labels.predictedLabel", "Predicted label");
  const primaryScanLine = hasProb ? `${labelPrefix}: ${tag}; ${probabilityLine}` : `${labelPrefix}: ${tag}`;

  return {
    family,
    heroCaption: pp(t, "predictionPresentation.labels.predictedLabel", "Predicted label"),
    conclusionPrimary: tag,
    probabilityLine,
    showProbability: true,
    primaryScanLine,
  };
}

export function formatPredictionResultOneLiner(data: PredictionSingleResponse, t?: Translate): string {
  const s = formatClinicalPredictionSurface(data, t);
  return s.primaryScanLine;
}

/**
 * Project `result_summary` into a minimal shape compatible with single prediction responses,
 * so we can reuse `formatPredictionResultOneLiner`.
 */
export function taskResultSummaryToSingleResponse(rs: Record<string, unknown>): PredictionSingleResponse | null {
  const pt = String(rs.prediction_type || "classification").toLowerCase();
  if (pt === "batch") return null;

  const prediction_type: "classification" | "regression" = pt === "regression" ? "regression" : "classification";
  const p = normalizeProbability01(rs.predicted_probability ?? rs.probability);
  let pv: number | null = null;
  if (rs.predicted_value != null && rs.predicted_value !== "") {
    const n = Number(rs.predicted_value);
    if (!Number.isNaN(n)) pv = n;
  }
  if (pv == null && rs.risk_score != null && rs.risk_score !== "") {
    const n = Number(rs.risk_score);
    if (!Number.isNaN(n)) pv = n;
  }
  const labelRaw = rs.predicted_label ?? rs.label_display ?? rs.outcome_display;
  const labelStr = labelRaw != null && String(labelRaw).trim() !== "" ? String(labelRaw).trim() : "";

  const hasAny = p != null || labelStr !== "" || pv != null;
  if (!hasAny) return null;

  const w = rs.warnings;
  const warnings = Array.isArray(w) ? w.map((x) => String(x)) : [];

  return {
    ok: true,
    model_id: String(rs.model_id ?? ""),
    display_name: String(rs.display_name ?? ""),
    task_name: String(rs.task_name ?? ""),
    prediction_type,
    predicted_label: rs.predicted_label != null && String(rs.predicted_label).trim() !== "" ? String(rs.predicted_label) : null,
    predicted_probability: p,
    predicted_value: pv,
    label_display: String(rs.label_display ?? labelStr),
    outcome_display: String(rs.outcome_display ?? labelStr),
    feature_values_used: {},
    warnings,
    timestamp: String(rs.timestamp ?? ""),
    risk_score: rs.risk_score != null && !Number.isNaN(Number(rs.risk_score)) ? Number(rs.risk_score) : null,
  };
}

/** Tasks list: one-line outcome summary for completed prediction tasks. */
export function formatPredictionTaskListOutcomeLine(
  rs: Record<string, unknown> | null | undefined,
  t?: Translate,
): string {
  if (!rs || typeof rs !== "object") return "";
  if (String(rs.prediction_type).toLowerCase() === "batch") {
    const tr = Number(rs.total_rows);
    const sr = Number(rs.succeeded_rows);
    if (Number.isFinite(tr) && tr >= 0) {
      const ok = Number.isFinite(sr) ? sr : 0;
      if (t) return t("predictionPresentation.taskList.batchCounts", { total: tr, succeeded: ok });
      return `Total ${tr}; succeeded ${ok}`;
    }
    const h = String(rs.headline || "").trim();
    return h || "";
  }
  const single = taskResultSummaryToSingleResponse(rs);
  if (single) {
    const line = formatPredictionResultOneLiner(single, t).trim();
    if (line) return line;
  }
  const st = String(rs.summary_text || "").trim();
  if (st) return scrubLegacyRiskSummaryText(st, rs);
  const h = String(rs.headline || "").trim();
  return h ? scrubLegacyRiskSummaryText(h, rs) : "";
}

function scrubLegacyRiskSummaryText(text: string, rs: Record<string, unknown>): string {
  const t0 = tidyExplanationSummary(text);
  const f = inferPredictionTaskFamily({
    task_name: String(rs.task_name || ""),
    display_name: String(rs.display_name || ""),
    model_id: String(rs.model_id || ""),
  });
  let s = t0;
  if (f === "clinical_outcome" || f === "survival_benefit") {
    s = s.replace(/\bhigh\s*risk\b/gi, "Failure").replace(/\blow\s*risk\b/gi, "Improvement");
  } else if (f === "mortality") {
    s = s.replace(/\bhigh\s*risk\b/gi, "Death").replace(/\blow\s*risk\b/gi, "Survival");
  } else if (f === "resistance") {
    s = s.replace(/\bhigh\s*risk\b/gi, "Resistant").replace(/\blow\s*risk\b/gi, "Sensitive");
  }
  const s1 = clinicalizeExplanationFeatureNames(s);
  return shortExplainSummary(s1, 200);
}

/** @deprecated Use formatClinicalPredictionSurface; kept for backwards compatibility. */
export function buildSingleResultPresentation(data: PredictionSingleResponse, t?: Translate) {
  const s = formatClinicalPredictionSurface(data, t);
  const probTitle = pp(t, "predictionPresentation.labels.predictedProbability", "Predicted probability");
  return {
    family: s.family,
    headline: s.conclusionPrimary,
    headlineSub: "",
    probabilityTitle: probTitle,
    probabilityValue: s.probabilityLine.replace(/^.*?[:\uFF1A]\s*/, ""),
    hideRawLabelLine: true,
    probLineEn: "",
    labelLineEn: "",
  };
}

export function tidyExplanationSummary(text: string): string {
  let s = text.trim();
  if (!s) return "";
  s = s.replace(/^shap\s*[:\uFF1A]\s*/i, "");
  s = s.replace(/\bdebug\b/gi, "");
  s = s.replace(/\btrace\b/gi, "");
  s = s.replace(/\s+/g, " ");
  return s;
}

export function shortExplainSummary(text: string, maxLen = 220): string {
  const t = tidyExplanationSummary(text);
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen)}…`;
}

export function formatTopFeatureNamesForDoctor(names: string[], schemaFields?: PredictionFieldSchema[] | null): string {
  return formatClinicalFeatureNameList(names, schemaFields);
}

/** Explanation summary: denoise + replace internal field names with display labels. */
export function doctorFacingExplanationSummary(
  text: string,
  opts?: { fields?: PredictionFieldSchema[] | null; extraKeys?: string[] | null },
): string {
  const t = tidyExplanationSummary(text);
  if (!t) return "";
  return clinicalizeExplanationFeatureNames(t, { schemaFields: opts?.fields ?? undefined, extraKeys: opts?.extraKeys ?? undefined });
}

/**
 * Same as {@link doctorFacingExplanationSummary}, but in English UI replaces primarily-Chinese prose with
 * a short English product fallback (no translation of the original free text). When structured top features
 * exist on the card, the copy points readers to that section instead of asking them to switch UI language.
 */
export function localizedDoctorFacingExplanationSummary(
  text: string | null | undefined,
  opts: {
    fields?: PredictionFieldSchema[] | null;
    extraKeys?: string[] | null;
    locale: string;
    t: Translate;
    hasStructuredTopFeatures?: boolean;
  },
): string {
  const raw = String(text || "").trim();
  if (!raw) return "";
  const processed = doctorFacingExplanationSummary(raw, { fields: opts.fields, extraKeys: opts.extraKeys });
  const loc = resolveUiLocale(opts.locale).toLowerCase();
  if (!loc.startsWith("en")) return processed;
  if (!textLooksPrimarilyCjk(processed)) return processed;

  const hasFeat = Boolean(opts.hasStructuredTopFeatures);
  const intro = String(opts.t("prediction.explanation.summaryEnglishStructuredIntro"));
  if (hasFeat) {
    const pointer = String(opts.t("prediction.explanation.summaryEnglishStructuredPointer"));
    return `${intro}\n\n${pointer}`.trim();
  }
  return String(opts.t("prediction.explanation.summaryEnglishNoStructuredFallback"));
}

/** Batch column check: one-line summary (kept consistent across pages). */
export function formatBatchColumnAlignmentSummary(
  matched: number,
  missing: number,
  extra: number,
  t?: Translate,
): string {
  if (t) return t("predictionPresentation.batch.columnAlignmentSummary", { matched, missing, extra });
  return `Column alignment: matched ${matched} · missing ${missing} · extra ${extra}`;
}

/** History detail: batch field alignment summary. */
export function formatHistoryBatchFieldCheckLine(
  matched: number,
  missing: number,
  extra: number,
  t?: Translate,
): string {
  if (t) {
    return t("pages.history.labels.columnAlignmentSummary", { matched, missing, extra });
  }
  return `Column alignment: matched ${matched} · missing ${missing} · extra ${extra}`;
}

/**
 * Legacy compatibility: parse archived prediction-history index lines (English or legacy Chinese tokens).
 */
export function parseHistoryListItemToSingleResponse(it: PredictionHistoryListItem): PredictionSingleResponse | null {
  if (it.type !== "single") return null;
  const s = (it.summary || "").trim();
  const mZh = s.match(RE_HISTORY_LINE_RESULT_AND_PROB);
  if (mZh) {
    const pr = mZh[2].trim();
    if (pr === "—") return null;
    const prob = Number(pr);
    if (Number.isNaN(prob) || prob < 0 || prob > 1) return null;
    return {
      ok: true,
      model_id: it.model_id,
      display_name: it.display_name,
      task_name: it.task_name,
      prediction_type: "classification",
      predicted_probability: prob,
      predicted_label: null,
      label_display: "",
      outcome_display: "",
      feature_values_used: {},
      warnings: [],
      timestamp: it.timestamp,
    };
  }
  const m = s.match(/result[:\uFF1A]\s*([^\uFF1B;]+)\s*[\uFF1B;]\s*prob(?:ability)?[:\uFF1A]\s*([\d.]+|—)/i);
  if (m) {
    const pr = m[2].trim();
    if (pr === "—") return null;
    const prob = Number(pr);
    if (Number.isNaN(prob) || prob < 0 || prob > 1) return null;
    return {
      ok: true,
      model_id: it.model_id,
      display_name: it.display_name,
      task_name: it.task_name,
      prediction_type: "classification",
      predicted_probability: prob,
      predicted_label: null,
      label_display: "",
      outcome_display: "",
      feature_values_used: {},
      warnings: [],
      timestamp: it.timestamp,
    };
  }
  const m2 = s.match(RE_HISTORY_LINE_PROB_ONLY);
  if (m2) {
    const prob = Number(m2[1].trim());
    if (!Number.isNaN(prob) && prob >= 0 && prob <= 1) {
      return {
        ok: true,
        model_id: it.model_id,
        display_name: it.display_name,
        task_name: it.task_name,
        prediction_type: "classification",
        predicted_probability: prob,
        predicted_label: null,
        label_display: "",
        outcome_display: "",
        feature_values_used: {},
        warnings: [],
        timestamp: it.timestamp,
      };
    }
  }
  const m2en = s.match(/prob(?:ability)?[:\uFF1A]\s*([\d.]+)/i);
  if (m2en) {
    const prob = Number(m2en[1].trim());
    if (!Number.isNaN(prob) && prob >= 0 && prob <= 1) {
      return {
        ok: true,
        model_id: it.model_id,
        display_name: it.display_name,
        task_name: it.task_name,
        prediction_type: "classification",
        predicted_probability: prob,
        predicted_label: null,
        label_display: "",
        outcome_display: "",
        feature_values_used: {},
        warnings: [],
        timestamp: it.timestamp,
      };
    }
  }
  return null;
}

function scrubHistoryIndexSummaryLine(summary: string, it: PredictionHistoryListItem): string {
  const f = inferPredictionTaskFamily({ task_name: it.task_name, display_name: it.display_name, model_id: it.model_id });
  let o = summary;
  if (f === "clinical_outcome" || f === "survival_benefit") {
    o = o.replace(/\bhigh\s*risk\b/gi, "Failure").replace(/\blow\s*risk\b/gi, "Improvement");
  } else if (f === "mortality") {
    o = o.replace(/\bhigh\s*risk\b/gi, "Death").replace(/\blow\s*risk\b/gi, "Survival");
  } else if (f === "resistance") {
    o = o.replace(/\bhigh\s*risk\b/gi, "Resistant").replace(/\blow\s*risk\b/gi, "Sensitive");
  }
  return o;
}

/**
 * Parses fixed legacy batch summary tokens from archived prediction-history list records.
 * Supports English index lines and common legacy Chinese numeric summaries.
 */
function parseLegacyBatchSummaryCounts(summary: string): { total: number; succeeded: number; failed: number } | null {
  const s = summary.trim();
  if (!s) return null;
  const mZh = s.match(RE_LEGACY_BATCH_SUMMARY_COUNTS_ZH);
  if (mZh) {
    const total = Number(mZh[1]);
    const succeeded = Number(mZh[2]);
    const failed = Number(mZh[3]);
    if (Number.isFinite(total) && Number.isFinite(succeeded) && Number.isFinite(failed)) {
      return { total, succeeded, failed };
    }
  }
  const mEn = s.match(/^\s*Total\s*(\d+)\s*[;,;]\s*succeeded\s*(\d+)\s*[;,;]\s*failed\s*(\d+)\s*$/i);
  if (mEn) {
    const total = Number(mEn[1]);
    const succeeded = Number(mEn[2]);
    const failed = Number(mEn[3]);
    if (Number.isFinite(total) && Number.isFinite(succeeded) && Number.isFinite(failed)) {
      return { total, succeeded, failed };
    }
  }
  return null;
}

/** History list summary line (kept consistent with result cards). */
export function formatPredictionHistoryListLine(it: PredictionHistoryListItem, t?: Translate): string {
  if (it.type !== "single") {
    const batch = it as unknown as Record<string, unknown>;
    const tr = batch.total_rows;
    const sr = batch.succeeded_rows;
    const fr = batch.failed_rows;
    if (t && tr != null && sr != null && fr != null) {
      return t("pages.history.labels.batchSummary", {
        total: tr,
        succeeded: sr,
        failed: fr,
      });
    }
    const s = String(it.summary || "").trim();
    if (s) {
      const parsed = parseLegacyBatchSummaryCounts(s);
      if (parsed && t) {
        return t("pages.history.labels.batchSummary", {
          total: parsed.total,
          succeeded: parsed.succeeded,
          failed: parsed.failed,
        });
      }
      return clinicalizeExplanationFeatureNames(scrubHistoryIndexSummaryLine(s, it));
    }
    if (t) return t("pages.history.labels.noSummary");
    return "Completed · See the details panel for counts and the download link.";
  }
  const pseudo = parseHistoryListItemToSingleResponse(it);
  if (pseudo) return formatPredictionResultOneLiner(pseudo);
  return clinicalizeExplanationFeatureNames(scrubHistoryIndexSummaryLine(String(it.summary || ""), it));
}

export function predictionHistoryResultTitle(type: "single" | "batch"): string {
  return type === "single" ? "Single prediction" : "Batch prediction";
}

export function predictionHistoryListTitleLine(taskName: string, type: "single" | "batch"): string {
  const mode = type === "single" ? "Single" : "Batch";
  const name = taskName?.trim() || "Prediction";
  return `${name} · ${mode}`;
}
