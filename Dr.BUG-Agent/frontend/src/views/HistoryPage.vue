<template>
  <div class="history-page">
    <header class="history-header">
      <h2 class="wb-section-title">{{ $t("pages.history.title") }}</h2>
      <p class="history-subtitle">{{ $t("pages.history.subtitle") }}</p>
    </header>

    <section class="history-filter wb-card">
      <select v-model="filterType" class="history-field">
        <option value="">{{ $t("pages.history.filters.allTypes") }}</option>
        <option value="single">{{ $t("pages.history.filters.single") }}</option>
        <option value="batch">{{ $t("pages.history.filters.batch") }}</option>
      </select>
      <input v-model.trim="filterTask" class="history-field" :placeholder="$t('pages.history.filters.taskPlaceholder')" />
      <input v-model.trim="filterModel" class="history-field" :placeholder="$t('pages.history.filters.modelPlaceholder')" />
      <button type="button" class="wb-btn wb-btn-secondary wb-btn-toolbar" @click="reload">{{ $t("pages.history.filters.query") }}</button>
    </section>

    <div class="history-content">
      <section class="history-list wb-card">
        <div class="history-panel-head">{{ $t("pages.history.panels.list") }}</div>
        <div v-if="loading" class="history-msg">{{ $t("pages.history.loading") }}</div>
        <div v-else-if="error" class="history-msg history-msg-error">{{ error }}</div>
        <div v-else-if="items.length === 0" class="history-msg">{{ $t("pages.history.empty") }}</div>
        <button
          v-for="it in items"
          :key="it.record_id"
          type="button"
          class="history-item"
          :class="{ 'history-item-active': selectedId === it.record_id }"
          @click="selectRecord(it.record_id)"
        >
          <div class="history-item-time">
            <span class="history-item-type-chip">{{ it.type === "single" ? $t("pages.history.labels.singleChip") : $t("pages.history.labels.batchChip") }}</span>
            <span>{{ formatTs(it.timestamp) }}</span>
          </div>
          <div class="history-item-title">{{ it.type === "single" ? $t("pages.history.labels.singleTitle") : $t("pages.history.labels.batchTitle") }}</div>
          <div class="history-item-model">{{ it.display_name || it.model_id }}</div>
          <div class="history-item-summary">{{ formatPredictionHistoryListLine(it, tFn) }}</div>
        </button>
      </section>

      <section class="history-detail wb-card">
        <div class="history-panel-head">{{ $t("pages.history.panels.detail") }}</div>
        <div v-if="detailLoading" class="history-msg">{{ $t("pages.history.detailLoading") }}</div>
        <div v-else-if="detailError" class="history-msg history-msg-error">{{ detailError }}</div>
        <template v-else-if="detail">
          <div class="history-detail-time">{{ formatTs(detail.timestamp) }}</div>
          <h3 class="history-detail-title">{{ detail.type === "single" ? $t("pages.history.labels.singleTitle") : $t("pages.history.labels.batchTitle") }}</h3>
          <div class="history-detail-kv">
            <div class="history-detail-kv-row"><span class="history-detail-kv-key">{{ $t("pages.history.labels.task") }}</span><span>{{ detail.task_name || $t("pages.history.labels.na") }}</span></div>
            <div class="history-detail-kv-row"><span class="history-detail-kv-key">{{ $t("pages.history.labels.model") }}</span><span>{{ detail.display_name || detail.model_id }}</span></div>
          </div>

          <template v-if="detail.type === 'single'">
            <div v-if="singleHistorySurface" class="history-conclusion-block">
              <p class="history-report-paragraph">
                <template v-if="historyIsRegression">
                  <I18nT v-if="historyHasProbability" keypath="prediction.explanation.reportSummary.regressionLeadProb" tag="span">
                    <template #lead>
                      <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
                    </template>
                    <template #conclusion>
                      <strong>{{ singleHistorySurface.conclusionPrimary }}</strong>
                    </template>
                    <template #probability>
                      <strong>{{ historyProbabilityPercentStr }}</strong>
                    </template>
                  </I18nT>
                  <I18nT v-else keypath="prediction.explanation.reportSummary.regressionLeadNoProb" tag="span">
                    <template #lead>
                      <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
                    </template>
                    <template #conclusion>
                      <strong>{{ singleHistorySurface.conclusionPrimary }}</strong>
                    </template>
                  </I18nT>
                </template>
                <template v-else>
                  <I18nT v-if="historyHasProbability" keypath="prediction.explanation.reportSummary.classificationLeadProb" tag="span">
                    <template #lead>
                      <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
                    </template>
                    <template #label>
                      <strong>{{ singleHistorySurface.conclusionPrimary }}</strong>
                    </template>
                    <template #probability>
                      <strong>{{ historyProbabilityPercentStr }}</strong>
                    </template>
                  </I18nT>
                  <I18nT v-else keypath="prediction.explanation.reportSummary.classificationLeadNoProb" tag="span">
                    <template #lead>
                      <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
                    </template>
                    <template #label>
                      <strong>{{ singleHistorySurface.conclusionPrimary }}</strong>
                    </template>
                  </I18nT>
                </template>
                <template v-if="historyMainContributingVariablesLine">
                  {{ " " }}
                  <span>{{ t("prediction.explanation.reportSummary.varsClause", { variables: historyMainContributingVariablesLine }) }}</span>
                </template>
                <template v-if="historyShowWaterfallTail">
                  {{ " " }}
                  <span>{{ t("prediction.explanation.reportSummary.waterfallTail") }}</span>
                </template>
              </p>
            </div>
            <div v-if="detail.waterfall_image_url" class="history-waterfall-block">
              <div class="history-fig-frame">
                <img :src="detail.waterfall_image_url" :alt="$t('pages.history.detail.waterfallAlt')" class="history-image" />
              </div>
            </div>
            <div v-else-if="singleHistorySurface" class="history-msg">{{ $t("pages.history.detail.noExplanationImages") }}</div>
          </template>

          <template v-else>
            <div class="history-detail-kv history-detail-row-gap">
              <div class="history-detail-kv-row"><span class="history-detail-kv-key">{{ $t("pages.history.labels.file") }}</span><span>{{ detail.file_name }}</span></div>
              <div class="history-detail-kv-row"><span class="history-detail-kv-key">{{ $t("pages.history.labels.totalRows") }}</span><span>{{ detail.total_rows }}</span></div>
              <div class="history-detail-kv-row"><span class="history-detail-kv-key">{{ $t("pages.history.labels.succeeded") }}</span><span>{{ detail.succeeded_rows }}</span></div>
              <div class="history-detail-kv-row"><span class="history-detail-kv-key">{{ $t("pages.history.labels.failed") }}</span><span>{{ detail.failed_rows }}</span></div>
            </div>
            <div class="history-detail-link">
              <a :href="detail.download_url" target="_blank" rel="noopener">{{ $t("pages.history.labels.download") }}</a>
            </div>
            <details v-if="detail.field_check_summary" class="history-fold-muted">
              <summary>{{ $t("pages.history.labels.supplementColumnMapping") }}</summary>
              <div class="history-detail-inline">{{ historyBatchFieldCheckLine }}</div>
            </details>
          </template>

          <details v-if="historyWarningBlocks.length" class="history-warning-fold" open>
            <summary>{{ $t("prediction.explanation.variablesHandledByPreprocessing") }}</summary>
            <div class="history-warning-body">
              <p v-for="(block, idx) in historyWarningBlocks" :key="idx">{{ block }}</p>
            </div>
          </details>
        </template>
        <div v-else class="history-msg">{{ $t("pages.history.pickHint") }}</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { I18nT, useI18n } from "vue-i18n";
import { ApiError, getPredictionHistory, getPredictionHistoryDetail } from "../api";
import type { PredictionFieldSchema, PredictionHistoryListItem, PredictionHistoryRecord } from "../types";
import { formatDisplayDateTime } from "../utils/dateFormat";
import {
  formatClinicalPredictionSurface,
  formatHistoryBatchFieldCheckLine,
  formatPredictionHistoryListLine,
} from "../utils/predictionPresentation";
import {
  featureLabelForPreprocessingNote,
  formatPredictionDataPreprocessingNotes,
  joinVariableLabels,
} from "../utils/predictionPreprocessingNotes";

const { t, locale } = useI18n();
type Translate = (key: string, values?: Record<string, unknown>) => string;
const tFn: Translate = (key, values) => t(key, values);

const items = ref<PredictionHistoryListItem[]>([]);
const loading = ref(false);
const error = ref("");
const selectedId = ref<string | null>(null);
const detail = ref<PredictionHistoryRecord | null>(null);
const detailLoading = ref(false);
const detailError = ref("");

const filterType = ref<"" | "single" | "batch">("");
const filterTask = ref("");
const filterModel = ref("");

const historyPseudoSchemaFields = computed((): PredictionFieldSchema[] => {
  const d = detail.value;
  if (!d || d.type !== "single") return [];
  const o = d.input_summary || {};
  const names = new Set<string>(Object.keys(o));
  for (const x of d.top_features || []) {
    if (x?.name) names.add(String(x.name));
  }
  return [...names].map((name) => ({ name, label: "", type: "string", required: false }));
});

const historyBatchFieldCheckLine = computed(() => {
  const d = detail.value;
  if (!d || d.type !== "batch" || !d.field_check_summary) return "";
  const s = d.field_check_summary;
  return formatHistoryBatchFieldCheckLine(s.matched_count, s.missing_count, s.extra_count, tFn);
});

const historyMainContributingVariablesLine = computed(() => {
  const d = detail.value;
  if (!d || d.type !== "single" || !d.top_features?.length) return "";
  const loc = String(locale.value || "");
  const names = d.top_features.slice(0, 6).map((x) => String(x.name));
  const labels = names.map((n) => featureLabelForPreprocessingNote(n, historyPseudoSchemaFields.value, loc));
  return joinVariableLabels(labels, loc);
});

const historyIsRegression = computed(() => {
  const d = detail.value;
  if (!d || d.type !== "single") return false;
  return d.predicted_probability == null && d.predicted_value != null;
});

const historyHasProbability = computed(() => {
  const d = detail.value;
  if (!d || d.type !== "single") return false;
  const p = d.predicted_probability;
  return p != null && !Number.isNaN(Number(p));
});

const historyProbabilityPercentStr = computed(() => {
  const d = detail.value;
  if (!d || d.type !== "single" || d.predicted_probability == null || Number.isNaN(Number(d.predicted_probability))) return "";
  return `${(Number(d.predicted_probability) * 100).toFixed(2)}%`;
});

const historyShowWaterfallTail = computed(() => Boolean(detail.value?.type === "single" && detail.value.waterfall_image_url));

const historyWarningBlocks = computed(() => {
  const d = detail.value;
  if (!d?.warnings?.length) return [];
  return formatPredictionDataPreprocessingNotes(d.warnings, {
    locale: String(locale.value || ""),
    t: tFn,
    schemaFields: d.type === "single" ? historyPseudoSchemaFields.value : null,
  });
});

const singleHistorySurface = computed(() => {
  const d = detail.value;
  if (!d || d.type !== "single") return null;
  const isReg = d.predicted_probability == null && d.predicted_value != null;
  return formatClinicalPredictionSurface({
    ok: true,
    model_id: d.model_id,
    display_name: d.display_name,
    task_name: d.task_name,
    prediction_type: isReg ? "regression" : "classification",
    predicted_label: d.predicted_label,
    predicted_probability: d.predicted_probability ?? null,
    predicted_value: d.predicted_value ?? null,
    label_display: String(d.predicted_label ?? ""),
    outcome_display: String(d.predicted_label ?? ""),
    feature_values_used: {},
    warnings: d.warnings || [],
    timestamp: d.timestamp,
  });
});

function formatTs(v: string): string {
  return formatDisplayDateTime(v);
}

async function selectRecord(id: string) {
  selectedId.value = id;
  detailLoading.value = true;
  detailError.value = "";
  try {
    detail.value = await getPredictionHistoryDetail(id);
  } catch (e) {
    detail.value = null;
    detailError.value =
      e instanceof ApiError ? tFn("pages.history.detail.errorWithCode", { message: e.message, code: e.code }) : String(e);
  } finally {
    detailLoading.value = false;
  }
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    const data = await getPredictionHistory({
      type: filterType.value || undefined,
      task: filterTask.value || undefined,
      model: filterModel.value || undefined,
    });
    items.value = data.items || [];
    if (items.value.length > 0) {
      if (!selectedId.value || !items.value.some((x) => x.record_id === selectedId.value)) {
        await selectRecord(items.value[0].record_id);
      }
    } else {
      selectedId.value = null;
      detail.value = null;
    }
  } catch (e) {
    error.value =
      e instanceof ApiError ? tFn("pages.history.detail.errorWithCode", { message: e.message, code: e.code }) : String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void reload();
});
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.history-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-1);
}

.history-subtitle {
  margin: 0;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
}

.history-filter {
  flex-shrink: 0;
  padding: var(--wb-space-3);
  display: flex;
  gap: var(--wb-space-2);
  flex-wrap: wrap;
  align-items: center;
}

.history-field {
  height: var(--wb-control-height-sm);
  min-height: var(--wb-control-height-sm);
  font-size: var(--wb-font-size-sm);
  min-width: 150px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: 0 var(--wb-chat-bubble-padding-x);
  background: var(--wb-surface);
  color: var(--wb-text-primary);
}

.history-content {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-3);
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.history-list,
.history-detail {
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--wb-space-3);
}

.history-panel-head {
  margin-bottom: var(--wb-space-2);
  font-size: var(--wb-font-size-md);
  font-weight: 650;
}

.history-msg {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
  padding: var(--wb-space-2) 0;
}

.history-msg-error {
  color: var(--wb-error);
}

.history-item {
  width: 100%;
  text-align: left;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-2);
  margin-bottom: var(--wb-space-2);
  background: var(--wb-surface);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.history-item:hover {
  border-color: var(--wb-border-strong);
  background: var(--wb-surface-soft);
}

.history-item-active {
  border-color: #c8d3e0;
  background: var(--wb-accent-soft);
}

.history-item-time {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--wb-chat-input-padding-y);
}

.history-item-type-chip {
  display: inline-flex;
  align-items: center;
  height: var(--wb-tag-height-compact);
  padding: 0 var(--wb-chat-input-padding-y);
  border-radius: 999px;
  border: 1px solid #d5deea;
  background: #f3f7fc;
  color: #52667f;
}

.history-item-title {
  margin-top: var(--wb-chat-bubble-gap);
  font-size: var(--wb-font-size-sm);
  font-weight: 650;
}

.history-item-model,
.history-item-summary {
  margin-top: var(--wb-space-micro);
  font-size: var(--wb-font-size-xs);
  color: #3f4652;
}

.history-detail-time {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.history-detail-title {
  margin: var(--wb-space-1) 0 var(--wb-chat-input-padding-y) 0;
  font-size: var(--wb-font-size-md);
}

.history-detail-row {
  font-size: var(--wb-font-size-sm);
  line-height: 1.6;
}

.history-detail-kv {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-1) var(--wb-chat-input-padding-x);
  margin-top: var(--wb-space-1);
}

.history-detail-kv-row {
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  align-items: baseline;
  font-size: var(--wb-font-size-sm);
}

.history-detail-kv-key {
  min-width: var(--wb-kv-key-min-width);
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
}

.history-detail-row-gap {
  margin-top: var(--wb-space-2);
}

.history-detail-inline {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
  color: #3f4652;
}
.history-alias {
  margin-bottom: var(--wb-space-2);
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
  background: #fff;
  border: 1px dashed #b0bec5;
  border-radius: var(--wb-radius-xs);
}
.history-alias-title {
  font-size: var(--wb-font-size-2xs);
  font-weight: 600;
  color: #455a64;
  margin-bottom: var(--wb-space-micro);
}
.history-alias-list {
  margin: 0;
  padding-left: var(--wb-space-3);
  font-size: var(--wb-font-size-2xs);
  line-height: 1.55;
}
.history-alias-raw {
  font-size: var(--wb-font-size-2xs);
  background: #eceff1;
  padding: 0 4px;
  border-radius: 3px;
}

.history-waterfall-block {
  margin-top: var(--wb-space-3);
}
.history-fig-frame {
  overflow: auto;
  max-height: min(260px, 46vh);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: #fff;
}
.history-image {
  display: block;
  max-width: 100%;
  width: auto;
  height: auto;
  max-height: min(248px, 44vh);
  object-fit: contain;
  margin: 0 auto;
}

.history-detail-link {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-sm);
}

.history-warning-fold {
  margin-top: var(--wb-space-2);
  font-size: 14px;
  color: var(--wb-text-primary);
}
.history-warning-fold summary {
  cursor: pointer;
  font-weight: 700;
  font-size: 15px;
  color: #263238;
}
.history-warning-body {
  margin-top: var(--wb-space-1);
  line-height: 1.55;
}
.history-warning-body p {
  margin: 0 0 0.5em;
  font-size: 14px;
  color: var(--wb-text-primary);
}
.history-warning-body p:last-child {
  margin-bottom: 0;
}

.history-fold-muted {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}
.history-fold-muted summary {
  cursor: pointer;
  font-weight: 600;
}

.history-conclusion-block {
  margin-top: var(--wb-space-2);
  padding: 0;
  border: none;
  background: transparent;
}
.history-report-paragraph {
  margin: 0;
  font-size: var(--wb-font-size-md);
  font-weight: 400;
  line-height: 1.55;
  color: var(--wb-text-primary);
  word-break: break-word;
}

@media (max-width: 1260px) {
  .history-content {
    grid-template-columns: 1fr;
  }

  .history-detail-kv {
    grid-template-columns: 1fr;
  }
}
</style>

