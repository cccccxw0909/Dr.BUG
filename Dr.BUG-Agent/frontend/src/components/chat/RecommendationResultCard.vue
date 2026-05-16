<template>
  <div class="rec-primary-card">
    <p class="rec-result-summary">{{ i18nT("chat.recommendationResult.summaryLead") }}</p>

    <div v-if="rankedCandidates.length" class="rec-table-wrap">
      <table class="rec-table">
        <thead>
          <tr>
            <th class="col-rank">{{ i18nT("chat.recommendationResult.table.rank") }}</th>
            <th class="col-regimen">{{ i18nT("chat.recommendationResult.table.regimenName") }}</th>
            <th class="col-therapy">{{ i18nT("chat.recommendationResult.table.therapyDetails") }}</th>
            <th class="col-prob">{{ i18nT("chat.recommendationResult.table.modelEstimatedSurvivalProb") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(c, i) in rankedCandidates" :key="`${c.regimen_id || 'x'}-${i}`">
            <td class="col-rank">{{ i + 1 }}</td>
            <td class="col-regimen">
              <div class="cand-name">{{ candidateDisplayName(c) }}</div>
            </td>
            <td class="col-therapy">
              <div v-if="candidateLines(c).length" class="cand-treat">
                <span v-for="(line, j) in candidateLines(c)" :key="j" class="cand-treat-line">{{ line }}</span>
              </div>
              <div
                v-else-if="(c.regimen_id || c.regimen_name) && c.treatment_values != null && typeof c.treatment_values === 'object'"
                class="cand-treat cand-treat-muted"
              >
                {{ i18nT("chat.recommendationResult.noNonzeroTherapy") }}
              </div>
              <span v-else class="cand-treat-muted">—</span>
            </td>
            <td class="col-prob">{{ formatProbabilityPercent(c.predicted_probability) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else class="rec-empty-hint">{{ i18nT("chat.recommendationResult.emptyHint") }}</p>

    <div v-if="showBaselineComparison" class="rec-baseline-section">
      <div class="rec-baseline-row">
        <span class="rec-baseline-k">{{ i18nT("chat.recommendationResult.compare.observedBaseline") }}</span>
        <span class="rec-baseline-v">{{ formatProbabilityPercent(data.observed_prediction_probability) }}</span>
      </div>
      <div class="rec-baseline-row">
        <span class="rec-baseline-k">{{ i18nT("chat.recommendationResult.compare.top1Predicted") }}</span>
        <span class="rec-baseline-v">{{ formatProbabilityPercent(data.recommended_top1_probability) }}</span>
      </div>
      <div class="rec-baseline-row">
        <span class="rec-baseline-k">{{ i18nT("chat.recommendationResult.compare.deltaTop1") }}</span>
        <span class="rec-baseline-v">{{ formatDeltaPercentPoints(data.delta_probability_top1) }}</span>
      </div>
    </div>

    <p class="rec-disclaimer">{{ i18nT("chat.recommendationResult.researchDisclaimer") }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { RecommendationRegimenResultRow, SurvivalRecommendationResult } from "../../types";
import { dedupeTopCandidates } from "../../utils/recommendationCandidateUtils";
import { formatTreatmentValueLines } from "../../utils/recommendationTreatmentDisplay";

const props = defineProps<{ data: SurvivalRecommendationResult }>();

const { t: i18nT } = useI18n();

const showBaselineComparison = computed(() => {
  const o = props.data.observed_regimen;
  return o != null && typeof o === "object";
});

const rankedCandidates = computed((): RecommendationRegimenResultRow[] => {
  const d = dedupeTopCandidates(props.data.top_candidates);
  return [...d].sort((a, b) => {
    const pa = a.predicted_probability;
    const pb = b.predicted_probability;
    const na = pa === undefined || pa === null || Number.isNaN(Number(pa));
    const nb = pb === undefined || pb === null || Number.isNaN(Number(pb));
    if (na && nb) return 0;
    if (na) return 1;
    if (nb) return -1;
    return Number(pb) - Number(pa);
  });
});

function candidateDisplayName(c: RecommendationRegimenResultRow): string {
  const name = (c.regimen_name || "").trim();
  return name || i18nT("common.na");
}

function candidateLines(c: RecommendationRegimenResultRow): string[] {
  return formatTreatmentValueLines(c.treatment_values, i18nT);
}

function formatProbabilityPercent(v: number | undefined): string {
  if (v === undefined || v === null || Number.isNaN(Number(v))) return i18nT("common.na");
  const n = Number(v);
  return `${(n * 100).toFixed(1)}%`;
}

function formatDeltaPercentPoints(v: number | undefined): string {
  if (v === undefined || v === null || Number.isNaN(Number(v))) return i18nT("common.na");
  const n = Number(v);
  const sign = n > 0 ? "+" : "";
  const body = `${sign}${(n * 100).toFixed(1)}`;
  return `${body}%`;
}
</script>

<style scoped>
.rec-primary-card {
  box-sizing: border-box;
  width: 100%;
  max-width: var(--wb-chat-workflow-card-max);
  margin: 4px 0 0;
  padding: 24px 28px 28px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  /* Match .chat-bubble (ChatMessageList) so embedded result reads like assistant prose */
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
}

.rec-result-summary {
  margin: 0 0 18px;
  color: #1f2937;
}

.rec-table-wrap {
  width: 100%;
  margin-bottom: 18px;
}

.rec-table {
  width: 100%;
  border-collapse: collapse;
}

.rec-table th,
.rec-table td {
  border: 1px solid var(--wb-border);
  padding: 11px 13px;
  text-align: left;
  vertical-align: middle;
}

.rec-table th {
  background: #f9fafb;
  font-weight: 600;
  color: #111827;
}

.col-rank {
  width: 48px;
  white-space: nowrap;
}

.col-prob {
  width: 128px;
  white-space: nowrap;
}

.cand-name {
  font-weight: 600;
  color: var(--wb-text-primary);
}

.cand-treat {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #1f2937;
}

.cand-treat-muted {
  color: #6b7280;
  font-style: italic;
}

.rec-empty-hint {
  margin: 0 0 16px;
  color: #6b7280;
}

.rec-baseline-section {
  margin: 0 0 18px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
  color: #1f2937;
}

.rec-baseline-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-bottom: 6px;
  align-items: baseline;
}

.rec-baseline-row:last-child {
  margin-bottom: 0;
}

.rec-baseline-k {
  min-width: 200px;
  font-weight: 600;
  color: #374151;
}

.rec-baseline-v {
  font-variant-numeric: tabular-nums;
}

.rec-disclaimer {
  margin: 0;
  color: var(--wb-text-secondary);
}
</style>
