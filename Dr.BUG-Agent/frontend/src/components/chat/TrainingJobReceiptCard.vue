<template>
  <div class="receipt-card" :class="{ 'receipt-card--embedded': embedded }">
    <div class="receipt-head">
      <div class="receipt-title">{{ data.title }}</div>
      <span class="receipt-state">{{ friendlyTaskStatus }}</span>
    </div>

    <div class="receipt-intro" role="region" :aria-label="t('training.receiptCard.introAriaLabel')">
      <p v-for="(line, idx) in receiptIntroLines" :key="`intro-${idx}`" class="receipt-intro-p">{{ line }}</p>
    </div>

    <div class="receipt-note-row">
      <span
        ><b>{{ t("training.receiptCard.progressNoteBold") }}</b>{{ receiptProgressLine }}</span
      >
    </div>

    <ul class="receipt-summary">
      <li v-for="(line, i) in data.summary_lines" :key="i">{{ line }}</li>
    </ul>

    <div class="receipt-preview-box receipt-preview-box--always">
      <div class="receipt-preview-heading">{{ t("training.receiptCard.previewHeading") }}</div>
      <div v-if="previewLoading" class="receipt-preview-empty">{{ t("training.receiptCard.previewLoading") }}</div>
      <div v-else-if="previewError" class="receipt-preview-empty">{{ previewError }}</div>
      <template v-else-if="previewData">
        <div class="receipt-preview-scale">
          <template v-if="previewUsesFeatureSubset">
            <span v-if="previewScaleConfirmed">{{ t("training.receiptCard.previewScaleConfirmed", previewScaleParams) }}</span>
            <span v-else>{{ t("training.receiptCard.previewScaleSelectedFeatures", previewScaleParams) }}</span>
          </template>
          <span v-else>{{ t("training.receiptCard.previewRowsColsValue", previewScaleParams) }}</span>
        </div>
        <div v-if="previewData.missing_overview && previewData.missing_overview.length" class="receipt-preview-block">
          <b>{{ t("training.receiptCard.missingOverviewTop") }}</b>
          <span>{{ missingOverviewPreviewText }}</span>
        </div>
        <div
          v-if="previewData.label_distribution && Object.keys(previewData.label_distribution).length"
          class="receipt-preview-block"
        >
          <span>{{ formattedLabelDistribution }}</span>
        </div>
        <div v-if="previewData.rows.length && displayPreviewHeaders.length" class="receipt-preview-table-wrap">
          <table class="receipt-preview-table">
            <thead class="receipt-preview-thead">
              <tr>
                <th v-for="col in displayPreviewHeaders" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in previewData.rows" :key="idx">
                <td v-for="col in displayPreviewHeaders" :key="`${idx}-${col}`">
                  {{ formatPreviewCell(row, col, idx) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="receipt-preview-empty">{{ t("training.receiptCard.noPreview") }}</div>
    </div>
    <div v-if="data.next_hint" class="receipt-next-hint">{{ data.next_hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { getDatasetPreview } from "../../api";
import type { DatasetPreviewInfo, TrainingJobReceiptData } from "../../types";
import { formatMissingOverviewPairs } from "../../utils/labelValueTypography";
import { formatTrainingLabelDistribution } from "../../utils/trainingLabelDistribution";
import { formatTaskStatusLabel } from "../../utils/taskPresentation";

const props = defineProps<{ data: TrainingJobReceiptData; embedded?: boolean }>();
const { t, locale } = useI18n();
const previewLoading = ref(false);
const previewError = ref("");
const previewData = ref<DatasetPreviewInfo | null>(null);
const friendlyTaskStatus = computed(() => formatTaskStatusLabel(String(props.data.task_status || ""), t));

const mergedPayload = computed(() =>
  props.data.merged_payload_snapshot && typeof props.data.merged_payload_snapshot === "object"
    ? (props.data.merged_payload_snapshot as Record<string, unknown>)
    : {},
);

const receiptFeatureScreeningEnabled = computed(() => Boolean(mergedPayload.value.use_cv_shap));
const receiptIntroLines = computed(() =>
  ["training.receiptCard.introP1", "training.receiptCard.introP2", "training.receiptCard.introP3"]
    .map((k) => String(t(k)).trim())
    .filter(Boolean),
);

const receiptProgressLine = computed(() =>
  receiptFeatureScreeningEnabled.value
    ? t("training.receiptCard.progressFeatureScreening")
    : t("training.receiptCard.progressTrainingPrep"),
);

function normalizeFeatureList(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const x of raw) {
    const s = String(x ?? "").trim();
    if (!s || seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
}

const PREVIEW_ROW_INDEX_HEADER = "#";

/** Ordered columns for API request and table body: # → selected candidates → required (med_cols) → outcome (deduped). If final_features exist, use that ordering instead. */
const previewFeatureColumns = computed(() => {
  const p = mergedPayload.value;
  const finals = normalizeFeatureList(p.final_features);
  const target = String(p.target_column || "").trim();

  if (finals.length > 0) {
    const seen = new Set<string>();
    const ordered: string[] = [];
    for (const c of finals) {
      if (seen.has(c)) continue;
      seen.add(c);
      ordered.push(c);
    }
    if (target && !seen.has(target)) ordered.push(target);
    return ordered;
  }

  const selectedOrdered = normalizeFeatureList(p.selected_features).filter((c) => c !== target);
  const requiredRaw = normalizeFeatureList(p.med_cols).filter((c) => c !== target);
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const c of selectedOrdered) {
    if (seen.has(c)) continue;
    seen.add(c);
    ordered.push(c);
  }
  for (const c of requiredRaw) {
    if (seen.has(c)) continue;
    seen.add(c);
    ordered.push(c);
  }
  if (target && !seen.has(target)) ordered.push(target);
  return ordered;
});

const previewUsesFeatureSubset = computed(() => previewFeatureColumns.value.length > 0);

const previewScaleConfirmed = computed(() => normalizeFeatureList(mergedPayload.value.final_features).length > 0);

const previewFeatureCountExcludingOutcome = computed(() => {
  const cols = previewFeatureColumns.value;
  const target = String(mergedPayload.value.target_column || "").trim();
  if (!cols.length) return 0;
  const hasOutcome = Boolean(target && cols.includes(target));
  return Math.max(0, cols.length - (hasOutcome ? 1 : 0));
});

const previewScaleParams = computed(() => {
  const rows = previewData.value?.row_count ?? 0;
  const cols = previewData.value?.column_count ?? 0;
  const fc = previewFeatureCountExcludingOutcome.value;
  return {
    n: rows,
    rows,
    cols,
    featureCount: fc,
    rowCount: rows,
  };
});

/** Table headers: display-only index column + modeling columns (never ask API for "#"). */
const displayPreviewHeaders = computed(() => {
  if (previewUsesFeatureSubset.value) {
    return [PREVIEW_ROW_INDEX_HEADER, ...previewFeatureColumns.value];
  }
  const r = previewData.value?.rows || [];
  if (r.length === 0) return [];
  return Object.keys(r[0] || {});
});

const previewRequestKey = computed(
  () =>
    `${props.data.job_id}|${String(mergedPayload.value.dataset_id || "").trim()}|${previewFeatureColumns.value.join("\u001f")}|${String(mergedPayload.value.target_column || "").trim()}`,
);

const formattedLabelDistribution = computed(() => {
  const p = previewData.value;
  if (!p?.label_distribution) return "";
  return formatTrainingLabelDistribution(
    p.label_distribution,
    mergedPayload.value.clinical_task_id,
    p.target_column ?? mergedPayload.value.target_column,
    mergedPayload.value,
    t,
  );
});

const missingOverviewPreviewText = computed(() => {
  const mo = previewData.value?.missing_overview;
  if (!mo?.length) return "";
  return formatMissingOverviewPairs(mo.slice(0, 5), String(locale.value || ""));
});

function formatCell(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function formatPreviewCell(row: Record<string, unknown>, col: string, rowIdx: number): string {
  if (col === PREVIEW_ROW_INDEX_HEADER) return String(rowIdx + 1);
  return formatCell(row[col]);
}

async function loadPreview() {
  const datasetId = String(mergedPayload.value.dataset_id || "").trim();
  const target = String(mergedPayload.value.target_column || "").trim();
  if (!datasetId) {
    previewError.value = t("training.receiptCard.missingDatasetId");
    previewData.value = null;
    return;
  }
  previewLoading.value = true;
  previewError.value = "";
  try {
    const cols = previewFeatureColumns.value;
    const resp = await getDatasetPreview(datasetId, {
      targetColumn: target || undefined,
      limit: 8,
      columns: cols.length ? cols : undefined,
    });
    previewData.value = resp.preview;
  } catch {
    previewError.value = t("training.receiptCard.noPreview");
    previewData.value = null;
  } finally {
    previewLoading.value = false;
  }
}

watch(
  () => previewRequestKey.value,
  () => {
    previewData.value = null;
    void loadPreview();
  },
  { immediate: true },
);
</script>

<style scoped>
.receipt-card {
  margin-top: 6px;
  border: 1px solid #e5e9ef;
  background: #fff;
  padding: 10px;
  border-radius: 8px;
}

.receipt-card--embedded {
  margin-top: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.receipt-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.receipt-title {
  font-weight: 650;
  color: var(--wb-text-main);
  font-size: var(--wb-font-size-card-title);
  line-height: var(--wb-line-height-card);
}

.receipt-state {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: var(--wb-font-size-caption);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
  border: 1px solid #e5e7eb;
  background: #f9fafb;
}

.receipt-intro {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e8ecf2;
  background: #f8fafc;
}

.receipt-intro-p {
  margin: 0 0 0.65em;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
}

.receipt-intro-p:last-child {
  margin-bottom: 0;
}

.receipt-note-row {
  margin-top: 10px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-body-secondary);
}

.receipt-summary {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}

.receipt-preview-heading {
  font-weight: 650;
  font-size: var(--wb-font-size-card-body);
  color: var(--wb-text-main);
  margin-bottom: 6px;
}

.receipt-preview-scale {
  margin-bottom: 6px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}

.receipt-preview-box {
  margin-top: 10px;
  padding: 8px;
  background: #fff;
  border: 1px solid #d7dce4;
  border-radius: 6px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}

.receipt-preview-box--always {
  margin-top: 10px;
}

.receipt-preview-empty {
  color: var(--wb-text-caption-muted);
}

.receipt-preview-block {
  margin-top: 4px;
}

.receipt-preview-table-wrap {
  margin-top: 6px;
  overflow: auto;
  max-height: 220px;
  border: 1px solid #e6e9ee;
}

.receipt-preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
}

.receipt-preview-thead {
  position: sticky;
  top: 0;
  background: #f6f8fa;
}

.receipt-preview-table th {
  text-align: left;
  border-bottom: 1px solid #ddd;
  padding: 4px 6px;
}

.receipt-preview-table td {
  border-bottom: 1px solid #f0f0f0;
  padding: 4px 6px;
}

.receipt-next-hint {
  margin-top: 8px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}
</style>
