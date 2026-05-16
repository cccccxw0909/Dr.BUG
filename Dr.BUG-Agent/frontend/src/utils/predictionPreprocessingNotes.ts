/**
 * Doctor-facing copy for prediction preprocessing / pipeline warnings.
 * Parses English backend templates; localized UI strings come from i18n keys.
 * Missing-input lines are merged into one paragraph with localized variable lists.
 */
import type { PredictionFieldSchema } from "../types";
import { doctorFacingFeatureLabel, resolveClinicalFeatureDisplayName } from "./featureDisplayName";
import { sanitizeUserFacingLine, type Translate } from "./messageSanitizer";

function containsCjk(s: string): boolean {
  return /[\u3400-\u9FFF]/.test(s);
}

function resolveUiLocale(locale: string): string {
  return String(locale || "").toLowerCase();
}

export function joinVariableLabels(labels: string[], locale: string): string {
  const deduped = [...new Set(labels.map((l) => l.trim()).filter(Boolean))];
  if (deduped.length === 0) return "";
  const tag = locale.replace("_", "-");
  try {
    return new Intl.ListFormat(tag, { style: "long", type: "conjunction" }).format(deduped);
  } catch {
    return deduped.join(resolveUiLocale(locale).startsWith("zh") ? "\u3001" : ", ");
  }
}

export function featureLabelForPreprocessingNote(
  rawName: string,
  fields: PredictionFieldSchema[] | null | undefined,
  locale: string,
): string {
  const loc = resolveUiLocale(locale);
  const f = fields?.find((x) => x.name === rawName);
  if (loc.startsWith("zh")) {
    const lab = (f?.label || "").trim();
    if (lab) return lab;
    return resolveClinicalFeatureDisplayName(rawName);
  }
  return f ? doctorFacingFeatureLabel(f) : resolveClinicalFeatureDisplayName(rawName);
}

type ParsedMissing = { kind: "missing"; rawName: string };
type ParsedTruncated = { kind: "truncated"; count: number };
type ParsedBatchNonNumeric = { kind: "batch_non_numeric"; rawName: string };
type ParsedBatchBinary = { kind: "batch_binary_suspect"; rawName: string };

// Legacy backend note templates (English); parsed so UI can render localized i18n copy.
function tryParseMissingFeatureLine(line: string): ParsedMissing | null {
  const s = line.trim();
  const mCurly = /^Feature\s+\u201c([^\u201d]+)\u201d\s+is\s+missing(?:\s+and\s+was\s+handled\s+by\s+the\s+model\s+workflow)?/i.exec(
    s,
  );
  if (mCurly) return { kind: "missing", rawName: mCurly[1].trim() };
  const mSemi = /^Feature\s+\u201c([^\u201d]+)\u201d\s+is\s+missing;\s+handled\s+per\s+model\s+pipeline/i.exec(s);
  if (mSemi) return { kind: "missing", rawName: mSemi[1].trim() };
  const m2 = /^Feature\s*\[\s*([^\]]+?)\s*\]\s+is\s+missing/i.exec(s);
  if (m2) return { kind: "missing", rawName: m2[1].trim() };
  return null;
}

function tryParseTruncated(line: string): ParsedTruncated | null {
  const m = /^(\d+)\s+additional\s+missing-feature\s+notes\s+omitted$/i.exec(line.trim());
  if (!m) return null;
  const n = Number(m[1]);
  if (!Number.isFinite(n)) return null;
  return { kind: "truncated", count: n };
}

function tryParseBatchNonNumeric(line: string): ParsedBatchNonNumeric | null {
  const m = /^Column\s+"([^"]+)"\s+does\s+not\s+look\s+numeric\s+in\s+the\s+file$/i.exec(line.trim());
  if (!m) return null;
  return { kind: "batch_non_numeric", rawName: m[1].trim() };
}

function tryParseBatchBinarySuspect(line: string): ParsedBatchBinary | null {
  const m = /^Column\s+"([^"]+)"\s+may\s+not\s+be\s+binary;\s+verify\s+allowed\s+values$/i.exec(line.trim());
  if (!m) return null;
  return { kind: "batch_binary_suspect", rawName: m[1].trim() };
}

type KnownNote =
  | "explanationSkippedNoModel"
  | "explanationFailed"
  | "batchModeNoShap"
  | "shapPlotExportFailed"
  | "shapNotInstalled"
  | "shapUnsupportedModelType"
  | "shapComputationFailed";

// Pipeline note templates (English); matched so callers can map to i18n keys.
function matchKnownPipelineNote(line: string): KnownNote | null {
  const s = line.trim();
  if (
    s === "Prediction context has no loaded model; skipping single-sample explanation." ||
    s === "Loaded model missing in prediction context; skipping single-sample explanation."
  ) {
    return "explanationSkippedNoModel";
  }
  if (
    s === "Single-sample SHAP explanation is disabled for batch prediction to preserve execution efficiency." ||
    s === "SHAP explanation is disabled for this run."
  ) {
    return "batchModeNoShap";
  }
  if (s === "SHAP ran, but plot export failed (check server logs)." || s === "SHAP was computed, but plot export failed; check server logs.") {
    return "shapPlotExportFailed";
  }
  if (/^This explanation run failed:/i.test(s) || /^Explanation generation failed:/i.test(s)) return "explanationFailed";
  if (
    s === "SHAP is not installed in this runtime; single-sample explanation is unavailable." ||
    s === "SHAP is not installed in the current environment; single-sample explanation is unavailable."
  ) {
    return "shapNotInstalled";
  }
  if (
    s === "This model type does not support single-sample SHAP (tree models required)." ||
    s === "The current model type does not support single-sample SHAP; a tree model is required."
  ) {
    return "shapUnsupportedModelType";
  }
  if (/^SHAP computation failed/i.test(s)) return "shapComputationFailed";
  return null;
}

function knownNoteToKey(known: KnownNote): string {
  switch (known) {
    case "explanationSkippedNoModel":
      return "prediction.explanation.preprocessingExplanationSkippedNoModel";
    case "batchModeNoShap":
      return "prediction.explanation.preprocessingBatchModeNoShap";
    case "shapPlotExportFailed":
      return "prediction.explanation.preprocessingShapPlotExportFailed";
    case "shapNotInstalled":
      return "prediction.explanation.preprocessingShapNotInstalled";
    case "shapUnsupportedModelType":
      return "prediction.explanation.preprocessingShapUnsupportedModelType";
    case "shapComputationFailed":
      return "prediction.explanation.preprocessingShapComputationFailed";
    default:
      return "prediction.explanation.preprocessingExplanationFailed";
  }
}

/**
 * Returns one or more paragraphs/lines: merged missing-variable copy first, then truncation / batch / other notes.
 */
export function formatPredictionDataPreprocessingNotes(
  lines: string[] | null | undefined,
  opts: {
    locale: string;
    t: Translate;
    schemaFields?: PredictionFieldSchema[] | null;
  },
): string[] {
  if (!lines?.length) return [];

  const loc = resolveUiLocale(opts.locale);
  const isEn = loc.startsWith("en");

  const missingOrder: string[] = [];
  const missingSeen = new Set<string>();
  let truncated: ParsedTruncated | null = null;
  const extraLines: string[] = [];
  const extraSeen = new Set<string>();
  let needsGeneric = false;

  const pushExtra = (s: string) => {
    const x = s.trim();
    if (!x || extraSeen.has(x)) return;
    extraSeen.add(x);
    extraLines.push(x);
  };

  for (const rawLine of lines) {
    const line = String(rawLine ?? "").trim();
    if (!line) continue;

    const missing = tryParseMissingFeatureLine(line);
    if (missing) {
      if (!missingSeen.has(missing.rawName)) {
        missingSeen.add(missing.rawName);
        missingOrder.push(missing.rawName);
      }
      continue;
    }

    const tr = tryParseTruncated(line);
    if (tr) {
      truncated = tr;
      continue;
    }

    const bn = tryParseBatchNonNumeric(line);
    if (bn) {
      const label = featureLabelForPreprocessingNote(bn.rawName, opts.schemaFields, opts.locale);
      pushExtra(
        isEn
          ? opts.t("prediction.explanation.preprocessingBatchNonNumericEn", { feature: label })
          : opts.t("prediction.explanation.preprocessingBatchNonNumericZh", { feature: label }),
      );
      continue;
    }

    const bb = tryParseBatchBinarySuspect(line);
    if (bb) {
      const label = featureLabelForPreprocessingNote(bb.rawName, opts.schemaFields, opts.locale);
      pushExtra(
        isEn
          ? opts.t("prediction.explanation.preprocessingBatchBinarySuspectEn", { feature: label })
          : opts.t("prediction.explanation.preprocessingBatchBinarySuspectZh", { feature: label }),
      );
      continue;
    }

    const known = matchKnownPipelineNote(line);
    if (known) {
      pushExtra(opts.t(knownNoteToKey(known)));
      continue;
    }

    const sanitized = sanitizeUserFacingLine(line, opts.t);
    if (sanitized && sanitized !== line) {
      pushExtra(sanitized);
      continue;
    }

    if (sanitized && !containsCjk(sanitized)) {
      pushExtra(sanitized);
      continue;
    }

    needsGeneric = true;
  }

  const out: string[] = [];

  if (missingOrder.length === 1) {
    const label = featureLabelForPreprocessingNote(missingOrder[0], opts.schemaFields, opts.locale);
    out.push(
      isEn
        ? opts.t("prediction.explanation.variablesHandledOneEn", { variable: label })
        : opts.t("prediction.explanation.variablesHandledOneZh", { variable: label }),
    );
  } else if (missingOrder.length > 1) {
    const labels = missingOrder.map((raw) => featureLabelForPreprocessingNote(raw, opts.schemaFields, opts.locale));
    const joined = joinVariableLabels(labels, opts.locale);
    out.push(
      isEn
        ? opts.t("prediction.explanation.variablesHandledSeveralEn", { variables: joined })
        : opts.t("prediction.explanation.variablesHandledSeveralZh", { variables: joined }),
    );
  }

  if (truncated) {
    out.push(
      isEn
        ? opts.t("prediction.explanation.preprocessingTruncatedWarningsEn", { count: truncated.count })
        : opts.t("prediction.explanation.preprocessingTruncatedWarningsZh", { count: truncated.count }),
    );
  }

  for (const e of extraLines) {
    if (!out.includes(e)) out.push(e);
  }

  if (needsGeneric && missingOrder.length === 0) {
    out.push(
      isEn
        ? opts.t("prediction.explanation.preprocessingGenericFallbackEn")
        : opts.t("prediction.explanation.preprocessingGenericFallbackZh"),
    );
  }

  return out;
}
