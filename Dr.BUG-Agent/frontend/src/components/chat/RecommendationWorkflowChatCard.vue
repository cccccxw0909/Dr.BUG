<template>
  <div v-if="card.status === 'cancelled'" class="rec-primary-card rec-primary-card--cancelled">
    <p class="rec-cancelled-line">{{ i18nT("chat.recommendationWorkflow.states.cancelledTitle") }}</p>
  </div>

  <div v-else class="rec-primary-card" :class="{ 'rec-primary-card--editing-input': card.status === 'editing' }">
    <div
      v-if="card.status === 'failed'"
      class="rec-status-strip rec-status-strip--error"
      role="status"
    >
      {{ i18nT("chat.recommendationWorkflow.statusStrip.failed") }}
    </div>
    <div
      v-else-if="card.status === 'polling' || card.status === 'submitting'"
      class="rec-status-strip rec-status-strip--info"
      role="status"
    >
      {{
        card.status === "submitting"
          ? i18nT("chat.recommendationWorkflow.running.submitting")
          : i18nT("chat.recommendationWorkflow.running.polling")
      }}
    </div>

    <template v-if="card.status === 'editing'">
      <header class="rec-wf-header">
        <div class="rec-wf-title-row">
          <h2 class="rec-wf-heading">{{ i18nT("chat.recommendationWorkflow.labels.title") }}</h2>
        </div>
        <div class="rec-wf-badge-row">
          <span class="rec-wf-context-badge">{{ i18nT("chat.recommendationWorkflow.labels.tagSurvivalSingle") }}</span>
        </div>
      </header>

      <div class="rec-edit-chip-row" role="group" :aria-label="i18nT('chat.recommendationWorkflow.editingChips.ariaGroup')">
        <span class="rec-edit-chip">{{ i18nT("chat.recommendationWorkflow.editingChips.regimens", { count: card.enabledRegimenCount }) }}</span>
        <span class="rec-edit-chip">{{ editingTaskChip }}</span>
        <span v-if="patientFieldCount > 0" class="rec-edit-chip">{{
          i18nT("chat.recommendationWorkflow.editingChips.patientFields", {
            filled: validation?.filledCount ?? 0,
            total: patientFieldCount,
          })
        }}</span>
      </div>
      <p v-if="patientCompletenessWarning" class="rec-patient-complete-hint">{{ patientCompletenessWarning }}</p>
    </template>

    <template v-else-if="card.status !== 'cancelled'">
      <section class="rec-so-section">
        <div class="rec-so-overview-head">
          <div class="rec-so-section-title">{{ i18nT("chat.predictionSubmittedSummary.sectionOverview") }}</div>
          <span v-if="card.status === 'completed'" class="rec-wf-status-pill rec-wf-status-pill--muted" role="status">
            {{ i18nT("chat.recommendationWorkflow.labels.completedBadge") }}
          </span>
        </div>
        <div class="rec-so-kv-grid">
          <div class="rec-so-kv">
            <span class="rec-so-k">{{ i18nT("chat.batchPrediction.labels.model") }}</span>
            <span class="rec-so-v">{{ overviewModelDisplay }}</span>
          </div>
          <div class="rec-so-kv">
            <span class="rec-so-k">{{ i18nT("chat.predictionSubmittedSummary.labels.algorithm") }}</span>
            <span class="rec-so-v">{{ overviewAlgorithmDisplay }}</span>
          </div>
          <div class="rec-so-kv">
            <span class="rec-so-k">{{ i18nT("chat.predictionSubmittedSummary.labels.task") }}</span>
            <span class="rec-so-v">{{ i18nT("chat.recommendationWorkflow.postSubmit.taskLabel") }}</span>
          </div>
          <div class="rec-so-kv">
            <span class="rec-so-k">{{ i18nT("chat.predictionSubmittedSummary.labels.mode") }}</span>
            <span class="rec-so-v">{{ i18nT("chat.recommendationWorkflow.postSubmit.modeLabel") }}</span>
          </div>
        </div>
      </section>
      <p class="rec-so-inline-summary">{{ postSubmitInlineSummary }}</p>
    </template>

    <p v-if="validation && validation.errorCount > 0 && !showReadonlySummaryGrid" class="rec-wf-validation-inline">
      {{ i18nT("chat.recommendationWorkflow.patientFeatures.validationIssuesBanner", { count: validation.errorCount }) }}
    </p>

    <div
      v-if="(card.status === 'editing' || card.status === 'failed') && card.enabledRegimenCount < 1 && !card.regimensLoading"
      class="rec-callout rec-callout--warn"
    >
      <div class="rec-callout-title">{{ i18nT("chat.recommendationWorkflow.banner.title") }}</div>
      <p class="rec-callout-desc">{{ i18nT("chat.recommendationWorkflow.banner.description") }}</p>
      <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="emitAction({ action: 'openRegimenManagement' })">
        {{ i18nT("chat.recommendationWorkflow.banner.openRegimens") }}
      </button>
    </div>

    <p v-if="card.regimensLoading && card.status === 'editing'" class="rec-muted-line">
      {{ i18nT("chat.recommendationWorkflow.labels.checkingRegimens") }}
    </p>
    <p v-else-if="card.regimensError" class="rec-error-text">{{ card.regimensError }}</p>

    <div v-if="card.submitError && showSubmitError" class="rec-alerts">
      <div class="rec-error-text">{{ card.submitError }}</div>
    </div>
    <p v-if="card.status === 'failed' && card.pollError" class="rec-error-text rec-poll-error">{{ card.pollError }}</p>

    <section class="rec-fields-section">
      <template v-if="!card.schema">
        <div v-if="card.modelsLoading" class="rec-muted-line">{{ i18nT("chat.batchPrediction.loadingModels") }}</div>
        <div v-else-if="card.modelsError" class="rec-error-text">{{ card.modelsError }}</div>
        <template v-else>
          <div class="field-grid field-grid-flat rec-wf-field-grid">
            <div class="field-block rec-wf-span-full">
              <label class="field-label">{{ i18nT("chat.recommendationWorkflow.modelSelect.targetLabel") }}</label>
              <select
                :value="card.selectedModelId ?? ''"
                class="rec-wf-pfc-input rec-wf-pfc-full-mt"
                :disabled="isBusy || card.schemaLoading"
                @change="onModelChange(($event.target as HTMLSelectElement).value)"
              >
                <option value="">{{ i18nT("chat.assistantAction.pleaseSelect") }}</option>
                <option v-for="m in card.models" :key="m.model_id" :value="m.model_id">
                  {{ recOptionLabels[m.model_id] || m.model_id }}{{ !m.has_schema ? i18nT("chat.recommendationWorkflow.modelSelect.noSchemaSuffix") : "" }}
                </option>
              </select>
              <p v-if="card.schemaLoading" class="rec-muted-line rec-schema-loading">
                {{ i18nT("chat.recommendationWorkflow.modelSelect.loadingSchema") }}
              </p>
              <p v-if="card.schemaError" class="rec-error-text">{{ card.schemaError }}</p>
            </div>
          </div>
        </template>
      </template>

      <template v-else-if="showReadonlySummaryGrid">
        <div class="rec-so-fields-heading">
          <div class="rec-so-section-title">{{ i18nT("chat.predictionSubmittedSummary.sectionFields") }}</div>
        </div>
        <p class="rec-so-treatment-hint">{{ i18nT("chat.recommendationWorkflow.postSubmit.treatmentVariablesHint") }}</p>
        <div class="rec-so-readonly-stack">
          <div v-for="grp in patientFieldGroups" :key="'ro-' + grp.key" class="rec-so-ro-group">
            <div v-if="grp.key !== '_default'" class="group-title">{{ grp.key }}</div>
            <div class="rec-ro-field-grid">
              <div v-for="f in grp.fields" :key="f.name" class="rec-ro-cell">
                <div class="rec-ro-label">{{ doctorFacingFeatureLabel(f) }}</div>
                <div class="rec-ro-value">{{ readonlyFieldDisplay(f) }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="rec-wf-form-stack">
          <div v-for="grp in patientFieldGroups" :key="grp.key" class="rec-wf-form-group">
            <div v-if="grp.key !== '_default'" class="group-title">{{ grp.key }}</div>
            <div class="field-grid field-grid-flat rec-wf-field-grid">
              <div v-for="f in grp.fields" :key="f.name" class="field-block">
                <label class="field-label">
                  {{ doctorFacingFeatureLabel(f) }}
                  <span v-if="f.required" class="rec-wf-req">*</span>
                  <span v-if="f.unit" class="rec-wf-unit">({{ f.unit }})</span>
                </label>
                <p v-if="f.reference_range" class="field-meta">{{ f.reference_range }}</p>
                <p v-if="f.description" class="field-meta">{{ f.description }}</p>

                <template v-if="f.type === 'binary'">
                  <div class="binary-radio-row">
                    <label class="tri-option tri-option-compact">
                      <input
                        type="radio"
                        :name="`rb-${card.card_id}-${f.name}`"
                        :checked="binaryValue(f.name) === 0"
                        :disabled="fieldsDisabled"
                        @change="emitField(f.name, 0)"
                      />
                      {{ i18nT("predictionPresentation.boolean.no") }}
                    </label>
                    <label class="tri-option tri-option-compact">
                      <input
                        type="radio"
                        :name="`rb-${card.card_id}-${f.name}`"
                        :checked="binaryValue(f.name) === 1"
                        :disabled="fieldsDisabled"
                        @change="emitField(f.name, 1)"
                      />
                      {{ i18nT("predictionPresentation.boolean.yes") }}
                    </label>
                  </div>
                </template>

                <select
                  v-else-if="f.type === 'categorical'"
                  class="rec-wf-pfc-input rec-wf-pfc-full-mt"
                  :disabled="fieldsDisabled"
                  :value="String(fieldStr(f.name))"
                  @change="emitField(f.name, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="">—</option>
                  <option v-for="op in f.options || []" :key="String(op)" :value="String(op)">{{ op }}</option>
                </select>

                <input
                  v-else-if="f.type === 'int'"
                  type="number"
                  step="1"
                  class="rec-wf-pfc-input rec-wf-pfc-full-mt"
                  :disabled="fieldsDisabled"
                  :value="fieldStr(f.name)"
                  @input="emitField(f.name, ($event.target as HTMLInputElement).value)"
                />

                <input
                  v-else-if="f.type === 'float'"
                  type="number"
                  step="any"
                  class="rec-wf-pfc-input rec-wf-pfc-full-mt"
                  :disabled="fieldsDisabled"
                  :value="fieldStr(f.name)"
                  @input="emitField(f.name, ($event.target as HTMLInputElement).value)"
                />

                <input
                  v-else
                  type="text"
                  class="rec-wf-pfc-input rec-wf-pfc-full-mt"
                  :disabled="fieldsDisabled"
                  :value="fieldStr(f.name)"
                  @input="emitField(f.name, ($event.target as HTMLInputElement).value)"
                />

                <div v-if="fieldErr(f.name)" class="rec-wf-field-err">{{ fieldErr(f.name) }}</div>
              </div>
            </div>
          </div>
        </div>

        <details class="rec-wf-accordion" :open="card.observedCompareExpanded ?? false" @toggle="onCompareToggle">
          <summary class="rec-wf-accordion-summary">
            <span class="rec-wf-accordion-chevron" aria-hidden="true">›</span>
            <span class="rec-wf-accordion-label">{{ i18nT("chat.recommendationWorkflow.compareOptional.summary") }}</span>
          </summary>
          <div class="rec-wf-accordion-body">
            <p class="rec-wf-accordion-hint">{{ i18nT("chat.recommendationWorkflow.compareOptional.hint") }}</p>
            <div class="field-grid field-grid-flat rec-wf-field-grid">
              <div v-for="k in REGIMEN_TREATMENT_FIELD_KEYS" :key="k" class="field-block">
                <label class="field-label">{{ observedTreatmentLabel(k) }}</label>
                <input
                  type="number"
                  step="any"
                  class="rec-wf-pfc-input rec-wf-pfc-full-mt"
                  :placeholder="observedPlaceholder(k)"
                  :disabled="fieldsDisabled"
                  :value="card.observedTreatmentValues[k]"
                  @input="onObservedInput(k, $event)"
                />
              </div>
            </div>
          </div>
        </details>
      </template>
    </section>

    <footer v-if="showActionRow" class="rec-wf-footer">
      <div class="rec-wf-action-row">
        <button
          type="button"
          class="wb-btn wb-btn-secondary rec-wf-footer-btn"
          :disabled="isBusy"
          @click="emitAction({ action: 'cancel', cardId: card.card_id })"
        >
          {{ i18nT("common.cancel") }}
        </button>
        <button
          type="button"
          class="wb-btn wb-btn-primary rec-wf-footer-btn rec-wf-footer-btn-primary"
          :disabled="isBusy || !card.selectedModelId || !card.schema || card.enabledRegimenCount < 1"
          @click="emitAction({ action: 'submit', cardId: card.card_id })"
        >
          {{ i18nT("chat.recommendationWorkflow.actions.submitJob") }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { filterNonTreatmentPatientFields } from "../../utils/recommendationPatientFeatures";
import { recommendationPatientFieldCoverageStats } from "../../utils/recommendationCoverageCheck";
import { analyzePredictionForm } from "../../utils/predictionFormValidation";
import type {
  PredictionFieldSchema,
  PredictionModelListItem,
  RecommendationWorkflowCardData,
  RecommendationWorkflowChatAction,
  RegimenTreatmentFieldKey,
} from "../../types";
import { doctorFacingFeatureLabel, formatSubmitSummaryFieldValue } from "../../utils/predictionPresentation";
import { extractKnownAlgorithmName } from "../../utils/predictionSubmittedSummaryPresentation";
import { buildPredictionModelOptionLabelMap, predictionModelPrimaryDisplayLabel } from "../../utils/modelPresentation";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "../../types";

const props = defineProps<{ card: RecommendationWorkflowCardData; embedded?: boolean }>();

const { t: i18nT } = useI18n();

const emit = defineEmits<{
  (e: "action", payload: RecommendationWorkflowChatAction): void;
}>();

const showSubmitError = computed(() => props.card.status === "editing" || props.card.status === "failed");

const showActionRow = computed(() => props.card.status === "editing" || props.card.status === "failed");

const fieldsDisabled = computed(
  () =>
    props.card.predictRunning ||
    props.card.status === "submitting" ||
    props.card.status === "polling" ||
    props.card.status === "completed",
);

function observedTreatmentLabel(k: RegimenTreatmentFieldKey): string {
  return i18nT(`chat.recommendationWorkflow.observedTreatment.${k}`);
}

function observedPlaceholder(k: RegimenTreatmentFieldKey): string {
  return String(k).includes("freq")
    ? String(i18nT("chat.recommendationWorkflow.observedTreatment.placeholderFreq"))
    : String(i18nT("chat.recommendationWorkflow.observedTreatment.placeholderDose"));
}

const recOptionLabels = computed(() =>
  buildPredictionModelOptionLabelMap(props.card.models || [], i18nT),
);

const isBusy = computed(
  () =>
    props.card.predictRunning ||
    props.card.status === "submitting" ||
    props.card.status === "polling",
);

const patientFields = computed(() =>
  props.card.schema ? filterNonTreatmentPatientFields(props.card.schema.fields) : [],
);

const patientFieldCount = computed(() => patientFields.value.length);

const validation = computed(() =>
  patientFields.value.length ? analyzePredictionForm(patientFields.value, props.card.formValues, i18nT) : null,
);

const showReadonlySummaryGrid = computed(
  () =>
    !!props.card.schema &&
    (props.card.status === "submitting" || props.card.status === "polling" || props.card.status === "completed"),
);

function readonlyFieldDisplay(f: PredictionFieldSchema): string {
  return formatSubmitSummaryFieldValue(f, props.card.formValues[f.name]);
}

function looksLikeInternalModelRegistryId(s: string): boolean {
  const t = String(s || "").trim();
  if (!t) return true;
  if (/^model[\w-]*$/i.test(t)) return true;
  if (/_(binary|multiclass)_classification$/i.test(t)) return true;
  if (/_cand_\d+_/i.test(t)) return true;
  return false;
}

const overviewModelDisplay = computed(() => {
  const sel = props.card.selectedModelId;
  const m = props.card.models.find((x) => x.model_id === sel);
  const primary = m ? predictionModelPrimaryDisplayLabel(m, i18nT) : "";
  const dn = String(props.card.schema?.display_name || "").trim();
  const cand = primary || dn;
  if (cand && !looksLikeInternalModelRegistryId(cand)) return cand;
  return i18nT("chat.predictionSubmittedSummary.friendlyModel.survival");
});

const overviewAlgorithmDisplay = computed(() => {
  const m = props.card.models.find((x) => x.model_id === props.card.selectedModelId);
  const display = String(m?.display_name || props.card.schema?.display_name || "");
  const id = String(m?.model_id || props.card.selectedModelId || "");
  const extracted = extractKnownAlgorithmName(display, id);
  return extracted || i18nT("common.na");
});

const postSubmitInlineSummary = computed(() => {
  const filled = validation.value?.filledCount ?? 0;
  const total = patientFieldCount.value;
  return String(
    i18nT("chat.recommendationWorkflow.postSubmit.inlineSummary", {
      count: props.card.enabledRegimenCount,
      filled,
      total,
    }),
  );
});

const editingTaskChip = computed(() => {
  const mt = String(props.card.schema?.model_type || "").toLowerCase();
  if (!props.card.schema) {
    return String(i18nT("chat.recommendationWorkflow.editingChips.taskPending"));
  }
  if (mt === "binary") return String(i18nT("chat.recommendationWorkflow.editingChips.taskBinary"));
  if (mt === "regression") return String(i18nT("chat.recommendationWorkflow.editingChips.taskRegression"));
  if (mt === "multiclass") return String(i18nT("chat.recommendationWorkflow.editingChips.taskMulticlass"));
  return String(i18nT("chat.recommendationWorkflow.editingChips.taskOther", { type: mt || "—" }));
});

const patientCompletenessWarning = computed(() => {
  const s = props.card.schema;
  if (!s || props.card.status !== "editing") return "";
  const cov = recommendationPatientFieldCoverageStats(s, props.card.formValues);
  if (cov.total === 0 || cov.filled >= cov.total) return "";
  if (!cov.ok) return String(i18nT("chat.recommendationWorkflow.validation.patientFieldsLowCompletion"));
  return String(i18nT("chat.recommendationWorkflow.validation.patientFieldsIncompleteSoft"));
});

function fieldErr(name: string): string {
  return validation.value?.fieldErrors[name] || "";
}

function fieldStr(name: string): string {
  const v = props.card.formValues[name];
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "true" : "";
  return String(v);
}

function binaryValue(name: string): 0 | 1 | null {
  const v = props.card.formValues[name];
  if (v === null || v === undefined || v === "") return null;
  if (v === false || v === 0 || v === "0" || v === "false") return 0;
  if (v === true || v === 1 || v === "1" || v === "true") return 1;
  return null;
}

function emitField(name: string, value: unknown) {
  emit("action", { action: "updateValue", cardId: props.card.card_id, name, value });
}

function onModelChange(id: string) {
  emit("action", { action: "selectModel", cardId: props.card.card_id, modelId: id || null });
}

function onObservedInput(k: RegimenTreatmentFieldKey, e: Event) {
  const raw = (e.target as HTMLInputElement).value;
  const n = raw === "" ? 0 : parseFloat(raw);
  emit("action", {
    action: "updateObservedTreatment",
    cardId: props.card.card_id,
    key: k,
    value: Number.isFinite(n) ? n : 0,
  });
}

function onCompareToggle(e: Event) {
  const el = e.target as HTMLDetailsElement;
  if (!(el instanceof HTMLDetailsElement)) return;
  emit("action", {
    action: "setObservedCompareExpanded",
    cardId: props.card.card_id,
    expanded: el.open,
  });
}

function emitAction(payload: RecommendationWorkflowChatAction) {
  emit("action", payload);
}

type Group = { key: string; fields: PredictionFieldSchema[] };

const patientFieldGroups = computed<Group[]>(() => {
  const fields = patientFields.value;
  const map = new Map<string, PredictionFieldSchema[]>();
  for (const f of fields) {
    const k = (f.group && f.group.trim()) || "_default";
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(f);
  }
  const out: Group[] = [];
  for (const [key, flds] of map.entries()) {
    out.push({ key, fields: flds });
  }
  out.sort((a, b) => {
    if (a.key === "_default") return -1;
    if (b.key === "_default") return 1;
    return a.key.localeCompare(b.key);
  });
  return out;
});
</script>

<style scoped>
.rec-primary-card {
  box-sizing: border-box;
  width: 100%;
  max-width: var(--wb-chat-workflow-card-max);
  margin: 4px 0 0;
  padding: 24px 28px 28px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  gap: 0;
}

.rec-primary-card--cancelled {
  padding: 16px 20px;
  background: #f9fafb;
  border-color: #e5e7eb;
  box-shadow: none;
}

.rec-cancelled-line {
  margin: 0;
  font-size: var(--wb-font-size-card-body);
  font-weight: 600;
  color: var(--wb-embed-submission-copy);
}

.rec-status-strip {
  margin: -24px -28px 16px;
  padding: 6px 28px;
  font-size: var(--wb-font-size-rec-meta);
  font-weight: 600;
  line-height: var(--wb-line-height-card);
  border-radius: 12px 12px 0 0;
}

.rec-status-strip--success {
  background: #ecfdf5;
  color: #065f46;
  border-bottom: 1px solid #a7f3d0;
}

.rec-status-strip--error {
  background: #fef2f2;
  color: #991b1b;
  border-bottom: 1px solid #fecaca;
}

.rec-status-strip--info {
  background: #f8fafc;
  color: #334155;
  border-bottom: 1px solid #e2e8f0;
}

/* Workflow form header — title row + badge row (not cramped single line) */
.rec-wf-header {
  margin-bottom: 8px;
}

.rec-wf-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px 14px;
}

.rec-wf-heading {
  margin: 0;
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--wb-font-size-rec-primary-title);
  font-weight: 700;
  color: var(--wb-embed-submission-copy);
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.rec-wf-status-pill {
  flex-shrink: 0;
  font-size: var(--wb-font-size-rec-meta);
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 999px;
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
  white-space: nowrap;
  line-height: 1.35;
}

.rec-wf-status-pill--muted {
  font-size: 13px;
  font-weight: 600;
  padding: 3px 10px;
  background: #f8fafc;
  color: var(--wb-embed-submission-copy);
  border-color: #e2e8f0;
}

.rec-so-section {
  margin-bottom: 0;
}

.rec-so-overview-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px 14px;
  margin-bottom: 6px;
}

.rec-so-section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--wb-embed-submission-copy);
  letter-spacing: 0.02em;
  margin: 0;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(55, 71, 79, 0.12);
  flex: 1 1 auto;
  min-width: 0;
}

.rec-so-kv-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-1) var(--wb-space-2);
  font-size: 15px;
}

@media (min-width: 720px) {
  .rec-so-kv-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.rec-so-kv {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-micro);
  min-width: 0;
}

.rec-so-k {
  color: var(--wb-embed-submission-copy);
  font-weight: 600;
  font-size: 15px;
}

.rec-so-v {
  color: var(--wb-embed-submission-copy);
  font-weight: 400;
  word-break: break-word;
  font-size: 15px;
}

.rec-so-inline-summary {
  margin: 0 0 12px;
  padding: 0;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.45;
  color: var(--wb-embed-submission-copy);
}

.rec-so-fields-heading {
  margin-bottom: 6px;
}

.rec-so-treatment-hint {
  margin: 0 0 var(--wb-space-2);
  font-size: 14px;
  line-height: 1.45;
  color: var(--wb-embed-submission-copy);
}

.rec-so-readonly-stack {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.rec-ro-field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-1) var(--wb-chat-input-padding-y);
}

@media (min-width: 640px) {
  .rec-ro-field-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1100px) {
  .rec-ro-field-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.rec-ro-cell {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: var(--wb-radius-xs);
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
  min-width: 0;
  box-sizing: border-box;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
}

.rec-ro-label {
  font-size: 15px;
  color: var(--wb-embed-submission-copy);
  font-weight: 600;
  line-height: 1.4;
}

.rec-ro-value {
  margin-top: 4px;
  font-size: 15px;
  font-weight: 400;
  line-height: 1.4;
  letter-spacing: 0;
  color: var(--wb-embed-submission-copy);
  word-break: break-word;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}

.rec-wf-badge-row {
  margin-top: 6px;
}

.rec-wf-context-badge {
  display: inline-block;
  font-size: var(--wb-font-size-rec-meta);
  padding: 4px 12px;
  border-radius: 999px;
  background: #f3f4f6;
  color: var(--wb-embed-submission-copy);
  border: 1px solid #e5e7eb;
  white-space: nowrap;
  line-height: 1.35;
}

.rec-wf-meta-inline {
  margin: 0 0 12px;
  padding: 0;
  font-size: var(--wb-font-size-rec-meta);
  color: var(--wb-embed-submission-copy);
  line-height: var(--wb-line-height-card);
}

.rec-wf-validation-inline {
  margin: 0 0 10px;
  font-size: var(--wb-font-size-rec-warn);
  color: #b00020;
  line-height: var(--wb-line-height-card);
}

.rec-callout {
  padding: 12px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.rec-callout--warn {
  border: 1px solid #e8d4b8;
  background: #fffaf3;
}

.rec-callout-title {
  font-weight: 700;
  font-size: var(--wb-font-size-rec-label);
  color: #92400e;
  margin-bottom: 6px;
}

.rec-callout-desc {
  margin: 0 0 10px;
  font-size: var(--wb-font-size-rec-body);
  color: #1f2937;
  line-height: var(--wb-line-height-card);
}

.rec-muted-line {
  margin: 0 0 8px;
  font-size: var(--wb-font-size-rec-meta);
  color: var(--wb-embed-submission-copy);
  line-height: var(--wb-line-height-card);
}

.rec-schema-loading {
  margin-top: 8px;
}

.rec-error-text {
  margin: 0 0 8px;
  font-size: var(--wb-font-size-rec-body);
  color: #b00020;
  line-height: var(--wb-line-height-card);
}

.rec-poll-error {
  margin-bottom: 12px;
}

.rec-alerts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0 0 14px;
}

.rec-inline-warn {
  font-size: var(--wb-font-size-rec-warn);
  font-weight: 500;
  color: #9a3412;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 10px 12px;
  line-height: var(--wb-line-height-card);
}

.rec-fields-section {
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
  flex: 1 1 auto;
  min-height: 0;
}

/**
 * Field layout mirrors PredictionFormChatCard: `.field-grid` + `.field-grid-flat` + bordered `.field-block`,
 * pill radios (`.tri-option.tri-option-compact`), and `.rec-wf-pfc-input` aligned with `.pfc-control`.
 */
.rec-wf-form-stack {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.rec-wf-form-group {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-1);
}

.field-grid.rec-wf-field-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--wb-space-1) var(--wb-chat-input-padding-y);
}

@media (min-width: 720px) {
  .field-grid.rec-wf-field-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1100px) {
  .field-grid.rec-wf-field-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1400px) {
  .field-grid.rec-wf-field-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
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

.field-grid.rec-wf-field-grid > .field-block.rec-wf-span-full {
  grid-column: 1 / -1;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
  border: 1px solid var(--wb-border-subtle);
  background: #fff;
  border-radius: var(--wb-radius-xs);
  box-sizing: border-box;
}

.field-label {
  display: flex;
  align-items: baseline;
  gap: var(--wb-space-1);
  font-weight: 600;
  font-size: var(--wb-font-size-rec-label);
  color: var(--wb-embed-submission-copy);
}

.rec-wf-req {
  color: #b00020;
}

.rec-wf-unit {
  font-weight: 500;
  color: var(--wb-embed-submission-copy);
  font-size: var(--wb-font-size-rec-meta);
}

.rec-wf-pfc-input {
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

.rec-wf-pfc-full-mt {
  width: 100%;
  margin-top: var(--wb-space-1);
  box-sizing: border-box;
}

.rec-wf-field-err {
  font-size: var(--wb-font-size-rec-meta);
  color: #b00020;
  margin-top: var(--wb-space-micro);
  line-height: var(--wb-line-height-tight);
}

.group-title {
  font-size: var(--wb-font-size-rec-label);
  font-weight: 700;
  color: var(--wb-embed-submission-copy);
  margin: var(--wb-chat-input-padding-x) 0 var(--wb-chat-input-padding-y);
  border-bottom: 1px solid #e2eaf5;
  padding-bottom: var(--wb-space-micro);
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
  color: var(--wb-embed-submission-copy);
  padding: var(--wb-space-micro) var(--wb-chat-input-padding-y);
  border: 1px solid #dbe6f2;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  box-sizing: border-box;
}

.tri-option-compact {
  /* Match PredictionFormChatCard `.pfc-control` / `.tri-option-compact` height */
  min-height: var(--wb-control-height-sm);
  padding-top: 0;
  padding-bottom: 0;
  padding-left: var(--wb-chat-input-padding-y);
  padding-right: var(--wb-chat-input-padding-y);
}

.tri-option input {
  margin: 0;
}

.rec-wf-accordion {
  margin-top: var(--wb-space-2);
  border: 1px solid var(--wb-border-subtle);
  border-radius: var(--wb-radius-sm);
  background: #fff;
  overflow: hidden;
}

.rec-wf-accordion-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  cursor: pointer;
  font-weight: 600;
  font-size: var(--wb-font-size-rec-body);
  color: var(--wb-embed-submission-copy);
  list-style: none;
  background: #f9fafb;
  line-height: var(--wb-line-height-card);
}

.rec-wf-accordion-summary::-webkit-details-marker {
  display: none;
}

.rec-wf-accordion-chevron {
  display: inline-flex;
  width: 1.1rem;
  justify-content: center;
  font-size: 1rem;
  line-height: 1;
  color: var(--wb-embed-submission-copy);
  transition: transform 0.15s ease;
  flex-shrink: 0;
}

.rec-wf-accordion[open] .rec-wf-accordion-chevron {
  transform: rotate(90deg);
}

.rec-wf-accordion-label {
  flex: 1;
  line-height: inherit;
}

.rec-wf-accordion-body {
  padding: 10px 14px 14px;
  border-top: 1px solid #eef2f7;
  background: #f9fafb;
}

.rec-wf-accordion-hint {
  margin: 0 0 10px;
  font-size: var(--wb-font-size-rec-meta);
  color: var(--wb-embed-submission-copy);
  line-height: var(--wb-line-height-card);
}

.rec-wf-footer {
  flex-shrink: 0;
  margin-top: var(--wb-space-2);
  padding-top: var(--wb-chat-input-padding-y);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #f9fafb 35%, #f9fafb 100%);
  border-top: 1px solid #e8ebef;
  padding-bottom: var(--wb-space-micro);
}

.rec-wf-action-row {
  display: flex;
  gap: var(--wb-chat-input-padding-y);
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
}

.rec-wf-footer-btn {
  font-size: var(--wb-font-size-rec-meta);
}

.rec-wf-footer-btn-primary {
  font-weight: 600;
}

.rec-edit-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 0 0 14px;
}

.rec-edit-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 11px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--wb-embed-submission-copy);
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  max-width: 100%;
}

.rec-patient-complete-hint {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.45;
  font-weight: 500;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.rec-primary-card--editing-input {
  padding: 20px 22px 22px;
  gap: 0;
}

.rec-primary-card--editing-input .rec-wf-header {
  margin-bottom: 16px;
}

.rec-primary-card--editing-input .rec-wf-heading {
  font-size: 1.05rem;
  letter-spacing: -0.01em;
}

.rec-primary-card--editing-input .rec-edit-chip-row {
  margin-bottom: 16px;
}

.rec-primary-card--editing-input .rec-callout {
  margin-bottom: 18px;
}

.rec-primary-card--editing-input .rec-patient-complete-hint {
  margin-bottom: 18px;
}

.rec-primary-card--editing-input .rec-fields-section {
  margin-top: 10px;
  padding-top: 14px;
}

.rec-primary-card--editing-input .field-label {
  font-size: 14px;
  font-weight: 600;
}

.rec-primary-card--editing-input .field-meta {
  font-size: 13px;
}

.rec-primary-card--editing-input .rec-wf-pfc-input {
  font-size: 14px;
  min-height: 38px;
}

.rec-primary-card--editing-input .tri-option-compact {
  min-height: 38px;
  font-size: 13px;
}

.rec-primary-card--editing-input .field-grid.rec-wf-field-grid {
  grid-template-columns: minmax(0, 1fr);
}

@media (min-width: 720px) {
  .rec-primary-card--editing-input .field-grid.rec-wf-field-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1000px) {
  .rec-primary-card--editing-input .field-grid.rec-wf-field-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
