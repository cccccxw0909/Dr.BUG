import type { PredictionSchemaPayload, RecommendationWorkflowCardData } from "../types";
import type { Translate } from "./messageSanitizer";
import { getPredictionFormExecuteBlockers } from "./predictionFormValidation";
import { recommendationPatientFieldCoverageStats } from "./recommendationCoverageCheck";
import { filterNonTreatmentPatientFields } from "./recommendationPatientFeatures";

function loc(t: Translate | undefined, key: string, values: Record<string, unknown>, enFallback: string): string {
  return t ? t(key, values) : enFallback;
}

export function getRecommendationWorkflowBlockers(card: RecommendationWorkflowCardData, t?: Translate): string | null {
  if (card.regimensLoading)
    return loc(
      t,
      "chat.recommendationWorkflow.validation.regimensLoading",
      {},
      "Checking the regimen library—please wait.",
    );
  if (card.enabledRegimenCount < 1) {
    return loc(
      t,
      "chat.recommendationWorkflow.validation.noEnabledRegimens",
      {},
      "No enabled candidate regimens in the library. Open Datasets → Regimen management to add and enable at least one regimen.",
    );
  }
  if (!card.schema) {
    return getPredictionFormExecuteBlockers(
      {
        selectedModelId: card.selectedModelId,
        schema: null,
        formValues: {},
      },
      t,
    );
  }
  const patientFields = filterNonTreatmentPatientFields(card.schema.fields);
  if (patientFields.length === 0) {
    return loc(
      t,
      "chat.recommendationWorkflow.validation.noNonTreatmentPatientFields",
      {},
      "This model's feature table has no non-treatment patient fields (it may only include therapy-related columns). Use a survival model that includes clinical/laboratory non-treatment features.",
    );
  }
  const patientSchema: PredictionSchemaPayload = {
    ...card.schema,
    fields: patientFields,
  };
  const basic = getPredictionFormExecuteBlockers(
    {
      selectedModelId: card.selectedModelId,
      schema: patientSchema,
      formValues: card.formValues,
    },
    t,
  );
  if (basic) return basic;

  const cov = recommendationPatientFieldCoverageStats(card.schema, card.formValues);
  if (!cov.ok) {
    return loc(
      t,
      "chat.recommendationWorkflow.validation.tooFewFeaturesCompleted",
      { filled: cov.filled, total: cov.total },
      `Too few patient features have been completed (${cov.filled}/${cov.total}). Please complete most required fields before running the recommendation.`,
    );
  }
  return null;
}
