<template>
  <div class="workflow-card" :class="{ 'workflow-card--embedded': embedded }" data-testid="training-workflow-card">
    <div class="workflow-head">
      <div class="workflow-title">{{ workflowCardBusinessTitle(effectivePhase, i18nT) }}</div>
    </div>

    <div v-if="workflowNonPendingAlert" class="wf-nonpending-alert">
      {{ workflowNonPendingAlertText }}
    </div>

    <template v-if="effectivePhase === WF_PHASE3">
        <div class="wf-p3-summary-block">
          <p class="wf-p3-card-lead wf-p3-card-lead--conclusion">
            <I18nT keypath="chat.trainingWorkflow.phase3.summaryConclusionRich" tag="span">
              <template #featureBold>
                <strong>{{ phase3InputFeaturesBoldPhrase }}</strong>
              </template>
            </I18nT>
          </p>
          <p v-if="medCols.length" class="wf-p3-card-lead wf-p3-card-lead--tight">
            <I18nT keypath="chat.trainingWorkflow.phase3.summaryRequiredRich" tag="span">
              <template #requiredBold>
                <strong>{{ phase3RequiredTreatmentBoldPhrase }}</strong>
              </template>
              <template #list>{{ phase3RequiredLabelsJoined }}</template>
            </I18nT>
          </p>
          <p v-if="phase3SuggestedAdditionalColumns.length" class="wf-p3-card-lead wf-p3-card-lead--tight">
            <I18nT
              :keypath="
                phase3SuggestedAdditionalColumns.length === 1
                  ? 'chat.trainingWorkflow.phase3.summarySuggestedRichOne'
                  : 'chat.trainingWorkflow.phase3.summarySuggestedRichMany'
              "
              tag="span"
            >
              <template #suggestedBold>
                <strong>{{ phase3SuggestedVarsBoldPhrase }}</strong>
              </template>
              <template #list>{{ phase3SuggestedLabelsJoined }}</template>
            </I18nT>
          </p>
          <p v-if="phase3OtherPoolList.length === 1" class="wf-p3-card-lead wf-p3-card-lead--tight">
            <I18nT keypath="chat.trainingWorkflow.phase3.summaryOtherSingleRich" tag="span">
              <template #featureBold>
                <strong>{{ phase3OtherSingleBoldLabel }}</strong>
              </template>
            </I18nT>
          </p>
          <p v-else-if="phase3OtherPoolList.length > 1" class="wf-p3-card-lead wf-p3-card-lead--tight">
            <I18nT keypath="chat.trainingWorkflow.phase3.summaryOtherManyRich" tag="span">
              <template #list>{{ phase3OtherPoolLabelsJoined }}</template>
            </I18nT>
          </p>
        </div>

        <section class="wf-p3-section wf-p3-shap-stack">
          <p class="wf-p3-shap-guide">{{ i18nT("chat.trainingWorkflow.phase3.shapInterpretationGuide") }}</p>
          <div class="wf-p3-explanation-body">
            <template v-if="shapModelOptionsSorted.length">
              <div v-if="shapModelOptionsSorted.length > 1" class="wf-p2-shap-head wf-p2-shap-head--p3">
                <span class="wf-shap-label">{{ i18nT("chat.trainingWorkflow.phase2.explanationModel") }}</span>
                <select v-model="selectedShapModel" class="wf-shap-select">
                  <option v-for="m in shapModelOptionsSorted" :key="m" :value="m">{{ shapModelOptionLabel(m) }}</option>
                </select>
              </div>
              <div v-if="!phase2BeeswarmUrl && !phase2BarUrl" class="wf-p2-muted wf-p2-shap-missing">
                {{ i18nT("chat.trainingWorkflow.phase2.noShapFigures") }}
              </div>
              <div
                v-else
                class="wf-shap-grid"
                :class="{ 'wf-shap-grid--dual': Boolean(phase2BeeswarmUrl && phase2BarUrl) }"
              >
                <div v-if="phase2BeeswarmUrl" class="wf-shap-cell">
                  <div class="wf-shap-cap">{{ i18nT("chat.trainingWorkflow.phase3.beeswarmPlot") }}</div>
                  <a :href="phase2BeeswarmUrl" target="_blank" rel="noreferrer" class="wf-shap-img-wrap">
                    <img :src="phase2BeeswarmUrl" class="wf-shap-img" alt="" />
                  </a>
                </div>
                <div v-if="phase2BarUrl" class="wf-shap-cell">
                  <div class="wf-shap-cap">{{ i18nT("chat.trainingWorkflow.phase3.barPlot") }}</div>
                  <a :href="phase2BarUrl" target="_blank" rel="noreferrer" class="wf-shap-img-wrap">
                    <img :src="phase2BarUrl" class="wf-shap-img" alt="" />
                  </a>
                </div>
              </div>
              <p v-if="phase3HasShapFigures" class="wf-p3-explanation-note-below">
                {{ i18nT("chat.trainingWorkflow.phase3.screeningFigureNote") }}
              </p>
            </template>
            <div v-else class="wf-p2-muted">{{ i18nT("chat.trainingWorkflow.phase2.noShapFigures") }}</div>
          </div>
        </section>

        <section
          class="wf-p3-section wf-p3-pick"
          :class="{ 'wf-p3-pick--readonly': isWorkflowFrozen }"
          aria-labelledby="wf-p3-pick-heading"
        >
          <div class="wf-p3-pick-head wf-p3-pick-head--split">
            <h3 id="wf-p3-pick-heading" class="wf-p3-pick-heading">
              {{ i18nT("chat.trainingWorkflow.phase3.pickFeaturesHeading") }}
            </h3>
            <p class="wf-p3-pick-counts" role="status">{{ phase3PickCountLine }}</p>
          </div>
          <p class="wf-p3-pick-legend">{{ i18nT("chat.trainingWorkflow.phase3.pickFeaturesLegend") }}</p>

          <div class="wf-p3-panel wf-p3-panel--required">
            <div class="wf-p3-panel-title">{{ i18nT("chat.trainingWorkflow.phase3.panelRequiredTitle") }}</div>
            <p class="wf-p3-panel-note">{{ i18nT("chat.trainingWorkflow.phase3.panelRequiredNote") }}</p>
            <div class="wf-p3-grid wf-p3-grid--panel" role="list">
              <label
                v-for="col in medCols"
                :key="'p3r-' + col"
                class="wf-p3-item wf-p3-item--locked"
                :title="col"
                role="listitem"
              >
                <input type="checkbox" class="wf-p3-checkbox wf-p3-checkbox--locked" :checked="true" disabled />
                <span class="wf-p3-item-body">
                  <span class="wf-p3-item-name-row">
                    <span class="wf-feat-pri">{{ trainingFeaturePrimaryLabel(col) }}</span>
                  </span>
                </span>
              </label>
              <div v-if="medCols.length === 0" class="wf-p2-muted wf-p3-grid-empty" role="status">
                {{ i18nT("chat.trainingWorkflow.phase3.panelRequiredEmpty") }}
              </div>
            </div>
          </div>

          <div class="wf-p3-panel wf-p3-panel--optional">
            <div class="wf-p3-panel-title">{{ i18nT("chat.trainingWorkflow.phase3.panelOptionalTitle") }}</div>

            <div v-if="phase3SuggestedPickList.length" class="wf-p3-subpanel">
              <div class="wf-p3-subpanel-title">{{ i18nT("chat.trainingWorkflow.phase3.subpanelSuggestedTitle") }}</div>
              <div class="wf-p3-grid wf-p3-grid--panel" role="list">
                <label
                  v-for="col in phase3SuggestedPickList"
                  :key="'p3s-' + col"
                  class="wf-p3-item"
                  :title="col"
                  role="listitem"
                >
                  <input
                    type="checkbox"
                    class="wf-p3-checkbox"
                    :checked="picked.has(col)"
                    :disabled="isWorkflowFrozen"
                    @change="onToggleP3(col, ($event.target as HTMLInputElement).checked)"
                  />
                  <span class="wf-p3-item-body">
                    <span class="wf-p3-item-name-row">
                      <span class="wf-feat-pri">{{ trainingFeaturePrimaryLabel(col) }}</span>
                    </span>
                  </span>
                </label>
              </div>
            </div>

            <div v-if="phase3OtherPoolList.length" class="wf-p3-subpanel">
              <div class="wf-p3-subpanel-title">{{ i18nT("chat.trainingWorkflow.phase3.subpanelOtherTitle") }}</div>
              <div class="wf-p3-grid wf-p3-grid--panel" role="list">
                <label
                  v-for="col in phase3OtherPoolList"
                  :key="'p3o-' + col"
                  class="wf-p3-item"
                  :title="col"
                  role="listitem"
                >
                  <input
                    type="checkbox"
                    class="wf-p3-checkbox"
                    :checked="picked.has(col)"
                    :disabled="isWorkflowFrozen"
                    @change="onToggleP3(col, ($event.target as HTMLInputElement).checked)"
                  />
                  <span class="wf-p3-item-body">
                    <span class="wf-p3-item-name-row">
                      <span class="wf-feat-pri">{{ trainingFeaturePrimaryLabel(col) }}</span>
                    </span>
                  </span>
                </label>
              </div>
            </div>

            <div
              v-if="phase3SuggestedPickList.length === 0 && phase3OtherPoolList.length === 0"
              class="wf-p2-muted wf-p3-grid-empty"
              role="status"
            >
              {{ i18nT("chat.trainingWorkflow.phase3.noOptionalFeatures") }}
            </div>
          </div>
        </section>

        <div v-if="!isWorkflowFrozen" class="wf-actions wf-actions-phase3">
          <button type="button" class="wb-btn wb-btn-primary" :disabled="finalFeatures.length === 0" @click="confirmPhase3">
            {{ i18nT("chat.trainingWorkflow.phase3.confirmFeaturesButton") }}
          </button>
        </div>
        <div v-else-if="isWorkflowSubmitted" class="wf-actions wf-actions-submitted-hint wf-actions-phase3-readonly">
          <span>{{ i18nT("chat.trainingWorkflow.phase3.featureConfirmationSubmitted") }}</span>
        </div>
      </template>

      <template v-else-if="effectivePhase === WF_PHASE4">
        <div class="wf-phase4-intro">
          <p class="wf-phase4-intro-line">
            <b>{{ i18nT("chat.trainingWorkflow.labels.currentStep") }}</b>{{ workflowCurrentDoingLine(effectivePhase, i18nT) }}
          </p>
          <p class="wf-phase4-intro-line">
            <b>{{ i18nT("chat.trainingWorkflow.labels.mustConfirm") }}</b>{{ workflowUserMustConfirmLine(effectivePhase, i18nT) }}
          </p>
          <p class="wf-phase4-intro-line">
            <b>{{ i18nT("chat.trainingWorkflow.labels.nextStep") }}</b>{{ workflowWhatHappensNextLine(effectivePhase, i18nT) }}
          </p>
          <p class="wf-phase4-intro-line">{{ i18nT("chat.trainingWorkflow.phase4.cvComparisonHint") }}</p>
        </div>
        <AllModelPerformanceTable
          class="wf-mt-sm"
          embedded
          workflow-table
          :artifacts="mergedArtifactMap"
          :result-summary="mergedResultSummary"
          :objective-metric="p4Objective"
          final-model=""
          :workflow-selected-algorithm="p4ModelType"
          :ml-task-type="String((props.data.params_snapshot || {}).ml_task_type || props.data.ml_task_type || '')"
          @evidence-state="onPhase4TableEvidence"
        />
        <div
          v-if="phase4CvDataMissingBanner"
          class="wf-phase4-cv-missing"
          role="alert"
        >
          <span class="wf-phase4-cv-missing-text">{{ i18nT("chat.trainingWorkflow.phase4.cvTableMissingAfterRefresh") }}</span>
          <button
            type="button"
            class="wb-btn wb-btn-secondary wb-btn-sm wf-phase4-reload-btn"
            :disabled="phase4ReloadBusy || phase4TableEvidence.loading"
            @click="onReloadPhase4Evidence"
          >
            {{ i18nT("chat.trainingWorkflow.phase4.reloadModelComparison") }}
          </button>
        </div>

        <template v-if="!isWorkflowFrozen">
          <div class="wf-mt">
            <label class="wf-label">{{ i18nT("chat.trainingWorkflow.phase4.algorithmLabel") }}</label>
            <select v-model="p4ModelType" class="wf-input-full" @change="p4UserLockedModel = true">
              <option v-for="opt in p4ModelOptions" :key="opt" :value="opt">
                {{ p4ModelOptionLabel(opt) }}
              </option>
            </select>
          </div>
          <div class="wf-mt">
            <label class="wf-label">{{ i18nT("chat.trainingWorkflow.phase4.metricLabel") }}</label>
            <select v-model="p4Objective" class="wf-input-full">
              <option v-for="op in metricOptions" :key="op.value" :value="op.value">{{ op.label }}</option>
            </select>
          </div>
          <div class="wf-mt">
            <label class="wf-label">{{ i18nT("chat.trainingWorkflow.phase4.tuningEffortLabel") }}</label>
            <select v-model="p4TuningLevel" class="wf-input-full">
              <option value="default">{{ i18nT("chat.trainingWorkflow.phase4.tuningDefault") }}</option>
              <option value="full">{{ i18nT("chat.trainingWorkflow.phase4.tuningFull") }}</option>
            </select>
          </div>

          <div class="wf-actions">
            <button
              type="button"
              class="wb-btn wb-btn-primary"
              :disabled="phase4ConfirmBlocked"
              @click="confirmPhase4"
            >
              {{ i18nT("chat.trainingWorkflow.phase4.confirmStartTraining") }}
            </button>
          </div>
        </template>
        <div v-else-if="isWorkflowSubmitted" class="wf-actions wf-actions-submitted-hint">
          <span>{{ i18nT("chat.trainingWorkflow.phase4.submittedConfigHint") }}</span>
        </div>
      </template>

      <template v-else-if="effectivePhase === WF_PHASE5">
        <div class="wf-step-block">
          <div>
            <b>{{ i18nT("chat.trainingWorkflow.phase5.headlineTrainingDone") }}</b>
            {{ i18nT("chat.trainingWorkflow.phase5.leadReviewPerformance") }}
          </div>
          <div class="wf-step-mt">{{ i18nT("chat.trainingWorkflow.phase5.publishDecisionPrompt") }}</div>
          <div class="wf-step-mt wf-phase5-publish-consequence">
            <b>{{ i18nT("chat.trainingWorkflow.labels.nextStep") }}</b>{{ workflowWhatHappensNextLine(effectivePhase, i18nT) }}
          </div>
        </div>

        <div class="wf-phase5-publish-summary wf-mt">
          <div class="wf-phase5-publish-heading">{{ i18nT("chat.trainingWorkflow.phase5.publishReviewTitle") }}</div>
          <div class="wf-phase5-metrics-scroll wf-mt-sm">
            <table v-if="phase5SummaryLines.length" class="wf-phase5-meta-table">
              <thead>
                <tr>
                  <th v-for="(line, idx) in phase5SummaryLines" :key="'p5h-' + idx">{{ line.label }}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td v-for="(line, idx) in phase5SummaryLines" :key="'p5v-' + idx">{{ line.value }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="phase5LockedFeatures.length" class="wf-mt">
            <div class="wf-label">
              {{
                i18nT("chat.trainingWorkflow.phase5.inputFeaturesHeading", {
                  count: phase5LockedFeatures.length,
                })
              }}
            </div>
            <div class="wf-p5-feature-chips">
              <span
                v-for="f in phase5VisibleFeatures"
                :key="'p5f-' + f"
                class="wf-p5-chip"
                :title="f"
              >{{ clinicalizeExplanationFeatureNames(trainingFeaturePrimaryLabel(f)) }}</span>
            </div>
            <button
              v-if="phase5FeatureExpandable"
              type="button"
              class="wb-btn wb-btn-text wb-btn-sm wf-p5-features-toggle"
              @click="phase5FeaturesExpanded = !phase5FeaturesExpanded"
            >
              {{
                phase5FeaturesExpanded
                  ? i18nT("task.resultCard.presentation.collapseAllFeatures")
                  : i18nT("task.resultCard.presentation.expandAllFeatures")
              }}
            </button>
          </div>
        </div>

        <div class="wf-phase5-results-box wf-mt">
          <div class="wf-phase5-results-head">
            <div class="wf-phase5-results-title">{{ i18nT("chat.trainingWorkflow.phase5.finalMetricsTitle") }}</div>
          </div>
          <div class="wf-phase5-results-body">
            <p v-if="!phase5HasRenderableKeyMetrics" class="wf-phase5-metrics-hint">
              {{ i18nT("chat.trainingWorkflow.phase5.finalMetricsUnavailable") }}
            </p>
            <div v-if="phase5HorizontalMetricCells.length" class="wf-phase5-metrics-scroll">
              <table class="wf-phase5-metrics-table">
                <thead>
                  <tr>
                    <th
                      v-for="cell in phase5HorizontalMetricCells"
                      :key="'h-' + cell.key"
                      :class="{ 'wf-metric-primary': cell.isPrimary }"
                    >
                      {{ cell.label }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td
                      v-for="cell in phase5HorizontalMetricCells"
                      :key="'v-' + cell.key"
                      :class="{ 'wf-metric-primary': cell.isPrimary }"
                    >
                      {{ cell.value }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <details v-if="phase5ChartBlocks.length" class="wf-phase5-charts-details wf-mt-sm">
              <summary class="wf-phase5-charts-summary">{{ i18nT("task.resultCard.viewTrainingCharts") }}</summary>
              <div class="wf-phase5-charts-grid">
                <div v-for="blk in phase5ChartBlocks" :key="blk.url" class="wf-phase5-chart-cell">
                  <div class="wf-phase5-chart-cap">{{ blk.caption }}</div>
                  <img :src="blk.url" class="wf-phase5-chart-img" alt="" />
                </div>
              </div>
            </details>
          </div>
        </div>
        <div class="wf-mt">
          <label class="wf-label">{{ i18nT("chat.trainingWorkflow.phase5.releaseDisplayNameLabel") }}</label>
          <input
            v-model="p5DisplayName"
            type="text"
            class="wf-input-full"
            :disabled="isWorkflowFrozen"
            :placeholder="i18nT('chat.trainingWorkflow.phase5.releaseDisplayNamePlaceholder')"
          />
        </div>
        <div class="wf-mt">
          <label class="wf-label">{{ i18nT("chat.trainingWorkflow.phase5.releaseModelIdLabel") }}</label>
          <input
            v-model="p5ModelId"
            type="text"
            class="wf-input-full"
            :disabled="isWorkflowFrozen"
            :placeholder="i18nT('chat.trainingWorkflow.phase5.releaseModelIdPlaceholder')"
          />
        </div>
        <div class="wf-mt">
          <label class="wf-label">{{ i18nT("chat.trainingWorkflow.phase5.notesLabel") }}</label>
          <textarea v-model="p5Notes" rows="2" class="wf-input-full" :disabled="isWorkflowFrozen" />
        </div>

        <div v-if="!isWorkflowFrozen" class="wf-actions wf-actions-phase5-release">
          <button type="button" class="wb-btn wb-btn-secondary" @click="skipPublish">
            {{ i18nT("chat.trainingWorkflow.phase5.skipPublish") }}
          </button>
          <button type="button" class="wb-btn wb-btn-primary" @click="confirmPhase5">
            {{ i18nT("chat.trainingWorkflow.phase5.confirmPublish") }}
          </button>
        </div>
        <div v-else-if="isWorkflowSubmitted" class="wf-actions wf-actions-submitted-hint">
          <span>{{ i18nT("chat.trainingWorkflow.phase5.submittedHint") }}</span>
        </div>
      </template>

    <div v-if="embedded && showEscapeFooter" class="wf-escape-footer">
      <p class="wf-escape-hint">{{ i18nT("chat.trainingWorkflow.escape.returnLaterHint") }}</p>
      <button type="button" class="wb-btn wb-btn-secondary wb-btn-sm" @click="onRequestCancelJob">
        {{ i18nT("chat.trainingWorkflow.escape.cancelTask") }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { I18nT, useI18n } from "vue-i18n";
import { getTaskDetail } from "../../api";
import AllModelPerformanceTable from "./AllModelPerformanceTable.vue";
import {
  clinicalTaskIdDisplayLabel,
  objectiveMetricOptionsForMlTaskType,
} from "../../config/trainingSchemas";
import type { TaskDetailData, TrainingWorkflowPendingActionData } from "../../types";
import { clinicalizeExplanationFeatureNames } from "../../utils/featureDisplayName";
import {
  cvRowModelToAlgorithmOption,
  pickBestCvRow,
  TRAINING_WORKFLOW_ALGORITHM_OPTIONS,
  type CvMetricRow,
} from "../../utils/cvModelSelection";
import {
  WF_PHASE3,
  WF_PHASE4,
  WF_PHASE5,
  normalizeWorkflowPhase,
  formatShapScreeningModelDisplayName,
  trainingFeaturePrimaryLabel,
  trainingMetricLabel,
  trainingModelTypeDisplay,
  workflowCardBusinessTitle,
  workflowCurrentDoingLine,
  workflowUserMustConfirmLine,
  workflowWhatHappensNextLine,
} from "../../utils/trainingWorkflowPresentation";
import {
  canonicalBucketForShapScreeningSlug,
  parseShapBarBaselineSlug,
  parseShapBeeswarmBaselineSlug,
} from "../../utils/trainingShapScreeningPlots";

const { t: i18nT, locale } = useI18n();

const p4ModelOptions = [...TRAINING_WORKFLOW_ALGORITHM_OPTIONS];

function p4ModelOptionLabel(opt: string): string {
  return `${trainingModelTypeDisplay(opt)} (${opt})`;
}

const props = defineProps<{ data: TrainingWorkflowPendingActionData; embedded?: boolean }>();
const emit = defineEmits<{
  (e: "confirm", payload: Record<string, unknown>): void;
  (e: "request-cancel-job", payload: { job_id: string }): void;
}>();
const selectedShapModel = ref("");

const effectivePhase = computed(() => normalizeWorkflowPhase(String(props.data.phase || "")));

const refreshedTaskDetail = ref<TaskDetailData | null>(null);

/** Prefer non-empty CV rows: a stale refresh must not wipe rows already present on the chat card snapshot. */
function mergeTrainingWorkflowResultSummary(
  base: Record<string, unknown>,
  fresh: Record<string, unknown> | undefined | null,
): Record<string, unknown> {
  if (!fresh || typeof fresh !== "object") return { ...base };
  const merged: Record<string, unknown> = { ...base, ...fresh };
  const br = base.all_model_metrics_rows;
  const fr = fresh.all_model_metrics_rows;
  const brLen = Array.isArray(br) ? br.length : 0;
  const frLen = Array.isArray(fr) ? fr.length : 0;
  if (frLen > 0) merged.all_model_metrics_rows = fr;
  else if (brLen > 0) merged.all_model_metrics_rows = br;

  const bkm = base.key_metrics;
  const fkm = fresh.key_metrics;
  const fkmOk = fkm && typeof fkm === "object" && Object.keys(fkm as object).length > 0;
  const bkmOk = bkm && typeof bkm === "object" && Object.keys(bkm as object).length > 0;
  if (fkmOk) merged.key_metrics = fkm;
  else if (bkmOk) merged.key_metrics = bkm;

  const bfm = base.final_model_metrics;
  const ffm = fresh.final_model_metrics;
  const ffmOk = ffm && typeof ffm === "object" && Object.keys(ffm as object).length > 0;
  const bfmOk = bfm && typeof bfm === "object" && Object.keys(bfm as object).length > 0;
  if (ffmOk) merged.final_model_metrics = ffm;
  else if (bfmOk) merged.final_model_metrics = bfm;

  const fmp = fresh.metrics_protocol;
  if (fmp != null && String(fmp).trim() !== "") merged.metrics_protocol = fmp;
  else if (base.metrics_protocol != null) merged.metrics_protocol = base.metrics_protocol;

  if (fresh.enable_search_applied !== undefined && fresh.enable_search_applied !== null) {
    merged.enable_search_applied = fresh.enable_search_applied;
  }

  return merged;
}

const mergedResultSummary = computed((): Record<string, unknown> => {
  const base = (props.data.result_summary || {}) as Record<string, unknown>;
  const fresh = refreshedTaskDetail.value?.task?.result_summary;
  return mergeTrainingWorkflowResultSummary(base, fresh as Record<string, unknown> | undefined);
});

const mergedArtifactMap = computed((): Record<string, string> => {
  const base = (props.data.artifacts || {}) as Record<string, string>;
  const tArts = (refreshedTaskDetail.value?.task?.artifacts || {}) as Record<string, string>;
  const top = refreshedTaskDetail.value?.artifacts || {};
  return { ...base, ...tArts, ...top };
});

async function refreshWorkflowTaskEvidence() {
  if (
    effectivePhase.value !== WF_PHASE3 &&
    effectivePhase.value !== WF_PHASE4 &&
    effectivePhase.value !== WF_PHASE5
  ) {
    refreshedTaskDetail.value = null;
    return;
  }
  try {
    refreshedTaskDetail.value = await getTaskDetail(props.data.job_id);
  } catch {
    refreshedTaskDetail.value = null;
  }
}

async function refreshPhase3ShapEvidenceWithRetries() {
  if (effectivePhase.value !== WF_PHASE3) return;
  for (let attempt = 0; attempt < 4; attempt++) {
    await refreshWorkflowTaskEvidence();
    if (attempt < 3) await new Promise((r) => setTimeout(r, 450 * (attempt + 1)));
  }
}

async function refreshPhase4EvidenceWithRetries() {
  if (effectivePhase.value !== WF_PHASE4) return;
  for (let attempt = 0; attempt < 4; attempt++) {
    await refreshWorkflowTaskEvidence();
    const rs = refreshedTaskDetail.value?.task?.result_summary as Record<string, unknown> | undefined;
    const n = Array.isArray(rs?.all_model_metrics_rows) ? rs.all_model_metrics_rows.length : 0;
    if (n > 0) break;
    if (attempt < 3) await new Promise((r) => setTimeout(r, 450 * (attempt + 1)));
  }
}

watch(
  () => [props.data.job_id, effectivePhase.value, props.data.status],
  () => {
    void (async () => {
      const pending = String(props.data.status || "").toLowerCase() === "pending";
      if (effectivePhase.value === WF_PHASE4 && pending) {
        await refreshPhase4EvidenceWithRetries();
      } else if (effectivePhase.value === WF_PHASE3 && pending) {
        await refreshPhase3ShapEvidenceWithRetries();
      } else {
        await refreshWorkflowTaskEvidence();
      }
    })();
  },
  { immediate: true },
);

const phase4TableEvidence = ref({ loading: true, rowCount: 0 });
const phase4ReloadBusy = ref(false);

function onPhase4TableEvidence(payload: { loading: boolean; rowCount: number; workflowMode: boolean }) {
  if (!payload.workflowMode || effectivePhase.value !== WF_PHASE4) return;
  phase4TableEvidence.value = { loading: payload.loading, rowCount: payload.rowCount };
}

async function onReloadPhase4Evidence() {
  if (phase4ReloadBusy.value) return;
  phase4ReloadBusy.value = true;
  try {
    await refreshPhase4EvidenceWithRetries();
  } finally {
    phase4ReloadBusy.value = false;
  }
}

const phase4CvDataMissingBanner = computed(() => {
  if (effectivePhase.value !== WF_PHASE4) return false;
  if (String(props.data.status || "").toLowerCase() !== "pending") return false;
  return !phase4TableEvidence.value.loading && phase4TableEvidence.value.rowCount === 0;
});

const phase4ConfirmBlocked = computed(() => {
  if (effectivePhase.value !== WF_PHASE4) return false;
  if (String(props.data.status || "").toLowerCase() !== "pending") return false;
  return phase4TableEvidence.value.loading || phase4TableEvidence.value.rowCount === 0;
});

const isWorkflowSubmitted = computed(() => String(props.data.status || "").toLowerCase() === "submitted");
const isWorkflowFrozen = computed(() => String(props.data.status || "").toLowerCase() !== "pending");

const showEscapeFooter = computed(
  () =>
    Boolean(props.embedded) &&
    !isWorkflowFrozen.value &&
    String(props.data.status || "").toLowerCase() === "pending" &&
    effectivePhase.value !== WF_PHASE3,
);

function onRequestCancelJob() {
  emit("request-cancel-job", { job_id: props.data.job_id });
}

/** Superseded / completed / locked: compact alert only (submitted keeps evidence visible without this banner). */
const workflowNonPendingAlert = computed(() => {
  const s = String(props.data.status || "").toLowerCase();
  return s !== "pending" && s !== "submitted";
});

const workflowNonPendingAlertText = computed(() => {
  const st = String(props.data.status || "").toLowerCase();
  if (st === "superseded") return i18nT("chat.trainingWorkflow.inactive.superseded");
  if (st === "completed") return i18nT("chat.trainingWorkflow.inactive.completedLocked");
  if (st === "locked") return i18nT("chat.trainingWorkflow.inactive.lockedState");
  return i18nT("chat.trainingWorkflow.inactive.statusLine", {
    status: st || i18nT("chat.trainingWorkflow.inactive.statusUnknownHandled"),
  });
});

const suggested = computed(() => (props.data.suggested_final_features || []).map((x) => String(x)).filter(Boolean));
const medCols = computed(() => (props.data.med_cols || []).map((x) => String(x)).filter(Boolean));
const candidatePool = computed(() => (props.data.candidate_pool_columns || []).map((x) => String(x)).filter(Boolean));
const suggestedSet = computed(() => new Set(suggested.value));
const medColsSet = computed(() => new Set(medCols.value));

const phase3SuggestedPickList = computed(() =>
  suggested.value.filter((c) => !medColsSet.value.has(String(c).trim())),
);

const phase3OtherPoolList = computed(() =>
  candidatePool.value.filter((c) => !medColsSet.value.has(String(c).trim()) && !suggestedSet.value.has(String(c).trim())),
);

function phase3IsRequiredColumn(col: string): boolean {
  return medColsSet.value.has(String(col).trim());
}

const picked = ref<Set<string>>(new Set<string>());
const finalFeatures = computed(() => Array.from(picked.value));

function onToggleP3(col: string, checked: boolean) {
  const next = new Set(picked.value);
  if (checked) next.add(col);
  else next.delete(col);
  // Required clinical columns must stay selected.
  for (const c of medCols.value) next.add(c);
  picked.value = next;
}

watch(
  () => props.data.card_id,
  () => {
    const phase = normalizeWorkflowPhase(String(props.data.phase || ""));
    selectedShapModel.value = "";
    if (phase !== WF_PHASE3) return;
    const next = new Set<string>();
    for (const c of suggested.value) next.add(c);
    for (const c of medCols.value) next.add(c);
    picked.value = next;
  },
  { immediate: true },
);

function confirmPhase3() {
  emit("confirm", {
    job_id: props.data.job_id,
    phase: WF_PHASE3,
    action: "confirm_final_features",
    final_features: finalFeatures.value,
  });
}

const p4ModelType = ref("xgboost");
const p4Objective = ref("auroc");
const p4TuningLevel = ref<"default" | "full">("default");

const metricOptions = computed(() => {
  const ml = String(props.data.ml_task_type || "binary");
  return objectiveMetricOptionsForMlTaskType(ml);
});

const phase4CvRows = computed<CvMetricRow[]>(() => {
  const r = mergedResultSummary.value.all_model_metrics_rows;
  if (!Array.isArray(r)) return [];
  return r.filter((x) => x && typeof x === "object") as CvMetricRow[];
});

const p4UserLockedModel = ref(false);
let p4ApplyingCvPick = false;

function applyPhase4BestModelFromCv() {
  if (normalizeWorkflowPhase(String(props.data.phase || "")) !== WF_PHASE4) return;
  if (p4UserLockedModel.value) return;
  const rows = phase4CvRows.value;
  if (!rows.length) return;
  const best = pickBestCvRow(rows, p4Objective.value);
  const opt = best?.model ? cvRowModelToAlgorithmOption(String(best.model), p4ModelOptions) : undefined;
  if (!opt) return;
  p4ApplyingCvPick = true;
  try {
    p4ModelType.value = opt;
  } finally {
    p4ApplyingCvPick = false;
  }
}

watch(p4Objective, () => {
  if (normalizeWorkflowPhase(String(props.data.phase || "")) !== WF_PHASE4) return;
  if (String(props.data.status || "").toLowerCase() !== "pending") return;
  applyPhase4BestModelFromCv();
});

watch(
  () => phase4CvRows.value,
  () => {
    if (normalizeWorkflowPhase(String(props.data.phase || "")) !== WF_PHASE4) return;
    if (String(props.data.status || "").toLowerCase() !== "pending") return;
    applyPhase4BestModelFromCv();
  },
  { deep: true },
);

watch(
  () => props.data.card_id,
  () => {
    if (normalizeWorkflowPhase(String(props.data.phase || "")) !== WF_PHASE4) return;
    p4UserLockedModel.value = false;
    const p = props.data.params_snapshot || {};
    const defaultObj = String((p as Record<string, unknown>).ml_task_type) === "regression" ? "mse" : "auroc";
    p4Objective.value = String((p as Record<string, unknown>).objective_metric || defaultObj);
    const ops = metricOptions.value;
    if (ops.length && !ops.some((o) => o.value === p4Objective.value)) p4Objective.value = ops[0].value;
    p4TuningLevel.value = Boolean((p as Record<string, unknown>).enable_search) ? "full" : "default";
    if (!phase4CvRows.value.length) {
      p4ModelType.value = String((p as Record<string, unknown>).model_type || "xgboost");
    } else {
      applyPhase4BestModelFromCv();
    }
  },
  { immediate: true },
);

function confirmPhase4() {
  emit("confirm", {
    job_id: props.data.job_id,
    phase: WF_PHASE4,
    action: "confirm_train_config",
    model_type: p4ModelType.value,
    objective_metric: p4Objective.value,
    enable_search: p4TuningLevel.value === "full",
  });
}

const p5ModelId = ref("");
const p5DisplayName = ref("");
const p5Notes = ref("");
const phase5FeaturesExpanded = ref(false);
const P5_FEATURE_PREVIEW = 20;


const releaseDraftModelId = computed(() => {
  const rs = (props.data.result_summary || {}) as Record<string, unknown>;
  const ps = (props.data.params_snapshot || {}) as Record<string, unknown>;
  const raw = rs.model_id_draft ?? rs.model_id ?? ps.model_id ?? props.data.model_id;
  return raw != null ? String(raw).trim() : "";
});

function findArtifactUrlByName(predicate: (name: string) => boolean): string | null {
  for (const [name, url] of Object.entries(mergedArtifactMap.value)) {
    if (predicate(name.toLowerCase())) return String(url);
  }
  return null;
}

type ShapModelArtifacts = { beeswarm?: string; bar?: string };

function preferArtifactUrl(prev: string | undefined, next: string): string {
  return prev && prev.length > 0 ? prev : next;
}

const shapArtifactsByModel = computed<Record<string, ShapModelArtifacts>>(() => {
  const out: Record<string, ShapModelArtifacts> = {};
  for (const [nameRaw, url] of Object.entries(mergedArtifactMap.value)) {
    const base = nameRaw.replace(/\\/g, "/").split("/").pop() || nameRaw;
    const nameLow = base.toLowerCase();
    if (!nameLow.endsWith(".png") || !nameLow.includes("shap")) continue;
    const strUrl = String(url);

    if (nameLow.includes("beeswarm")) {
      const rawSlug = parseShapBeeswarmBaselineSlug(nameLow);
      const isGenericBee =
        nameLow === "shap_beeswarm.png" || nameLow === "shap-beeswarm.png";
      const bucket =
        rawSlug != null
          ? canonicalBucketForShapScreeningSlug(rawSlug)
          : isGenericBee
            ? "default"
            : null;
      if (bucket == null) continue;
      if (!out[bucket]) out[bucket] = {};
      out[bucket].beeswarm = preferArtifactUrl(out[bucket].beeswarm, strUrl);
      continue;
    }

    const barSlug = parseShapBarBaselineSlug(nameLow);
    if (barSlug) {
      const bucket = canonicalBucketForShapScreeningSlug(barSlug);
      if (!out[bucket]) out[bucket] = {};
      out[bucket].bar = preferArtifactUrl(out[bucket].bar, strUrl);
    }
  }
  const genericBee = findArtifactUrlByName((n) => n === "shap_beeswarm.png" || n === "shap-beeswarm.png");
  const genericBar = findArtifactUrlByName((n) => n === "shap_bar.png" || n === "shap-bar.png");
  if (genericBee || genericBar) {
    if (!out.default) out.default = {};
    if (genericBee) out.default.beeswarm = preferArtifactUrl(out.default.beeswarm, genericBee);
    if (genericBar) out.default.bar = preferArtifactUrl(out.default.bar, genericBar);
  }
  return out;
});
const shapModelOptionsSorted = computed(() => {
  const keys = Object.keys(shapArtifactsByModel.value);
  return [...keys].sort((a, b) =>
    formatShapScreeningModelDisplayName(a).localeCompare(formatShapScreeningModelDisplayName(b)),
  );
});

/** Locale-aware list for lead paragraphs. */
function formatConjoinedList(labels: string[], localeStr: string): string {
  void localeStr;
  const items = labels.map((s) => String(s || "").trim()).filter(Boolean);
  if (items.length === 0) return "";
  if (items.length === 1) return items[0]!;
  if (items.length === 2) {
    return i18nT("chat.listConjunction.two", { first: items[0], second: items[1] });
  }
  return i18nT("chat.listConjunction.many", {
    items: items.slice(0, -1).join(i18nT("chat.listSeparator")),
    last: items[items.length - 1],
  });
}

/** Suggested features that are not required clinical columns — “additionally recommended”. */
const phase3SuggestedAdditionalColumns = computed(() =>
  suggested.value.filter((c) => !medColsSet.value.has(String(c).trim())),
);

const phase3TotalInputFeatures = computed(() => finalFeatures.value.length);

/** Default screening outcome size (required ∪ suggested), for summary lead copy. */
const phase3ScreeningCompactCount = computed(() => {
  const s = new Set<string>();
  for (const c of suggested.value) s.add(String(c).trim());
  for (const c of medCols.value) s.add(String(c).trim());
  return s.size;
});

const phase3RequiredLabelsJoined = computed(() =>
  formatConjoinedList(
    medCols.value.map((c) => trainingFeaturePrimaryLabel(c)),
    String(locale.value || "en-US"),
  ),
);

const phase3SuggestedLabelsJoined = computed(() =>
  formatConjoinedList(
    phase3SuggestedAdditionalColumns.value.map((c) => trainingFeaturePrimaryLabel(c)),
    String(locale.value || "en-US"),
  ),
);

const phase3OtherPoolLabelsJoined = computed(() =>
  formatConjoinedList(
    phase3OtherPoolList.value.map((c) => trainingFeaturePrimaryLabel(c)),
    String(locale.value || "en-US"),
  ),
);

const phase3InputFeaturesBoldPhrase = computed(() =>
  i18nT("chat.trainingWorkflow.phase3.inputFeaturesBoldPhrase", { count: phase3ScreeningCompactCount.value }),
);

const phase3RequiredTreatmentBoldPhrase = computed(() =>
  medCols.value.length === 1
    ? i18nT("chat.trainingWorkflow.phase3.requiredTreatmentBoldOne")
    : i18nT("chat.trainingWorkflow.phase3.requiredTreatmentBoldMany", { count: medCols.value.length }),
);

const phase3SuggestedVarsBoldPhrase = computed(() =>
  phase3SuggestedAdditionalColumns.value.length === 1
    ? i18nT("chat.trainingWorkflow.phase3.suggestedVarsBoldOne")
    : i18nT("chat.trainingWorkflow.phase3.suggestedVarsBoldMany", {
        count: phase3SuggestedAdditionalColumns.value.length,
      }),
);

const phase3OtherSingleBoldLabel = computed(() =>
  phase3OtherPoolList.value.length === 1 ? trainingFeaturePrimaryLabel(phase3OtherPoolList.value[0]!) : "",
);

const phase3SelectedSuggestedCount = computed(() =>
  phase3SuggestedPickList.value.filter((c) => picked.value.has(c)).length,
);

const phase3SelectedOtherCount = computed(() =>
  phase3OtherPoolList.value.filter((c) => picked.value.has(c)).length,
);

const phase3PickCountLine = computed(() => {
  const total = finalFeatures.value.length;
  const req = medCols.value.length;
  const sug = phase3SelectedSuggestedCount.value;
  const opt = phase3SelectedOtherCount.value;
  if (opt > 0) {
    return i18nT("chat.trainingWorkflow.phase3.pickFeaturesCountThreeParts", { total, required: req, suggested: sug, optional: opt });
  }
  return i18nT("chat.trainingWorkflow.phase3.pickFeaturesCountTwoParts", { total, required: req, suggested: sug });
});

function shapModelOptionLabel(m: string): string {
  if (m === "default") return i18nT("chat.trainingWorkflow.phase2.explanationModelUnknown");
  return formatShapScreeningModelDisplayName(m);
}

const phase2BeeswarmUrl = computed(() => shapArtifactsByModel.value[selectedShapModel.value || ""]?.beeswarm || null);
const phase2BarUrl = computed(() => shapArtifactsByModel.value[selectedShapModel.value || ""]?.bar || null);
const phase3HasShapFigures = computed(() => Boolean(phase2BeeswarmUrl.value || phase2BarUrl.value));

watch(
  () => shapModelOptionsSorted.value,
  () => ensureSelectedShapModel(),
  { immediate: true },
);

function ensureSelectedShapModel() {
  const options = shapModelOptionsSorted.value;
  if (options.length === 0) {
    selectedShapModel.value = "";
    return;
  }
  if (!options.includes(selectedShapModel.value)) selectedShapModel.value = options[0];
}

function normalizeKeyMetricsBlob(src: unknown): Record<string, unknown> {
  if (!src || typeof src !== "object") return {};
  const o = src as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(o)) {
    out[String(k).toLowerCase().replace(/-/g, "_")] = v;
  }
  return out;
}

/** Final trained model metrics only — never use all_model_metrics_rows (Phase4 CV comparison). */
const mergedKeyMetrics = computed((): Record<string, unknown> => {
  const rs = mergedResultSummary.value as Record<string, unknown>;
  for (const tk of ["final_model_metrics", "key_metrics", "final_model_key_metrics", "final_metrics"] as const) {
    const blob = normalizeKeyMetricsBlob(rs[tk]);
    if (Object.keys(blob).length > 0) return blob;
  }
  const fm = rs.final_model_metrics;
  if (fm && typeof fm === "object") {
    const blob = normalizeKeyMetricsBlob(fm);
    if (Object.keys(blob).length > 0) return blob;
  }
  return {};
});

const phase5LockedFeatures = computed(() => {
  const rs = mergedResultSummary.value as Record<string, unknown>;
  const raw = rs.final_features_locked;
  if (Array.isArray(raw)) return raw.map((x) => String(x)).filter((s) => s.trim());
  const ps = (props.data.params_snapshot || {}) as Record<string, unknown>;
  const ff = ps.final_features;
  if (Array.isArray(ff)) return ff.map((x) => String(x)).filter((s) => s.trim());
  return [];
});

const phase5VisibleFeatures = computed(() => {
  const all = phase5LockedFeatures.value;
  if (phase5FeaturesExpanded.value || all.length <= P5_FEATURE_PREVIEW) return all;
  return all.slice(0, P5_FEATURE_PREVIEW);
});

const phase5FeatureExpandable = computed(() => phase5LockedFeatures.value.length > P5_FEATURE_PREVIEW);

const phase5SummaryLines = computed(() => {
  const rs = mergedResultSummary.value as Record<string, unknown>;
  const ps = (props.data.params_snapshot || {}) as Record<string, unknown>;
  const mlRaw = String(ps.ml_task_type || props.data.ml_task_type || "binary").toLowerCase();
  const mlKindLabel =
    mlRaw === "multiclass"
      ? i18nT("task.resultCard.presentation.mlMulticlass")
      : mlRaw === "regression"
        ? i18nT("task.resultCard.presentation.mlRegression")
        : i18nT("task.resultCard.presentation.mlBinary");
  const clinicalLabel = clinicalTaskIdDisplayLabel(ps.clinical_task_id, i18nT);
  const taskKindValue = clinicalLabel ? `${clinicalLabel} · ${mlKindLabel}` : mlKindLabel;
  const dataset =
    String(rs.dataset_display_name || "").trim() || i18nT("task.resultCard.presentation.datasetUnknown");
  const algo =
    String(rs.programmer_model || rs.trained_model_programmer_name || ps.model_type || "").trim() ||
    i18nT("common.na");
  const primaryRaw = String(ps.objective_metric || rs.primary_metric_requested || "").trim().toLowerCase();
  const primaryLabel = primaryRaw ? trainingMetricLabel(primaryRaw) : i18nT("common.na");
  return [
    { label: i18nT("chat.trainingWorkflow.phase5.summaryTaskKind"), value: taskKindValue },
    { label: i18nT("chat.trainingWorkflow.phase5.summaryAlgorithm"), value: algo },
    { label: i18nT("task.resultCard.presentation.primaryMetric"), value: primaryLabel },
    { label: i18nT("task.resultCard.presentation.dataset"), value: dataset },
  ];
});

function resolveKeyMetric(km: Record<string, unknown>, ...keys: string[]): unknown {
  for (const k of keys) {
    const lk = k.toLowerCase();
    if (lk in km) return km[lk];
    if (k in km) return km[k];
  }
  return undefined;
}

type Phase5MetricCell = { key: string; label: string; value: string; isPrimary: boolean };

const phase5HorizontalMetricCells = computed<Phase5MetricCell[]>(() => {
  if (effectivePhase.value !== WF_PHASE5) return [];
  const km = mergedKeyMetrics.value;
  const ml = String((props.data.params_snapshot || {}).ml_task_type || props.data.ml_task_type || "binary").toLowerCase();
  const primary = String(
    (props.data.params_snapshot || {}).objective_metric ||
      mergedResultSummary.value.primary_metric_requested ||
      "",
  )
    .trim()
    .toLowerCase();

  const fmt = (v: unknown) => formatMetric(v);

  if (ml === "regression") {
    return [
      {
        key: "mse",
        label: trainingMetricLabel("mse"),
        value: fmt(resolveKeyMetric(km, "mse")),
        isPrimary: primary === "mse",
      },
      {
        key: "pcc",
        label: i18nT("chat.modelPerformanceTable.metricShort.pcc"),
        value: fmt(resolveKeyMetric(km, "pcc", "pearson")),
        isPrimary: primary === "pcc" || primary === "pearson",
      },
    ];
  }

  const specs = [
    { key: "accuracy", aliases: [] as string[], label: trainingMetricLabel("accuracy") },
    { key: "precision", aliases: [], label: trainingMetricLabel("precision") },
    { key: "recall", aliases: [], label: trainingMetricLabel("recall") },
    { key: "f1", aliases: ["f1_score"], label: trainingMetricLabel("f1_score") },
    { key: "auroc", aliases: [], label: trainingMetricLabel("auroc") },
    { key: "auprc", aliases: [], label: trainingMetricLabel("auprc") },
  ];
  return specs.map((s) => ({
    key: s.key,
    label: s.label,
    value: fmt(resolveKeyMetric(km, s.key, ...s.aliases)),
    isPrimary: primary === s.key || (s.key === "f1" && (primary === "f1" || primary === "f1_score")),
  }));
});

const phase5HasRenderableKeyMetrics = computed(() => {
  const cells = phase5HorizontalMetricCells.value;
  const na = i18nT("common.na");
  return cells.some((c) => c.value !== na);
});

const rocChartUrl = computed(() =>
  findArtifactUrlByName((name) => (name.includes("roc") || name.includes("auc")) && name.endsWith(".png")),
);
const prChartUrl = computed(() =>
  findArtifactUrlByName((name) => (name.includes("pr") || name.includes("precision_recall")) && name.endsWith(".png")),
);
const regressionChartUrl = computed(() =>
  findArtifactUrlByName((name) => (name.includes("regression") || name.includes("scatter") || name.includes("pred")) && name.endsWith(".png")),
);

const phase5ChartBlocks = computed(() => {
  const out: { caption: string; url: string }[] = [];
  if (rocChartUrl.value) out.push({ caption: i18nT("chat.trainingWorkflow.phase5.rocChart"), url: rocChartUrl.value });
  if (prChartUrl.value) out.push({ caption: i18nT("chat.trainingWorkflow.phase5.prChart"), url: prChartUrl.value });
  if (regressionChartUrl.value) {
    out.push({
      caption: i18nT("chat.trainingWorkflow.phase5.regressionChart"),
      url: regressionChartUrl.value,
    });
  }
  return out;
});

function formatMetric(v: unknown): string {
  if (v == null || v === "") return i18nT("common.na");
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : String(v);
  const n = Number(v);
  if (!Number.isNaN(n) && String(v).trim() !== "") return n.toFixed(3);
  return String(v);
}

watch(
  () => props.data.card_id,
  () => {
    if (normalizeWorkflowPhase(String(props.data.phase || "")) !== WF_PHASE5) return;
    p5Notes.value = "";
    p5ModelId.value = releaseDraftModelId.value;
    const ps = (props.data.params_snapshot || {}) as Record<string, unknown>;
    p5DisplayName.value = String(ps.model_name || "").trim();
    phase5FeaturesExpanded.value = false;
  },
  { immediate: true },
);

function confirmPhase5() {
  const po: Record<string, unknown> = {};
  const dn = p5DisplayName.value.trim();
  if (dn) {
    po.display_name = dn;
    po.model_name = dn;
  }
  if (p5ModelId.value.trim()) po.model_id = p5ModelId.value.trim();
  if (p5Notes.value.trim()) po.notes = p5Notes.value.trim();
  emit("confirm", {
    job_id: props.data.job_id,
    phase: WF_PHASE5,
    action: "confirm_publish",
    do_publish: true,
    publish_overrides: Object.keys(po).length ? po : undefined,
  });
}

function skipPublish() {
  emit("confirm", {
    job_id: props.data.job_id,
    phase: WF_PHASE5,
    action: "confirm_publish",
    do_publish: false,
  });
}
</script>

<style scoped>
.workflow-card {
  border: 1px solid #e5e9ef;
  padding: 12px;
  margin-top: 6px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(31, 41, 55, 0.04);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.workflow-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.workflow-title {
  font-weight: 700;
  color: var(--wb-text-main);
  font-size: var(--wb-font-size-card-title);
  line-height: var(--wb-line-height-card);
}

.wf-nonpending-alert {
  margin-top: 8px;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid #eceff3;
  background: #fff;
  color: var(--wb-text-body-secondary);
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}

.wf-escape-footer {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.wf-escape-hint {
  margin: 0;
  flex: 1 1 220px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}

.wf-actions-submitted-hint {
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}

.workflow-card input,
.workflow-card select,
.workflow-card textarea {
  box-sizing: border-box;
  max-width: 100%;
  border: 1px solid #d2dbe7;
  border-radius: 7px;
  min-height: 30px;
  padding: 0 8px;
  background: #fff;
}

.workflow-card textarea {
  padding-top: 8px;
}

.workflow-card input:disabled,
.workflow-card select:disabled,
.workflow-card textarea:disabled {
  color: var(--wb-text-disabled);
}

.wf-step-block {
  margin-top: 10px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
}
.wf-step-mt {
  margin-top: 8px;
}
.wf-next-step {
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-body-secondary);
}

.wf-phase4-intro {
  margin-top: 10px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-body-secondary);
}

.wf-phase4-intro-line {
  margin: 0;
  padding: 0;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
}
.wf-phase5-publish-consequence {
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-body-secondary);
}
.wf-layer-title {
  font-weight: 600;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}
.wf-layer-hint {
  margin: 4px 0 0;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}
.wf-layer {
  padding: 8px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e5e9ef;
}
.wf-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  align-items: center;
}
.wf-meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: var(--wb-font-size-caption);
  line-height: var(--wb-line-height-caption);
  font-weight: 500;
  color: var(--wb-text-body-secondary);
  background: #f6f7f9;
  border: 1px solid #e5e7eb;
  max-width: 100%;
}
.wf-feat-pri {
  font-weight: 500;
}
.wf-p2-box {
  margin-top: 10px;
  padding: 8px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  background: #fff;
}

.wf-p2-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.wf-p2-title {
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  font-weight: 600;
}
.wf-p2-sub {
  margin-top: 4px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}
.wf-p2-body {
  margin-top: 8px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}
.wf-p2-line {
  margin-bottom: 6px;
}
.wf-p2-muted {
  color: var(--wb-text-caption-muted);
}
.wf-p2-warn {
  margin-top: 4px;
  color: #7a5600;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
}
.wf-tech-inline {
  margin: 6px 0;
  padding: 6px;
  background: #fff;
  border: 1px solid #eceff3;
  border-radius: 6px;
  font-size: var(--wb-font-size-caption);
  line-height: var(--wb-line-height-caption);
}
.wf-mono-small {
  margin-top: 4px;
  word-break: break-all;
  color: var(--wb-text-caption-muted);
}
.wf-p2-shap-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.wf-shap-label {
  font-weight: 600;
}
.wf-shap-select {
  min-width: 180px;
}
.wf-shap-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-top: 8px;
  width: 100%;
  box-sizing: border-box;
}

.wf-shap-grid--dual {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 720px) {
  .wf-shap-grid--dual {
    grid-template-columns: 1fr;
  }
}

.wf-shap-cell {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.wf-shap-cap {
  font-weight: 600;
  margin-bottom: 6px;
  text-align: center;
  width: 100%;
}
.wf-shap-img-wrap {
  display: flex;
  justify-content: center;
  width: 100%;
}
.wf-shap-img {
  width: 100%;
  height: auto;
  max-height: 320px;
  object-fit: contain;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
}
.wf-p3-section {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #eceff3;
  width: 100%;
  box-sizing: border-box;
}

.wf-p3-card-lead {
  margin: 10px 0 0;
  padding: 0;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
}

.wf-p2-shap-head--p3 {
  margin-top: 0;
}

.wf-p3-shap-stack .wf-p3-explanation-body {
  margin-top: 0;
}

.wf-p2-explain-title--p3 {
  margin-top: 8px;
}

.wf-p3-explanation-note-below {
  margin: 12px 0 0;
  padding: 0 8px;
  text-align: center;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}

.wf-p3-section-title {
  margin: 0;
  font-weight: 600;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
  flex: 1 1 auto;
  min-width: 0;
}

.wf-p3-explanation-body {
  margin-top: 10px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}

.wf-p3-pick {
  background: transparent;
  width: 100%;
  box-sizing: border-box;
}

.wf-p3-pick-head--split {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 16px;
  margin-bottom: 12px;
}

.wf-p3-pick-heading {
  margin: 0;
  font-weight: 600;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
  flex: 1 1 12rem;
  min-width: 0;
}

.wf-p3-pick-counts {
  margin: 0;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
  font-weight: 400;
  flex: 0 1 auto;
  text-align: right;
}

@media (max-width: 480px) {
  .wf-p3-pick-head--split {
    flex-direction: column;
    align-items: flex-start;
  }
  .wf-p3-pick-counts {
    text-align: left;
  }
}

.wf-p3-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  width: 100%;
  box-sizing: border-box;
  padding: 0;
}

@media (min-width: 560px) {
  .wf-p3-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 720px) {
  .wf-p3-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }
}

@media (min-width: 1100px) {
  .wf-p3-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.wf-p3-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin: 0;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  cursor: pointer;
  color: var(--wb-text-main);
  border: 1px solid #e8ecf2;
  border-radius: 8px;
  background: #fafbfc;
  box-sizing: border-box;
  min-width: 0;
  width: 100%;
  text-align: left;
}

.wf-p3-checkbox {
  margin: 0;
  flex-shrink: 0;
}

.wf-p3-item-body {
  display: block;
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.wf-p3-item-name-row {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 0.15em;
  row-gap: 2px;
  min-width: 0;
}

.wf-p3-item-role {
  font-size: var(--wb-font-size-caption);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
  font-weight: 400;
}

.wf-p3-item-sep {
  margin: 0 0.2em;
  color: var(--wb-text-caption-muted);
}

.wf-p3-grid-empty {
  grid-column: 1 / -1;
  padding: 8px 2px;
}

.wf-p3-pick--readonly .wf-p3-item {
  cursor: default;
}

.wf-p3-pick--readonly .wf-p3-grid {
  opacity: 0.94;
}

.wf-p3-pick--readonly .wf-p3-checkbox {
  cursor: not-allowed;
}

.wf-actions-phase3 {
  margin-top: 10px;
}

.wf-actions-phase3-readonly {
  margin-top: 8px;
  padding-top: 4px;
}
.wf-mt-sm {
  margin-top: 8px;
}
.wf-phase5-results-box {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
}
.wf-phase5-results-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.wf-phase5-results-title {
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  font-weight: 600;
}
.wf-phase5-results-body {
  margin-top: 8px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}
.wf-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.wf-actions-hint {
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}
.wf-mt {
  margin-top: 10px;
}
.wf-label {
  display: block;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  font-weight: 600;
}
.wf-input-full {
  display: block;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  margin-top: 4px;
}
.wf-check-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
}
.wf-metric-line {
  margin-left: 8px;
}

.wf-phase4-cv-missing {
  margin-top: 8px;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid #f0c9c9;
  background: #fff8f8;
  color: #7f1d1d;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.wf-phase4-cv-missing-text {
  flex: 1 1 200px;
  min-width: 0;
}

.wf-phase4-reload-btn {
  flex-shrink: 0;
}

.wf-phase5-metrics-scroll {
  overflow-x: auto;
  max-width: 100%;
}

.wf-phase5-metrics-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 420px;
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
}

.wf-phase5-metrics-table th,
.wf-phase5-metrics-table td {
  border: 1px solid #d0d7de;
  padding: 6px 10px;
  text-align: center;
  white-space: nowrap;
}

.wf-phase5-metrics-table th {
  background: #f6f8fa;
  color: var(--wb-text-body-secondary);
  font-weight: 650;
}

.wf-phase5-metrics-table td {
  font-weight: 450;
  color: var(--wb-text-main);
}

.wf-metric-primary {
  font-weight: 750 !important;
  color: #0f172a !important;
}

.wf-phase5-publish-summary {
  padding: 8px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  background: #fff;
}

.wf-phase5-publish-heading {
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  font-weight: 500;
  color: var(--wb-text-body-secondary);
}

.wf-phase5-meta-table {
  border-collapse: collapse;
  width: 100%;
  min-width: min(100%, 720px);
  font-size: var(--wb-font-size-table-cell);
  line-height: var(--wb-line-height-table);
}

.wf-phase5-meta-table th,
.wf-phase5-meta-table td {
  border: 1px solid #d0d7de;
  padding: 6px 10px;
  text-align: center;
  font-weight: 450;
  vertical-align: top;
}

.wf-phase5-meta-table th {
  background: #f6f8fa;
  color: var(--wb-text-body-secondary);
  font-weight: 650;
}

.wf-phase5-meta-table td {
  word-break: break-word;
  white-space: normal;
  min-width: 72px;
  color: var(--wb-text-main);
}

.wf-p5-feature-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.wf-p5-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: var(--wb-font-size-caption);
  line-height: var(--wb-line-height-caption);
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #1e293b;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-p5-features-toggle {
  margin-top: 6px;
}

.wf-phase5-metrics-hint {
  margin: 0 0 8px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-body-secondary);
}

.wf-phase5-charts-details {
  border: 1px solid #e5e9ef;
  border-radius: 6px;
  padding: 6px 8px;
  background: #fff;
}

.wf-phase5-charts-summary {
  cursor: pointer;
  font-weight: 650;
  color: var(--wb-text-body-secondary);
}

.wf-phase5-charts-grid {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.wf-phase5-chart-cell {
  min-width: 280px;
  max-width: 420px;
  flex: 1 1 300px;
}

.wf-phase5-chart-cap {
  font-weight: 600;
  margin-bottom: 4px;
}

.wf-phase5-chart-img {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.wf-p2-explain-title {
  margin: 10px 0 4px;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  font-weight: 600;
  color: var(--wb-text-main);
}

.wf-p2-shap-scope-hint {
  margin: 0 0 8px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}

.wf-p2-shap-missing {
  margin-top: 4px;
}

.workflow-card--embedded {
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
  margin-top: 0;
}

.workflow-card--embedded .wf-p2-box {
  margin-top: 12px;
  padding: 12px 0 0;
  border: none;
  border-top: 1px solid #eceff3;
  background: transparent;
  border-radius: 0;
}

.workflow-card--embedded .wf-layer {
  padding: 8px 0;
  border: none;
  background: transparent;
}

.workflow-card--embedded .wf-p3-pick {
  margin-top: 14px;
  padding-top: 12px;
  padding-left: 0;
  padding-right: 0;
  border: none;
  border-top: 1px solid #eceff3;
  border-radius: 0;
  background: transparent;
}

.workflow-card--embedded .wf-p3-item:not(.wf-p3-item--locked) {
  background: #fff;
}

.workflow-card--embedded .wf-p3-item.wf-p3-item--locked {
  background: #fff8f4;
  border: 1px solid #edd5c8;
  color: var(--wb-text-main);
}

.workflow-card--embedded .wf-phase5-publish-summary,
.workflow-card--embedded .wf-phase5-results-box {
  border: none;
  padding: 0;
  background: transparent;
}

.workflow-card--embedded .wf-phase5-charts-details {
  border: 1px solid #e5e9ef;
  background: #fff;
}

.wf-p3-summary-block {
  margin-top: 10px;
}

.wf-p3-card-lead--conclusion {
  margin: 0;
  font-weight: 500;
}

.wf-p3-card-lead--tight {
  margin-top: 10px;
}

.wf-p3-shap-guide {
  margin: 0 0 12px;
  padding: 0;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
}

.wf-p3-pick-legend {
  margin: 0 0 12px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-caption-muted);
}

.wf-p3-panel {
  margin-top: 12px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid #e8ecf2;
  box-sizing: border-box;
}

.wf-p3-panel--required {
  background: #fff7ed;
  border-color: #fed7aa;
}

.wf-p3-panel--optional {
  background: var(--wb-surface, #fff);
}

.wf-p3-panel-title {
  font-weight: 700;
  font-size: var(--wb-font-size-card-body);
  line-height: var(--wb-line-height-card);
  color: var(--wb-text-main);
  margin: 0 0 6px;
}

.wf-p3-panel-note {
  margin: 0 0 10px;
  font-size: var(--wb-font-size-card-meta);
  line-height: var(--wb-line-height-caption);
  color: var(--wb-text-body-secondary);
}

.wf-p3-subpanel {
  margin-top: 12px;
}

.wf-p3-subpanel:first-of-type {
  margin-top: 0;
}

.wf-p3-subpanel-title {
  font-weight: 650;
  margin: 0 0 8px;
  font-size: var(--wb-font-size-sm);
  color: var(--wb-text-body-secondary);
}

.wf-p3-grid--panel {
  margin-top: 0;
}

.wf-p3-item--locked {
  cursor: default;
  background: #fff8f4;
  border: 1px solid #edd5c8;
  color: var(--wb-text-main);
  box-shadow: none;
}

.wf-p3-item--locked .wf-feat-pri {
  color: var(--wb-text-main);
}

.wf-p3-item--locked .wf-p3-checkbox,
.wf-p3-checkbox--locked {
  cursor: not-allowed;
  accent-color: var(--wb-running, #c58b49);
}

.wf-actions-phase5-release {
  flex-wrap: wrap;
}
</style>

