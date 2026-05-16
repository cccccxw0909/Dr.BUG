import type { PredictionModelListItem, PredictionTaskKey } from "../types";
import {
  RE_DURATION_DOMAIN,
  RE_EFFICACY_DOMAIN,
  RE_PANEL_BATCH_HINT,
  RE_PANEL_SINGLE_PATIENT_HINT,
  RE_RESISTANCE_DOMAIN,
  RE_SURVIVAL_DOMAIN,
} from "../i18n/lexicons/zhPredictionTaskInference";

/** Chinese/English keyword patterns in this file match clinician chat input, not UI strings. */

export const PREDICTION_TASK_KEYS_ORDER: readonly PredictionTaskKey[] = [
  "survival",
  "efficacy",
  "resistance",
  "duration",
] as const;

const CLINICAL_TASK_ID_TO_KEY: Record<string, PredictionTaskKey> = {
  mortality_28d: "survival",
  clinical_efficacy: "efficacy",
  polymyxin_resistance: "resistance",
  treatment_duration: "duration",
};

export function isPredictionModelPublished(m: PredictionModelListItem): boolean {
  return m.is_published !== false;
}

/** Maps UI task keys (survival, efficacy, …) to backend canonical task keys. */
export function canonicalApiTaskFromUiKey(k: PredictionTaskKey): string {
  const m: Record<PredictionTaskKey, string> = {
    survival: "survival_outcome",
    efficacy: "clinical_efficacy",
    resistance: "polymyxin_resistance",
    duration: "treatment_duration",
  };
  return m[k];
}

/** Inverse of canonicalApiTaskFromUiKey for API-driven task_key field. */
export function uiTaskKeyFromCanonicalApi(ck: string | undefined | null): PredictionTaskKey | null {
  if (!ck || !String(ck).trim()) return null;
  const m: Record<string, PredictionTaskKey> = {
    survival_outcome: "survival",
    clinical_efficacy: "efficacy",
    polymyxin_resistance: "resistance",
    treatment_duration: "duration",
  };
  return m[String(ck).trim()] ?? null;
}

export function inferPredictionTaskKeyFromModel(m: PredictionModelListItem): PredictionTaskKey | null {
  const fromApi = uiTaskKeyFromCanonicalApi(m.task_key);
  if (fromApi) return fromApi;

  const meta =
    m.metadata && typeof m.metadata === "object" ? (m.metadata as Record<string, unknown>) : undefined;
  const ct = String(m.clinical_task_id ?? meta?.clinical_task_id ?? "").trim();
  if (ct && CLINICAL_TASK_ID_TO_KEY[ct]) return CLINICAL_TASK_ID_TO_KEY[ct];

  const hay = [m.model_id, m.task_name, m.display_name].join(" ").toLowerCase();

  if (/polymyxin|resistan|mic\b|suscept/.test(hay)) return "resistance";
  if (/treatment_duration|duration|therapy_days|days_of_treatment/.test(hay)) {
    return "duration";
  }
  if (/mortality|survival|28d|28-day|prognosis/.test(hay)) return "survival";
  if (/efficacy|clinical_outcome|clinical outcome|improvement/.test(hay)) return "efficacy";

  return null;
}

export function predictionModelsForTask(
  items: PredictionModelListItem[],
  taskKey: PredictionTaskKey | null,
): PredictionModelListItem[] {
  if (taskKey == null) return [];
  const canon = canonicalApiTaskFromUiKey(taskKey);
  return items.filter((m) => {
    if (!isPredictionModelPublished(m)) return false;
    if (m.task_key && String(m.task_key).trim()) return String(m.task_key).trim() === canon;
    return inferPredictionTaskKeyFromModel(m) === taskKey;
  });
}

type KeywordRule = { key: PredictionTaskKey; patterns: RegExp[] };

const PREDICTION_TASK_KEYWORD_RULES: KeywordRule[] = [
  {
    key: "survival",
    patterns: [
      /\b28[-\s]?day\s+(survival|mortality)\b/i,
      /\b(28-day\s+survival|28-day\s+mortality)\b/i,
      /\b(survival|mortality|death|prognosis)\b/i,
      RE_SURVIVAL_DOMAIN,
    ],
  },
  {
    key: "efficacy",
    patterns: [
      /\bclinical\s+efficacy\b/i,
      /\b(treatment\s+efficacy|treatment\s+response)\b/i,
      /\b(improvement|efficacy)\b/i,
      RE_EFFICACY_DOMAIN,
    ],
  },
  {
    key: "resistance",
    patterns: [
      /\bpolymyxin\s+resistance\b/i,
      /\b(susceptibility|susceptible)\b/i,
      /\bresistance\b/i,
      /\bmic\b/i,
      RE_RESISTANCE_DOMAIN,
    ],
  },
  {
    key: "duration",
    patterns: [
      /\b(treatment\s+duration|antibiotic\s+duration|duration\s+of\s+therapy|days\s+of\s+treatment)\b/i,
      RE_DURATION_DOMAIN,
    ],
  },
];

/**
 * Single-patient vs batch panel: batch keywords win only when unambiguous (otherwise default single-patient).
 */
export function inferPredictionPanelModeFromUserText(raw: string): "form" | "batch" {
  const text = String(raw || "");
  const batch = RE_PANEL_BATCH_HINT.test(text);
  const single = RE_PANEL_SINGLE_PATIENT_HINT.test(text);
  if (batch && !single) return "batch";
  if (single && !batch) return "form";
  return "form";
}

/**
 * Infer preferred prediction task from the user's message (mirrors training normalizers / keyword style).
 * Returns null when ambiguous or no match — caller should show "Please select".
 */
export function inferPreferredPredictionTaskFromUserText(raw: string, _localeHint?: string): PredictionTaskKey | null {
  const text = String(raw || "").trim();
  if (!text) return null;

  const matched = new Set<PredictionTaskKey>();
  for (const rule of PREDICTION_TASK_KEYWORD_RULES) {
    for (const re of rule.patterns) {
      re.lastIndex = 0;
      if (re.test(text)) {
        matched.add(rule.key);
        break;
      }
    }
  }
  if (matched.size !== 1) return null;
  return [...matched][0]!;
}
