import type { PredictionSchemaPayload } from "../types";
import { filterNonTreatmentPatientFields, isRegimenTreatmentFieldName } from "./recommendationPatientFeatures";

function nonEmpty(v: unknown): boolean {
  if (v === null || v === undefined) return false;
  if (typeof v === "boolean") return true;
  if (typeof v === "number") {
    if (Number.isNaN(v)) return false;
    return true;
  }
  if (typeof v === "string") return v.trim() !== "";
  return true;
}

/**
 * Mirrors backend `backend/prediction/inference.py` coverage check for merged regimen comparison inputs:
 * treatment slots in feature_order count as filled (regimen supplies numeric values, including 0).
 */
export function regimenComparisonCoverageStats(
  schema: PredictionSchemaPayload,
  formValues: Record<string, unknown>,
): { filled: number; total: number; minRequired: number; ok: boolean } {
  const order =
    schema.feature_order?.length > 0
      ? schema.feature_order
      : schema.fields.map((f) => f.name).filter(Boolean);
  const total = order.length;
  let filled = 0;
  for (const name of order) {
    if (isRegimenTreatmentFieldName(name)) {
      filled += 1;
      continue;
    }
    if (nonEmpty(formValues[name])) filled += 1;
  }
  const minRequired = total >= 4 ? Math.max(3, Math.round(total * 0.5)) : 0;
  const ok = total < 4 || filled >= minRequired;
  return { filled, total, minRequired, ok };
}

/**
 * Coverage for the regimen recommendation patient form only (non-treatment fields shown in UI).
 * Must stay aligned with `analyzePredictionForm(patientFields, formValues)` filled/total used in meta lines.
 */
export function recommendationPatientFieldCoverageStats(
  schema: PredictionSchemaPayload,
  formValues: Record<string, unknown>,
): { filled: number; total: number; minRequired: number; ok: boolean } {
  const patientFields = filterNonTreatmentPatientFields(schema.fields);
  const total = patientFields.length;
  let filled = 0;
  for (const f of patientFields) {
    if (nonEmpty(formValues[f.name])) filled += 1;
  }
  const minRequired = total >= 4 ? Math.max(3, Math.round(total * 0.5)) : 0;
  const ok = total < 4 || filled >= minRequired;
  return { filled, total, minRequired, ok };
}
