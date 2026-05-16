<template>
  <div class="wb-shell-root">
    <WorkbenchTopBar />
    <div class="wb-layout" :class="{ 'wb-layout-no-right': hideRight }">
      <aside class="wb-layout-panel wb-layout-panel-left wb-card" data-testid="shell-sidebar">
        <slot name="left" />
      </aside>
      <main class="wb-layout-panel wb-layout-panel-main wb-card" data-testid="shell-main">
        <slot name="main" />
      </main>
      <section
        v-if="!hideRight"
        class="wb-layout-panel wb-layout-panel-right wb-card"
        data-testid="shell-workspace-status"
      >
        <slot name="right" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import WorkbenchTopBar from "../components/WorkbenchTopBar.vue";

withDefaults(
  defineProps<{
    hideRight?: boolean;
  }>(),
  { hideRight: false },
);
</script>

<style scoped>
.wb-shell-root {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100dvh;
  min-height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  padding-top: var(--wb-topbar-height);
}

.wb-layout {
  flex: 1 1 auto;
  min-height: 0;
  box-sizing: border-box;
  overflow: hidden;
  display: grid;
  grid-template-columns:
    var(--wb-shell-sidebar-width) minmax(0, 1fr)
    minmax(var(--wb-shell-detail-panel-min), var(--wb-shell-detail-panel-max));
  grid-template-rows: minmax(0, 1fr);
  gap: var(--wb-space-4);
  background: var(--wb-bg);
  padding: 10px var(--wb-space-4) var(--wb-space-4);
}

.wb-layout.wb-layout-no-right {
  grid-template-columns: var(--wb-shell-sidebar-width) minmax(0, 1fr);
}

.wb-layout-panel {
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  padding: var(--wb-space-4);
  background: var(--wb-surface);
  overflow: hidden;
}

.wb-layout-panel-left {
  padding: var(--wb-space-3);
  overflow-y: auto;
  overflow-x: hidden;
}

/**
 * Center column: primary white workspace card (aligns visually with side panels).
 * Inner routes control their own inset; Workbench uses full card height with internal scroll + composer.
 */
.wb-layout-panel-main {
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.wb-layout-panel-right {
  background: var(--wb-surface-soft);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  /** Tighter horizontal inset so detail cards and scrollbar sit nearer the panel edge. */
  padding-left: var(--wb-space-3);
  padding-right: var(--wb-space-1);
}

.wb-layout-panel-right > * {
  min-width: 0;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
</style>
