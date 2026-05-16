/**
 * Pick default modeling algorithm from CV comparison rows (Phase4 card).
 */

export type CvMetricRow = Record<string, unknown> & { model?: string };

/** Phase4 algorithm `<select>` values; keep in sync with training workflow UI. */
export const TRAINING_WORKFLOW_ALGORITHM_OPTIONS = [
  "xgboost",
  "lightgbm",
  "catboost",
  "random_forest",
  "logistic_regression",
  "svm",
  "knn",
] as const;

function toNum(v: unknown): number | null {
  if (v == null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function rowMetricValue(row: CvMetricRow, metric: string): unknown {
  const m = metric.toLowerCase();
  if (m === "f1") return row.f1 ?? row.f1_score;
  if (m === "pearson" || m === "pcc") return row.pcc ?? row.pearson;
  return row[m];
}

export function compareCvRowsByMetric(a: CvMetricRow, b: CvMetricRow, metric: string): number {
  const m = metric.toLowerCase();
  const av = toNum(rowMetricValue(a, m));
  const bv = toNum(rowMetricValue(b, m));
  if (av == null && bv == null) return 0;
  if (av == null) return 1;
  if (bv == null) return -1;
  const lowerIsBetter = m === "mse" || m === "mae" || m === "rmse";
  return lowerIsBetter ? av - bv : bv - av;
}

export function pickBestCvRow(rows: CvMetricRow[], objectiveMetric: string): CvMetricRow | undefined {
  const om = String(objectiveMetric || "").trim().toLowerCase();
  if (!rows.length || !om) return rows[0];
  const sorted = [...rows].sort((a, b) => compareCvRowsByMetric(a, b, om));
  return sorted[0];
}

/** Map programmer-style CV model name (e.g. XGBoost) to training workflow select value (e.g. xgboost). */
export function cvRowModelToAlgorithmOption(rowModel: string, options: readonly string[]): string | undefined {
  const raw = String(rowModel || "").trim().toLowerCase();
  const compact = raw.replace(/[\s_-]+/g, "");
  for (const opt of options) {
    const o = opt.replace(/_/g, "");
    if (compact.includes(o) || raw.includes(opt.replace("_", " "))) return opt;
  }
  if (compact.includes("logistic")) return "logistic_regression";
  if (compact.includes("randomforest")) return "random_forest";
  return undefined;
}
