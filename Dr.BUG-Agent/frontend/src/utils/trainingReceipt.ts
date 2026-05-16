/**
 * Training confirmation receipt: generate a readable summary from the final merged payload, matching backend pending.payload + completed_params merge semantics.
 */

import type { ChatTurnData } from "../types";
import type { Translate } from "./messageSanitizer";
import {
  isNonEmptyString,
  normalizePhase1TrainingPayloadForSubmit,
  normalizeTrainingPayloadForSubmit,
} from "./trainingPayloadBuilder";

function loc(t: Translate | undefined, key: string, values?: Record<string, unknown>, en?: string): string {
  if (t) return values ? String(t(key, values)) : String(t(key));
  return en ?? "";
}

function naDisplay(t?: Translate): string {
  return loc(t, "common.na", {}, "—");
}

/** Match orchestrator behavior: merge before normalizing for display; server validation remains authoritative. */
export function buildMergedNormalizedTrainingPayload(chat: ChatTurnData): Record<string, unknown> {
  const base = chat.pending_confirmation?.payload && typeof chat.pending_confirmation.payload === "object"
    ? { ...(chat.pending_confirmation.payload as Record<string, unknown>) }
    : {};
  const completed = chat.completed_params && typeof chat.completed_params === "object"
    ? chat.completed_params
    : {};
  return normalizeTrainingPayloadForSubmit({ ...base, ...completed });
}

/** Training Phase 1: after merging pending + completed values, output only Phase 1 contract fields. */
export function buildMergedPhase1TrainingPayload(chat: ChatTurnData): Record<string, unknown> {
  const base = chat.pending_confirmation?.payload && typeof chat.pending_confirmation.payload === "object"
    ? { ...(chat.pending_confirmation.payload as Record<string, unknown>) }
    : {};
  const completed = chat.completed_params && typeof chat.completed_params === "object" ? chat.completed_params : {};
  return normalizePhase1TrainingPayloadForSubmit({ ...base, ...completed });
}

/** Readable feature-source summary; med_cols alone is not a source, and multiple sources include priority notes. */
export function summarizeTrainingFeatureSource(p: Record<string, unknown>, t?: Translate): string {
  const finalN = Array.isArray(p.final_features) ? (p.final_features as unknown[]).length : 0;
  const fs = isNonEmptyString(p.feature_set) ? String(p.feature_set).trim() : "";
  const selN = Array.isArray(p.selected_features) ? (p.selected_features as unknown[]).length : 0;

  const sep = loc(t, "chat.trainingReceipt.featureSource.clauseSep", {}, "; ");

  let primary = "";
  if (finalN > 0) {
    primary = loc(
      t,
      "chat.trainingReceipt.featureSource.finalFeatures",
      { count: finalN },
      `Final modeling columns (final_features), ${finalN} columns`,
    );
  } else if (fs) {
    primary = loc(t, "chat.trainingReceipt.featureSource.namedGroup", { name: fs }, `Named feature group (feature_set=${fs})`);
  } else if (selN > 0) {
    primary = loc(
      t,
      "chat.trainingReceipt.featureSource.candidatePool",
      { count: selN },
      `Candidate feature pool (selected_features), ${selN} items`,
    );
  } else {
    primary = loc(t, "chat.trainingReceipt.featureSource.none", {}, "(none)");
  }

  const extras: string[] = [];
  if (finalN > 0 && fs)
    extras.push(
      loc(
        t,
        "chat.trainingReceipt.featureSource.extraNamedAlso",
        { name: fs },
        `A named feature group (feature_set=${fs}) was also provided`,
      ),
    );
  if (finalN > 0 && selN > 0)
    extras.push(
      loc(
        t,
        "chat.trainingReceipt.featureSource.extraPoolAlsoFinal",
        { count: selN },
        `Candidate pool (selected_features) also submitted with ${selN} items`,
      ),
    );
  if (finalN === 0 && fs && selN > 0)
    extras.push(
      loc(
        t,
        "chat.trainingReceipt.featureSource.extraPoolOnly",
        { count: selN },
        `Candidate pool (selected_features) also submitted with ${selN} items`,
      ),
    );

  let out = primary;
  if (extras.length) out += sep + extras.join(sep);
  const multi = (finalN > 0 ? 1 : 0) + (fs ? 1 : 0) + (selN > 0 ? 1 : 0);
  if (multi > 1) {
    out += loc(
      t,
      "chat.trainingReceipt.featureSource.multiSourceSuffix",
      {},
      ". Multiple sources were submitted; execution priority follows the backend/runtime.",
    );
  }
  return out;
}

export function coreTrainingReceiptLines(p: Record<string, unknown>, t?: Translate): string[] {
  const dash = naDisplay(t);
  const featureSummary = summarizeTrainingFeatureSource(p, t);
  const lines = [
    loc(t, "chat.trainingReceipt.lines.datasetId", { value: p.dataset_id ?? dash }, `Dataset dataset_id: ${p.dataset_id ?? dash}`),
    loc(
      t,
      "chat.trainingReceipt.lines.clinicalTaskId",
      { value: p.clinical_task_id ?? dash },
      `Clinical task clinical_task_id: ${p.clinical_task_id ?? dash}`,
    ),
    loc(t, "chat.trainingReceipt.lines.mlTaskType", { value: p.ml_task_type ?? dash }, `ML type ml_task_type: ${p.ml_task_type ?? dash}`),
    loc(
      t,
      "chat.trainingReceipt.lines.targetColumn",
      { value: p.target_column ?? dash },
      `Target column target_column: ${p.target_column ?? dash}`,
    ),
    loc(t, "chat.trainingReceipt.lines.featureSourceLine", { summary: featureSummary }, `Feature source: ${featureSummary}`),
    loc(
      t,
      "chat.trainingReceipt.lines.phaseHint",
      {},
      "Initial training setup was submitted; model choice, metrics, final modeling columns, and release are confirmed in later chat steps.",
    ),
  ];
  if (isNonEmptyString(p.model_type) || isNonEmptyString(p.objective_metric)) {
    lines.push(
      loc(
        t,
        "chat.trainingReceipt.lines.optionalPrefill",
        { modelType: p.model_type ?? dash, objective: p.objective_metric ?? dash },
        `(Optional prefill) model_type: ${p.model_type ?? dash}; objective_metric: ${p.objective_metric ?? dash}`,
      ),
    );
  }
  return lines;
}

/** Chat receipt after training job creation: short factual lines only (workflow narrative lives in the receipt card intro). */
export function buildUserFacingTrainingReceiptLines(p: Record<string, unknown>, t?: Translate): string[] {
  const lines: string[] = [];
  const selected = new Set<string>();
  const addAll = (raw: unknown) => {
    if (!Array.isArray(raw)) return;
    for (const x of raw) {
      const s = String(x ?? "").trim();
      if (s) selected.add(s);
    }
  };
  addAll(p.selected_features);
  addAll(p.med_cols);
  const totalSelected = selected.size;
  const lockedN = Array.isArray(p.med_cols)
    ? (p.med_cols as unknown[]).map((x) => String(x ?? "").trim()).filter(Boolean).length
    : 0;

  if (totalSelected > 0) {
    lines.push(
      loc(
        t,
        lockedN > 0
          ? "training.receiptCard.summarySelectedFeatureCountWithLocked"
          : "training.receiptCard.summarySelectedFeatureCountNoLocked",
        { count: totalSelected, lockedCount: lockedN },
        lockedN > 0
          ? `${totalSelected} selected input features in this request, including ${lockedN} locked variables.`
          : `${totalSelected} selected input feature(s) in this request.`,
      ),
    );
  }

  return lines;
}
