import { sortPredictionModelsForDisplay } from "./utils/modelPresentation";
import type {
  ApiErrorPayload,
  BatchFieldCheckResponse,
  BatchPredictionRunResponse,
  ChatTurnData,
  DatasetMeta,
  DatasetPreviewInfo,
  DatasetSchemaInfo,
  ModelMeta,
  PredictionModelListItem,
  PredictionHistoryListItem,
  PredictionHistoryRecord,
  PredictionSchemaPayload,
  PredictionSingleResponse,
  RegimenRecord,
  RegimenTreatmentValues,
  SurvivalRecommendationResult,
  TaskDetailData,
  TaskStatusData,
} from "./types";

import { DEFAULT_APP_LOCALE, i18n } from "./i18n";

function activeUiLocaleForHeader(): string {
  const loc = i18n.global.locale as unknown;
  const v =
    typeof loc === "object" && loc !== null && "value" in loc
      ? String((loc as { value: string }).value).trim()
      : String(loc).trim();
  if (v) return v;
  return DEFAULT_APP_LOCALE;
}

/**
 * In development, default to Vite same-origin + proxy (see vite.config.ts) so GET/POST and /prediction/* forward consistently to the backend.
 * Production builds, or runs without the dev server, still connect directly to 8001 unless VITE_API_BASE_URL overrides it.
 */
export const API_BASE_URL =
  import.meta.env.DEV && import.meta.env.VITE_DIRECT_API !== "1"
    ? ""
    : (import.meta.env.VITE_API_BASE_URL as string | undefined) || "http://127.0.0.1:8001";

const BASE_URL = API_BASE_URL;

export class ApiError extends Error {
  code: string;
  constructor(message: string, code = "UNKNOWN_ERROR") {
    super(message);
    this.code = code;
  }
}

async function parseFetchResponse(res: Response): Promise<{ raw: string; parsed: unknown | null }> {
  const raw = await res.text();
  const contentType = (res.headers.get("content-type") || "").toLowerCase();
  const declaredJson = contentType.includes("application/json") || contentType.includes("+json");
  const looksLikeJson = /^[\s]*[{[]/.test(raw);

  if (!declaredJson && !looksLikeJson) {
    return { raw, parsed: null };
  }

  if (!raw.trim()) {
    return { raw, parsed: null };
  }

  try {
    return { raw, parsed: JSON.parse(raw) as unknown };
  } catch {
    return { raw, parsed: null };
  }
}

const CHAT_PENDING_SCOPE_SESSION_KEY = "clinical_agent_chat_session_v1";

/** Browser-session scope used to isolate anonymous users and backend pending_action records. */
export function getOrCreateChatSessionIdForScope(): string {
  if (typeof localStorage === "undefined") return "";
  let s = localStorage.getItem(CHAT_PENDING_SCOPE_SESSION_KEY);
  if (!s) {
    s = `cs_${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
    localStorage.setItem(CHAT_PENDING_SCOPE_SESSION_KEY, s);
  }
  return s;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const base = isFormData ? {} : { "Content-Type": "application/json" };
  const mergedHeaders: Record<string, string> = {
    ...base,
    ...(init?.headers as Record<string, string> | undefined),
    "X-UI-Locale": activeUiLocaleForHeader(),
  };
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: mergedHeaders,
  });

  const { raw, parsed } = await parseFetchResponse(res);

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    let code = "HTTP_ERROR";
    if (parsed !== null && typeof parsed === "object") {
      const err = parsed as Partial<ApiErrorPayload>;
      if (typeof err.message === "string" && err.message.trim()) message = err.message.trim();
      if (typeof err.error_code === "string" && err.error_code.trim()) code = err.error_code.trim();
    }
    throw new ApiError(message, code);
  }

  if (parsed === null || typeof parsed !== "object") {
    console.error("[api] Expected JSON envelope from", path, res.status, raw.slice(0, 500));
    throw new ApiError("Invalid response from server.", "INVALID_RESPONSE");
  }

  const envelope = parsed as { status?: string; data?: unknown; message?: string; error_code?: string };
  if (envelope.status === "error") {
    throw new ApiError(
      envelope.message?.trim() || `Request failed (${res.status})`,
      envelope.error_code?.trim() || "HTTP_ERROR",
    );
  }

  return envelope.data as T;
}

export async function postChatTurn(
  message: string,
  opts?: {
    clientCompletedParams?: Record<string, unknown>;
    chatContext?: Record<string, unknown>;
    userId?: string;
    sessionId?: string;
  },
): Promise<ChatTurnData> {
  const body: Record<string, unknown> = { message };
  if (opts?.userId) body.user_id = opts.userId;
  const sid = opts?.sessionId ?? getOrCreateChatSessionIdForScope();
  if (sid) body.session_id = sid;
  const ccp = opts?.clientCompletedParams;
  if (ccp && typeof ccp === "object" && Object.keys(ccp).length > 0) {
    body.client_completed_params = ccp;
  }
  const chatCtx = opts?.chatContext;
  if (chatCtx && typeof chatCtx === "object" && Object.keys(chatCtx).length > 0) {
    body.chat_context = chatCtx;
  }
  return request<ChatTurnData>("/chat/turn", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function postConfirm(
  pendingActionId: string,
  opts?: { completedParams?: Record<string, unknown>; locale?: string },
): Promise<{ job_id?: string; assistant_message: string; task?: Record<string, unknown> | null }> {
  const body: Record<string, unknown> = { pending_action_id: pendingActionId, confirmed: true };
  if (opts?.completedParams && Object.keys(opts.completedParams).length > 0) {
    body.completed_params = opts.completedParams;
  }
  const loc = opts?.locale != null ? String(opts.locale).trim() : "";
  if (loc) body.locale = loc;
  return request<{ job_id?: string; assistant_message: string; task?: Record<string, unknown> | null }>(
    "/actions/confirm",
    {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getTasks(): Promise<{ items: Array<Record<string, unknown>>; total: number }> {
  return request<{ items: Array<Record<string, unknown>>; total: number }>("/tasks");
}

export async function getTaskStatus(jobId: string): Promise<TaskStatusData> {
  return request<TaskStatusData>(`/tasks/${jobId}/status`);
}

export async function getTaskDetail(jobId: string): Promise<TaskDetailData> {
  return request<TaskDetailData>(`/tasks/${jobId}`);
}

export async function postTrainingWorkflow(
  jobId: string,
  body: Record<string, unknown>,
): Promise<{ message?: string; job_id?: string }> {
  return request<{ message?: string; job_id?: string }>(`/tasks/${jobId}/training/workflow`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteTask(jobId: string): Promise<{ message?: string; job_id?: string }> {
  return request<{ message?: string; job_id?: string }>(`/tasks/${jobId}`, {
    method: "DELETE",
  });
}

export async function cancelTask(jobId: string): Promise<{ message?: string; job_id?: string }> {
  return request<{ message?: string; job_id?: string }>(`/tasks/${jobId}/cancel`, {
    method: "POST",
  });
}

export async function getDatasets(): Promise<{ items: DatasetMeta[]; total: number }> {
  return request<{ items: DatasetMeta[]; total: number }>("/datasets");
}

export async function uploadDataset(
  file: File,
  opts?: { availableTasks?: string[] },
): Promise<{ dataset: DatasetMeta }> {
  const form = new FormData();
  form.append("file", file);
  if (opts?.availableTasks?.length) {
    form.append("available_tasks", JSON.stringify(opts.availableTasks));
  }
  return request<{ dataset: DatasetMeta }>("/datasets/upload", {
    method: "POST",
    body: form,
  });
}

export async function deleteDataset(datasetId: string): Promise<{ message?: string; dataset_id: string }> {
  return request<{ message?: string; dataset_id: string }>(`/datasets/${encodeURIComponent(datasetId)}`, {
    method: "DELETE",
  });
}

/** Direct file URL for browser download (not JSON envelope). */
export function getDatasetFileDownloadUrl(datasetId: string): string {
  return `${BASE_URL}/datasets/${encodeURIComponent(datasetId)}/file`;
}

export type ModelPatchPayload = {
  task_name?: string | null;
  notes?: string | null;
  is_published?: boolean | null;
};

export async function patchModel(modelId: string, body: ModelPatchPayload): Promise<{ model: ModelMeta }> {
  return request<{ model: ModelMeta }>(`/models/${encodeURIComponent(modelId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteModel(modelId: string): Promise<{ message?: string; model_id: string }> {
  return request<{ message?: string; model_id: string }>(`/models/${encodeURIComponent(modelId)}`, {
    method: "DELETE",
  });
}

export async function getDatasetSchema(datasetId: string): Promise<{ schema: DatasetSchemaInfo }> {
  return request<{ schema: DatasetSchemaInfo }>(`/datasets/${encodeURIComponent(datasetId)}/schema`);
}

export async function getDatasetPreview(
  datasetId: string,
  opts?: { targetColumn?: string; limit?: number; columns?: string[] },
): Promise<{ preview: DatasetPreviewInfo }> {
  const qs = new URLSearchParams();
  if (opts?.targetColumn) qs.set("target_column", opts.targetColumn);
  if (typeof opts?.limit === "number") qs.set("limit", String(opts.limit));
  if (opts?.columns?.length) qs.set("columns", opts.columns.join(","));
  const query = qs.toString();
  return request<{ preview: DatasetPreviewInfo }>(
    `/datasets/${encodeURIComponent(datasetId)}/preview${query ? `?${query}` : ""}`,
  );
}

export async function getModels(taskType?: string): Promise<{ items: ModelMeta[]; total: number }> {
  const query = taskType ? `?task_type=${encodeURIComponent(taskType)}` : "";
  return request<{ items: ModelMeta[]; total: number }>(`/models${query}`);
}

export async function getModelDetail(modelId: string): Promise<{ model: ModelMeta }> {
  return request<{ model: ModelMeta }>(`/models/${encodeURIComponent(modelId)}`);
}

export async function getPredictionModels(): Promise<{ items: PredictionModelListItem[]; total: number }> {
  const data = await request<{ items: PredictionModelListItem[]; total: number }>("/prediction/models");
  return { ...data, items: sortPredictionModelsForDisplay(data.items) };
}

/** Canonical released models for prediction (same registry as GET /models); optional canonical task filter. */
export async function getAvailablePredictionModels(
  canonicalTaskKey?: string,
): Promise<{ items: PredictionModelListItem[]; total: number; invalid_task?: boolean }> {
  const q =
    canonicalTaskKey != null && String(canonicalTaskKey).trim()
      ? `?task=${encodeURIComponent(String(canonicalTaskKey).trim())}`
      : "";
  const data = await request<{ items: PredictionModelListItem[]; total: number; invalid_task?: boolean }>(
    `/models/available-for-prediction${q}`,
  );
  return { ...data, items: sortPredictionModelsForDisplay(data.items) };
}

export async function getPredictionModelSchema(modelId: string): Promise<PredictionSchemaPayload> {
  return request<PredictionSchemaPayload>(`/prediction/models/${encodeURIComponent(modelId)}/schema`);
}

export async function postPredictionSingle(body: {
  model_id: string;
  values: Record<string, unknown>;
  session_id?: string;
  locale?: string;
}): Promise<PredictionSingleResponse> {
  return request<PredictionSingleResponse>("/prediction/single", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function postPredictionBatchCheck(body: {
  model_id: string;
  file: File;
  locale?: string;
}): Promise<BatchFieldCheckResponse> {
  const form = new FormData();
  form.append("model_id", body.model_id);
  form.append("file", body.file);
  const loc = body.locale != null ? String(body.locale).trim() : "";
  if (loc) form.append("locale", loc);
  return request<BatchFieldCheckResponse>("/prediction/batch/check", {
    method: "POST",
    body: form,
  });
}

export async function postPredictionBatchRun(body: {
  model_id: string;
  file: File;
  session_id?: string;
  locale?: string;
}): Promise<BatchPredictionRunResponse> {
  const form = new FormData();
  form.append("model_id", body.model_id);
  form.append("file", body.file);
  if (body.session_id) form.append("session_id", body.session_id);
  const loc = body.locale != null ? String(body.locale).trim() : "";
  if (loc) form.append("locale", loc);
  return request<BatchPredictionRunResponse>("/prediction/batch/run", {
    method: "POST",
    body: form,
  });
}

export async function getPredictionHistory(opts?: {
  type?: "single" | "batch";
  task?: string;
  model?: string;
}): Promise<{ items: PredictionHistoryListItem[]; total: number }> {
  const qs = new URLSearchParams();
  if (opts?.type) qs.set("type", opts.type);
  if (opts?.task) qs.set("task", opts.task);
  if (opts?.model) qs.set("model", opts.model);
  const q = qs.toString();
  return request<{ items: PredictionHistoryListItem[]; total: number }>(`/prediction/history${q ? `?${q}` : ""}`);
}

export async function getPredictionHistoryDetail(recordId: string): Promise<PredictionHistoryRecord> {
  return request<PredictionHistoryRecord>(`/prediction/history/${encodeURIComponent(recordId)}`);
}

export type RegimenWritePayload = {
  regimen_name: string;
  enabled: boolean;
  notes: string | null;
  treatment_values: RegimenTreatmentValues;
};

export async function listRegimens(): Promise<{ items: RegimenRecord[]; total: number }> {
  return request<{ items: RegimenRecord[]; total: number }>("/recommendation/regimens");
}

export async function createRegimen(body: RegimenWritePayload): Promise<{ regimen: RegimenRecord }> {
  return request<{ regimen: RegimenRecord }>("/recommendation/regimens", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateRegimen(
  regimenId: string,
  body: RegimenWritePayload,
): Promise<{ regimen: RegimenRecord }> {
  return request<{ regimen: RegimenRecord }>(`/recommendation/regimens/${encodeURIComponent(regimenId)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteRegimen(
  regimenId: string,
): Promise<{ message?: string; regimen_id: string }> {
  return request<{ message?: string; regimen_id: string }>(
    `/recommendation/regimens/${encodeURIComponent(regimenId)}`,
    { method: "DELETE" },
  );
}

export type RecommendationJobCreatePayload = {
  model_id: string;
  patient_features: Record<string, unknown>;
  observed_regimen?: RegimenTreatmentValues;
  regimen_ids?: string[];
  top_k?: number;
  mode: "survival_only";
  locale?: string;
};

export async function postRecommendationJob(
  body: RecommendationJobCreatePayload,
): Promise<{ job_id: string; job: Record<string, unknown> }> {
  return request<{ job_id: string; job: Record<string, unknown> }>("/recommendation/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Fetch recommendation.json from task detail artifacts without the shared request wrapper. */
export async function fetchRecommendationArtifactJson(
  url: string,
): Promise<SurvivalRecommendationResult | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as SurvivalRecommendationResult;
  } catch {
    return null;
  }
}

