<template>
  <div v-if="failed" class="chat-workflow-fallback wb-card" data-testid="workflow-embed-fallback" role="alert">
    <p class="chat-workflow-fallback-text">{{ i18nT("app.shell.workflowStepUnavailable") }}</p>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t: i18nT } = useI18n();
const failed = ref(false);

onErrorCaptured((err) => {
  if (import.meta.env.DEV) console.warn("[SafeWorkflowEmbed]", err);
  failed.value = true;
  return false;
});
</script>

<style scoped>
.chat-workflow-fallback {
  padding: var(--wb-space-3);
  border: 1px dashed var(--wb-border-strong);
  border-radius: var(--wb-radius-sm);
  background: var(--wb-surface-soft);
}
.chat-workflow-fallback-text {
  margin: 0;
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-sm);
  line-height: 1.45;
}
</style>
