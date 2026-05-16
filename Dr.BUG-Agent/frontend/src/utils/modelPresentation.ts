import type { Translate } from "./messageSanitizer";
import type { PredictionModelListItem } from "../types";
import { summarizeFeatureSources } from "./taskPresentation";

/** Collapse `X — X` duplicated labels (same as backend normalize_duplicate_em_dash_label). */
export function normalizeDuplicateEmDashLabel(raw: string): string {
  const t = String(raw || "").trim();
  if (!t.includes(" — ")) return t;
  const parts = t.split(" — ");
  if (parts.length === 2 && parts[0].trim() === parts[1].trim()) return parts[0].trim();
  return t;
}

export type ModelRecord = Record<string, unknown>;

function loc(t: Translate | undefined, key: string, values?: Record<string, unknown>, en?: string): string {
  if (t) return values ? String(t(key, values)) : String(t(key));
  return en ?? "";
}

function missingPlaceholder(t?: Translate): string {
  return loc(t, "models.presentation.missingName", {}, "-");
}

/** Display name: do not invent values; fall back through existing fields only. */
export function modelDisplayName(m: ModelRecord | null | undefined, t?: Translate): string {
  if (!m) return missingPlaceholder(t);
  const cand = ["display_name", "model_name", "name", "task_name", "model_id"] as const;
  for (const k of cand) {
    const v = m[k];
    if (v != null && String(v).trim() !== "") return String(v);
  }
  return missingPlaceholder(t);
}

/** Task-first label for prediction/regimen dropdowns (clinical_task-aware when present). */
export function predictionModelPrimaryDisplayLabel(
  m: {
    model_id: string;
    display_name?: string;
    task_name?: string;
    clinical_task_id?: string;
    metadata?: Record<string, unknown>;
    model_type?: string;
  },
  t?: Translate,
): string {
  const meta =
    m.metadata && typeof m.metadata === "object" ? (m.metadata as Record<string, unknown>) : undefined;
  const ctRaw = String(m.clinical_task_id ?? meta?.clinical_task_id ?? "").trim();
  if (ctRaw && t) {
    const key = `models.presentation.taskOriented.${ctRaw}`;
    try {
      const phrase = t(key);
      if (phrase && phrase !== key) return phrase;
    } catch {
      /* fall through */
    }
  }
  const taskName = String(m.task_name || "").trim();
  if (taskName && !/^model[\w-]*$/i.test(taskName) && taskName.length > 2) return taskName;
  const dn = String(m.display_name || "").trim();
  if (dn && dn !== m.model_id) return dn;
  return m.model_id ? String(m.model_id) : missingPlaceholder(t);
}

/** Display algorithm/backbone type separately from ML task type. */
export function formatModelTypeLabel(raw: string | null | undefined, t?: Translate): string {
  if (raw == null || raw === "") return missingPlaceholder(t);
  const s = String(raw).trim();
  const key = s.toLowerCase().replace(/[\s-]+/g, "_");
  const map: Record<string, string> = {
    catboost: "CatBoost",
    xgboost: "XGBoost",
    lightgbm: "LightGBM",
    random_forest: "Random forest",
    logistic_regression: "Logistic regression",
    svm: "SVM",
    knn: "kNN",
  };
  if (map[key]) return map[key];
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Display-oriented ML task type from the model registry; avoids exposing raw internal enums such as binary. */
export function formatMlTaskKindDisplay(raw: string | null | undefined, t?: Translate): string {
  const s = String(raw || "").trim().toLowerCase();
  if (!s) return missingPlaceholder(t);
  if (s === "binary_classification" || s === "binary") return "Binary classification";
  if (s === "multiclass" || s === "multi_class" || s === "multinomial") return "Multiclass classification";
  if (s === "multilabel") return "Multilabel classification";
  if (s === "regression") return "Regression";
  if (s === "survival") return "Survival";
  return String(raw);
}

/** True if the string is an ML problem type, not an estimator (e.g. LightGBM). */
export function isMlTaskKindOnly(raw: string | null | undefined): boolean {
  const k = String(raw || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/-/g, "_");
  return (
    k === "binary" ||
    k === "multiclass" ||
    k === "regression" ||
    k === "binary_classification" ||
    k === "classification" ||
    k === "multi_class" ||
    k === "multinomial" ||
    k === "continuous" ||
    k === "multilabel"
  );
}

function pickPredictionDisplayName(m: PredictionModelListItem, t?: Translate): string {
  const d = String(m.display_name || "").trim();
  if (d) return normalizeDuplicateEmDashLabel(d);
  const mn = String(m.model_name || "").trim();
  if (mn) return normalizeDuplicateEmDashLabel(mn);
  const n = m.name != null ? String(m.name).trim() : "";
  if (n) return normalizeDuplicateEmDashLabel(n);
  return normalizeDuplicateEmDashLabel(String(m.model_id || "").trim() || missingPlaceholder(t));
}

function pickEstimatorAlgorithmString(m: PredictionModelListItem): string {
  const meta = m.metadata && typeof m.metadata === "object" ? (m.metadata as Record<string, unknown>) : undefined;
  const candidates: unknown[] = [m.algorithm, m.model_family, meta?.estimator, meta?.algorithm, m.model_type];
  for (const c of candidates) {
    if (c == null || c === "") continue;
    const s = String(c).trim();
    if (!s || isMlTaskKindOnly(s)) continue;
    return s;
  }
  return "";
}

function parseOptionalEpochMs(iso: string | null | undefined): number | null {
  const s = String(iso || "").trim();
  if (!s) return null;
  const ms = Date.parse(s.endsWith("Z") ? s : s.includes("T") || s.includes(":") ? s : `${s}T00:00:00Z`);
  return Number.isNaN(ms) ? null : ms;
}

/** Short timestamp for duplicate disambiguation (local wall clock). */
export function formatPublishedAtShort(iso: string | null | undefined): string {
  const s = String(iso || "").trim();
  if (!s) return "";
  const ms = parseOptionalEpochMs(s);
  if (ms == null) return s.length > 16 ? s.slice(0, 16) : s;
  const dt = new Date(ms);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

/**
 * Base dropdown line (no collision suffix). Order: name · algorithm · vversion.
 */
export function buildPredictionModelOptionBaseLabel(model: PredictionModelListItem, t?: Translate): string {
  const displayName = pickPredictionDisplayName(model, t);
  const algoRaw = pickEstimatorAlgorithmString(model);
  let line: string;
  if (algoRaw) {
    line = `${displayName} · ${formatModelTypeLabel(algoRaw, t)}`;
  } else {
    line = displayName;
  }
  const ver = model.version != null ? String(model.version).trim() : "";
  if (ver) line = `${line} · v${ver}`;
  return line;
}

/**
 * Per-model_id labels; appends published/registered time only when the base label repeats in the list.
 */
export function buildPredictionModelOptionLabelMap(
  items: PredictionModelListItem[],
  t?: Translate,
): Record<string, string> {
  const bases = items.map((m) => ({ m, base: buildPredictionModelOptionBaseLabel(m, t) }));
  const counts = new Map<string, number>();
  for (const { base } of bases) counts.set(base, (counts.get(base) ?? 0) + 1);
  const out: Record<string, string> = {};
  for (const { m, base } of bases) {
    let line = base;
    if ((counts.get(base) ?? 0) > 1) {
      const stamp =
        formatPublishedAtShort(m.published_at) ||
        formatPublishedAtShort(m.registered_at) ||
        formatPublishedAtShort(m.released_at);
      if (stamp) line = `${base} · ${stamp}`;
    }
    out[m.model_id] = line;
  }
  return out;
}

/** Same ordering as backend available-for-prediction (newest publish first). */
export function sortPredictionModelsForDisplay(items: PredictionModelListItem[]): PredictionModelListItem[] {
  return [...items].sort((a, b) => {
    const pa = parseOptionalEpochMs(a.published_at);
    const pb = parseOptionalEpochMs(b.published_at);
    if (pa != null && pb != null && pa !== pb) return pb - pa;
    if (pa != null && pb == null) return -1;
    if (pa == null && pb != null) return 1;
    const ra = parseOptionalEpochMs(a.registered_at ?? a.released_at);
    const rb = parseOptionalEpochMs(b.registered_at ?? b.released_at);
    if (ra != null && rb != null && ra !== rb) return rb - ra;
    if (ra != null && rb == null) return -1;
    if (ra == null && rb != null) return 1;
    const da = pickPredictionDisplayName(a).toLowerCase();
    const db = pickPredictionDisplayName(b).toLowerCase();
    const c = da.localeCompare(db);
    if (c !== 0) return c;
    return String(a.model_id).localeCompare(String(b.model_id));
  });
}

/**
 * Dropdown label for prediction / batch / recommendation model pickers (single model, no collision suffix).
 */
export function formatPredictionModelOptionLabel(model: PredictionModelListItem, t?: Translate): string {
  return buildPredictionModelOptionBaseLabel(model, t);
}

function formatMetricScalar(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "number" && Number.isFinite(v)) {
    const a = Math.abs(v);
    if (a === 0) return "0";
    if (a >= 1e6 || a < 1e-4) return v.toExponential(3);
    return String(Number(v.toFixed(4)));
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

export function pickSourceJobId(m: ModelRecord | null | undefined): string | undefined {
  if (!m) return undefined;
  const direct = ["source_job_id", "source_task_id", "training_job_id", "job_id"] as const;
  for (const k of direct) {
    const v = m[k];
    if (v != null && String(v).trim() !== "") return String(v);
  }
  const meta = m.metadata;
  if (meta && typeof meta === "object") {
    const mid = (meta as ModelRecord).training_job_id ?? (meta as ModelRecord).source_job_id;
    if (mid != null && String(mid).trim() !== "") return String(mid);
  }
  return undefined;
}

export type ModelStatusTags = {
  /** Model selected in the current session. */
  isCurrent: boolean;
  /** Published / unpublished / unknown. */
  publish: string;
};

export function buildModelStatusTags(
  m: ModelRecord,
  currentModelId: string | null | undefined,
  t?: Translate,
): ModelStatusTags {
  const isCurrent = Boolean(currentModelId && String(m.model_id || "") === String(currentModelId));
  const pub = m.is_published;
  let publish = loc(t, "models.presentation.publishState.unknown", {}, "Publish status unknown");
  if (pub === true) publish = loc(t, "models.presentation.publishState.published", {}, "Published");
  else if (pub === false) publish = loc(t, "models.presentation.publishState.unpublished", {}, "Not published");
  const st = m.status;
  if (typeof st === "string" && st && pub == null) {
    const low = st.toLowerCase();
    publish =
      low === "published"
        ? loc(t, "models.presentation.publishState.published", {}, "Published")
        : low === "draft"
          ? loc(t, "models.presentation.publishState.draft", {}, "Draft")
          : low === "archived"
            ? loc(t, "models.presentation.publishState.archived", {}, "Archived")
            : String(st);
  }
  return { isCurrent, publish };
}

export function featureSummaryFromModel(m: ModelRecord | null | undefined): string {
  if (!m) return "";
  const direct = summarizeFeatureSources({
    feature_set: m.feature_set,
    final_features: m.final_features,
    selected_features: m.selected_features,
  } as Record<string, unknown>);
  if (direct) return direct;
  const p = m.training_params;
  if (p && typeof p === "object") return summarizeFeatureSources(p as Record<string, unknown>);
  return "";
}

export function formatMetricEntries(m: ModelRecord | null | undefined): Array<[string, string]> {
  if (!m) return [];
  const km = m.key_metrics;
  if (km && typeof km === "object" && !Array.isArray(km)) {
    return Object.entries(km as Record<string, unknown>).map(([k, v]) => [
      k,
      typeof v === "object" && v !== null ? JSON.stringify(v) : formatMetricScalar(v),
    ]);
  }
  return [];
}

/** Safe deep-copy serialization for the metadata snapshot detail section. */
export function safeModelJson(m: unknown): string {
  try {
    return JSON.stringify(m ?? {}, null, 2);
  } catch {
    return String(m);
  }
}
