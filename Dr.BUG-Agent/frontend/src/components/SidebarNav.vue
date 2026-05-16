<template>
  <div class="sidebar-nav" data-testid="sidebar-nav">
    <button class="wb-btn wb-btn-primary sidebar-nav-new" @click="$emit('newSession')">
      + {{ $t("nav.newSession") }}
    </button>

    <button
      v-for="item in items"
      :key="item.key"
      class="sidebar-nav-item sidebar-nav-nav-btn"
      :class="{ 'is-active': active === item.key }"
      @click="$emit('change', item.key)"
    >
      {{ item.label }}
    </button>

    <div class="sidebar-nav-section">
      <h3 class="sidebar-nav-title">{{ $t("nav.sessions") }}</h3>
      <div v-if="sessions.length === 0" class="sidebar-nav-empty">{{ $t("nav.emptySessions") }}</div>
      <div
        v-for="s in sessions"
        :key="s.id"
        class="sidebar-nav-item sidebar-nav-session-btn"
        :class="{ 'is-active': activeSessionId === s.id }"
        @click="$emit('selectSession', s.id)"
      >
        <div class="sidebar-nav-item-title">{{ sessionSidebarTitle(s, t) }}</div>
        <div class="sidebar-nav-item-meta">{{ toDisplayTime(s.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { computed } from "vue";
import type { NavKey, SessionItem } from "../types";
import { formatDisplayDateTime } from "../utils/dateFormat";
import { sessionSidebarTitle } from "../utils/sessionPresentation";

defineProps<{
  active: NavKey;
  sessions: SessionItem[];
  activeSessionId: string | null;
}>();

defineEmits<{
  (e: "change", key: NavKey): void;
  (e: "newSession"): void;
  (e: "selectSession", sessionId: string): void;
}>();

const { t } = useI18n();

const items = computed<Array<{ key: NavKey; label: string }>>(() => [
  { key: "tasks", label: t("nav.tasks") },
  { key: "datasets", label: t("nav.datasets") },
  { key: "models", label: t("nav.models") },
  { key: "history", label: t("nav.history") },
]);

function toDisplayTime(v: string): string {
  return formatDisplayDateTime(v);
}
</script>

<style scoped>
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-3);
}

.sidebar-nav-new {
  width: 100%;
}

.sidebar-nav-section {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}

.sidebar-nav-title {
  margin: 0;
  font-size: var(--wb-sidebar-section-title-size);
  font-weight: var(--wb-sidebar-section-title-weight);
  color: var(--wb-text-primary);
}

.sidebar-nav-empty {
  padding: var(--wb-space-3);
  border: 1px dashed var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  color: var(--wb-text-secondary);
  font-size: var(--wb-sidebar-muted-size);
  line-height: var(--wb-sidebar-row-line-height);
}

.sidebar-nav-item {
  width: 100%;
  text-align: left;
  padding: var(--wb-space-2) var(--wb-chat-bubble-padding-x);
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface);
  color: var(--wb-text-primary);
  box-shadow: none;
  cursor: pointer;
  font-family: inherit;
  transition: border-color 120ms ease, background 120ms ease, color 120ms ease;
}

/** Top nav buttons: override UA font sizing to match tokens. */
.sidebar-nav-nav-btn {
  margin: 0;
  display: flex;
  align-items: center;
  font-size: var(--wb-font-size-md);
  font-weight: 400;
  line-height: 1.4;
  min-height: var(--wb-control-height);
}

.sidebar-nav-item:hover {
  border-color: var(--wb-border-strong);
  background: #f9fafb;
}

.sidebar-nav-item.is-active {
  border-color: var(--wb-accent);
  background: #f1f5f9;
  color: #1f2937;
  box-shadow: inset 3px 0 0 var(--wb-accent);
}

.sidebar-nav-item-title {
  font-size: var(--wb-sidebar-row-size);
  font-weight: var(--wb-sidebar-row-weight);
  line-height: var(--wb-sidebar-row-line-height);
}

.sidebar-nav-item-meta {
  margin-top: var(--wb-chat-bubble-gap);
  font-size: var(--wb-sidebar-muted-size);
  line-height: var(--wb-sidebar-row-line-height);
  color: var(--wb-text-muted);
}

.sidebar-nav-session-btn {
  width: 100%;
  max-width: 100%;
  padding: var(--wb-chat-input-padding-y) var(--wb-chat-bubble-padding-x);
  box-sizing: border-box;
  border-color: #e7ecf3;
  background: #fcfdff;
  color: var(--wb-text-secondary);
}

.sidebar-nav-session-btn .sidebar-nav-item-title {
  color: var(--wb-text-primary);
  font-size: var(--wb-font-size-md);
  font-weight: 400;
  line-height: 1.4;
}

.sidebar-nav-session-btn:hover {
  border-color: #d8e0ea;
  background: #f8fafd;
}

.sidebar-nav-session-btn.is-active {
  border-color: var(--wb-accent);
  background: #f1f5f9;
  color: #1f2937;
}

.sidebar-nav-item-title,
.sidebar-nav-item-meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
