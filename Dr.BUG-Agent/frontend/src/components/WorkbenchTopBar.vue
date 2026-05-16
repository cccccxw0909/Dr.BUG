<template>
  <header class="workbench-topbar" data-testid="workbench-topbar">
    <div class="workbench-topbar-brand">Dr.BUG</div>
    <div class="workbench-topbar-actions">
      <LanguageToggle />
    </div>
  </header>
</template>

<script setup lang="ts">
import LanguageToggle from "./LanguageToggle.vue";
</script>

<style scoped>
.workbench-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--wb-topbar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 24px 0;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid var(--wb-border);
  z-index: 50;
  box-sizing: border-box;
}

@media (max-width: 640px) {
  .workbench-topbar {
    padding: 4px 14px 0;
  }
}

.workbench-topbar-brand {
  font-size: 22px;
  font-weight: 700;
  color: var(--wb-text-main);
  letter-spacing: -0.01em;
  flex-shrink: 0;
  line-height: 1.2;
  margin-left: 12px;
}

.workbench-topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  min-width: 0;
}
</style>
