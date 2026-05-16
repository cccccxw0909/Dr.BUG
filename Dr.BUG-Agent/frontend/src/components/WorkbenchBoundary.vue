<template>
  <div v-if="broken" class="wb-workbench-boundary wb-card" data-testid="workbench-boundary-fallback">
    <p class="wb-workbench-boundary-text">{{ t("app.shell.workbenchRenderFailed") }}</p>
    <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="recover">
      {{ t("app.shell.resetWorkflowUi") }}
    </button>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const emit = defineEmits<{ recover: [] }>();

const broken = ref(false);

onErrorCaptured((err) => {
  if (import.meta.env.DEV) console.error("[WorkbenchBoundary]", err);
  broken.value = true;
  return false;
});

function recover() {
  broken.value = false;
  emit("recover");
}
</script>

<style scoped>
.wb-workbench-boundary {
  padding: var(--wb-space-4);
  max-width: 42rem;
}
.wb-workbench-boundary-text {
  margin: 0 0 var(--wb-space-3);
  color: var(--wb-text-secondary);
  font-size: var(--wb-font-size-md);
  line-height: 1.5;
}
</style>
