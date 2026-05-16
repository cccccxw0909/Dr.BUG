<template>
  <div class="regimen-section">
    <section v-if="loadError" class="regimen-alert regimen-alert-error wb-card">
      <div class="regimen-alert-title">
        <b>{{ i18nT("regimen.management.loadFailedBold") }}</b>{{ i18nT("regimen.management.loadFailedColon") }}{{ loadError }}
      </div>
      <button type="button" class="wb-btn wb-btn-secondary" @click="refresh">
        {{ i18nT("regimen.management.retry") }}
      </button>
    </section>

    <section class="regimen-toolbar wb-card">
      <div class="regimen-toolbar-row">
        <button type="button" class="wb-btn wb-btn-secondary" :disabled="loading" @click="refresh">
          {{ loading ? i18nT("common.refreshing") : i18nT("common.refresh") }}
        </button>
        <button
          type="button"
          class="wb-btn wb-btn-primary"
          :disabled="loading || saving || editingId !== null"
          @click="startCreate"
        >
          {{ i18nT("regimen.management.newRegimen") }}
        </button>
      </div>
    </section>

    <section v-if="panelError" class="regimen-alert regimen-alert-warning wb-card">
      {{ panelError }}
    </section>

    <div class="regimen-main-scroll">
      <div class="regimen-list-section-head">
        <h3 class="regimen-list-section-title">{{ i18nT("regimen.management.listSectionTitle") }}</h3>
        <span class="regimen-list-section-count">{{ i18nT("regimen.management.listCount", { count: items.length }) }}</span>
      </div>

      <section v-if="editingId === 'new'" class="regimen-form-shell wb-card regimen-form-shell-compact">
        <div class="regimen-form-body">
          <div class="regimen-fields">
            <div class="regimen-name-notes-block">
              <div class="regimen-label-pair-row">
                <span class="regimen-label">{{ i18nT("regimen.management.labels.regimenName") }}</span>
                <span class="regimen-label">{{ i18nT("regimen.management.labels.notes") }}</span>
              </div>
              <div class="regimen-input-pair-row">
                <input v-model="draft.regimen_name" class="regimen-input" type="text" :disabled="saving" />
                <textarea v-model="draft.notes" class="regimen-textarea regimen-notes-compact" rows="2" :disabled="saving" />
              </div>
              <label class="regimen-checkbox">
                <input v-model="draft.enabled" type="checkbox" :disabled="saving" />
                <span>{{ i18nT("regimen.management.labels.enabled") }}</span>
              </label>
            </div>
            <div class="regimen-numeric-block">
              <div v-for="g in REGIMEN_DOSE_FIELD_GROUPS" :key="g.key" class="regimen-dose-group">
                <div class="regimen-dose-group-title">{{ i18nT(`regimen.management.groups.${g.key}`) }}</div>
                <div class="regimen-numeric-grid">
                  <div v-for="k in g.fields" :key="k" class="regimen-num-cell">
                    <span class="regimen-dose-field-label">{{ treatmentFieldFormLabel(k) }}</span>
                    <div class="regimen-input-suffix-row">
                      <input
                        class="regimen-input regimen-input-in-suffix"
                        type="number"
                        step="any"
                        :disabled="saving"
                        :value="draft.treatment_values[k]"
                        @input="onTreatmentNumInput(k, $event)"
                      />
                      <span class="regimen-field-unit">{{ fieldUnitSuffix(k) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="regimen-form-actions">
          <button type="button" class="wb-btn wb-btn-secondary" :disabled="saving" @click="cancelEdit">
            {{ i18nT("regimen.management.cancel") }}
          </button>
          <button type="button" class="wb-btn wb-btn-primary" :disabled="saving" @click="submitCreate">
            {{ saving ? i18nT("regimen.management.saving") : i18nT("regimen.management.saveRegimen") }}
          </button>
        </div>
      </section>

      <template v-if="editingId !== 'new'">
        <div v-if="!loading && items.length === 0 && !loadError" class="regimen-empty wb-card">
          {{ i18nT("regimen.management.empty") }}
        </div>
        <div v-else-if="loading && items.length === 0 && !loadError" class="regimen-loading">
          {{ i18nT("regimen.management.loading") }}
        </div>

        <section
          v-for="r in items"
          :key="r.regimen_id"
          class="regimen-item-shell wb-card"
        :class="{
          'regimen-item-selected':
            props.selectedRegimenId === r.regimen_id && editingId !== r.regimen_id && editingId !== 'new',
        }"
        @click="onRegimenCardClick(r)"
      >
        <template v-if="editingId === r.regimen_id">
          <h3 class="regimen-form-title">{{ i18nT("regimen.management.formTitleEdit") }}</h3>
          <div class="regimen-form-body">
            <div class="regimen-fields">
              <div class="regimen-name-notes-block">
                <div class="regimen-label-pair-row">
                  <span class="regimen-label">{{ i18nT("regimen.management.labels.regimenName") }}</span>
                  <span class="regimen-label">{{ i18nT("regimen.management.labels.notes") }}</span>
                </div>
                <div class="regimen-input-pair-row">
                  <input v-model="draft.regimen_name" class="regimen-input" type="text" :disabled="saving" />
                  <textarea v-model="draft.notes" class="regimen-textarea regimen-notes-compact" rows="2" :disabled="saving" />
                </div>
                <label class="regimen-checkbox">
                  <input v-model="draft.enabled" type="checkbox" :disabled="saving" />
                  <span>{{ i18nT("regimen.management.labels.enabled") }}</span>
                </label>
              </div>
              <div class="regimen-numeric-block">
                <div class="regimen-numeric-title">{{ i18nT("regimen.management.numericSectionTitle") }}</div>
                <div v-for="g in REGIMEN_DOSE_FIELD_GROUPS" :key="g.key" class="regimen-dose-group">
                  <div class="regimen-dose-group-title">{{ i18nT(`regimen.management.groups.${g.key}`) }}</div>
                  <div class="regimen-numeric-grid">
                    <div v-for="k in g.fields" :key="k" class="regimen-num-cell">
                      <span class="regimen-dose-field-label">{{ treatmentFieldFormLabel(k) }}</span>
                      <div class="regimen-input-suffix-row">
                        <input
                          class="regimen-input regimen-input-in-suffix"
                          type="number"
                          step="any"
                          :disabled="saving"
                          :value="draft.treatment_values[k]"
                          @input="onTreatmentNumInput(k, $event)"
                        />
                        <span class="regimen-field-unit">{{ fieldUnitSuffix(k) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="regimen-form-actions">
            <button type="button" class="wb-btn wb-btn-secondary" :disabled="saving" @click="cancelEdit">
              {{ i18nT("regimen.management.cancel") }}
            </button>
            <button type="button" class="wb-btn wb-btn-primary" :disabled="saving" @click="submitUpdate(r.regimen_id)">
              {{ saving ? i18nT("regimen.management.saving") : i18nT("regimen.management.saveRegimen") }}
            </button>
          </div>
        </template>
        <template v-else>
          <div class="regimen-item-top">
            <div class="regimen-item-name">
              <span class="regimen-item-title">{{ r.regimen_name || i18nT("regimen.management.unnamed") }}</span>
              <span v-if="r.enabled" class="wb-status wb-status-success">{{ i18nT("regimen.management.statusEnabled") }}</span>
              <span v-else class="wb-status wb-status-pending">{{ i18nT("regimen.management.statusDisabled") }}</span>
            </div>
            <div class="regimen-item-actions">
              <button
                type="button"
                class="wb-btn wb-btn-sm wb-btn-edit"
                :disabled="editingId !== null || saving"
                @click.stop="startEdit(r)"
              >
                {{ i18nT("regimen.management.edit") }}
              </button>
              <button
                type="button"
                class="wb-btn wb-btn-sm wb-btn-danger regimen-delete-btn"
                :disabled="editingId !== null || saving"
                @click.stop="onDelete(r)"
              >
                {{ i18nT("regimen.management.delete") }}
              </button>
            </div>
          </div>
          <p v-if="r.notes" class="regimen-notes-preview">{{ r.notes }}</p>
        </template>
      </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ApiError, createRegimen, deleteRegimen, listRegimens, updateRegimen } from "../api";
import type { RegimenRecord, RegimenTreatmentFieldKey, RegimenTreatmentValues } from "../types";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "../types";
import { isDailyFreqField, REGIMEN_DOSE_FIELD_GROUPS } from "../utils/regimenDosingPresentation";

const { t: i18nT } = useI18n();

function treatmentFieldFormLabel(k: RegimenTreatmentFieldKey): string {
  return i18nT(`regimen.treatmentDisplay.fields.${k}.formLabel`);
}

function fieldUnitSuffix(k: RegimenTreatmentFieldKey): string {
  return isDailyFreqField(k) ? i18nT("regimen.management.units.freqPerDay") : i18nT("regimen.management.units.doseG");
}

type DraftForm = {
  regimen_name: string;
  enabled: boolean;
  notes: string;
  treatment_values: RegimenTreatmentValues;
};

const props = withDefaults(
  defineProps<{
    selectedRegimenId?: string | null;
    refreshSignal?: number;
  }>(),
  { selectedRegimenId: null, refreshSignal: 0 },
);

const emit = defineEmits<{
  (e: "selectRegimen", regimen: RegimenRecord): void;
  (e: "regimenDeleted", regimenId: string): void;
}>();

function onRegimenCardClick(r: RegimenRecord) {
  if (editingId.value) return;
  emit("selectRegimen", r);
}

const items = ref<RegimenRecord[]>([]);
const loading = ref(false);
const loadError = ref("");
const saving = ref(false);
const panelError = ref("");
const editingId = ref<string | "new" | null>(null);

const draft = reactive<DraftForm>(emptyDraft());

function emptyTreatmentValues(): RegimenTreatmentValues {
  const o = {} as RegimenTreatmentValues;
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    o[k] = 0;
  }
  return o;
}

function emptyDraft(): DraftForm {
  return {
    regimen_name: "",
    enabled: true,
    notes: "",
    treatment_values: emptyTreatmentValues(),
  };
}

function normalizeTreatmentValues(raw: Record<string, unknown> | undefined): RegimenTreatmentValues {
  const o = emptyTreatmentValues();
  if (!raw || typeof raw !== "object") return o;
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    const v = raw[k];
    const n = typeof v === "number" ? v : parseFloat(String(v));
    o[k] = Number.isFinite(n) ? n : 0;
  }
  return o;
}

function recordToDraft(r: RegimenRecord): DraftForm {
  return {
    regimen_name: r.regimen_name || "",
    enabled: !!r.enabled,
    notes: r.notes ?? "",
    treatment_values: normalizeTreatmentValues(r.treatment_values as unknown as Record<string, unknown>),
  };
}

function assignDraft(next: DraftForm) {
  draft.regimen_name = next.regimen_name;
  draft.enabled = next.enabled;
  draft.notes = next.notes;
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    draft.treatment_values[k] = next.treatment_values[k];
  }
}

function onTreatmentNumInput(k: RegimenTreatmentFieldKey, e: Event) {
  const raw = (e.target as HTMLInputElement).value;
  const n = raw === "" ? 0 : parseFloat(raw);
  draft.treatment_values[k] = Number.isFinite(n) ? n : 0;
}

async function refresh() {
  panelError.value = "";
  loadError.value = "";
  loading.value = true;
  try {
    const data = await listRegimens();
    items.value = data.items.map((it) => ({
      ...it,
      treatment_values: normalizeTreatmentValues(it.treatment_values as unknown as Record<string, unknown>),
    }));
  } catch (e) {
    loadError.value = e instanceof ApiError ? e.message : i18nT("regimen.management.requestFailed");
  } finally {
    loading.value = false;
  }
}

function nextDefaultRegimenName(): string {
  const prefix = i18nT("regimen.management.defaultNewRegimenPrefix");
  let max = 0;
  const escaped = prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^${escaped}\\s*(\\d+)\\s*$`, "i");
  for (const r of items.value) {
    const name = (r.regimen_name || "").trim();
    const m = name.match(re);
    if (m) max = Math.max(max, parseInt(m[1] || "0", 10) || 0);
  }
  return `${prefix} ${max + 1}`;
}

function regimenSaveUserMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "HTTP_ERROR" || /422|400/i.test(e.message)) {
      return i18nT("regimen.management.saveValidationHuman");
    }
    return e.message;
  }
  return i18nT("regimen.management.saveFailed");
}

function startCreate() {
  panelError.value = "";
  editingId.value = "new";
  assignDraft(emptyDraft());
  draft.regimen_name = nextDefaultRegimenName();
}

function startEdit(r: RegimenRecord) {
  panelError.value = "";
  editingId.value = r.regimen_id;
  assignDraft(recordToDraft(r));
}

function cancelEdit() {
  editingId.value = null;
  panelError.value = "";
  assignDraft(emptyDraft());
}

function buildPayload(): {
  regimen_name: string;
  enabled: boolean;
  notes: string | null;
  treatment_values: RegimenTreatmentValues;
} {
  const notes = draft.notes.trim();
  const tv = emptyTreatmentValues();
  for (const k of REGIMEN_TREATMENT_FIELD_KEYS) {
    tv[k] = draft.treatment_values[k];
  }
  return {
    regimen_name: draft.regimen_name.trim(),
    enabled: draft.enabled,
    notes: notes.length ? notes : null,
    treatment_values: tv,
  };
}

function normalizeRecord(r: RegimenRecord): RegimenRecord {
  return {
    ...r,
    treatment_values: normalizeTreatmentValues(r.treatment_values as unknown as Record<string, unknown>),
  };
}

async function submitCreate() {
  panelError.value = "";
  saving.value = true;
  try {
    const { regimen } = await createRegimen(buildPayload());
    const row = normalizeRecord(regimen);
    items.value = [row, ...items.value.filter((x) => x.regimen_id !== row.regimen_id)];
    cancelEdit();
  } catch (e) {
    panelError.value = regimenSaveUserMessage(e);
  } finally {
    saving.value = false;
  }
}

async function submitUpdate(regimenId: string) {
  panelError.value = "";
  saving.value = true;
  try {
    const { regimen } = await updateRegimen(regimenId, buildPayload());
    const row = normalizeRecord(regimen);
    items.value = items.value.map((x) => (x.regimen_id === row.regimen_id ? row : x));
    cancelEdit();
  } catch (e) {
    panelError.value = regimenSaveUserMessage(e);
  } finally {
    saving.value = false;
  }
}

async function onDelete(r: RegimenRecord) {
  if (
    !window.confirm(
      i18nT("regimen.management.deleteConfirm", { name: r.regimen_name?.trim() ? r.regimen_name : r.regimen_id }),
    )
  )
    return;
  panelError.value = "";
  saving.value = true;
  try {
    await deleteRegimen(r.regimen_id);
    items.value = items.value.filter((x) => x.regimen_id !== r.regimen_id);
    emit("regimenDeleted", r.regimen_id);
  } catch (e) {
    panelError.value = e instanceof ApiError ? e.message : i18nT("regimen.management.deleteFailed");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  void refresh();
});

watch(
  () => props.refreshSignal,
  () => {
    if (editingId.value === "new") return;
    void refresh();
  },
);

defineExpose({ refresh, beginEdit: startEdit });
</script>

<style scoped>
.regimen-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  overflow: hidden;
}

.regimen-toolbar,
.regimen-alert {
  flex-shrink: 0;
}

.regimen-main-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: var(--wb-space-1);
  padding-bottom: var(--wb-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
}

.regimen-list-section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--wb-space-2) var(--wb-space-3);
  flex-shrink: 0;
  margin-bottom: 0;
  padding-bottom: var(--wb-space-2);
  border-bottom: 1px solid var(--wb-border);
}

.regimen-list-section-title {
  margin: 0;
  font-size: var(--wb-font-size-md);
  font-weight: 650;
  color: var(--wb-text-primary);
  letter-spacing: 0.01em;
}

.regimen-list-section-count {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
}

.regimen-toolbar {
  padding: var(--wb-space-3) var(--wb-space-4);
}

.regimen-toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
  align-items: center;
}

.regimen-alert {
  padding: var(--wb-space-3);
}

.regimen-alert-error {
  border: 1px solid #e8c9c9;
  background: #fdf5f5;
  color: var(--wb-text-primary);
}

.regimen-alert-warning {
  border: 1px solid #e5d9c4;
  background: #fcfaf5;
  color: var(--wb-text-primary);
}

.regimen-alert-title {
  margin-bottom: var(--wb-space-2);
}

.regimen-empty,
.regimen-loading {
  padding: var(--wb-space-5);
  text-align: center;
  color: var(--wb-text-secondary);
}

.regimen-form-shell {
  flex-shrink: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  padding: var(--wb-space-4);
  padding-bottom: var(--wb-space-6);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0;
  overflow-x: hidden;
}

.regimen-form-shell-compact {
  padding: var(--wb-space-3);
  padding-bottom: calc(var(--wb-space-6) + var(--wb-space-3));
}

.regimen-form-title {
  margin: 0 0 var(--wb-space-3);
  font-size: var(--wb-font-size-md);
  font-weight: 650;
  color: var(--wb-text-primary);
  flex-shrink: 0;
}

.regimen-form-body {
  flex: 0 0 auto;
  width: 100%;
  min-width: 0;
}

.regimen-item-shell {
  padding: var(--wb-space-4);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.regimen-item-selected {
  border-color: var(--wb-accent) !important;
  background: var(--wb-accent-soft) !important;
}

.regimen-item-top {
  display: flex;
  justify-content: space-between;
  gap: var(--wb-space-3);
  align-items: flex-start;
}

.regimen-item-name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wb-space-2);
}

.regimen-item-title {
  font-size: var(--wb-font-size-md);
  font-weight: 650;
}

.regimen-item-actions {
  display: flex;
  gap: var(--wb-space-2);
  flex-shrink: 0;
}

.regimen-delete-btn {
  flex-shrink: 0;
}

.regimen-notes-preview {
  margin: 4px 0 0;
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-secondary);
}

.regimen-dose-group {
  margin-top: var(--wb-space-3);
}

.regimen-dose-group:first-child {
  margin-top: 0;
}

.regimen-dose-group-title {
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
  color: var(--wb-text-primary);
  margin-bottom: var(--wb-space-2);
}

.regimen-form-actions {
  flex-shrink: 0;
  margin-top: var(--wb-space-3);
  padding-top: var(--wb-space-3);
  border-top: 1px solid var(--wb-border);
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
  justify-content: flex-start;
}

.regimen-fields {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  align-items: stretch;
}

.regimen-name-notes-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.regimen-label-pair-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wb-space-3);
}

.regimen-label-pair-row .regimen-label {
  margin-bottom: 0;
}

.regimen-input-pair-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wb-space-3);
  align-items: stretch;
}

.regimen-notes-compact {
  min-height: 2.6rem;
  max-height: 5.5rem;
  resize: vertical;
  line-height: 1.35;
}

@media (max-width: 720px) {
  .regimen-label-pair-row,
  .regimen-input-pair-row {
    grid-template-columns: 1fr;
  }
}

.regimen-checkbox {
  display: flex;
  align-items: center;
  gap: var(--wb-space-2);
  font-size: var(--wb-font-size-sm);
  font-weight: 500;
  color: var(--wb-text-primary);
}

.regimen-label {
  display: block;
  margin-bottom: 4px;
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
  color: var(--wb-text-primary);
}

.regimen-dose-field-label {
  display: block;
  margin-bottom: 4px;
  font-size: var(--wb-font-size-xs);
  font-weight: 400;
  color: var(--wb-text-primary);
  line-height: 1.35;
  word-break: break-word;
}

.regimen-input,
.regimen-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  font-size: var(--wb-font-size-sm);
  background: var(--wb-surface);
  color: var(--wb-text-primary);
}

.regimen-numeric-block {
  border: 1px dashed var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-3);
  background: var(--wb-surface-soft);
}

.regimen-numeric-title {
  font-size: var(--wb-font-size-sm);
  font-weight: 500;
  color: var(--wb-text-primary);
  margin-bottom: var(--wb-space-2);
}

.regimen-numeric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--wb-space-3);
  align-items: end;
}

@media (max-width: 1200px) {
  .regimen-numeric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .regimen-numeric-grid {
    grid-template-columns: 1fr;
  }
}

.regimen-num-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.regimen-input-suffix-row {
  display: flex;
  align-items: stretch;
  min-height: 38px;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface);
  overflow: hidden;
}

.regimen-input-in-suffix {
  border: none !important;
  border-radius: 0 !important;
  flex: 1;
  min-width: 0;
  height: 100%;
}

.regimen-field-unit {
  flex-shrink: 0;
  padding: 0 10px;
  font-size: var(--wb-font-size-xs);
  font-weight: 400;
  color: var(--wb-text-primary);
  background: var(--wb-surface-soft);
  border-left: 1px solid var(--wb-border);
  display: inline-flex;
  align-items: center;
}
</style>
