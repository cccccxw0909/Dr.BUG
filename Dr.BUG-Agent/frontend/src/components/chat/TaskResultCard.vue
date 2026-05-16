<template>
  <div
    class="task-result-card"
    :class="{ 'task-result-card-training-receipt': hasTrainingReceipt, 'task-result-card--embedded': embedded }"
  >
    <div v-if="showPrimaryCardTitle" class="task-result-title">{{ data.title }}</div>
    <div v-if="data.errorReason" class="task-result-error">{{ data.errorReason }}</div>

    <template v-if="hasTrainingReceipt">
      <div class="task-result-training-summary">
        <div class="task-result-receipt">
          <template v-if="trainingReceiptParagraphsHtml.length">
            <p
              v-for="(html, idx) in trainingReceiptParagraphsHtml"
              :key="'rcp-' + idx"
              class="task-result-receipt-p task-result-receipt-html-p"
              v-html="html"
            />
          </template>
          <template v-else>
            <p
              v-for="(para, idx) in data.trainingCompletedPresentation!.receiptParagraphs"
              :key="'rcp-' + idx"
              class="task-result-receipt-p"
            >
              {{ para }}
            </p>
          </template>
        </div>

        <div v-if="trainingShapMatch" class="task-result-training-block task-result-shap-block">
          <div class="task-result-training-section-title">{{ shapBeeswarmCaption }}</div>
          <div class="task-result-shap-figure">
            <img :src="trainingShapMatch.url" class="task-result-shap-img" :alt="shapBeeswarmCaption" />
          </div>
        </div>
        <div v-else-if="showTrainingShapUnavailable" class="task-result-training-block">
          <p class="task-result-shap-unavailable">{{ trainingShapUnavailableText }}</p>
        </div>

        <div v-if="showTrainingCandidateBlock" class="task-result-training-block">
          <div class="task-result-training-section-title">{{ t("task.resultCard.trainingReceipt.candidateCvComparisonTitle") }}</div>
          <p class="task-result-candidate-hint">{{ t("task.resultCard.trainingReceipt.candidateCvComparisonHint") }}</p>
          <p v-if="showTrainingCandidateErrorOnly" class="task-result-candidate-fallback">
            {{ t("task.resultCard.trainingReceipt.candidateCvComparisonLoadFailed") }}
          </p>
          <AllModelPerformanceTable
            v-else
            embedded
            workflow-table
            :artifacts="artifactMap"
            :result-summary="(props.data.resultSummary || {}) as Record<string, unknown>"
            :objective-metric="String((props.data.resultSummary || {}).primary_metric_requested || '')"
            :final-model="String((props.data.resultSummary || {}).trained_model_programmer_name || '')"
            :ml-task-type="String((props.data.resultSummary || {}).ml_task_type || '')"
            :workflow-selected-algorithm="trainingWorkflowSelectedAlgorithm"
            @evidence-state="onTrainingCandidateEvidence"
          />
        </div>
      </div>
    </template>

    <template v-else-if="isTrainingCompletedLegacyHeavy">
      <div
        v-if="(data.trainingCompletedPresentation!.summaryRows?.length ?? 0) > 0"
        class="task-result-presentation"
      >
        <div class="task-result-metrics-table-scroll">
          <table class="task-result-meta-table">
            <thead>
              <tr>
                <th
                  v-for="(row, idx) in data.trainingCompletedPresentation!.summaryRows"
                  :key="'sr-h-' + idx"
                >
                  {{ row.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td
                  v-for="(row, idx) in data.trainingCompletedPresentation!.summaryRows"
                  :key="'sr-v-' + idx"
                >
                  {{ row.value }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="featureSection" class="task-result-features">
        <div class="task-result-subtitle">{{ featureSection.title }}</div>
        <div class="task-result-chips">
          <span
            v-for="c in visibleFeatureChips"
            :key="c.raw"
            class="task-result-chip"
            :title="c.raw"
          >{{ c.display }}</span>
        </div>
        <button
          v-if="featureExpandable"
          type="button"
          class="wb-btn wb-btn-text wb-btn-sm task-result-features-toggle"
          @click="featuresExpanded = !featuresExpanded"
        >
          {{
            featuresExpanded
              ? t("task.resultCard.presentation.collapseAllFeatures")
              : t("task.resultCard.presentation.expandAllFeatures")
          }}
        </button>
      </div>

      <div v-if="horizontalTrainingMetrics.length > 0" class="task-result-metrics">
        <div class="task-result-subtitle">{{ t("task.resultCard.keyMetrics") }}</div>
        <div class="task-result-metrics-table-scroll">
          <table class="task-result-metrics-table">
            <thead>
              <tr>
                <th
                  v-for="col in horizontalTrainingMetrics"
                  :key="'h-' + col.key"
                  :class="{ 'task-result-metric-primary': col.isPrimary }"
                >
                  {{ col.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td
                  v-for="col in horizontalTrainingMetrics"
                  :key="'v-' + col.key"
                  :class="{ 'task-result-metric-primary': col.isPrimary }"
                >
                  {{ col.value }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <details v-if="trainingChartItems.length" class="task-result-charts">
        <summary>{{ t("task.resultCard.viewTrainingCharts") }}</summary>
        <div class="task-result-charts-grid">
          <div v-for="c in trainingChartItems" :key="c.url" class="task-result-chart-cell">
            <div class="task-result-chart-cap">{{ c.caption }}</div>
            <img :src="c.url" class="task-result-thumb-image" alt="" />
          </div>
        </div>
      </details>
    </template>

    <template v-else>
      <div v-if="horizontalTrainingMetrics.length > 0" class="task-result-metrics">
        <div class="task-result-subtitle">{{ t("task.resultCard.keyMetrics") }}</div>
        <div class="task-result-metrics-table-scroll">
          <table class="task-result-metrics-table">
            <thead>
              <tr>
                <th
                  v-for="col in horizontalTrainingMetrics"
                  :key="'h2-' + col.key"
                  :class="{ 'task-result-metric-primary': col.isPrimary }"
                >
                  {{ col.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td
                  v-for="col in horizontalTrainingMetrics"
                  :key="'v2-' + col.key"
                  :class="{ 'task-result-metric-primary': col.isPrimary }"
                >
                  {{ col.value }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else-if="metricEntries.length > 0" class="task-result-metrics">
        <div class="task-result-subtitle">{{ t("task.resultCard.keyMetrics") }}</div>
        <div v-for="([k, v]) in metricEntries" :key="k" class="task-result-metric-row">
          <span class="task-result-metric-key">{{ metricLabel(k) }}</span>
          <span class="task-result-metric-value">{{ metricValue(v) }}</span>
        </div>
      </div>

      <details class="task-result-tech">
        <summary>{{ t("task.resultCard.technicalDetails") }}</summary>
        <div class="task-result-tech-body">
          <div v-if="resultHeadlineDisplay" class="task-result-tech-block">
            <b>{{ t("task.resultCard.resultSummaryBold") }}</b>{{ resultHeadlineDisplay }}
          </div>
          <div v-if="artifactNames.length" class="task-result-artifact">
            <b>{{ t("task.resultCard.artifactsBold") }}</b>{{ t("task.resultCard.artifactsBody", { count: artifactNames.length }) }}
          </div>
          <div v-if="thumbnailUrl" class="task-result-thumb">
            <div class="task-result-subtitle">{{ t("task.resultCard.representativeChart") }}</div>
            <img :src="thumbnailUrl" class="task-result-thumb-image" alt="" />
          </div>
          <AllModelPerformanceTable
            :artifacts="artifactMap"
            :result-summary="(props.data.resultSummary || {}) as Record<string, unknown>"
            :objective-metric="String((props.data.resultSummary || {}).primary_metric_requested || '')"
            :final-model="String((props.data.resultSummary || {}).trained_model_programmer_name || '')"
            :ml-task-type="String((props.data.resultSummary || {}).ml_task_type || '')"
          />
        </div>
      </details>
    </template>

    <div v-if="data.nextStep && !hasTrainingReceipt" class="task-result-next">{{ data.nextStep }}</div>

    <div class="task-result-actions" :class="{ 'task-result-actions-training-receipt': hasTrainingReceipt }">
      <button v-if="data.jobId" type="button" class="wb-btn wb-btn-secondary" @click="$emit('goTask', data.jobId)">
        {{ primaryActionLabel }}
      </button>
      <button
        v-if="data.modelPublished && data.modelId"
        type="button"
        class="wb-btn wb-btn-secondary"
        @click="$emit('goModel', data.modelId)"
      >
        {{ t("task.resultCard.actions.openModelSummary") }}
      </button>
      <a
        v-if="showTrainingReportDownload"
        class="wb-btn wb-btn-secondary task-result-download-report"
        :href="trainingReportDownloadHref"
        download
        rel="noreferrer"
      >
        {{ t("task.resultCard.actions.downloadReport") }}
      </a>
      <button
        v-if="showStartPredictionTraining"
        type="button"
        class="wb-btn wb-btn-primary"
        @click="$emit('startPrediction', { modelId: data.modelId })"
      >
        {{ t("task.resultCard.actions.startPrediction") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { API_BASE_URL } from "../../api";
import AllModelPerformanceTable from "./AllModelPerformanceTable.vue";
import type { TaskResultCardData } from "../../types";
import { sanitizeUserFacingLine } from "../../utils/messageSanitizer";
import { localizeTrainingResultHeadlineForEnUi } from "../../utils/trainingBackendDisplayGuard";
import {
  isPredictionJobType,
  isRecommendationJobType,
  isReportGenerationJob,
  isShapGenerationJob,
  isTrainingJobType,
} from "../../utils/taskPresentation";
import { cvRowModelToAlgorithmOption, TRAINING_WORKFLOW_ALGORITHM_OPTIONS } from "../../utils/cvModelSelection";
import { trainingMetricLabel } from "../../utils/trainingWorkflowPresentation";
import { trainingReceiptFinalModelDisplayName } from "../../utils/statusMessages";
import {
  anyShapBeeswarmInArtifacts,
  pickFinalModelShapBeeswarmFromArtifacts,
} from "../../utils/trainingShapArtifacts";

const props = defineProps<{ data: TaskResultCardData; embedded?: boolean }>();
const { t } = useI18n();
defineEmits<{
  (e: "goTask", jobId: string): void;
  (e: "goModel", modelId: string): void;
  (e: "startPrediction", payload?: { modelId?: string }): void;
}>();
const metricEntries = computed(() => Object.entries(props.data.metrics || {}));

const featuresExpanded = ref(false);

/** Candidate CV table visibility for training receipt (hide empty block after artifact load). */
const trainingCandidateEvidence = ref<{ loading: boolean; rowCount: number; error: boolean } | null>(null);

function onTrainingCandidateEvidence(payload: {
  loading: boolean;
  rowCount: number;
  workflowMode: boolean;
  error: boolean;
}) {
  trainingCandidateEvidence.value = {
    loading: payload.loading,
    rowCount: payload.rowCount,
    error: payload.error,
  };
}

watch(
  () => props.data.trainingCompletedPresentation?.showCandidateModelComparison,
  (show) => {
    if (!show) trainingCandidateEvidence.value = null;
  },
  { immediate: true },
);
const featureSection = computed(() => props.data.trainingCompletedPresentation?.featureSection);
const visibleFeatureChips = computed(() => {
  const fs = featureSection.value;
  if (!fs) return [];
  const lim = fs.previewLimit ?? 20;
  if (featuresExpanded.value || fs.chips.length <= lim) return fs.chips;
  return fs.chips.slice(0, lim);
});
const featureExpandable = computed(() => {
  const fs = featureSection.value;
  if (!fs) return false;
  return fs.chips.length > (fs.previewLimit ?? 20);
});

const hasTrainingReceipt = computed(
  () =>
    props.data.variant === "completed" &&
    isTrainingJobType(String(props.data.jobType || "")) &&
    ((props.data.trainingCompletedPresentation?.receiptParagraphs?.length ?? 0) > 0 ||
      (props.data.trainingCompletedPresentation?.receiptParagraphsHtml?.length ?? 0) > 0),
);

const trainingReceiptParagraphsHtml = computed(
  () => props.data.trainingCompletedPresentation?.receiptParagraphsHtml ?? [],
);

const receiptFinalModelDisplayName = computed(() =>
  trainingReceiptFinalModelDisplayName((props.data.resultSummary || {}) as Record<string, unknown>, undefined, t),
);

const trainingShapMatch = computed(() =>
  pickFinalModelShapBeeswarmFromArtifacts(artifactMap.value, receiptFinalModelDisplayName.value),
);

const showTrainingShapUnavailable = computed(() => {
  if (!hasTrainingReceipt.value) return false;
  if (trainingShapMatch.value) return false;
  const mr = props.data.resultSummary?.model_registered;
  const anyOther = anyShapBeeswarmInArtifacts(artifactMap.value);
  if (mr === true) return true;
  if (mr === false) return anyOther;
  return anyOther;
});

const trainingShapUnavailableText = computed(() => {
  const mr = props.data.resultSummary?.model_registered;
  if (mr === true) return t("task.resultCard.trainingReceipt.shapUnavailablePublishedModel");
  if (mr === false) return t("task.resultCard.trainingReceipt.shapUnavailableTrainedModel");
  return t("task.resultCard.trainingReceipt.shapUnavailableFinalModelUnknown");
});

const shapBeeswarmCaption = computed(() => {
  if (!trainingShapMatch.value) return "";
  const model = receiptFinalModelDisplayName.value.trim();
  const fallbackAlgo = t("task.resultCard.trainingReceipt.algorithmFallback");
  if (!model || model === fallbackAlgo) return t("task.resultCard.trainingReceipt.shapBeeswarmTitle");
  const mr = props.data.resultSummary?.model_registered;
  if (mr === true) return t("task.resultCard.trainingReceipt.shapBeeswarmTitleForPublishedModel", { model });
  if (mr === false) return t("task.resultCard.trainingReceipt.shapBeeswarmTitleForTrainedModel", { model });
  return t("task.resultCard.trainingReceipt.shapBeeswarmTitleForFinalModelUnknown", { model });
});

const showTrainingCandidateBlock = computed(() => {
  if (!props.data.trainingCompletedPresentation?.showCandidateModelComparison) return false;
  const ev = trainingCandidateEvidence.value;
  if (ev === null) return true;
  return ev.loading || ev.rowCount > 0 || ev.error;
});

const showTrainingCandidateErrorOnly = computed(() => {
  const ev = trainingCandidateEvidence.value;
  if (!ev) return false;
  return !ev.loading && ev.rowCount === 0 && ev.error;
});

const isTrainingCompletedLegacyHeavy = computed(
  () =>
    props.data.variant === "completed" &&
    isTrainingJobType(String(props.data.jobType || "")) &&
    !hasTrainingReceipt.value &&
    Boolean(props.data.trainingCompletedPresentation?.summaryRows?.length),
);

const showStartPredictionTraining = computed(() => {
  if (!hasTrainingReceipt.value) return false;
  return props.data.resultSummary?.model_registered === true;
});

/** Hide large heading on training receipt cards; narrative summary opens the card. */
const showPrimaryCardTitle = computed(() => {
  if (hasTrainingReceipt.value) return false;
  return Boolean(String(props.data.title || "").trim());
});

const trainingChartItems = computed(() => {
  const out: { caption: string; url: string }[] = [];
  for (const [name, url] of Object.entries(artifactMap.value)) {
    if (!/\.png$/i.test(name)) continue;
    const n = name.toLowerCase();
    if (!/(roc|pr|shap|scatter|regression|pred|auc|curve)/i.test(n)) continue;
    out.push({ caption: name.replace(/\.png$/i, ""), url: String(url) });
  }
  return out;
});

/** Training completion: fixed metric columns (two-row table); missing values show as NA. */
const horizontalTrainingMetrics = computed(() => {
  if (!isTrainingJobType(String(props.data.jobType || ""))) return [];
  const m = (props.data.metrics || {}) as Record<string, unknown>;
  const reg = String(props.data.resultSummary?.ml_task_type || "").toLowerCase() === "regression";
  const primary = String(props.data.resultSummary?.primary_metric_requested || "").toLowerCase().trim();
  const order = reg
    ? (["mse", "pcc"] as const)
    : (["accuracy", "precision", "recall", "f1", "auroc", "auprc"] as const);
  const naStr = t("common.na");
  const out: { key: string; label: string; value: string; isPrimary: boolean }[] = [];
  for (const k of order) {
    const raw =
      k === "f1"
        ? m.f1 ?? m.f1_score
        : k === "pcc"
          ? m.pcc ?? m.pearson
          : m[k];
    const hasVal = raw !== undefined && raw !== null && String(raw).trim() !== "";
    const value = hasVal ? metricValue(raw as string | number) : naStr;
    const label =
      k === "pcc" ? t("chat.modelPerformanceTable.metricShort.pcc") : trainingMetricLabel(k);
    const isPrimary =
      primary === k ||
      (k === "pcc" && (primary === "pcc" || primary === "pearson")) ||
      (k === "f1" && (primary === "f1" || primary === "f1_score"));
    out.push({ key: k, label, value, isPrimary });
  }
  return out;
});

const trainingWorkflowSelectedAlgorithm = computed(() => {
  if (!hasTrainingReceipt.value) return "";
  const fm = String(
    props.data.resultSummary?.trained_model_programmer_name ||
      props.data.resultSummary?.programmer_model ||
      "",
  ).trim();
  return cvRowModelToAlgorithmOption(fm, TRAINING_WORKFLOW_ALGORITHM_OPTIONS) ?? "";
});

function inferFailureFromTaskResultCard(data: TaskResultCardData): boolean {
  if (data.errorReason) return true;
  const jobStatus = String(data.status ?? "").toLowerCase();
  if (jobStatus === "failed") return true;
  const rs = (data.resultSummary || {}) as Record<string, unknown>;
  const st = String(rs.status ?? "").toLowerCase();
  if (st === "failed") return true;
  const title = String(data.title || "");
  const tl = title.toLowerCase();
  if (
    tl.includes("failed") ||
    tl.includes("failure") ||
    tl.includes("error") ||
    tl.includes("did not complete") ||
    tl.includes("unsuccessful")
  ) {
    return true;
  }
  return false;
}

const isFailureTaskResult = computed(() => {
  if (props.data.variant === "failed") return true;
  if (props.data.variant === "completed") return false;
  return inferFailureFromTaskResultCard(props.data);
});

const primaryActionLabel = computed(() => {
  if (isFailureTaskResult.value) return t("task.resultCard.actions.reviewSetup");
  const jt = String(props.data.jobType || "");
  if (isTrainingJobType(jt)) return t("task.resultCard.actions.reviewPerformance");
  if (isPredictionJobType(jt)) return t("task.resultCard.actions.viewPredictionReport");
  if (isRecommendationJobType(jt)) return t("task.resultCard.actions.reviewRankedRegimens");
  if (isShapGenerationJob(jt)) return t("task.resultCard.actions.exportSummary");
  if (isReportGenerationJob(jt)) return t("task.resultCard.actions.openReport");
  return t("task.resultCard.actions.reviewSetup");
});

const resultHeadline = computed(() => String((props.data.resultSummary || {}).headline || ""));
const resultHeadlineDisplay = computed(() => {
  const loc = localizeTrainingResultHeadlineForEnUi(resultHeadline.value, t);
  return sanitizeUserFacingLine(loc, t) || loc;
});
const artifactMap = computed(() => (props.data.artifacts || {}) as Record<string, string>);

/** Training receipt card: show only when task snapshot lists report.pdf (same source as Tasks panel artifact scan). */
const showTrainingReportDownload = computed(
  () =>
    hasTrainingReceipt.value &&
    Boolean(props.data.jobId) &&
    Boolean(artifactMap.value["report.pdf"]),
);

const trainingReportDownloadHref = computed(() => {
  const jid = props.data.jobId;
  if (!jid) return "#";
  return `${API_BASE_URL}/tasks/${encodeURIComponent(jid)}/artifacts/report.pdf`;
});

const artifactNames = computed(() => Object.keys(artifactMap.value));
const thumbnailUrl = computed(() => {
  const entries = Object.entries(artifactMap.value);
  const preferred = entries.find(([name]) => /roc|pr|beeswarm|shap|scatter/i.test(name) && /\.png$/i.test(name));
  if (preferred) return preferred[1];
  const anyPng = entries.find(([name]) => /\.png$/i.test(name));
  return anyPng ? anyPng[1] : "";
});

function metricLabel(key: string): string {
  return trainingMetricLabel(key);
}

function metricValue(v: string | number): string {
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : String(v);
  const n = Number(v);
  if (!Number.isNaN(n) && String(v).trim() !== "" && /^-?\d/.test(String(v).trim())) return n.toFixed(3);
  return String(v);
}
</script>

<style scoped>
.task-result-card {
  border: 1px solid #d8e5f3;
  background: linear-gradient(180deg, #f5f9ff 0%, #f3f8ff 100%);
  padding: var(--wb-space-3);
  border-radius: var(--wb-chat-embed-radius);
  margin-top: var(--wb-space-1);
  max-width: 100%;
  box-sizing: border-box;
}

.task-result-card-training-receipt,
.task-result-card--embedded {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  margin-top: 0;
}

.task-result-training-summary {
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
  color: var(--wb-text-main);
}

.task-result-receipt {
  margin-top: 0;
  padding-top: 2px;
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
  color: var(--wb-text-main);
}

.task-result-receipt-p {
  margin: 0 0 0.9em;
}

.task-result-receipt-p:last-child {
  margin-bottom: 0;
}

.task-result-receipt-html-p :deep(strong) {
  font-weight: 750;
  color: #0f172a;
}

.task-result-training-block {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eceff3;
}

.task-result-training-section-title {
  font-size: var(--wb-font-size-sm);
  font-weight: 600;
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-body-secondary);
  margin: 0 0 8px;
}

.task-result-shap-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.task-result-shap-figure {
  width: fit-content;
  max-width: min(100%, 600px);
  margin: 0;
  box-sizing: border-box;
}

.task-result-shap-img {
  display: block;
  width: auto;
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
  box-sizing: border-box;
}

.task-result-shap-unavailable {
  margin: 0;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}

.task-result-candidate-hint {
  margin: 0 0 10px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}

.task-result-candidate-fallback {
  margin: 0;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}

.task-result-charts-nested {
  margin-top: 10px;
}

.task-result-title {
  font-weight: 650;
  color: var(--wb-text-main);
  font-size: var(--wb-font-size-card-title);
  line-height: var(--wb-line-height-card);
}

.task-result-error {
  margin-top: var(--wb-space-1);
  color: #b00020;
}

.task-result-presentation {
  margin-top: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}

.task-result-meta-table {
  border-collapse: collapse;
  width: 100%;
  min-width: min(100%, 720px);
}

.task-result-meta-table th,
.task-result-meta-table td {
  border: 1px solid #d0d7de;
  padding: 6px 10px;
  text-align: center;
  font-weight: 450;
  color: #334155;
  vertical-align: top;
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
}

.task-result-meta-table th {
  background: #f6f8fa;
  color: var(--wb-text-body-secondary);
}

.task-result-meta-table td {
  word-break: break-word;
  white-space: normal;
  min-width: 72px;
}

.task-result-metrics {
  margin-top: var(--wb-chat-input-padding-y);
}

.task-result-subtitle {
  font-weight: 600;
  color: var(--wb-text-body-secondary);
  margin-bottom: var(--wb-space-micro);
  font-size: var(--wb-font-size-card-title);
  line-height: var(--wb-line-height-card);
}

.task-result-metric-row {
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-xs);
  line-height: 1.5;
}

.task-result-metric-key {
  min-width: 110px;
  color: var(--wb-text-body-secondary);
}

.task-result-metric-value {
  font-weight: 600;
}

.task-result-metrics-table-scroll {
  overflow-x: auto;
  max-width: 100%;
}

.task-result-metrics-table {
  border-collapse: collapse;
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
  min-width: min(100%, 720px);
}

.task-result-metrics-table th,
.task-result-metrics-table td {
  border: 1px solid #d0d7de;
  padding: 6px 10px;
  text-align: center;
  white-space: nowrap;
  font-weight: 450;
  color: #24303f;
}

.task-result-metrics-table th {
  background: #f6f8fa;
  color: var(--wb-text-body-secondary);
  font-weight: 600;
}

.task-result-metric-primary {
  font-weight: 750 !important;
  color: #0f172a !important;
}

.task-result-features {
  margin-top: var(--wb-chat-input-padding-y);
}

.task-result-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.task-result-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: var(--wb-font-size-2xs);
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #1e293b;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-result-features-toggle {
  margin-top: 8px;
}

.task-result-next {
  margin-top: var(--wb-chat-input-padding-y);
  color: var(--wb-text-body-secondary);
  font-size: var(--wb-font-size-xs);
}

.task-result-actions {
  margin-top: var(--wb-chat-input-padding-y);
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  flex-wrap: wrap;
}

.task-result-actions-training-receipt {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eceff3;
}

.task-result-download-report {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.task-result-charts {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-chat-input-padding-y);
  border: 1px solid #d0d7de;
  border-radius: var(--wb-radius-sm);
  background: #fff;
  font-size: var(--wb-font-size-xs);
}

.task-result-charts summary {
  cursor: pointer;
  font-weight: 650;
  color: var(--wb-text-body-secondary);
}

.task-result-charts-grid {
  margin-top: var(--wb-space-2);
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
}

.task-result-chart-cell {
  min-width: 200px;
  max-width: 360px;
  flex: 1 1 240px;
}

.task-result-chart-cap {
  font-weight: 600;
  margin-bottom: var(--wb-space-micro);
  color: var(--wb-text-body-secondary);
  word-break: break-word;
}

.task-result-tech {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-chat-input-padding-y);
  border: 1px solid #d0d7de;
  border-radius: var(--wb-radius-sm);
  background: #fff;
  font-size: var(--wb-font-size-2xs);
}

.task-result-tech summary {
  cursor: pointer;
  font-weight: 650;
  color: var(--wb-text-body-secondary);
}

.task-result-tech-body {
  margin-top: var(--wb-space-2);
}

.task-result-tech-block {
  margin-top: var(--wb-space-1);
  line-height: 1.45;
}

.task-result-artifact {
  margin-top: var(--wb-space-1);
}

.task-result-thumb {
  margin-top: var(--wb-chat-input-padding-y);
  max-width: 360px;
}

.task-result-thumb-image {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: var(--wb-space-micro);
}

.task-result-empty-chart {
  margin-top: var(--wb-space-1);
  color: var(--wb-text-caption-muted);
}
</style>
