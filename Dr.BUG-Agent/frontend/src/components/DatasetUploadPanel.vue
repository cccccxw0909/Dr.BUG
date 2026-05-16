<template>
  <div class="upload-panel">
    <div class="upload-intro">
      <p class="upload-intro-text">{{ $t("components.datasetUpload.intro") }}</p>
    </div>

    <div class="upload-task-block">
      <div class="upload-task-title">{{ $t("components.datasetUpload.tasksTitle") }}</div>
      <div class="upload-task-grid">
        <label v-for="opt in taskOptions" :key="opt.value" class="upload-task-item">
          <input v-model="selectedTasks" type="checkbox" :value="opt.value" :disabled="uploading" />
          <span>{{ opt.label }}</span>
        </label>
      </div>
    </div>

    <div class="wb-file-pick">
      <label class="wb-file-pick-label wb-btn wb-btn-secondary" :class="{ 'is-disabled': uploading }">
        {{ $t("components.datasetUpload.pickFile") }}
        <input type="file" class="wb-file-pick-input" accept=".csv,.xlsx,.xls" :disabled="uploading" @change="onFileChange" />
      </label>
      <button type="button" class="wb-btn wb-btn-primary" :disabled="!selectedFile || uploading" @click="onUpload">
        {{ uploading ? $t("components.datasetUpload.uploading") : $t("components.datasetUpload.upload") }}
      </button>
    </div>

    <div v-if="selectedFile" class="wb-file-pick-name">{{ $t("components.datasetUpload.selected") }}: <b>{{ selectedFile.name }}</b></div>
    <div v-if="hint" class="upload-hint upload-hint-success">{{ hint }}</div>
    <div v-if="error" class="upload-hint upload-hint-error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ApiError, getDatasets, uploadDataset } from "../api";

const emit = defineEmits<{ (e: "uploaded"): void }>();

const { t } = useI18n();

const TASK_VALUES = [
  "clinical_efficacy",
  "mortality_28d",
  "polymyxin_resistance",
  "treatment_duration",
] as const;

const taskOptions = computed(() =>
  TASK_VALUES.map((value) => ({
    value,
    label: t(`components.datasetUpload.taskOptions.${value}`),
  })),
);

const selectedTasks = ref<string[]>([...TASK_VALUES]);
const selectedFile = ref<File | null>(null);
const uploading = ref(false);
const hint = ref("");
const error = ref("");

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] || null;
}

async function onUpload() {
  if (!selectedFile.value) return;
  uploading.value = true;
  hint.value = "";
  error.value = "";
  try {
    const tasks = selectedTasks.value.length ? [...selectedTasks.value] : undefined;
    const res = await uploadDataset(selectedFile.value, { availableTasks: tasks });
    hint.value = t("components.datasetUpload.uploadSuccess", { name: res.dataset.name || res.dataset.id });
    selectedFile.value = null;
    emit("uploaded");
    await loadDatasets();
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = t("components.datasetUpload.uploadFailedWithCode", { code: e.code, message: e.message });
    } else {
      error.value = t("components.datasetUpload.uploadFailed", { message: String(e) });
    }
  } finally {
    uploading.value = false;
  }
}

async function loadDatasets() {
  error.value = "";
  try {
    await getDatasets();
  } catch {
    /* The list is refreshed by the parent. */
  }
}

onMounted(async () => {
  await loadDatasets();
});
</script>

<style scoped>
.upload-panel {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
  padding: var(--wb-space-3);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface-soft);
}

.upload-intro-text {
  margin: 0;
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-secondary);
  line-height: 1.5;
}

.upload-task-block {
  padding: var(--wb-space-3);
  border-radius: var(--wb-radius-sm);
  border: 1px dashed var(--wb-border-strong);
  background: var(--wb-surface);
}

.upload-task-title {
  font-size: var(--wb-font-size-xs);
  font-weight: 650;
  color: var(--wb-text-primary);
  margin-bottom: var(--wb-space-2);
}

.upload-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--wb-space-2);
}

.upload-task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-primary);
}

.upload-hint {
  padding: 8px 10px;
  border-radius: var(--wb-radius-sm);
  font-size: var(--wb-font-size-xs);
  border: 1px solid transparent;
}

.upload-hint-success {
  color: #4d735b;
  background: #f2f8f4;
  border-color: #d3e3d7;
}

.upload-hint-error {
  color: var(--wb-error);
  background: #fdf4f4;
  border-color: #eed4d4;
}
</style>
