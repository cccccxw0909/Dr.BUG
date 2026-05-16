<template>
  <div class="bpr-root">
    <section class="bpr-stats">
      <div class="bpr-stat">
        <span class="bpr-stat-label">{{ t("prediction.batchResult.uploadedTable") }}</span>
        <span class="bpr-stat-value">{{ data.file_name || na }}</span>
      </div>
      <div class="bpr-stat">
        <span class="bpr-stat-label">{{ t("prediction.batchResult.totalRecords") }}</span>
        <span class="bpr-stat-value">{{ data.total_rows }}</span>
      </div>
      <div class="bpr-stat">
        <span class="bpr-stat-label">{{ t("prediction.batchResult.succeeded") }}</span>
        <span class="bpr-stat-value">{{ data.succeeded_rows }}</span>
      </div>
      <div class="bpr-stat">
        <span class="bpr-stat-label">{{ t("prediction.batchResult.failed") }}</span>
        <span
          class="bpr-stat-value"
          :class="{ 'bpr-stat-value-failed': data.failed_rows > 0 }"
        >{{ data.failed_rows }}</span>
      </div>
    </section>

    <div class="bpr-actions">
      <a
        v-if="downloadHref !== '#'"
        class="wb-btn wb-btn-primary"
        :href="downloadHref"
        target="_blank"
        rel="noopener"
      >{{ t("prediction.batchResult.downloadResults") }}</a>
      <span v-else class="bpr-muted">{{ t("prediction.batchResult.noDownloadLink") }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { BatchPredictionRunResponse } from "../../types";

const props = defineProps<{ data: BatchPredictionRunResponse }>();
const { t } = useI18n();

const na = computed(() => t("common.na"));

const downloadHref = computed(() => {
  const raw = props.data.download_url || "";
  if (!raw) return "#";
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  return raw;
});
</script>

<style scoped>
/** Content-only root; white report frame from ChatMessageList `.chat-embed-card`. */
.bpr-root {
  margin: 0;
  padding: 0;
  max-width: 100%;
  box-sizing: border-box;
  border: none;
  background: transparent;
}
.bpr-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--wb-space-2);
  margin-bottom: var(--wb-space-3);
}
@media (min-width: 640px) {
  .bpr-stats {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.bpr-stat {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: var(--wb-radius-sm);
  padding: var(--wb-chat-input-padding-y) var(--wb-chat-bubble-padding-x);
  box-sizing: border-box;
  text-align: center;
}
.bpr-stat-label {
  display: block;
  font-size: 17px;
  color: #111827;
  font-weight: 600;
  line-height: 1.35;
}
.bpr-stat-value {
  display: block;
  margin-top: var(--wb-space-1);
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  line-height: 1.25;
  word-break: break-word;
}
.bpr-stat-value-failed {
  color: #991b1b;
}

.bpr-actions {
  margin-bottom: 0;
}
.bpr-actions a {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.bpr-muted {
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-muted);
}
</style>
