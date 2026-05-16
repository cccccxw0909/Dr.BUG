import type { PredictionFieldSchema, PredictionSchemaPayload } from "../types";
import { REGIMEN_TREATMENT_FIELD_KEYS } from "../types";

const TREATMENT_NAME_SET = new Set<string>(REGIMEN_TREATMENT_FIELD_KEYS as unknown as string[]);

/** Matches backend regimen treatment field names; the main recommendation form hides these fields because treatment values come from the regimen library. */
export function isRegimenTreatmentFieldName(name: string): boolean {
  return TREATMENT_NAME_SET.has(name);
}

export function filterNonTreatmentPatientFields(fields: PredictionFieldSchema[]): PredictionFieldSchema[] {
  return fields.filter((f) => !isRegimenTreatmentFieldName(f.name));
}

/** Submit only non-treatment patient features to prevent treatment keys lingering in the schema from entering patient_features. */
export function buildPatientFeaturesPayload(
  schema: PredictionSchemaPayload,
  formValues: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of filterNonTreatmentPatientFields(schema.fields)) {
    if (Object.prototype.hasOwnProperty.call(formValues, f.name)) {
      out[f.name] = formValues[f.name];
    }
  }
  return out;
}
