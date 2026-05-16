<template>
  <div class="task-detail-root">
    <div v-if="!jobId" class="task-detail-muted">{{ $t("panels.taskDetail.emptyPick") }}</div>
    <div v-else-if="loading" class="task-inline-muted">{{ $t("panels.taskDetail.loading") }}</div>
    <div v-else-if="loadError" class="task-load-error">
      <div><b>{{ $t("panels.taskDetail.loadFailed") }}</b>{{ loadError }}</div>
    </div>
    <div v-else-if="detail">
      <div class="task-detail-tabbar" role="tablist">
        <button
          type="button"
          class="task-detail-tab"
          role="tab"
          :class="{ 'is-active': detailTab === 'summary' }"
          @click="detailTab = 'summary'"
        >
          {{ $t("panels.taskDetail.tabs.summary") }}
        </button>
        <button
          type="button"
          class="task-detail-tab"
          role="tab"
          :class="{ 'is-active': detailTab === 'logs' }"
          @click="detailTab = 'logs'"
        >
          {{ $t("panels.taskDetail.tabs.logs") }}
        </button>
      </div>

      <div v-show="detailTab === 'summary'" class="task-detail-tab-panel">
      <!-- 1) Basic info -->
      <h4 class="task-h4-first">{{ $t("panels.taskDetail.basic.title") }}</h4>
      <div class="task-body-dense">
        <div><b>{{ $t("panels.taskDetail.basic.jobType") }}</b>{{ formatJobTypeLabel(String(detail.task.job_type || ""), t) }}</div>
        <div>
          <b>{{ $t("panels.taskDetail.basic.status") }}</b>{{ formatTaskStatusLabel(String(detail.task.status || ""), t) }}
        </div>
        <div v-if="taskProgressOneLiner">
          <b>{{ $t("panels.taskDetail.basic.progressNote") }}</b>{{ taskProgressOneLiner }}
        </div>
        <div v-if="taskMsgLayers.headLine" class="task-body-dense">
          <b>{{ $t("panels.taskDetail.basic.primaryNote") }}</b>{{ taskMsgLayers.headLine }}
        </div>
        <details v-if="taskMsgLayers.showSupplement" class="task-msg-supplement">
          <summary>{{ $t("panels.taskDetail.basic.supplement") }}</summary>
          <div class="task-msg-supplement-body">{{ taskMsgLayers.tailText }}</div>
        </details>
        <details v-else-if="showMessageAsMuted && sanitizedTaskMessage" class="task-msg-supplement">
          <summary>{{ $t("panels.taskDetail.basic.supplement") }}</summary>
          <div class="task-msg-supplement-body task-msg-secondary">{{ sanitizedTaskMessage }}</div>
        </details>
        <div v-if="detail.task.created_at"><b>{{ $t("panels.taskDetail.basic.createdAt") }}</b>{{ formatDisplayDateTime(String(detail.task.created_at)) }}</div>
        <div v-if="detail.task.started_at"><b>{{ $t("panels.taskDetail.basic.startedAt") }}</b>{{ formatDisplayDateTime(String(detail.task.started_at)) }}</div>
        <div v-if="detail.task.completed_at"><b>{{ $t("panels.taskDetail.basic.completedAt") }}</b>{{ formatDisplayDateTime(String(detail.task.completed_at)) }}</div>
      </div>

      <!-- 2) Training summary -->
      <template v-if="isTrainingJobType(String(detail.task.job_type || ''))">
        <h4>{{ $t("panels.taskDetail.trainingSummary.title") }}</h4>
        <div class="task-body-dense">
          <template v-if="trainingSummary || featureSummary">
            <div v-if="trainingSummary?.dataset_id"><b>{{ $t("panels.taskDetail.trainingSummary.datasetId") }}</b>{{ trainingSummary.dataset_id }}</div>
            <div v-if="trainingSummary?.clinical_task_id"><b>{{ $t("panels.taskDetail.trainingSummary.scenario") }}</b>{{ trainingSummary.clinical_task_id }}</div>
            <div v-if="trainingSummary?.ml_task_type"><b>{{ $t("panels.taskDetail.trainingSummary.taskType") }}</b>{{ trainingSummary.ml_task_type }}</div>
            <div v-if="trainingSummary?.model_type">
              <b>{{ $t("panels.taskDetail.trainingSummary.algorithm") }}</b>{{ trainingModelTypeDisplay(String(trainingSummary.model_type)) }}
              <span v-if="trainingModelTypeDisplay(String(trainingSummary.model_type)) !== trainingSummary.model_type" class="task-inline-code">
                ({{ trainingSummary.model_type }})
              </span>
            </div>
            <div v-if="trainingSummary?.target_column">
              <b>{{ $t("panels.taskDetail.trainingSummary.target") }}</b>{{ clinicalFieldDisplay(trainingSummary.target_column) }}
            </div>
            <div v-if="trainingSummary?.objective_metric"><b>{{ $t("panels.taskDetail.trainingSummary.primaryMetric") }}</b>{{ trainingSummary.objective_metric }}</div>
            <div v-if="featureSummary"><b>{{ $t("panels.taskDetail.trainingSummary.featureSource") }}</b>{{ featureSummary }}</div>
          </template>
          <div v-else class="task-inline-muted">{{ $t("panels.taskDetail.trainingSummary.empty") }}</div>
        </div>
      </template>

      <template v-if="isTrainWorkflowGate">
        <details class="task-flow-hint">
          <summary>{{ $t("panels.taskDetail.pending.foldSummary") }}</summary>
        <h4>{{ $t("panels.taskDetail.pending.trainingTitle") }}</h4>
        <div class="task-body-dense task-body-tight">
          {{ $t("panels.taskDetail.pending.currentStepLabel") }}<b>{{ workflowPhaseLabel }}</b>
          <div v-if="filterSummaryDisplay" class="task-mt-s">
            <b>{{ $t("panels.taskDetail.pending.filterSummaryLabel") }}</b>{{ filterSummaryDisplay }}
          </div>
        </div>
        <div class="task-flow-callout">
          {{ $t("panels.taskDetail.pending.callout") }}
        </div>
        <template v-if="trainingWorkflowPhase === WF_PHASE3">
          <div class="task-mt-m task-fs-body">
            <b>{{ $t("panels.taskDetail.pending.phase3Title") }}</b>{{ $t("panels.taskDetail.pending.phase3Hint") }}
          </div>
          <div class="task-phase3-scroll">
            <label
              v-for="col in phase3ColumnChoices"
              :key="'p3-' + col"
              class="task-phase3-label"
            >
              <input type="checkbox" :value="col" v-model="phase3Pick" disabled />
              <span class="task-p3-friendly">{{ clinicalFieldDisplay(col) }}</span>
            </label>
          </div>
        </template>

        <template v-else-if="trainingWorkflowPhase === WF_PHASE4">
          <div class="task-mt-m task-fs-body"><b>{{ $t("panels.taskDetail.trainingConfig.sectionTitle") }}</b></div>
          <div class="task-mt-m">
            <label class="task-form-label">{{ $t("panels.taskDetail.trainingConfig.modelType") }}</label>
            <select v-model="p4ModelType" class="task-select-full" disabled>
              <option v-for="opt in p4ModelTypeOptions" :key="opt" :value="opt">{{ trainingModelTypeDisplay(opt) }} ({{ opt }})</option>
            </select>
          </div>
          <div class="task-mt-m">
            <label class="task-form-label">{{ $t("panels.taskDetail.trainingConfig.objectiveMetric") }}</label>
            <select v-model="p4Objective" class="task-select-full" disabled>
              <option v-for="op in p4MetricOptions" :key="op.value" :value="op.value">{{ op.label }}</option>
            </select>
          </div>
          <label class="task-checkbox-row">
            <input v-model="p4EnableSearch" type="checkbox" disabled />
            {{ $t("panels.taskDetail.trainingConfig.enableSearch") }}
          </label>
          <div class="task-hint-muted">{{ $t("panels.taskDetail.trainingConfig.confirmTrainInChatHint") }}</div>
        </template>

        <template v-else-if="trainingWorkflowPhase === WF_PHASE5">
          <div class="task-mt-m task-fs-body">
            <b>{{ $t("panels.taskDetail.release.sectionTitle") }}</b>
          </div>
          <label class="task-checkbox-row">
            <input v-model="p5DoPublish" type="checkbox" disabled />
            {{ $t("panels.taskDetail.release.publishCheckbox") }}
          </label>
          <div class="task-mt-m">
            <label class="task-inline-label">{{ $t("panels.taskDetail.release.releaseModelIdOptional") }}</label>
            <input
              v-model="p5ModelId"
              type="text"
              class="task-input-block"
              :placeholder="$t('panels.taskDetail.release.modelIdPlaceholder')"
              disabled
            />
          </div>
          <div class="task-mt-m">
            <label class="task-inline-label">{{ $t("panels.taskDetail.release.notesOptional") }}</label>
            <textarea v-model="p5Notes" rows="2" class="task-input-block" disabled />
          </div>
          <div class="task-hint-muted">{{ $t("panels.taskDetail.release.confirmReleaseInChatHint") }}</div>
        </template>
        </details>
      </template>

      <!-- 4) Results: training vs prediction -->
      <h4>{{ $t("panels.taskDetail.result.title") }}</h4>
      <template v-if="isPredictionJob">
        <div v-if="predictionResultOverview" class="task-pred-overview">
          <div><b>{{ $t("panels.taskDetail.result.predictionMode") }}</b>{{ predictionModeDisplay }}</div>
          <div><b>{{ $t("panels.taskDetail.result.currentStatus") }}</b>{{ formatTaskStatusLabel(String(detail.task.status || ""), t) }}</div>
          <div v-if="predictionModelDisplay"><b>{{ $t("panels.taskDetail.result.modelId") }}</b>{{ predictionModelDisplay }}</div>
          <details v-if="predictionHeadline" class="task-pred-headline-fold">
            <summary>{{ $t("panels.taskDetail.result.headlineFoldTitle") }}</summary>
            <div class="task-msg-supplement-body">{{ predictionHeadlineSanitized }}</div>
          </details>
          <template v-if="isBatchPredictionTask">
            <div v-if="predictionBatchFile"><b>{{ $t("panels.taskDetail.result.uploadedTable") }}</b>{{ predictionBatchFile }}</div>
            <div v-if="predictionBatchCounts"><b>{{ $t("panels.taskDetail.result.generationStatus") }}</b>{{ predictionBatchCounts }}</div>
            <div v-if="predictionDownloadUrl">
              <a :href="predictionDownloadUrl" target="_blank" rel="noreferrer">{{ $t("panels.taskDetail.result.downloadPredictionFile") }}</a>
            </div>
          </template>
          <template v-else>
            <div v-if="predictionSingleOutcomeLine"><b>{{ $t("panels.taskDetail.result.singleOutcome") }}</b>{{ predictionSingleOutcomeLine }}</div>
            <template v-else>
              <div v-if="predictionProbDisplay"><b>{{ $t("panels.taskDetail.result.predictedProbability") }}</b>{{ predictionProbDisplay }}</div>
              <div v-if="predictionLabelRaw"><b>{{ $t("panels.taskDetail.result.modelOutput") }}</b>{{ predictionLabelRaw }}</div>
            </template>
          </template>
          <div v-if="predictionHistoryId" class="task-msg-secondary">
            {{ $t("panels.taskDetail.result.historyRecordHint", { recordId: predictionHistoryId }) }}
          </div>
        </div>
        <div v-else class="task-detail-muted">{{ $t("panels.taskDetail.result.noReadablePredictionOverview") }}</div>
      </template>
      <template v-else-if="isRecommendationJob">
        <div v-if="hasRecommendationOverview" class="task-rec-overview">
          <div v-if="recommendationModelDisplay"><b>{{ $t("panels.taskDetail.recommendation.modelLabel") }}</b>{{ recommendationModelDisplay }}</div>
          <div v-if="recommendationHeadline"><b>{{ $t("panels.taskDetail.recommendation.headlineLabel") }}</b>{{ recommendationHeadline }}</div>
          <div v-if="recommendationTop1Line"><b>{{ $t("panels.taskDetail.recommendation.top1Label") }}</b>{{ recommendationTop1Line }}</div>
          <div v-if="recommendationProbLine"><b>{{ $t("panels.taskDetail.recommendation.top1ProbLabel") }}</b>{{ recommendationProbLine }}</div>
          <div v-if="recommendationDeltaLine"><b>{{ $t("panels.taskDetail.recommendation.deltaLabel") }}</b>{{ recommendationDeltaLine }}</div>
          <div v-if="recommendationArtifactUrl" class="task-rec-artifact">
            <a :href="recommendationArtifactUrl" target="_blank" rel="noreferrer">{{ $t("panels.taskDetail.recommendation.viewStructured") }}</a>
          </div>
        </div>
        <div v-else class="task-detail-muted">{{ $t("panels.taskDetail.recommendation.emptyStructured") }}</div>
      </template>
      <template v-else>
        <div v-if="hasAnyResult" class="task-body-dense">
          <div v-if="modelIdResolved"><b>{{ $t("panels.taskDetail.result.modelId") }}</b>{{ modelIdResolved }}</div>
          <div v-if="artifactEntries.length">
            <b>{{ $t("panels.taskDetail.artifacts.summary", { count: artifactEntries.length }) }}</b>
            <div class="task-mt-s">
              <button type="button" class="wb-btn wb-btn-text wb-btn-sm" @click="artifactsExpanded = !artifactsExpanded">
                {{ artifactsExpanded ? $t("panels.taskDetail.artifacts.collapse") : $t("panels.taskDetail.artifacts.expand") }}
              </button>
            </div>
            <ul v-if="artifactsExpanded" class="task-artifact-list">
              <li v-for="([name, url]) in artifactEntries" :key="name">
                <a :href="url" target="_blank" rel="noreferrer">{{ artifactLabel(name) }}</a>
              </li>
            </ul>
          </div>
          <div v-if="metricEntries.length > 0">
            <b>{{ $t("panels.taskDetail.metrics.title") }}</b>
            <div v-for="([k, v]) in metricEntries" :key="k" class="task-metric-line">
              {{ $t("panels.taskDetail.metrics.line", { label: metricLabel(k), value: metricValueDisplay(v) }) }}
            </div>
          </div>
          <div v-if="reportGenerationNotice" class="task-report-notice">
            {{ reportGenerationNotice }}
          </div>
        </div>
        <div v-else class="task-inline-muted">{{ $t("panels.taskDetail.result.empty") }}</div>
      </template>

      <div v-if="modelIdResolved" class="task-mt-m-lg">
        <button type="button" class="wb-btn wb-btn-secondary wb-btn-toolbar" @click="$emit('goModels', modelIdResolved)">
          {{ $t("panels.taskDetail.result.goToModels") }}
        </button>
      </div>
      <div class="task-mt-m">
        <button
          type="button"
          class="wb-btn wb-btn-sm wb-btn-danger"
          :disabled="isDeletingTask"
          @click="emit('deleteTask', String(detail.task.id || ''))"
        >
          {{ deleteButtonLabel }}
        </button>
      </div>

      <!-- 5) Failure / cancellation -->
      <template v-if="isFailedOrCanceled">
        <h4>{{ $t("panels.taskDetail.failure.title") }}</h4>
        <div
          v-if="failureReason"
          class="task-failure-box"
        >
          {{ failureReason }}
        </div>
        <div v-else class="task-inline-muted">{{ $t("panels.taskDetail.failure.missingErrorMessage", { status: detail.task.status }) }}</div>
      </template>

      <details class="task-tech-root">
        <summary>{{ $t("panels.taskDetail.tech.detailsSummary") }}</summary>
        <p class="task-tech-intro">{{ $t("panels.taskDetail.tech.intro") }}</p>
        <div class="task-tech-line"><b>{{ $t("panels.taskDetail.tech.internalJobId") }}</b><code>{{ detail.task.id }}</code></div>
        <div v-if="publishSummaryDisplay" class="task-tech-line"><b>{{ $t("panels.taskDetail.tech.releaseParams") }}</b>{{ publishSummaryDisplay }}</div>
        <details v-if="hasParams" class="task-tech-nested">
          <summary>{{ $t("panels.taskDetail.tech.paramsSnapshot") }}</summary>
          <pre class="task-pre">{{ paramsJson }}</pre>
        </details>
        <details v-if="detail.task.result_summary && Object.keys(summaryObj).length" class="task-tech-nested">
          <summary>{{ $t("panels.taskDetail.tech.rawSummary") }}</summary>
          <div v-if="headline" class="task-tech-line"><b>{{ $t("panels.taskDetail.tech.rawHeadline") }}</b>{{ sanitizedHeadline }}</div>
          <div v-if="otherSummaryEntries.length > 0" class="task-tech-kv">
            <div v-for="([k, v]) in otherSummaryEntries" :key="k" class="task-tech-kv-row">
              <b>{{ k }}:</b> {{ typeof v === "object" ? JSON.stringify(v) : String(v) }}
            </div>
          </div>
        </details>
      </details>
      </div>

      <div v-show="detailTab === 'logs'" class="task-detail-tab-panel task-detail-logs-panel">
        <h4 class="task-h4-first">{{ $t("panels.taskDetail.tabs.logs") }}</h4>
        <div v-if="dedupedLogs.length > 0" class="task-log-box">
          <div v-for="(log, idx) in dedupedLogs" :key="idx" class="task-log-row">
            <div><b>{{ formatLogTime(log.time) }}</b></div>
            <div>{{ sanitizeLogMessage(log.message) }}</div>
          </div>
        </div>
        <div v-else class="task-detail-muted">{{ $t("panels.taskDetail.tech.noLogs") }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { ApiError, getTaskDetail } from "../api";
import { formatDisplayDateTime } from "../utils/dateFormat";
import { objectiveMetricOptionsForMlTaskType } from "../config/trainingSchemas";
import type { TaskDetailData } from "../types";
import { clinicalizeExplanationFeatureNames, resolveClinicalFeatureDisplayName } from "../utils/featureDisplayName";
import { humanizePublishSummarySnippet, sanitizeUserFacingLine } from "../utils/messageSanitizer";
import { localizeTrainingFilterSummaryForEnUi, localizeTrainingResultHeadlineForEnUi } from "../utils/trainingBackendDisplayGuard";
import { buildTaskMessageLayers } from "../utils/taskMessageLayers";
import { formatPredictionResultOneLiner, taskResultSummaryToSingleResponse } from "../utils/predictionPresentation";
import {
  extractTrainingSummaryFromParams,
  formatJobTypeLabel,
  formatTaskStatusLabel,
  getReadableTaskFailureReason,
  isPredictionJobType,
  isRecommendationJobType,
  isTrainingJobType,
  pickModelIdFromTask,
  summarizeFeatureSources,
} from "../utils/taskPresentation";
import { formatTaskStatusCompanionLine } from "../utils/taskStatusNarrative";
import { trainingMetricLabel, trainingModelTypeDisplay, workflowSubmittedBadgeLabel } from "../utils/trainingWorkflowPresentation";

const { t } = useI18n();
type Translate = (key: string, values?: Record<string, unknown>) => string;
const tFn: Translate = (key, values) => t(key, values);

const props = defineProps<{ jobId: string | null; deletingTaskStatuses?: Record<string, string> }>();

const emit = defineEmits<{
  (e: "goModels", modelId: string): void;
  (e: "deleteTask", jobId: string): void;
}>();

const WF_PHASE3 = "train_phase3_feature_confirm_pending";
const WF_PHASE4 = "train_phase4_train_config_pending";
const WF_PHASE5 = "train_phase5_publish_pending";
const WF_PHASE4_ALIAS = "train_phase4_config_confirm_pending";
const WF_PHASE5_ALIAS = "train_phase5_publish_confirm_pending";

const loading = ref(false);
const loadError = ref("");
const detail = ref<TaskDetailData | null>(null);

const phase3Pick = ref<string[]>([]);
const p4ModelTypeOptions = ["xgboost", "lightgbm", "catboost", "random_forest", "logistic_regression", "svm", "knn"];
const p4ModelType = ref("xgboost");
const p4Objective = ref("auroc");
const p4EnableSearch = ref(false);
const p5DoPublish = ref(true);
const p5ModelId = ref("");
const p5Notes = ref("");
const artifactsExpanded = ref(false);
const detailTab = ref<"summary" | "logs">("summary");

const summaryObj = computed(() => (detail.value?.task.result_summary as Record<string, unknown>) || {});

function clinicalFieldDisplay(v: string | undefined | null): string {
  if (v == null || !String(v).trim()) return t("common.na");
  return resolveClinicalFeatureDisplayName(String(v));
}

function sanitizeLogMessage(m: unknown): string {
  const s = sanitizeUserFacingLine(m == null ? "" : String(m), t);
  return s || t("common.na");
}

const sanitizedTaskMessage = computed(() => sanitizeUserFacingLine(String(detail.value?.task?.message || ""), t));

const taskMsgLayers = computed(() => {
  const task = detail.value?.task;
  if (!task) return { headLine: "", tailText: "", showSupplement: false, headlineSanitized: "" };
  return buildTaskMessageLayers(task as Record<string, unknown>, t);
});

const taskProgressOneLiner = computed(() => {
  if (!detail.value?.task) return "";
  return formatTaskStatusCompanionLine(detail.value.task as Record<string, unknown>, t);
});

const filterSummaryDisplay = computed(() => {
  const s = String(summaryObj.value.filter_summary || "").trim();
  if (!s) return "";
  const jt = String(detail.value?.task?.job_type || "");
  const body = isTrainingJobType(jt) ? localizeTrainingFilterSummaryForEnUi(s, tFn) : s;
  return clinicalizeExplanationFeatureNames(body);
});

const sanitizedHeadline = computed(() => {
  const h = headline.value;
  const jt = String(detail.value?.task?.job_type || "");
  const line = isTrainingJobType(jt) ? localizeTrainingResultHeadlineForEnUi(h, tFn) : h;
  return sanitizeUserFacingLine(line, t) || line;
});

function formatLogTime(t: unknown): string {
  return formatDisplayDateTime(String(t || ""));
}

const GENERIC_STATUS_MESSAGES = new Set(
  [
    "recommendation completed",
    "prediction completed",
    "training completed",
    "completed",
    "success",
    "succeeded",
  ].map((s) => s.toLowerCase()),
);

function isMutedTaskMessage(msg: string): boolean {
  const low = msg.toLowerCase().trim();
  if (GENERIC_STATUS_MESSAGES.has(low)) return true;
  if (/^recommendation completed\b/i.test(msg)) return true;
  if (/^prediction completed\b/i.test(msg)) return true;
  if (/^training completed\b/i.test(msg)) return true;
  const head = String(summaryObj.value.headline || "").trim();
  if (head && msg.trim() === head) return true;
  return false;
}

const showMessageAsMuted = computed(() => {
  const msg = String(detail.value?.task?.message || "").trim();
  if (!msg) return false;
  return isMutedTaskMessage(msg);
});

const dedupedLogs = computed(() => {
  const logs = detail.value?.logs || [];
  const rows = Array.isArray(logs) ? logs : [];
  const out: Array<Record<string, unknown>> = [];
  let prevMsg = "";
  for (const row of rows) {
    const m = String((row as { message?: unknown }).message ?? "").trim();
    if (m && m === prevMsg) continue;
    prevMsg = m;
    out.push(row as Record<string, unknown>);
  }
  return out;
});

const isRecommendationJob = computed(() => isRecommendationJobType(String(detail.value?.task.job_type || "")));

const recommendationModelDisplay = computed(() => {
  const rs = summaryObj.value;
  const fromSummary = rs.model_id != null ? String(rs.model_id).trim() : "";
  if (fromSummary) return fromSummary;
  return predictionModelDisplay.value;
});

const recommendationHeadline = computed(() => String(summaryObj.value.headline || "").trim());

const recommendationTop1Line = computed(() => {
  const raw = summaryObj.value.recommended_top1_regimen;
  if (!raw || typeof raw !== "object") return "";
  const r = raw as Record<string, unknown>;
  const name = String(r.regimen_name || "").trim();
  const id = String(r.regimen_id || "").trim();
  if (!name && !id) return "";
  if (name && id) return tFn("panels.taskDetail.recommendation.regimenPair", { name, id });
  return name || id;
});

const recommendationProbLine = computed(() => {
  const n = Number(summaryObj.value.recommended_top1_probability);
  if (Number.isNaN(n)) return "";
  return n <= 1 ? `${(n * 100).toFixed(2)}%` : String(Number(n.toFixed(4)));
});

const recommendationDeltaLine = computed(() => {
  const n = Number(summaryObj.value.delta_probability_top1);
  if (Number.isNaN(n)) return "";
  return n <= 1 ? `${(n * 100).toFixed(2)}%` : String(Number(n.toFixed(4)));
});

const recommendationArtifactUrl = computed(() => {
  const arts = detail.value?.artifacts || {};
  const u = arts["recommendation.json"];
  return typeof u === "string" && u.trim() ? u.trim() : "";
});

const hasRecommendationOverview = computed(() =>
  Boolean(
    recommendationHeadline.value ||
      recommendationModelDisplay.value ||
      recommendationTop1Line.value ||
      recommendationProbLine.value ||
      recommendationArtifactUrl.value,
  ),
);
const trainingWorkflowPhase = computed(() => {
  const raw = String(summaryObj.value.train_workflow_phase || "");
  if (raw === WF_PHASE4_ALIAS) return WF_PHASE4;
  if (raw === WF_PHASE5_ALIAS) return WF_PHASE5;
  return raw;
});
const workflowPhaseLabel = computed(() => workflowSubmittedBadgeLabel(trainingWorkflowPhase.value));

const isTrainWorkflowGate = computed(() => {
  const t = detail.value?.task;
  if (!t) return false;
  return (
    isTrainingJobType(String(t.job_type || "")) &&
    String(t.status || "") === "waiting_user" &&
    Boolean(trainingWorkflowPhase.value)
  );
});

const phase3ColumnChoices = computed(() => {
  const rs = summaryObj.value;
  const pool = (rs.candidate_pool_columns as string[]) || [];
  const sug = (rs.suggested_final_features as string[]) || [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const c of [...pool, ...sug]) {
    const s = String(c || "").trim();
    if (!s || seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
});

const p4MetricOptions = computed(() => {
  const p = (taskRecord.value.params || {}) as Record<string, unknown>;
  const ml = String(p.ml_task_type || "binary");
  return objectiveMetricOptionsForMlTaskType(ml);
});
const headline = computed(() => String(summaryObj.value.headline || ""));
const metricEntries = computed(() => {
  const km = (summaryObj.value.key_metrics as Record<string, unknown>) || {};
  return Object.entries(km);
});
const otherSummaryEntries = computed(() =>
  Object.entries(summaryObj.value).filter(
    ([k]) =>
      k !== "headline" &&
      k !== "key_metrics" &&
      k !== "report_generation_status" &&
      k !== "report_generation_error" &&
      k !== "training_core_status",
  ),
);

const taskRecord = computed(() => (detail.value?.task || {}) as Record<string, unknown>);
const trainingSummary = computed(() => extractTrainingSummaryFromParams(taskRecord.value.params as Record<string, unknown>));
const featureSummary = computed(() => summarizeFeatureSources(taskRecord.value.params as Record<string, unknown>, t));

const hasParams = computed(() => {
  const p = taskRecord.value.params;
  return p && typeof p === "object" && Object.keys(p as object).length > 0;
});
const paramKeyCount = computed(() => {
  const p = taskRecord.value.params as Record<string, unknown>;
  return p ? Object.keys(p).length : 0;
});
const paramsJson = computed(() => {
  const p = taskRecord.value.params;
  try {
    return JSON.stringify(p ?? {}, null, 2);
  } catch {
    return String(p);
  }
});

const modelIdResolved = computed(() => pickModelIdFromTask(taskRecord.value));
const artifactEntries = computed(() => Object.entries(detail.value?.artifacts || {}));
const publishSummary = computed(() => {
  const p = taskRecord.value.params as Record<string, unknown> | undefined;
  const po = p?.publish_overrides as Record<string, unknown> | undefined;
  if (!po || typeof po !== "object") return "";
  const parts: string[] = [];
  if (po.model_id != null) parts.push(`publish_overrides.model_id=${po.model_id}`);
  if (po.notes != null) parts.push(`notes=${po.notes}`);
  return parts.join("; ");
});

const publishSummaryDisplay = computed(() => humanizePublishSummarySnippet(publishSummary.value, t));

/** Notice when training finished but report/PDF failed (decoupled from core training success). */
const isPredictionJob = computed(() => isPredictionJobType(String(detail.value?.task.job_type || "")));

const predictionModelDisplay = computed(() => {
  const rs = summaryObj.value;
  const dn = rs.display_name != null ? String(rs.display_name).trim() : "";
  if (dn) return dn;
  const fromRs = rs.model_id != null ? String(rs.model_id).trim() : "";
  if (fromRs) return fromRs;
  const p = taskRecord.value.params as Record<string, unknown> | undefined;
  if (p?.model_id != null) return String(p.model_id).trim();
  return "";
});

const isBatchPredictionTask = computed(() => {
  const p = taskRecord.value.params as Record<string, unknown> | undefined;
  if (String(p?.prediction_mode || "").toLowerCase() === "batch") return true;
  return String(summaryObj.value.prediction_type || "").toLowerCase() === "batch";
});

const predictionModeDisplay = computed(() =>
  isBatchPredictionTask.value ? tFn("panels.taskDetail.result.modeBatch") : tFn("panels.taskDetail.result.modeSingle"),
);

const predictionBatchFile = computed(() => {
  const fn = summaryObj.value.file_name;
  return fn != null && String(fn).trim() ? String(fn).trim() : "";
});

const predictionBatchCounts = computed(() => {
  const rs = summaryObj.value;
  const totalRows = rs.total_rows;
  const succeeded = rs.succeeded_rows;
  const failed = rs.failed_rows;
  if (totalRows == null && succeeded == null) return "";
  const dash = tFn("common.na");
  return tFn("panels.taskDetail.result.batchCounts", {
    total: totalRows ?? dash,
    succeeded: succeeded ?? dash,
    failed: failed ?? dash,
  });
});

const predictionSingleOutcomeLine = computed(() => {
  const single = taskResultSummaryToSingleResponse(summaryObj.value);
  return single ? formatPredictionResultOneLiner(single) : "";
});

const predictionDownloadUrl = computed(() => {
  const u = summaryObj.value.download_url;
  return typeof u === "string" && u.trim() ? u.trim() : "";
});

const predictionHistoryId = computed(() => {
  const p = taskRecord.value.params as Record<string, unknown> | undefined;
  const fromP = p?.history_record_id != null ? String(p.history_record_id).trim() : "";
  if (fromP) return fromP;
  const h = summaryObj.value.history_record_id;
  return h != null && String(h).trim() ? String(h).trim() : "";
});

const predictionHeadline = computed(() => String(summaryObj.value.headline || "").trim());

const predictionHeadlineSanitized = computed(() => sanitizeUserFacingLine(predictionHeadline.value, t));

const predictionProbDisplay = computed(() => {
  const rs = summaryObj.value;
  if (rs.probability == null && rs.predicted_probability == null) return "";
  const n = Number(rs.probability ?? rs.predicted_probability);
  if (Number.isNaN(n)) return "";
  return n <= 1 ? `${(n * 100).toFixed(1)}%` : String(n);
});

const predictionLabelRaw = computed(() => {
  const rs = summaryObj.value;
  if (rs.predicted_label == null) return "";
  return String(rs.predicted_label).trim();
});

const predictionResultOverview = computed(() => {
  if (!detail.value || !isPredictionJob.value) return false;
  if (isBatchPredictionTask.value) {
    return Boolean(
      predictionHeadline.value ||
        predictionModelDisplay.value ||
        predictionBatchFile.value ||
        predictionBatchCounts.value ||
        predictionDownloadUrl.value ||
        predictionHistoryId.value,
    );
  }
  return Boolean(
    predictionHeadline.value ||
      predictionSingleOutcomeLine.value ||
      predictionProbDisplay.value ||
      predictionLabelRaw.value ||
      predictionModelDisplay.value ||
      predictionHistoryId.value,
  );
});

const reportGenerationNotice = computed(() => {
  if (!isTrainingJobType(String(detail.value?.task.job_type || ""))) return "";
  const st = String(detail.value?.task.status || "").toLowerCase();
  if (st !== "completed" && st !== "succeeded" && st !== "success") return "";
  const rs = summaryObj.value;
  const rg = rs.report_generation_status;
  if (rg == null) return "";
  if (String(rg) === "ok") return "";
  const err = String(rs.report_generation_error || "").trim();
  return err || tFn("panels.taskDetail.result.reportGenerationFailedNotice");
});

const hasAnyResult = computed(() => {
  if (!detail.value) return false;
  if (isPredictionJobType(String(detail.value.task.job_type || ""))) return false;
  if (isRecommendationJobType(String(detail.value.task.job_type || ""))) return hasRecommendationOverview.value;
  if (modelIdResolved.value) return true;
  if (artifactEntries.value.length > 0) return true;
  if (metricEntries.value.length > 0) return true;
  if (publishSummary.value) return true;
  const rs = detail.value.task.result_summary;
  if (rs && typeof rs === "object" && Object.keys(rs as object).length > 0) return true;
  return false;
});

const isFailedOrCanceled = computed(() => {
  const s = String(detail.value?.task.status || "").toLowerCase();
  return s === "failed" || s === "canceled" || s === "cancelled";
});
const isDeletingTask = computed(() => {
  const id = String(detail.value?.task?.id || "");
  if (!id) return false;
  return Boolean((props.deletingTaskStatuses || {})[id]);
});
const deleteButtonLabel = computed(() => {
  const id = String(detail.value?.task?.id || "");
  const st = String((props.deletingTaskStatuses || {})[id] || "");
  if (st === "canceling") return t("panels.taskDetail.delete.canceling");
  if (st === "deleting") return t("panels.taskDetail.delete.deleting");
  return t("panels.taskDetail.delete.deleteCurrent");
});

const failureReason = computed(() => getReadableTaskFailureReason(taskRecord.value, t));

function syncWorkflowFormFromTask() {
  const t = detail.value?.task;
  if (!t || String(t.status) !== "waiting_user") return;
  const ph = trainingWorkflowPhase.value;
  const p = (t.params || {}) as Record<string, unknown>;
  const rs = summaryObj.value;
  if (ph === WF_PHASE3) {
    const sug = (rs.suggested_final_features as string[]) || [];
    phase3Pick.value = Array.isArray(sug) ? sug.map((x) => String(x)) : [];
  }
  if (ph === WF_PHASE4) {
    p4ModelType.value = String(p.model_type || "xgboost");
    p4Objective.value = String(p.objective_metric || (p.ml_task_type === "regression" ? "mse" : "auroc"));
    p4EnableSearch.value = Boolean(p.enable_search);
    const options = p4MetricOptions.value;
    if (options.length && !options.some((o) => o.value === p4Objective.value)) {
      p4Objective.value = options[0].value;
    }
  }
  if (ph === WF_PHASE5) {
    p5DoPublish.value = true;
    p5ModelId.value = "";
    p5Notes.value = "";
  }
}

async function reloadDetail() {
  const id = props.jobId;
  if (!id) return;
  detail.value = await getTaskDetail(id);
  syncWorkflowFormFromTask();
}

watch(
  () => props.jobId,
  async (id) => {
    detailTab.value = "summary";
    loadError.value = "";
    detail.value = null;
    if (!id) return;
    loading.value = true;
    try {
      detail.value = await getTaskDetail(id);
      syncWorkflowFormFromTask();
    } catch (e) {
      if (e instanceof ApiError) {
        loadError.value = t("panels.taskDetail.loadErrorWithCode", { message: e.message, code: e.code });
      } else {
        loadError.value = t("panels.taskDetail.loadErrorGeneric", { message: String(e) });
      }
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);

watch(
  () => [detail.value?.task?.status, trainingWorkflowPhase.value, taskRecord.value.params] as const,
  () => {
    syncWorkflowFormFromTask();
  },
);

function metricLabel(key: string): string {
  return trainingMetricLabel(key);
}

function metricValueDisplay(v: unknown): string {
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(4) : String(v);
  return String(v);
}

function artifactLabel(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("all_model_metrics")) return tFn("panels.taskDetail.result.artifactLabels.allModelMetrics");
  if (lower.includes("cv_results")) return tFn("panels.taskDetail.result.artifactLabels.cvResults");
  if (lower.includes("final_features")) return tFn("panels.taskDetail.result.artifactLabels.finalFeatures");
  if (lower.includes("phase2_feature_summary")) return tFn("panels.taskDetail.result.artifactLabels.phase2FeatureSummary");
  if (lower.includes("config")) return tFn("panels.taskDetail.result.artifactLabels.configSnapshot");
  if (lower.includes("metrics")) return tFn("panels.taskDetail.result.artifactLabels.metrics");
  if (lower.includes("report")) return tFn("panels.taskDetail.result.artifactLabels.trainingReport");
  if (lower.includes("shap")) return tFn("panels.taskDetail.result.artifactLabels.shapArtifacts");
  if (lower.endsWith(".png")) return tFn("panels.taskDetail.result.artifactLabels.chart");
  if (lower.includes("recommendation.json")) return tFn("panels.taskDetail.result.artifactLabels.recommendationJson");
  if (lower.includes("roc") || lower.includes("pr_curve")) return tFn("panels.taskDetail.result.artifactLabels.performanceCurves");
  return tFn("panels.taskDetail.result.artifactLabels.default");
}
</script>

<style scoped>
.task-detail-root {
  font-size: var(--wb-font-size-sm);
  line-height: var(--wb-line-height);
  color: var(--wb-text-primary);
}

.task-detail-tabbar {
  display: flex;
  gap: var(--wb-space-1);
  margin-bottom: var(--wb-space-3);
  padding-bottom: var(--wb-space-2);
  border-bottom: 1px solid var(--wb-border);
}

.task-detail-tab {
  flex: 1;
  min-height: var(--wb-control-height-sm);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface-soft);
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
  font-weight: 650;
  cursor: pointer;
}

.task-detail-tab.is-active {
  border-color: var(--wb-accent);
  background: var(--wb-accent-soft);
  color: var(--wb-text-primary);
}

.task-detail-tab-panel {
  min-height: 0;
}

.task-detail-logs-panel .task-log-box {
  margin-top: var(--wb-space-2);
}

.task-detail-root h4 {
  margin: var(--wb-space-3) 0 var(--wb-space-2);
  font-size: var(--wb-detail-section-title-size);
  font-weight: var(--wb-detail-section-title-weight);
  line-height: var(--wb-line-height-tight);
  color: var(--wb-text-primary);
}

.task-detail-root h4:first-of-type,
.task-detail-root .task-h4-first {
  margin-top: 0;
}

.task-detail-muted {
  color: var(--wb-text-secondary);
}

.task-inline-muted {
  color: var(--wb-text-secondary);
}

.task-load-error {
  padding: var(--wb-chat-bubble-padding-x);
  border: 1px solid #f5c2c7;
  background: #fdf0f1;
  border-radius: var(--wb-radius-xs);
}

.task-h4-first {
  margin-top: 0;
}

.task-body-dense {
  font-size: var(--wb-font-size-xs);
  line-height: 1.65;
}

.task-body-tight {
  line-height: 1.6;
}

.task-mt-s {
  margin-top: var(--wb-space-1);
}

.task-mt-m {
  margin-top: var(--wb-chat-input-padding-y);
}

.task-mt-m-lg {
  margin-top: var(--wb-chat-input-padding-x);
}

.task-flow-callout {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-chat-input-padding-y);
  border: 1px solid #d0d7de;
  border-radius: var(--wb-radius-xs);
  background: #f6f8fa;
  font-size: var(--wb-font-size-xs);
  color: #444;
}

.task-fs-body {
  font-size: var(--wb-font-size-xs);
}

.task-inline-code {
  font-size: var(--wb-font-size-2xs);
  color: var(--wb-text-muted);
}

.task-phase3-scroll {
  max-height: none;
  overflow: visible;
  border: 1px solid #dbe6f2;
  border-radius: var(--wb-space-micro);
  padding: var(--wb-chat-input-padding-y);
  margin-top: var(--wb-chat-input-padding-y);
}

.task-phase3-label {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-chat-input-padding-y);
  align-items: center;
  font-size: var(--wb-font-size-xs);
  margin: var(--wb-space-micro) 0;
}

.task-p3-friendly {
  font-weight: 600;
  color: var(--wb-text-primary);
}
.task-form-label {
  display: block;
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
}

.task-select-full {
  width: 100%;
  margin-top: var(--wb-space-micro);
}

.task-checkbox-row {
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  align-items: center;
  margin-top: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-xs);
}

.task-hint-muted {
  margin-top: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-2xs);
  color: #57606a;
}

.task-inline-label {
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
}

.task-input-block {
  display: block;
  width: 100%;
  margin-top: var(--wb-space-micro);
}

.task-artifact-list {
  margin: var(--wb-space-micro) 0;
  padding-left: calc(var(--wb-space-3) + 2px);
}

.task-metric-line {
  margin-left: var(--wb-chat-input-padding-y);
}

.task-report-notice {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-chat-input-padding-y);
  border-radius: var(--wb-space-micro);
  background: #fff8e6;
  border: 1px solid #f0d060;
  font-size: var(--wb-font-size-xs);
  color: #5d4e37;
}

.task-failure-box {
  padding: var(--wb-chat-input-padding-y);
  background: #fdf0f1;
  border: 1px solid #f5c2c7;
  border-radius: var(--wb-space-micro);
  font-size: var(--wb-font-size-xs);
  white-space: pre-wrap;
}

.task-log-box {
  max-height: none;
  overflow: visible;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-2);
  background: var(--wb-surface-soft);
}

.task-log-row {
  margin-bottom: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
}

.task-tech-root {
  margin-top: var(--wb-space-2);
  border: 1px dashed var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-2);
}

.task-tech-root summary {
  cursor: pointer;
  user-select: none;
  font-weight: 650;
}

.task-tech-intro {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.task-tech-line {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
}

.task-tech-nested {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
}

.task-tech-nested summary {
  cursor: pointer;
}

.task-pre {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-chat-input-padding-y);
  background: #f8f8f8;
  border: 1px solid #e5e5e5;
  border-radius: var(--wb-space-micro);
  overflow: auto;
  max-height: var(--wb-scroll-max-lg);
  font-size: var(--wb-font-size-2xs);
}

.task-tech-kv {
  margin-top: var(--wb-space-1);
}

.task-tech-kv-row {
  margin-bottom: var(--wb-space-micro);
  font-size: var(--wb-font-size-2xs);
}

.task-flow-hint {
  margin: var(--wb-space-2) 0;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-2);
  background: #fafbfc;
}

.task-flow-hint summary {
  cursor: pointer;
  font-weight: 650;
}

.task-pred-overview {
  font-size: var(--wb-font-size-sm);
  line-height: 1.65;
}

.task-msg-secondary {
  margin-top: var(--wb-space-micro);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-muted, #8a92a1);
  line-height: 1.45;
}

.task-msg-supplement {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
}

.task-msg-supplement summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--wb-text-secondary);
}

.task-msg-supplement-body {
  margin-top: var(--wb-space-1);
  white-space: pre-wrap;
  line-height: 1.5;
  color: var(--wb-text-primary);
}

.task-pred-headline-fold {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
}

.task-pred-headline-fold summary {
  cursor: pointer;
  font-weight: 600;
}

.task-log-box-nested {
  max-height: 240px;
  overflow: auto;
}

.task-rec-overview {
  font-size: var(--wb-font-size-xs);
  line-height: 1.65;
}

.task-rec-artifact {
  margin-top: var(--wb-chat-input-padding-y);
}
</style>
