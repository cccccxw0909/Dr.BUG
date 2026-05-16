import type { PredictionFieldSchema, PredictionSchemaPayload } from "../types";

import type { Translate } from "./messageSanitizer";
import { doctorFacingFeatureLabel } from "./featureDisplayName";

export type PredictionFormStats = {
  filledCount: number;
  missingRequiredCount: number;
  errorCount: number;
  fieldErrors: Record<string, string>;
};

function isEmptyValue(v: unknown): boolean {
  if (v === null || v === undefined) return true;
  if (typeof v === "string" && v.trim() === "") return true;
  return false;
}

function parseNumberLoose(raw: unknown): { ok: boolean; val: number | null } {
  if (raw === null || raw === undefined || raw === "") return { ok: true, val: null };
  if (typeof raw === "number" && !Number.isNaN(raw)) return { ok: true, val: raw };
  const s = String(raw).trim();
  if (!s) return { ok: true, val: null };
  const n = Number(s);
  if (Number.isNaN(n)) return { ok: false, val: null };
  return { ok: true, val: n };
}

function fieldDisplay(f: PredictionFieldSchema): string {
  return doctorFacingFeatureLabel(f);
}

function loc(
  t: Translate | undefined,
  key: string,
  values: Record<string, unknown>,
  enFallback: string,
): string {
  return t ? t(key, values) : enFallback;
}

/** Pass `t` from `useI18n()` for localized messages; omit only where callers are not migrated yet (English fallback). */
export function analyzePredictionForm(
  fields: PredictionFieldSchema[],
  formValues: Record<string, unknown>,
  t?: Translate,
): PredictionFormStats {
  const fieldErrors: Record<string, string> = {};
  let filledCount = 0;
  let missingRequiredCount = 0;

  for (const f of fields) {
    const raw = formValues[f.name];
    const empty = isEmptyValue(raw);
    const label = fieldDisplay(f);

    if (!empty) filledCount += 1;

    if (f.required && empty) {
      missingRequiredCount += 1;
      fieldErrors[f.name] = loc(
        t,
        "chat.predictionForm.validation.requiredFill",
        { label },
        `Please fill in ${label}.`,
      );
      continue;
    }

    if (empty) continue;

    if (f.type === "float" || f.type === "int") {
      const { ok, val } = parseNumberLoose(raw);
      if (!ok) {
        fieldErrors[f.name] = loc(
          t,
          "chat.predictionForm.validation.needValidNumber",
          { label },
          `"${label}" must be a valid number.`,
        );
        continue;
      }
      if (val === null) continue;
      if (f.type === "int" && !Number.isInteger(val)) {
        fieldErrors[f.name] = loc(
          t,
          "chat.predictionForm.validation.needInteger",
          { label },
          `"${label}" must be an integer.`,
        );
        continue;
      }
      if (f.min !== undefined && f.min !== null && val < Number(f.min)) {
        fieldErrors[f.name] = loc(
          t,
          "chat.predictionForm.validation.min",
          { label, min: f.min },
          `"${label}" must be at least ${f.min}.`,
        );
        continue;
      }
      if (f.max !== undefined && f.max !== null && val > Number(f.max)) {
        fieldErrors[f.name] = loc(
          t,
          "chat.predictionForm.validation.max",
          { label, max: f.max },
          `"${label}" must be at most ${f.max}.`,
        );
        continue;
      }
    }

    if (f.type === "categorical" || f.type === "binary") {
      const opts = f.options;
      if (Array.isArray(opts) && opts.length > 0) {
        const s = String(raw);
        const ok = opts.some((o) => String(o) === s);
        if (!ok)
          fieldErrors[f.name] = loc(
            t,
            "chat.predictionForm.validation.pickValidOption",
            { label },
            `"${label}": choose a valid option from the list.`,
          );
      }
    }
  }

  return {
    filledCount,
    missingRequiredCount,
    errorCount: Object.keys(fieldErrors).length,
    fieldErrors,
  };
}

export function buildInitialFormValues(fields: PredictionFieldSchema[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (f.default !== undefined && f.default !== null) {
      out[f.name] = f.default;
    } else if (f.type === "binary") {
      out[f.name] = null;
    } else {
      out[f.name] = "";
    }
  }
  return out;
}

/** Single-sample prediction: pre-flight checks when form and model are ready; `null` means OK to submit. */
export function getPredictionFormExecuteBlockers(
  st: {
    selectedPredictionTaskKey?: string | null;
    selectedModelId: string | null;
    schema: PredictionSchemaPayload | null;
    formValues: Record<string, unknown>;
    schemaLoading?: boolean;
  },
  t?: Translate,
): string | null {
  if ("selectedPredictionTaskKey" in st && !st.selectedPredictionTaskKey)
    return loc(
      t,
      "chat.predictionForm.validation.blockers.selectPredictionTask",
      {},
      "Choose a prediction task in the workspace first.",
    );
  if (!st.selectedModelId)
    return loc(
      t,
      "chat.predictionForm.validation.blockers.selectModel",
      {},
      "Select a prediction model in the workspace first.",
    );
  if (st.schemaLoading)
    return loc(
      t,
      "chat.predictionForm.validation.blockers.schemaLoading",
      {},
      "Loading fields for this model—please wait.",
    );
  if (!st.schema)
    return loc(
      t,
      "chat.predictionForm.validation.blockers.schemaMissing",
      {},
      "Could not load model fields. Check your connection, pick the model again, or try later.",
    );

  const a = analyzePredictionForm(st.schema.fields, st.formValues, t);
  if (a.missingRequiredCount > 0) {
    return loc(
      t,
      "chat.predictionForm.validation.blockers.missingRequiredCount",
      { count: a.missingRequiredCount },
      `${a.missingRequiredCount} required field(s) are still empty. Complete fields marked * before running.`,
    );
  }
  if (a.errorCount > 0) {
    const first = Object.entries(a.fieldErrors)[0];
    if (first) return `${first[1]}`;
    return loc(
      t,
      "chat.predictionForm.validation.blockers.genericFormatError",
      {},
      "Some fields still have invalid values—fix the hints under each field before running.",
    );
  }
  if (a.filledCount < 1)
    return loc(
      t,
      "chat.predictionForm.validation.blockers.fillAtLeastOne",
      {},
      "Enter at least one patient field before running prediction.",
    );
  return null;
}

/** @deprecated Bottom panel removed; use getPredictionFormExecuteBlockers */
export function getPredictionExecuteBlockers(
  st: {
    active: boolean;
    selectedModelId: string | null;
    schema: { fields: PredictionFieldSchema[] } | null;
    formValues: Record<string, unknown>;
  } | null | undefined,
  t?: Translate,
): string | null {
  if (!st?.active)
    return loc(
      t,
      "chat.predictionForm.validation.blockers.openWorkspaceFirst",
      {},
      'Send a message such as "predict" in chat to open the prediction workspace first.',
    );
  return getPredictionFormExecuteBlockers(
    {
      selectedModelId: st.selectedModelId,
      schema: st.schema as PredictionSchemaPayload | null,
      formValues: st.formValues,
    },
    t,
  );
}
