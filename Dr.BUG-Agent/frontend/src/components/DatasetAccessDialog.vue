<template>
  <Teleport to="body">
    <div class="dad-overlay" role="presentation" @click.self="$emit('close')">
      <div class="dad-dialog wb-card" role="dialog" :aria-label="dialogAriaLabel">
        <div class="dad-head">
          <h4 class="dad-title">{{ title }}</h4>
          <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="$emit('close')">
            {{ i18nT("common.close") }}
          </button>
        </div>
        <p v-if="subtitle" class="dad-sub">{{ subtitle }}</p>

        <div v-if="loading" class="dad-state">{{ i18nT("panels.context.datasetAccess.loading") }}</div>
        <div v-else-if="errorMessage" class="dad-state dad-error">{{ errorMessage }}</div>

        <template v-else-if="mode === 'preview' && preview">
          <dl class="dad-kv">
            <div class="dad-kv-row">
              <dt>{{ i18nT("panels.context.datasetAccess.rowCount") }}</dt>
              <dd>{{ preview.row_count }}</dd>
            </div>
            <div class="dad-kv-row">
              <dt>{{ i18nT("panels.context.datasetAccess.columnCount") }}</dt>
              <dd>{{ preview.column_count }}</dd>
            </div>
          </dl>
          <div v-if="columnNames.length" class="dad-block">
            <div class="dad-block-title">{{ i18nT("panels.context.datasetAccess.fieldNames") }}</div>
            <p class="dad-field-names">{{ columnNames.join(", ") }}</p>
          </div>
          <div v-if="preview.rows?.length && tableColumns.length" class="dad-block">
            <div class="dad-block-title">{{ i18nT("panels.context.datasetAccess.sampleRows") }}</div>
            <div class="dad-table-wrap">
              <table class="dad-table">
                <thead>
                  <tr>
                    <th v-for="col in tableColumns" :key="col">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in preview.rows" :key="ri">
                    <td v-for="col in tableColumns" :key="col">{{ formatCell(row[col]) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <p v-else-if="preview.row_count > 0" class="dad-state">{{ i18nT("panels.context.datasetAccess.noSampleRows") }}</p>
          <p class="dad-privacy">{{ i18nT("panels.context.datasetAccess.privacyNote") }}</p>
        </template>

        <template v-else-if="mode === 'schema' && schema">
          <div class="dad-table-wrap">
            <table class="dad-table">
              <thead>
                <tr>
                  <th>{{ i18nT("panels.context.datasetAccess.schemaColumn") }}</th>
                  <th>{{ i18nT("panels.context.datasetAccess.schemaDtype") }}</th>
                  <th>{{ i18nT("panels.context.datasetAccess.schemaNumeric") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in schema.columns" :key="c.name">
                  <td>{{ c.name }}</td>
                  <td>{{ c.dtype }}</td>
                  <td>{{ c.is_numeric ? i18nT("predictionPresentation.boolean.yes") : i18nT("predictionPresentation.boolean.no") }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ApiError, getDatasetPreview, getDatasetSchema } from "../api";
import type { DatasetPreviewInfo, DatasetSchemaInfo } from "../types";

const props = defineProps<{
  datasetId: string;
  datasetLabel?: string;
  mode: "preview" | "schema";
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "previewFailed", datasetId: string): void;
}>();

const { t: i18nT } = useI18n();

const loading = ref(true);
const errorMessage = ref("");
const preview = ref<DatasetPreviewInfo | null>(null);
const schema = ref<DatasetSchemaInfo | null>(null);

const title = computed(() => {
  const bit =
    props.mode === "preview"
      ? i18nT("panels.context.actions.previewDataset")
      : i18nT("panels.context.actions.viewFieldSchema");
  const name = (props.datasetLabel || "").trim();
  return name ? `${bit} — ${name}` : bit;
});

const subtitle = computed(() =>
  props.datasetLabel ? "" : i18nT("panels.context.datasetAccess.dialogSubtitleId", { id: props.datasetId }),
);

const dialogAriaLabel = computed(() => title.value);

const columnNames = computed(() => {
  const rows = preview.value?.rows;
  if (!rows?.length) return [];
  const keys = new Set<string>();
  for (const r of rows) {
    Object.keys(r).forEach((k) => keys.add(k));
  }
  return Array.from(keys);
});

const tableColumns = computed(() => columnNames.value);

function formatCell(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

async function load() {
  loading.value = true;
  errorMessage.value = "";
  preview.value = null;
  schema.value = null;
  const id = String(props.datasetId || "").trim();
  if (!id) {
    errorMessage.value = i18nT("panels.context.datasetAccess.missingId");
    loading.value = false;
    return;
  }
  try {
    if (props.mode === "preview") {
      const { preview: p } = await getDatasetPreview(id, { limit: 10 });
      preview.value = p;
    } else {
      const { schema: s } = await getDatasetSchema(id);
      schema.value = s;
    }
  } catch (e) {
    const msg = e instanceof ApiError ? e.message : String(e);
    errorMessage.value = msg;
    if (props.mode === "preview") emit("previewFailed", id);
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.datasetId, props.mode] as const,
  () => {
    void load();
  },
);

onMounted(() => {
  void load();
});
</script>

<style scoped>
.dad-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--wb-space-4);
  box-sizing: border-box;
}

.dad-dialog {
  width: min(720px, 100%);
  max-height: min(88vh, 900px);
  overflow: auto;
  padding: var(--wb-space-4);
  box-sizing: border-box;
}

.dad-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wb-space-3);
}

.dad-title {
  margin: 0;
  font-size: var(--wb-font-size-md);
  font-weight: 650;
}

.dad-sub {
  margin: var(--wb-space-2) 0 0;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-muted);
}

.dad-state {
  margin-top: var(--wb-space-3);
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-secondary);
}

.dad-error {
  color: var(--wb-error);
}

.dad-kv {
  margin: var(--wb-space-3) 0 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dad-kv-row {
  display: flex;
  gap: var(--wb-space-2);
  font-size: var(--wb-font-size-xs);
}

.dad-kv-row dt {
  margin: 0;
  color: var(--wb-text-secondary);
  min-width: 7rem;
}

.dad-kv-row dd {
  margin: 0;
  font-weight: 600;
}

.dad-block {
  margin-top: var(--wb-space-3);
}

.dad-block-title {
  font-size: var(--wb-font-size-xs);
  font-weight: 600;
  color: var(--wb-text-secondary);
  margin-bottom: 4px;
}

.dad-field-names {
  margin: 0;
  font-size: var(--wb-font-size-xs);
  line-height: 1.45;
  word-break: break-word;
}

.dad-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
}

.dad-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.dad-table th,
.dad-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--wb-border);
  text-align: left;
  vertical-align: top;
}

.dad-table th {
  background: var(--wb-surface-soft);
  font-weight: 600;
}

.dad-privacy {
  margin: var(--wb-space-3) 0 0;
  font-size: var(--wb-font-size-xs);
  color: var(--wb-text-secondary);
  line-height: 1.5;
}
</style>
