<template>
  <div class="pss-card">
    <section class="pss-section pss-overview">
      <div class="pss-section-title">{{ i18nT("chat.predictionSubmittedSummary.sectionOverview") }}</div>
      <div class="pss-kv-grid">
        <div class="pss-kv">
          <span class="pss-k">{{ i18nT("chat.batchPrediction.labels.model") }}</span>
          <span class="pss-v">{{ friendlyModelName }}</span>
        </div>
        <div class="pss-kv">
          <span class="pss-k">{{ i18nT("chat.predictionSubmittedSummary.labels.algorithm") }}</span>
          <span class="pss-v">{{ algorithmDisplay }}</span>
        </div>
        <div class="pss-kv">
          <span class="pss-k">{{ i18nT("chat.predictionSubmittedSummary.labels.task") }}</span>
          <span class="pss-v">{{ taskDisplay }}</span>
        </div>
        <div class="pss-kv">
          <span class="pss-k">{{ i18nT("chat.predictionSubmittedSummary.labels.mode") }}</span>
          <span class="pss-v">{{ i18nT("chat.predictionSubmittedSummary.modeSingle") }}</span>
        </div>
      </div>
    </section>

    <section class="pss-section pss-fields-block">
      <div class="pss-section-title">{{ i18nT("chat.predictionSubmittedSummary.sectionFields") }}</div>
      <p v-if="variablesCompletionSummary" class="pss-fields-status">{{ variablesCompletionSummary }}</p>
      <div class="pss-field-grid">
        <div v-for="row in data.field_rows" :key="row.name" class="pss-field-cell">
          <div class="pss-field-label">{{ row.label }}</div>
          <div class="pss-field-value">{{ row.value }}</div>
        </div>
      </div>
    </section>

    <p v-if="data.status === 'pending'" class="pss-hint">{{ i18nT("chat.predictionSubmittedSummary.hintPending") }}</p>
    <p v-else-if="data.status === 'failed' && data.error_message" class="pss-err">{{ data.error_message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { PredictionSubmittedSummaryPayload } from "../../types";
import {
  extractKnownAlgorithmName,
  inferSubmittedSummaryModelKind,
} from "../../utils/predictionSubmittedSummaryPresentation";

const props = defineProps<{ data: PredictionSubmittedSummaryPayload }>();

const { t: i18nT } = useI18n();

const modelKind = computed(() =>
  inferSubmittedSummaryModelKind({
    task_name: props.data.task_name,
    model_display_name: props.data.model_display_name,
    model_id: props.data.model_id,
  }),
);

const friendlyModelName = computed(() =>
  i18nT(`chat.predictionSubmittedSummary.friendlyModel.${modelKind.value}`),
);

const algorithmDisplay = computed(() => {
  const name = extractKnownAlgorithmName(
    String(props.data.model_display_name || ""),
    String(props.data.model_id || ""),
  );
  return name || i18nT("common.na");
});

function looksLikeModelRegistrySlug(s: string): boolean {
  return /_cand_\d+_/i.test(s) || /_(binary|multiclass)_classification$/i.test(s);
}

/** User-facing task line; omit values that duplicate internal model registry IDs. */
const taskDisplay = computed(() => {
  const raw = String(props.data.task_name || "").trim();
  if (!raw) return i18nT("common.na");
  const mid = String(props.data.model_id || "").trim();
  if (mid && raw === mid) return i18nT("common.na");
  if (looksLikeModelRegistrySlug(raw)) return i18nT("common.na");
  return raw;
});

const variablesCompletionSummary = computed(() => {
  const rows = props.data.field_rows || [];
  const total = rows.length;
  if (total < 1) return "";
  const filled = rows.filter((r) => {
    const v = String(r.value ?? "").trim();
    return v !== "" && v !== "—";
  }).length;
  return String(
    i18nT("chat.predictionSubmittedSummary.completedVariablesSummary", {
      filled,
      total,
    }),
  );
});
</script>

<style scoped>
/** Root is content-only; outer white report card comes from ChatMessageList `.chat-embed-card`. */
.pss-card {
  max-width: 100%;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
}
.pss-overview {
  margin-bottom: 0;
}
.pss-section {
  margin-bottom: var(--wb-space-2);
}
.pss-fields-block {
  margin-top: var(--wb-space-2);
  margin-bottom: 0;
  padding-top: var(--wb-space-2);
  border-top: 1px solid #e8ebef;
}
.pss-fields-status {
  margin: 0 0 var(--wb-space-2);
  font-size: 15px;
  line-height: 1.45;
  font-weight: 500;
  color: var(--wb-embed-submission-copy);
}
.pss-section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--wb-embed-submission-copy);
  letter-spacing: 0.02em;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(55, 71, 79, 0.12);
}
.pss-kv-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-1) var(--wb-space-2);
  font-size: 15px;
}
@media (min-width: 720px) {
  .pss-kv-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.pss-kv {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-micro);
  min-width: 0;
}
.pss-k {
  color: var(--wb-embed-submission-copy);
  font-weight: 600;
  font-size: 15px;
}
.pss-v {
  color: var(--wb-embed-submission-copy);
  font-weight: 400;
  word-break: break-word;
  font-size: 15px;
}

.pss-field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-1) var(--wb-chat-input-padding-y);
}
@media (min-width: 640px) {
  .pss-field-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (min-width: 1100px) {
  .pss-field-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.pss-field-cell {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: var(--wb-radius-xs);
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
  min-width: 0;
  box-sizing: border-box;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
}
.pss-field-label {
  font-size: 15px;
  color: var(--wb-embed-submission-copy);
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0;
}
.pss-field-value {
  margin-top: 4px;
  font-size: 15px;
  font-weight: 400;
  line-height: 1.4;
  letter-spacing: 0;
  color: var(--wb-embed-submission-copy);
  word-break: break-word;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}
.pss-hint {
  margin: var(--wb-space-1) 0 0;
  font-size: 14px;
  color: var(--wb-embed-submission-copy);
  font-weight: 600;
}
.pss-err {
  margin: var(--wb-space-1) 0 0;
  font-size: 14px;
  color: #b00020;
}
</style>
