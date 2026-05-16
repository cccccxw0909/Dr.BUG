import { computed, type ComputedRef, type Ref } from "vue";
import type { PredictionFormCardData } from "../types";

export type PredictionDomainMode = "single" | "batch";

/**
 * Derived layer with prediction_form_card as the single source of truth: do not duplicate state; only normalize single/batch views.
 */
export function usePredictionDomain(
  card: Ref<PredictionFormCardData> | ComputedRef<PredictionFormCardData>,
): {
  mode: ComputedRef<PredictionDomainMode>;
  batch: ComputedRef<PredictionFormCardData["batch"]>;
  batchBusy: ComputedRef<boolean>;
  singleBusy: ComputedRef<boolean>;
  anyBusy: ComputedRef<boolean>;
} {
  const mode = computed<PredictionDomainMode>(() => (card.value.active_panel === "batch" ? "batch" : "single"));
  const batch = computed(() => card.value.batch);
  const batchBusy = computed(() => Boolean(batch.value?.checkRunning || batch.value?.runRunning));
  const singleBusy = computed(() => Boolean(card.value.predictRunning));
  const anyBusy = computed(() => batchBusy.value || singleBusy.value);
  return { mode, batch, batchBusy, singleBusy, anyBusy };
}
