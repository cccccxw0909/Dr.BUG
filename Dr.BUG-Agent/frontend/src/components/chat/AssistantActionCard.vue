<template>
  <div
    class="assistant-action-card"
    :class="{ 'assistant-action-card--embedded': embedded }"
    data-testid="assistant-action-card"
  >
    <div class="assistant-card-head">
      <div class="assistant-card-title-wrap">
        <div v-if="!embedded" class="assistant-card-label">{{ i18nT("chat.assistantAction.cardLabel") }}</div>
        <div class="assistant-card-title">{{ actionText }}</div>
      </div>
      <span class="assistant-card-state" :class="cardStateClass">{{ cardStateLabel }}</span>
    </div>

    <div v-if="kv.length && !isTraining" class="assistant-param-section">
      <div class="assistant-section-title">{{ i18nT("chat.assistantAction.sectionCurrentParams") }}</div>
      <div
        v-if="isPredictionDraft"
        class="assistant-draft-hint"
      >
        {{ i18nT("chat.assistantAction.predictionDraftHint") }}
      </div>
      <div v-if="kvGridItems.length" class="assistant-kv-grid">
        <div v-for="item in kvGridItems" :key="item.key" class="assistant-kv-item">
          <div class="assistant-kv-label">{{ item.k }}</div>
          <div class="assistant-kv-value">{{ item.v }}</div>
        </div>
      </div>
      <div v-if="kvComplexItems.length" class="assistant-kv-complex-list">
        <div v-for="item in kvComplexItems" :key="item.key" class="assistant-param-row">
          <div class="assistant-param-key">{{ item.k }}:</div>
          <div class="assistant-param-complex">
            <div v-for="line in previewLines(item.key, item.raw)" :key="line">{{ line }}</div>
            <button v-if="hasMore(item.raw)" type="button" class="wb-btn wb-btn-text wb-btn-sm assistant-expand-btn" @click="toggleExpand(item.key)">
              {{ expanded[item.key] ? i18nT("chat.assistantAction.collapse") : i18nT("chat.assistantAction.expandAll") }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div
      v-if="pendingIsLive && effectiveMissingFields.length > 0 && !(isTraining && editing)"
      class="assistant-alert-shell assistant-alert-shell-error"
    >
      <div v-if="!isTraining" class="assistant-alert-title">{{ i18nT("chat.assistantAction.sectionMissingTitle") }}</div>
      <div class="assistant-alert-text">{{ missingText }}</div>
    </div>
    <div v-else-if="pendingIsLive && isPredictionDraft" class="assistant-alert-shell assistant-alert-shell-neutral">
      <div class="assistant-alert-title">{{ i18nT("chat.assistantAction.alertStatusTitle") }}</div>
      <div class="assistant-alert-text">{{ i18nT("chat.assistantAction.alertFillFeatures") }}</div>
    </div>

    <div
      v-if="isPredictionDraft && !confirmationSuccess && pendingIsLive"
      class="assistant-edit-shell assistant-edit-shell-predict"
    >
      <div class="assistant-edit-title">{{ i18nT("chat.assistantAction.patientFeaturesTitle") }}</div>
      <template v-if="predictionDraftFieldNames.length > 0">
        <div v-for="name in predictionDraftFieldNames" :key="name" class="assistant-predict-field-block">
          <label class="assistant-predict-field-label">{{ name }}</label>
          <input
            v-model="predictionFeatureInputs[name]"
            type="text"
            class="assistant-predict-field-input"
            :placeholder="i18nT('chat.assistantAction.placeholderFillFeature', { name })"
            autocomplete="off"
          />
        </div>
      </template>
      <template v-else>
        <div class="assistant-predict-fallback-hint">{{ i18nT("chat.assistantAction.predictionFallbackHint") }}</div>
        <textarea
          v-model="predictionFallbackJson"
          rows="4"
          class="assistant-predict-json-textarea"
          placeholder='{"feature_a": 1, "feature_b": 0.5}'
        />
      </template>
      <div v-if="!predictionDraftReady && pendingIsLive" class="assistant-predict-warn">
        {{ i18nT("chat.assistantAction.predictionWarnFill") }}
      </div>
    </div>
    <div v-if="pendingStatusText" style="margin-top:6px;color:#b00020;">{{ pendingStatusText }}</div>

    <div v-if="isTraining && editing && !confirmationSuccess" class="assistant-edit-shell assistant-edit-shell-train">
      <div v-if="datasetListError" class="assistant-dataset-err">{{ datasetListError }}</div>
      <div v-if="datasetSchemaError" class="assistant-dataset-err">{{ datasetSchemaError }}</div>
      <div v-if="datasetSwitchHint" class="assistant-dataset-hint">{{ datasetSwitchHint }}</div>
      <div v-if="trainingEditRequirementStrip" class="assistant-training-require-strip" role="status">
        {{ trainingEditRequirementStrip }}
      </div>

      <template v-for="sec in trainingEditorSections" :key="sec.id">
        <div
          v-if="sec.id !== 'advancedParams'"
          class="assistant-train-section"
          :class="'assistant-train-section-' + sec.id"
        >
          <div class="assistant-train-section-head">
            <span class="assistant-train-section-title">{{ i18nT(sec.titleKey) }}</span>
          </div>
          <div v-for="f in sec.fields" :key="sec.id + '-' + f.key" class="assistant-train-field-row">
            <label class="assistant-train-field-label">
              {{ f.label }}<span v-if="f.required" class="assistant-req-star">*</span>
              <button
                v-if="tooltipKeyForTrainingField(f.key)"
                type="button"
                class="assistant-field-help"
                :title="i18nT(tooltipKeyForTrainingField(f.key)!)"
                :aria-label="i18nT(tooltipKeyForTrainingField(f.key)!)"
              >
                ?
              </button>
            </label>
            <div v-if="f.key !== 'clinical_task_id' && f.description" class="assistant-train-field-desc">{{ f.description }}</div>

            <template v-if="f.key === 'dataset_id'">
              <template v-if="datasetDropdownAvailable">
                <select
                  :value="draft.dataset_id"
                  class="assistant-train-select-full"
                  @change="onDatasetSelectChange($event)"
                >
                  <option value="">{{ i18nT("chat.assistantAction.selectDataset") }}</option>
                  <option v-for="d in datasetList" :key="d.id" :value="d.id">{{ datasetOptionLabel(d, datasetList) }}</option>
                </select>
              </template>
              <p v-else class="assistant-dataset-empty">{{ i18nT("chat.assistantAction.datasetErrors.listEmpty") }}</p>
            </template>

            <select
              v-else-if="f.type === 'select' && !(f.key === 'target_column' && !hasDatasetColumns)"
              :value="String(getFieldValue(f.key) ?? '')"
              class="assistant-train-select-full"
              @change="setFieldValue(f.key, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">{{ i18nT("chat.assistantAction.pleaseSelect") }}</option>
              <option v-for="op in fieldOptions(f.key)" :key="op.value" :value="op.value">{{ op.label }}</option>
            </select>

            <div
              v-else-if="f.type === 'multiselect' && isColumnField(f.key)"
              class="assistant-multi-grid-shell"
              :class="{ 'is-disabled': !hasDatasetColumns }"
            >
              <label v-for="col in columnNames" :key="`${f.key}-${col}`" class="assistant-multi-grid-item">
                <input
                  type="checkbox"
                  :checked="arrayFieldValue(f.key).includes(col)"
                  :disabled="!hasDatasetColumns"
                  @change="toggleColumnInField(f.key, col, ($event.target as HTMLInputElement).checked)"
                />
                <span>{{ col }}</span>
              </label>
              <div v-if="!hasDatasetColumns" class="assistant-multi-grid-note">{{ i18nT("chat.assistantAction.noColumnsNote") }}</div>
            </div>
            <select
              v-else-if="f.type === 'multiselect'"
              multiple
              class="assistant-train-multiselect"
              :value="arrayFieldValue(f.key)"
              @change="onMultiSelectChange(f.key, $event)"
            >
              <option v-for="col in columnOptions" :key="col.value" :value="col.value">{{ col.label }}</option>
            </select>

            <input
              v-else-if="f.type === 'switch'"
              type="checkbox"
              :checked="Boolean(getFieldValue(f.key))"
              @change="setFieldValue(f.key, ($event.target as HTMLInputElement).checked)"
            />

            <input
              v-else-if="f.type === 'number'"
              type="number"
              class="assistant-train-input-full"
              :min="f.min"
              :max="f.max"
              :step="f.step || 1"
              :value="Number(getFieldValue(f.key) ?? f.defaultValue ?? 0)"
              @input="setFieldValue(f.key, Number(($event.target as HTMLInputElement).value || 0))"
            />

            <textarea
              v-else-if="f.type === 'textarea'"
              class="assistant-train-textarea"
              :value="String(getFieldValue(f.key) ?? '')"
              @input="setFieldValue(f.key, ($event.target as HTMLTextAreaElement).value)"
              :placeholder="f.placeholder || ''"
            />

            <input
              v-else
              type="text"
              class="assistant-train-input-full"
              :value="String(getFieldValue(f.key) ?? '')"
              @input="setFieldValue(f.key, ($event.target as HTMLInputElement).value)"
              :placeholder="f.placeholder || ''"
            />
            <div v-if="isColumnField(f.key) && !hasDatasetColumns" class="assistant-column-hint">{{ i18nT("chat.assistantAction.columnFetchHint") }}</div>
            <div v-if="trainingFieldError(f.key)" class="assistant-field-err">{{ trainingFieldError(f.key) }}</div>
          </div>
        </div>

        <div
          v-else
          class="assistant-train-section assistant-train-section-advancedParams training-advanced-section"
        >
          <div class="assistant-train-section-head training-advanced-section-head">
            <span class="assistant-train-section-title">{{ i18nT(sec.titleKey) }}</span>
          </div>
          <div class="training-advanced-grid">
            <div class="training-advanced-check-row">
              <div v-if="advancedFieldEnableSearch" class="training-checkbox-row">
                <input
                  :id="'training-adv-' + advancedFieldEnableSearch.key"
                  type="checkbox"
                  :checked="Boolean(getFieldValue(advancedFieldEnableSearch.key))"
                  @change="
                    setFieldValue(advancedFieldEnableSearch.key, ($event.target as HTMLInputElement).checked)
                  "
                />
                <label class="training-checkbox-label-text" :for="'training-adv-' + advancedFieldEnableSearch.key">
                  {{ advancedFieldEnableSearch.label
                  }}<span v-if="advancedFieldEnableSearch.required" class="assistant-req-star">*</span>
                </label>
                <button
                  v-if="tooltipKeyForTrainingField(advancedFieldEnableSearch.key)"
                  type="button"
                  class="assistant-field-help"
                  :title="i18nT(tooltipKeyForTrainingField(advancedFieldEnableSearch.key)!)"
                  :aria-label="i18nT(tooltipKeyForTrainingField(advancedFieldEnableSearch.key)!)"
                >
                  ?
                </button>
              </div>
              <div v-if="advancedFieldCvShap" class="training-checkbox-row">
                <input
                  :id="'training-adv-' + advancedFieldCvShap.key"
                  type="checkbox"
                  :checked="Boolean(getFieldValue(advancedFieldCvShap.key))"
                  @change="setFieldValue(advancedFieldCvShap.key, ($event.target as HTMLInputElement).checked)"
                />
                <label class="training-checkbox-label-text" :for="'training-adv-' + advancedFieldCvShap.key">
                  {{ advancedFieldCvShap.label
                  }}<span v-if="advancedFieldCvShap.required" class="assistant-req-star">*</span>
                </label>
                <button
                  v-if="tooltipKeyForTrainingField(advancedFieldCvShap.key)"
                  type="button"
                  class="assistant-field-help"
                  :title="i18nT(tooltipKeyForTrainingField(advancedFieldCvShap.key)!)"
                  :aria-label="i18nT(tooltipKeyForTrainingField(advancedFieldCvShap.key)!)"
                >
                  ?
                </button>
              </div>
            </div>
            <div class="training-number-grid">
              <div v-if="advancedFieldMinFeatures" class="training-number-cell">
                <div class="training-number-inline">
                  <label class="training-number-label" :for="'training-adv-' + advancedFieldMinFeatures.key">
                    {{ advancedFieldMinFeatures.label
                    }}<span v-if="advancedFieldMinFeatures.required" class="assistant-req-star">*</span>
                  </label>
                  <input
                    :id="'training-adv-' + advancedFieldMinFeatures.key"
                    type="number"
                    class="assistant-train-input-full training-number-input"
                    :min="advancedFieldMinFeatures.min"
                    :max="advancedFieldMinFeatures.max"
                    :step="advancedFieldMinFeatures.step || 1"
                    :value="
                      Number(getFieldValue(advancedFieldMinFeatures.key) ?? advancedFieldMinFeatures.defaultValue ?? 0)
                    "
                    @input="
                      setFieldValue(
                        advancedFieldMinFeatures.key,
                        Number(($event.target as HTMLInputElement).value || 0),
                      )
                    "
                  />
                </div>
                <div v-if="trainingFieldError(advancedFieldMinFeatures.key)" class="assistant-field-err">
                  {{ trainingFieldError(advancedFieldMinFeatures.key) }}
                </div>
              </div>
              <div v-if="advancedFieldMaxFeatures" class="training-number-cell">
                <div class="training-number-inline">
                  <label class="training-number-label" :for="'training-adv-' + advancedFieldMaxFeatures.key">
                    {{ advancedFieldMaxFeatures.label
                    }}<span v-if="advancedFieldMaxFeatures.required" class="assistant-req-star">*</span>
                  </label>
                  <input
                    :id="'training-adv-' + advancedFieldMaxFeatures.key"
                    type="number"
                    class="assistant-train-input-full training-number-input"
                    :min="advancedFieldMaxFeatures.min"
                    :max="advancedFieldMaxFeatures.max"
                    :step="advancedFieldMaxFeatures.step || 1"
                    :value="
                      Number(getFieldValue(advancedFieldMaxFeatures.key) ?? advancedFieldMaxFeatures.defaultValue ?? 0)
                    "
                    @input="
                      setFieldValue(
                        advancedFieldMaxFeatures.key,
                        Number(($event.target as HTMLInputElement).value || 0),
                      )
                    "
                  />
                </div>
                <div v-if="trainingFieldError(advancedFieldMaxFeatures.key)" class="assistant-field-err">
                  {{ trainingFieldError(advancedFieldMaxFeatures.key) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div class="assistant-action-row assistant-action-row--training-edit">
        <button type="button" class="wb-btn wb-btn-secondary" :disabled="!validationReport.canSubmit" @click="saveEdit">
          {{ i18nT("chat.assistantAction.saveDraft") }}
        </button>
        <button type="button" class="wb-btn wb-btn-secondary" @click="cancelEdit">{{ i18nT("chat.assistantAction.cancel") }}</button>
        <button type="button" class="wb-btn wb-btn-primary" :disabled="confirmDisabled" @click="onConfirmClick">
          {{ i18nT("chat.assistantAction.startTraining") }}
        </button>
        <span v-if="validationReport.warnings.length > 0 && validationReport.canSubmit" class="assistant-action-inline-warn">
          {{ i18nT("chat.assistantAction.warningsCanSubmit", { count: validationReport.warnings.length }) }}
        </span>
      </div>
    </div>

    <div v-if="isTraining && confirmationSuccess" class="assistant-inline-banner assistant-inline-banner--success">
      {{ i18nT("chat.assistantAction.trainingConfirmSuccess") }}
    </div>
    <div v-else-if="isTraining && trainingInactiveNotice" class="assistant-inline-banner assistant-inline-banner--muted">
      {{ trainingInactiveNotice }}
    </div>
    <div v-else-if="!isTraining && confirmationSuccess" class="assistant-inline-banner assistant-inline-banner--success">
      {{ i18nT("chat.assistantAction.nonTrainingConfirmSuccess") }}
    </div>
    <div v-else-if="!isTraining && nonTrainingInactiveNotice" class="assistant-inline-banner assistant-inline-banner--muted">
      {{ nonTrainingInactiveNotice }}
    </div>

    <div v-if="inlineActionError" class="assistant-inline-banner assistant-inline-banner--error">
      <b>{{ i18nT("chat.assistantAction.submitFailedBold") }}</b>{{ inlineActionError }}{{ i18nT("chat.assistantAction.submitFailedTail") }}
    </div>

    <div v-if="showPrimaryActionRow" class="assistant-action-row">
      <button type="button" class="wb-btn wb-btn-primary" :disabled="confirmDisabled" @click="onConfirmClick">{{ confirmButtonLabel }}</button>
      <button type="button" class="wb-btn wb-btn-secondary" :disabled="modifyParamsDisabled" @click="startEdit">
        {{ isTraining ? i18nT("chat.assistantAction.modifySetup") : i18nT("chat.assistantAction.modifyParamsTrainingOnly") }}
      </button>
      <span v-if="isTraining && validationReport.warnings.length > 0 && validationReport.canSubmit" class="assistant-action-inline-warn">
        {{ i18nT("chat.assistantAction.warnBeforeSubmit") }}
      </span>
      <span v-if="isTraining && !pendingIsLive" class="assistant-inline-hint-wide">
        {{ i18nT("chat.assistantAction.noPendingHintBeforeStrong") }}<strong>{{ i18nT("chat.assistantAction.noPendingHintStrong") }}</strong>{{ i18nT("chat.assistantAction.noPendingHintAfterStrong") }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { getDatasetSchema, getDatasets } from "../../api";
import {
  createTrainingFieldSchemas,
  objectiveMetricOptionsForMlTaskType,
  TRAINING_PHASE1_ADVANCED_PARAM_KEYS,
  TRAINING_PHASE1_FEATURE_KEYS,
  TRAINING_PHASE1_SETUP_KEYS,
  type SelectOption,
  type TrainingFieldGroup,
  type TrainingFieldKey,
  type TrainingFieldSchema,
} from "../../config/trainingSchemas";
import type { ChatTurnData, DatasetMeta } from "../../types";
import { formatDisplayDateTime } from "../../utils/dateFormat";
import {
  inferMlTaskTypeFromClinicalTaskId,
  missingTrainingPhase1ParameterKeys,
  missingTrainingParameterKeys,
  normalizePhase1TrainingPayloadForSubmit,
  normalizeTrainingPayloadForSubmit,
  patchFromTrainingDraft,
  trainingDraftFromCompletedParams,
} from "../../utils/trainingPayloadBuilder";
import type { Translate } from "../../utils/messageSanitizer";
import { analyzeTrainingSubmission, type SchemaValidationMode } from "../../utils/trainingValidation";

const props = defineProps<{
  data: ChatTurnData;
  /** When inside chat-embed-card: no outer card chrome (border/radius/shadow). */
  embedded?: boolean;
  contextDatasetId?: string | null;
  /** Currently submitting pending_action_id; only this card shows the submitting state. */
  submittingActionId?: string | null;
  actionConfirmError?: { pendingActionId: string; message: string } | null;
}>();
const emit = defineEmits<{
  (e: "confirm", detail?: { patient_features: Record<string, unknown> }): void;
  (e: "editParams", payload: { updatedParams: Record<string, unknown>; missingFields: string[] }): void;
}>();

const { t: i18nT, te } = useI18n();

const i18nTranslate: Translate = (key, values) => i18nT(key, (values ?? {}) as Record<string, unknown>);

const trainingFieldSchemas = computed(() => createTrainingFieldSchemas(i18nTranslate));

function schemasForKeys(keys: readonly TrainingFieldKey[]): TrainingFieldSchema[] {
  const set = new Set<string>(keys as unknown as string[]);
  return trainingFieldSchemas.value.filter((f) => set.has(f.key));
}

const trainingPhase1SetupFields = computed(() => schemasForKeys(TRAINING_PHASE1_SETUP_KEYS));
const trainingPhase1FeatureFields = computed(() => schemasForKeys(TRAINING_PHASE1_FEATURE_KEYS));
const trainingPhase1AdvancedParamFields = computed(() => schemasForKeys(TRAINING_PHASE1_ADVANCED_PARAM_KEYS));

const trainingEditorSections = computed(() => [
  { id: "setup", titleKey: "chat.assistantAction.trainingSections.sectionA", fields: trainingPhase1SetupFields.value },
  { id: "features", titleKey: "chat.assistantAction.trainingSections.sectionB", fields: trainingPhase1FeatureFields.value },
  { id: "advancedParams", titleKey: "chat.assistantAction.trainingSections.sectionC", fields: trainingPhase1AdvancedParamFields.value },
]);

const advancedFieldEnableSearch = computed(() =>
  trainingPhase1AdvancedParamFields.value.find((f) => f.key === "enable_feature_set_search") ?? null,
);
const advancedFieldCvShap = computed(() => trainingPhase1AdvancedParamFields.value.find((f) => f.key === "use_cv_shap") ?? null);
const advancedFieldMinFeatures = computed(() => trainingPhase1AdvancedParamFields.value.find((f) => f.key === "min_features") ?? null);
const advancedFieldMaxFeatures = computed(() => trainingPhase1AdvancedParamFields.value.find((f) => f.key === "max_features") ?? null);

function tooltipKeyForTrainingField(key: TrainingFieldKey): string | null {
  const map: Partial<Record<TrainingFieldKey, string>> = {
    clinical_task_id: "training.schemas.tooltips.clinical_task_id",
    ml_task_type: "training.schemas.tooltips.ml_task_type",
    selected_features: "training.schemas.tooltips.selected_features",
    med_cols: "training.schemas.tooltips.med_cols",
    enable_feature_set_search: "training.schemas.tooltips.enable_feature_set_search",
    use_cv_shap: "training.schemas.tooltips.use_cv_shap",
  };
  return map[key] ?? null;
}

const expanded = reactive<Record<string, boolean>>({});

type DraftShape = ReturnType<typeof trainingDraftFromCompletedParams>;
const draft = reactive(trainingDraftFromCompletedParams(props.data.completed_params || {}));

const datasetList = ref<DatasetMeta[]>([]);
const datasetListError = ref("");

const datasetSchemaError = ref("");
const datasetSwitchHint = ref("");

const columnNames = ref<string[]>([]);
const schemaLoading = ref(false);

const confirmValidationColumns = ref<string[]>([]);
const confirmSchemaMode = ref<SchemaValidationMode>("none");
let confirmSchemaFetchGen = 0;

const datasetUserTouched = ref(false);

/** Legacy publish group removed from Phase 1 editor UI */
const groupExpanded = reactive<Record<TrainingFieldGroup, boolean>>({
  data_task: true,
  feature_columns: true,
  advanced: false,
  publish: false,
});

const editing = ref(false);
const isTraining = computed(
  () =>
    props.data.recognized_action === "create_training_job" ||
    props.data.recognized_action === "draft_training_job",
);

const isPredictionDraft = computed(() => props.data.recognized_action === "draft_single_prediction");

const predictionDraftFieldNames = computed(() => {
  const raw = (props.data.completed_params as Record<string, unknown> | undefined)?.draft_schema_field_names;
  return Array.isArray(raw) ? raw.map((x) => String(x)) : [];
});

const predictionFeatureInputs = reactive<Record<string, string>>({});
const predictionFallbackJson = ref("");

watch(
  () =>
    [
      props.data.pending_confirmation?.pending_action_id ?? "",
      predictionDraftFieldNames.value.join("\x00"),
    ] as const,
  () => {
    if (!isPredictionDraft.value) return;
    Object.keys(predictionFeatureInputs).forEach((k) => delete predictionFeatureInputs[k]);
    for (const n of predictionDraftFieldNames.value) predictionFeatureInputs[n] = "";
    predictionFallbackJson.value = "";
  },
  { immediate: true },
);

function coerceFeatureValue(raw: string): string | number | boolean {
  const trimmed = raw.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  const n = Number(trimmed);
  if (trimmed !== "" && !Number.isNaN(n) && /^-?\d*\.?\d+(e[+-]?\d+)?$/i.test(trimmed)) return n;
  return trimmed;
}

function buildPatientFeaturesForConfirm(): Record<string, unknown> {
  const names = predictionDraftFieldNames.value;
  if (names.length > 0) {
    const out: Record<string, unknown> = {};
    for (const n of names) {
      const raw = String(predictionFeatureInputs[n] ?? "").trim();
      if (raw === "") continue;
      out[n] = coerceFeatureValue(raw);
    }
    return out;
  }
  const rawJson = predictionFallbackJson.value.trim();
  const parsed = JSON.parse(rawJson) as unknown;
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error(i18nT("chat.assistantAction.errors.predictionJsonMustBeObject"));
  }
  return { ...(parsed as Record<string, unknown>) };
}

const predictionDraftReady = computed(() => {
  if (!isPredictionDraft.value) return false;
  const names = predictionDraftFieldNames.value;
  if (names.length > 0) {
    return names.every((n) => String(predictionFeatureInputs[n] ?? "").trim() !== "");
  }
  const rawTrim = predictionFallbackJson.value.trim();
  if (!rawTrim) return false;
  try {
    const o = JSON.parse(rawTrim) as unknown;
    return typeof o === "object" && o !== null && !Array.isArray(o) && Object.keys(o as object).length > 0;
  } catch {
    return false;
  }
});

function onConfirmClick() {
  if (isPredictionDraft.value) {
    try {
      const patient_features = buildPatientFeaturesForConfirm();
      if (!patient_features || Object.keys(patient_features).length === 0) {
        return;
      }
      emit("confirm", { patient_features });
    } catch {
      /* The button should be disabled when predictionDraftReady is false; keep this as a fallback. */
    }
    return;
  }
  emit("confirm");
}

const confirmationSuccess = computed(() => props.data.confirmation_outcome === "success");

/** Match the backend: confirm only a complete pending action with status=pending; missing-parameter drafts often have no pending action and must not be treated as finished. */
const pendingIsLive = computed(() => {
  const p = props.data.pending_confirmation;
  return Boolean(
    p && typeof p === "object" && p.status === "pending" && typeof p.pending_action_id === "string" && p.pending_action_id.length > 0,
  );
});

const clinicalForMlInference = computed(() => {
  if (editing.value && isTraining.value) {
    return String(draft.clinical_task_id || "").trim();
  }
  return String((props.data.completed_params as Record<string, unknown> | undefined)?.clinical_task_id ?? "").trim();
});

/** Server missing_fields minus ML type when it is implied by the clinical task (demo inference). */
const effectiveMissingFields = computed(() => {
  const raw = props.data.missing_fields ?? [];
  if (!isTraining.value) return raw;
  const inferred = inferMlTaskTypeFromClinicalTaskId(clinicalForMlInference.value);
  if (!inferred) return raw;
  return raw.filter((k) => k !== "ml_task_type");
});

/** Locale-aware join for top-of-card training missing-field line. */
function formatTrainingMissingList(labels: string[]): string {
  if (labels.length === 0) return "";
  const parts = labels.map((s, i) => (i === 0 ? s : s.charAt(0).toLowerCase() + s.slice(1)));
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) {
    return i18nT("chat.listConjunction.two", { first: parts[0], second: parts[1] });
  }
  return i18nT("chat.listConjunction.many", {
    items: parts.slice(0, -1).join(i18nT("chat.listSeparator")),
    last: parts[parts.length - 1],
  });
}

const trainingInactiveNotice = computed(() => {
  if (!isTraining.value || confirmationSuccess.value || pendingIsLive.value) return "";
  const p = props.data.pending_confirmation;
  if (p && p.status !== "pending") {
    return i18nT("chat.assistantAction.trainingInactive.notPendingWithStatus", { status: String(p.status) });
  }
  if (!p && (effectiveMissingFields.value?.length ?? 0) > 0) {
    return "";
  }
  if (!p) {
    return i18nT("chat.assistantAction.trainingInactive.noPendingAfterSubmit");
  }
  return "";
});

const nonTrainingInactiveNotice = computed(() => {
  if (isTraining.value || isPredictionDraft.value || confirmationSuccess.value || pendingIsLive.value || !props.data.recognized_action)
    return "";
  const p = props.data.pending_confirmation;
  if (p && p.status !== "pending") {
    return i18nT("chat.assistantAction.nonTrainingInactive.notPendingWithStatus", { status: String(p.status) });
  }
  if (!p && (effectiveMissingFields.value?.length ?? 0) > 0) return "";
  if (!p) {
    return i18nT("chat.assistantAction.nonTrainingInactive.noPendingDone");
  }
  return "";
});

/** When parameters are missing, the backend often does not create a pending action; still show the action row so users can open the editor and fill gaps. */
const showPrimaryActionRow = computed(() => {
  if (confirmationSuccess.value) return false;
  if (isTraining.value && editing.value) return false;
  if (isTraining.value) return true;
  if (isPredictionDraft.value) return true;
  return pendingIsLive.value;
});

const isSubmittingThisCard = computed(
  () =>
    !!props.submittingActionId &&
    props.submittingActionId === props.data.pending_confirmation?.pending_action_id,
);

const inlineActionError = computed(() => {
  const pid = props.data.pending_confirmation?.pending_action_id;
  if (!pid || !props.actionConfirmError) return "";
  if (props.actionConfirmError.pendingActionId !== pid) return "";
  return props.actionConfirmError.message;
});

watch(
  () => props.data.pending_confirmation?.pending_action_id,
  () => {
    datasetUserTouched.value = false;
  },
);

watch(
  () => props.data.pending_confirmation,
  (p) => {
    if (!p && editing.value) editing.value = false;
  },
);

async function syncConfirmValidationSchema(datasetIdRaw: string) {
  const id = String(datasetIdRaw || "").trim();
  if (!id) {
    confirmValidationColumns.value = [];
    confirmSchemaMode.value = "none";
    return;
  }
  const gen = ++confirmSchemaFetchGen;
  confirmSchemaMode.value = "loading";
  try {
    const resp = await getDatasetSchema(id);
    if (gen !== confirmSchemaFetchGen) return;
    const cols = (resp.schema.columns || []).map((c) => c.name);
    confirmValidationColumns.value = cols;
    confirmSchemaMode.value = cols.length > 0 ? "ok" : "fail";
  } catch {
    if (gen !== confirmSchemaFetchGen) return;
    confirmValidationColumns.value = [];
    confirmSchemaMode.value = "fail";
  }
}

watch(
  () => [isTraining.value, editing.value, props.data.completed_params?.dataset_id] as const,
  ([tr, ed, ds]) => {
    if (!tr || ed) return;
    void syncConfirmValidationSchema(String(ds || ""));
  },
  { immediate: true },
);

watch(
  () => isTraining.value,
  (tr) => {
    if (!tr) {
      confirmValidationColumns.value = [];
      confirmSchemaMode.value = "none";
    }
  },
);

const PREDICTION_PARAM_ALLOW = new Set([
  "model_id",
  "draft_schema_field_names",
  "prediction_mode",
]);

function predictionParamVisible(key: string): boolean {
  if (key === "patient_features") return false;
  if (PREDICTION_PARAM_ALLOW.has(key)) return true;
  return key.startsWith("draft_");
}

const kv = computed(() => {
  const p = (props.data.completed_params || {}) as Record<string, unknown>;
  const featureSelectionEnabled = toBoolLike(p.enable_feature_selection ?? p.enable_feature_set_search, true);
  const entries = Object.entries(props.data.completed_params || {});
  const filtered = isPredictionDraft.value ? entries.filter(([k]) => predictionParamVisible(k)) : entries;
  return filtered.map(([k, v]) => ({
    key: k,
    k: fieldLabel(k),
    kind: isComplex(v) ? "complex" : "primitive",
    v: isComplex(v) ? "" : displayPrimitiveValue(k, v, featureSelectionEnabled),
    raw: v,
  }));
});

function toBoolLike(v: unknown, defaultValue = true): boolean {
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  if (typeof v === "string") {
    const lower = v.trim().toLowerCase();
    if (!lower) return defaultValue;
    if (["false", "0", "no", "off"].includes(lower)) return false;
    if (["true", "1", "yes", "on"].includes(lower)) return true;
  }
  return defaultValue;
}

function displayPrimitiveValue(key: string, value: unknown, featureSelectionEnabled: boolean): string {
  // Presentation-only rule: when feature selection is disabled, show empty min/max feature counts.
  if (!featureSelectionEnabled && (key === "min_features" || key === "max_features")) return "";
  if (value === null || value === undefined) return "";
  return String(value);
}

const PARAM_PRIORITY = [
  "dataset_id",
  "clinical_task_id",
  "ml_task_type",
  "target_column",
  "model_type",
  "feature_source",
  "objective_metric",
  "selected_features",
  "med_cols",
  "final_features",
] as const;

const priorityIndex = new Map<string, number>(PARAM_PRIORITY.map((k, idx) => [k, idx]));

const kvGridItems = computed(() =>
  kv.value
    .filter((x) => x.kind === "primitive")
    .slice()
    .sort((a, b) => {
      const ia = priorityIndex.get(a.key) ?? 999;
      const ib = priorityIndex.get(b.key) ?? 999;
      if (ia !== ib) return ia - ib;
      return a.k.localeCompare(b.k);
    }),
);

const kvComplexItems = computed(() =>
  kv.value
    .filter((x) => x.kind !== "primitive")
    .slice()
    .sort((a, b) => {
      const ia = priorityIndex.get(a.key) ?? 999;
      const ib = priorityIndex.get(b.key) ?? 999;
      if (ia !== ib) return ia - ib;
      return a.k.localeCompare(b.k);
    }),
);

const datasetDropdownAvailable = computed(() => datasetList.value.length > 0 && !datasetListError.value);

function datasetBaseDisplayName(d: DatasetMeta): string {
  return String(d.file_name || d.name || "").trim();
}

/** yyyy-MM-dd for disambiguation labels (demo-facing; never append raw ids). */
function datasetUploadDateLabel(iso: string | undefined): string {
  if (!iso) return "";
  const raw = String(iso).trim();
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(raw);
  if (m) return m[1];
  const formatted = formatDisplayDateTime(raw);
  const m2 = /^(\d{4}-\d{2}-\d{2})/.exec(formatted);
  return m2 ? m2[1] : "";
}

function stableDatasetDisambigIndex(items: DatasetMeta[], d: DatasetMeta): number {
  const sorted = [...items].sort((a, b) => String(a.id).localeCompare(String(b.id)));
  return sorted.findIndex((x) => x.id === d.id) + 1;
}

function datasetOptionLabel(d: DatasetMeta, all: DatasetMeta[]): string {
  const base = datasetBaseDisplayName(d);
  const uploadDate = datasetUploadDateLabel(d.created_at);

  if (!base) {
    const unnamedPeers = all.filter((x) => !datasetBaseDisplayName(x));
    if (unnamedPeers.length > 1) {
      if (uploadDate) {
        return i18nT("chat.assistantAction.datasetOptionUnnamedWithDate", { date: uploadDate });
      }
      const idx = stableDatasetDisambigIndex(unnamedPeers, d);
      return i18nT("chat.assistantAction.datasetOptionUnnamedIndexed", { index: idx });
    }
    return i18nT("chat.assistantAction.datasetOptionUnnamed");
  }

  const sameBase = all.filter((x) => datasetBaseDisplayName(x) === base);
  if (sameBase.length > 1) {
    if (uploadDate) {
      return i18nT("chat.assistantAction.datasetOptionWithUploadDate", { name: base, date: uploadDate });
    }
    const idx = stableDatasetDisambigIndex(sameBase, d);
    return i18nT("chat.assistantAction.datasetOptionDuplicateFallback", { name: base, index: idx });
  }

  return base;
}

const actionText = computed(() => {
  const a = props.data.recognized_action;
  const map: Record<string, string> = {
    create_training_job: "chat.assistantAction.actionTitles.create_training_job",
    draft_training_job: "chat.assistantAction.actionTitles.draft_training_job",
    create_prediction_job: "chat.assistantAction.actionTitles.create_prediction_job",
    draft_single_prediction: "chat.assistantAction.actionTitles.draft_single_prediction",
    create_recommendation_job: "chat.assistantAction.actionTitles.create_recommendation_job",
    create_report_job: "chat.assistantAction.actionTitles.create_report_job",
  };
  const path = a ? map[a] : undefined;
  return path ? i18nT(path) : i18nT("chat.assistantAction.actionTitles.unknown");
});

const missingText = computed(() => {
  const fields = effectiveMissingFields.value;
  if (isTraining.value && fields.length > 0) {
    return i18nT("chat.assistantAction.trainingStillNeededLine", {
      items: formatTrainingMissingList(fields.map(fieldLabel)),
    });
  }
  return fields.map(fieldLabel).join(i18nT("chat.listSeparator"));
});
const pendingStatusText = computed(() => {
  const status = props.data.pending_confirmation?.status;
  if (!status || status === "pending") return "";
  if (status === "expired") return i18nT("chat.assistantAction.pendingStatus.expired");
  if (status === "superseded") return i18nT("chat.assistantAction.pendingStatus.superseded");
  return i18nT("chat.assistantAction.pendingStatus.unknown", { status });
});

const cardStateLabel = computed(() => {
  if (confirmationSuccess.value) return i18nT("chat.assistantAction.cardState.confirmed");
  if (pendingIsLive.value && effectiveMissingFields.value.length > 0) return i18nT("chat.assistantAction.cardState.missing");
  if (pendingIsLive.value && isPredictionDraft.value) return i18nT("chat.assistantAction.cardState.fill");
  if (pendingIsLive.value) return i18nT("chat.assistantAction.cardState.pending");
  if (pendingStatusText.value) return i18nT("chat.assistantAction.cardState.stale");
  return i18nT("chat.assistantAction.cardState.draft");
});

const cardStateClass = computed(() => {
  if (confirmationSuccess.value) return "is-success";
  if (pendingIsLive.value && effectiveMissingFields.value.length > 0) return "is-warning";
  if (pendingIsLive.value) return "is-pending";
  if (pendingStatusText.value) return "is-error";
  return "is-neutral";
});

const mergedPayloadForValidation = computed(() => {
  const base = props.data.completed_params || {};
  if (!isTraining.value) {
    if (editing.value) {
      const patch = patchFromTrainingDraft(draft as DraftShape);
      return normalizeTrainingPayloadForSubmit({ ...base, ...patch });
    }
    return normalizeTrainingPayloadForSubmit(base);
  }
  if (editing.value) {
    const patch = patchFromTrainingDraft(draft as DraftShape);
    return normalizePhase1TrainingPayloadForSubmit({ ...base, ...patch });
  }
  return normalizePhase1TrainingPayloadForSubmit(base);
});

/** Phase 1 editor: client-side required-field strip while drafting (not server missing_fields). */
const trainingEditRequirementStrip = computed(() => {
  if (!isTraining.value || !editing.value) return "";
  const keys = missingTrainingPhase1ParameterKeys(mergedPayloadForValidation.value as Record<string, unknown>, true);
  if (keys.length === 0) return "";
  return i18nT("chat.assistantAction.trainingStillNeededLine", {
    items: formatTrainingMissingList(keys.map(fieldLabel)),
  });
});

const validationSchemaMode = computed<SchemaValidationMode>(() => {
  if (!isTraining.value) return "none";
  if (editing.value) {
    const id = String(draft.dataset_id || "").trim();
    if (!id) return "none";
    if (datasetSchemaError.value) return "fail";
    if (schemaLoading.value) return "loading";
    if (columnNames.value.length > 0) return "ok";
    return "loading";
  }
  return confirmSchemaMode.value;
});

const validationValidColumns = computed(() => {
  if (validationSchemaMode.value !== "ok") return null;
  const cols = editing.value ? columnNames.value : confirmValidationColumns.value;
  return new Set(cols);
});

const validationReport = computed(() =>
  analyzeTrainingSubmission({
    normalizedPayload: mergedPayloadForValidation.value,
    rawPrimaryMetric: editing.value
      ? String(draft.primary_metric ?? "")
      : String((props.data.completed_params as Record<string, unknown> | undefined)?.primary_metric ?? ""),
    rawModelName: editing.value
      ? String(draft.model_name ?? "")
      : String((props.data.completed_params as Record<string, unknown> | undefined)?.model_name ?? ""),
    schemaMode: validationSchemaMode.value,
    validColumns: validationValidColumns.value,
    phase1Only: isTraining.value,
    t: i18nTranslate,
  }),
);

function trainingFieldError(key: TrainingFieldKey): string {
  return validationReport.value.fieldErrors[key] || "";
}

const confirmDisabled = computed(() => {
  if (!props.data.pending_confirmation) return true;
  if (props.data.pending_confirmation.status !== "pending") return true;
  if (isSubmittingThisCard.value) return true;
  if (isTraining.value) {
    return !validationReport.value.canSubmit;
  }
  if (isPredictionDraft.value) {
    return !predictionDraftReady.value;
  }
  if (!props.data.can_confirm) return true;
  if (effectiveMissingFields.value.length > 0) return true;
  return false;
});

const confirmButtonLabel = computed(() => {
  if (isSubmittingThisCard.value) return i18nT("chat.assistantAction.confirmCreating");
  if (isPredictionDraft.value) return i18nT("chat.assistantAction.confirmExecutePrediction");
  if (isTraining.value) return i18nT("chat.assistantAction.startTraining");
  return i18nT("chat.assistantAction.confirmExecute");
});

const modifyParamsDisabled = computed(() => {
  if (!isTraining.value) return true;
  return isSubmittingThisCard.value;
});

function fieldLabel(key: string): string {
  const assist = `chat.assistantAction.fieldLabels.${key}`;
  if (te(assist)) return i18nT(assist);
  const generic = `chat.fieldLabels.${key}`;
  if (te(generic)) return i18nT(generic);
  return key;
}
function isComplex(v: unknown): boolean {
  return typeof v === "object" && v !== null;
}
function toggleExpand(k: string) {
  expanded[k] = !expanded[k];
}
function flattenToLines(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item, idx) => `${idx + 1}. ${typeof item === "object" ? JSON.stringify(item) : String(item)}`);
  }
  if (typeof value === "object" && value !== null) {
    return Object.entries(value as Record<string, unknown>).map(([k, v]) => `${fieldLabel(k)}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`);
  }
  return [String(value)];
}
function previewLines(key: string, value: unknown): string[] {
  const lines = flattenToLines(value);
  if (expanded[key]) return lines;
  return lines.slice(0, 4);
}
function hasMore(value: unknown): boolean {
  return flattenToLines(value).length > 4;
}

const columnOptions = computed<SelectOption[]>(() => columnNames.value.map((name) => ({ label: name, value: name })));
const hasDatasetColumns = computed(() => columnNames.value.length > 0);
function isColumnField(key: TrainingFieldKey): boolean {
  return key === "target_column" || key === "selected_features" || key === "final_features" || key === "med_cols";
}
function arrayFieldValue(key: TrainingFieldKey): string[] {
  const value = getFieldValue(key);
  return Array.isArray(value) ? value.map((v) => String(v)) : [];
}
function fieldOptions(key: TrainingFieldKey): SelectOption[] {
  if (key === "target_column" && hasDatasetColumns.value) return columnOptions.value;
  if (key === "objective_metric") return objectiveMetricOptionsForMlTaskType(String(draft.ml_task_type || "binary"));
  const field = trainingFieldSchemas.value.find((f) => f.key === key);
  return field?.options || [];
}
function getFieldValue(key: TrainingFieldKey): unknown {
  if (key === "publish_overrides.model_id") return draft.publish_model_id;
  if (key === "publish_overrides.notes") return draft.publish_notes;
  return (draft as Record<string, unknown>)[key];
}
function setFieldValue(key: TrainingFieldKey, value: unknown) {
  if (key === "publish_overrides.model_id") {
    draft.publish_model_id = String(value ?? "");
    return;
  }
  if (key === "publish_overrides.notes") {
    draft.publish_notes = String(value ?? "");
    return;
  }
  (draft as Record<string, unknown>)[key] = value;
  if (key === "clinical_task_id") {
    const inf = inferMlTaskTypeFromClinicalTaskId(String(value ?? ""));
    if (inf) {
      draft.ml_task_type = inf;
      const options = objectiveMetricOptionsForMlTaskType(inf);
      const current = String(draft.objective_metric || "");
      if (!options.some((op) => op.value === current)) {
        draft.objective_metric = options[0]?.value || (inf === "regression" ? "mse" : "auroc");
      }
    }
  } else if (key === "ml_task_type") {
    const options = objectiveMetricOptionsForMlTaskType(String(value || "binary"));
    const current = String(draft.objective_metric || "");
    if (!options.some((op) => op.value === current)) {
      draft.objective_metric = options[0]?.value || "auroc";
    }
  }
}
function onMultiSelectChange(key: TrainingFieldKey, event: Event) {
  const target = event.target as HTMLSelectElement;
  const values = Array.from(target.selectedOptions).map((op) => op.value);
  setFieldValue(key, values);
}

function toggleColumnInField(key: TrainingFieldKey, col: string, checked: boolean) {
  const cur = new Set(arrayFieldValue(key));
  if (checked) cur.add(col);
  else cur.delete(col);
  setFieldValue(key, Array.from(cur));
}

function reconcileColumnFieldsWithSchema() {
  const valid = new Set(columnNames.value);
  datasetSwitchHint.value = "";
  if (valid.size === 0) return;

  const hints: string[] = [];
  const targetCol = String(draft.target_column || "").trim();
  if (targetCol && !valid.has(targetCol)) {
    draft.target_column = "";
    hints.push(i18nT("chat.assistantAction.hints.targetColumnInvalid"));
  }
  for (const key of ["selected_features", "final_features", "med_cols"] as const) {
    const arr = Array.isArray(draft[key]) ? [...draft[key]] : [];
    const kept = arr.filter((x) => valid.has(String(x)));
    const removed = arr.length - kept.length;
    if (removed > 0) {
      hints.push(i18nT("chat.assistantAction.hints.columnsRemoved", { field: fieldLabel(key), count: removed }));
    }
    draft[key] = kept;
  }
  if (hints.length) datasetSwitchHint.value = hints.join(" ");
}

async function loadDatasetListForEditor() {
  datasetListError.value = "";
  try {
    const res = await getDatasets();
    datasetList.value = res.items || [];
    if (datasetList.value.length === 0) {
      datasetListError.value = i18nT("chat.assistantAction.datasetErrors.listEmpty");
    }
  } catch (err) {
    datasetList.value = [];
    datasetListError.value = i18nT("chat.assistantAction.datasetErrors.listLoadFailed", { message: String(err) });
  }
}

async function loadDatasetSchema(datasetIdRaw: string, options: { fromUserDatasetChange?: boolean } = {}) {
  schemaLoading.value = true;
  try {
    const datasetId = String(datasetIdRaw || "").trim();
    datasetSchemaError.value = "";
    if (!datasetId) {
      columnNames.value = [];
      if (!options.fromUserDatasetChange) {
        datasetSchemaError.value = i18nT("chat.assistantAction.datasetErrors.noDatasetId");
      }
      return;
    }
    try {
      const resp = await getDatasetSchema(datasetId);
      columnNames.value = (resp.schema.columns || []).map((c) => c.name);
      if (columnNames.value.length === 0) {
        datasetSchemaError.value = i18nT("chat.assistantAction.datasetErrors.noColumnsParsed");
      }
      reconcileColumnFieldsWithSchema();
    } catch (err) {
      columnNames.value = [];
      datasetSchemaError.value = i18nT("chat.assistantAction.datasetErrors.schemaReadFailed", { message: String(err) });
    }
  } finally {
    schemaLoading.value = false;
  }
}

async function onDatasetSelectChange(event: Event) {
  const v = String((event.target as HTMLSelectElement).value || "").trim();
  draft.dataset_id = v;
  datasetUserTouched.value = true;
  datasetSwitchHint.value = "";
  await loadDatasetSchema(v, { fromUserDatasetChange: true });
}

async function startEdit() {
  if (!isTraining.value) return;
  Object.assign(draft, trainingDraftFromCompletedParams(props.data.completed_params || {}));
  if (!datasetUserTouched.value) {
    const ctx = props.contextDatasetId?.trim();
    if (ctx) draft.dataset_id = ctx;
  }
  datasetSwitchHint.value = "";
  await loadDatasetListForEditor();
  await loadDatasetSchema(String(draft.dataset_id || "").trim());
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
}

function saveEdit() {
  if (!validationReport.value.canSubmit) return;
  const patch = patchFromTrainingDraft(draft as DraftShape);
  const base = { ...(props.data.completed_params || {}), ...patch };
  const merged = isTraining.value ? normalizePhase1TrainingPayloadForSubmit(base) : normalizeTrainingPayloadForSubmit(base);
  const missingFields = isTraining.value
    ? missingTrainingPhase1ParameterKeys(merged, true)
    : missingTrainingParameterKeys(merged, true);
  emit("editParams", { updatedParams: merged, missingFields });
  editing.value = false;
}
</script>

<style scoped>
.assistant-action-card {
  margin-top: var(--wb-space-1);
  padding: var(--wb-space-3);
  border: 1px solid #e5e9ef;
  border-radius: var(--wb-radius-md);
  background: #fff;
  box-shadow: 0 1px 2px rgba(31, 41, 55, 0.04);
  max-width: 100%;
  box-sizing: border-box;
}

.assistant-action-card--embedded {
  margin-top: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.assistant-inline-banner {
  margin-top: 8px;
  padding: 8px 0 0;
  border-radius: 0;
  font-size: var(--wb-font-size-card-meta);
  border-top: 1px solid #eceff3;
}

.assistant-inline-banner--success {
  background: transparent;
  color: var(--wb-text-caption-muted);
}

.assistant-inline-banner--muted {
  background: transparent;
  color: var(--wb-text-caption-muted);
}

.assistant-inline-banner--error {
  padding: 8px;
  border-top: none;
  border-radius: 6px;
  background: #ffeef0;
  color: #b00020;
  font-size: var(--wb-font-size-card-body);
}

.assistant-action-inline-warn {
  font-size: var(--wb-font-size-card-meta);
  color: #7a5600;
}

.assistant-inline-hint-wide {
  flex-basis: 100%;
  font-size: var(--wb-font-size-card-meta);
  color: #57606a;
  line-height: 1.5;
}

.assistant-predict-field-block {
  margin-bottom: var(--wb-chat-bubble-padding-x);
}

.assistant-predict-field-label {
  display: block;
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
  margin-bottom: var(--wb-space-micro);
  line-height: var(--wb-line-height-tight);
}

.assistant-predict-field-input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  padding: var(--wb-space-1) var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-sm);
  min-height: var(--wb-control-height-sm);
}

.assistant-predict-fallback-hint {
  font-size: var(--wb-font-size-2xs);
  color: var(--wb-text-secondary);
  margin-bottom: var(--wb-chat-input-padding-y);
  line-height: var(--wb-line-height);
}

.assistant-predict-json-textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: var(--wb-font-size-2xs);
  line-height: var(--wb-line-height);
}

.assistant-predict-warn {
  margin-top: var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-2xs);
  color: #b00020;
  line-height: var(--wb-line-height);
}

.assistant-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.assistant-card-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.assistant-card-label {
  font-size: var(--wb-font-size-2xs);
  color: #7d8796;
  line-height: var(--wb-line-height-tight);
}

.assistant-card-title {
  font-size: var(--wb-font-size-md);
  font-weight: 650;
  color: #1f2937;
  line-height: var(--wb-line-height-tight);
}

.assistant-card-state {
  border-radius: 999px;
  border: 1px solid transparent;
  padding: var(--wb-chat-bubble-gap) var(--wb-chat-input-padding-y);
  font-size: var(--wb-font-size-2xs);
  line-height: var(--wb-line-height-tight);
}

.assistant-card-state.is-success {
  background: #f9fafb;
  color: var(--wb-text-body-secondary);
  border-color: #e5e7eb;
}

.assistant-card-state.is-warning {
  background: #fcf8f2;
  color: #8f6f3f;
  border-color: #ebdcc6;
}

.assistant-card-state.is-pending {
  background: #f4f1fb;
  color: #66588a;
  border-color: #ddd5ee;
}

.assistant-card-state.is-error {
  background: #fdf4f4;
  color: #8d5454;
  border-color: #eacfcf;
}

.assistant-card-state.is-neutral {
  background: #f3f4f6;
  color: #5f6775;
  border-color: #dde2ea;
}

.assistant-param-section {
  margin-top: 10px;
  padding: 8px;
  border: 1px solid #dfe6f0;
  border-radius: 8px;
  background: #fff;
}

.assistant-section-title {
  margin-bottom: 6px;
  font-size: var(--wb-font-size-card-meta);
  color: #576273;
  font-weight: 600;
}

.assistant-draft-hint {
  margin: 4px 0;
  padding: 8px;
  border-radius: 6px;
  background: #f1f6fb;
  font-size: var(--wb-font-size-card-meta);
  color: #4f647f;
  line-height: 1.5;
}

.assistant-param-row {
  margin: 5px 0;
}

.assistant-kv-grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 6px 10px;
}

.assistant-kv-item {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed #ecf1f6;
}

.assistant-kv-item:last-child {
  border-bottom: none;
}

.assistant-kv-label {
  color: #728095;
  font-size: var(--wb-font-size-card-meta);
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.assistant-kv-value {
  color: #1f2937;
  font-size: var(--wb-font-size-card-body);
  line-height: 1.5;
  font-weight: 560;
  overflow-wrap: anywhere;
}

.assistant-kv-complex-list {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px dashed #e7edf5;
}

.assistant-param-key {
  font-weight: 600;
  font-size: var(--wb-font-size-card-body);
}

.assistant-param-value,
.assistant-param-complex {
  margin-left: 8px;
  font-size: var(--wb-font-size-card-meta);
  color: #415164;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.assistant-expand-btn {
  margin-top: 4px;
}

.assistant-alert-shell {
  margin-top: 8px;
  border-radius: 8px;
  padding: 8px 10px;
}

.assistant-alert-shell-error {
  border: 1px solid #efc8cf;
  background: #fff5f6;
}

.assistant-alert-shell-neutral {
  border: 1px solid #e8ecf2;
  background: #fff;
}

.assistant-alert-title {
  font-size: var(--wb-font-size-card-meta);
  font-weight: 650;
  margin-bottom: 3px;
}

.assistant-alert-shell-error .assistant-alert-title,
.assistant-alert-shell-error .assistant-alert-text {
  color: #b00020;
}

.assistant-alert-shell-neutral .assistant-alert-title,
.assistant-alert-shell-neutral .assistant-alert-text {
  color: var(--wb-text-body-secondary);
}

.assistant-alert-text {
  font-size: var(--wb-font-size-card-body);
  line-height: 1.45;
}

.assistant-edit-shell {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #fff;
}

.assistant-edit-shell-predict {
  border: 1px solid #c7ddf6;
}

.assistant-edit-shell-train {
  margin-top: 10px;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
}

.assistant-edit-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.assistant-training-require-strip {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: var(--wb-font-size-card-meta);
  line-height: 1.45;
  color: #7a5600;
  background: #fcf8f2;
  border: 1px solid #ebdcc6;
}

.assistant-train-section {
  margin: 0 0 14px;
  padding: 0 0 14px;
  border: none;
  border-bottom: 1px solid #eef2f7;
  border-radius: 0;
  background: transparent;
}

.assistant-train-section:last-of-type {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.assistant-train-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.assistant-train-section-title {
  font-weight: var(--wb-detail-section-title-weight, 650);
  font-size: var(--wb-detail-section-title-size, 14px);
  line-height: var(--wb-line-height-tight, 1.3);
  color: #1f2937;
}

.training-advanced-section {
  padding: 6px 10px 8px;
}

.training-advanced-section-head {
  margin-bottom: 6px;
}

.training-advanced-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.training-advanced-check-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}

.training-checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  width: fit-content;
  max-width: 100%;
  min-width: 0;
}

.training-checkbox-label-text {
  font-weight: 500;
  font-size: var(--wb-font-size-sm, 13px);
  color: var(--wb-text-primary, #1f2937);
  cursor: pointer;
  flex: 0 1 auto;
  min-width: 0;
  line-height: 1.35;
}

.training-number-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.training-number-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.training-number-inline {
  display: grid;
  grid-template-columns: max-content minmax(96px, 1fr);
  gap: 10px;
  align-items: center;
}

.training-number-label {
  font-weight: 500;
  font-size: var(--wb-font-size-sm, 13px);
  color: var(--wb-text-primary, #1f2937);
  white-space: nowrap;
}

.training-number-input {
  width: 100%;
  max-width: 120px;
  box-sizing: border-box;
}

@media (max-width: 520px) {
  .training-advanced-check-row {
    grid-template-columns: 1fr;
  }

  .training-number-grid {
    grid-template-columns: 1fr;
  }
}

.assistant-train-advanced-details {
  margin: 10px 0;
  padding: 6px 8px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #f6f8fa;
}

.assistant-train-advanced-summary {
  cursor: pointer;
  font-weight: 600;
  font-size: var(--wb-font-size-card-body);
  color: #374151;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  list-style: none;
}

.assistant-train-advanced-summary::-webkit-details-marker {
  display: none;
}

.assistant-train-advanced-body {
  margin-top: 8px;
  padding-top: 4px;
  border-top: 1px solid #e5e7eb;
}

.assistant-train-group {
  margin: 10px 0;
  padding: 8px;
  border: 1px solid #e1e7f0;
  border-radius: 8px;
}

.assistant-train-group-toggle {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  background: #f5f8fc;
  border: none;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.assistant-train-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.assistant-train-group-badge {
  font-size: var(--wb-font-size-caption);
  font-weight: 500;
  color: #666;
}

.assistant-train-group-content {
  margin-top: 8px;
}

.assistant-train-field-row {
  margin-bottom: 6px;
}

.assistant-train-field-label {
  display: block;
  font-weight: 500;
}

.assistant-train-field-desc {
  font-size: var(--wb-font-size-card-meta);
  color: #666;
}

.assistant-multi-grid-shell {
  max-height: 176px;
  overflow: auto;
  border: 1px solid #ccd6e4;
  border-radius: 6px;
  padding: 4px 6px;
  background: #fff;
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 2px 8px;
}

.assistant-multi-grid-shell.is-disabled {
  background: #f5f5f5;
}

.assistant-multi-grid-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 26px;
  padding: 2px 6px;
  font-size: var(--wb-font-size-sm);
  cursor: pointer;
  line-height: 1.35;
}

.assistant-multi-grid-item span {
  font-size: inherit;
}

.assistant-multi-grid-item input[type="checkbox"] {
  margin: 0;
  width: 14px;
  height: 14px;
  flex: 0 0 auto;
}

.assistant-multi-grid-note {
  grid-column: 1 / -1;
  font-size: var(--wb-font-size-card-meta);
  color: #888;
  margin-top: 4px;
}

.assistant-action-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.assistant-action-card input,
.assistant-action-card select,
.assistant-action-card textarea {
  border: 1px solid #d2dbe7;
  border-radius: var(--wb-radius-sm);
  min-height: var(--wb-control-height-sm);
  padding: 0 var(--wb-chat-input-padding-y);
  background: #fff;
  font-size: var(--wb-font-size-table-cell);
}

.assistant-action-card textarea {
  padding-top: var(--wb-chat-input-padding-y);
}

.assistant-inline-text-btn {
  margin-top: 4px;
}

@media (min-width: 860px) {
  .assistant-kv-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 960px) {
  .assistant-multi-grid-shell {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1400px) {
  .assistant-multi-grid-shell {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.assistant-dataset-err {
  font-size: var(--wb-font-size-card-meta);
  color: #b00020;
  margin-bottom: 6px;
}

.assistant-dataset-hint {
  font-size: var(--wb-font-size-card-meta);
  color: #7a5600;
  margin-bottom: 6px;
}

.assistant-dataset-empty {
  margin: 0;
  font-size: var(--wb-font-size-card-meta);
  color: #57606a;
}

.assistant-req-star {
  color: #b00020;
}

.assistant-field-help {
  margin-left: 6px;
  width: 18px;
  height: 18px;
  padding: 0;
  border-radius: 999px;
  border: 1px solid #c9d4e3;
  background: #f6f8fa;
  color: #445467;
  font-size: var(--wb-font-size-caption);
  font-weight: 700;
  line-height: 1;
  cursor: help;
  vertical-align: middle;
}

.assistant-train-select-full,
.assistant-train-input-full {
  display: block;
  width: 100%;
  box-sizing: border-box;
}

.assistant-train-multiselect {
  display: block;
  width: 100%;
  min-height: 90px;
}

.assistant-train-textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  min-height: 60px;
}

.assistant-column-hint {
  font-size: var(--wb-font-size-card-meta);
  color: #57606a;
}

.assistant-field-err {
  font-size: var(--wb-font-size-card-meta);
  color: #b00020;
  margin-top: 4px;
}

.assistant-train-section-features {
  background: #fafbff;
}

.assistant-train-section-advancedParams {
  background: #f9fafb;
}

.assistant-train-section-advancedParams.training-advanced-section .assistant-field-help {
  flex-shrink: 0;
}
</style>
