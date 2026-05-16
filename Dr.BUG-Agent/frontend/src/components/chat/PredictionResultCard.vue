<template>
  <div class="prc-root prc-report">
    <section class="prc-result-block" :aria-label="t('prediction.explanation.predictionResultAriaLabel')">
      <div class="prc-report-shell">
        <p class="prc-report-paragraph">
          <template v-if="isRegression">
            <I18nT v-if="hasProbability" keypath="prediction.explanation.reportSummary.regressionLeadProb" tag="span">
              <template #lead>
                <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
              </template>
              <template #conclusion>
                <strong>{{ surface.conclusionPrimary }}</strong>
              </template>
              <template #probability>
                <strong>{{ probabilityPercentStr }}</strong>
              </template>
            </I18nT>
            <I18nT v-else keypath="prediction.explanation.reportSummary.regressionLeadNoProb" tag="span">
              <template #lead>
                <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
              </template>
              <template #conclusion>
                <strong>{{ surface.conclusionPrimary }}</strong>
              </template>
            </I18nT>
          </template>
          <template v-else>
            <I18nT v-if="hasProbability" keypath="prediction.explanation.reportSummary.classificationLeadProb" tag="span">
              <template #lead>
                <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
              </template>
              <template #label>
                <strong>{{ surface.conclusionPrimary }}</strong>
              </template>
              <template #probability>
                <strong>{{ probabilityPercentStr }}</strong>
              </template>
            </I18nT>
            <I18nT v-else keypath="prediction.explanation.reportSummary.classificationLeadNoProb" tag="span">
              <template #lead>
                <strong>{{ t("prediction.explanation.reportSummary.predictionCompletedSentence") }}</strong>
              </template>
              <template #label>
                <strong>{{ surface.conclusionPrimary }}</strong>
              </template>
            </I18nT>
          </template>
          <template v-if="mainContributingVariablesLine">
            {{ " " }}
            <span>{{ t("prediction.explanation.reportSummary.varsClause", { variables: mainContributingVariablesLine }) }}</span>
          </template>
          <template v-if="showWaterfallTail">
            {{ " " }}
            <span>{{ t("prediction.explanation.reportSummary.waterfallTail") }}</span>
          </template>
        </p>
      </div>
    </section>

    <details v-if="variablesHandledBlocks.length" open class="prc-fold prc-zone">
      <summary class="prc-fold-sum">{{ t("prediction.explanation.variablesHandledByPreprocessing") }}</summary>
      <div class="prc-body-stack">
        <p v-for="(block, i) in variablesHandledBlocks" :key="i" class="prc-body-text">{{ block }}</p>
      </div>
    </details>

    <template v-if="effectiveEx != null">
      <template v-if="effectiveEx.supported">
        <div class="prc-waterfall-zone">
          <div v-if="explainWarnFormatted.length" class="prc-chart-pipeline-notes">
            <p v-for="(w, i) in explainWarnFormatted" :key="i" class="prc-note-secondary">{{ w }}</p>
          </div>

          <div v-if="effectiveEx.waterfall_image_url" class="prc-fig-block">
            <div class="prc-fig-frame">
              <img
                :src="effectiveEx.waterfall_image_url"
                :alt="t('prediction.explanation.waterfallAlt')"
                class="prc-shap-img"
                loading="lazy"
                @click="lightboxUrl = effectiveEx!.waterfall_image_url"
              />
            </div>
          </div>
          <div v-else class="prc-shap-empty">
            {{ t("prediction.explanation.noChartsHint") }}
          </div>
        </div>
      </template>

      <details v-else open class="prc-fold prc-zone">
        <summary class="prc-fold-sum">{{ t("prediction.explanation.individualExplanation") }}</summary>
        <div class="prc-body-stack">
          <template v-if="unsupportedLinesFormatted.length">
            <p v-for="(line, i) in unsupportedLinesFormatted" :key="i" class="prc-body-text">{{ line }}</p>
          </template>
          <p v-else class="prc-body-text">{{ t("prediction.explanation.singleExplanationNotReady") }}</p>
        </div>
      </details>
    </template>

    <details v-else open class="prc-fold prc-zone">
      <summary class="prc-fold-sum">{{ t("prediction.explanation.individualExplanation") }}</summary>
      <p class="prc-body-text">{{ t("prediction.explanation.noExtraExplanation") }}</p>
    </details>

    <div v-if="lightboxUrl" class="prediction-lightbox-mask" @click="lightboxUrl = null">
      <img :src="lightboxUrl" :alt="t('prediction.explanation.lightboxAlt')" class="prediction-lightbox-image" @click.stop />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { I18nT, useI18n } from "vue-i18n";

import type { PredictionExplanationBlock, PredictionFieldSchema, PredictionSingleResponse } from "../../types";

import { formatClinicalPredictionSurface } from "../../utils/predictionPresentation";
import {
  featureLabelForPreprocessingNote,
  formatPredictionDataPreprocessingNotes,
  joinVariableLabels,
} from "../../utils/predictionPreprocessingNotes";

const props = defineProps<{ data: PredictionSingleResponse }>();

const { t, locale } = useI18n();

const lightboxUrl = ref<string | null>(null);

const surface = computed(() => formatClinicalPredictionSurface(props.data, t));

const isRegression = computed(() => props.data.prediction_type === "regression");

const hasProbability = computed(() => {
  const p = props.data.predicted_probability;
  return p != null && !Number.isNaN(Number(p));
});

const probabilityPercentStr = computed(() => {
  const p = props.data.predicted_probability;
  if (p == null || Number.isNaN(Number(p))) return "";
  return `${(Number(p) * 100).toFixed(2)}%`;
});

const effectiveEx = computed<PredictionExplanationBlock | null>(() => {
  const d = props.data;
  if (d.explanation != null) return d.explanation;

  const hasWhitelist =
    d.explanation_supported != null ||
    d.shap_supported != null ||
    !!(d.waterfall_plot_url || d.force_plot_url) ||
    (d.top_positive_drivers && d.top_positive_drivers.length > 0) ||
    (d.top_negative_drivers && d.top_negative_drivers.length > 0);

  if (!hasWhitelist) return null;

  const top_features: Array<{ name: string; direction: "increase" | "decrease" }> = [];
  for (const x of d.top_positive_drivers || []) {
    const n = typeof x === "string" ? x : x?.name;
    if (n) top_features.push({ name: String(n), direction: "increase" });
  }
  for (const x of d.top_negative_drivers || []) {
    const n = typeof x === "string" ? x : x?.name;
    if (n) top_features.push({ name: String(n), direction: "decrease" });
  }

  return {
    supported: Boolean(d.explanation_supported ?? d.shap_supported),
    summary_text: "",
    top_features,
    waterfall_image_url: d.waterfall_plot_url ?? null,
    force_image_url: d.force_plot_url ?? null,
    warnings: [],
  };
});

const schemaFieldsForPresentation = computed((): PredictionFieldSchema[] => {
  const attached = props.data.feature_schema_fields;
  if (attached?.length) return attached;

  const names = new Set<string>();
  const used = props.data.feature_values_used || {};
  for (const k of Object.keys(used)) names.add(k);
  for (const x of effectiveEx.value?.top_features || []) {
    if (x?.name) names.add(String(x.name));
  }
  return [...names].map((name) => ({ name, label: "", type: "string", required: false }));
});

const noteOpts = computed(() => ({
  locale: String(locale.value || ""),
  t,
  schemaFields: schemaFieldsForPresentation.value,
}));

const variablesHandledBlocks = computed(() => formatPredictionDataPreprocessingNotes(props.data.warnings, noteOpts.value));

const locStr = computed(() => String(locale.value || ""));

const mainContributingVariablesLine = computed(() => {
  const tf = effectiveEx.value?.top_features;
  if (!tf?.length) return "";
  const names = tf.slice(0, 6).map((x) => x.name);
  const labels = names.map((n) => featureLabelForPreprocessingNote(n, schemaFieldsForPresentation.value, locStr.value));
  return joinVariableLabels(labels, locStr.value);
});

const showWaterfallTail = computed(
  () => Boolean(effectiveEx.value?.supported && effectiveEx.value?.waterfall_image_url),
);

const explainWarn = computed(() => {
  const ex = effectiveEx.value;
  const w = ex?.warnings;
  if (!w?.length) return [];
  return ex?.supported ? w : [];
});

const explainWarnFormatted = computed(() => formatPredictionDataPreprocessingNotes(explainWarn.value, noteOpts.value));

const unsupportedLines = computed(() => {
  const ex = effectiveEx.value;
  if (!ex || ex.supported) return [];
  return ex.warnings?.length ? ex.warnings : [];
});

const unsupportedLinesFormatted = computed(() =>
  formatPredictionDataPreprocessingNotes(unsupportedLines.value, noteOpts.value),
);
</script>

<style scoped>
.prc-root.prc-report {
  --prc-title-size: 16px;
  --prc-body-size: 15px;
  --prc-note-size: 14px;
  --prc-section-title-color: #263238;
  --prc-zone-rule: 1px solid #e8ebef;
  max-width: 100%;
  box-sizing: border-box;
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  overflow: visible;
}

.prc-result-block {
  margin-bottom: var(--wb-space-2);
}

.prc-report-shell {
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
}

.prc-report-paragraph {
  margin: 0;
  font-size: var(--wb-font-size-chat-body);
  font-weight: 400;
  line-height: var(--wb-line-height-prose);
  color: var(--wb-text-primary);
  word-break: break-word;
}

.prc-waterfall-zone {
  margin-top: var(--wb-space-3);
}

.prc-fold-sum {
  font-size: var(--prc-title-size);
  font-weight: 700;
  color: var(--prc-section-title-color);
  cursor: pointer;
  user-select: none;
  list-style: none;
}
.prc-fold-sum::-webkit-details-marker {
  display: none;
}

/** Light report sections: divider + spacing only (no nested cards). */
.prc-zone {
  margin: 0;
  padding: var(--wb-space-2) 0;
  border: none;
  border-radius: 0;
  background: transparent;
  border-top: var(--prc-zone-rule);
}

.prc-body-stack {
  margin-top: var(--wb-space-1);
}
.prc-body-text {
  margin: 0 0 var(--wb-space-1);
  font-size: var(--prc-body-size);
  font-weight: 400;
  line-height: 1.55;
  color: var(--wb-text-primary);
}
.prc-body-text:last-child {
  margin-bottom: 0;
}

.prc-chart-pipeline-notes {
  margin-bottom: var(--wb-space-2);
}
.prc-note-secondary {
  margin: 0 0 var(--wb-space-micro);
  font-size: var(--prc-note-size);
  font-weight: 400;
  color: #6d5c00;
  line-height: 1.45;
}
.prc-note-secondary:last-child {
  margin-bottom: 0;
}

.prc-shap-images {
  display: flex;
  flex-direction: column;
  gap: var(--wb-space-2);
}
.prc-fig-block {
  margin-top: 0;
}
.prc-fig-frame {
  overflow: auto;
  max-height: min(260px, 46vh);
  border-radius: var(--wb-radius-xs);
  border: 1px solid var(--wb-border-strong);
  background: #fff;
}
.prc-shap-img {
  display: block;
  max-width: 100%;
  width: auto;
  height: auto;
  max-height: min(248px, 44vh);
  object-fit: contain;
  cursor: zoom-in;
  margin: 0 auto;
}
.prc-shap-empty {
  font-size: var(--prc-body-size);
  color: #57606a;
  line-height: 1.5;
}

.prediction-lightbox-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.78);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--wb-space-3);
  box-sizing: border-box;
}
.prediction-lightbox-image {
  max-width: 96vw;
  max-height: 92vh;
  object-fit: contain;
  background: #fff;
  border-radius: var(--wb-space-micro);
}
</style>
