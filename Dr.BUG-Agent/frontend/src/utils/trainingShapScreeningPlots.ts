import { normalizeAlgorithmName } from "./normalizeAlgorithmName";

/** Basename lowercase, e.g. shap_beeswarm_xgboost.png */
export function parseShapBeeswarmBaselineSlug(basenameLower: string): string | null {
  const m = basenameLower.match(/^shap[_-]?beeswarm[_-]+(.+)\.png$/i);
  const raw = m?.[1]?.trim();
  return raw?.length ? raw : null;
}

/** Baseline bar plot: shap_bar_* / shap-bar_* — not beeswarm summaries. */
export function parseShapBarBaselineSlug(basenameLower: string): string | null {
  const m = basenameLower.match(/^shap[_-]?bar[_-]+(.+)\.png$/i);
  const raw = m?.[1]?.trim();
  if (!raw?.length) return null;
  if (raw.includes("beeswarm")) return null;
  return raw;
}

export function canonicalBucketForShapScreeningSlug(rawSlug: string): string {
  const n = normalizeAlgorithmName(rawSlug);
  return n || "default";
}
