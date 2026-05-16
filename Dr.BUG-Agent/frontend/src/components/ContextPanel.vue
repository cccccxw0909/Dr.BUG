<template>
  <div
    class="context-panel"
    :class="{
      'context-panel-fill': mode === 'tasks' || mode === 'models' || mode === 'datasets',
      'context-panel-workbench-scroll': mode === 'workbench',
    }"
    data-testid="context-panel"
  >
    <template v-if="mode === 'workbench'">
      <section class="context-card context-card-plain context-card-resources">
        <div class="context-card-title">{{ $t("panels.context.current.configurationTitle") }}</div>
        <div class="context-resource-grid">
          <div class="context-resource-row">
            <span class="context-resource-label">{{ $t("panels.context.current.dataset") }}</span>
            <span class="context-resource-value">{{ datasetValue }}</span>
          </div>
          <div class="context-resource-row">
            <span class="context-resource-label">{{ $t("panels.context.current.model") }}</span>
            <span class="context-resource-value">{{ modelValue }}</span>
          </div>
          <div class="context-resource-row">
            <span class="context-resource-label">{{ $t("panels.context.current.task") }}</span>
            <span class="context-resource-value">{{ taskValue }}</span>
          </div>
        </div>
      </section>

      <section class="context-card context-card-plain">
        <div class="context-card-title">{{ $t("panels.context.current.status") }}</div>
        <div class="context-status-head">
          <span class="wb-status" :class="statusToneClass">{{ workspaceStatus.label }}</span>
          <span class="context-inline-meta">{{ workspaceStatus.desc }}</span>
        </div>
        <div v-if="workspaceProgress !== null" class="context-progress">
          <div class="context-progress-track">
            <div class="context-progress-fill" :style="{ width: `${workspaceProgress}%` }" />
          </div>
          <div class="context-inline-meta">{{ $t("panels.context.labels.progress") }} {{ workspaceProgress }}%</div>
        </div>
        <div class="context-subsection">
          <div class="context-card-subtitle">{{ $t("panels.context.recentResult.title") }}</div>
          <div v-if="trainingLastResultLine" class="context-activity-row">
            <span class="context-resource-label">{{ $t("panels.context.recentResult.lastTraining") }}</span>
            <span class="context-resource-value">{{ trainingLastResultLine }}</span>
          </div>
          <div v-if="predictionSummary?.lastResult" class="context-activity-row context-activity-prediction-single">
            <span class="context-resource-label">{{ $t("panels.context.recentResult.lastSinglePrediction") }}</span>
            <div class="context-prediction-compact-lines">
              <div class="context-prediction-compact-line1">{{ lastSinglePredictionCompact.line1 }}</div>
              <div v-if="lastSinglePredictionCompact.line2" class="context-prediction-compact-line2">
                {{ lastSinglePredictionCompact.line2 }}
              </div>
            </div>
            <span class="context-inline-meta">{{ formatActivityTs(predictionSummary.lastResult.timestamp) }}</span>
          </div>
          <div v-else-if="bothPredictionEmpty" class="context-inline-meta">
            {{ $t("panels.context.recentResult.emptyPredictionSession") }}
          </div>
          <div v-else class="context-inline-meta">{{ $t("panels.context.recentResult.emptySingleHint") }}</div>

          <div v-if="batchPredictionSummary?.lastResult" class="context-activity-row">
            <span class="context-resource-label">{{ $t("panels.context.recentResult.lastBatchPrediction") }}</span>
            <span class="context-resource-value">{{ batchPredictionLine }}</span>
            <span class="context-inline-meta">{{ formatActivityTs(batchPredictionSummary.lastResult.timestamp) }}</span>
          </div>
          <div v-else-if="!bothPredictionEmpty" class="context-inline-meta">
            {{ $t("panels.context.recentResult.emptyBatchHint") }}
          </div>

          <template v-if="recommendationSummary">
            <div v-if="recommendationSummary.running" class="context-activity-row context-activity-regimen">
              <span class="context-resource-label">{{ $t("panels.context.recommendationSummary.title") }}</span>
              <span class="context-resource-value">{{ $t("panels.context.recommendationSummary.runningHint") }}</span>
            </div>
            <div v-else-if="recommendationSummary.lastSummary" class="context-activity-row context-activity-regimen">
              <span class="context-resource-label">{{ $t("panels.context.recommendationSummary.title") }}</span>
              <div class="context-prediction-compact-lines">
                <div class="context-prediction-compact-line1">{{ recommendationSummary.lastSummary.line1 }}</div>
                <div v-if="recommendationSummary.lastSummary.line2" class="context-prediction-compact-line2">
                  {{ recommendationSummary.lastSummary.line2 }}
                </div>
              </div>
            </div>
            <div v-else class="context-inline-meta">{{ $t("panels.context.recommendationSummary.emptyHint") }}</div>
          </template>
        </div>
      </section>
    </template>

    <template v-else-if="mode === 'tasks'">
      <div class="context-panel-detail-stack">
        <h3 class="wb-section-title context-page-title">{{ $t("panels.context.taskDetails.title") }}</h3>
        <div class="context-content-block context-panel-task-detail-scroll">
          <TaskDetailPanel
            :job-id="selectedTaskId"
            :deleting-task-statuses="deletingTaskStatuses || {}"
            @go-models="emit('goModels', $event)"
            @delete-task="emit('deleteTask', $event)"
          />
        </div>
      </div>
    </template>

    <template v-else-if="mode === 'datasets'">
      <template v-if="(datasetsSection || 'data') === 'data'">
        <div class="context-panel-detail-stack">
          <h3 class="wb-section-title context-page-title">{{ $t("panels.context.datasetDetails.title") }}</h3>
          <div v-if="!selectedDataset" class="context-empty-tip">
            {{ $t("panels.context.empty.datasetDetailsHint") }}
          </div>
          <div v-else class="context-detail-stack-inner context-panel-detail-scroll context-panel-detail-scroll-edge">
            <section class="context-card context-detail-card">
              <div class="context-detail-card-title wb-detail-panel-section-title">{{ $t("panels.context.cards.datasetSummary") }}</div>
              <dl class="wb-detail-summary-kv">
                <div class="wb-detail-summary-row">
                  <dt>{{ $t("panels.context.datasetSummaryLabels.name") }}</dt>
                  <dd>{{ selectedDataset.name || selectedDataset.file_name || $t("common.na") }}</dd>
                </div>
                <div class="wb-detail-summary-row">
                  <dt>{{ $t("panels.context.datasetSummaryLabels.status") }}</dt>
                  <dd>
                    <span v-if="selectedDataset.id === workbenchDatasetId" class="wb-status wb-status-pending">{{
                      $t("panels.context.badges.current")
                    }}</span>
                    <span v-else class="context-status-muted">{{ $t("panels.context.labels.statusNotCurrent") }}</span>
                  </dd>
                </div>
                <div class="wb-detail-summary-row">
                  <dt>{{ $t("panels.context.datasetSummaryLabels.datasetId") }}</dt>
                  <dd class="wb-detail-summary-id">{{ selectedDataset.id }}</dd>
                </div>
                <div class="wb-detail-summary-row">
                  <dt>{{ $t("panels.context.datasetSummaryLabels.fileFormat") }}</dt>
                  <dd>{{ selectedDataset.file_type || $t("common.na") }}</dd>
                </div>
                <div class="wb-detail-summary-row">
                  <dt>{{ $t("panels.context.datasetSummaryLabels.uploadedAt") }}</dt>
                  <dd>{{ formatDisplayDateTime(selectedDataset.created_at) }}</dd>
                </div>
                <div class="wb-detail-summary-row">
                  <dt>{{ $t("panels.context.datasetSummaryLabels.description") }}</dt>
                  <dd>{{ selectedDataset.description || $t("common.na") }}</dd>
                </div>
              </dl>
            </section>

            <section class="context-card context-detail-card">
              <div class="context-detail-card-title wb-detail-panel-section-title">{{ $t("panels.context.cards.dataAccess") }}</div>
              <p class="context-access-note">{{ $t("panels.context.datasetAccess.shortPrivacyNote") }}</p>
              <div class="context-access-btn-row">
                <button
                  type="button"
                  class="wb-btn wb-btn-secondary wb-btn-sm"
                  :disabled="datasetPreviewDisabled"
                  :title="datasetPreviewDisabled ? $t('panels.context.datasetAccess.previewUnavailableTitle') : ''"
                  @click="emitOpenDatasetAccess('preview')"
                >
                  {{ $t("panels.context.actions.previewDataset") }}
                </button>
                <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="openDatasetDownload(selectedDataset.id)">
                  {{ $t("panels.context.actions.downloadFile") }}
                </button>
                <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="emitOpenDatasetAccess('schema')">
                  {{ $t("panels.context.actions.viewFieldSchema") }}
                </button>
              </div>
            </section>

            <section class="context-card context-detail-card">
              <div class="context-detail-card-title wb-detail-panel-section-title">{{ $t("panels.context.labels.availableTasks") }}</div>
              <div v-if="orderedDatasetTasks.length === 0" class="wb-text-secondary">{{ $t("panels.context.empty.unspecified") }}</div>
              <div v-else class="context-detail-task-chips" role="list">
                <span v-for="task in orderedDatasetTasks" :key="task" class="context-detail-task-chip" role="listitem">{{
                  datasetTaskLabel(task)
                }}</span>
              </div>
            </section>

            <div class="context-actions context-actions-dataset-footer">
              <template v-if="selectedDataset.id === workbenchDatasetId">
                <span class="wb-status wb-status-pending context-footer-current-pill" role="status">{{
                  $t("panels.context.actions.currentDataset")
                }}</span>
              </template>
              <button
                v-else
                type="button"
                class="wb-btn wb-btn-secondary"
                @click="emit('setCurrentDataset', selectedDataset.id)"
              >
                {{ $t("panels.context.actions.setCurrentDataset") }}
              </button>
              <button type="button" class="wb-btn wb-btn-primary" @click="emit('trainWithDataset', selectedDataset.id)">
                {{ $t("panels.context.actions.startTraining") }}
              </button>
            </div>
          </div>
        </div>
        <DatasetAccessDialog
          v-if="datasetAccessDialog"
          :dataset-id="datasetAccessDialog.datasetId"
          :mode="datasetAccessDialog.mode"
          :dataset-label="datasetAccessDialog.datasetLabel"
          @close="emit('closeDatasetAccess')"
          @preview-failed="emit('datasetPreviewFailed', $event)"
        />
      </template>
      <template v-else>
        <div class="context-panel-detail-stack">
          <h3 class="wb-section-title context-page-title">{{ $t("panels.context.regimenDetails.title") }}</h3>
          <div class="context-panel-detail-scroll context-panel-detail-scroll-edge">
            <RegimenRightPanel
              :regimen="selectedRegimen"
              @regimen-updated="emit('regimenUpdated', $event)"
              @regimen-edit-request="emit('regimenEditRequest', $event)"
              @regimen-delete-request="emit('regimenDeleteRequest', $event)"
            />
          </div>
        </div>
      </template>
    </template>

    <template v-else-if="mode === 'models'">
      <div class="context-panel-detail-stack">
        <h3 class="wb-section-title context-page-title">{{ $t("panels.context.modelDetails.title") }}</h3>
        <div class="context-content-block context-panel-task-detail-scroll">
          <ModelDetailPanel
            :model-id="selectedModelId"
            :model="selectedModel"
            :current-model-id="selectedModelId"
            :detail-error="modelDetailError"
            @set-current="emit('setCurrentModel', $event)"
            @edit-model="emit('editModel', $event)"
            @delete-model="emit('deleteModel', $event)"
          />
        </div>
      </div>
    </template>

    <template v-else>
      <h3 class="wb-section-title context-page-title">{{ $t("panels.context.historyDetails.title") }}</h3>
      <div class="context-empty-tip">{{ $t("panels.context.empty.historyDetailsHint") }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import DatasetAccessDialog from "./DatasetAccessDialog.vue";
import ModelDetailPanel from "./ModelDetailPanel.vue";
import RegimenRightPanel from "./RegimenRightPanel.vue";
import TaskDetailPanel from "./TaskDetailPanel.vue";
import { getDatasetFileDownloadUrl } from "../api";
import type { DatasetMeta, ModelMeta, NavKey, PredictionSingleResponse, RegimenRecord, TaskItem } from "../types";
import { sortDatasetTasksForDisplay } from "../utils/datasetTaskOrder";
import { formatDisplayDateTime } from "../utils/dateFormat";
import { modelDisplayName } from "../utils/modelPresentation";
import { formatPredictionContextLastSingleLines } from "../utils/predictionPresentation";
import { sanitizeUserFacingLine } from "../utils/messageSanitizer";
import { formatJobTypeLabel, formatTaskStatusLabel, isTrainingJobType } from "../utils/taskPresentation";
import { localizeTrainingResultHeadlineForEnUi } from "../utils/trainingBackendDisplayGuard";
import { formatTaskListProgressLine, formatTaskStatusCompanionLine } from "../utils/taskStatusNarrative";
import { getTrainingWorkflowDisplayState } from "../utils/trainingWorkflowCard";

const { t: i18nT, te } = useI18n();

function formatActivityTs(timeIso: string): string {
  const s = formatDisplayDateTime(timeIso);
  const dash = i18nT("common.na");
  return s && s !== dash ? i18nT("panels.context.labels.timeWithValue", { time: s }) : "";
}

/** Clinical task chips: root taskKinds.* (same strings as pages.datasets.taskLabels). */
function datasetTaskLabel(task: string): string {
  const key = `taskKinds.${task}`;
  if (te(key)) return i18nT(key);
  return task;
}

export type DatasetAccessDialogPayload = {
  datasetId: string;
  mode: "preview" | "schema";
  datasetLabel?: string;
};

const {
  mode,
  datasetsSection,
  tasks,
  selectedTaskId,
  selectedDataset,
  selectedRegimen,
  selectedModel,
  selectedModelId,
  modelDetailError,
  deletingTaskStatuses,
  predictionSummary,
  batchPredictionSummary,
  recommendationSummary = null,
  workbenchDatasetId = null,
  datasetAccessDialog = null,
  datasetPreviewUnavailable,
} = defineProps<{
    mode: NavKey;
    datasetsSection?: "data" | "regimens";
    tasks: Array<TaskItem & Record<string, unknown>>;
    selectedTaskId: string | null;
    selectedDataset: DatasetMeta | null;
    selectedRegimen?: RegimenRecord | null;
    /** Workbench “current” dataset id (same ref as list selection in normal flows). */
    workbenchDatasetId?: string | null;
    datasetAccessDialog?: DatasetAccessDialogPayload | null;
    datasetPreviewUnavailable?: Record<string, boolean>;
    selectedModel: ModelMeta | null;
    selectedModelId: string | null;
    modelDetailError?: string;
    deletingTaskStatuses?: Record<string, string>;
    predictionSummary?: {
    active: boolean;
    predictRunning?: boolean;
    modelId: string | null;
    displayName?: string | null;
    taskName?: string | null;
    fieldCount: number;
    filledCount: number;
    missingRequiredCount: number;
    errorCount: number;
    step?: string;
    canExecute?: boolean;
    executeHint?: string | null;
    lastResult?: PredictionSingleResponse | null;
  } | null;
  batchPredictionSummary?: {
    active: boolean;
    modelId: string | null;
    fileName: string;
    checkStatus: string;
    matchedCount: number;
    missingCount: number;
    extraCount: number;
    runRunning?: boolean;
    lastResult?: {
      task_name: string;
      file_name?: string;
      display_name?: string;
      total_rows: number;
      succeeded_rows: number;
      failed_rows: number;
      timestamp: string;
    } | null;
  } | null;
  recommendationSummary?: {
    running: boolean;
    lastSummary: { jobId: string; line1: string; line2: string | null } | null;
  } | null;
  }>();

const datasetPreviewDisabled = computed(() => {
  const id = selectedDataset?.id;
  if (!id) return false;
  return !!datasetPreviewUnavailable?.[id];
});

const orderedDatasetTasks = computed(() => sortDatasetTasksForDisplay(selectedDataset?.available_tasks ?? []));

const emit = defineEmits<{
  (e: "setCurrentDataset", datasetId: string): void;
  (e: "trainWithDataset", datasetId: string): void;
  /** Optional job_id for locating the same record in the tasks page. */
  (e: "goTasks", jobId: string | null): void;
  (e: "goModels", modelId: string | null): void;
  (e: "setCurrentModel", modelId: string): void;
  (e: "deleteTask", jobId: string): void;
  (e: "regimenUpdated", regimen: RegimenRecord): void;
  (e: "editModel", modelId: string): void;
  (e: "deleteModel", modelId: string): void;
  (e: "openDatasetAccess", payload: DatasetAccessDialogPayload): void;
  (e: "closeDatasetAccess"): void;
  (e: "datasetPreviewFailed", datasetId: string): void;
  (e: "regimenEditRequest", regimen: RegimenRecord): void;
  (e: "regimenDeleteRequest", regimen: RegimenRecord): void;
}>();

function emitOpenDatasetAccess(accessMode: "preview" | "schema") {
  const d = selectedDataset;
  if (!d) return;
  emit("openDatasetAccess", {
    datasetId: d.id,
    mode: accessMode,
    datasetLabel: String(d.name || d.file_name || "").trim() || undefined,
  });
}

function openDatasetDownload(datasetId: string) {
  window.location.href = getDatasetFileDownloadUrl(datasetId);
}

const selectedTask = computed(() => {
  if (!selectedTaskId) return null;
  return tasks.find((t) => String(t.id) === String(selectedTaskId)) || null;
});

const bothPredictionEmpty = computed(
  () => !predictionSummary?.lastResult && !batchPredictionSummary?.lastResult,
);

const lastSinglePredictionCompact = computed(() => {
  const r = predictionSummary?.lastResult;
  if (!r) return { line1: "", line2: null as string | null };
  try {
    const x = formatPredictionContextLastSingleLines(r, i18nT);
    if (x.line1.trim()) return x;
  } catch {
    /* ignore */
  }
  const dash = i18nT("common.na");
  return { line1: `${r.display_name || dash} · ${r.task_name || dash}`, line2: null };
});

const datasetValue = computed(() => selectedDataset?.name || selectedDataset?.file_name || i18nT("panels.context.empty.noDataset"));
const modelValue = computed(() =>
  selectedModel ? modelDisplayName(selectedModel as Record<string, unknown>) : i18nT("panels.context.empty.noModel"),
);
const taskValue = computed(() => {
  if (!selectedTaskId) return i18nT("panels.context.empty.noTask");
  const task = selectedTask.value;
  if (!task) return i18nT("panels.context.empty.selectTaskHint");
  const jt = formatJobTypeLabel(String(task.job_type || ""), i18nT);
  const st = formatTaskStatusLabel(String(task.status || ""), i18nT);
  if (isTrainingJobType(String(task.job_type || "")) && String(task.status || "").toLowerCase() === "waiting_user") {
    const wf = getTrainingWorkflowDisplayState(task as TaskItem & Record<string, unknown>, i18nT);
    const title = wf.workflowBusinessTitle;
    return `${jt} · ${st} · ${title}`;
  }
  const companion =
    formatTaskStatusCompanionLine(task as Record<string, unknown>, i18nT) ||
    formatTaskListProgressLine(task as Record<string, unknown>, i18nT);
  return companion ? i18nT("panels.context.taskValue.withCompanion", { jobType: jt, status: st, companion }) : `${jt} · ${st}`;
});

const batchPredictionLine = computed(() => {
  const lr = batchPredictionSummary?.lastResult;
  if (!lr) return "";
  const displayName = String(lr.display_name || lr.task_name || "").trim() || i18nT("common.na");
  const failed = Number(lr.failed_rows);
  if (Number.isFinite(failed) && failed > 0) {
    return i18nT("panels.context.batchPredictionSummary.countsWithFailed", {
      displayName,
      total: lr.total_rows,
      succeeded: lr.succeeded_rows,
      failed,
    });
  }
  return i18nT("panels.context.batchPredictionSummary.counts", {
    displayName,
    total: lr.total_rows,
    succeeded: lr.succeeded_rows,
  });
});

/** When a training task is selected and completed, show a short summary in "Recent results". */
const trainingLastResultLine = computed(() => {
  const task = selectedTask.value as (TaskItem & Record<string, unknown>) | null;
  if (!task || !isTrainingJobType(String(task.job_type || ""))) return "";
  const st = String(task.status || "").toLowerCase();
  if (st !== "completed" && st !== "success" && st !== "succeeded") return "";
  const rs = (task.result_summary as Record<string, unknown>) || {};
  let headline = sanitizeUserFacingLine(String(rs.headline || ""), i18nT) || String(rs.headline || "").trim();
  headline = localizeTrainingResultHeadlineForEnUi(headline, i18nT);
  const released = Boolean(rs.model_registered) || Boolean(rs.is_published);
  const rel = released ? i18nT("taskNarrative.companion.trainingReleased") : i18nT("taskNarrative.companion.trainingNotReleased");
  if (headline) {
    const clip = headline.length > 100 ? `${headline.slice(0, 99)}…` : headline;
    return i18nT("taskNarrative.companion.trainingCompletedHeadline", { headline: clip, release: rel });
  }
  return i18nT("taskNarrative.companion.trainingCompletedFallback", { release: rel });
});

type StatusTone = "success" | "running" | "warning" | "error" | "pending";
const progressRaw = computed(() => Number((selectedTask.value as { progress?: unknown } | null)?.progress));

const workspaceStatus = computed<{ label: string; desc: string; tone: StatusTone }>(() => {
  const taskStatus = String((selectedTask.value as { status?: string } | null)?.status || "").toLowerCase();
  const progress = Number.isFinite(progressRaw.value) ? progressRaw.value : 0;
  if (batchPredictionSummary?.runRunning) {
    return { label: i18nT("workspace.status.running"), desc: i18nT("workspace.status.batchPredictionRunningDesc"), tone: "running" };
  }
  if (recommendationSummary?.running) {
    return {
      label: i18nT("workspace.status.running"),
      desc: i18nT("workspace.status.regimenComparisonRunningDesc"),
      tone: "running",
    };
  }
  if (predictionSummary?.predictRunning) {
    return { label: i18nT("workspace.status.running"), desc: i18nT("workspace.status.singlePredictionRunningDesc"), tone: "running" };
  }
  const sel = selectedTask.value as (TaskItem & Record<string, unknown>) | null;
  const companion = sel ? formatTaskStatusCompanionLine(sel as Record<string, unknown>, i18nT) : "";
  if (taskStatus === "running") {
    if (progress >= 95) return { label: i18nT("workspace.status.running"), desc: i18nT("workspace.status.nearCompletionDesc"), tone: "running" };
    if (sel && isTrainingJobType(String(sel.job_type || "")) && companion) {
      return { label: i18nT("workspace.status.runningInBackground"), desc: companion, tone: "running" };
    }
    return {
      label: i18nT("workspace.status.running"),
      desc: companion || i18nT("workspace.status.genericRunningDesc"),
      tone: "running",
    };
  }
  if (taskStatus === "waiting_user") {
    if (sel && isTrainingJobType(String(sel.job_type || ""))) {
      const wf = getTrainingWorkflowDisplayState(sel, i18nT);
      const title = wf.workflowBusinessTitle;
      return {
        label: i18nT("workspace.status.waitingConfirmation"),
        desc: i18nT("workspace.status.trainingWaitingConfirmDesc", { title }),
        tone: "pending",
      };
    }
    return {
      label: i18nT("workspace.status.waitingConfirmation"),
      desc: companion || i18nT("workspace.status.genericWaitingConfirmDesc"),
      tone: "pending",
    };
  }
  if (taskStatus === "queued") {
    if (progress > 0) return { label: i18nT("workspace.status.running"), desc: i18nT("workspace.status.startedProcessingDesc"), tone: "running" };
    return { label: i18nT("workspace.status.queued"), desc: companion || i18nT("workspace.status.queuedDesc"), tone: "pending" };
  }
  if (taskStatus === "completed" || taskStatus === "succeeded" || taskStatus === "success") {
    if (sel && isTrainingJobType(String(sel.job_type || ""))) {
      return { label: i18nT("workspace.status.trainingCompleted"), desc: companion || i18nT("workspace.status.trainingCompletedDesc"), tone: "success" };
    }
    if (sel && String(sel.job_type || "") === "recommend_regimen") {
      const jid = String(selectedTaskId || "").trim();
      const match =
        recommendationSummary?.lastSummary?.jobId &&
        jid &&
        recommendationSummary.lastSummary.jobId === jid;
      const desc =
        match && recommendationSummary?.lastSummary
          ? [recommendationSummary.lastSummary.line1, recommendationSummary.lastSummary.line2 || ""]
              .map((s) => s.trim())
              .filter(Boolean)
              .join(" · ")
          : i18nT("workspace.status.completedRegimenComparisonDesc");
      return { label: i18nT("workspace.status.completed"), desc, tone: "success" };
    }
    return { label: i18nT("workspace.status.completed"), desc: companion || i18nT("workspace.status.completedDesc"), tone: "success" };
  }
  if (taskStatus === "failed") {
    return { label: i18nT("workspace.status.failed"), desc: companion || i18nT("workspace.status.failedDesc"), tone: "error" };
  }
  if (taskStatus === "canceled" || taskStatus === "cancelled") {
    return { label: i18nT("workspace.status.canceled"), desc: companion || i18nT("workspace.status.canceledDesc"), tone: "pending" };
  }
  if (predictionSummary?.active) {
    if (predictionSummary.executeHint) {
      return { label: i18nT("workspace.status.pendingInput"), desc: predictionSummary.executeHint, tone: "pending" };
    }
    if (predictionSummary.canExecute) {
      return { label: i18nT("workspace.status.readyToExecute"), desc: i18nT("workspace.status.readyToExecuteDesc"), tone: "warning" };
    }
    return { label: i18nT("workspace.status.pendingInput"), desc: i18nT("workspace.status.pendingInputDesc"), tone: "pending" };
  }
  if (batchPredictionSummary?.active) {
    return { label: i18nT("workspace.status.pendingInput"), desc: i18nT("workspace.status.batchPendingInputDesc"), tone: "pending" };
  }
  return { label: i18nT("workspace.status.idle"), desc: i18nT("workspace.status.noActiveTask"), tone: "pending" };
});

const workspaceProgress = computed<number | null>(() => {
  const taskStatus = String((selectedTask.value as { status?: string } | null)?.status || "").toLowerCase();
  // When waiting for confirmation, a progress percentage can be misleading. Hide the progress bar.
  if (taskStatus === "waiting_user") return null;
  const p = progressRaw.value;
  if (!Number.isFinite(p)) return null;
  return Math.max(0, Math.min(100, Math.round(p)));
});

const statusToneClass = computed(() => {
  if (workspaceStatus.value.tone === "success") return "wb-status-success";
  if (workspaceStatus.value.tone === "running") return "wb-status-running";
  if (workspaceStatus.value.tone === "warning") return "wb-status-warning";
  if (workspaceStatus.value.tone === "error") return "wb-status-error";
  return "wb-status-pending";
});

</script>

<style scoped>
.context-panel {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  color: var(--wb-text-primary);
  font-size: var(--wb-font-size-sm);
  line-height: var(--wb-line-height);
}

.context-panel-workbench-scroll {
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: var(--wb-space-1);
}

.context-panel-fill {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.context-panel-detail-stack {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.context-panel-task-detail-scroll,
.context-panel-detail-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: var(--wb-space-1);
}

.context-panel-detail-scroll.context-panel-detail-scroll-edge {
  padding-left: 0;
  padding-right: 0;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.context-panel-fill .context-panel-detail-stack > .context-panel-task-detail-scroll,
.context-panel-fill .context-panel-detail-stack > .context-panel-detail-scroll {
  min-height: 0;
}

.context-panel-header {
  padding: var(--wb-space-3);
}

.context-meta-row {
  color: var(--wb-text-primary);
}

.context-note {
  margin: 0;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
}

.context-card {
  margin: var(--wb-space-2) 0;
  padding: var(--wb-space-3);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface);
  box-shadow: var(--wb-shadow-sm);
}

.context-card-plain {
  margin: 0;
}

.context-card-resources {
  padding-top: var(--wb-space-2);
}

.context-preview-block {
  margin-top: var(--wb-space-3);
  padding-top: var(--wb-space-2);
  border-top: 1px dashed var(--wb-border-strong);
}

.context-preview-note {
  margin: 0 0 var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  line-height: 1.5;
}

.context-card-prediction {
  border-color: #dbe4ef;
  background: #f8fbff;
}

.context-card-batch {
  border-color: #e4def2;
  background: #fbf9ff;
}

.context-card-title {
  margin-bottom: var(--wb-space-3);
  font-weight: 650;
  font-size: var(--wb-font-size-md);
}

.context-card-subtitle {
  margin-bottom: var(--wb-space-1);
  font-weight: 600;
}

.context-subsection {
  margin-top: var(--wb-space-3);
  padding-top: var(--wb-space-2);
  border-top: 1px dashed var(--wb-border-strong);
}

.context-explain {
  font-size: var(--wb-font-size-xs);
}

.context-inline-meta {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.context-status-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
}

.context-status-running {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-running);
}

.context-status-warning {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-warning);
}

.context-resource-grid {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
}

.context-resource-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.context-resource-label {
  font-size: var(--wb-font-size-xs);
  color: #222c3a;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.context-resource-value {
  font-size: var(--wb-font-size-sm);
  color: #6f7a8a;
  font-weight: 500;
  line-height: 1.45;
  word-break: break-word;
}

.context-progress {
  margin-top: var(--wb-space-3);
}

.context-progress-track {
  height: 6px;
  border-radius: 999px;
  background: #e8ecf2;
  overflow: hidden;
}

.context-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: #8fa4bc;
}

.context-activity-row {
  margin-bottom: var(--wb-space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.context-prediction-compact-lines {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 2px;
}

.context-prediction-compact-line1,
.context-prediction-compact-line2 {
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
  line-height: 1.4;
  letter-spacing: 0;
  color: #6f7a8a;
  word-break: break-word;
}

.context-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
  margin-top: var(--wb-space-2);
}

.context-action-column {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.context-action-btn {
  width: 100%;
  height: 38px;
  justify-content: center;
}

.context-content-block {
  margin-top: 0;
  min-height: 0;
}

.context-panel-detail-stack > .context-content-block {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.context-empty-tip {
  color: var(--wb-text-secondary);
}

.context-detail-stack-inner {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  width: 100%;
  max-width: none;
  box-sizing: border-box;
  align-self: stretch;
}

.context-detail-card {
  margin-top: 0;
}

.context-card.context-detail-card {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.context-card-section-heading {
  font-weight: 650;
  font-size: var(--wb-font-size-sm);
  margin-bottom: var(--wb-space-2);
}

.context-detail-card-title {
  margin-bottom: var(--wb-space-3);
}

.context-status-muted {
  font-size: var(--wb-font-size-sm);
  font-weight: 500;
  color: var(--wb-text-secondary);
}

.context-code-soft {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  word-break: break-all;
}

.context-access-note {
  margin: 0 0 var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
  font-weight: 400;
  color: var(--wb-text-secondary);
  line-height: 1.5;
}

.context-access-btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
}

.context-actions-dataset-footer {
  margin-top: var(--wb-space-1);
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.context-footer-current-pill {
  align-self: center;
}

.context-detail-task-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.context-detail-task-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border: 1px solid var(--wb-border);
  border-radius: 999px;
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
  color: var(--wb-text-primary);
  background: transparent;
  line-height: 1.3;
}

.context-chip-row {
  margin-top: var(--wb-space-1);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.context-chip {
  padding: 2px 8px;
  border: 1px solid var(--wb-border-strong);
  border-radius: 999px;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  background: var(--wb-surface-soft);
}

.context-page-title {
  margin: 0 0 var(--wb-space-1);
}

.context-tech {
  margin-top: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.context-tech summary {
  cursor: pointer;
  user-select: none;
  font-weight: 600;
}

</style>

