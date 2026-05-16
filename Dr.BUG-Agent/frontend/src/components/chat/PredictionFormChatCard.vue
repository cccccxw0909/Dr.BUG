<template>
  <div
    v-if="card.status === 'cancelled'"
    class="prediction-state-card prediction-state-card-cancelled"
  >
    <div class="prediction-state-title prediction-state-title-muted">{{ i18nT("chat.predictionForm.states.cancelledTitle") }}</div>
  </div>

  <div v-else class="prediction-form-card">
    <div
      v-if="card.predictRunning && card.active_panel === 'form'"
      class="prediction-running-banner"
      role="status"
      aria-live="polite"
    >
      {{ i18nT("chat.predictionForm.states.singleRunningTitle") }}
    </div>

    <div class="prediction-workspace-body">
      <div class="pfc-shared-flow">
        <div v-if="card.modelsLoading" class="pfc-muted">{{ i18nT("chat.predictionForm.labels.loadingModels") }}</div>
        <div v-else-if="card.modelsError" class="pfc-err">{{ card.modelsError }}</div>
        <template v-else>
          <div class="full-row pfc-model-block">
            <label class="pfc-label" for="pfc-task-select">{{ i18nT("chat.predictionForm.labels.stepChoosePredictionTask") }}</label>
            <select
              id="pfc-task-select"
              :value="selectedTaskValue"
              class="pfc-control pfc-full-mt"
              @change="onTaskSelect(($event.target as HTMLSelectElement).value)"
            >
              <option value="">{{ i18nT("chat.assistantAction.pleaseSelect") }}</option>
              <option v-for="k in predictionTaskKeysOrder" :key="k" :value="k">{{ predictionTaskOptionLabel(k) }}</option>
            </select>
          </div>

          <div class="full-row pfc-model-block">
            <label class="pfc-label" for="pfc-model-select-shared">{{ i18nT("chat.predictionForm.labels.stepChooseReleasedModel") }}</label>
            <select
              id="pfc-model-select-shared"
              :value="card.selectedModelId ?? ''"
              class="pfc-control pfc-full-mt"
              :disabled="!card.selectedPredictionTaskKey"
              @change="onModelChange(($event.target as HTMLSelectElement).value)"
            >
              <option value="">{{ i18nT("chat.assistantAction.pleaseSelect") }}</option>
              <option v-for="m in modelsForSelectedTask" :key="m.model_id" :value="m.model_id">
                {{ predictionOptionLabels[m.model_id] || m.model_id }}{{ !m.has_schema ? i18nT("chat.predictionForm.labels.noSchemaSuffix") : "" }}
              </option>
            </select>
            <div
              v-if="card.selectedPredictionTaskKey && modelsForSelectedTask.length === 0"
              class="pfc-muted pfc-mt-m"
            >
              {{ i18nT("chat.predictionForm.labels.noReleasedModelForTask") }}
            </div>
            <div v-if="card.selectedModelId && card.schemaLoading" class="pfc-muted pfc-mt-m">{{ i18nT("chat.predictionForm.labels.loadingFields") }}</div>
            <div v-if="card.schemaError" class="pfc-err-s pfc-mt-m">{{ card.schemaError }}</div>
          </div>
        </template>
      </div>

      <div class="pfc-mode-switch" role="tablist" :aria-label="i18nT('chat.predictionForm.aria.predictionModeTablist')">
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'single'"
          class="pfc-mode-tab"
          :class="{ 'pfc-mode-tab-active': mode === 'single' }"
          :disabled="panelSwitchDisabled"
          @click="emitAction({ action: 'setActivePanel', cardId: card.card_id, panel: 'form' })"
        >
          {{ i18nT("chat.predictionForm.modeSingle") }}
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'batch'"
          class="pfc-mode-tab"
          :class="{ 'pfc-mode-tab-active': mode === 'batch' }"
          :disabled="panelSwitchDisabled"
          @click="emitAction({ action: 'setActivePanel', cardId: card.card_id, panel: 'batch' })"
        >
          {{ i18nT("chat.predictionForm.modeBatch") }}
        </button>
      </div>

      <div v-show="mode === 'single'" class="pfc-mode-panel">
        <div v-if="card.submitError" class="pfc-err-t">{{ card.submitError }}</div>

        <div class="pfc-form-body">
          <template v-if="card.schema">
            <div class="full-row pfc-row-meta">
              <span class="pfc-fw">{{ schemaHeaderPrimary() }}</span>
              <span v-if="schemaHeaderAlgo()" class="pfc-muted-inline">({{ schemaHeaderAlgo() }})</span>
            </div>
            <div v-if="validation" class="full-row pfc-val-row">
              {{ i18nT("chat.predictionForm.progress.filledSummary", { filled: validation.filledCount, total: card.schema.fields.length }) }}
              <span v-if="validation.errorCount > 0" class="pfc-err-inline">{{
                i18nT("chat.predictionForm.progress.errorsInline", { count: validation.errorCount })
              }}</span>
            </div>

            <div class="field-grid field-grid-flat">
                <div v-for="f in flatFields" :key="f.name" class="field-block">
                  <label class="field-label" :for="`pfc-f-${card.card_id}-${f.name}`">
                    {{ doctorFacingFeatureLabel(f) }}
                    <span v-if="f.required" class="pfc-req">*</span>
                    <span v-if="f.unit" class="pfc-unit">({{ f.unit }})</span>
                  </label>
                  <div v-if="f.reference_range" class="field-meta">{{ f.reference_range }}</div>
                  <div v-if="f.description" class="field-meta">{{ f.description }}</div>

                  <template v-if="f.type === 'binary'">
                    <div class="binary-radio-row">
                      <label class="tri-option tri-option-compact">
                        <input
                          type="radio"
                          :name="`bin-${card.card_id}-${f.name}`"
                          :checked="binaryValue(f.name) === 0"
                          @change="emitField(f.name, 0)"
                        />
                        {{ i18nT("predictionPresentation.boolean.no") }}
                      </label>
                      <label class="tri-option tri-option-compact">
                        <input
                          type="radio"
                          :name="`bin-${card.card_id}-${f.name}`"
                          :checked="binaryValue(f.name) === 1"
                          @change="emitField(f.name, 1)"
                        />
                        {{ i18nT("predictionPresentation.boolean.yes") }}
                      </label>
                    </div>
                  </template>

                  <select
                    v-else-if="f.type === 'categorical'"
                    :id="`pfc-f-${card.card_id}-${f.name}`"
                    class="pfc-control pfc-full-mt"
                    :value="String(fieldStr(f.name))"
                    @change="emitField(f.name, ($event.target as HTMLSelectElement).value)"
                  >
                    <option value="">—</option>
                    <option v-for="op in f.options || []" :key="String(op)" :value="String(op)">{{ op }}</option>
                  </select>

                  <input
                    v-else-if="f.type === 'int'"
                    :id="`pfc-f-${card.card_id}-${f.name}`"
                    type="number"
                    step="1"
                    class="pfc-control pfc-full-mt"
                    :value="fieldStr(f.name)"
                    @input="emitField(f.name, ($event.target as HTMLInputElement).value)"
                  />

                  <input
                    v-else-if="f.type === 'float'"
                    :id="`pfc-f-${card.card_id}-${f.name}`"
                    type="number"
                    step="any"
                    class="pfc-control pfc-full-mt"
                    :value="fieldStr(f.name)"
                    @input="emitField(f.name, ($event.target as HTMLInputElement).value)"
                  />

                  <input
                    v-else
                    :id="`pfc-f-${card.card_id}-${f.name}`"
                    type="text"
                    class="pfc-control pfc-full-mt"
                    :value="fieldStr(f.name)"
                    @input="emitField(f.name, ($event.target as HTMLInputElement).value)"
                  />

                  <div v-if="fieldErr(f.name)" class="pfc-field-err">{{ fieldErr(f.name) }}</div>
                </div>
              </div>
          </template>
        </div>
      </div>

      <div v-show="mode === 'batch'" class="pfc-mode-panel prediction-batch-panel">
        <div v-if="batch?.runRunning" class="running-hint">
          {{ i18nT("chat.predictionForm.batch.runningHint", { elapsed: batchElapsedText }) }}
        </div>
        <div v-if="batch?.checkError" class="pfc-err-s">{{ batch.checkError }}</div>
        <div v-if="batch?.runError" class="pfc-err-s">{{ batch.runError }}</div>

        <div class="full-row pfc-mt-m">
          <label class="pfc-label">{{ i18nT("chat.predictionForm.labels.stepUploadTable") }}</label>
          <div class="wb-file-pick pfc-mt-s">
            <label
              class="wb-file-pick-label wb-btn wb-btn-secondary"
              :class="{ 'is-disabled': Boolean(batchBusy) }"
            >
              {{ i18nT("chat.batchPrediction.actions.chooseFile") }}
              <input
                type="file"
                class="wb-file-pick-input"
                accept=".csv,.xlsx,.xls"
                :disabled="Boolean(batchBusy)"
                @change="onBatchFile"
              />
            </label>
          </div>
          <div v-if="batch?.fileName" class="wb-file-pick-name pfc-mt-s">{{ i18nT("chat.batchPrediction.selectedFilePrefix") }}<b>{{ batch.fileName }}</b></div>
        </div>

        <div v-if="batch?.checkResult" class="pfc-batch-check">
          <div class="pfc-batch-check-title">{{ i18nT("chat.predictionForm.labels.columnCheckTitle") }}</div>
          <div>{{ batchColumnCheckLine }}</div>
          <div v-if="batch.checkResult.required_missing_fields.length" class="pfc-err-s pfc-mt-s">
            {{ i18nT("chat.predictionForm.batch.requiredMissing", { list: batchRequiredMissingLabels }) }}
          </div>
        </div>

      </div>
    </div>

    <footer class="prediction-workspace-footer">
      <div class="action-row">
        <button type="button" class="wb-btn wb-btn-secondary pfc-action-fs" :disabled="footerBusy" @click="emitAction({ action: 'cancel', cardId: card.card_id })">
          {{ i18nT("common.cancel") }}
        </button>
        <button
          v-if="mode === 'single'"
          type="button"
          class="wb-btn wb-btn-primary pfc-action-fs-fw"
          :disabled="footerBusy || !card.selectedPredictionTaskKey || !card.selectedModelId || !card.schema || card.schemaLoading"
          @click="emitAction({ action: 'submit', cardId: card.card_id })"
        >
          {{ i18nT("chat.assistantAction.confirmExecutePrediction") }}
        </button>
        <template v-else>
          <button type="button" class="wb-btn wb-btn-secondary pfc-action-fs" :disabled="!batch || batchBusy" @click="emitAction({ action: 'batchCheck', cardId: card.card_id })">
            {{ batch?.checkRunning ? i18nT("chat.predictionForm.footer.checkingColumns") : i18nT("chat.predictionForm.footer.checkColumnNames") }}
          </button>
          <button
            type="button"
            class="wb-btn wb-btn-primary pfc-action-fs-fw"
            :disabled="!batch || batchBusy || !batch.checkResult || !batch.checkResult.can_run"
            @click="emitAction({ action: 'batchRun', cardId: card.card_id })"
          >
            {{ batch?.runRunning ? i18nT("chat.predictionForm.footer.running") : i18nT("chat.assistantAction.confirmExecutePrediction") }}
          </button>
        </template>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRef, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePredictionDomain } from "../../composables/usePredictionDomain";
import { analyzePredictionForm } from "../../utils/predictionFormValidation";
import { doctorFacingFeatureLabel, formatClinicalFeatureNameList } from "../../utils/featureDisplayName";
import { formatBatchColumnAlignmentSummary } from "../../utils/predictionPresentation";
import type { PredictionFormCardData, PredictionFormChatAction, PredictionModelListItem, PredictionTaskKey } from "../../types";
import { PREDICTION_TASK_KEYS_ORDER, predictionModelsForTask } from "../../utils/predictionTaskInference";
import {
  buildPredictionModelOptionLabelMap,
  formatMlTaskKindDisplay,
  predictionModelPrimaryDisplayLabel,
} from "../../utils/modelPresentation";

const props = defineProps<{ card: PredictionFormCardData }>();

const emit = defineEmits<{
  (e: "action", payload: PredictionFormChatAction): void;
}>();

const { t: i18nT } = useI18n();

const predictionTaskKeysOrder = PREDICTION_TASK_KEYS_ORDER;

const selectedTaskValue = computed(() => props.card.selectedPredictionTaskKey ?? "");

const modelsForSelectedTask = computed(() =>
  predictionModelsForTask(props.card.models, props.card.selectedPredictionTaskKey ?? null),
);

const predictionOptionLabels = computed(() =>
  buildPredictionModelOptionLabelMap(modelsForSelectedTask.value, i18nT),
);

function predictionTaskOptionLabel(k: PredictionTaskKey): string {
  return i18nT(`chat.predictionForm.predictionTasks.${k}.label`);
}

function schemaHeaderPrimary(): string {
  const s = props.card.schema;
  if (!s) return "";
  const meta = s.metadata && typeof s.metadata === "object" ? (s.metadata as Record<string, unknown>) : undefined;
  return predictionModelPrimaryDisplayLabel(
    {
      model_id: s.model_id,
      display_name: s.display_name,
      task_name: s.task_name,
      clinical_task_id: String(meta?.clinical_task_id ?? "").trim(),
      model_type: s.model_type,
      metadata: meta,
    },
    i18nT,
  );
}

function schemaHeaderAlgo(): string {
  const mt = props.card.schema?.model_type;
  return mt ? formatMlTaskKindDisplay(mt, i18nT) : "";
}

const { mode, batch, batchBusy, anyBusy } = usePredictionDomain(toRef(props, "card"));

const footerBusy = computed(() => Boolean(props.card.predictRunning || batch.value?.runRunning));

/** While single prediction or batch check/run is active: disable panel switching to avoid interleaved state. */
const panelSwitchDisabled = computed(() => anyBusy.value);

const nowMs = ref(Date.now());
let batchTimer: number | null = null;
function ensureBatchTimer() {
  if (batchTimer != null) return;
  batchTimer = window.setInterval(() => {
    nowMs.value = Date.now();
  }, 1000);
}
function clearBatchTimer() {
  if (batchTimer == null) return;
  window.clearInterval(batchTimer);
  batchTimer = null;
}
watch(
  () => props.card.batch?.runRunning,
  (v) => {
    if (v) ensureBatchTimer();
    else clearBatchTimer();
  },
  { immediate: true },
);
onMounted(() => {
  if (props.card.batch?.runRunning) ensureBatchTimer();
});
onBeforeUnmount(() => clearBatchTimer());

const batchColumnCheckLine = computed(() => {
  const cr = props.card.batch?.checkResult;
  if (!cr) return "";
  return formatBatchColumnAlignmentSummary(
    cr.matched_fields.length,
    cr.missing_fields.length,
    cr.extra_fields.length,
    i18nT,
  );
});

const batchRequiredMissingLabels = computed(() => {
  const cr = props.card.batch?.checkResult;
  if (!cr?.required_missing_fields?.length) return "";
  return formatClinicalFeatureNameList(cr.required_missing_fields, props.card.schema?.fields ?? null);
});

const batchElapsedText = computed(() => {
  const t0 = props.card.batch?.runStartedAt;
  if (!t0) return i18nT("common.na");
  const sec = Math.max(0, Math.floor((nowMs.value - new Date(t0).getTime()) / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? i18nT("chat.predictionForm.elapsed.minutesSeconds", { minutes: m, seconds: s }) : i18nT("chat.predictionForm.elapsed.secondsOnly", { seconds: s });
});

function onBatchFile(ev: Event) {
  const inp = ev.target as HTMLInputElement;
  const f = inp.files?.[0] ?? null;
  emit("action", { action: "batchSetFile", cardId: props.card.card_id, file: f });
  inp.value = "";
}

const validation = computed(() =>
  props.card.schema ? analyzePredictionForm(props.card.schema.fields, props.card.formValues, i18nT) : null,
);

const flatFields = computed(() => props.card.schema?.fields ?? []);

function fieldErr(name: string): string {
  return validation.value?.fieldErrors[name] || "";
}

function binaryValue(name: string): 0 | 1 | null {
  const v = props.card.formValues[name];
  if (v === null || v === undefined || v === "") return null;
  if (v === false || v === 0 || v === "0" || v === "false") return 0;
  if (v === true || v === 1 || v === "1" || v === "true") return 1;
  return null;
}

function fieldStr(name: string): string {
  const v = props.card.formValues[name];
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "true" : "";
  return String(v);
}

function emitField(name: string, value: unknown) {
  emit("action", { action: "updateValue", cardId: props.card.card_id, name, value });
}

function onModelChange(id: string) {
  emit("action", { action: "selectModel", cardId: props.card.card_id, modelId: id || null });
}

function onTaskSelect(raw: string) {
  const v = raw.trim();
  emit("action", {
    action: "selectPredictionTask",
    cardId: props.card.card_id,
    taskKey: v ? (v as PredictionTaskKey) : null,
  });
}

function emitAction(payload: PredictionFormChatAction) {
  emit("action", payload);
}

</script>

<style scoped>
.pfc-req {
  color: #b00020;
}
.pfc-inline-muted {
  color: var(--wb-text-secondary);
}
.pfc-err-t {
  margin-top: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-xs);
  color: #b00020;
}
.pfc-muted {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}
.pfc-err {
  font-size: var(--wb-font-size-xs);
  color: #b00020;
}
.pfc-label {
  display: block;
  font-weight: 600;
  font-size: var(--wb-font-size-xs);
}
.pfc-control {
  width: 100%;
  margin-top: var(--wb-space-1);
  box-sizing: border-box;
  min-height: var(--wb-control-height-sm);
  border: 1px solid #d4deea;
  border-radius: var(--wb-radius-sm);
  background: #fff;
  padding: 0 var(--wb-chat-bubble-padding-x);
  color: var(--wb-text-primary);
  font-size: var(--wb-font-size-xs);
}
.pfc-full-mt {
  width: 100%;
  margin-top: var(--wb-space-1);
  box-sizing: border-box;
}
.pfc-mt-m {
  margin-top: var(--wb-chat-input-padding-y);
}
.pfc-mt-s {
  margin-top: var(--wb-space-1);
}
.pfc-help {
  margin: 0;
  font-size: var(--wb-font-size-2xs);
  color: var(--wb-text-secondary);
  line-height: var(--wb-line-height);
}
.pfc-err-s {
  margin-top: var(--wb-space-1);
  font-size: var(--wb-font-size-2xs);
  color: #b00020;
}
.pfc-row-meta {
  font-size: var(--wb-font-size-xs);
  margin-bottom: var(--wb-chat-input-padding-y);
}
.pfc-fw {
  font-weight: 600;
}
.pfc-muted-inline {
  color: var(--wb-text-secondary);
  margin-left: var(--wb-space-1);
}
.pfc-val-row {
  font-size: var(--wb-font-size-2xs);
  margin-bottom: var(--wb-chat-input-padding-y);
  color: #444;
}
.pfc-err-inline {
  color: #b00020;
}
.pfc-unit {
  font-weight: 500;
  color: #666;
  font-size: var(--wb-font-size-2xs);
}
.pfc-field-err {
  font-size: var(--wb-font-size-2xs);
  color: #b00020;
  margin-top: var(--wb-space-micro);
}
.pfc-action-fs {
  font-size: var(--wb-font-size-xs);
}
.pfc-action-fs-fw {
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
}
.pfc-batch-check {
  margin-top: var(--wb-space-2);
  border: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: var(--wb-radius-xs);
  padding: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-2xs);
}
.pfc-batch-check-title {
  font-weight: 600;
  margin-bottom: var(--wb-space-micro);
}

/** Layout shell only; white frame and padding come from ChatMessageList `.chat-embed-card`. */
.prediction-form-card {
  border: none;
  border-radius: 0;
  background: transparent;
  padding: 0;
  margin: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.prediction-state-card {
  margin-top: var(--wb-space-1);
  padding: var(--wb-space-3);
  border-radius: var(--wb-chat-embed-radius);
  font-size: var(--wb-font-size-xs);
  line-height: 1.5;
}
.prediction-state-card-cancelled {
  border: 1px solid #dde2ea;
  background: #f6f8fa;
  color: #57606a;
}
.prediction-state-title {
  font-weight: 700;
  color: #4a5565;
}
.prediction-state-title-muted {
  color: #4a5565;
}
.prediction-running-banner {
  margin: 0 0 var(--wb-space-2);
  padding: var(--wb-space-2) var(--wb-chat-input-padding-y);
  background: #fff8e6;
  border: 1px solid #f5d78e;
  border-radius: var(--wb-radius-sm);
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
  color: #7a5600;
}
.prediction-state-body {
  margin-top: var(--wb-chat-input-padding-y);
}
.prediction-state-kv {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1);
  margin-bottom: var(--wb-space-1);
  font-size: var(--wb-font-size-xs);
}
.pfc-sum-key {
  color: var(--wb-text-secondary);
  font-weight: 600;
}
.pfc-sum-val {
  color: var(--wb-text-primary);
}
.prediction-state-foot {
  margin-top: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-2xs);
  color: #57606a;
}

.pfc-mode-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 0 0 var(--wb-space-2);
  padding: 3px;
  border-radius: 8px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}
.pfc-mode-tab {
  flex: 1 1 120px;
  min-height: 32px;
  margin: 0;
  padding: 0 var(--wb-space-2);
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
  color: #4a5f78;
  cursor: pointer;
}
.pfc-mode-tab:hover:not(:disabled) {
  color: #223a59;
}
.pfc-mode-tab:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.pfc-mode-tab-active {
  background: #fff;
  color: #0d47a1;
  box-shadow: 0 1px 2px rgba(31, 41, 55, 0.08);
}

.prediction-workspace-body {
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e8ebef;
  padding-top: var(--wb-space-2);
}
.pfc-shared-flow {
  margin-bottom: var(--wb-space-2);
}
.pfc-mode-panel {
  display: flex;
  flex-direction: column;
}
.running-hint {
  margin-top: var(--wb-chat-input-padding-y);
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
  background: #fff8e6;
  border-radius: var(--wb-space-micro);
  font-size: var(--wb-font-size-xs);
  color: #7a5600;
}
.prediction-batch-panel {
  margin-top: 0;
  padding: 0;
  border: none;
  background: transparent;
}

.pfc-flow-steps {
  list-style: decimal;
  margin: 0 0 var(--wb-chat-bubble-padding-x) var(--wb-space-3);
  padding: 0;
  font-size: var(--wb-font-size-2xs);
  color: #5a6b7d;
  line-height: 1.6;
}
.pfc-flow-steps-batch {
  margin-left: var(--wb-space-3);
}
.pfc-step-done {
  color: #1b5e20;
  font-weight: 600;
}

.pfc-form-body {
  margin-top: 0;
  padding-bottom: var(--wb-space-1);
}
.field-grid-flat {
  gap: var(--wb-space-1) var(--wb-chat-input-padding-y);
}
.field-grid-flat .field-block {
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
}
.field-grid-flat .field-meta {
  display: none;
}
.full-row {
  width: 100%;
}
.pfc-model-block {
  padding-bottom: var(--wb-space-1);
}
.group-title {
  font-size: var(--wb-font-size-xs);
  font-weight: 700;
  color: #345;
  margin: var(--wb-chat-input-padding-x) 0 var(--wb-chat-input-padding-y);
  border-bottom: 1px solid #e2eaf5;
  padding-bottom: var(--wb-space-micro);
}
.field-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--wb-chat-bubble-padding-x) var(--wb-chat-input-padding-x);
}
@media (min-width: 720px) {
  .field-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 1100px) {
  .field-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (min-width: 1400px) {
  .field-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.field-block {
  min-width: 0;
  border: 1px solid #e8eef6;
  background: #fff;
  border-radius: var(--wb-radius-xs);
  padding: var(--wb-chat-input-padding-y);
  box-sizing: border-box;
}
.field-label {
  display: flex;
  align-items: baseline;
  gap: var(--wb-space-1);
  font-weight: 600;
  font-size: var(--wb-font-size-xs);
}
.field-meta {
  font-size: var(--wb-font-size-2xs);
  color: #6b7f92;
  margin-top: var(--wb-chat-bubble-gap);
}
.binary-radio-row {
  margin-top: var(--wb-space-1);
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1);
}
.tri-option {
  display: inline-flex;
  align-items: center;
  gap: var(--wb-space-micro);
  font-size: var(--wb-font-size-2xs);
  color: #334;
  padding: var(--wb-space-micro) var(--wb-chat-input-padding-y);
  border: 1px solid #dbe6f2;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  box-sizing: border-box;
}
.tri-option-compact {
  /* Match `.pfc-control` height in the same field card */
  min-height: var(--wb-control-height-sm);
  padding-top: 0;
  padding-bottom: 0;
  padding-left: var(--wb-chat-input-padding-y);
  padding-right: var(--wb-chat-input-padding-y);
}
.tri-option input {
  margin: 0;
}

.prediction-summary-readonly {
  margin-top: var(--wb-chat-bubble-padding-x);
  padding: var(--wb-chat-input-padding-y) var(--wb-chat-bubble-padding-x);
  border: 1px solid #c5d9ed;
  border-radius: var(--wb-radius-sm);
  background: #fff;
}
.prediction-summary-live {
  background: #fbfdff;
}
.prediction-summary-title {
  font-weight: 700;
  font-size: var(--wb-font-size-xs);
  color: #1a365d;
  margin-bottom: var(--wb-space-1);
}
.prediction-summary-group {
  margin-top: var(--wb-chat-input-padding-y);
}
.prediction-summary-group-title {
  font-size: var(--wb-font-size-2xs);
  font-weight: 700;
  color: #4a6fa5;
  margin-bottom: var(--wb-space-micro);
}
.prediction-summary-ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.prediction-summary-li {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1);
  justify-content: space-between;
  font-size: var(--wb-font-size-2xs);
  padding: var(--wb-space-micro) 0;
  border-bottom: 1px solid #eef2f7;
}
.prediction-summary-li:last-child {
  border-bottom: none;
}
.prediction-summary-label {
  color: var(--wb-text-secondary);
  font-weight: 500;
}
.prediction-summary-value {
  color: var(--wb-text-primary);
  font-weight: 600;
  text-align: right;
  word-break: break-word;
  max-width: 100%;
}

.prediction-workspace-footer {
  flex-shrink: 0;
  position: sticky;
  bottom: 0;
  margin-top: var(--wb-space-2);
  padding-top: var(--wb-chat-input-padding-y);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #f9fafb 35%, #f9fafb 100%);
  border-top: 1px solid #e8ebef;
  padding-bottom: var(--wb-space-micro);
}
.action-row {
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  flex-wrap: wrap;
  align-items: center;
}
</style>
