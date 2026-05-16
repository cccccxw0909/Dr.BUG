<template>
  <div class="workbench-page" data-testid="workbench-root">
    <div class="workbench-main">
      <!-- Single scroll column for welcome + chat / workflow embeds (scrollbar at workspace edge). -->
      <div
        class="workbench-center-scroll"
        :class="{ 'workbench-center-scroll--has-chat': workbenchLayout.showChatSurface }"
      >
        <!-- Welcome intro: static copy, not part of session.messages; may stay visible after the first user turn (session flag). -->
        <div v-if="keepWelcomeIntro" class="workbench-welcome-rail workbench-center-rail">
          <section class="workbench-welcome-section">
            <div class="workbench-welcome-flow">
              <h3 class="workbench-welcome-title">{{ $t("pages.workbench.welcomeTitle") }}</h3>
              <p class="workbench-welcome-body workbench-welcome-body-lead">
                {{ $t("pages.workbench.welcomeOverview") }}
              </p>
              <h4 class="workbench-welcome-subtitle">{{ $t("pages.workbench.capabilities.title") }}</h4>
              <ul class="workbench-welcome-list">
                <li>{{ $t("pages.workbench.capabilities.item1") }}</li>
                <li>{{ $t("pages.workbench.capabilities.item2") }}</li>
                <li>{{ $t("pages.workbench.capabilities.item3") }}</li>
              </ul>
              <h4 class="workbench-welcome-subtitle">{{ $t("pages.workbench.getStarted.title") }}</h4>
              <p class="workbench-welcome-body workbench-welcome-body-gap">{{ $t("pages.workbench.getStarted.body") }}</p>
              <h4 class="workbench-welcome-subtitle">{{ $t("pages.workbench.boundary.title") }}</h4>
              <p class="workbench-welcome-body workbench-welcome-body-trailing">
                {{ $t("pages.workbench.boundary.body") }}
              </p>
            </div>
            <template v-if="workbenchLayout.showQuickEntry">
              <h4 class="workbench-quick-entry-heading">{{ $t("pages.workbench.quickEntry.title") }}</h4>
              <div class="workbench-action-list">
                <button type="button" class="workbench-action-card" @click="sendTrainingQuickEntry">
                  <span class="workbench-action-card-main">
                    <span class="workbench-action-title">{{ $t("pages.workbench.quickEntry.training.title") }}</span>
                    <span class="workbench-action-desc">{{ $t("pages.workbench.quickEntry.training.description") }}</span>
                  </span>
                  <span class="workbench-action-affordance">
                    <span class="workbench-action-chip">{{ $t("pages.workbench.quickEntry.actionLabel") }}</span>
                  </span>
                </button>

                <button type="button" class="workbench-action-card" @click="$emit('startPrediction')">
                  <span class="workbench-action-card-main">
                    <span class="workbench-action-title">{{ $t("pages.workbench.quickEntry.prediction.title") }}</span>
                    <span class="workbench-action-desc">{{ $t("pages.workbench.quickEntry.prediction.description") }}</span>
                  </span>
                  <span class="workbench-action-affordance">
                    <span class="workbench-action-chip">{{ $t("pages.workbench.quickEntry.actionLabel") }}</span>
                  </span>
                </button>

                <button type="button" class="workbench-action-card" @click="$emit('startRecommendation')">
                  <span class="workbench-action-card-main">
                    <span class="workbench-action-title">{{ $t("pages.workbench.quickEntry.recommendation.title") }}</span>
                    <span class="workbench-action-desc">{{ $t("pages.workbench.quickEntry.recommendation.description") }}</span>
                  </span>
                  <span class="workbench-action-affordance">
                    <span class="workbench-action-chip">{{ $t("pages.workbench.quickEntry.actionLabel") }}</span>
                  </span>
                </button>
              </div>
            </template>
          </section>
        </div>

        <div
          v-if="workbenchLayout.showChatSurface"
          ref="chatSurfaceEl"
          class="workbench-chat-section workbench-chat-section--full-bleed"
          :class="{ 'workbench-chat-section--below-intro': keepWelcomeIntro }"
        >
          <div class="workbench-chat-rail">
            <ChatMessageList
              :messages="messages"
              :context-dataset-id="contextDatasetId"
              :submitting-pending-action-id="submittingPendingActionId ?? null"
              :action-confirm-error="actionConfirmError ?? null"
              :recovery-workflow-card="recoveryWorkflowCard ?? null"
              @confirm-action="$emit('confirm', $event)"
              @confirm-workflow="$emit('confirmWorkflow', $event)"
              @edit-params="$emit('editParams', $event)"
              @go-task="$emit('goTask', $event)"
              @go-model="$emit('goModel', $event)"
              @start-prediction="$emit('startPrediction', $event)"
              @prediction-form-action="$emit('predictionFormAction', $event)"
              @batch-prediction-action="$emit('batchPredictionAction', $event)"
              @recommendation-workflow-action="$emit('recommendationWorkflowAction', $event)"
              @request-cancel-training-job="$emit('requestCancelTrainingJob', $event)"
            />
          </div>
        </div>
      </div>

      <div
        class="workbench-composer"
        :class="{
          'workbench-composer--compact': workbenchLayout.compactInputChrome,
        }"
      >
        <div class="workbench-composer-inner workbench-composer-rail workbench-center-rail">
          <ChatInputBox
            :placeholder="$t('pages.workbench.chat.placeholder')"
            :send-label="$t('pages.workbench.chat.send')"
            @send="$emit('send', $event)"
          />
        </div>
      </div>
    </div>

    <div v-if="uiError" class="workbench-error">{{ uiError }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import ChatInputBox from "../components/chat/ChatInputBox.vue";
import ChatMessageList from "../components/chat/ChatMessageList.vue";
import type {
  BatchPredictionCardData,
  BatchPredictionChatAction,
  BatchPredictionRunResponse,
  ChatTurnData,
  DatasetMeta,
  PredictionFormCardData,
  PredictionFormChatAction,
  PredictionSubmittedSummaryPayload,
  RecommendationWorkflowChatAction,
  PredictionSingleResponse,
  TaskResultCardData,
  TrainingJobReceiptData,
  TrainingWorkflowPendingActionData,
} from "../types";

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
  predictionSubmittedSummary?: PredictionSubmittedSummaryPayload | null;
  recommendationWorkflowCard?: import("../types").RecommendationWorkflowCardData | null;
  recommendationResult?: import("../types").SurvivalRecommendationResult | null;
};

const props = defineProps<{
  messages: MessageItem[];
  /** When true, render the static welcome intro (not from messages); parent ties this to session UI flags. */
  keepWelcomeIntro: boolean;
  selectedDataset: DatasetMeta | null;
  contextDatasetId?: string | null;
  uiError: string;
  submittingPendingActionId?: string | null;
  actionConfirmError?: { pendingActionId: string; message: string } | null;
  /** When chat messages missed persisting a workflow card, render from task detail (same mapping as the status panel). */
  recoveryWorkflowCard?: TrainingWorkflowPendingActionData | null;
}>();

/**
 * Chat surface = message rows and/or recovery card. Quick entry cards hide once the session has any chat row.
 */
const workbenchLayout = computed(() => {
  const hasRows = props.messages.length > 0;
  const hasRecovery = Boolean(props.recoveryWorkflowCard);
  const showChatSurface = hasRows || hasRecovery;
  return {
    showQuickEntry: !hasRows && !hasRecovery,
    showChatSurface,
    compactInputChrome: !hasRows && !hasRecovery,
  };
});

const chatSurfaceEl = ref<HTMLElement | null>(null);

watch(
  () => props.messages.length,
  async (nextLen, prevLen) => {
    if (prevLen !== 0 || nextLen <= 0 || !props.keepWelcomeIntro) return;
    await nextTick();
    chatSurfaceEl.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  },
);

const { t } = useI18n();

const emit = defineEmits<{
  (e: "send", text: string): void;
  (e: "confirm", detail?: { patient_features?: Record<string, unknown> }): void;
  (e: "editParams", payload: { updatedParams: Record<string, unknown>; missingFields: string[] }): void;
  (e: "confirmWorkflow", payload: Record<string, unknown>): void;
  (e: "goTask", jobId: string): void;
  (e: "goModel", modelId: string): void;
  (e: "startPrediction", payload?: { modelId?: string }): void;
  (e: "startRecommendation"): void;
  (e: "recommendationWorkflowAction", payload: RecommendationWorkflowChatAction): void;
  (e: "predictionFormAction", payload: PredictionFormChatAction): void;
  (e: "batchPredictionAction", payload: BatchPredictionChatAction): void;
  (e: "requestCancelTrainingJob", payload: { job_id: string }): void;
}>();

function sendTrainingQuickEntry() {
  emit("send", t("pages.workbench.quickEntry.training.sendPhrase"));
}
</script>

<style scoped>
.workbench-page {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.workbench-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0;
  background: transparent;
}

.workbench-center-rail,
.workbench-composer-rail {
  width: min(100%, var(--workbench-content-max-width));
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
}

.workbench-chat-rail {
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
}

/** Welcome home rail wrapper (keeps existing gaps/flow). */
.workbench-welcome-rail {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-5);
}

.workbench-center-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 24px 28px 0;
  box-sizing: border-box;
}

/** Chat: keep the same scroll padding; rails control inner width. */
.workbench-center-scroll--has-chat {
  padding-left: 28px;
  padding-right: 28px;
}

.workbench-chat-section--full-bleed {
  width: 100%;
  max-width: none;
  margin: 0;
  min-width: 0;
  box-sizing: border-box;
}

/** Space between pinned welcome intro and the chat list (intro stays in DOM above). */
.workbench-chat-section--below-intro {
  margin-top: var(--wb-space-5);
}

.workbench-composer {
  flex: 0 0 auto;
  min-height: 0;
  padding: 12px 28px 16px;
  border-top: 1px solid var(--wb-border-subtle);
  background: var(--wb-surface);
  box-sizing: border-box;
}

.workbench-composer-inner {
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
}

.workbench-composer--compact :deep(.chat-input) {
  gap: 0;
}

.workbench-composer--compact :deep(.chat-input-row) {
  gap: var(--wb-space-2);
}

/* Welcome: single column; aligns with Quick entry rail. */
.workbench-welcome-flow {
  text-align: left;
  width: 100%;
}

.workbench-welcome-title {
  margin: 0 0 12px;
  font-size: 20px;
  line-height: 1.35;
  font-weight: 650;
  color: var(--wb-text-primary);
}

.workbench-welcome-body {
  margin: 0;
  font-size: var(--wb-font-size-sm);
  line-height: 1.55;
  font-weight: 400;
  color: var(--wb-text-primary);
}

.workbench-welcome-body-lead {
  margin: 0 0 16px;
}

.workbench-welcome-body-gap {
  margin: 0 0 16px;
}

.workbench-welcome-body-trailing {
  margin: 0 0 20px;
}

.workbench-welcome-subtitle {
  margin: 0 0 8px;
  font-size: var(--wb-font-size-sm);
  line-height: 1.42;
  font-weight: 575;
  color: var(--wb-text-primary);
}

.workbench-welcome-list {
  margin: 0 0 16px;
  padding-left: 1.125rem;
  font-size: var(--wb-font-size-sm);
  line-height: 1.55;
  font-weight: 400;
  color: var(--wb-text-primary);
  list-style-position: outside;
  display: grid;
  gap: 5px;
}

.workbench-welcome-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.workbench-quick-entry-heading {
  margin: 0 0 8px;
  font-size: var(--wb-detail-section-title-size);
  font-weight: var(--wb-detail-section-title-weight);
  line-height: 1.42;
  color: var(--wb-text-primary);
}

.workbench-action-list {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
}

.workbench-action-card {
  min-height: var(--wb-action-card-min-height);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--wb-space-2);
  text-align: left;
  padding: var(--wb-space-3);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface);
  color: var(--wb-text-primary);
  cursor: pointer;
  box-shadow: none;
  transition:
    border-color 140ms ease,
    background-color 140ms ease,
    box-shadow 140ms ease;
}

.workbench-action-card-main {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-1);
  align-items: flex-start;
  min-width: 0;
  flex: 1;
}

.workbench-action-affordance {
  flex-shrink: 0;
  align-self: center;
  margin-left: var(--wb-space-2);
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}

.workbench-action-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.25;
  white-space: nowrap;
  border-radius: 999px;
  border: 1px solid #d8dee8;
  color: #475569;
  background: transparent;
  pointer-events: none;
  transition:
    border-color 120ms ease,
    color 120ms ease,
    background-color 120ms ease;
}

.workbench-action-card:hover {
  border-color: #c5d0dc;
  background: #f8fafc;
}

.workbench-action-card:hover .workbench-action-chip {
  border-color: #c5ced9;
  color: var(--wb-accent);
  background: rgba(255, 255, 255, 0.65);
}

.workbench-action-card:active {
  border-color: #b9c6d6;
  background: #f3f6f9;
}

.workbench-action-title {
  font-size: var(--wb-font-size-sm);
  font-weight: 600;
}

.workbench-action-title-row {
  display: inline-flex;
  align-items: center;
  gap: var(--wb-space-1);
}

.workbench-action-badge {
  display: inline-flex;
  align-items: center;
  height: var(--wb-chip-height-sm);
  padding: 0 var(--wb-chat-shell-gap);
  border: 1px solid #d6deea;
  border-radius: 999px;
  font-size: var(--wb-font-size-micro);
  font-weight: 560;
  color: #5f6f83;
  background: #f4f7fb;
  line-height: 1;
}

.workbench-action-desc {
  color: var(--wb-text-primary);
  opacity: 0.78;
  font-size: var(--wb-font-size-xs);
  line-height: 1.45;
}

.workbench-chat-section {
  min-width: 0;
  width: 100%;
}

.workbench-error {
  margin-top: var(--wb-space-1);
  color: var(--wb-error);
  font-size: var(--wb-font-size-sm);
}
</style>
