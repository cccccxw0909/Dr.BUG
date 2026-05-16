<template>
  <div class="chat-message-list">
    <div v-if="messages.length === 0 && !recoveryWorkflowCard" class="chat-empty">{{ i18nT("chat.messageList.emptyState") }}</div>
    <div
      v-for="m in messages"
      :key="m.id"
      class="chat-row"
      :class="m.role === 'user' ? 'chat-row-user' : 'chat-row-assistant'"
    >
      <div v-if="m.role !== 'user'" class="chat-avatar-slot chat-avatar-slot-start">
        <span class="chat-avatar chat-avatar-assistant" aria-hidden="true">AI</span>
      </div>

      <div class="chat-thread" :class="m.role === 'user' ? 'chat-thread-user' : 'chat-thread-assistant'">
        <div class="chat-message-shell" :class="messageShellClass(m)">
          <div
            v-if="showAssistantBubble(m)"
            class="chat-bubble"
            :class="[bubbleClass(m), { 'chat-bubble-compact': m.role === 'user' && isCompactUserMessage(m.text) }]"
          >
            <span class="chat-text">{{ assistantBubbleText(m) }}</span>
          </div>
        </div>

        <div
          v-if="
            m.role === 'assistant' &&
            m.actionData &&
            m.actionData.route === 'deterministic_action' &&
            m.actionData.recognized_action !== 'draft_single_prediction'
          "
          class="chat-embed-card"
        >
          <SafeWorkflowEmbed>
            <AssistantActionCard
              embedded
              :data="m.actionData"
              :context-dataset-id="contextDatasetId"
              :submitting-action-id="submittingPendingActionId ?? null"
              :action-confirm-error="actionConfirmError ?? null"
              @confirm="$emit('confirmAction', $event)"
              @edit-params="$emit('editParams', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
        <div
          v-if="m.role === 'assistant' && m.actionData && m.actionData.route === 'tool_query'"
          class="chat-tool-query"
        >
          <div class="chat-tool-query-title">{{ i18nT("chat.messageList.toolQueryTitle") }}</div>
          <div v-if="(m.actionData.readonly_query_labels || []).length" class="chat-tool-labels">
            <span
              v-for="(lab, i) in m.actionData.readonly_query_labels || []"
              :key="i"
              class="chat-tool-label"
              >{{ lab }}</span>
          </div>
          <div v-else class="chat-tool-empty">{{ i18nT("chat.messageList.noTags") }}</div>
        </div>
        <div
          v-if="m.role === 'assistant' && m.actionData && m.actionData.route === 'fallback_template'"
          class="chat-fallback"
        >
          <b>{{ i18nT("chat.messageList.fallbackPrompt") }}</b>{{ i18nT("chat.narrative.fallbackNoExecutableTask") }}
        </div>
        <div v-if="m.role === 'assistant' && m.workflowActionData" class="chat-embed-card">
          <SafeWorkflowEmbed>
            <TrainingWorkflowActionCard
              embedded
              :data="m.workflowActionData"
              @confirm="$emit('confirmWorkflow', $event)"
              @request-cancel-job="$emit('requestCancelTrainingJob', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
        <div v-if="m.role === 'assistant' && m.resultData" class="chat-embed-card">
          <SafeWorkflowEmbed>
            <TaskResultCard
              embedded
              :data="m.resultData"
              @go-task="$emit('goTask', $event)"
              @go-model="$emit('goModel', $event)"
              @start-prediction="$emit('startPrediction', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
        <div v-if="m.role === 'assistant' && m.trainingReceiptData" class="chat-embed-card">
          <TrainingJobReceiptCard embedded :data="m.trainingReceiptData" />
        </div>
        <div
          v-if="m.role === 'assistant' && m.predictionFormCard && m.predictionFormCard.status !== 'submitted'"
          class="chat-embed-card"
        >
          <SafeWorkflowEmbed>
            <PredictionFormChatCard
              :card="m.predictionFormCard"
              @action="$emit('predictionFormAction', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
        <div v-if="m.role === 'assistant' && m.predictionSubmittedSummary" class="chat-embed-card">
          <PredictionSubmittedSummaryCard :data="m.predictionSubmittedSummary" />
        </div>
        <div v-if="m.role === 'assistant' && m.predictionResult" class="chat-embed-card">
          <PredictionResultCard :data="m.predictionResult" />
        </div>
        <div v-if="m.role === 'assistant' && m.batchPredictionCard" class="chat-embed-card">
          <SafeWorkflowEmbed>
            <BatchPredictionChatCard
              :card="m.batchPredictionCard"
              @action="$emit('batchPredictionAction', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
        <div v-if="m.role === 'assistant' && m.batchPredictionResult" class="chat-embed-card">
          <BatchPredictionResultCard :data="m.batchPredictionResult" />
        </div>
        <div v-if="m.role === 'assistant' && m.recommendationWorkflowCard" class="chat-embed-rec-primary">
          <SafeWorkflowEmbed>
            <RecommendationWorkflowChatCard
              embedded
              :card="m.recommendationWorkflowCard"
              @action="$emit('recommendationWorkflowAction', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
        <div v-if="m.role === 'assistant' && m.recommendationResult" class="chat-embed-rec-primary">
          <RecommendationResultCard :data="m.recommendationResult" />
        </div>
      </div>

      <div v-if="m.role === 'user'" class="chat-avatar-slot chat-avatar-slot-end">
        <span class="chat-avatar chat-avatar-user" aria-hidden="true">U</span>
      </div>
    </div>

    <div v-if="recoveryWorkflowCard" class="chat-row chat-row-assistant chat-row-recovery">
      <div class="chat-avatar-slot chat-avatar-slot-start">
        <span class="chat-avatar chat-avatar-assistant" aria-hidden="true">AI</span>
      </div>
      <div class="chat-thread chat-thread-assistant">
        <div class="chat-embed-card">
          <SafeWorkflowEmbed>
            <TrainingWorkflowActionCard
              embedded
              :data="recoveryWorkflowCard"
              @confirm="$emit('confirmWorkflow', $event)"
              @request-cancel-job="$emit('requestCancelTrainingJob', $event)"
            />
          </SafeWorkflowEmbed>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { useI18n } from "vue-i18n";
import SafeWorkflowEmbed from "./SafeWorkflowEmbed.vue";
import AssistantActionCard from "./AssistantActionCard.vue";
import BatchPredictionChatCard from "./BatchPredictionChatCard.vue";
import BatchPredictionResultCard from "./BatchPredictionResultCard.vue";
import PredictionFormChatCard from "./PredictionFormChatCard.vue";
import PredictionResultCard from "./PredictionResultCard.vue";
import PredictionSubmittedSummaryCard from "./PredictionSubmittedSummaryCard.vue";
import RecommendationResultCard from "./RecommendationResultCard.vue";
import RecommendationWorkflowChatCard from "./RecommendationWorkflowChatCard.vue";
import TrainingWorkflowActionCard from "./TrainingWorkflowActionCard.vue";
import TaskResultCard from "./TaskResultCard.vue";
import TrainingJobReceiptCard from "./TrainingJobReceiptCard.vue";
import type {
  ChatTurnData,
  BatchPredictionCardData,
  BatchPredictionChatAction,
  BatchPredictionRunResponse,
  PredictionFormCardData,
  PredictionFormChatAction,
  PredictionSubmittedSummaryPayload,
  RecommendationWorkflowCardData,
  RecommendationWorkflowChatAction,
  PredictionSingleResponse,
  SurvivalRecommendationResult,
  TaskResultCardData,
  TrainingJobReceiptData,
  TrainingWorkflowPendingActionData,
} from "../../types";

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
  predictionSubmittedSummary?: PredictionSubmittedSummaryPayload | null;
  predictionFormCard?: PredictionFormCardData | null;
  batchPredictionCard?: BatchPredictionCardData | null;
  batchPredictionResult?: BatchPredictionRunResponse | null;
  recommendationWorkflowCard?: RecommendationWorkflowCardData | null;
  recommendationResult?: SurvivalRecommendationResult | null;
};

defineEmits<{
  (e: "confirmAction", detail?: { patient_features?: Record<string, unknown> }): void;
  (e: "editParams", payload: { updatedParams: Record<string, unknown>; missingFields: string[] }): void;
  (e: "confirmWorkflow", payload: Record<string, unknown>): void;
  (e: "goTask", jobId: string): void;
  (e: "goModel", modelId: string): void;
  (e: "startPrediction", payload?: { modelId?: string }): void;
  (e: "predictionFormAction", payload: PredictionFormChatAction): void;
  (e: "batchPredictionAction", payload: BatchPredictionChatAction): void;
  (e: "recommendationWorkflowAction", payload: RecommendationWorkflowChatAction): void;
  (e: "requestCancelTrainingJob", payload: { job_id: string }): void;
}>();

const props = defineProps<{
  messages: MessageItem[];
  contextDatasetId?: string | null;
  submittingPendingActionId?: string | null;
  actionConfirmError?: { pendingActionId: string; message: string } | null;
  recoveryWorkflowCard?: TrainingWorkflowPendingActionData | null;
}>();

const { t: i18nT } = useI18n();

watch(
  () => props.messages,
  (msgs) => {
    const workflowMsgs = msgs.filter((m) => m.role === "assistant" && m.workflowActionData);
    if (workflowMsgs.length === 0) return;
    const last = workflowMsgs[workflowMsgs.length - 1];
    console.info("[workflow-bridge] chat_list_received_workflow_message", {
      total_messages: msgs.length,
      workflow_message_count: workflowMsgs.length,
      job_id: last.workflowActionData?.job_id || null,
      phase: last.workflowActionData?.phase || null,
      card_id: last.workflowActionData?.card_id || null,
    });
  },
  { deep: true },
);

function bubbleClass(m: MessageItem): string {
  if (m.role === "user") return "chat-bubble-user";
  if (m.kind === "status") return "chat-bubble-status";
  if (m.kind === "error") return "chat-bubble-error";
  const ad = m.actionData;
  if (
    ad?.route === "deterministic_action" &&
    (ad.recognized_action === "draft_training_job" || ad.recognized_action === "create_training_job")
  ) {
    return "chat-bubble-assistant chat-bubble-workflow-guide";
  }
  return "chat-bubble-assistant";
}

function messageShellClass(m: MessageItem): string {
  return m.role === "user" ? "chat-message-shell-user" : "chat-message-shell-assistant";
}

function isCompactUserMessage(text: string): boolean {
  const t = String(text || "");
  return !t.includes("\n") && t.trim().length <= 28;
}

/** Replace backend/protocol echoes with concise demo copy for training actions. */
function assistantBubbleText(m: MessageItem): string {
  const raw = String(m.text || "");
  if (m.role !== "assistant") return raw;
  const ad = m.actionData as ChatTurnData | null | undefined;
  if (ad?.route === "deterministic_action") {
    const ra = ad.recognized_action;
    if (ra === "draft_training_job") return i18nT("chat.assistantAction.trainingDraftBubble");
    if (ra === "create_training_job") return i18nT("chat.assistantAction.trainingPendingBubble");
  }
  if (/parsed\s+inputs|missing\s+fields\s+names\s+only|do\s+not\s+describe\s+training|do\s+not\s+invent/i.test(raw)) {
    return i18nT("chat.assistantAction.trainingDraftBubble");
  }
  return raw;
}

function showAssistantBubble(m: MessageItem): boolean {
  if (m.role === "user") return true;
  const t = String(m.text || "").trim();
  if (t.length > 0) return true;
  if (m.predictionSubmittedSummary || m.predictionResult) return false;
  if (m.resultData || m.workflowActionData || m.trainingReceiptData) return false;
  if (m.actionData && (m.actionData.route === "deterministic_action" || m.actionData.route === "tool_query"))
    return false;
  if (m.predictionFormCard || m.batchPredictionCard || m.batchPredictionResult) return false;
  if (m.recommendationWorkflowCard || m.recommendationResult) return false;
  return true;
}

</script>

<style scoped>
.chat-message-list {
  box-sizing: border-box;
  width: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0;
  padding: 20px 0 24px;
  background: transparent;
}

.chat-empty {
  padding: var(--wb-space-3);
  border: 1px dashed var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  color: var(--wb-text-body-secondary);
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
  text-align: center;
  background: #fff;
}

/**
 * Row-level chat layout: assistant rows start at the left gutter; user rows align to the right.
 * Avatars sit in fixed-width slots; workflow cards share the assistant column (not centered).
 */
.chat-row {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  width: 100%;
  margin-bottom: var(--wb-chat-row-gap);
}

.chat-row:last-child {
  margin-bottom: 0;
}

.chat-row-assistant {
  justify-content: flex-start;
  gap: var(--wb-chat-column-gap);
}

.chat-row-user {
  justify-content: flex-end;
  gap: var(--wb-chat-column-gap);
}

.chat-avatar-slot {
  flex: 0 0 var(--wb-chat-gutter-width);
  width: var(--wb-chat-gutter-width);
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
}

.chat-thread {
  display: flex;
  flex-direction: column;
  gap: var(--wb-chat-main-stack-gap);
  min-width: 0;
}

.chat-thread-assistant {
  flex: 1 1 auto;
  align-items: flex-start;
  width: 100%;
  max-width: none;
}

.chat-thread-user {
  flex: 1 1 auto;
  align-items: flex-end;
  width: 100%;
  max-width: none;
}

.chat-message-shell {
  display: flex;
  align-items: flex-start;
  width: 100%;
  min-width: 0;
}

.chat-message-shell-assistant {
  justify-content: flex-start;
}

.chat-message-shell-user {
  justify-content: flex-end;
}

.chat-bubble {
  display: flex;
  flex-direction: column;
  gap: var(--wb-chat-bubble-gap);
  box-sizing: border-box;
  width: fit-content;
  padding: var(--wb-chat-bubble-padding-y) var(--wb-chat-bubble-padding-x);
  border-radius: var(--wb-radius-sm);
  border: 1px solid var(--wb-border);
  box-shadow: var(--wb-shadow-sm);
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
}

.chat-bubble-assistant,
.chat-bubble-status,
.chat-bubble-error,
.chat-bubble-workflow-guide {
  max-width: min(100%, var(--wb-chat-bubble-assistant-max));
}

.chat-bubble-user {
  max-width: min(100%, var(--wb-chat-bubble-user-max));
  background: #edf2f7;
  border-color: #d7e0ea;
}

.chat-bubble-assistant {
  background: #ffffff;
  border-color: #e2e8f0;
}

/** Training workflow intro — guidance only, visually lighter than the setup card below */
.chat-bubble-workflow-guide {
  background: #f8fafc;
  border-color: #e8edf4;
  box-shadow: none;
  font-size: var(--wb-font-size-sm);
}

.chat-bubble-workflow-guide .chat-text {
  color: var(--wb-text-body-secondary);
}

.chat-bubble-status {
  background: #fdf9f2;
  border-color: #ecdcc6;
}

.chat-bubble-error {
  background: #fdf5f5;
  border-color: #edd7d7;
}

.chat-text {
  color: var(--wb-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-bubble-compact {
  width: fit-content;
  max-width: min(100%, var(--wb-chat-bubble-compact-max));
  padding: var(--wb-space-1) calc(var(--wb-space-2) - 2px);
}

.chat-avatar {
  width: var(--wb-chat-avatar-size);
  height: var(--wb-chat-avatar-size);
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--wb-font-size-xs);
  line-height: 1;
  font-weight: 650;
  flex-shrink: 0;
  user-select: none;
}

.chat-avatar-assistant {
  border: 1px solid #d6dfeb;
  background: #f4f7fb;
  color: #4d627e;
  font-size: var(--wb-font-size-sm);
  font-weight: 700;
  letter-spacing: 0.01em;
}

.chat-avatar-user {
  border: 1px solid #d8e1ec;
  background: #eef2f7;
  color: #556172;
}

.chat-embed-card {
  box-sizing: border-box;
  align-self: flex-start;
  width: 100%;
  max-width: min(100%, var(--wb-chat-workflow-card-max));
  min-width: 0;
  padding: var(--wb-space-2) var(--wb-chat-embed-padding-x) var(--wb-chat-embed-padding-y);
  border: 1px solid #dde6f1;
  border-radius: var(--wb-chat-embed-radius);
  background: #fff;
  box-shadow: 0 1px 2px rgba(31, 41, 55, 0.04);
}

/** Regimen recommendation: single primary card lives inside the child; avoid a second boxed wrapper. */
.chat-embed-rec-primary {
  box-sizing: border-box;
  align-self: flex-start;
  width: 100%;
  max-width: min(100%, var(--wb-chat-workflow-card-max));
  min-width: 0;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.chat-tool-query {
  box-sizing: border-box;
  align-self: flex-start;
  width: 100%;
  max-width: min(100%, var(--wb-chat-workflow-card-max));
  min-width: 0;
  margin-top: 0;
  padding: var(--wb-chat-bubble-padding-x) var(--wb-chat-input-padding-x);
  border: 1px solid #dbe4ef;
  border-radius: var(--wb-radius-sm);
  background: #f6fafe;
}

.chat-tool-query-title {
  margin-bottom: var(--wb-space-1);
  color: #51606f;
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
}

.chat-tool-labels {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1);
}

.chat-tool-label {
  display: inline-block;
  padding: var(--wb-chat-bubble-gap) var(--wb-chat-bubble-padding-x);
  border-radius: 999px;
  background: #e9f0f7;
  color: #4d657f;
  font-size: var(--wb-font-size-xs);
  line-height: var(--wb-line-height);
}

.chat-tool-empty {
  color: var(--wb-text-caption-muted);
  font-size: var(--wb-font-size-xs);
  line-height: var(--wb-line-height);
}

.chat-fallback {
  box-sizing: border-box;
  align-self: flex-start;
  width: 100%;
  max-width: min(100%, var(--wb-chat-workflow-card-max));
  min-width: 0;
  padding: var(--wb-chat-input-padding-y) var(--wb-chat-bubble-padding-x);
  border: 1px dashed #cfd6df;
  border-radius: var(--wb-radius-sm);
  background: #fff;
  font-size: var(--wb-font-size-chat-body);
  line-height: var(--wb-line-height-prose);
}
</style>
