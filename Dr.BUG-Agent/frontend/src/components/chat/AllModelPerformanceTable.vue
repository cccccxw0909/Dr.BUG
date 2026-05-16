<template>
  <div
    class="mpt-root"
    :class="{ 'mpt-embedded': embedded, 'mpt-workflow-embed': embedded && workflowTable }"
  >
    <button v-if="!embedded" type="button" class="wb-btn wb-btn-text wb-btn-sm" @click="toggleExpand">
      {{ expanded ? i18nT("chat.modelPerformanceTable.toggleCollapse") : i18nT("chat.modelPerformanceTable.toggleExpand") }}
    </button>
    <div v-if="bodyVisible" class="mpt-body">
      <div v-if="loading" class="mpt-muted">{{ i18nT("chat.modelPerformanceTable.loading") }}</div>
      <div v-else-if="errorMsg" class="mpt-error">{{ errorMsg }}</div>
      <template v-else-if="rows.length > 0">
        <div v-if="!workflowTable" class="mpt-summary-line">
          {{ i18nT("chat.modelPerformanceTable.summaryLine", { count: rows.length, metric: sortMetricLabel }) }}
        </div>
        <div v-if="rows.length === 1" class="mpt-warn-line">{{ i18nT("chat.modelPerformanceTable.singleModelHint") }}</div>
        <div class="mpt-table-scroll">
          <table class="mpt-table">
            <thead>
              <tr>
                <th>{{ i18nT("chat.modelPerformanceTable.colModel") }}</th>
                <th v-for="col in metricColumns" :key="col">{{ metricHeader(col) }}</th>
                <th v-if="!workflowTableSkipNotes">{{ notesHeader }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in rows"
                :key="r.model"
                :class="workflowRowClass(r.model)"
                :title="workflowFoldTooltip(r)"
              >
                <td class="mpt-cell-model">{{ r.model }}</td>
                <td
                  v-for="col in metricColumns"
                  :key="`${r.model}-${col}`"
                  :class="{ 'mpt-cell-best': workflowTable && isBestValueForMetric(r, col) }"
                  :title="metricCellTitle(r, col)"
                >
                  {{ formatMetricCellDisplay(r, col) }}
                </td>
                <td v-if="!workflowTableSkipNotes">{{ rowNote(r.model) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="mpt-muted">{{ emptyBodyText }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  cvRowModelToAlgorithmOption,
  TRAINING_WORKFLOW_ALGORITHM_OPTIONS,
} from "../../utils/cvModelSelection";
import { trainingMetricLabel } from "../../utils/trainingWorkflowPresentation";

const { t: i18nT } = useI18n();

const emit = defineEmits<{
  (
    e: "evidence-state",
    payload: { loading: boolean; rowCount: number; workflowMode: boolean; error: boolean },
  ): void;
}>();

type MetricRow = Record<string, unknown> & { model: string };

const props = defineProps<{
  artifacts?: Record<string, string>;
  resultSummary?: Record<string, unknown>;
  objectiveMetric?: string;
  finalModel?: string;
  mlTaskType?: string;
  /** When true, table starts expanded and loads rows on mount. */
  defaultExpanded?: boolean;
  /** Always show the table body (no expand/collapse toggle). */
  embedded?: boolean;
  /** Fixed columns for training workflow (classification vs regression). */
  workflowTable?: boolean;
  /** Phase4: highlight row matching algorithm `<select>` (e.g. lightgbm). */
  workflowSelectedAlgorithm?: string;
}>();

const expanded = ref(Boolean(props.defaultExpanded) || Boolean(props.embedded));
const errorMsg = ref("");

function bootstrapRowsFromSummary(): MetricRow[] {
  return sortRows(parseFromSummary(props.resultSummary || {}));
}

const initialSyncRows = bootstrapRowsFromSummary();
const rows = ref<MetricRow[]>(initialSyncRows);
/** When embedded workflow table already has rows from result_summary, skip initial loading spinner. */
const loading = ref(
  Boolean(props.embedded && props.workflowTable && initialSyncRows.length === 0),
);

const embedded = computed(() => Boolean(props.embedded));
const bodyVisible = computed(() => embedded.value || expanded.value);

const normObjective = computed(() => String(props.objectiveMetric || "").toLowerCase() || inferObjectiveFromRows(rows.value));
const sortMetricLabel = computed(() => {
  const n = String(normObjective.value || "").trim();
  return n ? trainingMetricLabel(n) : i18nT("chat.modelPerformanceTable.sortMetricPrimary");
});

const metricColumns = computed(() => {
  if (props.workflowTable) {
    return inferIsRegressionForPreset()
      ? ["mse", "pcc"]
      : ["accuracy", "precision", "recall", "f1", "auroc", "auprc"];
  }
  const isReg = inferIsRegression();
  // Single F1 column: formatMetricCell resolves f1 vs f1_score.
  return isReg ? ["mse", "mae", "rmse", "pearson", "pcc", "r2"] : ["accuracy", "precision", "recall", "f1", "auroc", "auprc"];
});

const workflowTableSkipNotes = computed(() => Boolean(props.workflowTable));

const notesHeader = computed(() => i18nT("chat.modelPerformanceTable.colNotes"));

const emptyBodyText = computed(() => {
  if (props.workflowTable) return i18nT("chat.modelPerformanceTable.modelComparisonLegacyFallback");
  return i18nT("chat.modelPerformanceTable.empty");
});

function inferIsRegressionForPreset(): boolean {
  return String(props.mlTaskType || "").toLowerCase() === "regression";
}

function inferIsRegression(): boolean {
  if (String(props.mlTaskType || "").toLowerCase() === "regression") return true;
  const keys = new Set<string>();
  for (const r of rows.value) Object.keys(r).forEach((k) => keys.add(k.toLowerCase()));
  return keys.has("mse") || keys.has("rmse") || keys.has("mae") || keys.has("r2");
}

function inferObjectiveFromRows(data: MetricRow[]): string {
  if (data.some((r) => r.auroc != null)) return "auroc";
  if (data.some((r) => r.f1 != null || r.f1_score != null)) return "f1";
  if (data.some((r) => r.accuracy != null)) return "accuracy";
  if (data.some((r) => r.rmse != null)) return "rmse";
  if (data.some((r) => r.mse != null)) return "mse";
  return "";
}

function metricHeader(key: string): string {
  if (props.workflowTable && key === "pcc") return i18nT("chat.modelPerformanceTable.metricShort.pcc");
  if (props.workflowTable && key === "f1") return trainingMetricLabel("f1_score");
  return trainingMetricLabel(key);
}

function resolveMetricRaw(r: MetricRow, col: string): unknown {
  if (col === "f1") return r.f1 ?? r.f1_score;
  if (col === "pcc") return r.pcc ?? r.pearson;
  return r[col];
}

/** Mean (or single value) shown in the cell; std goes to title when workflowTable. */
function formatMetricCellDisplay(r: MetricRow, col: string): string {
  return formatMetric(resolveMetricRaw(r, col));
}

function formatMetricCellTitleFull(r: MetricRow, col: string): string {
  const base = formatMetric(resolveMetricRaw(r, col));
  const sdKey = `${col}_std`;
  const sd = r[sdKey];
  if (sd != null && sd !== "" && Number(sd) !== 0) {
    return `${base} ± ${formatMetric(sd)}`;
  }
  return base;
}

function metricCellTitle(r: MetricRow, col: string): string {
  if (props.workflowTable) return formatMetricCellTitleFull(r, col);
  return formatMetricCellTitleFull(r, col);
}

function workflowFoldTooltip(r: MetricRow): string {
  if (!props.workflowTable) return "";
  const fm = r.fold_metrics;
  if (!Array.isArray(fm) || fm.length === 0) return "";
  try {
    return fm.map((fold) => JSON.stringify(fold)).join("\n");
  } catch {
    return "";
  }
}

function formatMetric(v: unknown): string {
  if (v == null || v === "") return i18nT("common.na");
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(4) : String(v);
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(4) : String(v);
}

function isFinalModel(model: string): boolean {
  const f = String(props.finalModel || "").toLowerCase();
  if (!f) return false;
  const m = String(model || "").toLowerCase();
  return m === f || m.includes(f) || f.includes(m);
}

function rowNote(model: string): string {
  if (workflowTableSkipNotes.value) return "";
  const notes: string[] = [];
  const sep = i18nT("chat.modelPerformanceTable.noteJoin");
  if (isFinalModel(model)) notes.push(i18nT("chat.modelPerformanceTable.noteFinalModel"));
  if (isBestByObjective(model)) notes.push(i18nT("chat.modelPerformanceTable.noteBestObjective"));
  return notes.join(sep) || i18nT("common.na");
}

function isBestByObjective(model: string): boolean {
  const om = normObjective.value;
  if (!om || rows.value.length === 0) return false;
  const sorted = [...rows.value].sort((a, b) => compareByMetric(a, b, om));
  return sorted.length > 0 && sorted[0].model === model;
}

function workflowRowClass(model: string): Record<string, boolean> {
  const sel = String(props.workflowSelectedAlgorithm || "").trim().toLowerCase();
  const picked = sel
    ? cvRowModelToAlgorithmOption(model, TRAINING_WORKFLOW_ALGORITHM_OPTIONS as unknown as string[]) === sel
    : false;
  return {
    "mpt-row-selected": Boolean(props.workflowTable && picked),
    "mpt-row-final": Boolean(!props.workflowTable && isFinalModel(model)),
  };
}

function isBestValueForMetric(row: MetricRow, metricKey: string): boolean {
  if (!props.workflowTable || rows.value.length === 0) return false;
  const mk = String(metricKey || "").toLowerCase();
  const lowerIsBetter = mk === "mse";
  const cur = toNum(resolveMetricRaw(row, mk));
  if (cur == null) return false;
  const nums: number[] = [];
  for (const r of rows.value) {
    const n = toNum(resolveMetricRaw(r, mk));
    if (n != null) nums.push(n);
  }
  if (!nums.length) return false;
  const best = lowerIsBetter ? Math.min(...nums) : Math.max(...nums);
  return Math.abs(cur - best) <= 1e-6 || cur === best;
}

function compareByMetric(a: MetricRow, b: MetricRow, metric: string): number {
  const av = toNum(resolveMetricValue(a, metric));
  const bv = toNum(resolveMetricValue(b, metric));
  if (av == null && bv == null) return 0;
  if (av == null) return 1;
  if (bv == null) return -1;
  const asc = metric === "mse" || metric === "mae" || metric === "rmse";
  return asc ? av - bv : bv - av;
}

function resolveMetricValue(r: MetricRow, metric: string): unknown {
  const m = String(metric || "").toLowerCase();
  if (m === "f1") return r.f1 ?? r.f1_score;
  if (m === "pearson") return r.pearson ?? r.pcc;
  return r[m];
}

function toNum(v: unknown): number | null {
  if (v == null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

async function toggleExpand() {
  if (embedded.value) return;
  expanded.value = !expanded.value;
  if (!expanded.value || rows.value.length || loading.value) return;
  await loadRows();
}

onMounted(async () => {
  if (!props.embedded && !props.defaultExpanded) return;
  expanded.value = true;
  await loadRows();
});

watch(
  () => props.resultSummary,
  async () => {
    if (!bodyVisible.value) return;
    await loadRows();
  },
  { deep: true },
);

watch(
  () => props.artifacts,
  async () => {
    if (!bodyVisible.value) return;
    await loadRows();
  },
  { deep: true },
);

function emitEvidenceState() {
  emit("evidence-state", {
    loading: loading.value,
    rowCount: rows.value.length,
    workflowMode: Boolean(props.workflowTable),
    error: Boolean(errorMsg.value),
  });
}

async function loadRows() {
  errorMsg.value = "";
  try {
    const fromSummary = parseFromSummary(props.resultSummary || {});
    if (fromSummary.length > 0) {
      rows.value = sortRows(fromSummary);
      loading.value = false;
      emitEvidenceState();
      return;
    }
    loading.value = true;
    const rowsFromArtifacts = await parseFromArtifacts(props.artifacts || {});
    rows.value = sortRows(rowsFromArtifacts);
  } catch (e) {
    errorMsg.value = i18nT("chat.modelPerformanceTable.loadFailed", { message: String(e) });
  } finally {
    loading.value = false;
    emitEvidenceState();
  }
}

watch([rows, loading], () => emitEvidenceState(), { immediate: true });

function sortRows(src: MetricRow[]): MetricRow[] {
  if (props.workflowTable) return [...src];
  const om = normObjective.value;
  if (!om) return src;
  return [...src].sort((a, b) => compareByMetric(a, b, om));
}

function parseFromSummary(summary: Record<string, unknown>): MetricRow[] {
  const rowsRaw = summary.all_model_metrics_rows;
  if (Array.isArray(rowsRaw)) {
    return rowsRaw
      .filter((x) => x && typeof x === "object")
      .map((x) => normalizeRow(x as Record<string, unknown>))
      .filter((x) => x.model);
  }
  return [];
}

function artifactBasename(key: string): string {
  const k = String(key || "").replace(/\\/g, "/").trim().toLowerCase();
  return k.split("/").pop() || k;
}

/**
 * Match backend/client artifact keys: basename, path suffix, or substring (e.g. artifacts/all_model_metrics.json).
 */
function artifactKeyMatchesFile(key: string, wantedFile: string): boolean {
  const normKey = String(key || "").replace(/\\/g, "/").toLowerCase();
  const want = wantedFile.toLowerCase();
  const base = artifactBasename(key);
  if (!want) return false;
  if (base === want) return true;
  if (base.endsWith(want)) return true;
  if (normKey.endsWith("/" + want)) return true;
  if (normKey.includes("/" + want) || normKey.includes(want)) return true;
  if (want.endsWith(".json")) {
    const stem = want.slice(0, -5);
    if (stem && (base === stem || base.startsWith(stem + "."))) return true;
  }
  return false;
}

function rankArtifactKeyMatch(key: string, wantedFile: string): number {
  const base = artifactBasename(key);
  const want = wantedFile.toLowerCase();
  if (base === want) return 0;
  if (base.endsWith(want)) return 1;
  return 2;
}

function resolveArtifactUrlForFile(artifacts: Record<string, string>, wantedFile: string): string | null {
  const entries = Object.entries(artifacts);
  const candidates = entries.filter(([k]) => artifactKeyMatchesFile(k, wantedFile));
  if (candidates.length === 0) return null;
  candidates.sort(([a], [b]) => {
    const d = rankArtifactKeyMatch(a, wantedFile) - rankArtifactKeyMatch(b, wantedFile);
    return d !== 0 ? d : a.localeCompare(b);
  });
  const url = candidates[0]?.[1];
  return url != null && String(url).trim() !== "" ? String(url) : null;
}

async function parseFromArtifacts(artifacts: Record<string, string>): Promise<MetricRow[]> {
  const priority = [
    "all_model_metrics.json",
    "model_comparison.json",
    "metrics_summary.json",
    "cv_results.json",
    "summary.json",
  ];
  for (const name of priority) {
    const url = resolveArtifactUrlForFile(artifacts, name);
    if (!url) continue;
    try {
      const data = await fetchJson(url);
      const extracted = extractRowsFromJson(name, data);
      if (extracted.length > 0) return extracted;
    } catch {
      // try next source
    }
  }
  return [];
}

async function fetchJson(url: string): Promise<unknown> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function jsonSourceBasename(fileName: string): string {
  return String(fileName || "").replace(/\\/g, "/").split("/").pop() || String(fileName || "");
}

function extractRowsFromJson(fileName: string, data: unknown): MetricRow[] {
  if (!data || typeof data !== "object") return [];
  const obj = data as Record<string, unknown>;
  const base = jsonSourceBasename(fileName).toLowerCase();

  if (Array.isArray(obj.all_model_metrics_rows)) {
    return obj.all_model_metrics_rows
      .filter((x) => x && typeof x === "object")
      .map((x) => normalizeRow(x as Record<string, unknown>))
      .filter((x) => x.model);
  }
  if (Array.isArray(obj.rows)) {
    return obj.rows
      .filter((x) => x && typeof x === "object")
      .map((x) => normalizeRow(x as Record<string, unknown>))
      .filter((x) => x.model);
  }
  if (base === "cv_results.json" || base.endsWith("cv_results.json")) {
    return Object.entries(obj).map(([model, val]) => {
      const row: Record<string, unknown> = { model };
      if (val && typeof val === "object") {
        for (const [k, v] of Object.entries(val as Record<string, unknown>)) {
          if (v && typeof v === "object" && "mean" in (v as Record<string, unknown>)) {
            row[k.toLowerCase().replace("-", "_")] = (v as Record<string, unknown>).mean;
          }
        }
      }
      return normalizeRow(row);
    });
  }
  if (obj.all_model_metrics && Array.isArray(obj.all_model_metrics)) {
    return (obj.all_model_metrics as Array<Record<string, unknown>>)
      .map((x) => normalizeRow(x))
      .filter((x) => x.model);
  }
  return [];
}

function normalizeRow(src: Record<string, unknown>): MetricRow {
  const out: MetricRow = { model: String(src.model || src.model_name || src.name || "") };
  for (const [k, v] of Object.entries(src)) {
    const nk = k.toLowerCase().replace("-", "_");
    if (nk === "model" || nk === "model_name" || nk === "name") continue;
    out[nk] = v;
  }
  if (out.f1 == null && out.f1_score != null) out.f1 = out.f1_score;
  return out;
}
</script>

<style scoped>
.mpt-root {
  margin-top: 8px;
}
.mpt-root.mpt-embedded {
  margin-top: 0;
}
.mpt-body {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
}
.mpt-embedded .mpt-body {
  margin-top: 0;
}

.mpt-workflow-embed .mpt-body {
  padding: 0;
  border: none;
  background: transparent;
}

.mpt-workflow-embed .mpt-table-scroll {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.mpt-muted {
  color: var(--wb-text-caption-muted);
}
.mpt-error {
  color: #b00020;
}
.mpt-summary-line {
  margin-bottom: 6px;
  color: var(--wb-text-body-secondary);
}
.mpt-warn-line {
  margin-bottom: 6px;
  color: #7a5600;
}
.mpt-table-scroll {
  overflow: auto;
}
.mpt-table {
  border-collapse: collapse;
  width: 100%;
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
}
.mpt-table th {
  text-align: left;
  border-bottom: 1px solid #ddd;
  padding: 4px 6px;
}
.mpt-table td {
  border-bottom: 1px solid #f0f0f0;
  padding: 4px 6px;
}
.mpt-cell-model {
  font-weight: 600;
}
.mpt-row-final {
  background: #e6ffed;
}

.mpt-row-selected {
  background: rgba(15, 23, 42, 0.04);
}

.mpt-cell-best {
  font-weight: 700;
}
</style>
