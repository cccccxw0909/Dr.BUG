<template>
  <div v-if="card.status === 'submitted' || card.status === 'finished'" class="bpc-state bpc-state-success">
    <div class="bpc-state-title">{{ i18nT("chat.batchPrediction.submittedTitle") }}</div>
    <div v-if="card.submittedSummary" class="bpc-submitted-body">
      <div class="bpc-kv"><span class="bpc-k">{{ i18nT("chat.batchPrediction.labels.model") }}</span><span>{{ card.submittedSummary.modelName || card.submittedSummary.modelId }}</span></div>
      <div class="bpc-kv"><span class="bpc-k">{{ i18nT("chat.batchPrediction.labels.file") }}</span><span>{{ card.submittedSummary.fileName || i18nT("common.na") }}</span></div>
      <div class="bpc-kv">
        <span class="bpc-k">{{ i18nT("chat.batchPrediction.labels.columnMatch") }}</span>
        <span>{{
          i18nT("chat.batchPrediction.submittedAlignment", {
            matched: card.submittedSummary.matchedCount,
            missing: card.submittedSummary.missingCount,
            extra: card.submittedSummary.extraCount,
          })
        }}</span>
      </div>
    </div>
  </div>

  <div v-else-if="card.status === 'cancelled'" class="bpc-state bpc-state-cancelled">
    <div class="bpc-state-cancel-title">{{ i18nT("chat.batchPrediction.cancelledTitle") }}</div>
  </div>

  <div v-else class="prediction-form-card">
    <div class="bpc-card-title">{{ i18nT("chat.batchPrediction.title") }}</div>
    <div class="bpc-intro">{{ i18nT("chat.batchPrediction.intro") }}</div>
    <div v-if="card.runRunning" class="running-hint">
      {{ i18nT("chat.batchPrediction.runningHint", { elapsed: elapsedText }) }}
      <div class="progress-track"><div class="progress-bar" /></div>
    </div>

    <div v-if="card.modelsLoading" class="bpc-muted bpc-mt-m">{{ i18nT("chat.batchPrediction.loadingModels") }}</div>
    <div v-if="card.modelsError" class="bpc-err bpc-mt-m">{{ card.modelsError }}</div>

    <div class="bpc-mt-m">
      <label class="bpc-label">{{ i18nT("chat.batchPrediction.modelSelect") }}</label>
      <select
        :value="card.selectedModelId ?? ''"
        class="bpc-select-full"
        @change="emit('action', { action: 'selectModel', cardId: card.card_id, modelId: (($event.target as HTMLSelectElement).value || null) })"
      >
        <option value="">{{ i18nT("chat.assistantAction.pleaseSelect") }}</option>
        <option v-for="m in card.models" :key="m.model_id" :value="m.model_id">{{ batchOptionLabels[m.model_id] || m.model_id }}</option>
      </select>
    </div>

    <div class="bpc-mt-m">
      <label class="bpc-label">{{ i18nT("chat.batchPrediction.uploadFile") }}</label>
      <div class="wb-file-pick bpc-mt-s">
        <label
          class="wb-file-pick-label wb-btn wb-btn-secondary"
          :class="{ 'is-disabled': filePickDisabled }"
        >
          {{ i18nT("chat.batchPrediction.actions.chooseFile") }}
          <input
            type="file"
            class="wb-file-pick-input"
            accept=".csv,.xlsx,.xls"
            :disabled="filePickDisabled"
            @change="onFileChange"
          />
        </label>
      </div>
      <div v-if="card.fileName" class="wb-file-pick-name bpc-mt-s">{{ i18nT("chat.batchPrediction.selectedFilePrefix") }}<b>{{ card.fileName }}</b></div>
    </div>

    <div v-if="card.checkResult" class="bpc-check-box">
      <div class="bpc-check-title">{{ i18nT("chat.batchPrediction.check.title") }}</div>
      <div>{{ i18nT("chat.batchPrediction.check.matched") }} {{ card.checkResult.matched_fields.length }}</div>
      <div>{{ i18nT("chat.batchPrediction.check.missing") }} {{ card.checkResult.missing_fields.length }}</div>
      <div>{{ i18nT("chat.batchPrediction.check.extra") }} {{ card.checkResult.extra_fields.length }}</div>
      <div v-if="card.checkResult.required_missing_fields.length" class="bpc-err-s">
        {{ i18nT("chat.batchPrediction.check.requiredMissing", { list: card.checkResult.required_missing_fields.join(listSep) }) }}
      </div>
      <details v-if="card.checkResult.missing_fields.length" class="bpc-mt-s">
        <summary>{{ i18nT("chat.batchPrediction.check.viewMissing") }}</summary>
        <div class="bpc-detail-text">{{ card.checkResult.missing_fields.join(listSep) }}</div>
      </details>
      <details v-if="card.checkResult.extra_fields.length" class="bpc-mt-s">
        <summary>{{ i18nT("chat.batchPrediction.check.viewExtra") }}</summary>
        <div class="bpc-detail-text">{{ card.checkResult.extra_fields.join(listSep) }}</div>
      </details>
      <div v-if="card.checkResult.warnings?.length" class="bpc-warn">
        {{ i18nT("chat.batchPrediction.check.suspiciousPrefix") }}{{ card.checkResult.warnings.slice(0, 4).join(warningSep) }}
      </div>
    </div>

    <div v-if="card.checkError" class="bpc-err bpc-mt-m">{{ card.checkError }}</div>
    <div v-if="card.runError" class="bpc-err bpc-mt-m">{{ card.runError }}</div>

    <div class="action-row">
      <button type="button" class="wb-btn wb-btn-ghost" @click="emit('action', { action: 'cancel', cardId: card.card_id })">{{ i18nT("chat.batchPrediction.actions.cancel") }}</button>
      <button type="button" class="wb-btn wb-btn-secondary" :disabled="card.checkRunning || card.runRunning" @click="emit('action', { action: 'check', cardId: card.card_id })">
        {{ card.checkRunning ? i18nT("chat.batchPrediction.states.checking") : i18nT("chat.batchPrediction.actions.checkFields") }}
      </button>
      <button
        type="button"
        class="wb-btn wb-btn-primary"
        :disabled="card.runRunning || card.checkRunning || !card.checkResult || !card.checkResult.can_run"
        @click="emit('action', { action: 'run', cardId: card.card_id })"
      >
        {{ card.runRunning ? i18nT("chat.batchPrediction.states.running") : i18nT("chat.batchPrediction.actions.confirmExecute") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { BatchPredictionCardData, BatchPredictionChatAction, PredictionModelListItem } from "../../types";
import { buildPredictionModelOptionLabelMap } from "../../utils/modelPresentation";

const props = defineProps<{ card: BatchPredictionCardData }>();
const emit = defineEmits<{ (e: "action", payload: BatchPredictionChatAction): void }>();

const { t: i18nT } = useI18n();

const batchOptionLabels = computed(() =>
  buildPredictionModelOptionLabelMap(props.card.models || [], i18nT),
);

const listSep = computed(() => i18nT("chat.listSeparator"));
const warningSep = computed(() => i18nT("chat.batchPrediction.check.warningSeparator"));

const filePickDisabled = computed(() => Boolean(props.card.checkRunning || props.card.runRunning));

const nowMs = ref(Date.now());
let timer: number | null = null;

function ensureTimer() {
  if (timer != null) return;
  timer = window.setInterval(() => {
    nowMs.value = Date.now();
  }, 1000);
}
function clearTimer() {
  if (timer == null) return;
  window.clearInterval(timer);
  timer = null;
}
watch(
  () => props.card.runRunning,
  (v) => {
    if (v) ensureTimer();
    else clearTimer();
  },
  { immediate: true },
);
onMounted(() => {
  if (props.card.runRunning) ensureTimer();
});
onBeforeUnmount(() => clearTimer());

const elapsedText = computed(() => {
  const ts = props.card.runStartedAt;
  if (!ts) return i18nT("chat.predictionForm.elapsed.secondsOnly", { seconds: 0 });
  const start = new Date(ts).getTime();
  if (!Number.isFinite(start)) return i18nT("chat.predictionForm.elapsed.secondsOnly", { seconds: 0 });
  const sec = Math.max(0, Math.floor((nowMs.value - start) / 1000));
  if (sec < 60) return i18nT("chat.predictionForm.elapsed.secondsOnly", { seconds: sec });
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return i18nT("chat.predictionForm.elapsed.minutesSeconds", { minutes: m, seconds: s });
});

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;
  emit("action", { action: "setFile", cardId: props.card.card_id, file });
}
</script>

<style scoped>
.bpc-state {
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-chat-bubble-padding-x);
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
  line-height: 1.5;
}
.bpc-state-success {
  border: 1px solid #b6e3c6;
  background: #f6fff8;
}
.bpc-state-cancelled {
  border: 1px solid #ddd;
  background: #f6f8fa;
  color: #57606a;
}
.bpc-state-title {
  font-weight: 700;
  color: #116329;
}
.bpc-state-cancel-title {
  font-weight: 600;
}
.bpc-submitted-body {
  margin-top: var(--wb-space-1);
}
.bpc-kv {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1);
  margin-bottom: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
}
.bpc-k {
  color: var(--wb-text-secondary);
  font-weight: 600;
}
.bpc-card-title {
  font-weight: 700;
  color: #234;
}
.bpc-intro {
  font-size: var(--wb-font-size-2xs);
  color: #567;
  margin-top: var(--wb-space-micro);
}
.bpc-muted {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}
.bpc-err {
  color: #b00020;
  font-size: var(--wb-font-size-xs);
}
.bpc-mt-m {
  margin-top: var(--wb-chat-input-padding-y);
}
.bpc-mt-s {
  margin-top: var(--wb-space-1);
}
.bpc-label {
  display: block;
  font-weight: 600;
  font-size: var(--wb-font-size-xs);
}
.bpc-select-full {
  width: 100%;
  margin-top: var(--wb-space-1);
  box-sizing: border-box;
}
.bpc-check-box {
  margin-top: var(--wb-chat-bubble-padding-x);
  border: 1px solid #dbe6f2;
  background: #fff;
  border-radius: var(--wb-radius-xs);
  padding: var(--wb-chat-input-padding-y);
}
.bpc-check-title {
  font-weight: 600;
  margin-bottom: var(--wb-space-micro);
}
.bpc-err-s {
  margin-top: var(--wb-space-1);
  color: #b00020;
}
.bpc-detail-text {
  font-size: var(--wb-font-size-2xs);
  color: #444;
  margin-top: var(--wb-space-micro);
}
.bpc-warn {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-2xs);
  color: #7a5600;
}

.prediction-form-card {
  border: 1px solid #c8d5e6;
  border-radius: var(--wb-radius-sm);
  background: #f8fbff;
  padding: var(--wb-chat-bubble-padding-x);
  margin-top: var(--wb-space-1);
}
.action-row {
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  flex-wrap: wrap;
  margin-top: var(--wb-chat-bubble-padding-x);
  padding-top: var(--wb-chat-input-padding-y);
  border-top: 1px solid #dde7f2;
}
.running-hint {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
  background: #fff8e6;
  border-radius: var(--wb-space-micro);
  font-size: var(--wb-font-size-xs);
  color: #7a5600;
}
.progress-track {
  margin-top: var(--wb-space-1);
  width: 100%;
  height: var(--wb-space-1);
  background: #efe3b8;
  border-radius: 999px;
  overflow: hidden;
}
.progress-bar {
  width: 35%;
  height: 100%;
  background: linear-gradient(90deg, #c49500, #e0b323);
  border-radius: 999px;
  animation: batch-progress-slide 1.1s linear infinite;
}
@keyframes batch-progress-slide {
  0% {
    transform: translateX(-110%);
  }
  100% {
    transform: translateX(320%);
  }
}
</style>
