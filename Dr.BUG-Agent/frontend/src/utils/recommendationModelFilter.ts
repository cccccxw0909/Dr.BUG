import type { PredictionModelListItem } from "../types";

/**
 * Coarse filter aligned with backend survival-only recommendation checks: registered schema and metadata hints for survival/mortality outcomes.
 * POST /recommendation/jobs remains authoritative.
 */
export function isSurvivalRecommendationCandidate(m: PredictionModelListItem): boolean {
  if (m.task_key === "survival_outcome") {
    return m.has_schema !== false;
  }
  if (!m.has_schema) return false;
  const t = `${m.model_id} ${m.task_name} ${m.display_name}`.toLowerCase();
  const keys = ["survival", "mortality", "death", "28d", "28-day", "28_day", "mortality_28d"];
  return keys.some((k) => t.includes(k));
}
