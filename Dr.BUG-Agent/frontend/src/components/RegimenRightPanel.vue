<template>
  <div class="regimen-right">
    <div v-if="!regimen" class="regimen-right-empty wb-detail-text-helper">{{ i18nT("regimen.rightPanel.emptyHint") }}</div>
    <template v-else>
      <!-- TODO(regimens): Duplicate action — expose only when a duplicate API exists. -->

      <section class="regimen-right-card regimen-summary-card">
        <div class="regimen-right-card-title wb-detail-panel-section-title">{{ i18nT("regimen.rightPanel.sections.summary") }}</div>
        <dl class="wb-detail-summary-kv regimen-summary-compact">
          <div class="wb-detail-summary-row">
            <dt>{{ i18nT("regimen.rightPanel.summaryLabels.name") }}</dt>
            <dd>{{ regimen.regimen_name || i18nT("regimen.rightPanel.unnamed") }}</dd>
          </div>
          <div class="wb-detail-summary-row">
            <dt>{{ i18nT("regimen.rightPanel.summaryLabels.status") }}</dt>
            <dd>
              <span v-if="regimen.enabled" class="wb-status wb-status-success">{{ i18nT("regimen.rightPanel.statusEnabled") }}</span>
              <span v-else class="wb-status wb-status-pending">{{ i18nT("regimen.rightPanel.statusDisabled") }}</span>
            </dd>
          </div>
          <div class="wb-detail-summary-row">
            <dt>{{ i18nT("regimen.rightPanel.summaryLabels.regimenId") }}</dt>
            <dd class="wb-detail-summary-id">{{ regimen.regimen_id }}</dd>
          </div>
          <div class="wb-detail-summary-row">
            <dt>{{ i18nT("regimen.rightPanel.summaryLabels.notes") }}</dt>
            <dd>
              <span v-if="regimen.notes">{{ regimen.notes }}</span>
              <span v-else class="wb-detail-text-helper">{{ i18nT("regimen.rightPanel.noNotes") }}</span>
            </dd>
          </div>
          <div v-if="regimen.created_at" class="wb-detail-summary-row">
            <dt>{{ i18nT("regimen.rightPanel.summaryLabels.createdAt") }}</dt>
            <dd>{{ formatDisplayDateTime(regimen.created_at) }}</dd>
          </div>
          <div v-if="regimen.updated_at" class="wb-detail-summary-row">
            <dt>{{ i18nT("regimen.rightPanel.summaryLabels.updatedAt") }}</dt>
            <dd>{{ formatDisplayDateTime(regimen.updated_at) }}</dd>
          </div>
        </dl>
      </section>

      <section class="regimen-right-card">
        <div class="regimen-right-card-title wb-detail-panel-section-title">{{ i18nT("regimen.rightPanel.sections.composition") }}</div>

        <dl class="regimen-right-dl regimen-dose-unified">
          <div
            v-for="(row, idx) in orderedDoseRows"
            :key="row.key"
            class="regimen-right-dl-row"
            :class="{ 'regimen-dose-first-zero': showZeroDivider && idx === activeDoseRows.length }"
          >
            <dt>{{ row.label }}</dt>
            <dd>{{ row.display }}</dd>
          </div>
        </dl>
      </section>

      <section class="regimen-right-card regimen-actions-card">
        <div class="regimen-right-card-title wb-detail-panel-section-title">{{ i18nT("regimen.rightPanel.sections.actions") }}</div>
        <div class="regimen-right-action-row">
          <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="emit('regimenEditRequest', regimen)">
            {{ i18nT("regimen.rightPanel.actions.editRegimen") }}
          </button>
          <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" :disabled="saving" @click="toggleEnabled">
            {{
              regimen.enabled
                ? saving
                  ? i18nT("regimen.rightPanel.actions.disabling")
                  : i18nT("regimen.rightPanel.actions.disableRegimen")
                : saving
                  ? i18nT("regimen.rightPanel.actions.enabling")
                  : i18nT("regimen.rightPanel.actions.enableRegimen")
            }}
          </button>
          <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm regimen-btn-delete-soft" @click="emit('regimenDeleteRequest', regimen)">
            {{ i18nT("regimen.management.delete") }}
          </button>
        </div>
        <p v-if="error" class="regimen-right-error">{{ error }}</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ApiError, updateRegimen } from "../api";
import type { RegimenRecord, RegimenTreatmentFieldKey, RegimenTreatmentValues } from "../types";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "../types";
import { formatDisplayDateTime } from "../utils/dateFormat";
import { isDailyFreqField } from "../utils/regimenDosingPresentation";

const { t: i18nT, locale } = useI18n();

function treatmentFieldFormLabel(k: RegimenTreatmentFieldKey): string {
  return i18nT(`regimen.treatmentDisplay.fields.${k}.formLabel`);
}

function formatDoseDisplay(k: RegimenTreatmentFieldKey, n: number): string {
  if (isDailyFreqField(k)) {
    return String(i18nT("regimen.rightPanel.doseDisplay.freqPerDay", { value: n }));
  }
  return String(i18nT("regimen.rightPanel.doseDisplay.doseG", { value: n }));
}

const props = defineProps<{ regimen: RegimenRecord | null }>();

const emit = defineEmits<{
  (e: "regimenUpdated", r: RegimenRecord): void;
  (e: "regimenEditRequest", r: RegimenRecord): void;
  (e: "regimenDeleteRequest", r: RegimenRecord): void;
}>();

const saving = ref(false);
const error = ref("");

watch(
  () => props.regimen?.regimen_id,
  () => {
    error.value = "";
  },
);

function rowForKey(k: RegimenTreatmentFieldKey, tv: RegimenTreatmentValues) {
  return {
    key: k,
    label: treatmentFieldFormLabel(k),
    display: formatDoseDisplay(k, tv[k] ?? 0),
  };
}

const activeDoseRows = computed(() => {
  void locale.value;
  const r = props.regimen;
  if (!r?.treatment_values) return [];
  const tv = r.treatment_values as RegimenTreatmentValues;
  return REGIMEN_TREATMENT_FIELD_KEYS.filter((k) => (tv[k] ?? 0) !== 0).map((k) => rowForKey(k, tv));
});

const zeroDoseRows = computed(() => {
  void locale.value;
  const r = props.regimen;
  if (!r?.treatment_values) return [];
  const tv = r.treatment_values as RegimenTreatmentValues;
  return REGIMEN_TREATMENT_FIELD_KEYS.filter((k) => (tv[k] ?? 0) === 0).map((k) => rowForKey(k, tv));
});

const orderedDoseRows = computed(() => [...activeDoseRows.value, ...zeroDoseRows.value]);

const showZeroDivider = computed(() => activeDoseRows.value.length > 0 && zeroDoseRows.value.length > 0);

function normalizeTreatmentValues(raw: Record<string, unknown> | undefined): RegimenTreatmentValues {
  const o = {} as RegimenTreatmentValues;
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    const v = raw?.[k];
    const n = typeof v === "number" ? v : parseFloat(String(v));
    o[k] = Number.isFinite(n) ? n : 0;
  }
  return o;
}

async function toggleEnabled() {
  const r = props.regimen;
  if (!r) return;
  error.value = "";
  saving.value = true;
  try {
    const payload = {
      regimen_name: r.regimen_name,
      enabled: !r.enabled,
      notes: r.notes,
      treatment_values: normalizeTreatmentValues(r.treatment_values as unknown as Record<string, unknown>),
    };
    const { regimen: updated } = await updateRegimen(r.regimen_id, payload);
    emit("regimenUpdated", updated);
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : i18nT("regimen.rightPanel.toggleFailed");
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.regimen-right {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
  font-size: var(--wb-font-size-card-body);
  width: 100%;
  max-width: none;
  box-sizing: border-box;
  padding-bottom: var(--wb-space-4);
}

.regimen-right-empty {
  line-height: 1.45;
}

.regimen-right-card {
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface);
  padding: var(--wb-space-3);
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.regimen-summary-card.regimen-right-card {
  padding: var(--wb-space-2) var(--wb-space-3);
}

.regimen-summary-card .regimen-right-card-title {
  margin-bottom: var(--wb-space-2);
}

.regimen-summary-compact :deep(.wb-detail-summary-row) {
  padding: 5px 0;
  gap: var(--wb-space-1);
}

.regimen-summary-compact :deep(.wb-detail-summary-row dt) {
  font-size: var(--wb-font-size-xs);
  line-height: 1.35;
}

.regimen-summary-compact :deep(.wb-detail-summary-row dd) {
  font-size: var(--wb-font-size-sm);
  line-height: 1.35;
}

.regimen-right-card-title {
  margin-bottom: var(--wb-space-3);
}

.regimen-dose-unified {
  display: flex;
  flex-direction: column;
}

.regimen-dose-first-zero {
  border-top: 1px solid var(--wb-border);
  margin-top: var(--wb-space-1);
  padding-top: var(--wb-space-2);
}

.regimen-right-error {
  margin: var(--wb-space-2) 0 0;
  color: var(--wb-error);
  font-size: var(--wb-font-size-card-meta);
}

.regimen-right-dl {
  margin: 0;
}

.regimen-right-dl-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--wb-space-2);
  padding: 6px 0;
  border-bottom: 1px dashed var(--wb-border);
  font-size: var(--wb-font-size-sm);
  align-items: baseline;
}

.regimen-dose-unified .regimen-right-dl-row:last-child {
  border-bottom: none;
}

.regimen-right-dl dt {
  margin: 0;
  font-weight: 400;
  color: var(--wb-text-primary);
}

.regimen-right-dl dd {
  margin: 0;
  font-weight: 400;
  color: var(--wb-text-primary);
}

.regimen-right-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
}

.regimen-btn-delete-soft {
  border-color: #e8d5d5;
  color: #b45353;
}

.regimen-btn-delete-soft:hover:not(:disabled) {
  border-color: #e8c9c9;
  background: #fdf8f8;
  color: #991b1b;
}

.regimen-actions-card {
  padding-bottom: var(--wb-space-4);
}
</style>
