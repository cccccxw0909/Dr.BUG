/**
 * Helpers classify user-entered chat text (including Chinese commands).
 * Chinese trigger strings live in `i18n/lexicons/zhChatIntent.ts`, not in locale JSON.
 */

import {
  NEEDLES_RECOMMENDATION_RESULT_SUMMARY_ZH,
  RE_BATCH_PANEL_HINT,
  RE_BATCH_PREFIX,
  RE_OPEN_MEDICATION_RECOMMENDATION,
  RE_OPEN_REGIMEN_PLAN,
  RE_PREDICT_OUTCOME_WINDOW,
  RE_PREDICT_PATIENT,
  RE_SINGLE_SAMPLE_PREDICTION,
  TRAILING_CHAT_PUNCT_RE,
  ZH_BATCH_INFERENCE,
  ZH_BATCH_PREDICTION,
  ZH_DO_A_PREDICT,
  ZH_I_THINK_PREDICT,
  ZH_I_WANT_BATCH_PREDICTION,
  ZH_I_WANT_PREDICT,
  ZH_PREDICTION_CONFIG,
  ZH_PREDICTION_EXECUTE_PHRASES,
  ZH_PREDICTION_EXIT_PHRASES,
  ZH_PREDICTION_WORD,
  ZH_PREDICT_A_BIT,
  ZH_START_PREDICTION_EXACT,
  ZH_TRAINING,
} from "../i18n/lexicons/zhChatIntent";

export function isPredictionExitCommand(text: string): boolean {
  const trimmed = text.trim();
  return ZH_PREDICTION_EXIT_PHRASES.has(trimmed);
}

export function isPredictionExecuteCommand(text: string): boolean {
  const trimmed = text.trim();
  return ZH_PREDICTION_EXECUTE_PHRASES.has(trimmed);
}

export function isPredictionEnterCommand(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.includes(ZH_TRAINING)) return false;
  if (trimmed === ZH_PREDICTION_WORD || trimmed === ZH_I_WANT_PREDICT || trimmed.startsWith(ZH_I_WANT_PREDICT)) return true;
  if (trimmed === ZH_PREDICTION_CONFIG || trimmed.includes(ZH_I_THINK_PREDICT)) return true;
  if (trimmed.includes(ZH_DO_A_PREDICT) || trimmed.includes(ZH_PREDICT_A_BIT)) return true;
  if (RE_SINGLE_SAMPLE_PREDICTION.test(trimmed)) return true;
  if (/\/predict\b/i.test(trimmed)) return true;
  // Natural clinical prediction requests — open workspace without waiting for LLM routing.
  if (RE_PREDICT_PATIENT.test(trimmed)) return true;
  if (RE_PREDICT_OUTCOME_WINDOW.test(trimmed)) return true;
  if (/\b(predict|prediction)\b.{0,60}\b(patient|survival|mortality|efficacy|resistance|duration)\b/i.test(trimmed)) {
    return true;
  }
  return false;
}

export function isBatchPredictionEnterCommand(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.includes(ZH_TRAINING)) return false;
  return trimmed === ZH_BATCH_PREDICTION || trimmed === ZH_I_WANT_BATCH_PREDICTION || trimmed === ZH_BATCH_INFERENCE;
}

/** User text mentions training; prediction shortcuts must not intercept training-bound messages. */
export function includesTrainingKeyword(text: string): boolean {
  return text.includes(ZH_TRAINING);
}

/** Exact phrase used to open the prediction workspace when no editing card exists. */
export function isExactStartPredictionCommand(text: string): boolean {
  return text.trim() === ZH_START_PREDICTION_EXACT;
}

/**
 * When the chat route is deterministic draft_single_prediction, decide whether to open the batch panel
 * from legacy Chinese / batch-style user wording (same regex behavior as prior inline logic).
 */
export function draftSinglePredictionChatPreferOpenBatch(raw: string): boolean {
  return RE_BATCH_PANEL_HINT.test(raw) || RE_BATCH_PREFIX.test(raw.trim());
}

/** Same idea as backend `_message_seeks_completed_recommendation_result`: do not hijack result Q&A into the workspace card. */
function messageSeeksRecommendationResultSummary(text: string): boolean {
  const m = text.trim();
  if (!m || m.length > 240) return false;
  if (NEEDLES_RECOMMENDATION_RESULT_SUMMARY_ZH.some((x) => m.includes(x))) return true;
  const low = m.toLowerCase();
  const needlesEn = [
    "recommendation result",
    "result of the recommendation",
    "the recommendation outcome",
    "show me the recommendation",
    "show recommendation result",
    "what was recommended",
    "which regimen was recommended",
    "what regimen was recommended",
    "recommended regimen",
    "regimen recommendation result",
    "ranking of regimens",
    "ranked regimens",
    "top regimen",
    "what is the recommendation",
    "summary of the recommendation",
  ];
  return needlesEn.some((x) => low.includes(x));
}

const STRUCTURED_MODEL_ID_RE = /(model_[a-zA-Z0-9_]+|demo_binary_v1|survival_28d_v1)/i;

/**
 * True when the message likely carries a structured recommendation/create payload that should stay on the agent path.
 */
export function suppressesRecommendationWorkspaceOpen(text: string): boolean {
  const t = text.trim();
  if (!t) return true;
  if (messageSeeksRecommendationResultSummary(t)) return true;
  const compact = t.replace(/\s+/g, "").toLowerCase();
  if (compact.includes("patient_features")) return true;
  if (compact.includes("candidate_regimens")) return true;
  if (STRUCTURED_MODEL_ID_RE.test(t) && t.includes("{") && t.includes("}")) return true;
  return false;
}

function stripTrailingPunctuation(s: string): string {
  return s.replace(TRAILING_CHAT_PUNCT_RE, "").trim();
}

/**
 * Natural-language shortcuts to open the same Model-based regimen recommendation workspace as the workbench quick entry,
 * without posting a chat turn that would resolve to create_recommendation_job + AssistantActionCard.
 */
export function isRecommendationWorkspaceEnterCommand(text: string): boolean {
  const raw = text.trim();
  if (!raw || includesTrainingKeyword(raw)) return false;
  if (suppressesRecommendationWorkspaceOpen(raw)) return false;

  const zhNorm = raw.replace(/\s+/g, "");
  if (RE_OPEN_MEDICATION_RECOMMENDATION.test(zhNorm)) return true;
  if (RE_OPEN_REGIMEN_PLAN.test(zhNorm)) return true;

  const core = stripTrailingPunctuation(raw.replace(/\s+/g, " "));
  const low = core.toLowerCase();
  // Same canonical phrase as en-US `chat.syntheticUser.openRecommendationWorkspace` (users often type it verbatim).
  if (low === "open regimen recommendation" || low === "please open regimen recommendation") return true;
  if (low === "regimen recommendation") return true;
  if (low === "medication recommendation") return true;
  if (low === "recommend regimen" || low === "recommend a regimen") return true;
  if (low === "generate an individualized regimen recommendation") return true;

  return false;
}
