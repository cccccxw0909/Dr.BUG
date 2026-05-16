<template>
  <div class="tasks-page tasks-page-flex">
    <header class="tasks-head">
      <h2 class="wb-section-title">{{ $t("pages.tasks.title") }}</h2>
      <p class="tasks-lead">{{ $t("pages.tasks.subtitle") }}</p>
    </header>

    <div class="tasks-toolbar wb-card">
      <div class="tasks-toolbar-row">
        <label class="tasks-field">
          <span class="tasks-field-label">{{ $t("pages.tasks.filters.status") }}</span>
          <select v-model="statusFilter" class="tasks-select">
            <option value="">{{ $t("pages.tasks.statusOptions.all") }}</option>
            <option value="queued">{{ $t("pages.tasks.statusOptions.queued") }}</option>
            <option value="running">{{ $t("pages.tasks.statusOptions.running") }}</option>
            <option value="waiting_user">{{ $t("pages.tasks.statusOptions.waitingUser") }}</option>
            <option value="completed">{{ $t("pages.tasks.statusOptions.completed") }}</option>
            <option value="failed">{{ $t("pages.tasks.statusOptions.failed") }}</option>
            <option value="canceled">{{ $t("pages.tasks.statusOptions.canceled") }}</option>
          </select>
        </label>
        <label class="tasks-field">
          <span class="tasks-field-label">{{ $t("pages.tasks.filters.type") }}</span>
          <select v-model="typeFilter" class="tasks-select">
            <option value="">{{ $t("pages.tasks.typeOptions.all") }}</option>
            <option value="train_model">{{ $t("pages.tasks.typeOptions.train") }}</option>
            <option value="predict_outcome">{{ $t("pages.tasks.typeOptions.predict") }}</option>
            <option value="recommend_regimen">{{ $t("pages.tasks.typeOptions.recommend") }}</option>
            <option value="generate_report">{{ $t("pages.tasks.typeOptions.report") }}</option>
            <option value="__other__">{{ $t("pages.tasks.typeOptions.other") }}</option>
          </select>
        </label>
        <label class="tasks-field">
          <span class="tasks-field-label">{{ $t("pages.tasks.filters.sort") }}</span>
          <select v-model="sortKey" class="tasks-select">
            <option value="activity_desc">{{ $t("pages.tasks.sortOptions.activityDesc") }}</option>
            <option value="created_desc">{{ $t("pages.tasks.sortOptions.createdDesc") }}</option>
            <option value="created_asc">{{ $t("pages.tasks.sortOptions.createdAsc") }}</option>
          </select>
        </label>
        <button type="button" class="wb-btn wb-btn-secondary wb-btn-toolbar" :disabled="loading" @click="$emit('refresh')">
          {{ loading ? $t("common.refreshing") : $t("common.refresh") }}
        </button>
      </div>
    </div>

    <div v-if="loadError" class="tasks-banner tasks-banner-error wb-card">
      <div class="tasks-banner-title">{{ $t("pages.tasks.banners.loadFailedTitle") }}</div>
      <p class="tasks-banner-text">{{ loadError }}</p>
      <button type="button" class="wb-btn wb-btn-secondary wb-btn-toolbar" @click="$emit('refresh')">{{ $t("common.retry") }}</button>
      <p v-if="tasks.length > 0" class="tasks-banner-meta">{{ $t("pages.tasks.banners.cachedListHint") }}</p>
    </div>

    <div v-if="!loading && filteredSorted.length === 0 && tasks.length === 0 && !loadError" class="tasks-empty wb-card">
      {{ $t("pages.tasks.empty.none") }}
    </div>
    <div v-else-if="!loading && filteredSorted.length === 0 && tasks.length > 0" class="tasks-empty wb-card tasks-empty-muted">
      {{ $t("pages.tasks.empty.filteredNone") }}
    </div>

    <div v-if="loading && tasks.length === 0 && !loadError" class="tasks-loading">{{ $t("pages.tasks.loading") }}</div>

    <div v-if="filteredSorted.length > 0" class="tasks-list-scroll">
      <div class="tasks-list">
      <article
        v-for="task in filteredSorted"
        :key="String(task.id)"
        class="task-card wb-card"
        :class="{ 'task-card-active': String(selectedTaskId) === String(task.id) }"
        @click="$emit('selectTask', String(task.id))"
      >
        <div class="task-card-top">
          <div class="task-card-titles">
            <div class="task-card-name">{{ taskDisplayName(task) }}</div>
          </div>
          <button
            type="button"
            class="wb-btn wb-btn-sm wb-btn-danger task-card-delete"
            :disabled="isDeleting(String(task.id))"
            @click.stop="$emit('deleteTask', String(task.id))"
          >
            {{ isDeleting(String(task.id)) ? deletingLabel(String(task.id)) : $t("common.delete") }}
          </button>
        </div>

        <div class="task-card-sub">
          <span class="task-pill task-pill-type">{{ formatJobTypeLabel(String(task.job_type || ""), t) }}</span>
          <span class="task-pill" :class="statusPillClass(String(task.status))">{{ formatTaskStatusLabel(String(task.status), t) }}</span>
        </div>

        <div class="task-card-meta">
          <span v-if="activity(task).created"><span class="meta-k">{{ $t("pages.tasks.meta.created") }}</span>{{ activity(task).created }}</span>
          <span v-if="activity(task).updated"><span class="meta-k">{{ $t("pages.tasks.meta.recentActivity") }}</span>{{ activity(task).updated }}</span>
        </div>

        <div v-if="taskWhereLine(task)" class="task-card-where">
          <span class="meta-k">{{ $t("pages.tasks.meta.progressNote") }}</span>{{ taskWhereLine(task) }}
        </div>

        <div class="task-card-progress-block">
          <div class="task-progress-track">
            <div
              class="task-progress-fill"
              :class="progressFillClass(String(task.status))"
              :style="{ width: `${Math.min(100, Math.max(0, Number(task.progress || 0)))}%` }"
            />
          </div>
          <div class="task-progress-label">{{ $t("pages.tasks.meta.progress") }} {{ task.progress ?? 0 }}%</div>
        </div>

        <div v-if="predictionTaskOutcomeLine(task)" class="task-card-result-line">{{ predictionTaskOutcomeLine(task) }}</div>
      </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { TaskItem } from "../types";
import { formatDisplayDateTime } from "../utils/dateFormat";
import { formatPredictionTaskListOutcomeLine } from "../utils/predictionPresentation";
import { formatJobTypeLabel, formatTaskStatusLabel, isPrimaryTaskCategory, pickTaskActivityTime } from "../utils/taskPresentation";
import { formatTaskListProgressLine, formatTaskWhatItIs } from "../utils/taskStatusNarrative";

const props = withDefaults(
  defineProps<{
    tasks: Array<TaskItem & Record<string, unknown>>;
    selectedTaskId: string | null;
    loadError?: string;
    loading?: boolean;
    deletingTaskStatuses?: Record<string, string>;
  }>(),
  { loadError: "", loading: false, deletingTaskStatuses: () => ({}) },
);

defineEmits<{ (e: "selectTask", jobId: string): void; (e: "refresh"): void; (e: "deleteTask", jobId: string): void }>();

const statusFilter = ref("");
const typeFilter = ref("");
const sortKey = ref<"activity_desc" | "created_desc" | "created_asc">("activity_desc");
const { t } = useI18n();

const filtered = computed(() => {
  let rows = props.tasks;
  if (statusFilter.value) {
    rows = rows.filter((t) => String(t.status) === statusFilter.value);
  }
  if (typeFilter.value) {
    if (typeFilter.value === "__other__") {
      rows = rows.filter((t) => !isPrimaryTaskCategory(String(t.job_type || "")));
    } else {
      rows = rows.filter((t) => String(t.job_type || "") === typeFilter.value);
    }
  }
  return rows;
});

function parseTime(v: unknown): number {
  if (v == null || v === "") return 0;
  const t = new Date(String(v)).getTime();
  return Number.isFinite(t) ? t : 0;
}

const filteredSorted = computed(() => {
  const rows = [...filtered.value];
  if (sortKey.value === "created_desc") {
    rows.sort((a, b) => parseTime(b.created_at) - parseTime(a.created_at));
  } else if (sortKey.value === "created_asc") {
    rows.sort((a, b) => parseTime(a.created_at) - parseTime(b.created_at));
  } else {
    rows.sort((a, b) => {
      const ta = Math.max(parseTime((a as { updated_at?: string }).updated_at), parseTime(a.completed_at), parseTime(a.created_at));
      const tb = Math.max(parseTime((b as { updated_at?: string }).updated_at), parseTime(b.completed_at), parseTime(b.created_at));
      return tb - ta;
    });
  }
  return rows;
});

function predictionTaskOutcomeLine(t: TaskItem & Record<string, unknown>): string {
  if (String(t.job_type || "") !== "predict_outcome") return "";
  const st = String(t.status || "").toLowerCase();
  if (!["completed", "succeeded", "success"].includes(st)) return "";
  const rs = (t.result_summary || {}) as Record<string, unknown>;
  return formatPredictionTaskListOutcomeLine(rs);
}

function taskDisplayName(row: TaskItem & Record<string, unknown>): string {
  return formatTaskWhatItIs(row as Record<string, unknown>, t);
}

function taskWhereLine(row: TaskItem & Record<string, unknown>): string {
  return formatTaskListProgressLine(row as Record<string, unknown>, t);
}

function activity(t: TaskItem & Record<string, unknown>) {
  const a = pickTaskActivityTime(t);
  return {
    created: a.created ? formatDisplayDateTime(a.created) : "",
    updated: a.updated ? formatDisplayDateTime(a.updated) : "",
  };
}

function isDeleting(jobId: string): boolean {
  return Boolean((props.deletingTaskStatuses || {})[jobId]);
}

function deletingLabel(jobId: string): string {
  const st = String((props.deletingTaskStatuses || {})[jobId] || "");
  if (st === "canceling") return t("common.canceling");
  if (st === "deleting") return t("common.deleting");
  return t("common.processing");
}

function statusPillClass(status: string): string {
  const s = String(status).toLowerCase();
  if (s === "completed" || s === "succeeded" || s === "success") return "task-pill-success";
  if (s === "failed") return "task-pill-error";
  if (s === "running") return "task-pill-running";
  if (s === "waiting_user") return "task-pill-warn";
  if (s === "queued") return "task-pill-queue";
  if (s === "canceled" || s === "cancelled") return "task-pill-muted";
  return "task-pill-muted";
}

function progressFillClass(status: string): string {
  const s = String(status).toLowerCase();
  if (s === "failed") return "is-failed";
  if (s === "completed" || s === "succeeded") return "is-done";
  if (s === "canceled" || s === "cancelled") return "is-canceled";
  return "is-active";
}
</script>

<style scoped>
.tasks-page {
  color: var(--wb-text-primary);
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-4);
}

.tasks-page-flex {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.tasks-list-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: var(--wb-space-1);
}

.tasks-head {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-1);
}

.tasks-lead {
  margin: 0;
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-secondary);
  line-height: 1.5;
}

.tasks-toolbar {
  flex-shrink: 0;
  padding: var(--wb-space-3) var(--wb-space-4);
}

.tasks-toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-3);
  align-items: flex-end;
}

.tasks-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
}

.tasks-field-label {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  font-weight: 600;
}

.tasks-select {
  min-height: var(--wb-control-height-sm);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  padding: 0 10px;
  background: var(--wb-surface);
  color: var(--wb-text-primary);
  font-size: var(--wb-font-size-sm);
}

.tasks-banner {
  flex-shrink: 0;
  padding: var(--wb-space-3);
}

.tasks-banner-error {
  border-color: #e8c9c9;
  background: #fdf5f5;
}

.tasks-banner-title {
  font-weight: 650;
  margin-bottom: var(--wb-space-1);
}

.tasks-banner-text {
  margin: 0 0 var(--wb-space-2);
  font-size: var(--wb-font-size-sm);
}

.tasks-banner-meta {
  margin: var(--wb-space-2) 0 0;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.tasks-empty {
  flex-shrink: 0;
  padding: var(--wb-space-5);
  text-align: center;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
}

.tasks-empty-muted {
  border-style: dashed;
}

.tasks-loading {
  flex-shrink: 0;
  color: var(--wb-text-secondary);
  padding: var(--wb-space-3);
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.task-card {
  padding: var(--wb-space-3);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    box-shadow 0.15s ease;
}

.task-card:hover {
  border-color: var(--wb-border-strong);
  background: var(--wb-surface-soft);
}

.task-card-active {
  border-color: var(--wb-accent);
  background: var(--wb-accent-soft);
  box-shadow: var(--wb-shadow-sm), 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.task-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--wb-space-2);
}

.task-card-titles {
  min-width: 0;
  flex: 1;
}

.task-card-name {
  font-size: var(--wb-font-size-md);
  font-weight: 650;
  line-height: 1.35;
  word-break: break-word;
}

.task-card-sub {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.task-card-result-line {
  margin-top: 10px;
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-primary);
  line-height: 1.45;
  word-break: break-word;
}

.task-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
  border: 1px solid var(--wb-border-strong);
  color: var(--wb-text-secondary);
  background: #f7f8fa;
}

.task-pill-type {
  border-color: #d4dbe5;
  color: #445d79;
  background: #f4f7fb;
}

.task-pill-success {
  border-color: #b8d4c0;
  color: #1b5e2a;
  background: #f0faf2;
}

.task-pill-error {
  border-color: #e8b4b8;
  color: #8b1c2c;
  background: #fdf4f5;
}

.task-pill-running {
  border-color: #b8c9e6;
  color: #1a4a8c;
  background: #f3f7fd;
}

.task-pill-warn {
  border-color: #e2d0a8;
  color: #6a5220;
  background: #fffbf0;
}

.task-pill-queue {
  border-color: #ddd2a8;
  color: #6a5f1a;
  background: #fdfcf3;
}

.task-pill-muted {
  opacity: 0.9;
}

.task-card-delete {
  flex-shrink: 0;
}

.task-card-meta {
  margin-top: var(--wb-space-2);
  display: flex;
  flex-wrap: wrap;
  gap: var(--wb-space-3);
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
}

.meta-k {
  margin-right: 4px;
  color: var(--wb-text-primary);
  font-weight: 600;
}

.task-card-where {
  margin-top: 6px;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  line-height: 1.45;
}

.task-card-progress-block {
  margin-top: var(--wb-space-2);
}

.task-progress-track {
  height: 6px;
  background: #e8ecf2;
  border-radius: 999px;
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: #6b8cae;
  transition: width 0.2s ease;
}

.task-progress-fill.is-active {
  background: #4f6b8a;
}

.task-progress-fill.is-done {
  background: #5f8b6d;
}

.task-progress-fill.is-failed {
  background: #b56b6b;
}

.task-progress-fill.is-canceled {
  background: #9ca3af;
}

.task-progress-label {
  margin-top: 4px;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-muted);
}
</style>
