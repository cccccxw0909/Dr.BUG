<template>
  <div class="datasets-page datasets-page-flex">
    <header class="datasets-header">
      <h2 class="wb-section-title">{{ pageHeadingTitle }}</h2>
      <p class="datasets-subtitle">{{ pageHeadingSubtitle }}</p>
      <div class="datasets-segment" role="tablist" :aria-label="$t('pages.datasets.aria.sectionTabs')">
        <button
          type="button"
          class="datasets-segment-btn"
          :class="{ 'datasets-segment-btn-active': activeSection === 'data' }"
          role="tab"
          :aria-selected="activeSection === 'data'"
          @click="setSection('data')"
        >
          {{ $t("pages.datasets.tabs.data") }}
        </button>
        <button
          type="button"
          class="datasets-segment-btn"
          :class="{ 'datasets-segment-btn-active': activeSection === 'regimens' }"
          role="tab"
          :aria-selected="activeSection === 'regimens'"
          @click="setSection('regimens')"
        >
          {{ $t("pages.datasets.tabs.regimens") }}
        </button>
      </div>
    </header>

    <div class="datasets-body">
      <template v-if="activeSection === 'data'">
        <div class="datasets-data-layout">
          <section class="datasets-toolbar wb-card">
            <div class="datasets-toolbar-row">
              <button type="button" class="wb-btn wb-btn-secondary" :disabled="datasetsRefreshing" @click="emit('refreshDatasets')">
                {{ datasetsRefreshing ? $t("common.refreshing") : $t("common.refresh") }}
              </button>
              <button
                v-if="!uploadPanelOpen"
                type="button"
                class="wb-btn wb-btn-primary"
                @click="uploadPanelOpen = true"
              >
                {{ $t("pages.datasets.uploadDataset") }}
              </button>
            </div>
          </section>

          <section v-if="uploadPanelOpen" class="datasets-upload-expanded wb-card">
            <div class="datasets-upload-expanded-head">
              <h3 class="datasets-section-title datasets-upload-expanded-title">{{ $t("pages.datasets.sections.createDataset") }}</h3>
              <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="uploadPanelOpen = false">
                {{ $t("common.close") }}
              </button>
            </div>
            <p class="datasets-section-lead">{{ $t("pages.datasets.sections.createDatasetHint") }}</p>
            <DatasetUploadPanel @uploaded="onDatasetUploaded" />
          </section>

          <div class="datasets-list-region datasets-list-scroll">
            <div class="datasets-list-section-head">
              <h3 class="datasets-list-section-title">{{ $t("pages.datasets.sections.datasetList") }}</h3>
              <span class="datasets-list-count">{{ $t("pages.datasets.count", { count: datasets.length }) }}</span>
            </div>

            <div v-if="datasets.length === 0" class="datasets-empty">{{ $t("pages.datasets.empty") }}</div>
            <article
              v-for="d in datasets"
              :key="d.id"
              class="dataset-item"
              :class="{ 'dataset-item-active': selectedDatasetId === d.id }"
              @click="$emit('selectDataset', d.id)"
            >
              <div class="dataset-item-top">
                <div class="dataset-item-name">
                  <span class="dataset-item-title">{{ d.name || d.file_name || $t("pages.datasets.unnamedDataset") }}</span>
                  <span v-if="selectedDatasetId === d.id" class="wb-status wb-status-pending">{{ $t("pages.datasets.currentDatasetBadge") }}</span>
                </div>
                <button
                  type="button"
                  class="wb-btn wb-btn-sm wb-btn-danger dataset-delete-btn"
                  @click.stop="$emit('deleteDataset', d.id)"
                >
                  {{ $t("common.delete") }}
                </button>
              </div>

              <div class="dataset-item-meta">
                <span><strong>{{ $t("pages.datasets.meta.format") }}</strong> {{ d.file_type || $t("common.na") }}</span>
                <span><strong>{{ $t("pages.datasets.meta.uploadedAt") }}</strong> {{ formatDisplayDateTime(d.created_at) }}</span>
              </div>

              <div class="dataset-task-row">
                <span class="dataset-task-label">{{ $t("pages.datasets.meta.availableTasks") }}</span>
                <div v-if="orderedTasks(d).length" class="dataset-task-chips">
                  <span v-for="task in orderedTasks(d)" :key="task" class="dataset-task-chip">{{ taskLabel(task) }}</span>
                </div>
                <span v-else class="wb-text-secondary">{{ $t("pages.datasets.meta.unspecified") }}</span>
              </div>
            </article>
          </div>
        </div>
      </template>

      <div v-else class="datasets-regimen-layout">
        <RegimenManagementSection
          ref="regimenSectionRef"
          :selected-regimen-id="selectedRegimenId"
          :refresh-signal="regimenRefreshSignal"
          @select-regimen="$emit('selectRegimen', $event)"
          @regimen-deleted="$emit('regimenDeleted', $event)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import DatasetUploadPanel from "../components/DatasetUploadPanel.vue";
import RegimenManagementSection from "../components/RegimenManagementSection.vue";
import type { DatasetMeta, RegimenRecord } from "../types";
import { sortDatasetTasksForDisplay } from "../utils/datasetTaskOrder";
import { formatDisplayDateTime } from "../utils/dateFormat";

defineProps<{
  datasets: DatasetMeta[];
  selectedDatasetId: string | null;
  selectedRegimenId?: string | null;
  regimenRefreshSignal?: number;
  datasetsRefreshing?: boolean;
}>();

const emit = defineEmits<{
  (e: "selectDataset", id: string): void;
  (e: "trainWithDataset", id: string): void;
  (e: "sectionChange", section: "data" | "regimens"): void;
  (e: "selectRegimen", regimen: RegimenRecord): void;
  (e: "regimenDeleted", regimenId: string): void;
  (e: "deleteDataset", id: string): void;
  (e: "refreshDatasets"): void;
}>();

const regimenSectionRef = ref<{ beginEdit?: (r: RegimenRecord) => void } | null>(null);

function beginRegimenEdit(r: RegimenRecord) {
  regimenSectionRef.value?.beginEdit?.(r);
}

defineExpose({ beginRegimenEdit });

type PageSection = "data" | "regimens";
const activeSection = ref<PageSection>("data");
const uploadPanelOpen = ref(false);

const { t } = useI18n();

const pageHeadingTitle = computed(() =>
  activeSection.value === "data" ? t("pages.datasets.tabs.data") : t("pages.datasets.tabs.regimens"),
);
const pageHeadingSubtitle = computed(() =>
  activeSection.value === "data" ? t("pages.datasets.subtitle") : t("pages.datasets.subtitleRegimens"),
);

function onDatasetUploaded() {
  emit("refreshDatasets");
  uploadPanelOpen.value = false;
}

const TASK_LABELS: Record<string, string> = {
  clinical_efficacy: "pages.datasets.taskLabels.clinical_efficacy",
  mortality_28d: "pages.datasets.taskLabels.mortality_28d",
  polymyxin_resistance: "pages.datasets.taskLabels.polymyxin_resistance",
  treatment_duration: "pages.datasets.taskLabels.treatment_duration",
};

function taskLabel(task: string): string {
  const key = TASK_LABELS[task];
  return key ? t(key) : task;
}

function orderedTasks(d: DatasetMeta): string[] {
  return sortDatasetTasksForDisplay(d.available_tasks || []);
}

function setSection(s: PageSection) {
  activeSection.value = s;
}

watch(
  () => activeSection.value,
  (s) => {
    emit("sectionChange", s);
  },
);

onMounted(() => {
  emit("sectionChange", activeSection.value);
  if (typeof sessionStorage === "undefined") return;
  if (sessionStorage.getItem("workbench_open_regimens") === "1") {
    activeSection.value = "regimens";
    sessionStorage.removeItem("workbench_open_regimens");
    emit("sectionChange", "regimens");
  }
});
</script>

<style scoped>
.datasets-page {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-4);
}

.datasets-page-flex {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.datasets-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.datasets-subtitle {
  margin: 0;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
}

.datasets-segment {
  display: inline-flex;
  margin-top: var(--wb-space-2);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  overflow: hidden;
  background: var(--wb-surface);
  box-shadow: var(--wb-shadow-sm);
}

.datasets-segment-btn {
  margin: 0;
  padding: var(--wb-chat-input-padding-y) var(--wb-space-4);
  border: none;
  background: transparent;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.datasets-segment-btn:hover {
  background: var(--wb-surface-soft);
  color: var(--wb-text-primary);
}

.datasets-segment-btn-active {
  background: var(--wb-accent-soft);
  color: var(--wb-accent-hover);
  font-weight: 650;
}

.datasets-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  overflow: hidden;
}

.datasets-data-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  overflow: hidden;
}

.datasets-toolbar {
  flex-shrink: 0;
  padding: var(--wb-space-3) var(--wb-space-4);
  box-sizing: border-box;
}

.datasets-toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
  align-items: center;
}

.datasets-upload-expanded {
  flex-shrink: 0;
  padding: var(--wb-space-4);
  box-sizing: border-box;
}

.datasets-upload-expanded-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wb-space-3);
  margin-bottom: var(--wb-space-2);
}

.datasets-upload-expanded-title {
  margin: 0;
}

.datasets-list-region {
  box-sizing: border-box;
  min-width: 0;
}

.datasets-list-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: var(--wb-space-1);
}

.datasets-list-section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--wb-space-2) var(--wb-space-3);
  margin-bottom: var(--wb-space-3);
  padding-bottom: var(--wb-space-2);
  border-bottom: 1px solid var(--wb-border);
}

.datasets-list-section-title {
  margin: 0;
  font-size: var(--wb-font-size-md);
  font-weight: 650;
  color: var(--wb-text-primary);
  letter-spacing: 0.01em;
}

.datasets-list-count {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
}

.datasets-regimen-layout {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.datasets-section-title {
  margin: 0;
  font-size: var(--wb-font-size-md);
}

.datasets-section-lead {
  margin: 0;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  line-height: 1.45;
}

.datasets-empty {
  padding: var(--wb-space-5);
  border: 1px dashed var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  color: var(--wb-text-secondary);
  text-align: center;
}

.dataset-item {
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-3);
  background: var(--wb-surface);
  box-shadow: var(--wb-shadow-sm);
  margin-bottom: var(--wb-space-2);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.dataset-item:hover {
  border-color: var(--wb-border-strong);
  background: var(--wb-surface-soft);
}

.dataset-item-active {
  border-color: var(--wb-accent);
  background: var(--wb-accent-soft);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.dataset-item-top {
  display: flex;
  justify-content: space-between;
  gap: var(--wb-space-2);
  align-items: flex-start;
}

.dataset-item-name {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--wb-space-2);
  min-width: 0;
}

.dataset-item-title {
  font-size: var(--wb-font-size-md);
  font-weight: 650;
}

.dataset-delete-btn {
  flex-shrink: 0;
}

.dataset-item-meta {
  margin-top: var(--wb-space-2);
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1) var(--wb-space-3);
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
}

.dataset-item-meta strong {
  margin-right: var(--wb-space-micro);
  color: var(--wb-text-primary);
  font-weight: 600;
}

.dataset-task-row {
  margin-top: var(--wb-space-2);
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--wb-space-1) var(--wb-space-2);
}

.dataset-task-label {
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
}

.dataset-task-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.dataset-task-chip {
  padding: 2px 8px;
  border: 1px solid var(--wb-border);
  border-radius: 999px;
  font-size: var(--wb-font-size-xs);
  font-weight: 500;
  color: var(--wb-text-secondary);
  background: transparent;
}
</style>
