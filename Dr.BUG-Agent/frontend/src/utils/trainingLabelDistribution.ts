/**
 * Human-readable label distribution for training dataset preview (avoid raw "0:26, 1:49").
 */

import type { Translate } from "./messageSanitizer";

export type LabelOutcomeFamily = "clinical_outcome" | "survival" | "resistance" | "unknown";

function loc(t: Translate | undefined, key: string, values?: Record<string, unknown>, en?: string): string {
  if (t) return values ? String(t(key, values)) : String(t(key));
  return en ?? "";
}

/** Infer outcome family from clinical task id and/or target column name (heuristic). */
export function inferLabelOutcomeFamily(clinicalTaskId: unknown, targetColumn: unknown): LabelOutcomeFamily {
  const ct = String(clinicalTaskId || "").toLowerCase();
  const tc = String(targetColumn || "").toLowerCase();
  const blob = `${ct} ${tc}`;
  if (/clinical_efficacy|clinical_outcome|efficacy|outcome|improv/i.test(blob)) return "clinical_outcome";
  if (/mortality|survival|surviv|death|28d|28_day/i.test(blob)) return "survival";
  if (/resistan|polymyxin|mic/i.test(blob)) return "resistance";
  return "unknown";
}

function countForClass(dist: Record<string, number>, classKey: string): number {
  const v = dist[classKey];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

/**
 * Format label_distribution for UI. Keys are often "0"/"1" from the backend.
 */
export function formatTrainingLabelDistribution(
  distribution: Record<string, number> | undefined,
  clinicalTaskId: unknown,
  targetColumn: unknown,
  previewMerged?: Record<string, unknown> | null,
  t?: Translate,
): string {
  if (!distribution || typeof distribution !== "object" || Object.keys(distribution).length === 0) {
    return "";
  }
  const merged = previewMerged || {};
  const ct = clinicalTaskId ?? merged.clinical_task_id;
  const tc = targetColumn ?? merged.target_column;
  const family = inferLabelOutcomeFamily(ct, tc);

  const c0 = countForClass(distribution, "0");
  const c1 = countForClass(distribution, "1");

  if (family === "clinical_outcome") {
    return loc(
      t,
      "training.labelDistribution.clinical.line",
      { pos: c1, neg: c0 },
      `Label distribution: improvement ${c1}, non-improvement ${c0}`,
    );
  }
  if (family === "survival") {
    return loc(
      t,
      "training.labelDistribution.survival.line",
      { survived: c1, died: c0 },
      `Label distribution: survived ${c1}, died ${c0}`,
    );
  }
  if (family === "resistance") {
    return loc(
      t,
      "training.labelDistribution.resistance.line",
      { resistant: c1, nonResistant: c0 },
      `Label distribution: resistant ${c1}, non-resistant ${c0}`,
    );
  }

  const parts = Object.entries(distribution).map(([cls, n]) =>
    loc(t, "training.labelDistribution.fallback.classSamples", { cls, count: n }, `Class ${cls}: ${n} samples`),
  );
  const sep = loc(t, "training.labelDistribution.fallback.sep", {}, "; ");
  return loc(
    t,
    "training.labelDistribution.fallback.line",
    { body: parts.join(sep) },
    `Label distribution: ${parts.join(sep)}`,
  );
}
