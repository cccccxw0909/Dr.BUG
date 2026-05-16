<template>
  <div class="models-page models-page-flex">
    <header class="models-header">
      <h2 class="wb-section-title">{{ $t("pages.models.title") }}</h2>
      <p class="models-subtitle">{{ $t("pages.models.subtitle") }}</p>
    </header>

    <section class="models-toolbar wb-card">
      <p class="models-note">{{ $t("pages.models.note") }}</p>
      <div class="models-toolbar-row">
        <label class="models-field">
          <span class="models-field-label">{{ $t("pages.models.filters.task") }}</span>
          <select v-model="taskFilter" class="models-select">
            <option value="">{{ $t("pages.models.taskAll") }}</option>
            <option v-for="opt in taskTypeOptions" :key="opt" :value="opt">{{ taskTypeLabel(opt) }}</option>
          </select>
        </label>
        <label class="models-field">
          <span class="models-field-label">{{ $t("pages.models.filters.sort") }}</span>
          <select v-model="sortMode" class="models-select">
            <option value="time_desc">{{ $t("pages.models.sortOptions.timeDesc") }}</option>
            <option value="time_asc">{{ $t("pages.models.sortOptions.timeAsc") }}</option>
            <option value="name_asc">{{ $t("pages.models.sortOptions.nameAsc") }}</option>
          </select>
        </label>
        <button type="button" class="wb-btn wb-btn-secondary" :disabled="loading" @click="$emit('refresh')">
          {{ loading ? $t("common.refreshing") : $t("common.refresh") }}
        </button>
      </div>
    </section>

    <section v-if="loadError" class="models-alert models-alert-error wb-card">
      <div class="models-alert-title"><b>{{ $t("pages.models.banners.loadFailedTitle") }}</b></div>
      <p class="models-alert-body">{{ $t("pages.models.banners.loadFailedBody") }}</p>
      <button type="button" class="wb-btn wb-btn-secondary" @click="$emit('refresh')">{{ $t("common.retry") }}</button>
      <div v-if="models.length > 0" class="models-alert-meta">{{ $t("pages.models.banners.cachedListHint") }}</div>
    </section>

    <section v-if="selectionMissing" class="models-alert models-alert-warning wb-card">
      {{ $t("pages.models.banners.selectionMissing") }}
    </section>

    <section v-if="!loading && models.length === 0 && !loadError" class="models-empty wb-card">
      {{ $t("pages.models.empty") }}
    </section>
    <div v-else-if="loading && models.length === 0 && !loadError" class="models-loading">{{ $t("pages.models.loading") }}</div>

    <div v-else-if="filteredSorted.length > 0" class="models-list-scroll">
    <section class="models-list-shell wb-card">
      <div class="models-list-head">
        <h3 class="models-list-title">{{ $t("pages.models.list.title") }}</h3>
        <span class="models-count">{{ $t("pages.models.list.count", { count: filteredSorted.length }) }}</span>
      </div>

      <article
        v-for="m in filteredSorted"
        :key="m.model_id"
        class="model-item"
        :class="{ 'model-item-active': currentModelId === m.model_id }"
        @click="$emit('selectModel', m.model_id)"
      >
        <div class="model-item-main">
          <div class="model-item-title-row">
            <div class="model-item-name">{{ listCardTitle(m) }}</div>
            <div class="model-item-tags">
              <span v-if="publishStatus(m) !== 'unknown'" class="model-tag">{{ publishLabel(m) }}</span>
            </div>
          </div>
          <div class="model-item-meta">
            <span v-if="algorithmShort(m) !== '—'">{{ $t("pages.models.list.algorithm") }}: {{ algorithmShort(m) }}</span>
            <span v-if="m.created_at">{{ $t("pages.models.list.registeredAt") }}: {{ formatDisplayDateTime(m.created_at) }}</span>
          </div>
        </div>

        <div class="model-item-actions" @click.stop>
          <button
            v-if="currentModelId !== m.model_id"
            type="button"
            class="wb-btn wb-btn-primary wb-btn-sm model-item-action-btn"
            @click="$emit('selectModel', m.model_id)"
          >
            {{ $t("pages.models.list.setCurrent") }}
          </button>
          <span v-else class="model-item-current-pill">{{ $t("pages.models.list.currentUsing") }}</span>
          <button type="button" class="wb-btn wb-btn-sm wb-btn-edit model-item-action-btn" @click="openEdit(m)">
            {{ $t("pages.models.list.edit") }}
          </button>
          <button type="button" class="wb-btn wb-btn-danger wb-btn-sm model-item-action-btn" @click="confirmDelete(m)">
            {{ $t("common.delete") }}
          </button>
        </div>
      </article>
    </section>
    </div>

    <div v-if="pageError" class="models-page-error">{{ $t("pages.models.errors.actionFailed") }}</div>

    <Teleport to="body">
      <div v-if="editTarget" class="models-modal-overlay" @click.self="closeEdit">
        <div class="models-modal wb-card">
          <h3 class="models-modal-title">{{ $t("pages.models.modal.title") }}</h3>
          <p class="models-modal-meta">{{ $t("pages.models.modal.internalId") }}: <code>{{ editTarget.model_id }}</code></p>
          <label class="models-modal-field">
            <span>{{ $t("pages.models.modal.displayName") }}</span>
            <input v-model="editForm.task_name" type="text" class="models-modal-input" />
          </label>
          <label class="models-modal-field">
            <span>{{ $t("pages.models.modal.notes") }}</span>
            <textarea v-model="editForm.notes" class="models-modal-textarea" rows="3" />
          </label>
          <label class="models-modal-check">
            <input v-model="editForm.is_published" type="checkbox" />
            <span>{{ $t("pages.models.modal.published") }}</span>
          </label>
          <p v-if="editError" class="models-modal-error">{{ editError }}</p>
          <div class="models-modal-actions">
            <button type="button" class="wb-btn wb-btn-secondary" :disabled="editSaving" @click="closeEdit">{{ $t("common.cancel") }}</button>
            <button type="button" class="wb-btn wb-btn-primary" :disabled="editSaving" @click="submitEdit">
              {{ editSaving ? $t("common.saving") : $t("common.save") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ApiError, deleteModel, patchModel } from "../api";
import type { ModelMeta } from "../types";
import { formatDisplayDateTime } from "../utils/dateFormat";
import { formatMlTaskKindDisplay, formatModelTypeLabel, modelDisplayName, type ModelRecord } from "../utils/modelPresentation";

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    models: ModelMeta[];
    currentModelId: string | null;
    loadError?: string;
    loading?: boolean;
    selectionMissing?: boolean;
    /** Triggered by right panel "Edit", then cleared by parent. */
    pendingOpenEditModelId?: string | null;
  }>(),
  { loadError: "", loading: false, selectionMissing: false, pendingOpenEditModelId: null },
);

const emit = defineEmits<{
  (e: "selectModel", id: string): void;
  (e: "refresh"): void;
  (e: "modelUpdated"): void;
  (e: "modelDeleted", modelId: string): void;
  (e: "pendingEditConsumed"): void;
}>();

const taskFilter = ref("");
const sortMode = ref<"time_desc" | "time_asc" | "name_asc">("time_desc");
const pageError = ref("");

const editTarget = ref<ModelMeta | null>(null);
const editForm = ref({ task_name: "", notes: "", is_published: true });
const editSaving = ref(false);
const editError = ref("");

const taskTypeOptions = computed(() => {
  const s = new Set<string>();
  for (const m of props.models) {
    const t = String(m.task_type || m.ml_task_type || "").trim();
    if (t) s.add(t);
  }
  return Array.from(s).sort();
});

const filteredSorted = computed(() => {
  let rows = props.models;
  if (taskFilter.value) {
    rows = rows.filter((m) => String(m.task_type || m.ml_task_type || "") === taskFilter.value);
  }
  const out = [...rows];
  if (sortMode.value === "name_asc") {
    out.sort((a, b) => displayName(a).localeCompare(displayName(b), "zh-CN"));
  } else if (sortMode.value === "time_asc") {
    out.sort((a, b) => parseTime(a.created_at) - parseTime(b.created_at));
  } else {
    out.sort((a, b) => parseTime(b.created_at) - parseTime(a.created_at));
  }
  return out;
});

function parseTime(v: string | undefined): number {
  if (!v) return 0;
  const t = new Date(v).getTime();
  return Number.isFinite(t) ? t : 0;
}

function asRec(m: ModelMeta): ModelRecord {
  return m as ModelRecord;
}

function displayName(m: ModelMeta) {
  return modelDisplayName(asRec(m), t);
}

function listCardTitle(m: ModelMeta): string {
  const name = displayName(m);
  const algo = formatModelTypeLabel(m.model_type != null ? String(m.model_type) : null, t);
  if (algo && algo !== "-") return `${name} · ${algo}`;
  return name || "—";
}

type PublishStatus = "published" | "unpublished" | "unknown";

function publishStatus(m: ModelMeta): PublishStatus {
  const v = (m as unknown as { is_published?: unknown }).is_published;
  if (v === true) return "published";
  if (v === false) return "unpublished";
  return "unknown";
}

function publishLabel(m: ModelMeta): string {
  const s = publishStatus(m);
  return t(`pages.models.publishStatus.${s}`);
}

function algorithmShort(m: ModelMeta): string {
  return formatModelTypeLabel(m.model_type != null ? String(m.model_type) : null, t);
}

function taskTypeLabel(raw: string): string {
  return formatMlTaskKindDisplay(raw, t);
}

function openEdit(m: ModelMeta) {
  editTarget.value = m;
  editForm.value = {
    task_name: m.display_name || m.task_name || m.model_name || displayName(m) || "",
    notes: m.notes != null ? String(m.notes) : "",
    is_published: m.is_published !== false,
  };
  editError.value = "";
}

watch(
  () => [props.pendingOpenEditModelId, props.loading, props.models] as const,
  async ([pending]) => {
    if (!pending || props.loading) return;
    await nextTick();
    const m = props.models.find((x) => x.model_id === pending);
    if (m) {
      openEdit(m);
      emit("pendingEditConsumed");
    } else if (props.models.length > 0) {
      emit("pendingEditConsumed");
    }
  },
);

function closeEdit() {
  editTarget.value = null;
  editError.value = "";
}

async function submitEdit() {
  const m = editTarget.value;
  if (!m) return;
  editSaving.value = true;
  editError.value = "";
  try {
    await patchModel(m.model_id, {
      task_name: editForm.value.task_name.trim() || null,
      notes: editForm.value.notes.trim() || null,
      is_published: editForm.value.is_published,
    });
    closeEdit();
    emit("modelUpdated");
  } catch (e) {
    console.error("ModelsPage submitEdit", e);
    editError.value = e instanceof ApiError ? e.message : t("pages.models.errors.saveFailed");
  } finally {
    editSaving.value = false;
  }
}

async function confirmDelete(m: ModelMeta) {
  if (!window.confirm(t("pages.models.confirms.removeFromRegistry", { name: displayName(m) }))) return;
  pageError.value = "";
  try {
    await deleteModel(m.model_id);
    emit("modelDeleted", m.model_id);
  } catch (e) {
    console.error("ModelsPage confirmDelete", e);
    pageError.value = "1";
  }
}
</script>

<style scoped>
.models-page {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-4);
}

.models-page-flex {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.models-list-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: var(--wb-space-1);
}

.models-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.models-subtitle {
  margin: 0;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
}

.models-toolbar {
  flex-shrink: 0;
  padding: var(--wb-space-4);
}

.models-note {
  margin: 0 0 var(--wb-space-2) 0;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
}

.models-toolbar-row {
  display: flex;
  gap: var(--wb-space-3);
  flex-wrap: wrap;
  align-items: flex-end;
}

.models-field {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-micro);
  min-width: 160px;
}

.models-field-label {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  font-weight: 600;
}

.models-select {
  min-height: var(--wb-control-height-sm);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: 0 var(--wb-chat-bubble-padding-x);
  background: #fff;
  font-size: var(--wb-font-size-sm);
}

.models-alert {
  padding: var(--wb-space-3);
  border-radius: var(--wb-radius-sm);
  border: 1px solid;
  font-size: var(--wb-font-size-sm);
}

.models-alert-title {
  margin-bottom: var(--wb-space-2);
}

.models-alert-body {
  margin: 0 0 var(--wb-space-2);
  color: var(--wb-text-secondary);
  line-height: var(--wb-line-height);
}

.models-alert-meta {
  margin-top: var(--wb-space-2);
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
}

.models-alert-error {
  border-color: #eed4d4;
  background: #fdf4f4;
}

.models-alert-warning {
  border-color: #ecdcc6;
  background: #fcf8f2;
}

.models-empty {
  padding: var(--wb-space-6);
  text-align: center;
  border-style: dashed;
  color: var(--wb-text-secondary);
}

.models-loading {
  color: var(--wb-text-secondary);
  padding: var(--wb-space-4);
}

.models-list-shell {
  padding: var(--wb-space-4);
}

.models-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wb-space-2);
  margin-bottom: var(--wb-space-3);
}

.models-list-title {
  margin: 0;
  font-size: var(--wb-font-size-md);
}

.models-count {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.model-item {
  display: flex;
  justify-content: space-between;
  gap: var(--wb-space-3);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-space-3);
  margin-bottom: var(--wb-space-2);
  background: var(--wb-surface);
  box-shadow: var(--wb-shadow-sm);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.model-item:hover {
  border-color: var(--wb-border-strong);
  background: var(--wb-surface-soft);
}

.model-item-active {
  border-color: var(--wb-accent);
  background: var(--wb-accent-soft);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.model-item-main {
  min-width: 0;
  flex: 1;
}

.model-item-title-row {
  display: flex;
  justify-content: space-between;
  gap: var(--wb-space-2);
  align-items: flex-start;
}

.model-item-name {
  font-size: var(--wb-font-size-md);
  font-weight: 650;
  line-height: 1.35;
}

.model-item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1);
}

.model-tag {
  padding: var(--wb-chat-bubble-gap) var(--wb-chat-input-padding-y);
  border: 1px solid var(--wb-border-strong);
  border-radius: 999px;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  background: #f7f8fa;
}

.model-item-meta {
  margin-top: var(--wb-space-2);
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-1) var(--wb-chat-input-padding-x);
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-xs);
}

.model-item-actions {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wb-chat-input-padding-y);
  flex-shrink: 0;
}

.model-item-action-btn {
  height: var(--wb-control-height-sm);
  padding-left: var(--wb-chat-input-padding-x);
  padding-right: var(--wb-chat-input-padding-x);
  box-sizing: border-box;
}

.model-item-current-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: var(--wb-control-height-sm);
  padding: 0 var(--wb-chat-bubble-padding-x);
  border-radius: var(--wb-radius-sm);
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
  color: #445d79;
  background: #e8eef6;
  border: 1px solid #d4dbe5;
  white-space: nowrap;
}

.models-page-error {
  color: var(--wb-error);
  font-size: var(--wb-font-size-sm);
}

.models-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 80;
  padding: var(--wb-space-4);
}

.models-modal {
  width: min(420px, 100%);
  padding: var(--wb-space-4);
  max-height: 90vh;
  overflow: auto;
}

.models-modal-title {
  margin: 0 0 var(--wb-space-2);
  font-size: var(--wb-font-size-md);
}

.models-modal-meta {
  margin: 0 0 var(--wb-space-3);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-muted);
}

.models-modal-field {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-micro);
  margin-bottom: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.models-modal-input,
.models-modal-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: var(--wb-chat-input-padding-y) var(--wb-chat-bubble-padding-x);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  font-size: var(--wb-font-size-sm);
}

.models-modal-check {
  display: flex;
  align-items: center;
  gap: var(--wb-chat-input-padding-y);
  margin: var(--wb-space-2) 0;
  font-size: var(--wb-font-size-sm);
}

.models-modal-error {
  color: var(--wb-error);
  font-size: var(--wb-font-size-xs);
}

.models-modal-actions {
  margin-top: var(--wb-space-3);
  display: flex;
  justify-content: flex-end;
  gap: var(--wb-space-2);
}
</style>
