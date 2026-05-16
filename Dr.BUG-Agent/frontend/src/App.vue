<template>
  <WorkbenchLayout class="wb-app-shell" :hide-right="activeNav === 'history'">
    <template #left>
      <SidebarNav
        :active="activeNav"
        :sessions="sessions"
        :active-session-id="activeSessionId"
        @change="activeNav = $event"
        @newSession="newSession"
        @select-session="selectSession"
      />
    </template>

    <!-- Main outlet is driven only by activeNav; recovery cards belong inside Workbench and must not affect routing. -->
    <template #main>
      <div class="wb-main-stack">
        <div v-if="shellRecoveryBanner" class="wb-shell-recovery-banner" role="status">
          <span class="wb-shell-recovery-text">{{ shellRecoveryBanner }}</span>
          <button type="button" class="wb-btn wb-btn-text wb-btn-sm" @click="shellRecoveryBanner = ''">
            {{ t("app.shell.dismissRecovery") }}
          </button>
        </div>
        <div v-if="shellStaleDetected" class="wb-shell-manual-recovery" role="region" aria-label="Recovery">
          <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="resetShellWorkflowState">
            {{ t("app.shell.resetWorkflowUi") }}
          </button>
        </div>
        <div
          class="wb-main-outlet"
          :class="{ 'wb-main-outlet--workspace': activeNav === 'workbench' }"
          :key="activeNav"
        >
          <template v-if="activeNav === 'workbench'">
            <WorkbenchBoundary @recover="resetShellWorkflowState">
              <Workbench
        :key="activeSessionId"
        :messages="currentSessionMessages"
        :keep-welcome-intro="keepWorkbenchWelcomeIntro"
        :selected-dataset="selectedDataset"
        :context-dataset-id="selectedDataset?.id ?? null"
        :ui-error="uiError"
        :submitting-pending-action-id="confirmingPendingActionId"
        :action-confirm-error="actionConfirmError"
        :recovery-workflow-card="recoveryTrainingWorkflowCard"
        @send="onSend"
        @confirm="(d) => onConfirm(d)"
        @edit-params="onEditParams"
        @confirm-workflow="onConfirmWorkflow"
        @go-task="onGoTasks"
        @go-model="onGoModels"
        @start-prediction="onWorkbenchStartPrediction"
        @start-recommendation="onWorkbenchStartRecommendation"
        @recommendation-workflow-action="onRecommendationWorkflowAction"
        @prediction-form-action="onPredictionFormAction"
        @batch-prediction-action="onBatchPredictionAction"
        @request-cancel-training-job="onRequestCancelTrainingJob"
              />
            </WorkbenchBoundary>
          </template>
      <TasksPage
        v-else-if="activeNav === 'tasks'"
        :tasks="tasks"
        :deleting-task-statuses="deletingTaskStatuses"
        :selected-task-id="selectedTaskId"
        :load-error="tasksLoadError"
        :loading="tasksLoading"
        @select-task="selectTask"
        @refresh="refreshTasks"
        @delete-task="onDeleteTask"
      />
      <DatasetsPage
        ref="datasetsPageRef"
        v-else-if="activeNav === 'datasets'"
        :datasets="datasets"
        :selected-dataset-id="selectedDatasetId"
        :selected-regimen-id="selectedRegimen?.regimen_id ?? null"
        :regimen-refresh-signal="regimenRefreshSignal"
        :datasets-refreshing="datasetsLoading"
        @select-dataset="onSelectDatasetPage"
        @section-change="onDatasetsSectionChange"
        @select-regimen="onSelectRegimen"
        @regimen-deleted="onRegimenPanelDeleted"
        @delete-dataset="onDeleteDataset"
        @refresh-datasets="refreshDatasets"
      />
      <ModelsPage
        v-else-if="activeNav === 'models'"
        :models="models"
        :current-model-id="selectedModelId"
        :load-error="modelsLoadError"
        :loading="modelsLoading"
        :selection-missing="modelIdMissingInList"
        :pending-open-edit-model-id="pendingModelsPageOpenEditId"
        @select-model="selectModel"
        @pending-edit-consumed="pendingModelsPageOpenEditId = null"
        @refresh="refreshModels"
        @model-updated="onModelUpdatedFromPage"
        @model-deleted="onModelDeletedFromPage"
      />
      <HistoryPage v-else />
        </div>
      </div>
    </template>

    <template v-if="activeNav !== 'history'" #right>
      <ContextPanel
        :mode="activeNav"
        :datasets-section="datasetsUiSection"
        :tasks="tasks"
        :selected-task-id="selectedTaskId"
        :selected-dataset="selectedDataset"
        :selected-regimen="selectedRegimen"
        :workbench-dataset-id="selectedDatasetId"
        :dataset-access-dialog="datasetAccessDialog"
        :dataset-preview-unavailable="datasetPreviewUnavailable"
        :selected-model="selectedModel"
        :selected-model-id="selectedModelId"
        :model-detail-error="modelDetailError"
        :deleting-task-statuses="deletingTaskStatuses"
        :prediction-summary="predictionPanelSummary"
        :batch-prediction-summary="batchPredictionPanelSummary"
        :recommendation-summary="recommendationPanelSummary"
        @set-current-dataset="onSelectDatasetPage"
        @train-with-dataset="sendTrainCommandWithDataset"
        @go-tasks="onGoTasks"
        @go-models="onGoModels"
        @set-current-model="selectModel"
        @delete-task="onDeleteTask"
        @regimen-updated="onRegimenPanelSaved"
        @open-dataset-access="onOpenDatasetAccess"
        @close-dataset-access="datasetAccessDialog = null"
        @dataset-preview-failed="onDatasetPreviewFailed"
        @regimen-edit-request="onRegimenEditRequest"
        @regimen-delete-request="onRegimenDeleteRequest"
        @edit-model="onContextModelEdit"
        @delete-model="onContextModelDelete"
      />
    </template>
  </WorkbenchLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ApiError,
  cancelTask,
  deleteModel,
  deleteTask,
  deleteDataset,
  deleteRegimen,
  getDatasets,
  getModelDetail,
  getModels,
  fetchRecommendationArtifactJson,
  getAvailablePredictionModels,
  getPredictionModelSchema,
  getTaskDetail,
  getTaskStatus,
  getTasks,
  listRegimens,
  postChatTurn,
  postConfirm,
  postPredictionSingle,
  postPredictionBatchCheck,
  postPredictionBatchRun,
  postRecommendationJob,
  postTrainingWorkflow,
  type RecommendationJobCreatePayload,
} from "./api";
import ContextPanel from "./components/ContextPanel.vue";
import SidebarNav from "./components/SidebarNav.vue";
import WorkbenchLayout from "./layouts/WorkbenchLayout.vue";
import DatasetsPage from "./views/DatasetsPage.vue";
import HistoryPage from "./views/HistoryPage.vue";
import ModelsPage from "./views/ModelsPage.vue";
import TasksPage from "./views/TasksPage.vue";
import Workbench from "./views/Workbench.vue";
import WorkbenchBoundary from "./components/WorkbenchBoundary.vue";
import type {
  ChatTurnData,
  BatchFieldCheckResponse,
  BatchPredictionCardData,
  BatchPredictionChatAction,
  BatchPredictionRunResponse,
  DatasetMeta,
  ModelMeta,
  NavKey,
  PredictionFormCardData,
  PredictionFormChatAction,
  PredictionFormSubmittedSummary,
  PredictionTaskKey,
  PredictionSubmittedSummaryPayload,
  PredictionSingleResponse,
  RecommendationWorkflowCardData,
  RecommendationWorkflowChatAction,
  RegimenRecord,
  RegimenTreatmentValues,
  SessionItem,
  SurvivalRecommendationResult,
  TaskDetailData,
  TaskItem,
  TaskResultCardData,
  TrainingJobReceiptData,
} from "./types";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "./types";
import type { TrainingWorkflowPendingActionData, TrainingWorkflowPhase } from "./types";
import { missingTrainingPhase1ParameterKeys } from "./utils/trainingPayloadBuilder";
import { migrateSessionsFromStorage } from "./utils/sessionPresentation";
import { buildMergedPhase1TrainingPayload, buildUserFacingTrainingReceiptLines } from "./utils/trainingReceipt";
import {
  buildCompletionCard,
  buildFailureCard,
  getJobProgressMessage,
  shouldAnnounceTransition,
  taskDetailToPredictionSingleResponse,
  type AnnounceState,
} from "./utils/statusMessages";
import {
  analyzePredictionForm,
  buildInitialFormValues,
  getPredictionFormExecuteBlockers,
} from "./utils/predictionFormValidation";
import { formatPredictionApiError } from "./utils/predictionFailureMessage";
import { isSurvivalRecommendationCandidate } from "./utils/recommendationModelFilter";
import { buildPatientFeaturesPayload } from "./utils/recommendationPatientFeatures";
import { getRecommendationWorkflowBlockers } from "./utils/recommendationWorkflowValidation";
import { sanitizeUserFacingLine } from "./utils/messageSanitizer";
import {
  includesTrainingKeyword,
  isBatchPredictionEnterCommand,
  isExactStartPredictionCommand,
  isPredictionEnterCommand,
  isPredictionExecuteCommand,
  isPredictionExitCommand,
  isRecommendationWorkspaceEnterCommand,
} from "./utils/chatIntentMatchers";
import {
  canonicalApiTaskFromUiKey,
  inferPreferredPredictionTaskFromUserText,
  inferPredictionPanelModeFromUserText,
  inferPredictionTaskKeyFromModel,
  predictionModelsForTask,
} from "./utils/predictionTaskInference";
import { buildPredictionSubmitSummaryRows } from "./utils/predictionPresentation";
import {
  isTrainingJobType,
} from "./utils/taskPresentation";
import {
  buildTrainingWorkflowPendingCard,
  normalizeTrainingWorkflowPhase,
  resolveTrainingWorkflowPhase,
  taskRowNeedsWorkflowConfirmation,
} from "./utils/trainingWorkflowCard";
import {
  sessionChatHasTrainCompletionResult,
  sessionChatHasTrainFailureResult,
} from "./utils/trainingWorkflowCompletion";
import {
  getTerminalCanceledAssistantMessage,
  getTerminalCompletionAssistantMessage,
  getTerminalFailureAssistantPrefix,
} from "./utils/taskTerminalCopy";

const { t, te, locale } = useI18n();

/** Active vue-i18n locale for non-chat API bodies (prediction, confirm, recommendation). */
function apiUiLocale(): string {
  return String(locale.value || "");
}

function chatActionLabel(action: string): string {
  const key = `chat.actionLabels.${action}`;
  return te(key) ? t(key) : action;
}

function chatFieldLabel(field: string): string {
  const key = `chat.fieldLabels.${field}`;
  return te(key) ? t(key) : field;
}

type MessageItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
  kind?: "normal" | "status" | "error";
  actionData?: ChatTurnData | null;
  workflowActionData?: TrainingWorkflowPendingActionData | null;
  resultData?: TaskResultCardData | null;
  trainingReceiptData?: TrainingJobReceiptData | null;
  predictionResult?: PredictionSingleResponse | null;
  predictionFormCard?: PredictionFormCardData | null;
  batchPredictionCard?: BatchPredictionCardData | null;
  batchPredictionResult?: BatchPredictionRunResponse | null;
  recommendationWorkflowCard?: RecommendationWorkflowCardData | null;
  recommendationResult?: SurvivalRecommendationResult | null;
  predictionSubmittedSummary?: PredictionSubmittedSummaryPayload | null;
};

const activeNav = ref<NavKey>("workbench");
const sessions = ref<SessionItem[]>([{ id: "s1", created_at: new Date().toISOString(), defaultSlot: 1 }]);
const activeSessionId = ref<string>("s1");
const sessionMessages = ref<Record<string, MessageItem[]>>({
  s1: [],
});
const latestChatData = ref<ChatTurnData | null>(null);
const uiError = ref("");
/** Guard double-submit: pending_action_id currently being confirmed. */
const confirmingPendingActionId = ref<string | null>(null);
/** Guard double-submit for training workflow cards: `${jobId}|${phase}`. */
const confirmingWorkflowKey = ref<string | null>(null);
/** Watchdog: time workflow confirm guard was set (for stale UI recovery). */
const confirmingWorkflowSince = ref<number | null>(null);
const actionConfirmError = ref<{ pendingActionId: string; message: string } | null>(null);
/** App-shell: non-blocking banner after watchdog or interrupted chat turn recovery. */
const shellRecoveryBanner = ref("");
/** True after watchdog detects stuck local state; shows manual reset (does not cancel backend tasks). */
const shellStaleDetected = ref(false);
/** `postChatTurn` / main assistant reply path in-flight (watchdog clears if stuck). */
const chatTurnInFlight = ref(false);
const chatTurnStartedAt = ref<number | null>(null);
/** Detect stuck tasks list loading spinner. */
const tasksRefreshStartedAt = ref<number | null>(null);

const tasks = ref<Array<TaskItem & Record<string, unknown>>>([]);
const tasksLoadError = ref("");
const tasksLoading = ref(false);
const selectedTaskId = ref<string | null>(null);
/** Latest GET /tasks/:id for workflow recovery cards (SHAP URLs, feature lists). */
const taskDetailById = ref<Record<string, TaskDetailData>>({});
const datasets = ref<DatasetMeta[]>([]);
const datasetsLoading = ref(false);
const selectedDatasetId = ref<string | null>(null);
/** Datasets / regimen management: regimen detail for the right panel. */
const selectedRegimen = ref<RegimenRecord | null>(null);
const regimenRefreshSignal = ref(0);
const datasetsPageRef = ref<{ beginRegimenEdit?: (r: RegimenRecord) => void } | null>(null);
const datasetAccessDialog = ref<{
  datasetId: string;
  mode: "preview" | "schema";
  datasetLabel?: string;
} | null>(null);
const datasetPreviewUnavailable = ref<Record<string, boolean>>({});
const datasetsUiSection = ref<"data" | "regimens">("data");
const models = ref<ModelMeta[]>([]);
const modelsLoadError = ref("");
const modelsLoading = ref(false);
/** Model detail "Edit" from context panel: hand off to ModelsPage modal. */
const pendingModelsPageOpenEditId = ref<string | null>(null);
const modelDetailError = ref("");
const selectedModelId = ref<string | null>(null);
const selectedModel = ref<ModelMeta | null>(null);
const deletingTaskStatuses = ref<Record<string, "canceling" | "deleting">>({});
let pollingTimer: number | null = null;
let shellWatchdogTimer: number | null = null;
const taskSessionOwner = ref<Record<string, string>>({});
const sessionCurrentTask = ref<Record<string, string | null>>({ s1: null });
const sessionTaskAnnounce = ref<Record<string, Record<string, AnnounceState>>>({});

const selectedDataset = computed(() => datasets.value.find((d) => d.id === selectedDatasetId.value) || null);
const batchUploadFileByCardId = ref<Record<string, File>>({});

const predictionPanelSummary = computed(() => {
  if (isRecommendationSessionFocus(selectedTaskId.value)) {
    return null;
  }
  const msgs = sessionMessages.value[activeSessionId.value] || [];
  if (msgs.some((m) => m.recommendationWorkflowCard && m.recommendationWorkflowCard.status !== "cancelled")) {
    return null;
  }
  let editingCard: PredictionFormCardData | null = null;
  let lastResult: PredictionSingleResponse | null = null;
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    if (lastResult == null && m.predictionResult) lastResult = m.predictionResult;
    if (!editingCard && m.predictionFormCard?.status === "editing") editingCard = m.predictionFormCard;
  }
  if (!editingCard && !lastResult) return null;

  if (!editingCard) {
    return {
      active: false,
      predictRunning: false,
      modelId: lastResult?.model_id ?? null,
      displayName: lastResult?.display_name ?? null,
      taskName: lastResult?.task_name ?? null,
      fieldCount: 0,
      filledCount: 0,
      missingRequiredCount: 0,
      errorCount: 0,
      step: "idle" as const,
      canExecute: false,
      executeHint: null as string | null,
      lastResult,
    };
  }

  const predictRunning = editingCard.predictRunning;
  let fieldCount = 0;
  let filledCount = 0;
  let missingRequiredCount = 0;
  let errorCount = 0;
  let displayName: string | null = null;
  let taskName: string | null = lastResult?.task_name ?? null;
  if (editingCard.schema) {
    const r = analyzePredictionForm(editingCard.schema.fields, editingCard.formValues, t);
    fieldCount = editingCard.schema.fields.length;
    filledCount = r.filledCount;
    missingRequiredCount = r.missingRequiredCount;
    errorCount = r.errorCount;
    displayName = editingCard.schema.display_name;
    taskName = editingCard.schema.task_name;
  }
  const execHint = getPredictionFormExecuteBlockers(
    {
      selectedPredictionTaskKey: editingCard.selectedPredictionTaskKey ?? null,
      selectedModelId: editingCard.selectedModelId,
      schema: editingCard.schema,
      formValues: editingCard.formValues,
      schemaLoading: editingCard.schemaLoading,
    },
    t,
  );
  const canExecute = Boolean(
    !execHint && !predictRunning && editingCard.schema && !editingCard.schemaLoading,
  );

  const step = !editingCard.selectedPredictionTaskKey
    ? ("select_task" as const)
    : editingCard.schema
      ? ("fill_features" as const)
      : ("select_model" as const);

  return {
    active: true,
    predictRunning,
    modelId: editingCard.selectedModelId,
    displayName,
    taskName,
    fieldCount,
    filledCount,
    missingRequiredCount,
    errorCount,
    step,
    canExecute,
    executeHint: execHint,
    lastResult,
  };
});
const batchPredictionPanelSummary = computed(() => {
  if (isRecommendationSessionFocus(selectedTaskId.value)) {
    return null;
  }
  const msgs = sessionMessages.value[activeSessionId.value] || [];
  if (msgs.some((m) => m.recommendationWorkflowCard && m.recommendationWorkflowCard.status !== "cancelled")) {
    return null;
  }
  let editingCard: BatchPredictionCardData | null = null;
  let embeddedForm: PredictionFormCardData | null = null;
  let lastResult: BatchPredictionRunResponse | null = null;
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    if (!lastResult && m.batchPredictionResult) lastResult = m.batchPredictionResult;
    if (!editingCard && m.batchPredictionCard && (m.batchPredictionCard.status === "editing" || m.batchPredictionCard.status === "checked")) {
      editingCard = m.batchPredictionCard;
    }
    const pfc = m.predictionFormCard;
    if (!embeddedForm && pfc?.status === "editing" && pfc.batch) {
      embeddedForm = pfc;
    }
  }
  if (embeddedForm?.batch) {
    const b = embeddedForm.batch;
    const lr = b.result ?? lastResult;
    return {
      active: true,
      modelId: embeddedForm.selectedModelId ?? lr?.model_id ?? null,
      fileName: b.fileName || lr?.file_name || "",
      checkStatus: b.checkResult
        ? b.checkResult.can_run
          ? t("prediction.batchWorkspace.checkPassed")
          : t("prediction.batchWorkspace.checkFailed")
        : t("prediction.batchWorkspace.checkNotRun"),
      matchedCount: b.checkResult?.matched_fields.length ?? 0,
      missingCount: b.checkResult?.missing_fields.length ?? 0,
      extraCount: b.checkResult?.extra_fields.length ?? 0,
      lastResult: lr,
      runRunning: Boolean(b.runRunning),
    };
  }
  if (!editingCard && !lastResult) return null;
  return {
    active: Boolean(editingCard),
    modelId: editingCard?.selectedModelId ?? lastResult?.model_id ?? null,
    fileName: editingCard?.fileName || lastResult?.file_name || "",
    checkStatus: editingCard?.checkResult
      ? editingCard.checkResult.can_run
        ? t("prediction.batchWorkspace.checkPassed")
        : t("prediction.batchWorkspace.checkFailed")
      : t("prediction.batchWorkspace.checkNotRun"),
    matchedCount: editingCard?.checkResult?.matched_fields.length ?? 0,
    missingCount: editingCard?.checkResult?.missing_fields.length ?? 0,
    extraCount: editingCard?.checkResult?.extra_fields.length ?? 0,
    lastResult,
    runRunning: Boolean(editingCard?.runRunning),
  };
});

const recommendationPanelSummary = computed(() => {
  if (activeNav.value !== "workbench") return null;
  const sid = activeSessionId.value;
  const msgs = sessionMessages.value[sid] || [];
  const hasOpenRecCard = msgs.some(
    (m) => m.recommendationWorkflowCard && m.recommendationWorkflowCard.status !== "cancelled",
  );
  if (!hasOpenRecCard && !isRecommendationSessionFocus(selectedTaskId.value)) return null;

  let running = false;
  let last: SurvivalRecommendationResult | null = null;
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    const c = m.recommendationWorkflowCard;
    if (c && (c.status === "submitting" || c.status === "polling")) running = true;
    if (!last && m.recommendationResult) last = m.recommendationResult;
  }

  let lastSummary: { jobId: string; line1: string; line2: string | null } | null = null;
  if (last) {
    const top = last.recommended_top1_regimen;
    const name = (top?.regimen_name || "").trim() || t("common.na");
    const p = last.recommended_top1_probability;
    let line2: string | null = null;
    if (p !== undefined && p !== null && !Number.isNaN(Number(p))) {
      line2 = t("panels.context.recommendationSummary.topProbShort", {
        prob: `${(Number(p) * 100).toFixed(1)}%`,
      });
    }
    lastSummary = {
      jobId: String(last.job_id || "").trim(),
      line1: t("panels.context.recommendationSummary.topRankLine", { name }),
      line2,
    };
  }

  return { running, lastSummary };
});

const modelIdMissingInList = computed(
  () =>
    selectedModelId.value != null &&
    models.value.length > 0 &&
    !models.value.some((m) => m.model_id === selectedModelId.value),
);
const currentSessionMessages = computed(() => sessionMessages.value[activeSessionId.value] || []);

/** When chat history missed inserting the workflow card, reconstruct it from task detail (same source as the right panel). */
const recoveryTrainingWorkflowCard = computed((): TrainingWorkflowPendingActionData | null => {
  if (activeNav.value !== "workbench") return null;
  const jid = selectedTaskId.value;
  if (!jid) return null;
  const row = tasks.value.find((t) => String(t.id) === String(jid));
  if (!row || !isTrainingJobType(String(row.job_type || ""))) return null;
  if (String(row.status || "") !== "waiting_user") return null;
  const owner = taskSessionOwner.value[jid];
  if (!owner || owner !== activeSessionId.value) return null;
  const detail = taskDetailById.value[jid];
  if (!detail) return null;
  const card = buildTrainingWorkflowPendingCard(jid, detail);
  if (!card || card.status !== "pending") return null;
  const rowPhase = resolveTrainingWorkflowPhase(row as Record<string, unknown>);
  if (!rowPhase || card.phase !== rowPhase) return null;
  const msgs = sessionMessages.value[activeSessionId.value] || [];
  const exists = msgs.some(
    (m) =>
      m.workflowActionData?.job_id === jid &&
      m.workflowActionData?.card_id === card.card_id,
  );
  if (exists) return null;
  return card;
});

/**
 * Persisted UI flag per session (not chat content): keep the static Workbench welcome intro mounted after the first user turn from an empty landing.
 * Hidden when the recovery-workflow surface shows with no chat rows so the fallback card stays primary.
 */
const keepWorkbenchWelcomeIntro = computed(() => {
  const sid = activeSessionId.value;
  const msgs = sessionMessages.value[sid] || [];
  if (msgs.length === 0 && recoveryTrainingWorkflowCard.value) return false;
  const sessionRow = sessions.value.find((s) => s.id === sid);
  return msgs.length === 0 || Boolean(sessionRow?.workbenchWelcomeIntroPinned);
});

async function ensureTaskDetailForSelectedWaitingTask() {
  const jid = selectedTaskId.value;
  if (!jid || activeNav.value !== "workbench") return;
  const row = tasks.value.find((t) => String(t.id) === String(jid));
  if (!row || !isTrainingJobType(String(row.job_type || ""))) return;
  if (String(row.status || "") !== "waiting_user") return;
  if (taskDetailById.value[jid]) return;
  try {
    const d = await getTaskDetail(jid);
    taskDetailById.value = { ...taskDetailById.value, [jid]: d };
  } catch {
    /* ignore */
  }
}

async function onRequestCancelTrainingJob(payload: { job_id: string }) {
  const jobId = String(payload?.job_id || "").trim();
  if (!jobId) return;
  if (!window.confirm(t("app.confirm.cancelTask"))) return;
  try {
    await cancelTask(jobId);
    const nextCache = { ...taskDetailById.value };
    delete nextCache[jobId];
    taskDetailById.value = nextCache;
    uiError.value = "";
    await refreshTasks();
  } catch (e) {
    uiError.value = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
  }
}


function pushMsg(
  role: "user" | "assistant",
  text: string,
  actionData?: ChatTurnData | null,
  kind: "normal" | "status" | "error" = "normal",
  resultData?: TaskResultCardData | null,
  trainingReceiptData?: TrainingJobReceiptData | null,
) {
  pushMsgToSession(activeSessionId.value, role, text, actionData, null, kind, resultData, trainingReceiptData);
}

function pinWorkbenchWelcomeIntroWhenFirstWorkbenchUserTurn(sid: string, role: "user" | "assistant") {
  if (role !== "user") return;
  const priorLen = sessionMessages.value[sid]?.length ?? 0;
  if (priorLen > 0) return;
  const idx = sessions.value.findIndex((s) => s.id === sid);
  if (idx < 0) return;
  const row = sessions.value[idx];
  if (row.workbenchWelcomeIntroPinned) return;
  const next = [...sessions.value];
  next[idx] = { ...row, workbenchWelcomeIntroPinned: true };
  sessions.value = next;
}

function pushMsgToSession(
  sid: string,
  role: "user" | "assistant",
  text: string,
  actionData?: ChatTurnData | null,
  workflowActionData?: TrainingWorkflowPendingActionData | null,
  kind: "normal" | "status" | "error" = "normal",
  resultData?: TaskResultCardData | null,
  trainingReceiptData?: TrainingJobReceiptData | null,
  predictionResult?: PredictionSingleResponse | null,
  predictionFormCard?: PredictionFormCardData | null,
  batchPredictionCard?: BatchPredictionCardData | null,
  batchPredictionResult?: BatchPredictionRunResponse | null,
  recommendationWorkflowCard?: RecommendationWorkflowCardData | null,
  recommendationResult?: SurvivalRecommendationResult | null,
  predictionSubmittedSummary?: PredictionSubmittedSummaryPayload | null,
) {
  pinWorkbenchWelcomeIntroWhenFirstWorkbenchUserTurn(sid, role);
  if (!sessionMessages.value[sid]) sessionMessages.value[sid] = [];
  if (workflowActionData && role === "assistant") {
    const existingIdx = (sessionMessages.value[sid] || []).findIndex(
      (m) =>
        m.role === "assistant" &&
        m.workflowActionData?.job_id === workflowActionData.job_id &&
        m.workflowActionData?.card_id === workflowActionData.card_id,
    );
    if (existingIdx >= 0) {
      const nextMsgs = [...sessionMessages.value[sid]];
      const prev = nextMsgs[existingIdx];
      nextMsgs[existingIdx] = {
        ...prev,
        text: text || prev.text,
        kind,
        actionData: actionData ?? prev.actionData ?? null,
        workflowActionData: { ...(prev.workflowActionData || {}), ...workflowActionData } as TrainingWorkflowPendingActionData,
      };
      sessionMessages.value[sid] = nextMsgs;
      traceWorkflow("upsert_workflow_message", {
        active_session_id: activeSessionId.value,
        target_session_id: sid,
        job_id: workflowActionData.job_id,
        phase: workflowActionData.phase,
        card_id: workflowActionData.card_id,
      });
      return;
    }
  }
  sessionMessages.value[sid].push({
    id: `${Date.now()}_${Math.random()}`,
    role,
    text,
    actionData,
    workflowActionData,
    kind,
    resultData,
    trainingReceiptData,
    predictionResult: predictionResult ?? null,
    predictionFormCard: predictionFormCard ?? undefined,
    batchPredictionCard: batchPredictionCard ?? undefined,
    batchPredictionResult: batchPredictionResult ?? null,
    recommendationWorkflowCard: recommendationWorkflowCard ?? undefined,
    recommendationResult: recommendationResult ?? null,
    predictionSubmittedSummary: predictionSubmittedSummary ?? undefined,
  });
  if (workflowActionData) {
    const messageCountAfter = (sessionMessages.value[sid] || []).length;
    traceWorkflow("append_workflow_message", {
      active_session_id: activeSessionId.value,
      target_session_id: sid,
      job_id: workflowActionData.job_id,
      phase: workflowActionData.phase,
      card_id: workflowActionData.card_id,
      message_count_before: Math.max(0, messageCountAfter - 1),
      message_count_after: messageCountAfter,
    });
  }
}

function patchPredictionFormCard(sid: string, cardId: string, patch: Partial<PredictionFormCardData>) {
  const msgs = sessionMessages.value[sid];
  if (!msgs) return;
  const idx = msgs.findIndex((m) => m.predictionFormCard?.card_id === cardId);
  if (idx < 0) return;
  const prev = msgs[idx].predictionFormCard!;
  const next = { ...prev, ...patch } as PredictionFormCardData;
  const nextMsgs = [...msgs];
  nextMsgs[idx] = { ...nextMsgs[idx], predictionFormCard: next };
  sessionMessages.value[sid] = nextMsgs;
}

function createDefaultEmbeddedBatch(): NonNullable<PredictionFormCardData["batch"]> {
  return {
    status: "editing",
    fileName: "",
    checkRunning: false,
    runRunning: false,
    runStartedAt: null,
    checkResult: null,
  };
}

function getPredictionFormCard(sid: string, cardId: string): PredictionFormCardData | null {
  const msgs = sessionMessages.value[sid] || [];
  const row = msgs.find((m) => m.predictionFormCard?.card_id === cardId);
  return row?.predictionFormCard ?? null;
}

function findLastEditingCardId(sid: string): string | null {
  const msgs = sessionMessages.value[sid] || [];
  for (let i = msgs.length - 1; i >= 0; i--) {
    const c = msgs[i].predictionFormCard;
    if (c?.status === "editing") return c.card_id;
  }
  return null;
}

function patchBatchPredictionCard(sid: string, cardId: string, patch: Partial<BatchPredictionCardData>) {
  const msgs = sessionMessages.value[sid];
  if (!msgs) return;
  const idx = msgs.findIndex((m) => m.batchPredictionCard?.card_id === cardId);
  if (idx >= 0) {
    const prev = msgs[idx].batchPredictionCard!;
    const next = { ...prev, ...patch } as BatchPredictionCardData;
    const nextMsgs = [...msgs];
    nextMsgs[idx] = { ...nextMsgs[idx], batchPredictionCard: next };
    sessionMessages.value[sid] = nextMsgs;
    return;
  }
  const fidx = msgs.findIndex((m) => m.predictionFormCard?.card_id === cardId);
  if (fidx < 0) return;
  const prevForm = msgs[fidx].predictionFormCard!;
  const b0 = { ...createDefaultEmbeddedBatch(), ...prevForm.batch };
  const bNext: NonNullable<PredictionFormCardData["batch"]> = { ...b0 };
  if (patch.fileName !== undefined) bNext.fileName = patch.fileName;
  if (patch.checkRunning !== undefined) bNext.checkRunning = patch.checkRunning;
  if (patch.runRunning !== undefined) bNext.runRunning = patch.runRunning;
  if (patch.runStartedAt !== undefined) bNext.runStartedAt = patch.runStartedAt;
  if (patch.checkError !== undefined) bNext.checkError = patch.checkError;
  if (patch.runError !== undefined) bNext.runError = patch.runError;
  if (patch.checkResult !== undefined) bNext.checkResult = patch.checkResult;
  if (patch.submittedSummary !== undefined) bNext.submittedSummary = patch.submittedSummary;
  if (patch.result !== undefined) bNext.result = patch.result;
  if (patch.status !== undefined) bNext.status = patch.status as NonNullable<PredictionFormCardData["batch"]>["status"];
  if (patch.closedAt !== undefined) bNext.closedAt = patch.closedAt;
  patchPredictionFormCard(sid, cardId, { batch: bNext });
}

function findBatchPredictionCard(sid: string, cardId: string): BatchPredictionCardData | null {
  const msgs = sessionMessages.value[sid] || [];
  for (const m of msgs) {
    if (m.batchPredictionCard?.card_id === cardId) return m.batchPredictionCard;
  }
  return null;
}

function formatPreviewFieldVal(v: unknown): string {
  if (typeof v === "boolean") return v ? t("predictionPresentation.boolean.yes") : t("predictionPresentation.boolean.no");
  return String(v);
}

function buildSubmittedSummaryFromCard(card: PredictionFormCardData): PredictionFormSubmittedSummary {
  const schema = card.schema!;
  const r = analyzePredictionForm(schema.fields, card.formValues, t);
  let displayName = schema.display_name || "";
  if (!displayName && card.selectedModelId) {
    const meta = card.models.find((m) => m.model_id === card.selectedModelId);
    if (meta) displayName = meta.display_name;
  }
  const previewFields: PredictionFormSubmittedSummary["previewFields"] = [];
  for (const f of schema.fields) {
    if (previewFields.length >= 8) break;
    const v = card.formValues[f.name];
    if (v === null || v === undefined || v === "") continue;
    previewFields.push({
      name: f.name,
      label: f.label || f.name,
      value: formatPreviewFieldVal(v),
    });
  }
  return {
    displayName: displayName || card.selectedModelId || "",
    modelId: card.selectedModelId!,
    fieldCount: schema.fields.length,
    filledCount: r.filledCount,
    previewFields,
    mode: "single",
    taskName: schema.task_name,
  };
}

function patchPredictionSubmittedSummaryMessage(sid: string, summaryId: string, patch: Partial<PredictionSubmittedSummaryPayload>) {
  const msgs = sessionMessages.value[sid];
  if (!msgs) return;
  const idx = msgs.findIndex((m) => m.predictionSubmittedSummary?.summary_id === summaryId);
  if (idx < 0) return;
  const prev = msgs[idx].predictionSubmittedSummary!;
  const next = { ...prev, ...patch } as PredictionSubmittedSummaryPayload;
  const nextMsgs = [...msgs];
  nextMsgs[idx] = { ...nextMsgs[idx], predictionSubmittedSummary: next };
  sessionMessages.value[sid] = nextMsgs;
}

function reconcilePredictionFormCardModelSelection(
  sid: string,
  cardId: string,
  opts?: { preferredModelId?: string | null; triggerUserText?: string | null },
) {
  const card = getPredictionFormCard(sid, cardId);
  if (!card) return;
  const items = card.models;
  const pref = opts?.preferredModelId?.trim() || null;
  const text = String(opts?.triggerUserText || "");

  let taskKey: PredictionTaskKey | null = card.selectedPredictionTaskKey ?? null;

  if (pref) {
    const m = items.find((x) => x.model_id === pref);
    if (m) {
      const tk = inferPredictionTaskKeyFromModel(m);
      if (tk) taskKey = tk;
    }
  } else if (taskKey == null) {
    taskKey = inferPreferredPredictionTaskFromUserText(text, String(locale.value || ""));
  }

  patchPredictionFormCard(sid, cardId, { selectedPredictionTaskKey: taskKey });

  const list = predictionModelsForTask(items, taskKey);
  let pick: string | null = null;
  if (pref && list.some((m) => m.model_id === pref)) pick = pref;
  else if (list.length === 1) pick = list[0].model_id;

  if (pick) onPredictionFormSelectModel(sid, cardId, pick);
  else onPredictionFormSelectModel(sid, cardId, null);
}

function predictionWorkspaceAssistantOpeningLine(taskKey: PredictionTaskKey | null): string {
  if (taskKey) return t(`prediction.narrative.intentRecognized.${taskKey}`);
  return t("prediction.narrative.workspaceOpenedAssistant");
}

async function onPredictionFormSelectTask(sid: string, cardId: string, taskKey: PredictionTaskKey | null) {
  const card = getPredictionFormCard(sid, cardId);
  if (!card) return;
  patchPredictionFormCard(sid, cardId, { selectedPredictionTaskKey: taskKey });
  if (taskKey == null) {
    onPredictionFormSelectModel(sid, cardId, null);
    return;
  }
  patchPredictionFormCard(sid, cardId, { modelsLoading: true, modelsError: "" });
  try {
    const data = await getAvailablePredictionModels(canonicalApiTaskFromUiKey(taskKey));
    patchPredictionFormCard(sid, cardId, {
      models: data.items,
      modelsLoading: false,
      modelsError: "",
    });
  } catch (e) {
    patchPredictionFormCard(sid, cardId, {
      modelsLoading: false,
      modelsError: formatPredictionApiError(e, t),
    });
  }
  const next = getPredictionFormCard(sid, cardId);
  if (!next) return;
  const list = predictionModelsForTask(next.models, taskKey);
  const cur = next.selectedModelId;
  if (cur && list.some((m) => m.model_id === cur)) return;
  if (list.length === 1) onPredictionFormSelectModel(sid, cardId, list[0].model_id);
  else onPredictionFormSelectModel(sid, cardId, null);
}

async function insertPredictionFormCard(
  sid: string,
  opts?: { openBatch?: boolean; preferredModelId?: string; triggerUserText?: string },
) {
  const triggerUserText = String(opts?.triggerUserText || "");
  const trimmedTrigger = triggerUserText.trim();
  const openBatch =
    trimmedTrigger.length > 0
      ? inferPredictionPanelModeFromUserText(triggerUserText) === "batch"
      : Boolean(opts?.openBatch);
  const prefId = opts?.preferredModelId?.trim() || null;
  const cardId = `pfc_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const recId = prefId || selectedModelId.value?.trim() || null;
  const recLabel = (selectedModel.value?.task_name || recId || "").trim() || null;
  const inferredTask = inferPreferredPredictionTaskFromUserText(triggerUserText, String(locale.value || ""));
  const initial: PredictionFormCardData = {
    kind: "prediction_form_card",
    card_id: cardId,
    status: "editing",
    models: [],
    modelsLoading: true,
    modelsError: "",
    selectedPredictionTaskKey: inferredTask,
    selectedModelId: null,
    schema: null,
    schemaLoading: false,
    schemaError: "",
    formValues: {},
    predictRunning: false,
    active_panel: openBatch ? "batch" : "form",
    batch: createDefaultEmbeddedBatch(),
    recommendedModelId: recId,
    recommendedModelLabel: recLabel,
  };
  pushMsgToSession(
    sid,
    "assistant",
    predictionWorkspaceAssistantOpeningLine(inferredTask),
    null,
    null,
    "normal",
    null,
    null,
    null,
    initial,
  );
  try {
    const data = await getAvailablePredictionModels();
    patchPredictionFormCard(sid, cardId, { models: data.items, modelsLoading: false, modelsError: "" });
    reconcilePredictionFormCardModelSelection(sid, cardId, {
      preferredModelId: opts?.preferredModelId ?? null,
      triggerUserText,
    });
  } catch (e) {
    patchPredictionFormCard(sid, cardId, {
      models: [],
      modelsLoading: false,
      modelsError: formatPredictionApiError(e, t),
    });
  }
}

function onWorkbenchStartPrediction(payload?: { modelId?: string }) {
  pushMsg("user", t("chat.syntheticUser.openPredictionWorkspace"));
  const pref = payload?.modelId?.trim();
  void insertPredictionFormCard(activeSessionId.value, pref ? { preferredModelId: pref } : undefined);
}

function onWorkbenchStartRecommendation() {
  void openRecommendationWorkspaceLikeQuickEntry(
    activeSessionId.value,
    t("chat.syntheticUser.openRecommendationWorkspace"),
  );
}

function emptyObservedTreatmentValues(): RegimenTreatmentValues {
  const o = {} as RegimenTreatmentValues;
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    o[k] = 0;
  }
  return o;
}

async function loadRecommendationFromTaskDetail(detail: TaskDetailData): Promise<SurvivalRecommendationResult | null> {
  const url = detail.artifacts?.["recommendation.json"];
  if (!url || typeof url !== "string") return null;
  const rec = await fetchRecommendationArtifactJson(url);
  if (!rec) return null;
  const jid = String(detail.task?.id || "").trim();
  return jid ? { ...rec, job_id: jid } : rec;
}

/** When this job id is an active/completed recommendation run, do not let stale prediction chat cards drive the workspace panel. */
function isRecommendationSessionFocus(jobId: string | null | undefined): boolean {
  const jid = String(jobId || "").trim();
  if (!jid) return false;
  const row = tasks.value.find((t) => String(t.id) === jid);
  if (row && String(row.job_type || "") === "recommend_regimen") return true;
  const msgs = sessionMessages.value[activeSessionId.value] || [];
  for (let i = msgs.length - 1; i >= 0; i--) {
    const c = msgs[i].recommendationWorkflowCard;
    if (!c?.jobId || String(c.jobId) !== jid) continue;
    const st = c.status;
    if (st === "submitting" || st === "polling" || st === "completed" || st === "failed") return true;
  }
  return false;
}

function patchRecommendationWorkflowCard(sid: string, cardId: string, patch: Partial<RecommendationWorkflowCardData>) {
  const msgs = sessionMessages.value[sid];
  if (!msgs) return;
  const idx = msgs.findIndex((m) => m.recommendationWorkflowCard?.card_id === cardId);
  if (idx < 0) return;
  const prev = msgs[idx].recommendationWorkflowCard!;
  const next = { ...prev, ...patch } as RecommendationWorkflowCardData;
  const nextMsgs = [...msgs];
  nextMsgs[idx] = { ...nextMsgs[idx], recommendationWorkflowCard: next };
  sessionMessages.value[sid] = nextMsgs;
}

function getRecommendationWorkflowCard(sid: string, cardId: string): RecommendationWorkflowCardData | null {
  const msgs = sessionMessages.value[sid] || [];
  const row = msgs.find((m) => m.recommendationWorkflowCard?.card_id === cardId);
  return row?.recommendationWorkflowCard ?? null;
}

function patchRecommendationWorkflowCardByJobId(sid: string, jobId: string, patch: Partial<RecommendationWorkflowCardData>) {
  const msgs = sessionMessages.value[sid];
  if (!msgs) return;
  const idx = msgs.findIndex((m) => m.recommendationWorkflowCard?.jobId === jobId);
  if (idx < 0) return;
  const prev = msgs[idx].recommendationWorkflowCard!;
  const next = { ...prev, ...patch } as RecommendationWorkflowCardData;
  const nextMsgs = [...msgs];
  nextMsgs[idx] = { ...nextMsgs[idx], recommendationWorkflowCard: next };
  sessionMessages.value[sid] = nextMsgs;
}

async function insertRecommendationWorkflowCard(sid: string) {
  const cardId = `rwc_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const recId = selectedModelId.value?.trim() || null;
  const recLabel = (selectedModel.value?.task_name || recId || "").trim() || null;
  const initial: RecommendationWorkflowCardData = {
    kind: "recommendation_workflow_card",
    card_id: cardId,
    status: "editing",
    models: [],
    modelsLoading: true,
    modelsError: "",
    selectedModelId: null,
    schema: null,
    schemaLoading: false,
    schemaError: "",
    formValues: {},
    observedTreatmentValues: emptyObservedTreatmentValues(),
    observedCompareExpanded: false,
    predictRunning: false,
    enabledRegimenCount: 0,
    regimensLoading: true,
    regimensError: "",
    recommendedModelId: recId,
    recommendedModelLabel: recLabel,
  };
  pushMsgToSession(
    sid,
    "assistant",
    t("recommendation.narrative.workspaceEnteredAssistant"),
    null,
    null,
    "normal",
    null,
    null,
    null,
    null,
    null,
    null,
    initial,
    null,
  );
  try {
    const [modelsData, regimensData] = await Promise.all([getAvailablePredictionModels(), listRegimens()]);
    const survival = modelsData.items.filter(isSurvivalRecommendationCandidate);
    const enabledCount = regimensData.items.filter((r) => r.enabled).length;
    patchRecommendationWorkflowCard(sid, cardId, {
      models: survival,
      modelsLoading: false,
      modelsError: survival.length === 0 ? t("recommendation.narrative.noSurvivalModelsError") : "",
      enabledRegimenCount: enabledCount,
      regimensLoading: false,
      regimensError: "",
    });
  } catch (e) {
    patchRecommendationWorkflowCard(sid, cardId, {
      modelsLoading: false,
      modelsError: formatPredictionApiError(e, t),
      regimensLoading: false,
      regimensError: formatPredictionApiError(e, t),
    });
  }
}

/** Same card insertion as quick entry; `userLine` is either the i18n synthetic bubble or the user-typed open command. */
async function openRecommendationWorkspaceLikeQuickEntry(sid: string, userLine: string) {
  pushMsg("user", userLine);
  await insertRecommendationWorkflowCard(sid);
}

async function submitRecommendationWorkflow(sid: string, cardId: string) {
  const card = getRecommendationWorkflowCard(sid, cardId);
  if (!card || card.status !== "editing") return;
  const block = getRecommendationWorkflowBlockers(card, t);
  if (block) {
    patchRecommendationWorkflowCard(sid, cardId, { submitError: block });
    return;
  }
  patchRecommendationWorkflowCard(sid, cardId, { submitError: undefined, predictRunning: true, status: "submitting" });
  try {
    const patient_features = buildPatientFeaturesPayload(card.schema!, card.formValues);
    const payload: RecommendationJobCreatePayload = {
      model_id: card.selectedModelId!,
      patient_features,
      mode: "survival_only",
      top_k: Math.max(1, card.enabledRegimenCount),
      locale: apiUiLocale(),
    };
    if (card.observedCompareExpanded) {
      payload.observed_regimen = { ...card.observedTreatmentValues };
    }
    const res = await postRecommendationJob(payload);
    const jobId = res.job_id;
    taskSessionOwner.value[jobId] = sid;
    sessionCurrentTask.value[sid] = jobId;
    selectedTaskId.value = jobId;
    if (!sessionTaskAnnounce.value[sid]) sessionTaskAnnounce.value[sid] = {};
    sessionTaskAnnounce.value[sid][jobId] = {};
    patchRecommendationWorkflowCard(sid, cardId, {
      status: "polling",
      predictRunning: false,
      jobId,
      submitError: undefined,
    });
    await refreshTasks();
    startPollingIfNeeded();
  } catch (e) {
    const msg = formatPredictionApiError(e, t);
    patchRecommendationWorkflowCard(sid, cardId, {
      predictRunning: false,
      status: "editing",
      submitError: msg,
    });
  }
}

function onRecommendationWorkflowSelectModel(sid: string, cardId: string, modelId: string | null) {
  patchRecommendationWorkflowCard(sid, cardId, {
    selectedModelId: modelId,
    schema: null,
    schemaError: "",
    formValues: {},
    submitError: undefined,
    observedCompareExpanded: false,
    observedTreatmentValues: emptyObservedTreatmentValues(),
  });
  if (modelId) void onRecommendationWorkflowLoadSchema(sid, cardId);
}

async function onRecommendationWorkflowLoadSchema(sid: string, cardId: string) {
  const msgs = sessionMessages.value[sid];
  const mid = msgs?.find((m) => m.recommendationWorkflowCard?.card_id === cardId)?.recommendationWorkflowCard
    ?.selectedModelId;
  if (!mid) return;
  patchRecommendationWorkflowCard(sid, cardId, { schemaLoading: true, schemaError: "" });
  try {
    const schema = await getPredictionModelSchema(mid);
    patchRecommendationWorkflowCard(sid, cardId, {
      schema,
      formValues: buildInitialFormValues(schema.fields),
      schemaLoading: false,
      submitError: undefined,
      observedCompareExpanded: false,
      observedTreatmentValues: emptyObservedTreatmentValues(),
    });
  } catch (e) {
    patchRecommendationWorkflowCard(sid, cardId, {
      schemaLoading: false,
      schemaError: formatPredictionApiError(e, t),
    });
  }
}

function onRecommendationWorkflowUpdateValue(sid: string, cardId: string, name: string, value: unknown) {
  const msgs = sessionMessages.value[sid];
  const card = msgs?.find((m) => m.recommendationWorkflowCard?.card_id === cardId)?.recommendationWorkflowCard;
  if (!card?.schema) return;
  const f = card.schema.fields.find((x) => x.name === name);
  let v: unknown = value;
  if (f?.type === "int" && typeof v === "string") {
    const t = v.trim();
    v = t === "" ? "" : Number.parseInt(t, 10);
  } else if (f?.type === "float" && typeof v === "string") {
    const t = v.trim();
    v = t === "" ? "" : Number(t);
  }
  patchRecommendationWorkflowCard(sid, cardId, { formValues: { ...card.formValues, [name]: v }, submitError: undefined });
}

function onRecommendationWorkflowAction(action: RecommendationWorkflowChatAction) {
  const sid = activeSessionId.value;
  switch (action.action) {
    case "openRegimenManagement":
      sessionStorage.setItem("workbench_open_regimens", "1");
      activeNav.value = "datasets";
      break;
    case "selectModel":
      onRecommendationWorkflowSelectModel(sid, action.cardId, action.modelId);
      break;
    case "loadSchema":
      void onRecommendationWorkflowLoadSchema(sid, action.cardId);
      break;
    case "updateValue":
      onRecommendationWorkflowUpdateValue(sid, action.cardId, action.name, action.value);
      break;
    case "updateObservedTreatment": {
      const card = getRecommendationWorkflowCard(sid, action.cardId);
      if (!card) return;
      const next = { ...card.observedTreatmentValues, [action.key]: action.value };
      patchRecommendationWorkflowCard(sid, action.cardId, { observedTreatmentValues: next });
      break;
    }
    case "setObservedCompareExpanded":
      patchRecommendationWorkflowCard(sid, action.cardId, { observedCompareExpanded: action.expanded });
      break;
    case "submit":
      void submitRecommendationWorkflow(sid, action.cardId);
      break;
    case "cancel":
      patchRecommendationWorkflowCard(sid, action.cardId, {
        status: "cancelled",
        closedAt: new Date().toISOString(),
        predictRunning: false,
      });
      break;
    default:
      break;
  }
}

/** Same as single-card batch upload tab; name kept for legacy call sites. */
async function insertBatchPredictionCard(sid: string, triggerUserText?: string) {
  await insertPredictionFormCard(sid, { openBatch: true, triggerUserText: triggerUserText?.trim() || "" });
}

function cancelAllEditingPredictionCards(sid: string) {
  const msgs = sessionMessages.value[sid] || [];
  for (const m of msgs) {
    const c = m.predictionFormCard;
    if (c?.status === "editing") {
      delete batchUploadFileByCardId.value[c.card_id];
      patchPredictionFormCard(sid, c.card_id, {
        status: "cancelled",
        closedAt: new Date().toISOString(),
        predictRunning: false,
        batch: createDefaultEmbeddedBatch(),
      });
    }
  }
}

function buildBatchSubmittedSummary(card: BatchPredictionCardData): BatchPredictionCardData["submittedSummary"] {
  const modelName = card.models.find((m) => m.model_id === card.selectedModelId)?.display_name || card.selectedModelId || "";
  return {
    modelId: card.selectedModelId || "",
    modelName,
    fileName: card.fileName,
    canRun: Boolean(card.checkResult?.can_run),
    matchedCount: card.checkResult?.matched_fields.length || 0,
    missingCount: card.checkResult?.missing_fields.length || 0,
    extraCount: card.checkResult?.extra_fields.length || 0,
  };
}

function validateBatchInput(card: BatchPredictionCardData): string | null {
  if (!card.selectedModelId) return t("prediction.workspace.selectModelFirst");
  const file = batchUploadFileByCardId.value[card.card_id];
  if (!file) return t("prediction.workspace.uploadPatientTable");
  return null;
}

function buildEmbeddedBatchSubmittedSummary(
  card: PredictionFormCardData,
  checkResult: BatchFieldCheckResponse,
): NonNullable<PredictionFormCardData["batch"]>["submittedSummary"] {
  const modelName =
    card.models.find((m) => m.model_id === card.selectedModelId)?.display_name || card.selectedModelId || "";
  return {
    modelId: card.selectedModelId || "",
    modelName,
    fileName: card.batch?.fileName || "",
    canRun: Boolean(checkResult.can_run),
    matchedCount: checkResult.matched_fields.length,
    missingCount: checkResult.missing_fields.length,
    extraCount: checkResult.extra_fields.length,
  };
}

function validateEmbeddedBatchInput(card: PredictionFormCardData, cardId: string): string | null {
  if (!card.selectedPredictionTaskKey) return t("prediction.workspace.selectTaskFirst");
  if (!card.selectedModelId) return t("prediction.workspace.selectModelFirst");
  const file = batchUploadFileByCardId.value[cardId];
  if (!file) return t("prediction.workspace.uploadPatientTable");
  return null;
}

async function checkEmbeddedBatchPrediction(sid: string, cardId: string) {
  const card = getPredictionFormCard(sid, cardId);
  if (!card || card.status === "cancelled") return;
  const batchPrev = { ...createDefaultEmbeddedBatch(), ...card.batch };
  const err = validateEmbeddedBatchInput(card, cardId);
  if (err) {
    patchPredictionFormCard(sid, cardId, { batch: { ...batchPrev, checkError: err } });
    return;
  }
  patchPredictionFormCard(sid, cardId, {
    batch: { ...batchPrev, checkRunning: true, checkError: undefined, runError: undefined },
  });
  try {
    const file = batchUploadFileByCardId.value[cardId];
    const out = await postPredictionBatchCheck({
      model_id: card.selectedModelId!,
      file,
      locale: apiUiLocale(),
    });
    const fresh = getPredictionFormCard(sid, cardId)!;
    const b = { ...createDefaultEmbeddedBatch(), ...fresh.batch };
    patchPredictionFormCard(sid, cardId, {
      batch: {
        ...b,
        status: "checked",
        checkRunning: false,
        checkResult: out as BatchFieldCheckResponse,
        submittedSummary: buildEmbeddedBatchSubmittedSummary(fresh, out as BatchFieldCheckResponse),
      },
    });
  } catch (e) {
    const fresh = getPredictionFormCard(sid, cardId);
    const b = { ...createDefaultEmbeddedBatch(), ...fresh?.batch };
    patchPredictionFormCard(sid, cardId, {
      batch: {
        ...b,
        checkRunning: false,
        checkError: formatPredictionApiError(e, t),
      },
    });
  }
}

async function runEmbeddedBatchPrediction(sid: string, cardId: string) {
  const card = getPredictionFormCard(sid, cardId);
  if (!card || card.status === "cancelled") return;
  const batchPrev = { ...createDefaultEmbeddedBatch(), ...card.batch };
  const err = validateEmbeddedBatchInput(card, cardId);
  if (err) {
    patchPredictionFormCard(sid, cardId, { batch: { ...batchPrev, runError: err, runStartedAt: null } });
    return;
  }
  if (!batchPrev.checkResult) {
    patchPredictionFormCard(sid, cardId, {
      batch: { ...batchPrev, runError: t("prediction.batchWorkspace.runNeedCheckColumns"), runStartedAt: null },
    });
    return;
  }
  if (!batchPrev.checkResult.can_run) {
    patchPredictionFormCard(sid, cardId, {
      batch: {
        ...batchPrev,
        runError: t("prediction.batchWorkspace.runMissingRequiredColumns"),
        runStartedAt: null,
      },
    });
    return;
  }
  patchPredictionFormCard(sid, cardId, {
    batch: { ...batchPrev, runRunning: true, runError: undefined, runStartedAt: new Date().toISOString() },
  });
  try {
    const file = batchUploadFileByCardId.value[cardId];
    const out = await postPredictionBatchRun({
      model_id: card.selectedModelId!,
      file,
      session_id: sid,
      locale: apiUiLocale(),
    });
    const fresh = getPredictionFormCard(sid, cardId)!;
    const b = { ...createDefaultEmbeddedBatch(), ...fresh.batch };
    patchPredictionFormCard(sid, cardId, {
      batch: {
        ...b,
        status: "finished",
        runRunning: false,
        runStartedAt: null,
        result: out,
        submittedSummary:
          fresh.batch?.checkResult != null
            ? buildEmbeddedBatchSubmittedSummary(fresh, fresh.batch.checkResult)
            : b.submittedSummary,
      },
    });
    pushMsgToSession(sid, "assistant", t("prediction.narrative.batchCompletedAssistant"), null, null, "normal", null, null, null, null, null, out);
  } catch (e) {
    const fresh = getPredictionFormCard(sid, cardId);
    const b = { ...createDefaultEmbeddedBatch(), ...fresh?.batch };
    patchPredictionFormCard(sid, cardId, {
      batch: {
        ...b,
        runRunning: false,
        runStartedAt: null,
        runError: formatPredictionApiError(e, t),
      },
    });
  }
}

async function checkBatchPredictionCard(sid: string, cardId: string) {
  const form = getPredictionFormCard(sid, cardId);
  if (form?.batch) {
    await checkEmbeddedBatchPrediction(sid, cardId);
    return;
  }
  const card = findBatchPredictionCard(sid, cardId);
  if (!card || card.status === "cancelled") return;
  const err = validateBatchInput(card);
  if (err) {
    patchBatchPredictionCard(sid, cardId, { checkError: err });
    return;
  }
  const file = batchUploadFileByCardId.value[card.card_id];
  patchBatchPredictionCard(sid, cardId, { checkRunning: true, checkError: undefined, runError: undefined });
  try {
    const out = await postPredictionBatchCheck({
      model_id: card.selectedModelId!,
      file,
      locale: apiUiLocale(),
    });
    patchBatchPredictionCard(sid, cardId, {
      status: "checked",
      checkRunning: false,
      checkResult: out as BatchFieldCheckResponse,
      submittedSummary: buildBatchSubmittedSummary({ ...card, checkResult: out }),
    });
  } catch (e) {
    patchBatchPredictionCard(sid, cardId, {
      checkRunning: false,
      checkError: formatPredictionApiError(e, t),
    });
  }
}

async function runBatchPredictionCard(sid: string, cardId: string) {
  const form = getPredictionFormCard(sid, cardId);
  if (form?.batch) {
    await runEmbeddedBatchPrediction(sid, cardId);
    return;
  }
  const card = findBatchPredictionCard(sid, cardId);
  if (!card || card.status === "cancelled") return;
  const err = validateBatchInput(card);
  if (err) {
    patchBatchPredictionCard(sid, cardId, { runError: err, runStartedAt: null });
    return;
  }
  if (!card.checkResult) {
    patchBatchPredictionCard(sid, cardId, {
      runError: t("prediction.batchWorkspace.runNeedCheckColumns"),
      runStartedAt: null,
    });
    return;
  }
  if (!card.checkResult.can_run) {
    patchBatchPredictionCard(sid, cardId, {
      runError: t("prediction.batchWorkspace.runMissingRequiredColumns"),
      runStartedAt: null,
    });
    return;
  }
  const file = batchUploadFileByCardId.value[card.card_id];
  patchBatchPredictionCard(sid, cardId, { runRunning: true, runError: undefined });
  try {
    const out = await postPredictionBatchRun({
      model_id: card.selectedModelId!,
      file,
      session_id: sid,
      locale: apiUiLocale(),
    });
    const merged = { ...card, checkResult: card.checkResult };
    patchBatchPredictionCard(sid, cardId, {
      status: "finished",
      runRunning: false,
      runStartedAt: null,
      result: out,
      submittedSummary: buildBatchSubmittedSummary(merged),
    });
    pushMsgToSession(sid, "assistant", t("prediction.narrative.batchCompletedAssistant"), null, null, "normal", null, null, null, null, null, out);
  } catch (e) {
    patchBatchPredictionCard(sid, cardId, {
      runRunning: false,
      runStartedAt: null,
      runError: formatPredictionApiError(e, t),
    });
  }
}

async function submitPredictionCard(sid: string, cardId: string) {
  const msgs = sessionMessages.value[sid];
  if (!msgs) return;
  const row = msgs.find((m) => m.predictionFormCard?.card_id === cardId);
  const card = row?.predictionFormCard;
  if (!card || card.status !== "editing") return;

  const block = getPredictionFormExecuteBlockers(
    {
      selectedPredictionTaskKey: card.selectedPredictionTaskKey ?? null,
      selectedModelId: card.selectedModelId,
      schema: card.schema,
      formValues: card.formValues,
      schemaLoading: card.schemaLoading,
    },
    t,
  );
  if (block) {
    patchPredictionFormCard(sid, cardId, { submitError: block });
    return;
  }

  const schema = card.schema!;
  const merged = { ...card, schema } as PredictionFormCardData;
  const summaryId = `pss_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const fieldRows = buildPredictionSubmitSummaryRows(schema.fields, card.formValues);
  const ds = selectedDataset.value;
  const workspaceContext =
    ds && (ds.name || ds.file_name)
      ? t("prediction.workspace.datasetContextPrefix", { name: String(ds.name || ds.file_name) })
      : null;
  const submitPayload: PredictionSubmittedSummaryPayload = {
    summary_id: summaryId,
    status: "pending",
    model_display_name: schema.display_name || card.models.find((m) => m.model_id === card.selectedModelId)?.display_name || "",
    model_id: card.selectedModelId!,
    task_name: schema.task_name || t("common.na"),
    mode: "single",
    submitted_at: new Date().toISOString(),
    workspace_context: workspaceContext,
    field_rows: fieldRows,
  };

  pushMsgToSession(
    sid,
    "assistant",
    "",
    null,
    null,
    "normal",
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    submitPayload,
  );

  patchPredictionFormCard(sid, cardId, { submitError: undefined, predictRunning: true });

  try {
    const data = await postPredictionSingle({
      model_id: card.selectedModelId!,
      values: { ...card.formValues },
      session_id: sid,
      locale: apiUiLocale(),
    });
    const summary = buildSubmittedSummaryFromCard(merged);
    patchPredictionSubmittedSummaryMessage(sid, summaryId, { status: "done" });
    patchPredictionFormCard(sid, cardId, {
      status: "submitted",
      predictRunning: false,
      submittedSummary: summary,
      result: data,
      submitError: undefined,
    });
    pushMsgToSession(sid, "assistant", "", null, null, "normal", null, null, { ...data, feature_schema_fields: schema.fields }, null, null, null, null, null, null);
  } catch (e) {
    const msg = formatPredictionApiError(e, t);
    patchPredictionSubmittedSummaryMessage(sid, summaryId, { status: "failed", error_message: msg });
    patchPredictionFormCard(sid, cardId, { predictRunning: false, submitError: msg });
    pushMsgToSession(sid, "assistant", t("prediction.narrative.singlePredictionFailed", { message: msg }), null, null, "error", null, null, null, null, null, null, null, null, null);
  }
}

function onPredictionFormSelectModel(sid: string, cardId: string, modelId: string | null) {
  const prev = getPredictionFormCard(sid, cardId);
  const prevModel = prev?.selectedModelId ?? null;
  if (
    modelId &&
    modelId === prevModel &&
    prev?.schema &&
    String(prev.schema.model_id || "") === String(modelId)
  ) {
    return;
  }
  const b = prev?.batch
    ? {
        ...prev.batch,
        checkResult: null,
        checkError: undefined,
        runError: undefined,
        status: "editing" as const,
      }
    : createDefaultEmbeddedBatch();
  patchPredictionFormCard(sid, cardId, {
    selectedModelId: modelId,
    schema: null,
    schemaError: "",
    formValues: {},
    submitError: undefined,
    batch: b,
  });
  if (modelId) {
    void onPredictionFormLoadSchema(sid, cardId);
  }
}

async function onPredictionFormLoadSchema(sid: string, cardId: string) {
  const msgs = sessionMessages.value[sid];
  const mid = msgs?.find((m) => m.predictionFormCard?.card_id === cardId)?.predictionFormCard?.selectedModelId;
  if (!mid) return;
  patchPredictionFormCard(sid, cardId, { schemaLoading: true, schemaError: "" });
  try {
    const schema = await getPredictionModelSchema(mid);
    patchPredictionFormCard(sid, cardId, {
      schema,
      formValues: buildInitialFormValues(schema.fields),
      schemaLoading: false,
      submitError: undefined,
    });
  } catch (e) {
    patchPredictionFormCard(sid, cardId, {
      schemaLoading: false,
      schemaError: formatPredictionApiError(e, t),
    });
  }
}

function onPredictionFormUpdateValue(sid: string, cardId: string, name: string, value: unknown) {
  const msgs = sessionMessages.value[sid];
  const card = msgs?.find((m) => m.predictionFormCard?.card_id === cardId)?.predictionFormCard;
  if (!card?.schema) return;
  const f = card.schema.fields.find((x) => x.name === name);
  let v: unknown = value;
  if (f?.type === "int" && typeof v === "string") {
    const t = v.trim();
    v = t === "" ? "" : Number.parseInt(t, 10);
  } else if (f?.type === "float" && typeof v === "string") {
    const t = v.trim();
    v = t === "" ? "" : Number(t);
  }
  patchPredictionFormCard(sid, cardId, { formValues: { ...card.formValues, [name]: v }, submitError: undefined });
}

function onPredictionFormAction(action: PredictionFormChatAction) {
  const sid = activeSessionId.value;
  switch (action.action) {
    case "selectPredictionTask":
      void onPredictionFormSelectTask(sid, action.cardId, action.taskKey);
      break;
    case "selectModel":
      onPredictionFormSelectModel(sid, action.cardId, action.modelId);
      break;
    case "loadSchema":
      void onPredictionFormLoadSchema(sid, action.cardId);
      break;
    case "updateValue":
      onPredictionFormUpdateValue(sid, action.cardId, action.name, action.value);
      break;
    case "submit":
      void submitPredictionCard(sid, action.cardId);
      break;
    case "cancel":
      delete batchUploadFileByCardId.value[action.cardId];
      patchPredictionFormCard(sid, action.cardId, {
        status: "cancelled",
        closedAt: new Date().toISOString(),
        predictRunning: false,
        selectedPredictionTaskKey: null,
        batch: createDefaultEmbeddedBatch(),
      });
      break;
    case "setActivePanel":
      patchPredictionFormCard(sid, action.cardId, { active_panel: action.panel });
      break;
    case "batchSelectModel":
      onPredictionFormSelectModel(sid, action.cardId, action.modelId);
      break;
    case "batchSetFile": {
      const cid = action.cardId;
      if (action.file) batchUploadFileByCardId.value[cid] = action.file;
      else delete batchUploadFileByCardId.value[cid];
      const cur = getPredictionFormCard(sid, cid);
      const b = {
        ...createDefaultEmbeddedBatch(),
        ...cur?.batch,
        fileName: action.file?.name || "",
        checkResult: null,
        checkError: undefined,
        runError: undefined,
        status: "editing" as const,
      };
      patchPredictionFormCard(sid, cid, { batch: b });
      break;
    }
    case "batchCheck":
      void checkEmbeddedBatchPrediction(sid, action.cardId);
      break;
    case "batchRun":
      void runEmbeddedBatchPrediction(sid, action.cardId);
      break;
    case "batchCancel":
      delete batchUploadFileByCardId.value[action.cardId];
      patchPredictionFormCard(sid, action.cardId, {
        active_panel: "form",
        batch: createDefaultEmbeddedBatch(),
      });
      break;
    default:
      break;
  }
}

function onBatchPredictionAction(action: BatchPredictionChatAction) {
  const sid = activeSessionId.value;
  switch (action.action) {
    case "selectModel":
      patchBatchPredictionCard(sid, action.cardId, {
        selectedModelId: action.modelId,
        checkResult: null,
        checkError: undefined,
        runError: undefined,
      });
      break;
    case "setFile":
      if (action.file) {
        batchUploadFileByCardId.value[action.cardId] = action.file;
      } else {
        delete batchUploadFileByCardId.value[action.cardId];
      }
      patchBatchPredictionCard(sid, action.cardId, {
        fileName: action.file?.name || "",
        checkResult: null,
        checkError: undefined,
        runError: undefined,
      });
      break;
    case "check":
      void checkBatchPredictionCard(sid, action.cardId);
      break;
    case "run":
      patchBatchPredictionCard(sid, action.cardId, { runStartedAt: new Date().toISOString() });
      void runBatchPredictionCard(sid, action.cardId);
      break;
    case "cancel":
      delete batchUploadFileByCardId.value[action.cardId];
      patchBatchPredictionCard(sid, action.cardId, {
        status: "cancelled",
        closedAt: new Date().toISOString(),
        checkRunning: false,
        runRunning: false,
        runStartedAt: null,
      });
      break;
    default:
      break;
  }
}

async function onSend(text: string) {
  uiError.value = "";
  actionConfirmError.value = null;
  const raw = text.trim();
  const sid = activeSessionId.value;

  if (!includesTrainingKeyword(raw)) {
    if (isBatchPredictionEnterCommand(raw)) {
      pushMsg("user", text);
      await insertBatchPredictionCard(sid, raw);
      return;
    }
    if (isPredictionExitCommand(raw)) {
      pushMsg("user", text);
      cancelAllEditingPredictionCards(sid);
      pushMsg("assistant", t("prediction.narrative.exitWorkspaceHint"));
      return;
    }
    if (isPredictionExecuteCommand(raw)) {
      pushMsg("user", text);
      const cid = findLastEditingCardId(sid);
      if (isExactStartPredictionCommand(raw) && !cid) {
        await insertPredictionFormCard(sid, { triggerUserText: raw });
        return;
      }
      if (cid) await submitPredictionCard(sid, cid);
      else
        pushMsg("assistant", t("prediction.narrative.noWorkspaceForExecuteHint"));
      return;
    }
    if (isPredictionEnterCommand(raw)) {
      pushMsg("user", text);
      await insertPredictionFormCard(sid, { triggerUserText: raw });
      return;
    }
    if (isRecommendationWorkspaceEnterCommand(raw)) {
      await openRecommendationWorkspaceLikeQuickEntry(sid, text);
      return;
    }
  }

  const prevTrain = latestChatData.value;
  // Merge only training-domain params into the chat turn; prediction draft patient_features never go to the next LLM message—confirm API only.
  const trainClientCtx =
    (prevTrain?.recognized_action === "create_training_job" ||
      prevTrain?.recognized_action === "draft_training_job") &&
    prevTrain.completed_params &&
    typeof prevTrain.completed_params === "object" &&
    Object.keys(prevTrain.completed_params as object).length > 0
      ? { ...(prevTrain.completed_params as Record<string, unknown>) }
      : undefined;
  const sm = selectedModel.value;
  const modelTaskHint = sm
    ? [sm.clinical_task_id, sm.ml_task_type, sm.task_type, sm.task_name].filter(Boolean).join("|")
    : "";
  const selectedTask =
    selectedTaskId.value != null
      ? tasks.value.find((t) => String(t.id) === String(selectedTaskId.value))
      : null;
  const focusJobType = selectedTask ? String((selectedTask as { job_type?: string }).job_type || "") : "";
  const chatContextMode = focusJobType === "recommend_regimen" ? "recommendation" : activeNav.value;
  const chatContext: Record<string, unknown> = {
    mode: chatContextMode,
    locale: String(locale.value || ""),
    ...(typeof navigator !== "undefined" && navigator.language ? { accept_language: navigator.language } : {}),
    dataset: selectedDataset.value ? `${selectedDataset.value.id}|${selectedDataset.value.name}` : "",
    model: selectedModelId.value || "",
    ...(modelTaskHint ? { model_task_hint: modelTaskHint } : {}),
    ...(selectedTaskId.value
      ? { focus_job_id: selectedTaskId.value, current_job_id: selectedTaskId.value }
      : {}),
    ...(selectedTask
      ? {
          focus_task_status: String((selectedTask as { status?: string }).status || ""),
          focus_job_type: focusJobType,
        }
      : {}),
    ...(sm && String(sm.task_name || "").trim()
      ? { selected_model_display_name: String(sm.task_name).trim() }
      : {}),
  };
  console.info("[chat-context-send]", {
    message: raw,
    page: activeNav.value,
    focus_job_id: (chatContext.focus_job_id as string | undefined) || "",
    current_job_id: (chatContext.current_job_id as string | undefined) || "",
    selectedTaskId: selectedTaskId.value || "",
    right_selected_task_id: selectedTask ? String(selectedTask.id || "") : "",
    right_selected_task_type: selectedTask ? String((selectedTask as { job_type?: string }).job_type || "") : "",
    pending_confirmation_id: latestChatData.value?.pending_confirmation?.pending_action_id || "",
  });
  pushMsg("user", text);
  chatTurnInFlight.value = true;
  chatTurnStartedAt.value = Date.now();
  try {
    const data = await postChatTurn(text, {
      ...(trainClientCtx ? { clientCompletedParams: trainClientCtx } : {}),
      chatContext,
    });
    if (data.route === "prediction_entry") {
      latestChatData.value = null;
      await insertPredictionFormCard(activeSessionId.value, { triggerUserText: raw });
      return;
    }
    if (
      data.route === "deterministic_action" &&
      data.recognized_action === "draft_single_prediction"
    ) {
      latestChatData.value = null;
      await insertPredictionFormCard(activeSessionId.value, { triggerUserText: raw });
      return;
    }
    latestChatData.value = data;
    pushMsg("assistant", toNaturalAssistantText(data), data);
  } catch (e) {
    const msg = e instanceof ApiError ? e.message : t("app.errors.chatModelUnavailable");
    pushMsg("assistant", msg, null, "error");
  } finally {
    chatTurnInFlight.value = false;
    chatTurnStartedAt.value = null;
  }
}

function toNaturalAssistantText(data: ChatTurnData): string {
  if (data.route === "prediction_entry") return data.assistant_message;
  if (data.route === "llm_chat") return data.assistant_message;
  if (data.route === "concise_status") return data.assistant_message;
  if (data.route === "workflow_guidance") return data.assistant_message;
  if (data.route === "tool_query") return data.assistant_message;
  if (data.route === "fallback_template") {
    return data.assistant_message || t("chat.narrative.fallbackNoExecutableTask");
  }
  // Training flow: copy is owned by the backend for consistency with the API and to avoid leaking internal action names.
  if (data.recognized_action === "draft_single_prediction") {
    return t("prediction.narrative.draftSingleUseWorkspaceHint");
  }
  if (data.recognized_action === "create_training_job" || data.recognized_action === "draft_training_job") {
    return data.assistant_message;
  }
  if (!data.recognized_action) return data.assistant_message;
  const action = chatActionLabel(data.recognized_action);
  if (data.missing_fields.length > 0) {
    return t("chat.narrative.recognizedMissingFields", {
      action,
      fields: data.missing_fields.map((f) => chatFieldLabel(f)).join(t("chat.listSeparator")),
    });
  }
  return t("chat.narrative.recognizedReadyToConfirm", { action });
}

function patchAssistantMessageAfterConfirm(pendingActionId: string) {
  const msgs = sessionMessages.value[activeSessionId.value] || [];
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const m = msgs[i];
    if (m.role === "assistant" && m.actionData?.pending_confirmation?.pending_action_id === pendingActionId) {
      sessionMessages.value[activeSessionId.value][i] = {
        ...m,
        actionData: m.actionData
          ? {
              ...m.actionData,
              pending_confirmation: null,
              can_confirm: false,
              missing_fields: [],
              confirmation_outcome: "success",
              confirmed_pending_action_id: pendingActionId,
            }
          : m.actionData,
      };
      break;
    }
  }
}

const WF_PHASE3: TrainingWorkflowPhase = "train_phase3_feature_confirm_pending";
const WF_PHASE4: TrainingWorkflowPhase = "train_phase4_train_config_pending";
const WF_PHASE5: TrainingWorkflowPhase = "train_phase5_publish_pending";
/**
 * Per session/job: dedupe workflow card inserts (card_id -> true).
 * At most one card per job per phase (avoid duplicates from polling).
 */
const sessionWorkflowCards = ref<Record<string, Record<string, boolean>>>({});
/** De-dupe training chat narratives: key = sessionId|jobId|narrative_kind|detail (e.g. stage bucket); avoids near-duplicate bubbles from polling/cards. */
const sessionTrainNarrativeKeys = ref<Record<string, boolean>>({});

const CW_PERSIST_KEY = "cw_chat_session_state_v3";
const WORKFLOW_TRACE_PREFIX = "[workflow-bridge]";

function traceWorkflow(step: string, payload?: Record<string, unknown>) {
  if (payload) console.info(`${WORKFLOW_TRACE_PREFIX} ${step}`, payload);
  else console.info(`${WORKFLOW_TRACE_PREFIX} ${step}`);
}

function trainPollNarrativeKey(sid: string, jobId: string, stage: string): string {
  const s = String(stage || "");
  let bucket = "other";
  if (s.includes("phase2") || s.includes("feature_search")) bucket = "p2";
  else if (s.includes("phase3")) bucket = "p3";
  else if (s.includes("phase4") || s === "model_training" || s === "evaluation") bucket = "p4";
  else if (s.includes("phase5") || s.includes("publish")) bucket = "p5";
  else if (s.includes("dataset")) bucket = "p0";
  return `${sid}|${jobId}|backend_running|${bucket}`;
}

function tryRestoreSessionState() {
  try {
    const raw = sessionStorage.getItem(CW_PERSIST_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const ps = parsed.sessions;
    const pa = parsed.activeSessionId;
    const pm = parsed.sessionMessages;
    const po = parsed.taskSessionOwner;
    const pc = parsed.sessionWorkflowCards;
    const pn = parsed.sessionTaskAnnounce;
    const pct = parsed.sessionCurrentTask;
    const pnk = parsed.sessionTrainNarrativeKeys;
    if (Array.isArray(ps)) sessions.value = migrateSessionsFromStorage(ps);
    if (typeof pa === "string" && pa) activeSessionId.value = pa;
    if (pm && typeof pm === "object") sessionMessages.value = pm as Record<string, MessageItem[]>;
    if (po && typeof po === "object") taskSessionOwner.value = po as Record<string, string>;
    if (pc && typeof pc === "object") sessionWorkflowCards.value = pc as Record<string, Record<string, boolean>>;
    if (pn && typeof pn === "object") sessionTaskAnnounce.value = pn as Record<string, Record<string, AnnounceState>>;
    if (pct && typeof pct === "object") sessionCurrentTask.value = pct as Record<string, string | null>;
    if (pnk && typeof pnk === "object") sessionTrainNarrativeKeys.value = pnk as Record<string, boolean>;
    traceWorkflow("restore_session_state", {
      active_session_id: activeSessionId.value,
      owner_count: Object.keys(taskSessionOwner.value).length,
      workflow_card_session_count: Object.keys(sessionWorkflowCards.value).length,
    });
  } catch {
    // ignore corrupted storage
  }
}

function persistSessionState() {
  try {
    const payload = {
      sessions: sessions.value,
      activeSessionId: activeSessionId.value,
      sessionMessages: sessionMessages.value,
      taskSessionOwner: taskSessionOwner.value,
      sessionWorkflowCards: sessionWorkflowCards.value,
      sessionCurrentTask: sessionCurrentTask.value,
      sessionTaskAnnounce: sessionTaskAnnounce.value,
      sessionTrainNarrativeKeys: sessionTrainNarrativeKeys.value,
    };
    sessionStorage.setItem(CW_PERSIST_KEY, JSON.stringify(payload));
  } catch {
    // ignore quota/private mode
  }
}

function ensureSessionWorkflowState(sessionId: string) {
  if (!sessionWorkflowCards.value[sessionId]) sessionWorkflowCards.value[sessionId] = {};
  if (!sessionTaskAnnounce.value[sessionId]) sessionTaskAnnounce.value[sessionId] = {};
}

function hasWorkflowCardMessage(sid: string, jobId: string, cardId: string): boolean {
  const msgs = sessionMessages.value[sid] || [];
  return msgs.some((m) => m.workflowActionData?.job_id === jobId && m.workflowActionData?.card_id === cardId);
}

/** True when the phase-5 release confirmation card is still awaiting the user (pending), so the final TaskResultCard is deferred. */
function hasTrainingWorkflowCardForTask(sid: string, taskId: string): boolean {
  const tid = String(taskId || "").trim();
  if (!tid) return false;
  return (sessionMessages.value[sid] || []).some(
    (m) =>
      m.role === "assistant" &&
      m.workflowActionData?.kind === "training_workflow_pending_action" &&
      String(m.workflowActionData.job_id || "").trim() === tid &&
      String(m.workflowActionData.phase || "") === WF_PHASE5 &&
      String(m.workflowActionData.status || "").toLowerCase() === "pending",
  );
}

/** Prefer the phase-5 workflow message for this job; otherwise the latest matching workflow assistant row. */
function trainingWorkflowPatchMessageIndex(sid: string, taskId: string): number {
  const tid = String(taskId || "").trim();
  const msgs = sessionMessages.value[sid] || [];
  let fallback = -1;
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    if (m.role !== "assistant" || !m.workflowActionData) continue;
    if (m.workflowActionData.kind !== "training_workflow_pending_action") continue;
    if (String(m.workflowActionData.job_id || "").trim() !== tid) continue;
    if (fallback < 0) fallback = i;
    if (String(m.workflowActionData.phase || "") === WF_PHASE5) return i;
  }
  return fallback;
}

function patchTrainingWorkflowCardForCompletedJob(sid: string, taskId: string, detail: TaskDetailData): void {
  const idx = trainingWorkflowPatchMessageIndex(sid, taskId);
  if (idx < 0) return;
  const msgs = sessionMessages.value[sid];
  if (!msgs || idx >= msgs.length) return;
  const prev = msgs[idx];
  const wf = prev.workflowActionData;
  if (!wf) return;

  const task = detail.task as Record<string, unknown>;
  const rsRaw = task.result_summary;
  const rs = (rsRaw && typeof rsRaw === "object" ? rsRaw : {}) as Record<string, unknown>;
  const taskArts =
    task.artifacts && typeof task.artifacts === "object" ? (task.artifacts as Record<string, string>) : {};
  const detailArts =
    detail.artifacts && typeof detail.artifacts === "object" ? (detail.artifacts as Record<string, string>) : {};
  const artifacts: Record<string, string> = { ...(wf.artifacts || {}), ...taskArts, ...detailArts };

  const fromRs =
    rs.key_metrics && typeof rs.key_metrics === "object" ? (rs.key_metrics as Record<string, unknown>) : undefined;
  const key_metrics = fromRs ?? wf.key_metrics;

  const ps = (task.params as Record<string, unknown>) || {};
  const rawModel = rs.model_id_draft ?? rs.model_id ?? ps.model_id ?? wf.model_id;
  const modelIdStr = rawModel != null ? String(rawModel).trim() : "";
  const model_id = modelIdStr || wf.model_id || null;

  const nextWf: TrainingWorkflowPendingActionData = {
    ...wf,
    result_summary: { ...((wf.result_summary || {}) as Record<string, unknown>), ...rs },
    artifacts,
    ...(key_metrics && typeof key_metrics === "object" ? { key_metrics } : {}),
    model_id,
  };

  const nextMsgs = [...msgs];
  nextMsgs[idx] = { ...prev, workflowActionData: nextWf };
  sessionMessages.value[sid] = nextMsgs;
  traceWorkflow("patch_workflow_train_completion", { owner_session_id: sid, job_id: taskId, message_index: idx });
}

function resolveWorkflowPhaseForAction(
  action: string,
  phaseRaw: unknown,
): TrainingWorkflowPhase | null {
  const fromPayload = normalizeTrainingWorkflowPhase(String(phaseRaw || ""));
  if (fromPayload) return fromPayload;
  if (action === "confirm_final_features") return WF_PHASE3;
  if (action === "confirm_train_config") return WF_PHASE4;
  if (action === "confirm_publish") return WF_PHASE5;
  return null;
}

function waitingWorkflowBubbleIntro(phaseRaw: string, useCvShap?: boolean): string {
  const phase = normalizeTrainingWorkflowPhase(String(phaseRaw || ""));
  if (!phase) return "";
  if (phase === WF_PHASE3) {
    return useCvShap ? t("chat.trainingWorkflow.phase3.waitingIntroScreening") : t("chat.trainingWorkflow.phase3.waitingIntroShort");
  }
  if (phase === WF_PHASE4) return t("training.narrative.waitingIntroModelSetup");
  if (phase === WF_PHASE5) return t("training.narrative.waitingIntroPublish");
  return "";
}

async function maybeInsertWorkflowCard(jobId: string) {
  let ownerSession = taskSessionOwner.value[jobId];
  let detailPrefetch: TaskDetailData | undefined;

  if (!ownerSession && selectedTaskId.value === jobId) {
    // Fallback: task focused in UI but owner missing — bind to the active session once.
    ownerSession = activeSessionId.value;
    taskSessionOwner.value[jobId] = ownerSession;
    traceWorkflow("owner_fallback_bound_to_active_session", {
      active_session_id: activeSessionId.value,
      job_id: jobId,
      owner_session_id: ownerSession,
    });
  }

  if (!ownerSession) {
    try {
      detailPrefetch = await getTaskDetail(jobId);
      taskDetailById.value = { ...taskDetailById.value, [jobId]: detailPrefetch };
      const task = (detailPrefetch.task as Record<string, unknown>) || {};
      const sidRaw = task.session_id;
      const sid = typeof sidRaw === "string" && sidRaw ? sidRaw : "";
      if (sid && sessions.value.some((s) => s.id === sid)) {
        ownerSession = sid;
        taskSessionOwner.value[jobId] = ownerSession;
        traceWorkflow("owner_resolved_from_task_payload", {
          job_id: jobId,
          owner_session_id: ownerSession,
        });
      }
    } catch {
      /* ignore */
    }
  }

  traceWorkflow("maybe_insert_enter", {
    active_session_id: activeSessionId.value,
    selected_task_id: selectedTaskId.value,
    job_id: jobId,
    owner_exists: Boolean(ownerSession),
    owner_session_id: ownerSession || null,
  });

  if (!ownerSession) {
    traceWorkflow("maybe_insert_skip_no_owner", { job_id: jobId });
    return;
  }
  ensureSessionWorkflowState(ownerSession);

  try {
    const detail = await getTaskDetail(jobId);
    taskDetailById.value = { ...taskDetailById.value, [jobId]: detail };
    const task = (detail.task as Record<string, unknown>) || {};
    const status = String(task.status || "");
    const rs = (task.result_summary as Record<string, unknown>) || {};
    const row = tasks.value.find((t) => String(t.id) === String(jobId));
    const rowPhase = row ? resolveTrainingWorkflowPhase(row as Record<string, unknown>) : null;
    traceWorkflow("maybe_insert_detail", {
      selected_task_id: selectedTaskId.value,
      job_id: jobId,
      status,
      train_workflow_phase: String(rs.train_workflow_phase || ""),
      current_stage: String(task.current_stage || ""),
      row_phase: rowPhase || null,
    });
    if (status !== "waiting_user") return;

    const card = buildTrainingWorkflowPendingCard(jobId, detail);
    traceWorkflow("extract_card_result", {
      job_id: jobId,
      success: Boolean(card),
      card_id: card?.card_id || null,
      phase: card?.phase || null,
      row_phase: rowPhase || null,
    });
    if (!card) return;
    if (rowPhase && rowPhase !== card.phase) {
      traceWorkflow("skip_card_phase_mismatch", {
        job_id: jobId,
        owner_session_id: ownerSession,
        row_phase: rowPhase,
        card_phase: card.phase,
        card_id: card.card_id,
      });
      return;
    }

    const cardId = card.card_id;
    if (sessionWorkflowCards.value[ownerSession][cardId]) {
      traceWorkflow("skip_duplicate_card", { job_id: jobId, owner_session_id: ownerSession, card_id: cardId });
      return;
    }
    if (hasWorkflowCardMessage(ownerSession, jobId, cardId)) {
      sessionWorkflowCards.value[ownerSession][cardId] = true;
      traceWorkflow("skip_duplicate_card_message", { job_id: jobId, owner_session_id: ownerSession, card_id: cardId });
      return;
    }

    // Single narrative thread: the card already has the stage title and form; the bubble is only one "why we paused" line, not repeating the card lead.
    const introKey = `${ownerSession}|${jobId}|waiting_intro|${card.phase}`;
    const seenIntro = Boolean(sessionTrainNarrativeKeys.value[introKey]);
    if (!seenIntro) {
      sessionTrainNarrativeKeys.value = { ...sessionTrainNarrativeKeys.value, [introKey]: true };
    }
    // Same session/stage: only the first bubble adds the situational line; after refresh do not stack the same hint again (card still inserts).
    const taskForIntro = (detail.task as Record<string, unknown>) || {};
    const paramsForIntro = (taskForIntro.params as Record<string, unknown>) || {};
    const useCvShapIntro = Boolean(paramsForIntro.use_cv_shap);
    const intro = seenIntro ? "" : waitingWorkflowBubbleIntro(String(card.phase || ""), useCvShapIntro);
    pushMsgToSession(ownerSession, "assistant", intro, null, card, "status");

    sessionWorkflowCards.value[ownerSession][cardId] = true;
    traceWorkflow("insert_card_success", { job_id: jobId, owner_session_id: ownerSession, card_id: cardId });
  } catch (e) {
    if (import.meta.env.DEV) console.warn("[maybeInsertWorkflowCard]", jobId, e);
  }
}

function markAllWorkflowCardsSubmitted(jobId: string, phase: unknown) {
  const phaseStr = String(phase ?? "");
  const base = sessionMessages.value;
  const out: Record<string, MessageItem[]> = { ...base };
  let mutated = false;
  for (const sid of Object.keys(out)) {
    const msgs = out[sid];
    if (!msgs?.length) continue;
    let changed = false;
    const updated = msgs.map((m) => {
      if (m.role !== "assistant" || !m.workflowActionData) return m;
      if (m.workflowActionData.job_id === jobId && m.workflowActionData.phase === phaseStr) {
        changed = true;
        return { ...m, workflowActionData: { ...m.workflowActionData, status: "submitted" as const } };
      }
      return m;
    });
    if (changed) {
      out[sid] = updated;
      mutated = true;
    }
  }
  if (mutated) sessionMessages.value = out;
}

function markTrainingJobTerminalAnnounced(sid: string, jobId: string, lastStatus: string, lastStage: string) {
  ensureSessionWorkflowState(sid);
  const prev = sessionTaskAnnounce.value[sid]?.[jobId] || {};
  sessionTaskAnnounce.value[sid] = {
    ...sessionTaskAnnounce.value[sid],
    [jobId]: {
      ...prev,
      isTerminalAnnounced: true,
      lastStatus,
      lastStage,
    },
  };
}

type InsertTrainingWorkflowTerminalOpts = { forceResultCard?: boolean };

/**
 * Insert the training completion / failure result card once per job.
 * Needed because `refreshTasks` may mark the job `completed` before poll runs again—then `shouldPollJob` is false and the terminal poll branch never fires.
 */
async function insertTrainingWorkflowTerminalIfMissing(
  sid: string,
  jobId: string,
  opts?: InsertTrainingWorkflowTerminalOpts,
): Promise<void> {
  const jid = String(jobId || "").trim();
  if (!jid || !sid) return;
  const msgs = sessionMessages.value[sid] || [];
  if (sessionChatHasTrainCompletionResult(msgs, jid)) {
    markTrainingJobTerminalAnnounced(sid, jid, "completed", "");
    return;
  }
  if (sessionChatHasTrainFailureResult(msgs, jid)) {
    markTrainingJobTerminalAnnounced(sid, jid, "failed", "");
    return;
  }
  let detail: TaskDetailData;
  try {
    detail = await getTaskDetail(jid);
  } catch {
    return;
  }
  taskDetailById.value = { ...taskDetailById.value, [jid]: detail };
  if (String(detail.task.job_type || "") !== "train_model") return;
  const st = String(detail.task.status || "").toLowerCase();
  const stage = String(detail.task.current_stage || "");
  if (st === "completed") {
    void refreshModels();
    try {
      if (hasTrainingWorkflowCardForTask(sid, jid) && !opts?.forceResultCard) {
        patchTrainingWorkflowCardForCompletedJob(sid, jid, detail);
        markTrainingJobTerminalAnnounced(sid, jid, "completed", stage);
        traceWorkflow("insert_train_terminal_completion_patch_workflow", { job_id: jid, owner_session_id: sid });
      } else {
        const msgsNow = sessionMessages.value[sid] || [];
        if (sessionChatHasTrainCompletionResult(msgsNow, jid)) {
          markTrainingJobTerminalAnnounced(sid, jid, "completed", stage);
          traceWorkflow("insert_train_terminal_completion_card_deduped", { job_id: jid, owner_session_id: sid });
        } else {
          pushMsgToSession(sid, "assistant", "", null, null, "status", buildCompletionCard(detail, t));
          markTrainingJobTerminalAnnounced(sid, jid, "completed", stage);
          traceWorkflow("insert_train_terminal_completion_card", { job_id: jid, owner_session_id: sid });
        }
      }
    } catch (e) {
      if (import.meta.env.DEV) console.warn("[insertTrainingWorkflowTerminalIfMissing] completion", jid, e);
    }
  } else if (st === "failed") {
    const task = detail.task;
    const reason = String(task.error_message || task.message || "").trim();
    const maskedReason = sanitizeUserFacingLine(reason, t);
    const pfx = getTerminalFailureAssistantPrefix("train_model", t);
    const shortReason = maskedReason ? `${pfx}${maskedReason}` : `${pfx.replace(/[:\uFF1A]$/, "")}.`;
    try {
      pushMsgToSession(sid, "assistant", shortReason, null, null, "error", buildFailureCard(task, t));
      markTrainingJobTerminalAnnounced(sid, jid, "failed", stage);
      traceWorkflow("insert_train_terminal_failure_card", { job_id: jid, owner_session_id: sid });
    } catch (e) {
      if (import.meta.env.DEV) console.warn("[insertTrainingWorkflowTerminalIfMissing] failure card", jid, e);
    }
  }
}

async function refreshPredictionFormCardsModelsForSession(sid: string) {
  const msgs = sessionMessages.value[sid] || [];
  for (const m of msgs) {
    const card = m.predictionFormCard;
    if (!card || card.status === "cancelled") continue;
    patchPredictionFormCard(sid, card.card_id, { modelsLoading: true, modelsError: "" });
    try {
      const tk = card.selectedPredictionTaskKey;
      const data = tk
        ? await getAvailablePredictionModels(canonicalApiTaskFromUiKey(tk))
        : await getAvailablePredictionModels();
      patchPredictionFormCard(sid, card.card_id, {
        models: data.items,
        modelsLoading: false,
        modelsError: "",
      });
      reconcilePredictionFormCardModelSelection(sid, card.card_id, {});
    } catch (e) {
      patchPredictionFormCard(sid, card.card_id, {
        modelsLoading: false,
        modelsError: formatPredictionApiError(e, t),
      });
    }
  }
}

async function refreshRecommendationWorkflowCardsModelsForSession(sid: string) {
  const msgs = sessionMessages.value[sid] || [];
  for (const m of msgs) {
    const card = m.recommendationWorkflowCard;
    if (!card || card.status === "cancelled") continue;
    patchRecommendationWorkflowCard(sid, card.card_id, { modelsLoading: true, modelsError: "" });
    try {
      const data = await getAvailablePredictionModels();
      const survival = data.items.filter(isSurvivalRecommendationCandidate);
      const regimensData = await listRegimens();
      const enabledCount = regimensData.items.filter((r) => r.enabled).length;
      patchRecommendationWorkflowCard(sid, card.card_id, {
        models: survival,
        modelsLoading: false,
        modelsError: survival.length === 0 ? t("recommendation.narrative.noSurvivalModelsError") : "",
        enabledRegimenCount: enabledCount,
        regimensLoading: false,
        regimensError: "",
      });
    } catch (e) {
      patchRecommendationWorkflowCard(sid, card.card_id, {
        modelsLoading: false,
        modelsError: formatPredictionApiError(e, t),
      });
    }
  }
}

async function flushTrainingWorkflowTerminalAfterRelease(ownerSession: string, jobId: string): Promise<void> {
  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    try {
      const st = await getTaskStatus(jobId);
      const s = String(st.task.status || "").toLowerCase();
      if (s === "completed" || s === "failed" || s === "canceled" || s === "cancelled") {
        await refreshTasks();
        await insertTrainingWorkflowTerminalIfMissing(ownerSession, jobId, { forceResultCard: true });
        await refreshPredictionFormCardsModelsForSession(ownerSession);
        await refreshRecommendationWorkflowCardsModelsForSession(ownerSession);
        return;
      }
    } catch {
      /* ignore */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  await refreshTasks();
  await insertTrainingWorkflowTerminalIfMissing(ownerSession, jobId, { forceResultCard: true });
  await refreshPredictionFormCardsModelsForSession(ownerSession);
  await refreshRecommendationWorkflowCardsModelsForSession(ownerSession);
}

async function onConfirmWorkflow(payload: Record<string, unknown>) {
  const jobId = String(payload.job_id || "").trim();
  const action = String(payload.action || "").trim();
  const confirmedPhase = resolveWorkflowPhaseForAction(action, payload.phase);
  traceWorkflow("confirm_workflow_clicked", {
    active_session_id: activeSessionId.value,
    job_id: jobId || null,
    action: action || null,
    payload_phase: payload.phase != null ? String(payload.phase) : null,
  });
  if (!jobId || !action) {
    uiError.value = t("app.errors.workflowConfirmMissingJobOrAction");
    return;
  }
  const wfSubmitKey = `${jobId}|${String(confirmedPhase || payload.phase || "")}`;
  if (confirmingWorkflowKey.value === wfSubmitKey) return;

  uiError.value = "";
  actionConfirmError.value = null;
  confirmingWorkflowKey.value = wfSubmitKey;
  try {
    await postTrainingWorkflow(jobId, payload);
    if (confirmedPhase) markAllWorkflowCardsSubmitted(jobId, confirmedPhase);
    await refreshTasks();

    const ownerSession = taskSessionOwner.value[jobId];
    if (ownerSession) {
      if (action === "confirm_final_features") {
        await maybeInsertWorkflowCard(jobId);
      } else if (action === "confirm_train_config") {
        // Progress is announced by polling status bubbles; avoid duplicating "training" style hints here.
      } else if (action === "confirm_publish") {
        if (ownerSession) void flushTrainingWorkflowTerminalAfterRelease(ownerSession, jobId);
      } else {
        pushMsgToSession(ownerSession, "assistant", t("chat.narrative.operationSubmitted"), null, null, "status");
      }
    }
    startPollingIfNeeded();
  } catch (e) {
    const msg = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
    uiError.value = t("app.errors.workflowSubmitFailed", { message: msg });
  } finally {
    if (confirmingWorkflowKey.value === wfSubmitKey) confirmingWorkflowKey.value = null;
  }
}

async function onConfirm(detail?: { patient_features?: Record<string, unknown> }) {
  const chat = latestChatData.value;
  const pending = chat?.pending_confirmation;
  if (!pending) return;
  if (confirmingPendingActionId.value) return;
  if (pending.status !== "pending") {
    uiError.value = t("app.errors.pendingActionNotConfirmable", { status: pending.status });
    return;
  }

  const isTrain =
    chat.recognized_action === "create_training_job" || chat.recognized_action === "draft_training_job";
  const isPredDraft = chat.recognized_action === "draft_single_prediction";
  if (isTrain) {
    const mergedNorm = buildMergedPhase1TrainingPayload(chat);
    const miss = missingTrainingPhase1ParameterKeys(mergedNorm, true);
    if (miss.length) {
      uiError.value = t("app.errors.trainMissingRequiredAfterMerge", { fields: miss.join(", ") });
      return;
    }
  } else if (isPredDraft) {
    const pf = detail?.patient_features;
    if (!pf || typeof pf !== "object" || Object.keys(pf).length === 0) {
      uiError.value = t("app.errors.predictionDraftNeedPatientFeatures");
      return;
    }
  } else if (chat.missing_fields?.length) {
    uiError.value = t("app.errors.missingParamsList", { fields: chat.missing_fields.join(", ") });
    return;
  }

  actionConfirmError.value = null;
  uiError.value = "";
  let completedParams: Record<string, unknown> | undefined =
    chat.completed_params && typeof chat.completed_params === "object"
      ? { ...(chat.completed_params as Record<string, unknown>) }
      : undefined;
  if (isPredDraft && detail?.patient_features) {
    completedParams = { ...completedParams, patient_features: detail.patient_features };
  }

  try {
    confirmingPendingActionId.value = pending.pending_action_id;

    const finalPayloadForReceipt = isTrain ? buildMergedPhase1TrainingPayload(chat) : {};

    const data = await postConfirm(pending.pending_action_id, {
      completedParams,
      locale: apiUiLocale(),
    });

    if (data.job_id) {
      const taskRec = data.task as Record<string, unknown> | undefined;
      const createdTaskStatus = String(taskRec?.status || "");
      selectedTaskId.value = data.job_id;
      taskSessionOwner.value[data.job_id] = activeSessionId.value;
      sessionCurrentTask.value[activeSessionId.value] = data.job_id;
      traceWorkflow("bind_job_owner", {
        active_session_id: activeSessionId.value,
        job_id: data.job_id,
        owner_session_id: taskSessionOwner.value[data.job_id],
      });
      if (!sessionTaskAnnounce.value[activeSessionId.value]) sessionTaskAnnounce.value[activeSessionId.value] = {};
      sessionTaskAnnounce.value[activeSessionId.value][data.job_id] = {};
      ensureSessionWorkflowState(activeSessionId.value);
      // Do not block the "creating task…" UX on task list refresh finishing.
      void refreshTasks();
      if (createdTaskStatus !== "failed") startPollingIfNeeded();

      if (isTrain) {
        if (createdTaskStatus === "failed") {
          const reason = String(
            taskRec?.error_message || taskRec?.message || t("training.narrative.precheckFailedDefault"),
          );
          pushMsg(
            "assistant",
            t("training.narrative.precheckFailedWithReason", { reason }),
            null,
            "error",
            buildFailureCard(
              {
                id: data.job_id,
                status: "failed",
                progress: Number(taskRec?.progress || 100),
                current_stage: String(taskRec?.current_stage || "training_precheck_failed"),
                message: String(taskRec?.message || t("training.narrative.precheckFailedDefault")),
                error_message: reason,
              },
              t,
            ),
          );
          if (!sessionTaskAnnounce.value[activeSessionId.value]) sessionTaskAnnounce.value[activeSessionId.value] = {};
          sessionTaskAnnounce.value[activeSessionId.value][data.job_id] = {
            lastStatus: "failed",
            lastStage: String(taskRec?.current_stage || "training_precheck_failed"),
            isTerminalAnnounced: true,
          };
        } else {
          const receipt: TrainingJobReceiptData = {
            pending_action_id: pending.pending_action_id,
            title: t("training.narrative.receiptTitleCreated"),
            job_id: data.job_id,
            task_kind_label: t("training.narrative.receiptTaskKindLabel"),
            backend_assistant_message: data.assistant_message,
            task_status: taskRec?.status != null ? String(taskRec.status) : undefined,
            task_message: taskRec?.message != null ? String(taskRec.message) : undefined,
            summary_lines: buildUserFacingTrainingReceiptLines(finalPayloadForReceipt, t),
            merged_payload_snapshot: finalPayloadForReceipt,
            next_hint: t("training.narrative.receiptNextHint"),
          };
          const screeningBubble = Boolean((finalPayloadForReceipt as Record<string, unknown>).use_cv_shap);
          pushMsg(
            "assistant",
            "",
            null,
            "status",
            null,
            receipt,
          );
        }
      } else {
        pushMsg("assistant", data.assistant_message || t("chat.narrative.confirmSucceededTaskCreated"), null, "status");
      }

      patchAssistantMessageAfterConfirm(pending.pending_action_id);
      latestChatData.value = null;
    } else {
      uiError.value = t("app.errors.confirmSucceededNoJobId");
      actionConfirmError.value = { pendingActionId: pending.pending_action_id, message: uiError.value };
    }
  } catch (e) {
    let msg = String(e);
    if (e instanceof ApiError) {
      msg = t("app.errors.withCode", { message: e.message, code: e.code });
      uiError.value = t("app.errors.confirmFailedWithCode", { code: e.code, message: e.message });
    } else {
      uiError.value = t("app.errors.confirmFailed", { message: msg });
    }
    actionConfirmError.value = { pendingActionId: pending.pending_action_id, message: msg };
    pushMsg("assistant", t("chat.narrative.taskCreateFailed", { message: msg }), null, "error");
  } finally {
    confirmingPendingActionId.value = null;
  }
}

function onEditParams(payload: { updatedParams: Record<string, unknown>; missingFields: string[] }) {
  actionConfirmError.value = null;
  const msgs = sessionMessages.value[activeSessionId.value] || [];
  let targetIdx = -1;
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const ad = msgs[i].actionData;
    if (
      msgs[i].role === "assistant" &&
      ad &&
      ad.route === "deterministic_action" &&
      (ad.recognized_action === "create_training_job" || ad.recognized_action === "draft_training_job")
    ) {
      targetIdx = i;
      break;
    }
  }

  const base = targetIdx >= 0 ? msgs[targetIdx].actionData : latestChatData.value;
  if (!base) return;

  const next = {
    ...base,
    completed_params: { ...(base.completed_params as Record<string, unknown>), ...payload.updatedParams },
    missing_fields: payload.missingFields,
    can_confirm: payload.missingFields.length === 0 && Boolean(base.pending_confirmation),
  };

  if (targetIdx >= 0) {
    msgs[targetIdx] = { ...msgs[targetIdx], actionData: next };
  }

  const samePending =
    latestChatData.value?.pending_confirmation?.pending_action_id &&
    latestChatData.value?.pending_confirmation?.pending_action_id === base.pending_confirmation?.pending_action_id;
  if (samePending || !latestChatData.value) {
    latestChatData.value = next;
  }
}

function resetShellWorkflowState() {
  confirmingWorkflowKey.value = null;
  confirmingWorkflowSince.value = null;
  confirmingPendingActionId.value = null;
  actionConfirmError.value = null;
  shellRecoveryBanner.value = "";
  shellStaleDetected.value = false;
  chatTurnInFlight.value = false;
  chatTurnStartedAt.value = null;
  tasksLoading.value = false;
  tasksRefreshStartedAt.value = null;
  uiError.value = "";
  stopPolling();
  startPollingIfNeeded();
  void refreshTasks();
  void refreshModels();
}

function runShellWatchdogTick() {
  const now = Date.now();
  const STALE_WF_MS = 50_000;
  const STALE_TASKS_MS = 90_000;
  const STALE_CHAT_MS = 60_000;
  let recovered = false;
  const selId = selectedTaskId.value;
  if (selId && confirmingWorkflowKey.value) {
    const row = tasks.value.find((x) => String(x.id) === String(selId));
    const st = row ? String(row.status || "").toLowerCase() : "";
    if (st && st !== "waiting_user" && String(confirmingWorkflowKey.value).startsWith(`${String(selId)}|`)) {
      confirmingWorkflowKey.value = null;
      confirmingWorkflowSince.value = null;
      shellRecoveryBanner.value = t("app.shell.watchdogRecover");
      shellStaleDetected.value = true;
      recovered = true;
    }
  }
  if (confirmingWorkflowKey.value && confirmingWorkflowSince.value && now - confirmingWorkflowSince.value > STALE_WF_MS) {
    confirmingWorkflowKey.value = null;
    confirmingWorkflowSince.value = null;
    shellRecoveryBanner.value = t("app.shell.watchdogWorkflowConfirm");
    shellStaleDetected.value = true;
    recovered = true;
  }
  if (tasksLoading.value && tasksRefreshStartedAt.value != null && now - tasksRefreshStartedAt.value > STALE_TASKS_MS) {
    tasksLoading.value = false;
    tasksRefreshStartedAt.value = null;
    shellRecoveryBanner.value = t("app.shell.watchdogTasksList");
    shellStaleDetected.value = true;
    recovered = true;
  }
  if (chatTurnInFlight.value && chatTurnStartedAt.value != null && now - chatTurnStartedAt.value > STALE_CHAT_MS) {
    chatTurnInFlight.value = false;
    chatTurnStartedAt.value = null;
    shellRecoveryBanner.value = t("app.shell.watchdogRecover");
    shellStaleDetected.value = true;
    recovered = true;
  }
  if (recovered) {
    stopPolling();
    startPollingIfNeeded();
    void refreshTasks();
    void refreshModels();
  }
}

async function refreshTasks() {
  tasksLoadError.value = "";
  tasksLoading.value = true;
  tasksRefreshStartedAt.value = Date.now();
  try {
    const data = await getTasks();
    tasks.value = data.items as Array<TaskItem & Record<string, unknown>>;
    const waitingOwnedJobs = tasks.value
      .filter((t) => String(t.status || "") === "waiting_user" && Boolean(taskSessionOwner.value[String(t.id)]))
      .map((t) => String(t.id));
    const waitingWorkflowJobs = tasks.value.filter((t) => taskRowNeedsWorkflowConfirmation(t)).map((t) => String(t.id));
    const selectedWaitingJob = tasks.value.find(
      (t) => String(t.id) === String(selectedTaskId.value || "") && String(t.status || "") === "waiting_user",
    );
    if (selectedWaitingJob) waitingOwnedJobs.push(String(selectedWaitingJob.id));
    const waitingCheckJobs = Array.from(new Set([...waitingOwnedJobs, ...waitingWorkflowJobs]));
    traceWorkflow("refresh_tasks_snapshot", {
      active_session_id: activeSessionId.value,
      selected_job_id: selectedTaskId.value,
      waiting_owned_jobs: waitingCheckJobs,
      waiting_workflow_jobs: waitingWorkflowJobs,
    });
    for (const jobId of waitingCheckJobs) {
      await maybeInsertWorkflowCard(jobId);
    }
    for (const [jobId, sid] of Object.entries(taskSessionOwner.value)) {
      if (sid !== activeSessionId.value) continue;
      const tr = tasks.value.find((t) => String(t.id) === jobId);
      if (!tr || String(tr.job_type || "") !== "train_model") continue;
      const st = String(tr.status || "").toLowerCase();
      if (st === "completed" || st === "failed") {
        void insertTrainingWorkflowTerminalIfMissing(sid, jobId);
      }
    }
  } catch (e) {
    tasksLoadError.value = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
  } finally {
    tasksLoading.value = false;
    tasksRefreshStartedAt.value = null;
  }
}

function onGoTasks(jobId: string | null) {
  activeNav.value = "tasks";
  if (jobId) {
    selectedTaskId.value = jobId;
    sessionCurrentTask.value[activeSessionId.value] = jobId;
  }
  void refreshTasks();
}

const SESSION_MODEL_KEY = "cw_current_model_id";

async function onGoModels(modelId: string | null) {
  activeNav.value = "models";
  await refreshModels();
  if (modelId && models.value.some((m) => m.model_id === modelId)) {
    await selectModel(modelId);
  }
}

async function refreshDatasets() {
  datasetsLoading.value = true;
  try {
    const data = await getDatasets();
    datasets.value = data.items;
    if (!selectedDatasetId.value && data.items.length > 0) selectedDatasetId.value = data.items[0].id;
  } finally {
    datasetsLoading.value = false;
  }
}

async function refreshModels() {
  modelsLoadError.value = "";
  modelsLoading.value = true;
  try {
    const data = await getModels();
    models.value = data.items;
    if (data.items.length === 0) {
      selectedModelId.value = null;
      selectedModel.value = null;
      modelDetailError.value = "";
      return;
    }
    let saved: string | null = null;
    try {
      saved = sessionStorage.getItem(SESSION_MODEL_KEY);
    } catch {
      saved = null;
    }
    const inList = (id: string | null) => Boolean(id && data.items.some((m) => m.model_id === id));
    const keep =
      inList(selectedModelId.value) ? selectedModelId.value : inList(saved) ? saved! : null;
    const pick = keep || data.items[0].model_id;
    await selectModel(pick);
  } catch (e) {
    console.error("refreshModels failed", e);
    modelsLoadError.value = "failed";
  } finally {
    modelsLoading.value = false;
  }
}

function selectTask(jobId: string) {
  selectedTaskId.value = jobId;
  sessionCurrentTask.value[activeSessionId.value] = jobId;
  startPollingIfNeeded();
}

function cleanupDeletedJobState(jobId: string) {
  delete taskSessionOwner.value[jobId];
  for (const sid of Object.keys(sessionWorkflowCards.value)) {
    const keys = Object.keys(sessionWorkflowCards.value[sid] || {});
    for (const k of keys) {
      if (k.startsWith(`${jobId}:`)) delete sessionWorkflowCards.value[sid][k];
    }
  }
  for (const sid of Object.keys(sessionMessages.value)) {
    sessionMessages.value[sid] = (sessionMessages.value[sid] || []).filter((m) => m.workflowActionData?.job_id !== jobId);
  }
  if (selectedTaskId.value === jobId) {
    selectedTaskId.value = null;
    stopPolling();
  }
  for (const sid of Object.keys(sessionCurrentTask.value)) {
    if (sessionCurrentTask.value[sid] === jobId) sessionCurrentTask.value[sid] = null;
  }
}

async function onDeleteTask(jobIdRaw: string) {
  const jobId = String(jobIdRaw || "").trim();
  if (!jobId) return;
  const ok = window.confirm(t("app.confirm.deleteTask", { jobId }));
  if (!ok) return;
  traceWorkflow("delete_task_request", {
    active_session_id: activeSessionId.value,
    selected_task_id: selectedTaskId.value,
    job_id: jobId,
    owner_session_id: taskSessionOwner.value[jobId] || null,
  });
  const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));
  try {
    deletingTaskStatuses.value[jobId] = "deleting";
    let resp: { message?: string; job_id?: string } | null = null;
    try {
      resp = await deleteTask(jobId);
    } catch (e) {
      if (!(e instanceof ApiError) || e.code !== "TASK_DELETE_NOT_ALLOWED") throw e;
      // User-flow fallback: if delete is not allowed, cancel first, wait for a terminal state, then delete.
      deletingTaskStatuses.value[jobId] = "canceling";
      traceWorkflow("delete_task_cancel_then_delete", {
        job_id: jobId,
        reason: "TASK_DELETE_NOT_ALLOWED",
      });
      await cancelTask(jobId);
      for (let i = 0; i < 8; i += 1) {
        const st = await getTaskStatus(jobId);
        const sv = String(st.task.status || "");
        traceWorkflow("delete_task_wait_cancel_state", { job_id: jobId, poll_index: i, status: sv });
        if (sv === "canceled" || sv === "cancelled" || sv === "failed" || sv === "completed") break;
        await sleep(500);
      }
      deletingTaskStatuses.value[jobId] = "deleting";
      resp = await deleteTask(jobId);
    }
    traceWorkflow("delete_task_success", { job_id: jobId, message: resp?.message ?? "Task deleted successfully" });
    cleanupDeletedJobState(jobId);
    tasks.value = tasks.value.filter((t) => String(t.id) !== jobId);
    uiError.value = "";
  } catch (e) {
    const msg = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
    traceWorkflow("delete_task_failed", { job_id: jobId, error: msg });
    uiError.value = t("app.errors.deleteTaskFailed", { message: msg });
  } finally {
    const next = { ...deletingTaskStatuses.value };
    delete next[jobId];
    deletingTaskStatuses.value = next;
  }
}

function selectDataset(datasetId: string) {
  selectedDatasetId.value = datasetId;
}

function onSelectDatasetPage(datasetId: string) {
  selectedRegimen.value = null;
  selectDataset(datasetId);
}

function onDatasetsSectionChange(section: "data" | "regimens") {
  datasetsUiSection.value = section;
  if (section === "data") {
    selectedRegimen.value = null;
  } else {
    selectedDatasetId.value = null;
  }
}

function onSelectRegimen(regimen: RegimenRecord) {
  selectedRegimen.value = regimen;
}

function onRegimenPanelSaved(regimen: RegimenRecord) {
  selectedRegimen.value = regimen;
  regimenRefreshSignal.value += 1;
}

function onRegimenPanelDeleted(regimenId: string) {
  if (selectedRegimen.value?.regimen_id === regimenId) selectedRegimen.value = null;
  regimenRefreshSignal.value += 1;
}

function onOpenDatasetAccess(payload: { datasetId: string; mode: "preview" | "schema"; datasetLabel?: string }) {
  datasetAccessDialog.value = payload;
}

function onDatasetPreviewFailed(datasetId: string) {
  datasetPreviewUnavailable.value = { ...datasetPreviewUnavailable.value, [datasetId]: true };
}

function onRegimenEditRequest(r: RegimenRecord) {
  void focusRegimenEditor(r);
}

async function focusRegimenEditor(r: RegimenRecord) {
  if (activeNav.value !== "datasets") activeNav.value = "datasets";
  datasetsUiSection.value = "regimens";
  await nextTick();
  datasetsPageRef.value?.beginRegimenEdit?.(r);
}

async function onRegimenDeleteRequest(r: RegimenRecord) {
  const nameHint = r.regimen_name?.trim() ? r.regimen_name : r.regimen_id;
  if (!window.confirm(t("regimen.management.deleteConfirm", { name: nameHint }))) return;
  try {
    await deleteRegimen(r.regimen_id);
    onRegimenPanelDeleted(r.regimen_id);
    uiError.value = "";
  } catch (e) {
    uiError.value = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
  }
}

async function onDeleteDataset(datasetId: string) {
  const ok = window.confirm(t("app.confirm.deleteDataset"));
  if (!ok) return;
  try {
    await deleteDataset(datasetId);
    uiError.value = "";
    await refreshDatasets();
    if (selectedDatasetId.value === datasetId) {
      selectedDatasetId.value = datasets.value[0]?.id ?? null;
    }
  } catch (e) {
    uiError.value = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
  }
}

async function onContextModelEdit(modelId: string) {
  const id = String(modelId || "").trim();
  if (!id) return;
  if (activeNav.value !== "models") {
    activeNav.value = "models";
    await refreshModels();
  }
  await nextTick();
  pendingModelsPageOpenEditId.value = id;
}

async function onContextModelDelete(modelId: string) {
  const id = String(modelId || "").trim();
  if (!id) return;
  const m = models.value.find((x) => x.model_id === id);
  const label = String(m?.task_name || m?.display_name || id).trim();
  if (!window.confirm(t("app.confirm.removeModelFromRegistry", { label }))) return;
  try {
    await deleteModel(id);
    await onModelDeletedFromPage(id);
    uiError.value = "";
  } catch (e) {
    uiError.value = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
  }
}

async function onModelUpdatedFromPage() {
  await refreshModels();
}

async function onModelDeletedFromPage(modelId: string) {
  void modelId;
  await refreshModels();
}

async function selectModel(modelId: string) {
  selectedModelId.value = modelId;
  try {
    sessionStorage.setItem(SESSION_MODEL_KEY, modelId);
  } catch {
    /* ignore private mode etc. */
  }
  modelDetailError.value = "";
  selectedModel.value = null;
  try {
    const data = await getModelDetail(modelId);
    selectedModel.value = data.model as ModelMeta;
  } catch (e) {
    modelDetailError.value = e instanceof ApiError ? `${e.message} (${e.code})` : String(e);
    selectedModel.value = null;
  }
}

async function sendTrainCommandWithDataset(datasetId: string) {
  activeNav.value = "workbench";
  selectedDatasetId.value = datasetId;
  await onSend(t("chat.syntheticUser.trainSurvivalWithDataset", { datasetId }));
}

function newSession() {
  const id = `s_${Date.now()}`;
  const maxSlot = sessions.value.reduce((m, s) => Math.max(m, s.defaultSlot ?? 0), 0);
  sessions.value.unshift({
    id,
    created_at: new Date().toISOString(),
    defaultSlot: maxSlot + 1,
  });
  activeSessionId.value = id;
  sessionMessages.value[id] = [];
  activeNav.value = "workbench";
  latestChatData.value = null;
  uiError.value = "";
  actionConfirmError.value = null;
  selectedTaskId.value = null;
  sessionTaskAnnounce.value[id] = {};
  sessionWorkflowCards.value[id] = {};
  sessionCurrentTask.value[id] = null;
}

function selectSession(sessionId: string) {
  const prevNav = activeNav.value;
  const wfKeyBefore = confirmingWorkflowKey.value;

  if (wfKeyBefore) {
    const wfJob = wfKeyBefore.split("|")[0]?.trim();
    if (wfJob && taskSessionOwner.value[wfJob] && taskSessionOwner.value[wfJob] !== sessionId) {
      confirmingWorkflowKey.value = null;
      confirmingWorkflowSince.value = null;
    }
  }

  activeSessionId.value = sessionId;
  if (!sessionMessages.value[sessionId]) sessionMessages.value[sessionId] = [];
  if (!sessionTaskAnnounce.value[sessionId]) sessionTaskAnnounce.value[sessionId] = {};
  if (!sessionWorkflowCards.value[sessionId]) sessionWorkflowCards.value[sessionId] = {};
  if (!Object.prototype.hasOwnProperty.call(sessionCurrentTask.value, sessionId)) sessionCurrentTask.value[sessionId] = null;
  selectedTaskId.value = sessionCurrentTask.value[sessionId] || null;
  activeNav.value = "workbench";
  latestChatData.value = null;
  uiError.value = "";
  actionConfirmError.value = null;

  if (!chatTurnInFlight.value) {
    shellRecoveryBanner.value = "";
    shellStaleDetected.value = false;
  }

  /** Same as navigating onto Workbench from Tasks/Data/etc.: refresh tasks + workflow cards when only activeSessionId changes. */
  if (prevNav === "workbench") {
    void refreshTasks();
  }
}

function sessionOwnedJobs(sessionId: string): string[] {
  return Object.entries(taskSessionOwner.value)
    .filter(([, sid]) => sid === sessionId)
    .map(([jobId]) => jobId);
}

function shouldPollJob(jobId: string): boolean {
  const t = tasks.value.find((x) => String(x.id) === jobId);
  if (!t) return true;
  const st = String(t.status || "").toLowerCase();
  const jt = String((t as { job_type?: string }).job_type || "").toLowerCase();
  // Train jobs often stay `waiting_user` until Phase-4 work starts; skipping polls hides running/failed transitions.
  if (st === "waiting_user" && jt === "train_model") return true;
  if (st === "waiting_user") return false;
  return st !== "completed" && st !== "failed" && st !== "canceled" && st !== "cancelled";
}

async function pollStatus() {
  const ownedJobs = sessionOwnedJobs(activeSessionId.value).filter((jobId) => shouldPollJob(jobId));
  const selectedJobs =
    selectedTaskId.value && shouldPollJob(selectedTaskId.value) ? [selectedTaskId.value] : [];
  const jobs = Array.from(new Set([...ownedJobs, ...selectedJobs]));
  if (jobs.length === 0) return;
  traceWorkflow("poll_tick_jobs", {
    active_session_id: activeSessionId.value,
    selected_task_id: selectedTaskId.value,
    owned_job_ids: ownedJobs,
    polling_job_ids: jobs,
  });
  for (const taskId of jobs) {
    try {
    const status = await getTaskStatus(taskId);
    traceWorkflow("poll_status", {
      active_session_id: activeSessionId.value,
      job_id: taskId,
      owner_session_id: taskSessionOwner.value[taskId] || null,
      status: String(status.task.status || ""),
      stage: String(status.task.current_stage || ""),
      is_waiting_user: String(status.task.status || "") === "waiting_user",
    });
    const idx = tasks.value.findIndex((t) => String(t.id) === taskId);
    const polled = status.task as Record<string, unknown>;
    if (idx >= 0) {
      tasks.value[idx] = { ...(tasks.value[idx] as Record<string, unknown>), ...polled } as TaskItem &
        Record<string, unknown>;
    } else {
      const merged = {
        id: taskId,
        status: String(polled.status ?? ""),
        progress: Number(polled.progress ?? 0),
        current_stage: String(polled.current_stage ?? ""),
        message: String(polled.message ?? ""),
        job_type: String(polled.job_type ?? ""),
        error_message: polled.error_message ?? null,
        created_at: String(polled.created_at ?? ""),
        started_at: polled.started_at ?? null,
        completed_at: polled.completed_at ?? null,
      } as TaskItem & Record<string, unknown>;
      tasks.value = [merged, ...tasks.value.filter((t) => String(t.id) !== taskId)];
    }
    const rowAfterPoll = tasks.value.find((t) => String(t.id) === taskId);
    const jobTypeForPoll = String(
      (rowAfterPoll as { job_type?: string } | undefined)?.job_type ||
        (status.task as { job_type?: string }).job_type ||
        "",
    );
    const ownerSession = taskSessionOwner.value[taskId];
    if (ownerSession) {
      if (!sessionCurrentTask.value[ownerSession]) sessionCurrentTask.value[ownerSession] = taskId;
      if (!sessionTaskAnnounce.value[ownerSession]) sessionTaskAnnounce.value[ownerSession] = {};
      const prev = sessionTaskAnnounce.value[ownerSession][taskId] || {};
      const nextStatus = String(status.task.status || "");
      const nextStage = String(status.task.current_stage || "");
      if (shouldAnnounceTransition(prev, nextStatus, nextStage)) {
        const msg = getJobProgressMessage({ ...status.task, job_type: jobTypeForPoll || undefined }, t);
        if (msg) {
          if (jobTypeForPoll === "train_model") {
            const nk = trainPollNarrativeKey(ownerSession, taskId, nextStage);
            if (!sessionTrainNarrativeKeys.value[nk]) {
              sessionTrainNarrativeKeys.value = { ...sessionTrainNarrativeKeys.value, [nk]: true };
              pushMsgToSession(ownerSession, "assistant", msg, null, null, "status");
            }
          } else {
            pushMsgToSession(ownerSession, "assistant", msg, null, null, "status");
          }
        }
      }
      sessionTaskAnnounce.value[ownerSession][taskId] = {
        ...prev,
        lastStatus: nextStatus,
        lastStage: nextStage,
      };
    }

    // When the task is waiting_user in phase3/4/5, auto-insert the pending confirmation card into chat.
    if (String(status.task.status || "") === "waiting_user") {
      await maybeInsertWorkflowCard(taskId);
    }

    const st = status.task.status;
    if (st === "completed" || st === "failed" || st === "canceled" || st === "cancelled") {
      await refreshTasks();
      const ownerSession = taskSessionOwner.value[taskId];
      const jtTerminal = String(
        (tasks.value.find((t) => String(t.id) === taskId) as { job_type?: string } | undefined)?.job_type ||
          jobTypeForPoll ||
          "",
      );
      if (ownerSession) {
        const prev = sessionTaskAnnounce.value[ownerSession]?.[taskId] || {};
        if (!prev.isTerminalAnnounced) {
          if (st === "completed") {
            const detail = await getTaskDetail(taskId);
            /** Prefer task detail after fetch: tasks list rows can briefly lack `job_type`, which mis-routed terminal copy and produced a text bubble plus the same training result card. */
            const effectiveJobType = String(
              (detail.task as { job_type?: string } | undefined)?.job_type || jtTerminal || "",
            ).trim();
            void refreshModels();
            if (effectiveJobType === "predict_outcome") {
              const pred = taskDetailToPredictionSingleResponse(detail, t);
              pushMsgToSession(
                ownerSession,
                "assistant",
                getTerminalCompletionAssistantMessage(detail, t),
                null,
                null,
                "status",
                null,
                null,
                pred,
              );
            } else if (effectiveJobType === "recommend_regimen") {
              const rec = await loadRecommendationFromTaskDetail(detail);
              if (rec) {
                pushMsgToSession(
                  ownerSession,
                  "assistant",
                  "",
                  null,
                  null,
                  "status",
                  null,
                  null,
                  null,
                  null,
                  null,
                  null,
                  null,
                  rec,
                );
              } else {
                pushMsgToSession(
                  ownerSession,
                  "assistant",
                  t("recommendation.narrative.completedArtifactMissing"),
                  null,
                  null,
                  "status",
                );
              }
              patchRecommendationWorkflowCardByJobId(ownerSession, taskId, { status: "completed" });
              sessionCurrentTask.value[ownerSession] = taskId;
              if (activeSessionId.value === ownerSession) {
                selectedTaskId.value = taskId;
              }
            } else {
              if (effectiveJobType === "train_model" && hasTrainingWorkflowCardForTask(ownerSession, taskId)) {
                patchTrainingWorkflowCardForCompletedJob(ownerSession, taskId, detail);
              } else {
                const assistantLine =
                  effectiveJobType === "train_model" ? "" : getTerminalCompletionAssistantMessage(detail, t);
                const ownerMsgs = sessionMessages.value[ownerSession] || [];
                const dupTrainCard =
                  effectiveJobType === "train_model" &&
                  sessionChatHasTrainCompletionResult(ownerMsgs, taskId);
                if (dupTrainCard) {
                  traceWorkflow("poll_skip_duplicate_train_completion_card", {
                    job_id: taskId,
                    owner_session_id: ownerSession,
                  });
                } else {
                  pushMsgToSession(
                    ownerSession,
                    "assistant",
                    assistantLine,
                    null,
                    null,
                    "status",
                    buildCompletionCard(detail, t),
                  );
                }
              }
            }
          } else if (st === "failed") {
            const reason = String(status.task.error_message || status.task.message || "").trim();
            const maskedReason = sanitizeUserFacingLine(reason, t);
            if (jtTerminal === "predict_outcome") {
              const pfx = getTerminalFailureAssistantPrefix(jtTerminal, t);
              const shortReason = maskedReason ? `${pfx}${maskedReason}` : `${pfx.replace(/[:\uFF1A]$/, "")}.`;
              pushMsgToSession(ownerSession, "assistant", shortReason, null, null, "error");
            } else if (jtTerminal === "recommend_regimen") {
              const pfx = getTerminalFailureAssistantPrefix(jtTerminal, t);
              const shortReason = maskedReason ? `${pfx}${maskedReason}` : `${pfx.replace(/[:\uFF1A]$/, "")}.`;
              pushMsgToSession(ownerSession, "assistant", shortReason, null, null, "error");
              patchRecommendationWorkflowCardByJobId(ownerSession, taskId, { status: "failed", pollError: maskedReason });
              sessionCurrentTask.value[ownerSession] = taskId;
              if (activeSessionId.value === ownerSession) {
                selectedTaskId.value = taskId;
              }
            } else {
              const pfx = getTerminalFailureAssistantPrefix(jtTerminal, t);
              const shortReason = maskedReason ? `${pfx}${maskedReason}` : `${pfx.replace(/[:\uFF1A]$/, "")}.`;
              pushMsgToSession(ownerSession, "assistant", shortReason, null, null, "error", buildFailureCard(status.task, t));
            }
          } else if (st === "canceled" || st === "cancelled") {
            pushMsgToSession(ownerSession, "assistant", getTerminalCanceledAssistantMessage(jtTerminal, t), null, null, "status");
            if (jtTerminal === "recommend_regimen") {
              patchRecommendationWorkflowCardByJobId(ownerSession, taskId, { status: "cancelled" });
            }
          }
          sessionTaskAnnounce.value[ownerSession][taskId] = {
            ...prev,
            isTerminalAnnounced: true,
            lastStatus: String(status.task.status || ""),
            lastStage: String(status.task.current_stage || ""),
          };
        }
      }
    }
    } catch {
    }
  }
}

function currentTaskStatus(): string | null {
  if (!selectedTaskId.value) return null;
  const task = tasks.value.find((t) => String(t.id) === selectedTaskId.value);
  return task?.status ? String(task.status) : null;
}

function stopPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function startPollingIfNeeded() {
  if (pollingTimer !== null) return;
  pollingTimer = window.setInterval(pollStatus, 2500);
}

onMounted(async () => {
  // Restore session/job binding early so waiting_user chat cards can come back after refresh.
  tryRestoreSessionState();
  selectedTaskId.value = sessionCurrentTask.value[activeSessionId.value] || selectedTaskId.value;
  await Promise.all([refreshTasks(), refreshDatasets(), refreshModels()]);
  startPollingIfNeeded();
  shellWatchdogTimer = window.setInterval(runShellWatchdogTick, 15_000);
  // On first load: if selectedTaskId already points at a waiting_user task, try to restore its chat confirmation card.
  if (selectedTaskId.value) {
    try {
      await maybeInsertWorkflowCard(selectedTaskId.value);
    } catch {
      /* ignore */
    }
  }
  traceWorkflow("mounted_ready", {
    active_session_id: activeSessionId.value,
    selected_job_id: selectedTaskId.value,
    owner_count: Object.keys(taskSessionOwner.value).length,
  });
});

onUnmounted(() => {
  stopPolling();
  if (shellWatchdogTimer !== null) {
    window.clearInterval(shellWatchdogTimer);
    shellWatchdogTimer = null;
  }
});

watch(confirmingWorkflowKey, (v) => {
  confirmingWorkflowSince.value = v ? Date.now() : null;
});

watch(selectedTaskId, () => {
  stopPolling();
  startPollingIfNeeded();
});

watch(activeNav, async (nav) => {
  if (nav !== "datasets") {
    selectedRegimen.value = null;
    datasetsUiSection.value = "data";
  }
  if (nav === "datasets") await refreshDatasets();
  if (nav === "models") await refreshModels();
  if (nav === "tasks" || nav === "workbench") await refreshTasks();
});

watch(
  [selectedTaskId, activeNav, () => tasks.value.find((x) => String(x.id) === String(selectedTaskId.value || ""))?.status],
  () => {
    void ensureTaskDetailForSelectedWaitingTask();
  },
);

watch(
  () => [
    sessions.value,
    activeSessionId.value,
    sessionMessages.value,
    taskSessionOwner.value,
    sessionWorkflowCards.value,
    sessionCurrentTask.value,
    sessionTaskAnnounce.value,
    sessionTrainNarrativeKeys.value,
  ],
  () => persistSessionState(),
  { deep: true },
);

</script>

<style scoped>
.wb-main-stack {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.wb-shell-recovery-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wb-space-2);
  padding: var(--wb-space-2) var(--wb-space-3);
  border-bottom: 1px solid var(--wb-border);
  background: var(--wb-surface-soft);
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-secondary);
}
.wb-shell-manual-recovery {
  padding: 0 var(--wb-space-3) var(--wb-space-2);
}
.wb-main-outlet {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: var(--wb-space-6) var(--wb-space-5);
  box-sizing: border-box;
}

.wb-main-outlet--workspace {
  padding: 0;
}
</style>

