<template>
  <div class="model-detail-panel">
    <div v-if="!modelId" class="model-detail-empty">{{ $t("panels.modelDetail.emptyPick") }}</div>
    <div v-else-if="detailError" class="model-detail-error">
      <div><b>{{ $t("panels.modelDetail.loadFailed") }}</b>: {{ detailError }}</div>
    </div>
    <div v-else-if="!record" class="model-detail-empty">{{ $t("panels.modelDetail.loading") }}</div>

    <div v-else class="model-detail-content">
      <section class="mdp-section" aria-label="Basic info">
        <div class="mdp-section-title">{{ $t("panels.modelDetail.sections.basic") }}</div>
        <div class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.displayName") }}</span><span>{{ modelDisplayName(record, t) }}</span>
        </div>
        <div class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.algorithm") }}</span>
          <span>{{ formatModelTypeLabel(record.model_type != null ? String(record.model_type) : null, t) }}</span>
        </div>
        <div class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.taskType") }}</span>
          <span>{{
            formatMlTaskKindDisplay(
              record.ml_task_type != null ? String(record.ml_task_type) : record.task_type != null ? String(record.task_type) : null,
              t,
            )
          }}</span>
        </div>
        <div class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.status") }}</span>
          <span class="status-row">
            <span v-if="tags.isCurrent" class="wb-status wb-status-pending">{{ $t("panels.modelDetail.fields.currentTag") }}</span>
            <span class="model-detail-tag">{{ tags.publish }}</span>
          </span>
        </div>
        <div v-if="record.version" class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.version") }}</span><span>{{ record.version }}</span>
        </div>
        <div v-if="record.created_at" class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.registeredAt") }}</span><span>{{ formatDisplayDateTime(record.created_at) }}</span>
        </div>
        <div v-if="record.published_at" class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.publishedAt") }}</span><span>{{ formatDisplayDateTime(record.published_at) }}</span>
        </div>
        <div v-if="record.updated_at" class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.updatedAt") }}</span><span>{{ formatDisplayDateTime(record.updated_at) }}</span>
        </div>
      </section>

      <div class="mdp-divider" role="separator" />

      <section class="mdp-section" aria-label="Summary metrics">
        <div class="mdp-section-title">{{ $t("panels.modelDetail.sections.metrics") }}</div>
        <div v-if="metricLines.length" class="model-metric-list">
          <div v-for="([k, v]) in metricLines" :key="k" class="model-detail-row model-metric-row">
            <span class="label">{{ metricLabel(k) }}</span><span>{{ v }}</span>
          </div>
        </div>
        <div v-else class="model-detail-empty-inline">{{ $t("panels.modelDetail.fields.missingMetrics") }}</div>
      </section>

      <div class="mdp-divider" role="separator" />

      <section class="mdp-section" aria-label="Notes">
        <div class="mdp-section-title">{{ $t("panels.modelDetail.sections.notes") }}</div>
        <div v-if="record.notes != null && String(record.notes).trim()" class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.noteLabel") }}</span><span>{{ record.notes }}</span>
        </div>
        <div v-else class="model-detail-empty-inline">{{ $t("panels.modelDetail.fields.noNotes") }}</div>
      </section>

      <div class="mdp-divider" role="separator" />

      <section class="mdp-section" aria-label="Source">
        <div class="mdp-section-title">{{ $t("panels.modelDetail.sections.source") }}</div>
        <div v-if="sourceJob" class="model-detail-row">
          <span class="label">{{ $t("panels.modelDetail.fields.sourceJob") }}</span><span>{{ sourceJob }}</span>
        </div>
        <div v-else class="model-detail-empty-inline">{{ $t("panels.modelDetail.fields.noSourceJob") }}</div>
      </section>

      <div class="mdp-divider" role="separator" />

      <details class="mdp-disclosure" aria-label="Technical details">
        <summary class="mdp-disclosure-summary">{{ $t("panels.modelDetail.sections.tech") }}</summary>
        <div class="mdp-disclosure-body">
          <div v-if="featureSum" class="model-detail-row model-tech-row">
            <span class="label">{{ $t("panels.modelDetail.fields.featureSummary") }}</span><span>{{ featureSum }}</span>
          </div>
          <div class="model-detail-row model-tech-row">
            <span class="label">{{ $t("panels.modelDetail.fields.internalId") }}</span><code>{{ record.model_id }}</code>
          </div>
          <div v-if="record.dataset_id" class="model-detail-row model-tech-row">
            <span class="label">{{ $t("panels.modelDetail.fields.datasetId") }}</span><span>{{ record.dataset_id }}</span>
          </div>
          <div v-if="record.clinical_task_id" class="model-detail-row model-tech-row">
            <span class="label">{{ $t("panels.modelDetail.fields.clinicalTaskId") }}</span><span>{{ record.clinical_task_id }}</span>
          </div>
          <div v-if="record.target_column" class="model-detail-row model-tech-row">
            <span class="label">{{ $t("panels.modelDetail.fields.targetColumn") }}</span><span>{{ record.target_column }}</span>
          </div>
          <div v-if="record.model_path" class="model-detail-row model-tech-row">
            <span class="label">{{ $t("panels.modelDetail.fields.path") }}</span><span class="model-path">{{ record.model_path }}</span>
          </div>
          <details class="model-json">
            <summary>{{ $t("panels.modelDetail.fields.fullJson") }}</summary>
            <pre class="model-json-pre">{{ snapshotText }}</pre>
          </details>
        </div>
      </details>

      <div class="model-detail-actions model-detail-actions-row" role="group" aria-label="Footer actions">
        <button
          v-if="!tags.isCurrent"
          type="button"
          class="wb-btn wb-btn-primary wb-btn-sm"
          @click="$emit('setCurrent', String(record.model_id))"
        >
          {{ $t("panels.modelDetail.actions.setCurrent") }}
        </button>
        <span v-else class="model-current-inline">{{ $t("panels.modelDetail.fields.currentSession") }}</span>
        <button type="button" class="wb-btn wb-btn-sm wb-btn-edit" @click="$emit('editModel', String(record.model_id))">
          {{ $t("panels.modelDetail.actions.edit") }}
        </button>
        <button type="button" class="wb-btn wb-btn-danger wb-btn-sm" @click="$emit('deleteModel', String(record.model_id))">
          {{ $t("common.delete") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { ModelMeta } from "../types";
import { formatDisplayDateTime } from "../utils/dateFormat";
import {
  buildModelStatusTags,
  featureSummaryFromModel,
  formatMetricEntries,
  formatMlTaskKindDisplay,
  formatModelTypeLabel,
  modelDisplayName,
  pickSourceJobId,
  safeModelJson,
  type ModelRecord,
} from "../utils/modelPresentation";
import { trainingMetricLabel } from "../utils/trainingWorkflowPresentation";

const { t } = useI18n();

const props = defineProps<{
  modelId: string | null;
  model: (ModelMeta & ModelRecord) | null;
  currentModelId: string | null;
  detailError?: string;
}>();

defineEmits<{
  (e: "setCurrent", modelId: string): void;
  (e: "editModel", modelId: string): void;
  (e: "deleteModel", modelId: string): void;
}>();

const detailError = computed(() => props.detailError || "");

const record = computed(() => (props.model || null) as ModelRecord | null);

const tags = computed(() => buildModelStatusTags(record.value || { model_id: "" }, props.currentModelId, t));

const sourceJob = computed(() => pickSourceJobId(record.value || undefined));

const featureSum = computed(() => featureSummaryFromModel(record.value || undefined));

const metricLines = computed(() => formatMetricEntries(record.value || undefined));

const snapshotText = computed(() => safeModelJson(record.value));

function metricLabel(key: string): string {
  return trainingMetricLabel(key);
}
</script>

<style scoped>
.model-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
  background: linear-gradient(180deg, #fcfdff 0%, #f9fbfe 100%);
  border: 1px solid #e3e8f0;
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-2);
}

.model-detail-empty {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
}

.model-detail-error {
  padding: var(--wb-space-3);
  border: 1px solid #eed4d4;
  background: #fdf4f4;
  border-radius: var(--wb-radius-sm);
  color: var(--wb-error);
}

.model-detail-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.mdp-section {
  padding: 12px 0;
}

.mdp-divider {
  height: 1px;
  background: #e8edf5;
  width: 100%;
}

.mdp-section-title {
  margin: 0 0 var(--wb-space-2);
  font-size: var(--wb-font-size-sm);
  font-weight: 700;
  color: #31465f;
}

.model-detail-row {
  display: grid;
  grid-template-columns: minmax(120px, 140px) 1fr;
  column-gap: var(--wb-space-2);
  align-items: start;
  line-height: 1.6;
  font-size: var(--wb-font-size-sm);
  margin-bottom: 4px;
  min-width: 0;
}

.label {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
  line-height: 1.8;
  flex: 0 0 auto;
}

.model-detail-row > :last-child {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.model-detail-tag {
  padding: 2px 8px;
  border: 1px solid var(--wb-border-strong);
  border-radius: 999px;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  background: #f7f8fa;
}

.model-detail-empty-inline {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
}

.model-metric-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-metric-row {
  margin-bottom: 0;
}

.mdp-disclosure {
  padding: 12px 0;
  border: 0;
}

.mdp-disclosure-summary {
  cursor: pointer;
  user-select: none;
  font-weight: 700;
  color: var(--wb-text-primary);
  list-style: none;
}

.mdp-disclosure-summary::-webkit-details-marker {
  display: none;
}

.mdp-disclosure-body {
  padding-top: var(--wb-space-2);
}

.model-tech-row {
  margin-top: var(--wb-space-2);
}

.model-path {
  font-size: 11px;
  color: var(--wb-text-muted);
}

.model-json {
  margin-top: var(--wb-space-2);
}

.model-json summary {
  cursor: pointer;
  user-select: none;
}

.model-json-pre {
  margin-top: var(--wb-space-2);
  padding: var(--wb-space-2);
  background: #f8f9fb;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  overflow: auto;
  max-height: 200px;
  font-size: 11px;
}

.model-detail-actions {
  margin-top: 0;
  padding: var(--wb-space-2) 0 0;
  border-top: 1px solid #e8edf5;
}

.model-detail-actions-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wb-space-2);
}

.model-current-inline {
  display: inline-flex;
  align-items: center;
  min-height: var(--wb-control-height-sm);
  padding: 0 10px;
  border-radius: var(--wb-radius-sm);
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
  color: #445d79;
  background: #e8eef6;
  border: 1px solid #d4dbe5;
}
</style>
