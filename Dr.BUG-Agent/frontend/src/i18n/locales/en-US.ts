const enUS = {
  predictionPresentation: {
    labels: {
      predictedLabel: "Predicted label",
      predictedProbability: "Predicted probability",
      clinicalConclusion: "Clinical conclusion",
      likelyHigherOutcome: "Likely higher-probability outcome",
      likelyLowerOutcome: "Likely lower-probability outcome",
      predictedValueLine: "Predicted value: {value}",
      predictedTreatmentDuration: "Predicted treatment duration: {days} days",
      na: "—",
    },
    outcomeLabels: {
      mortalitySurvival: "Survival",
      mortalityNonSurvival: "Death",
      clinicalImprovement: "Improvement",
      clinicalFailure: "Failure",
      resistanceResistant: "Resistant",
      resistanceSusceptible: "Sensitive",
    },
    boolean: {
      yes: "Yes",
      no: "No",
    },
    taskList: {
      batchCounts: "Total {total}; succeeded {succeeded}",
    },
    batch: {
      columnAlignmentSummary: "Column alignment: matched {matched} · missing {missing} · extra {extra}",
    },
  },
  workspace: {
    status: {
      idle: "Idle",
      noActiveTask: "No active tasks at the moment.",
      running: "Running",
      runningInBackground: "Running in the background",
      waitingConfirmation: "Waiting for confirmation",
      queued: "Queued",
      completed: "Completed",
      trainingCompleted: "Training completed",
      failed: "Failed",
      canceled: "Canceled",
      pendingInput: "Pending input",
      readyToExecute: "Ready to execute",
      batchPredictionRunningDesc: "Generating the batch prediction result file in the background.",
      regimenComparisonRunningDesc: "Scoring candidate regimens and estimating survival probabilities under the selected model.",
      singlePredictionRunningDesc: "Computing the single-patient prediction.",
      nearCompletionDesc: "The task is close to completion and is finalizing.",
      genericRunningDesc: "The current task is running in the background.",
      trainingWaitingConfirmDesc:
        "Current stage: {title}. This is waiting for your confirmation in the main card area (not running in the backend).",
      genericWaitingConfirmDesc: "Please confirm the next step in chat or the relevant task card.",
      startedProcessingDesc: "The task has started processing.",
      queuedDesc: "The task has been created and is waiting to be scheduled.",
      trainingCompletedDesc: "Review the result summary and release status.",
      completedDesc: "The task is completed. You can review the result.",
      completedRegimenComparisonDesc:
        "Regimen recommendation completed. Review ranked regimens and model estimates in the chat result card.",
      failedDesc: "The task failed. Review the summary and diagnostics under Tasks.",
      canceledDesc: "The task has been canceled or interrupted.",
      readyToExecuteDesc: 'The model and fields are ready. Click "Confirm and execute" in the prediction workspace.',
      pendingInputDesc:
        "Continue in the prediction workspace: choose a prediction task, select a released model for that task, then fill the required fields.",
      batchPendingInputDesc:
        "Choose a prediction task and a released model, then upload a data table and complete the column check in the prediction workspace.",
    },
  },
  nav: {
    brandTitle: "Dr.BUG",
    brandSubtitle: "",
    newSession: "New session",
    navigation: "Navigation",
    sessions: "Sessions",
    emptySessions: "No sessions yet",
    workbench: "Workbench",
    tasks: "Tasks",
    datasets: "Data management",
    models: "Model library",
    history: "Prediction records",
    language: "Language",
    languageZh: "Chinese",
    languageEn: "English",
    /** Native-language label for zh segment; intentional CJK for language switcher (scan allowlist). */
    langToggleZh: "中文",
    langToggleEn: "EN",
  },
  predictionFailure: {
    invalidInput:
      "The submitted input is incomplete or invalid. Please check the required fields and try again.",
    modelTaskMismatch:
      "The selected model is not available for this prediction task. Please choose a compatible model and try again.",
    executionFailed:
      "The prediction could not be completed. Please check the model, input data, and backend service, then try again.",
  },
  prediction: {
    explanation: {
      briefInterpretation: "Brief interpretation",
      /** @deprecated Retained for compatibility; English UI now uses summaryEnglish* keys below. */
      summaryLocaleMismatch:
        "This interpretation text was generated in Chinese. Switch the interface language to Chinese to read it in full.",
      summaryEnglishStructuredIntro:
        "The model prediction was mainly influenced by the main contributing variables listed below. The original free-text explanation was generated in another language, so only the structured variable summary is shown here.",
      summaryEnglishStructuredPointer:
        "Refer to the Main contributing variables section on this card for the ranked inputs.",
      summaryEnglishNoStructuredFallback:
        "A localized free-text interpretation is not available for this result. Please review the predicted label, probability, and other structured fields shown on this card.",
      defaultCollapsedHint: "",
      /** @deprecated Visible heading removed; use predictionResultAriaLabel for accessibility. */
      predictionResultHeading: "Prediction result",
      predictionResultAriaLabel: "Prediction result",
      variablesHandledByPreprocessing: "Variables handled by preprocessing",
      /** @deprecated Use variablesHandledByPreprocessing */
      dataPreprocessingNotes: "Variables handled by preprocessing",
      /** @deprecated Use variablesHandledByPreprocessing */
      modelReminders: "Variables handled by preprocessing",
      variablesHandledSeveralEn:
        "Several input variables were missing and were handled by the model preprocessing pipeline: {variables}.",
      variablesHandledOneEn:
        "One input variable was missing and was handled by the model preprocessing pipeline: {variable}.",
      preprocessingTruncatedWarningsEn: "{count} additional missing-variable reminders were omitted.",
      preprocessingGenericFallbackEn:
        "Some input variables were missing and were handled by the model preprocessing pipeline.",
      preprocessingExplanationSkippedNoModel:
        "Per-sample explanation was skipped because the prediction context did not include a loaded model pipeline.",
      preprocessingBatchModeNoShap:
        "Per-sample SHAP explanation is disabled for batch prediction runs to keep execution time predictable.",
      preprocessingShapPlotExportFailed:
        "SHAP values were computed but exporting explanation plots failed. Check server logs if you need details.",
      preprocessingExplanationFailed:
        "Generating the per-sample explanation failed. Check server logs if you need details.",
      preprocessingShapNotInstalled:
        "SHAP is not installed in this runtime environment, so per-sample explanation is unavailable.",
      preprocessingShapUnsupportedModelType:
        "This model type does not support per-sample SHAP explanations (tree-based models are required).",
      preprocessingShapComputationFailed: "SHAP computation failed for this sample. Check server logs if you need details.",
      preprocessingBatchNonNumericEn:
        'Column "{feature}" does not appear to be numeric in the uploaded file.',
      preprocessingBatchBinarySuspectEn:
        'Column "{feature}" may not be binary; confirm allowed values before interpreting results.',
      mainContributingVariables: "Main contributing variables",
      /** @deprecated Use mainContributingVariables */
      topFeatures: "Main contributing variables",
      chartsTitle: "Model explanation charts",
      chartsCollapsedHint: "",
      chartsFootnote: "",
      fieldLabelsWithAxis: "",
      waterfallCaption: "Variable contribution (waterfall)",
      reportSummary: {
        predictionCompletedSentence: "Prediction completed.",
        classificationLeadProb:
          "{lead} The model predicted {label} with a probability of {probability}.",
        classificationLeadNoProb: "{lead} The model predicted {label}.",
        regressionLeadProb: "{lead} {conclusion} Predicted probability: {probability}.",
        regressionLeadNoProb: "{lead} {conclusion}",
        varsClause: "The main variables contributing to this prediction were {variables}.",
        waterfallTail:
          "The waterfall plot below shows how individual variables increased or decreased the model output for this patient.",
      },
      waterfallPlotExplainer:
        "Shows how individual variables increased or decreased the model output for this patient.",
      waterfallAlt: "Waterfall plot of variable contributions",
      forceCaption: "Variable influence (force plot)",
      forcePlotExplainer:
        "Summarizes the variables pushing the prediction towards higher or lower model output.",
      forceAlt: "Force plot of variable influence",
      noChartsHint:
        "No explanation figures were returned for this prediction. Review the predicted label, probability, and main contributing variables on this card.",
      individualExplanation: "Individual result explanation",
      singleExplanationNotReady:
        "Per-sample explanation is not enabled for this model, or the explanation is not ready yet.",
      noExtraExplanation: "No additional explanation information.",
      nextStep: "Suggested follow-up",
      lightboxAlt: "Enlarge view",
      nextStepRegression:
        "Interpret the value using your unit's usual thresholds; for multiple patients, switch to batch prediction in the prediction workspace.",
      nextStepNonRegression:
        "“Recent single-patient prediction” on the right keeps the same conclusion summary as this card; for batch jobs, see history or the batch result card.",
    },
    batchResult: {
      uploadedTable: "Uploaded table",
      totalRecords: "Total records",
      succeeded: "Succeeded",
      failed: "Failed",
      downloadResults: "Download prediction result file",
      noDownloadLink: "No download link available",
    },
    workspace: {
      selectTaskFirst: "Choose a prediction task first.",
      selectModelFirst: "Select a released model for this task.",
      uploadPatientTable: "Select and upload a patient data table (CSV / Excel).",
      datasetContextPrefix: "Dataset: {name}",
    },
    batchWorkspace: {
      checkPassed: "Column check passed",
      checkFailed: "Column check failed",
      checkNotRun: "Column names not checked yet",
      runNeedCheckColumns:
        'Click "Check column names" first and align the table with the model requirements before running.',
      runMissingRequiredColumns:
        "Required columns required by the model are still missing; batch prediction cannot run. Fix column names or data using the check result and try again.",
    },
    narrative: {
      intentRecognized: {
        survival:
          "I recognized that you want to run a survival prediction. Please confirm the task and model below, then enter the patient variables and execute the prediction. Patient data is used only for this prediction and is not sent to the language model.",
        efficacy:
          "I recognized that you want to run a clinical efficacy prediction. Please confirm the task and model below, then enter the patient variables and execute the prediction. Patient data is used only for this prediction and is not sent to the language model.",
        resistance:
          "I recognized that you want to run a polymyxin resistance prediction. Please confirm the task and model below, then enter the patient variables and execute the prediction. Patient data is used only for this prediction and is not sent to the language model.",
        duration:
          "I recognized that you want to run a treatment duration prediction. Please confirm the task and model below, then enter the patient variables and execute the prediction. Patient data is used only for this prediction and is not sent to the language model.",
      },
      workspaceOpenedAssistant:
        "I’ve opened the prediction workspace. Choose a prediction task and a released model, then run a single-patient or batch prediction. Patient data is used only for this prediction and is not sent to the language model.",
      batchCompletedAssistant:
        "Batch prediction finished. You can download the result file to review record-level predictions.",
      singlePredictionFailed: "Prediction did not succeed: {message}",
      exitWorkspaceHint:
        "Prediction workspace closed. If you already have results, you can still review them under Recent single-patient prediction / Recent batch prediction on the right.",
      noWorkspaceForExecuteHint:
        "No active prediction workspace. Send “predict”, “I want to predict”, or “batch prediction” to open the workspace, fill the card, then confirm.",
      draftSingleUseWorkspaceHint:
        'Use the prediction workspace below: confirm the task and model, enter patient data, then click “Confirm and execute”. Patient data is used only for this prediction and is not sent to the language model.',
    },
  },
  task: {
    resultCard: {
      viewTrainingCharts: "View training charts",
      presentation: {
        taskType: "Task type",
        taskName: "Task name",
        dataset: "Dataset",
        model: "Model",
        featureCount: "Feature count",
        primaryMetric: "Primary metric",
        publishStatus: "Release status",
        published: "Published",
        notPublished: "Not published",
        publishUnknown: "Unknown",
        unnamedTask: "Untitled training task",
        datasetUnknown: "Not specified",
        mlBinary: "Binary classification",
        mlMulticlass: "Multiclass classification",
        mlRegression: "Regression",
        inputFeaturesTitle: "Input features ({count})",
        expandAllFeatures: "Show all features",
        collapseAllFeatures: "Show fewer features",
      },
      keyMetrics: "Key metrics",
      collapseDetails: "Collapse result details",
      expandFullResult: "View full result",
      technicalDetails: "Technical details",
      resultSummaryBold: "Result summary: ",
      artifactsBold: "Outputs: ",
      artifactsBody: "{count} files attached to this run (see Technical details).",
      representativeChart: "Representative chart",
      noChartFallback: "No chart to display; showing metrics and text summary instead.",
      viewReleasedModel: "Open model summary",
      goTaskErrors: "Review setup",
      goTaskDetails: "Open Tasks",
      trainingReceipt: {
        badgeTrainingCompleted: "Training completed",
        badgePublished: "Published",
        badgeNotPublished: "Not published",
        badgePublicationUnknown: "Release status unclear",
        badgeReadyForPrediction: "Ready for prediction",
        clinicalEfficacyTaskName: "clinical efficacy prediction",
        taskNameFallback: "this training task",
        datasetFallback: "the selected dataset",
        algorithmFallback: "the selected model",
        metricNameF1: "F1-score",
        otherMetricsUnavailable: "Other final metrics were not available",
        metricListJoiner: "; ",
        featureJoiner: ", ",
        featureAmongOthersSuffix: ", among others",
        bodyP1Published:
          "Training was completed successfully. Using the dataset {dataset_name}, Dr.BUG trained and released a {algorithm} model for {task_name} to the model registry. During feature selection, a compact {feature_count}-feature set was used for final modelling, consisting of {feature_list}.",
        bodyP1NotPublished:
          "Training was completed successfully. Using the dataset {dataset_name}, Dr.BUG trained and saved a {algorithm} model for {task_name} without releasing it to the registry. During feature selection, a compact {feature_count}-feature set was used for final modelling, consisting of {feature_list}.",
        bodyP1Unknown:
          "Training was completed successfully. Using the dataset {dataset_name}, Dr.BUG finished training a {algorithm} model for {task_name}. During feature selection, a compact {feature_count}-feature set was used for final modelling, consisting of {feature_list}.",
        bodyP2PrimaryEvalBefore: "In the final evaluation, ",
        bodyP2PrimaryEvalBetween: " was the primary metric and reached ",
        bodyP2PrimaryEvalAfter: ".",
        bodyP2OtherAchieved: " The model also achieved {other_metric_list}.",
        bodyP2OtherNone:
          " No additional final metrics were reported beyond the primary metric.",
        shapBeeswarmTitle: "SHAP beeswarm plot",
        shapBeeswarmTitleForModel: "SHAP beeswarm plot for {model}",
        shapBeeswarmTitleForPublishedModel: "SHAP beeswarm plot for the released {model} model",
        shapBeeswarmTitleForTrainedModel: "SHAP beeswarm plot for the trained {model} model",
        shapBeeswarmTitleForFinalModelUnknown: "SHAP beeswarm plot for the final {model} model",
        shapUnavailablePublishedModel: "SHAP explanation is not available for the released model in this run.",
        shapUnavailableTrainedModel: "SHAP explanation is not available for the trained model in this run.",
        shapUnavailableFinalModelUnknown:
          "SHAP explanation is not available for the final model in this run. Open Tasks to review saved outputs.",
        shapAttributionSentence:
          "The SHAP beeswarm plot below provides a model-based view of how the selected features contributed to the prediction output; it should not be interpreted as causal evidence.",
        bodyP2TailPublished:
          "The model has been released to the model registry and is now available for matching prediction workflows.",
        bodyP2TailNotPublished:
          "The trained model was saved as training output and will not appear in prediction model selectors unless you release it later.",
        bodyP2TailUnknown: "Open Tasks to confirm release status and review saved outputs.",
        candidateCvComparisonTitle: "Candidate model comparison under default-parameter cross-validation",
        candidateCvComparisonHint:
          "These results compare candidate algorithms under default-parameter cross-validation and are shown as model-selection context, not as the final trained model metrics.",
        candidateCvComparisonLoadFailed:
          "Candidate model comparison could not be loaded from task artifacts. You can still review metrics under Tasks.",
        viewDetails: "View details",
      },
      actions: {
        reviewSetup: "Review setup",
        reviewPerformance: "Review performance",
        downloadReport: "Download report",
        publishModel: "Release model",
        openModelSummary: "Open model summary",
        startPrediction: "Start prediction",
        viewPredictionReport: "View prediction report",
        reviewRankedRegimens: "Review ranked regimens",
        exportSummary: "Export summary",
        openReport: "Open report",
      },
      tech: {
        jobId: "Task ID",
        jobType: "Job type",
      },
    },
  },
  recommendation: {
    narrative: {
      workspaceEnteredAssistant:
        "I’ve opened the regimen recommendation workspace. Pick a published survival-outcome model to load the patient feature table; Dr.BUG will rank candidate regimens from the regimen library as model-based decision support, not as prescribing guidance.",
      noSurvivalModelsError:
        "No survival/outcome-compatible models are available (or schema is missing). Please publish a compatible survival model.",
      defaultCompletedTitle: "Regimen recommendation",
      completedArtifactMissing: "Regimen recommendation finished, but the structured result could not be read.",
    },
  },
  regimen: {
    management: {
      loadFailedBold: "Load failed",
      loadFailedColon: ": ",
      retry: "Retry",
      refreshList: "Refresh list",
      refreshing: "Refreshing…",
      newRegimen: "New regimen",
      defaultNewRegimenPrefix: "New regimen",
      saveValidationHuman:
        "Could not save regimen. Please check the regimen name and dosing fields.",
      listSectionTitle: "Regimens",
      listCount: "Total {count}",
      toolbarHint:
        "Maintain candidate regimens for the individualized recommendation flow. Empty numbers are submitted as 0; regimen IDs are generated by the system.",
      formTitleNew: "New regimen",
      formTitleEdit: "Edit regimen",
      labels: {
        regimenName: "Regimen name",
        notes: "Notes",
        enabled: "Enabled",
      },
      numericSectionTitle: "Composition and dosing",
      groups: {
        polymyxins: "Polymyxins",
        combination: "Combination agents",
      },
      units: {
        freqPerDay: "times/day",
        doseG: "g/day",
      },
      save: "Save",
      saveRegimen: "Save regimen",
      saving: "Saving…",
      cancel: "Cancel",
      empty: "No regimens yet. Click “New regimen” to add the first one.",
      loading: "Loading…",
      unnamed: "Unnamed regimen",
      statusEnabled: "Enabled",
      statusDisabled: "Disabled",
      edit: "Edit",
      delete: "Delete",
      internalIdLead: "Internal ID:",
      internalIdFoot: "Internal ID",
      requestFailed: "Request failed",
      saveFailed: "Save failed",
      deleteFailed: "Delete failed",
      deleteConfirm: 'Delete regimen "{name}"? This cannot be undone.',
    },
    rightPanel: {
      emptyHint: "Select a regimen from the list to view details and actions.",
      sections: {
        summary: "Regimen summary",
        composition: "Composition and dosing",
        actions: "Actions",
      },
      summaryLabels: {
        name: "Name",
        status: "Status",
        regimenId: "Regimen ID",
        notes: "Notes",
        createdAt: "Created",
        updatedAt: "Updated",
      },
      labels: {
        regimenName: "Regimen name",
        notes: "Notes",
        enabled: "Enabled",
        internalId: "Internal ID",
        regimenId: "Regimen ID",
        createdAt: "Created:",
        updatedAt: "Updated:",
      },
      unnamed: "Unnamed regimen",
      statusEnabled: "Enabled",
      statusDisabled: "Disabled",
      noNotes: "No notes yet",
      activeNonZeroDoses: "Active (non-zero) doses",
      zeroDoseItems: "Zero-dose items",
      noActiveDoses: "No active non-zero doses.",
      doseDisplay: {
        freqPerDay: "{value} times/day",
        doseG: "{value} g/day",
      },
      actions: {
        editRegimen: "Edit regimen",
        disableRegimen: "Disable",
        enableRegimen: "Enable",
        disabling: "Disabling…",
        enabling: "Enabling…",
      },
      toggleFailed: "Could not update regimen status.",
      saveChanges: "Save changes",
      saving: "Saving…",
      saveFailed: "Save failed",
    },
    treatmentDisplay: {
      lineDailyFreq: "{label}, daily frequency: {value}",
      lineDailyDose: "{label}, daily dose: {value}",
      clinicalFreqLine: "{label}: frequency {value} times/day",
      clinicalDoseGLine: "{label}: dose {value} g/day",
      compactFreq: "{label}: {value} times/day",
      compactDose: "{label}: {value} g/day",
      compactSep: " · ",
      fields: {
        colistin_cms_daily_freq: {
          shortLabel: "CMS",
          formLabel: "CMS daily dosing frequency",
        },
        polymyxin_b_daily_freq: {
          shortLabel: "Polymyxin B",
          formLabel: "Polymyxin B daily dosing frequency",
        },
        colistin_sulfate_daily_freq: {
          shortLabel: "Colistin sulfate",
          formLabel: "Colistin sulfate daily dosing frequency",
        },
        carbapenem_daily_dose: {
          shortLabel: "Carbapenem",
          formLabel: "Carbapenem daily dose",
        },
        sulbactam_daily_dose: {
          shortLabel: "Sulbactam",
          formLabel: "Sulbactam daily dose",
        },
        tigecycline_daily_dose: {
          shortLabel: "Tigecycline",
          formLabel: "Tigecycline daily dose",
        },
        minocycline_daily_dose: {
          shortLabel: "Minocycline",
          formLabel: "Minocycline daily dose",
        },
        vancomycin_daily_dose: {
          shortLabel: "Vancomycin",
          formLabel: "Vancomycin daily dose",
        },
        eravacycline_daily_dose: {
          shortLabel: "Eravacycline",
          formLabel: "Eravacycline daily dose",
        },
        aminoglycoside_daily_dose: {
          shortLabel: "Aminoglycoside",
          formLabel: "Aminoglycoside daily dose",
        },
      },
    },
  },
  training: {
    narrative: {
      waitingIntroFeatureConfirm:
        "Feature screening is complete. Review the results and confirm the final feature set before model training continues.",
      waitingIntroModelSetup: "Choose the model and training settings in the card below.",
      waitingIntroPublish:
        "The final model is ready for review. Check the metrics below, then decide whether to release it to the model registry.",
      precheckFailedWithReason: "Training pre-check did not finish: {reason}",
      precheckFailedDefault: "Training pre-check failed",
      receiptTitleCreated: "Model training created",
      receiptTaskKindLabel: "Model training",
      receiptNextHint: "When prompted, confirm the final input features in the workflow card below.",
      trainingCreatedStatusBubble: "I've received your model-training request. Please review the setup below.",
      trainingCreatedStatusBubbleScreening:
        "I've received your model-training request. Dr.BUG will prepare the selected dataset and candidate features before asking you to confirm the final feature set.",
    },
    receiptCard: {
      technicalDetails: "Technical details",
      internalJobId: "Internal job ID",
      taskKind: "Task kind",
      introAriaLabel: "What happens next in model training",
      introP1:
        "Training task created. Dr.BUG is preparing the selected inputs and running feature screening.",
      introP2: "",
      introP3: "",
      progressNoteBold: "Progress: ",
      progressFeatureScreening:
        "Feature screening is in progress. Please review the data preview below. You will be asked to confirm the final input features before training continues.",
      progressTrainingPrep:
        "Training is being prepared. Please review the selected features and outcome label before training continues.",
      previewHeading: "Data preview: selected features and outcome",
      previewScaleSelectedFeatures: "Scale: About {n} rows · {featureCount} selected features + outcome",
      previewScaleCandidate: "Scale: About {n} rows · {featureCount} selected features + outcome",
      previewScaleCandidateNoRequired:
        "Scale: About {rowCount} rows · {selectedCount} selected features + outcome",
      previewScaleCandidateWithRequired:
        "Scale: About {rowCount} rows · {selectedCount} selected features + {requiredCount} required features + outcome",
      previewScaleConfirmed: "Scale: About {n} rows · {featureCount} confirmed features + outcome",
      previewLoading: "Loading data preview…",
      rowsCols: "Scale: ",
      previewRowsColsValue: "About {rows} rows · {cols} columns",
      targetColumn: "Outcome column:",
      numericCategoricalCols: "Numeric / categorical columns:",
      missingOverviewTop: "Missing values (top): ",
      labelDistribution: "Label distribution:",
      summarySelectedFeatureCountWithLocked:
        "{count} selected input features in this request, including {lockedCount} locked variables.",
      summarySelectedFeatureCountNoLocked: "{count} selected input feature(s) in this request.",
      noPreview: "No data preview available.",
      missingDatasetId: "Dataset is missing; cannot load data preview.",
    },
    labelDistribution: {
      clinical: {
        line: "Label distribution: improvement {pos}, non-improvement {neg}",
      },
      survival: {
        line: "Label distribution: survived {survived}, died {died}",
      },
      resistance: {
        line: "Label distribution: resistant {resistant}, non-resistant {nonResistant}",
      },
      fallback: {
        line: "Label distribution: {body}",
        sep: "; ",
        classSamples: "Class {cls}: {count} samples",
      },
    },
    schemas: {
      groups: {
        data_task: "Data & task",
        feature_columns: "Features & columns",
        advanced: "Advanced settings",
        publish: "Release & notes",
      },
      fields: {
        dataset_id: {
          label: "Dataset",
          description: "Training dataset selected from your library.",
        },
        clinical_task_id: {
          label: "Clinical task",
          description: "",
        },
        ml_task_type: {
          label: "Machine learning task type",
        },
        target_column: {
          label: "Target column",
          description: "Outcome column from the dataset.",
        },
        feature_set: {
          label: "Named feature group (optional)",
          description: "",
        },
        selected_features: {
          label: "Candidate feature pool",
          description: "Select variables to enter the feature-screening pool.",
        },
        final_features: {
          label: "Final modeling columns",
          description: "Maps to Streamlit final_features; when non-empty it is semantically preferred",
        },
        med_cols: {
          label: "Locked variables",
          description: "Locked variables are always included in model training.",
        },
        model_type: {
          label: "Model type",
        },
        model_name: {
          label: "Model display name",
          description: "Optional; runtime may map this to an exact model name",
        },
        objective_metric: {
          label: "Primary metric",
        },
        primary_metric: {
          label: "Primary metric (override)",
          description: "Optional; when blank it aligns with objective_metric",
        },
        enable_feature_set_search: {
          label: "Enable feature-set search",
          description: "",
        },
        min_features: {
          label: "Minimum features",
        },
        max_features: {
          label: "Maximum features",
        },
        enable_search: {
          label: "Enable hyperparameter search",
        },
        use_cv_shap: {
          label: "CV-SHAP",
          description: "",
        },
        index_time: {
          label: "Index time",
          description: "Optional cohort indexing timestamp column name.",
        },
        label_time: {
          label: "Label time",
          description: "Optional outcome labeling timestamp column name.",
        },
        publish_overrides_model_id: {
          label: "Release model ID",
        },
        publish_overrides_notes: {
          label: "Release notes",
        },
      },
      options: {
        clinical_task: {
          mortality_28d: "Survival outcome",
          clinical_efficacy: "Clinical efficacy",
          polymyxin_resistance: "Polymyxin resistance",
          treatment_duration: "Treatment duration",
        },
        ml_task_type: {
          binary: "Binary classification",
          multiclass: "Multiclass classification",
          regression: "Regression",
        },
        model_type: {
          xgboost: "XGBoost",
          lightgbm: "LightGBM",
          catboost: "CatBoost",
          random_forest: "Random Forest",
          logistic_regression: "Logistic Regression",
          svm: "SVM",
          knn: "KNN",
        },
      },
      placeholders: {
        feature_set: "Leave blank or e.g. cand16",
        index_time: "Optional; blank becomes null",
        label_time: "Optional; blank becomes null",
        publish_model_id: "Optional",
        publish_notes: "Optional; multi-line notes supported",
      },
      tooltips: {
        clinical_task_id: "Pick the outcome family that matches your dataset labeling.",
        ml_task_type:
          "Inferred from the clinical task by default (for example survival and resistance tasks use binary classification; treatment duration uses regression). You can override it before training.",
        selected_features:
          "These variables can be screened and selected during feature-set search. If feature-set search is disabled, selected variables are used directly for model training.",
        med_cols:
          "Use this section for variables that must remain in the model input, such as clinically required treatment variables or predefined covariates.",
        enable_feature_set_search:
          "Search across feature subsets within the minimum and maximum size you set (slower, more exploratory).",
        use_cv_shap:
          "Cross-validated SHAP summaries for interpretability; takes longer but produces standardized explanation plots.",
      },
    },
    validation: {
      fieldLabels: {
        dataset_id: "Dataset",
        clinical_task_id: "Clinical task",
        ml_task_type: "Machine learning task type",
        target_column: "Target column",
        model_type: "Model type",
        objective_metric: "Primary metric",
        feature_source: "Feature configuration (pool, search, or explanation options)",
        feature_set: "Named feature group",
        selected_features: "Candidate feature pool",
        final_features: "Final modeling columns",
        med_cols: "Locked variables",
        min_features: "Minimum features",
        max_features: "Maximum features",
      },
      errors: {
        missingRequired: "Missing required: {field}",
        featureSourceRequired:
          "Insufficient feature source: add final modeling columns, a candidate pool, or a named group—or enable feature-set search or CV-SHAP (locked variables alone are not enough).",
        minMaxFeatureOrder:
          "Feature-set search is on: minimum features cannot exceed maximum features.",
        targetNotInSchema: "Target column is not in the current dataset schema—please pick again.",
        columnsNotInSchema: "{fieldLabel} lists columns not present in the current schema: {columns}",
      },
      warnings: {
        featBounds:
          "Feature counts are near or outside the usual contract range (1–20); please confirm this is intended.",
        schemaFail:
          "Dataset columns failed to load: target and feature columns cannot be validated against the schema automatically—manual entry errors are possible.",
        schemaLoading:
          "Columns are loading: once ready, target and selected features will be checked against the dataset.",
        featPriority:
          "Both final modeling columns (final_features) and a named feature group (feature_set) are set: semantics prefer final columns; execution order follows the backend.",
        poolOnly:
          "Candidate pool (selected_features) is set but final modeling columns are empty: this reflects a pool only, not the final training column plan.",
        poolOnlyPhase1:
          "Candidate pool is filled; the system will recommend final modeling columns after screening, and you will confirm them in chat before training.",
        primaryDefault:
          "Primary metric override (primary_metric) is blank: after submit it aligns with objective_metric (per current contract).",
        modelNameEmpty:
          "Model display name (model_name) is empty: the executor may map from model_type.",
        publishSkip:
          "No optional release overrides were set; this does not block submitting the training job.",
      },
      groupStatus: {
        error: "[Missing/errors]",
        warn: "[Warnings]",
        optional: "[Optional]",
        ok: "[Done]",
      },
    },
  },
  taskNarrative: {
    trainingStage: {
      datasetValidation: "Validating dataset and training parameters",
      phase2: "Selecting candidate modeling features",
      phase3: "Preparing final features and training configuration",
      phase4: "Training the model and generating reports",
      phase5: "Handling release-related steps",
      modelTraining: "Starting model training",
      evaluation: "Summarizing training results",
    },
    whatItIs: {
      training: "Model training",
      generic: "Background task",
    },
    companion: {
      queued: "Received by the system. It will start shortly.",
      canceled: "This task was stopped and no new results will be produced.",
      predict: {
        waitingUser: "Waiting for you to confirm parameters or fill required fields in the workspace",
        failed: "The prediction did not finish successfully. Please check the details and logs.",
      },
      predictSingle: {
        running: "Computing a single-patient prediction with the selected model",
        completed: "The result is ready. See the result card or Prediction / Report History.",
      },
      predictBatch: {
        running: "Computing predictions for each row of the uploaded table",
        completed: "The result file is ready. Download it in task details or view it in Prediction / Report History.",
      },
      recommend: {
        running: "Scoring ranked regimen alternatives",
        completed: "Ranked alternatives are ready. Review them in the result card or task summary.",
        waitingUser: "Waiting for you to confirm recommendation inputs in chat or the card",
        failed: "The recommendation did not finish successfully. Open task details for the error summary.",
      },
      shap: {
        running: "Generating SHAP explanations and related artifacts",
        completed: "Explanation artifacts are ready. View or download them in task details.",
        failed: "The explanation task failed. Please check task details and logs.",
      },
      report: {
        running: "Generating report content and attachments",
        completed: "The report is ready. Open or download it in task details.",
        failed: "The report task failed. Please check task details and logs.",
      },
      generic: {
        running: "Processing",
        completed: "The results are ready. Open task details to view outputs.",
        waitingUser: "Waiting for you to confirm the next step in chat or a task-related screen",
        failed: "Please open task details to review the reason and logs.",
      },
      trainingWaitingConfirm: "Waiting for confirmation (not running in the backend). Current: {title}.",
      trainingRunningWithStage: "Running in the backend: {stage}",
      trainingRunning: "Running in the backend",
      trainingReleased: "Released",
      trainingNotReleased: "Not released",
      trainingCompletedHeadline: "{headline} ({release})",
      trainingCompletedFallback: "Training completed ({release}). See task details and the result card.",
    },
    whereItStands: {
      waitingUserFallback: "Waiting for confirmation",
      queued: "Received by the system. It will start shortly.",
      runningFallback: "Processing",
      trainingCompleted: "Review the summary, artifacts, and whether it has been released.",
      canceled: "This task was stopped and no new results will be produced.",
    },
    progress: {
      completedFallback: "Open task details to review the record and next actions.",
      runningFallback: "Processing. Check task details for progress and logs.",
      queuedFallback: "Queued. Please refresh later to view progress.",
    },
  },
  taskPresentation: {
    status: {
      queued: "Queued",
      running: "Running",
      waitingUser: "Waiting for input",
      completed: "Completed",
      failed: "Failed",
      canceled: "Canceled",
    },
    jobType: {
      train: "Model training",
      predict: "Personalized prediction",
      shap: "Model explanation",
      recommend: "Regimen recommendation",
      report: "Report generation",
      publish: "Model release",
    },
    predictionTitle: {
      single: "Single-patient prediction",
      batch: "Batch prediction",
    },
    featureSource: {
      finalFeatures: "final_features: {count} columns",
      selectedFeatures: "selected_features: {count} columns",
      separator: "; ",
    },
    failureFallback: {
      noBackendReason: "Failed. No detailed reason was returned by the backend.",
    },
  },
  taskTerminal: {
    completion: {
      train: "Training finished. Review metrics and outputs when you are ready.",
      predictSingle: "Single-patient prediction finished. Review the result card and prediction history if needed.",
      predictBatch: "Batch prediction finished. Download or inspect the table from the card below.",
      recommend:
        "Regimen recommendation finished. Review ranked regimen alternatives—this is model-based ranking for clinical follow-up, not a treatment directive.",
      shap: "Explanation task finished. Review exported summaries from the task panel when needed.",
      report: "Report generation finished. Open the task summary for attachments.",
      generic: "Task finished. Review the summary in Tasks.",
    },
    failurePrefix: {
      train: "The training workflow could not be completed:",
      predict: "The prediction could not be completed:",
      recommend: "The regimen recommendation could not be completed:",
      shap: "The explanation task could not be completed:",
      report: "The report task could not be completed:",
      generic: "The task could not be completed:",
    },
    canceled: {
      train: "The training workflow was canceled.",
      predict: "The prediction task was canceled.",
      recommend: "The regimen recommendation was canceled.",
      shap: "The explanation task was canceled.",
      report: "The report task was canceled.",
      generic: "The task was canceled.",
    },
  },
  pages: {
    workbench: {
      title: "Workbench",
      welcomeTitle:
        "Welcome — I am Dr.BUG, an interactive clinical AI agent for CRGNB decision support.",
      welcomeOverview:
        "I can help you connect model development, patient-level prediction, model interpretation, and individualized regimen recommendation in a single workflow. You can start from structured data, train and release task-specific models, run single-patient or batch prediction, review interpretable outputs such as feature contributions and prediction records, and explore regimen references for individual patients.",
      capabilities: {
        title: "What I can help with",
        item1:
          "Train and release models for clinical efficacy, survival outcome, polymyxin resistance, or treatment duration.",
        item2:
          "Run single-patient or batch prediction using released models, and review how individual variables contribute to patient-level outcomes.",
        item3:
          "Generate individualized regimen recommendations based on the selected survival model.",
      },
      getStarted: {
        title: "How to start",
        body: "Choose a quick entry below, or describe your goal in chat. For example, you can ask me to train a survival prediction model, run a single-patient prediction, run a batch prediction, or generate an individualized regimen recommendation.",
      },
      boundary: {
        title: "Use boundary",
        body: "Dr.BUG is designed for research and decision-support evaluation. Model outputs do not replace clinical judgement. Patient data are used only for the selected workflow and are not sent to the language model.",
      },
      quickEntry: {
        title: "Quick entry",
        actionLabel: "Open",
        training: {
          title: "Model training",
          description: "Prepare training data and parameters, then create a training job.",
          /** Routed to chat; must stay recognizable to backend intent rules (includes "train"). */
          sendPhrase: "I want to train a model",
        },
        prediction: {
          title: "Personalized prediction",
          description: "Run single-patient or batch prediction with a released model.",
        },
        recommendation: {
          title: "Personalized regimen recommendation",
          description: "Generate personalized regimen recommendations based on the selected survival model.",
        },
      },
      chat: {
        placeholder:
          "Describe your goal, e.g. train a 28-day survival prediction model with the current dataset",
        send: "Send",
      },
    },
    tasks: {
      title: "Tasks",
      subtitle: "Track training, prediction, and recommendation jobs. Click a card to view details on the right.",
      filters: {
        status: "Status",
        type: "Type",
        sort: "Sort",
      },
      statusOptions: {
        all: "All",
        queued: "Queued",
        running: "Running",
        waitingUser: "Waiting for input",
        completed: "Completed",
        failed: "Failed",
        canceled: "Canceled",
      },
      typeOptions: {
        all: "All",
        train: "Model training",
        predict: "Prediction (single / batch)",
        recommend: "Regimen recommendation",
        report: "Report",
        other: "Other",
      },
      sortOptions: {
        activityDesc: "Recent activity (new → old)",
        createdDesc: "Created time (new → old)",
        createdAsc: "Created time (old → new)",
      },
      banners: {
        loadFailedTitle: "Failed to load tasks",
        cachedListHint: "Showing the last successfully loaded cached list. It may be outdated.",
      },
      empty: {
        none: "No tasks yet. Create a training or prediction job from the workbench, and it will appear here.",
        filteredNone: 'No tasks match the current filters. Adjust filters or click "Refresh".',
      },
      loading: "Loading…",
      meta: {
        created: "Created",
        recentActivity: "Recent activity",
        progressNote: "Progress note: ",
        progress: "Progress",
      },
    },
    datasets: {
      title: "Datasets",
      subtitle:
        "Upload and manage training datasets, and maintain the regimen library for personalized recommendation.",
      subtitleRegimens:
        "Create and edit candidate antibiotic regimens used in recommendation workflows.",
      uploadDataset: "Upload dataset",
      tabs: {
        data: "Datasets",
        regimens: "Regimens",
      },
      sections: {
        createDataset: "Upload dataset",
        createDatasetHint: "Upload CSV / Excel and select applicable clinical tasks.",
        datasetList: "Datasets",
      },
      count: "Total {count}",
      empty: "No datasets",
      unnamedDataset: "Unnamed dataset",
      currentDatasetBadge: "Current",
      meta: {
        format: "Format",
        uploadedAt: "Uploaded",
        availableTasks: "Available tasks",
        unspecified: "Unspecified",
      },
      taskLabels: {
        clinical_efficacy: "Clinical efficacy",
        mortality_28d: "Survival related",
        polymyxin_resistance: "Polymyxin resistance",
        treatment_duration: "Treatment duration",
      },
      aria: {
        sectionTabs: "Datasets sections",
      },
    },
    models: {
      title: "Models",
      subtitle:
        "Browse models from your released model library, view summaries, and set the model used in the current session.",
      note:
        '"Set as current model" only applies to the current browser session. The server does not persist a default model.',
      filters: {
        task: "Task filter",
        sort: "Sort",
      },
      taskAll: "All task types",
      sortOptions: {
        timeDesc: "Registered time (new → old)",
        timeAsc: "Registered time (old → new)",
        nameAsc: "Name (A → Z)",
      },
      banners: {
        loadFailedTitle: "Failed to load model list",
        loadFailedBody:
          "Failed to load models. Please refresh the page or check whether the backend service is running.",
        cachedListHint: "Showing the last successfully loaded cached list.",
        selectionMissing:
          "The model saved in this session is not in the list (it may have been removed). Please reselect or refresh.",
      },
      errors: {
        saveFailed: "Could not save changes. Please try again.",
        deleteFailed: "Could not delete the model. Please try again.",
        actionFailed: "Something went wrong. Please try again.",
      },
      empty:
        "No models yet. After training completes and you release a model, it will appear here for prediction.",
      loading: "Loading…",
      list: {
        title: "Model list",
        count: "Total {count}",
        algorithm: "Algorithm",
        registeredAt: "Registered",
        setCurrent: "Set as current",
        currentUsing: "Current",
        edit: "Edit",
      },
      modal: {
        title: "Edit model info",
        internalId: "Internal ID",
        displayName: "Display name",
        notes: "Notes",
        published: "Mark as published (enabled)",
      },
      confirms: {
        removeFromRegistry: 'Remove "{name}" from the released model library? This cannot be undone.',
      },
      publishStatus: {
        published: "Published",
        unpublished: "Unpublished",
        unknown: "Unknown",
      },
    },
    history: {
      title: "Prediction / Report History",
      subtitle:
        "Browse prediction records and report results. Select an item on the left to view details on the right.",
      filters: {
        allTypes: "All types",
        single: "Single",
        batch: "Batch",
        taskPlaceholder: "Filter by task name",
        modelPlaceholder: "Filter by model name",
        query: "Query",
      },
      panels: {
        list: "Records",
        detail: "Details",
      },
      loading: "Loading…",
      detailLoading: "Loading details…",
      empty: "No prediction records yet. After a prediction completes, it will appear here automatically.",
      pickHint: "Select a record on the left to view the full prediction result and charts here.",
      labels: {
        singleChip: "Single-patient",
        batchChip: "Batch",
        singleTitle: "Single-patient prediction",
        batchTitle: "Batch prediction",
        task: "Task",
        model: "Model",
        file: "File",
        totalRows: "Total rows",
        succeeded: "Succeeded",
        failed: "Failed",
        download: "Download result file",
        predictedLabel: "Predicted label",
        predictedProbability: "Predicted probability",
        predictedValue: "Predicted value",
        batchSummary: "Total {total}; succeeded {succeeded}; failed {failed}",
        supplementColumnMapping: "Supplement: column mapping",
        modelInterpretation: "Variables handled by preprocessing",
        recordId: "Record ID",
        createdAt: "Created",
        resultSummary: "Result summary",
        noSummary: "No summary available",
        na: "—",
        listSeparator: "; ",
        columnAlignmentSummary:
          "Column alignment: matched {matched} · missing {missing} · extra {extra}",
      },
      detail: {
        briefInterpretationLabel: "Brief interpretation:",
        topFeaturesLabel: "Main contributing variables:",
        chartSummaryTitle: "Model explanation charts",
        chartFoldHint: "",
        chartNote: "",
        waterfallCaption: "Variable contribution (waterfall)",
        waterfallAlt: "Waterfall plot of variable contributions",
        forceCaption: "Variable influence (force plot)",
        forceAlt: "Force plot of variable influence",
        noExplanationImages:
          "No explanation images are attached to this record. Review the predicted label, probability, and main contributing variables above.",
        fieldLabelsTitle: "",
        punctuation: {
          colon: ": ",
          gap: "  ",
        },
        scanRegressionWithProb:
          "{valueLabel}{colon}{value}{gap}{probLabel}{colon}{probability}",
        scanRegressionValueOnly: "{valueLabel}{colon}{value}",
        scanClassificationWithProb:
          "{labelLabel}{colon}{label}{gap}{probLabel}{colon}{probability}",
        scanClassificationLabelOnly: "{labelLabel}{colon}{label}",
        errorWithCode: "{message} ({code})",
        resultSummaryTailPrefix: "Result summary: ",
      },
      warnings: {
        predictionCompleted: "Prediction completed",
        trainingCompleted: "Training completed",
        recommendationCompleted: "Recommendation completed",
        statusCompleted: "Completed",
        statusFailed: "Failed",
        statusCanceled: "Canceled",
        predictionCompletedWithRest: "Prediction completed ({rest})",
        trainingCompletedWithRest: "Training completed ({rest})",
        recommendationCompletedWithRest: "Recommendation completed ({rest})",
        stateMachineRecoveryFailed:
          "State machine recovery failed. Please check logs in task details.",
        jobStatusUpdated: "Task status updated. Check the task list or details.",
        completionCardTitleFallback: "Training complete",
      },
    },
  },
  common: {
    na: "—",
    refresh: "Refresh",
    refreshing: "Refreshing…",
    retry: "Retry",
    close: "Close",
    cancel: "Cancel",
    confirm: "Confirm",
    delete: "Delete",
    save: "Save",
    saving: "Saving…",
    remove: "Remove",
    canceling: "Canceling…",
    deleting: "Deleting…",
    processing: "Processing…",
  },
  app: {
    session: {
      currentSession: "Current session",
      newSessionTitle: "New session {n}",
    },
    confirm: {
      deleteSession: "Delete the current session? This cannot be undone.",
      cancelTask: "Cancel this task? Any in-flight work may be stopped.",
      deleteTask: "Delete task {jobId}? This cannot be undone.",
      deleteDataset: "Delete this dataset? Files will be removed from the server and cannot be recovered.",
      removeModelFromRegistry: 'Remove "{label}" from the released model library? This cannot be undone.',
    },
    errors: {
      workflowConfirmMissingJobOrAction: "Workflow confirmation is missing job_id or action.",
      workflowSubmitFailed: "Workflow submission failed: {message}",
      pendingActionNotConfirmable: 'Pending action status is "{status}"; confirmation is not allowed.',
      trainMissingRequiredAfterMerge: "Still missing required fields: {fields} (same as pre-submit validation).",
      predictionDraftNeedPatientFeatures:
        "Fill patient features in this card before confirming. Values are sent only via the confirm API, not to the language model as chat content.",
      missingParamsList: "Missing parameters: {fields}",
      confirmSucceededNoJobId:
        "Confirmation succeeded but no job_id was returned. Check the backend /actions/confirm response shape.",
      confirmFailedWithCode: "Confirmation failed ({code}): {message}",
      confirmFailed: "Confirmation failed: {message}",
      deleteTaskFailed: "Failed to delete task: {message}",
      chatModelUnavailable: "The model service is currently unavailable.",
      withCode: "{message} (error code {code})",
    },
    shell: {
      workflowStepUnavailable:
        "This workflow step could not be displayed. You can open the task details, retry the action, or start a new workflow.",
      workbenchRenderFailed:
        "The chat workbench hit a rendering error. Use sidebar navigation anytime; reset this panel below or switch pages.",
      resetWorkflowUi: "Reset current workflow state",
      watchdogRecover: "The interface recovered from an interrupted workflow state. The task itself was not cancelled.",
      watchdogWorkflowConfirm: "A workflow confirmation appeared stuck; local UI locks were cleared.",
      watchdogTasksList: "Task list loading timed out in the UI; the loading state was cleared.",
      dismissRecovery: "Dismiss",
    },
  },
  chat: {
    syntheticUser: {
      openPredictionWorkspace: "Open prediction workspace",
      openRecommendationWorkspace: "Open regimen recommendation",
      trainSurvivalWithDataset: "Train a survival model with {datasetId}",
    },
    listSeparator: ", ",
    listConjunction: {
      two: "{first} and {second}",
      many: "{items}, and {last}",
    },
    /** Mirror backend onboarding_copy.py / welcome_policy (API may return the same text). */
    onboarding: {
      greetingBody:
        "Hello, I'm Dr.BUG, a clinical AI assistant for CRGNB anti-infective decision support.\n\n" +
        "I can help you train and publish prediction models, run single-patient or batch predictions, " +
        "review model performance and SHAP explanations, and compare candidate antibiotic regimens " +
        "for individualized treatment support.\n\n" +
        "You can start with:\n" +
        "\"Train a clinical efficacy prediction model with the current dataset\"\n" +
        "\"Run a prediction using the current model\"\n" +
        "\"Show the latest training result\"\n" +
        "\"Compare candidate antibiotic regimens\"\n" +
        "\"Recommend candidate antibiotic regimens\"",
      suffixDataset:
        "I see that the current dataset is {name}; you can start a training task with it directly.",
      suffixModel: "The current model is {name}; you can use it for prediction or review its summary.",
      suffixTrainingWaiting:
        "A training step is currently waiting for confirmation; you can complete it in the card below.",
      suffixPendingDraft: "An action is waiting for confirmation in the chat card before we can continue.",
    },
    narrative: {
      fallbackNoExecutableTask: "No executable task was recognized; handled as a normal Q&A response.",
      confirmSucceededTaskCreated: "Confirmed. The task has been created.",
      recognizedMissingFields: "Recognized as {action}. You still need to provide: {fields}.",
      recognizedReadyToConfirm: "Recognized as {action}. Parameters are ready; confirm to start execution.",
      taskCreateFailed: "Task was not created successfully: {message}",
      operationSubmitted: "Submitted.",
    },
    actionLabels: {
      create_training_job: "Training job",
      draft_training_job: "Training draft",
      create_prediction_job: "Prediction job",
      draft_single_prediction: "Single-patient prediction draft",
      create_recommendation_job: "Regimen recommendation job",
      create_report_job: "Report generation job",
    },
    fieldLabels: {
      dataset_id: "Dataset",
      clinical_task_id: "Clinical task",
        ml_task_type: "Machine learning task type",
      target_column: "Target column",
      selected_features: "Candidate feature pool",
      final_features: "Final modeling columns",
      med_cols: "Locked treatment variables",
      task_type: "Task type (legacy)",
      model_type: "Model type",
      model_name: "Model display name",
      feature_set: "Named feature group",
      feature_source: "Feature source (columns or default pool)",
      objective_metric: "Primary metric",
      primary_metric: "Primary metric override",
      enable_feature_set_search: "Enable feature-set search",
      min_features: "Minimum features",
      max_features: "Maximum features",
      enable_search: "Enable hyperparameter search",
      use_cv_shap: "CV-SHAP",
      index_time: "Index time",
      label_time: "Label time",
      publish_overrides: "Release parameters",
      model_id: "Model",
      patient_features: "Patient features",
      candidate_regimens: "Candidate regimens",
      source_job_id: "Source job",
      report_type: "Report type",
    },
    assistantAction: {
      cardLabel: "Parameter confirmation",
      sectionCurrentParams: "Current parameters",
      predictionDraftHint:
        "Feature values below are sent to the backend only when you confirm, for prediction execution—not as chat content to the language model.",
      expandAll: "Expand all",
      collapse: "Collapse",
      sectionMissingTitle: "Still needed from you",
      trainingStillNeededLine: "Still needed: {items}.",
      alertStatusTitle: "Current status",
      alertConfirmExecute: "Confirm whether to start execution.",
      alertFillFeatures: 'Fill the fields below, then click “Confirm and execute”.',
      patientFeaturesTitle: "Patient features (local entry)",
      placeholderFillFeature: "Enter {name}",
      predictionFallbackHint:
        "This model did not return a field-name list. Enter a JSON object manually (feature keys with numeric or text values); see the textarea placeholder for an example shape.",
      predictionWarnFill: "Complete the fields above, or provide a valid non-empty JSON object before confirming.",
      validationWarnCanSubmit: "Warnings present—you may still submit; please review them.",
      editorTitle: "Model training setup",
      trainingDraftBubble:
        "I have prepared a model-training workflow. First, select the clinical task, target column, candidate input features, and training settings. After you submit the setup, Dr.BUG will check the selected data, run feature screening if enabled, and ask you to confirm the final input features before model training continues. When training is complete, you can review the metrics and release the selected model to the model registry for later prediction.",
      trainingPendingBubble:
        "Training setup is ready for your review. Confirm when the clinical task, target column, and features look correct.",
      trainingSections: {
        primary: "Model training setup",
        advanced: "Advanced settings",
        sectionA: "Task and target",
        sectionB: "Feature and column configuration",
        sectionC: "Training advanced parameters",
      },
      phase1Hint:
        "Choose the dataset, clinical task, and target column, then refine the candidate feature pool and locked treatment variables. Feature lists are finalized in a later workflow step.",
      datasetOptionUnnamed: "Unnamed dataset",
      datasetOptionUnnamedWithDate: "Unnamed dataset · uploaded {date}",
      datasetOptionUnnamedIndexed: "Unnamed dataset ({index})",
      datasetOptionWithUploadDate: "{name} · uploaded {date}",
      datasetOptionDuplicateFallback: "{name} ({index})",
      datasetFilterPlaceholder: "Filter by file name (optional)",
      pleaseSelect: "Please select",
      selectDataset: "Select a dataset",
      useManualDatasetInput: "Enter dataset identifier manually",
      useDropdown: "Use dropdown selection",
      noColumnsNote: "No column list yet—enter dataset and load schema first.",
      columnFetchHint:
        "Dataset columns unavailable: multi-select disabled. Enter dataset and wait for schema, or pick columns once schema is ready.",
      save: "Save",
      saveDraft: "Save draft",
      startTraining: "Start training",
      cancel: "Cancel",
      warningsCanSubmit: "{count} warning(s); you may still save and submit.",
      trainingConfirmSuccess:
        "Training setup submitted. The training receipt is shown below.",
      trainingConfirmPendingFallback: "—",
      nonTrainingConfirmSuccess:
        'Confirmation completed. Check “Current task” on the right or Tasks for the new job.',
      submitFailedBold: "Submit failed:",
      submitFailedTail: '. Fix the setup and try “Confirm and start training” again.',
      confirmCreating: "Creating task…",
      confirmExecutePrediction: "Confirm and execute",
      confirmExecute: "Confirm and start",
      confirmStartTraining: "Confirm and start training",
      modifyParams: "Edit setup",
      modifySetup: "Edit setup",
      modifyParamsTrainingOnly: "Edit setup (training jobs only)",
      warnBeforeSubmit: "Warnings present—confirm before submitting.",
      noPendingHintBeforeStrong:
        "No pending confirmation yet (common when required fields are missing). Click “Edit setup”, complete required fields, then ",
      noPendingHintStrong: "send another message",
      noPendingHintAfterStrong:
        " (e.g. “continue training”). When a confirmable pending appears, click “Confirm and start training”.",
      errors: { predictionJsonMustBeObject: "JSON must be a non-empty object" },
      datasetErrors: {
        listEmpty: "Dataset list is empty—upload or refresh on the Datasets page.",
        listLoadFailed: "Failed to load datasets: {message}.",
        noDatasetId: "No dataset selected; column fields cannot sync yet.",
        columnsLoaded: "Column metadata loaded ({count} columns).",
        noColumnsParsed: "No column names were parsed for this dataset.",
        schemaReadFailed: "Failed to read dataset columns: {message}. Column controls fall back to manual/disabled.",
      },
      hints: {
        targetColumnInvalid: "Target column was invalid for the new dataset and was cleared—pick again.",
        columnsRemoved: "{field} — removed {count} column(s) not present in the new dataset.",
      },
      trainingInactive: {
        notPendingWithStatus:
          'Confirmation is no longer “in progress” ({status}). You cannot continue on this card. Start a new training request.',
        noPendingAfterSubmit:
          "No active confirmation. If you already submitted from this card, check the in-chat receipt below; otherwise start a new chat or wait for a new confirmation card.",
      },
      nonTrainingInactive: {
        notPendingWithStatus:
          'Confirmation status is “{status}”; you cannot continue on this card. Start over.',
        noPendingDone: "No active confirmation. If execution succeeded, check Tasks.",
      },
      pendingStatus: {
        expired: "This confirmation has expired.",
        superseded: "This confirmation was superseded by a newer action.",
        unknown: "This confirmation’s status is {status}.",
      },
      cardState: {
        confirmed: "Confirmed",
        missing: "Needs input",
        fill: "Needs patient fields",
        pending: "Awaiting confirmation",
        stale: "No longer valid",
        draft: "Draft",
      },
      actionTitles: {
        create_training_job: "Model training setup",
        draft_training_job: "Model training setup",
        create_prediction_job: "Prediction job",
        draft_single_prediction: "Prediction setup",
        create_recommendation_job: "Regimen recommendation job",
        create_report_job: "Report generation job",
        unknown: "Unknown task",
      },
      fieldLabels: {
        draft_schema_field_names: "Expected feature fields (names only)",
        task_type:
          "Task type (legacy — migrate to clinical task / ML task type)",
      },
    },
    trainingWorkflow: {
      titles: {
        business: {
          phase3: "Model training — feature confirmation",
          phase4: "Model training — model selection & training settings",
          phase5: "Model training — release confirmation",
          fallback: "Model training — awaiting confirmation",
        },
        stageShort: {
          phase3: "Feature confirmation",
          phase4: "Model & training settings",
          phase5: "Release confirmation",
          fallback: "Training flow",
        },
      },
      status: {
        pending: "Awaiting confirmation",
        submitted: "Submitted",
        completed: "Completed",
        locked: "Locked",
        processed: "Handled",
      },
      narrative: {
        currentDoing: {
          phase3:
            "Review the screening summary below and confirm the final feature set when ready.",
          phase4:
            "Modeling columns are set. Compare candidate models with cross-validation, choose an algorithm and primary metric, then start training.",
          phase5:
            "Training finished. Review charts and metrics below, then decide whether to release this model for prediction and regimen recommendation.",
          fallback: "Follow the card instructions below to confirm.",
        },
        userMustConfirm: {
          phase3: "",
          phase4: "Choose the model to train and the training settings.",
          phase5: "Confirm whether to release the model.",
          fallback: "",
        },
        whatNext: {
          phase3:
            "After you confirm, you will choose a model and training options, then training runs in the background.",
          phase4: "After you confirm, training and reporting run in the background—check Tasks for status.",
          phase5:
            "If you release the model, it will become available for prediction and regimen recommendation. If you skip release, the training outputs will remain saved, but the model will not appear in prediction model selectors.",
          fallback: "",
        },
        submittedSummary: {
          phase3: "Submitted—follow task status in Tasks / task details.",
          phase4: "Submitted—the task is now training.",
          phase5: "Submitted—check Tasks for the final release outcome.",
          fallback: "This confirmation step was handled.",
        },
      },
      badges: {
        phase3: "Feature confirmation",
        phase4: "Training configuration",
        phase5: "Release",
        fallback: "Training flow",
      },
      escape: {
        returnLaterHint:
          "You can open Tasks, Models, or Data management anytime; navigation is not blocked. To abandon this step, cancel from Tasks.",
        cancelTask: "Cancel training task",
      },
      phase2: {
        explainFiguresTitle: "Explanation figures (feature importance)",
        explanationModel: "Explanation model",
        explanationModelUnknown: "Unspecified model",
        shapBeeswarm: "Explanation figure (beeswarm)",
        shapBar: "Explanation figure (bar)",
        filterSummary: "Selection summary: ",
        candidateInfoSummary: "Candidate info (raw column names)",
        candidateCounts: "Suggested columns {suggested}, candidate pool ~{pool} columns.",
        featureScreeningExplanationFromModel: "Feature-screening explanation from {model}",
        featureScreeningExplanationGeneric: "Feature-screening explanation",
        screeningFiguresScopeHint:
          "These figures summarize the feature-screening results and may not correspond to the final trained model.",
        noShapFigures: "No explanation figures to show.",
        none: "None",
        phase2SubHint:
          "For comparing feature importance; collapsed by default to avoid distracting from confirmation.",
        collapseControl: "Collapse",
        expandControl: "Expand",
      },
      phase3: {
        waitingIntroShort: "I've received your model-training request. Please review the setup below.",
        waitingIntroScreening:
          "I've received your model-training request. Dr.BUG will prepare the selected dataset and candidate features before asking you to confirm the final feature set.",
        introBubbleFull:
          "Feature screening is complete. Please confirm the final input features below before model training continues.",
        confirmInstruction:
          "Feature screening is complete. Please confirm the final input features below before model training continues.",
        summaryLead:
          "I screened the selected candidate features and identified a compact feature set with {total} input features.",
        summaryConclusionRich:
          "I screened the selected candidate features and identified a compact feature set with {featureBold}.",
        inputFeaturesBoldPhrase: "{count} input features",
        summaryRequiredRich: "{requiredBold} are required by the task design: {list}.",
        requiredTreatmentBoldOne: "One treatment-related variable",
        requiredTreatmentBoldMany: "{count} treatment-related variables",
        summarySuggestedRichOne:
          "{suggestedBold} was additionally suggested by the feature-selection step: {list}.",
        summarySuggestedRichMany:
          "{suggestedBold} were additionally suggested by the feature-selection step: {list}.",
        suggestedVarsBoldOne: "One variable",
        suggestedVarsBoldMany: "{count} variables",
        summaryOtherSingleRich:
          "{featureBold} remains available but is not selected by default. If you consider it clinically important, you can add it when confirming the final feature set below.",
        summaryOtherManyRich:
          "These features remain available but are not selected by default: {list}. If you consider them clinically important, you can add them when confirming the final feature set below.",
        categoryLabels: {
          required: "Required by task design:",
          suggested: "Suggested by feature selection:",
          available: "Available but not selected by default:",
        },
        summaryRequiredLine: "{label} {list}.",
        summarySuggestedLine: "{label} {list}.",
        summaryOtherLine:
          "{label} {list}. If you consider these features clinically important, you can add them when confirming the final feature set below.",
        summaryRequiredOne: "{n} treatment-related variable is required by the task design: {list}.",
        summaryRequiredMany: "{n} treatment-related variables are required by the task design: {list}.",
        summarySuggestedOne:
          "{n} variable was additionally suggested by the feature-selection step: {list}.",
        summarySuggestedMany:
          "{n} variables were additionally suggested by the feature-selection step: {list}.",
        summaryOtherAvailableOne:
          "{list} remains available but is not selected by default. If you consider it clinically important, you can add it when confirming the final feature set below.",
        summaryOtherAvailableMany:
          "These features remain available but are not selected by default: {list}. If you consider them clinically important, you can add them when confirming the final feature set below.",
        shapInterpretationGuide:
          "The figures below show SHAP-based explanations from the screening models. The beeswarm plot shows how each feature contributes to individual model outputs. Points farther from zero have a larger effect; color indicates whether the feature value is high or low. The bar plot summarizes average absolute SHAP values, so longer bars indicate greater overall influence during feature screening. These figures support feature selection but do not imply causality.",
        screeningFigureNote:
          "These plots summarize the screening model. They may differ from the final trained model after feature confirmation.",
        beeswarmPlot: "Beeswarm plot",
        barPlot: "Bar plot",
        requiredIncludes: "Required includes",
        featureSetSelectionSuggestions: "Feature-set selection suggestions",
        explanationFromModel: "Feature-screening explanation from {model}",
        explanationNote:
          "These figures summarize the feature-screening results and may not correspond to the final trained model.",
        pickFeaturesHeading: "Pick final modeling features",
        pickFeaturesCountTwoParts: "{total} selected: {required} required + {suggested} suggested",
        pickFeaturesCountThreeParts:
          "{total} selected: {required} required + {suggested} suggested + {optional} other",
        pickFeaturesLegend:
          "Required means fixed input features for this task. Suggested means features recommended by the feature-selection step and selected by default.",
        panelRequiredTitle: "Required features",
        panelRequiredNote: "These inputs are fixed by the task design and cannot be removed.",
        panelRequiredEmpty: "No required features were specified for this task design.",
        panelOptionalTitle: "Optional features",
        subpanelSuggestedTitle: "Suggested by feature selection",
        subpanelOtherTitle: "Other available features",
        noOptionalFeatures: "No optional features are available beyond the required set.",
        featureRoleRequired: "Required",
        featureRoleSuggested: "Suggested",
        noFeaturesRetry: "No features available—refresh in task details and try again.",
        confirmFeaturesButton: "Confirm feature set",
        selectedCount: "{count} selected",
        featureConfirmationSubmitted: "Feature set confirmed.",
      },
      phase4: {
        cvComparisonHint:
          "Cross-validation metrics for each candidate model using default settings. Bold numbers are best within each metric column (ties allowed). Choose an algorithm, primary metric, and training mode below.",
        algorithmLabel: "Model to train",
        metricLabel: "Primary metric to optimize",
        tuningEffortLabel: "Training effort",
        tuningDefault: "Default parameters",
        tuningFull: "Grid search (may improve performance but takes longer)",
        submittedConfigHint: "Training configuration submitted.",
        enableSearch: "Allow automatic search for stronger hyperparameters (slower)",
        confirmStartTraining: "Start training with this setup",
        afterSubmitHint: "Training runs in the background—open Tasks to track progress.",
        cvTableMissingAfterRefresh:
          "Model comparison is still unavailable after refreshing task details. Open Tasks to verify artifacts, or confirm modeling features again.",
        reloadModelComparison: "Reload model comparison",
      },
      phase5: {
        publishReviewTitle: "Model pending release",
        finalMetricsTitle: "Final model metrics",
        finalMetricsUnavailable:
          "Final training metrics are not available on this summary yet. Open Tasks and check metrics.json / task summary, or wait for the training job to finish writing results.",
        summaryTaskKind: "Task type",
        summaryAlgorithm: "Algorithm",
        inputFeaturesHeading: "Input features ({count})",
        headlineTrainingDone: "Training complete.",
        leadReviewPerformance: "Review performance below before release.",
        publishDecisionPrompt:
          "Choose whether to release this model to the registry for prediction workflows, and optionally edit the model identifier and notes.",
        technicalSummary: "Technical details",
        draftModelIdLabel: "Draft model id:",
        keyMetricsLabel: "Key metrics:",
        artifactsLine:
          "Artifacts: {count} item(s) including reports and charts (file names under technical details in task details).",
        resultsBlockTitle: "Training results and charts",
        expandTech: "Show charts and comparison table",
        collapseTech: "Hide charts and comparison table",
        techCollapsedHint: "",
        metricColMetric: "Metric",
        metricColValue: "Value",
        metricColNote: "Note",
        noMetricTable: "No metric table—fallback text summary only.",
        rocChart: "ROC curve",
        prChart: "PR curve",
        regressionChart: "Regression prediction plot",
        noChart: "No chart",
        releaseDisplayNameLabel: "Model display name (recommended)",
        releaseDisplayNamePlaceholder: "e.g. mortality-0505 — shown in Models and prediction pickers",
        releaseModelIdLabel: "Release model id (optional)",
        releaseModelIdPlaceholder: "Leave empty to keep the draft id above",
        notesLabel: "Notes (optional)",
        skipPublish: "Do not release",
        confirmPublish: "Release model",
        publishCheckbox: "Release this model for prediction and regimen recommendation",
        submittedHint: "Release decision submitted.",
      },
      labels: {
        currentStep: "",
        mustConfirm: "",
        nextStep: "",
        resultSummary: "Result summary: ",
        primaryMetricNote: "Primary metric",
        metricDash: "-",
        metricKvLine: "{label}: {value}",
      },
      inactive: {
        expandDetails: "View details",
        collapseDetails: "Collapse details",
        recordOnlyHint:
          "Follow Tasks / task details for the latest status; this card only records your confirmation in chat.",
        superseded:
          "This confirmation was updated by a later step—follow task status on the Tasks page.",
        completedLocked: "Finished—follow background task status.",
        lockedState: "Locked—follow background task status.",
        statusLine: "Status: {status}. Open Tasks for details.",
        statusUnknownHandled: "handled",
      },
      backendCopy: {
        headlineWorkflowCompleted: "Training workflow completed.",
        filterSummarySubsetSearchDisabled:
          "Subset search was not enabled. The suggested modeling columns use the current candidate pool; final columns can be adjusted in the next step.",
        filterSummaryGenericEnFallback: "See task details for the screening summary.",
      },
    },
    predictionForm: {
      aria: { predictionModeTablist: "Prediction mode" },
      states: {
        singleRunningTitle: "Running prediction…",
        cancelledTitle: "Prediction workspace · Cancelled",
      },
      modeSingle: "Single-patient prediction",
      modeBatch: "Batch prediction",
      labels: {
        stepChoosePredictionTask: "1. Choose the prediction task",
        stepChooseReleasedModel: "2. Choose a released model for this task",
        stepUploadTable: "4. Upload a patient table (CSV / Excel)",
        columnCheckTitle: "Column check",
        noSchemaSuffix: " (no fields available)",
        noReleasedModelForTask: "No released model is available for this task.",
        loadingModels: "Loading model list…",
        loadingFields: "Loading fields…",
      },
      modelPicker: {
        taskAndAlgo: "{task} · {algo}",
      },
      predictionTasks: {
        survival: { label: "Survival prediction", modelPhrase: "Survival prediction model" },
        efficacy: { label: "Clinical efficacy prediction", modelPhrase: "Clinical efficacy prediction model" },
        resistance: { label: "Polymyxin resistance prediction", modelPhrase: "Polymyxin resistance prediction model" },
        duration: { label: "Treatment duration prediction", modelPhrase: "Treatment duration prediction model" },
      },
      progress: {
        filledSummary: "{filled} of {total} variables completed",
        errorsInline: " · {count} need fixing",
      },
      batch: {
        runningHint: "Running batch prediction (elapsed {elapsed}). Please wait.",
        requiredMissing: "Still missing required columns: {list}",
      },
      elapsed: {
        minutesSeconds: "{minutes} min {seconds} s",
        secondsOnly: "{seconds} s",
      },
      footer: {
        checkingColumns: "Checking…",
        checkColumnNames: "Check column names",
        running: "Running…",
      },
      validation: {
        requiredFill: 'Please fill in "{label}".',
        needValidNumber: '"{label}" must be a valid number.',
        needInteger: '"{label}" must be an integer.',
        min: '"{label}" must be at least {min}.',
        max: '"{label}" must be at most {max}.',
        pickValidOption: '"{label}": choose a valid option from the list.',
        blockers: {
          selectPredictionTask: "Choose a prediction task in the workspace first.",
          selectModel: "Select a released model for this task in the workspace first.",
          schemaLoading: "Loading fields for this model—please wait.",
          schemaMissing: "Could not load model fields. Check your connection, pick the model again, or try later.",
          missingRequiredCount:
            "{count} required field(s) are still empty. Complete fields marked * before running.",
          genericFormatError: "Some fields still have invalid values—fix the hints under each field before running.",
          fillAtLeastOne: "Enter at least one patient field before running prediction.",
          openWorkspaceFirst:
            'Send a message such as "predict" in chat to open the prediction workspace first.',
        },
      },
    },
    batchPrediction: {
      submittedTitle: "Batch prediction · Submitted",
      labels: {
        model: "Model",
        file: "File",
        columnMatch: "Column match",
      },
      submittedAlignment: "Matched {matched} · Missing {missing} · Extra {extra}",
      cancelledTitle: "Batch prediction · Cancelled",
      title: "Batch prediction",
      intro: "Upload CSV / Excel, check columns, then confirm to run.",
      runningHint:
        "Running batch prediction (elapsed {elapsed}). Larger batches take longer—thanks for your patience.",
      loadingModels: "Loading model list…",
      modelSelect: "Model",
      uploadFile: "Upload file",
      selectedFilePrefix: "Selected: ",
      actions: { chooseFile: "Choose file", cancel: "Cancel", checkFields: "Check columns", confirmExecute: "Confirm and execute" },
      states: { checking: "Checking…", running: "Running…" },
      check: {
        title: "Column check results",
        matched: "Matched:",
        missing: "Missing:",
        extra: "Extra:",
        requiredMissing: "Missing required fields: {list}",
        viewMissing: "View missing columns",
        viewExtra: "View extra columns",
        suspiciousPrefix: "Suspicious fields/types:",
        warningSeparator: "; ",
      },
    },
    recommendationWorkflow: {
      statusStrip: {
        completed: "Regimen recommendation · Completed",
        failed: "Regimen recommendation · Failed",
      },
      states: {
        cancelledTitle: "Regimen recommendation · Cancelled",
        completedTitle: "Regimen recommendation · Completed",
        failedTitle: "Regimen recommendation · Failed",
      },
      labels: {
        title: "Model-based regimen recommendation",
        tagSurvivalSingle: "Survival outcome · Single patient",
        completedBadge: "Completed",
        checkingRegimens: "Checking regimen library…",
        enabledRegimenCount: "Enabled candidate regimens: <b>{count}</b>",
      },
      editingChips: {
        ariaGroup: "Regimen recommendation summary",
        regimens: "Candidate regimens: {count} enabled",
        taskPending: "Task: Survival outcome · …",
        taskBinary: "Task: Survival outcome · Binary",
        taskRegression: "Task: Survival outcome · Regression",
        taskMulticlass: "Task: Survival outcome · Multiclass",
        taskOther: "Task: Survival outcome · {type}",
        patientFields: "Patient fields: {filled} / {total} completed",
      },
      introHtml:
        "Choose a published survival-outcome model and enter <strong>non-treatment</strong> patient features. Candidate regimens come from the <strong>regimen library</strong>; rankings are model-based comparisons for discussion—not prescribing guidance. A clinician should interpret results in context.",
      meta: {
        enabledRegimens: "Enabled candidate regimens: {count}",
        survivalOutcomePending: "Survival outcome: —",
        survivalOutcomeBinary: "Survival outcome: Binary",
        survivalOutcomeRegression: "Survival outcome: Regression",
        survivalOutcomeMulticlass: "Survival outcome: Multiclass",
        survivalOutcomeOther: "Survival outcome: {type}",
        filledNonTreatment: "Filled {filled} of {total} non-treatment patient fields",
      },
      banner: {
        title: "No enabled regimens available",
        description:
          "Open Datasets in the sidebar, switch to the Regimens tab, then add and enable at least one candidate regimen before submitting.",
        openRegimens: "Open regimen management",
      },
      running: {
        submitting: "Submitting recommendation job…",
        polling: "Submitted—scoring ranked regimen alternatives…",
      },
      modelSelect: {
        targetLabel: "Target model (survival outcome)",
        loadingSchema: "Loading patient feature table…",
        noSchemaSuffix: " (no schema)",
      },
      patientFeatures: {
        progressFilled: "Filled {filled} / {total} non-treatment patient fields",
        progressErrors: " · {count} validation issue(s)",
        validationIssuesBanner: "{count} validation issue(s) on patient fields",
      },
      compareOptional: {
        summary: "Compare with current regimen (optional)",
        hint: "Optional. Provide the observed regimen to estimate the baseline probability and compare it with the top-ranked recommendation.",
      },
      observedTreatment: {
        colistin_cms_daily_freq: "CMS frequency",
        polymyxin_b_daily_freq: "PMB frequency",
        colistin_sulfate_daily_freq: "Colistin sulfate frequency",
        carbapenem_daily_dose: "Carbapenem dose",
        sulbactam_daily_dose: "Sulbactam dose",
        tigecycline_daily_dose: "Tigecycline dose",
        minocycline_daily_dose: "Minocycline dose",
        vancomycin_daily_dose: "Vancomycin dose",
        eravacycline_daily_dose: "Eravacycline dose",
        aminoglycoside_daily_dose: "Aminoglycoside dose",
        placeholderFreq: "times/day",
        placeholderDose: "g/day",
      },
      actions: {
        submitJob: "Run regimen recommendation",
      },
      postSubmit: {
        taskLabel: "Regimen recommendation",
        modeLabel: "Single-patient recommendation",
        inlineSummary: "Candidate regimens: {count} · Completed variables: {filled} of {total}",
        treatmentVariablesHint: "Treatment variables are generated from candidate regimens during recommendation.",
      },
      validation: {
        regimensLoading: "Checking the regimen library—please wait.",
        noEnabledRegimens:
          "No enabled candidate regimens in the library. Open Datasets → Regimen management to add and enable at least one regimen.",
        noNonTreatmentPatientFields:
          "This model's feature table has no non-treatment patient fields (it may only include therapy-related columns). Use a survival model that includes clinical/laboratory non-treatment features.",
        patientFieldsIncompleteSoft:
          "Some patient fields are incomplete. Missing fields will be filled with model defaults, but completing more fields may improve recommendation reliability.",
        patientFieldsLowCompletion:
          "Too few patient fields are complete. Missing fields will be filled with model defaults, but completing most required fields is recommended before running the recommendation.",
        tooFewFeaturesCompleted:
          "Too few patient features have been completed ({filled}/{total}). Please complete most required fields before running the recommendation.",
      },
    },
    recommendationResult: {
      summaryLead:
        "The regimen recommendation has been completed. The table below ranks candidate regimens by model-estimated survival probability under the selected survival-outcome model. These rankings are intended for clinical review and should not be interpreted as treatment orders.",
      compare: {
        observedBaseline: "Estimated survival with current regimen",
        top1Predicted: "Estimated survival with top-ranked regimen",
        deltaTop1: "Estimated improvement",
      },
      table: {
        rank: "Rank",
        regimenName: "Regimen",
        therapyDetails: "Therapy details",
        modelEstimatedSurvivalProb: "Model-estimated survival probability",
        predictedSurvivalProb: "Model-estimated survival probability",
        regimenAndTherapy: "Regimen & therapy",
      },
      researchDisclaimer:
        "For research support only. Model estimates are not treatment directives and require individualized clinical judgment.",
      emptyHint: "No ranked candidate data.",
      noNonzeroTherapy: "No non-zero therapy parameters",
    },
    predictionSubmittedSummary: {
      title: "Submission details",
      badgePending: "Submitted—running",
      badgeDone: "Completed",
      badgeFail: "Unsuccessful",
      sectionOverview: "Submission overview",
      completedVariablesSummary: "Completed variables: {filled} of {total}",
      sectionFields: "Submitted clinical variables",
      technicalDetails: "Technical details",
      friendlyModel: {
        survival: "Survival prediction model",
        mortality: "Mortality prediction model",
        survival_benefit: "Survival benefit prediction model",
        resistance: "Resistance prediction model",
        treatment_duration: "Treatment duration prediction model",
        clinical_outcome: "Clinical outcome prediction model",
        generic: "Prediction model",
      },
      labels: {
        task: "Task",
        mode: "Mode",
        submittedAt: "Submitted at",
        workspace: "Workspace",
        algorithm: "Algorithm",
        modelId: "Model ID",
      },
      modeSingle: "Single-patient prediction",
      hintPending: "The model is computing; results will appear in messages below.",
    },
    modelPerformanceTable: {
      toggleExpand: "View all model performance",
      toggleCollapse: "Collapse all model performance",
      loading: "Loading model performance…",
      summaryLine: "{count} model result(s), sorted by {metric} by default.",
      singleModelHint: "Only one model result is available to display.",
      colModel: "Model",
      colNotes: "Notes",
      colRecommendation: "Recommendation",
      metricShort: {
        pcc: "PCC",
      },
      modelComparisonUnavailable: "Model comparison results are not available yet.",
      modelComparisonLegacyFallback:
        "Model comparison table is missing for this task (older run or incomplete CV). Open Tasks for artifacts or re-run feature confirmation.",
      empty: "No full model comparison table yet.",
      noteFinalModel: "Final selected model",
      noteBestObjective: "Best on primary metric",
      noteJoin: " / ",
      sortMetricPrimary: "primary metric",
      loadFailed: "Failed to load: {message}",
    },
    messageList: {
      emptyState:
        "Start here: use the input box below to begin training, prediction, regimen recommendation, and other flows.",
      toolQueryTitle: "System information retrieved",
      noTags: "(No labels)",
      fallbackPrompt: "Note: ",
    },
    statusMessages: {
      predict: {
        batchQueued: "Batch prediction submitted and queued for processing.",
        batchRunning: "Computing predictions row-by-row for the uploaded table.",
        singleQueued: "Single-patient prediction submitted and queued.",
        singleRunning: "Computing single-patient prediction.",
      },
      recommend: {
        queued: "Regimen recommendation submitted and queued.",
        running: "Scoring ranked regimen alternatives under the selected model.",
      },
      shap: {
        queued: "Explanation job submitted and queued.",
        running: "Generating model explanation figures and related outputs.",
      },
      report: {
        queued: "Report job submitted and queued.",
        running: "Generating report content or attachments.",
      },
      genericJob: {
        queued: "Task submitted and queued.",
        running: "Task is processing.",
      },
      training: {
        queued: "Feature screening is in progress.",
        featureScreeningInProgress: "Feature screening is in progress.",
        datasetValidation: "Validating dataset and training parameters.",
        phase2Features: "Feature screening is in progress.",
        phase3Features: "Preparing final features and training configuration in the background.",
        phase4Training: "Training the model and generating reports in the background.",
        phase5Release: "Processing release-related steps in the background.",
        modelTrainingStarting: "Starting model training.",
        evaluation: "Summarizing training results.",
        runningFallback: "Training job in progress.",
      },
      completion: {
        headlineDefault: "Training finished.",
        backendHeadlineUiMismatch: "Training finished. Review the summary and outputs in the task panel.",
        trainingReviewRelease:
          "Training is complete. Review the performance summary, then release this model if it should be used for prediction and regimen recommendation.",
        trainCompletedModelRegistered:
          "The model is released and registered. You can select it for single-patient or batch prediction and for regimen recommendation.",
        trainCompletedModelNotRegistered:
          "Training finished without releasing this run to the registry. It will not appear in prediction or regimen recommendation model lists; you can still review reports and artifacts under Tasks.",
        trainCompletedRegistryUnknown:
          "Training finished. Open Tasks for the authoritative summary, outputs, and release status.",
        modelReleasedCardTitle: "Model released",
        trainingCompletedNotReleasedCardTitle: "Training completed, model not released",
        trainingDoneCardTitle: "Training completed",
        keyMetricsHeading: "Key metrics this run:",
        metricBullet: "- {label}: {value}",
        tailHint:
          "Review charts and metrics in the task panel when helpful; released models appear in the model list for prediction.",
        cardTitleFallbackTrainingDone: "Training complete",
        nextStepReleased:
          "This model has been released and can be used for prediction; open the task for reports and charts.",
        nextStepNotReleased:
          "Training finished without release—you can still review reports and outputs; release the model when you want it available for prediction.",
      },
      layers: {
        backendTaskMessageUiMismatch:
          "Task status was updated. Open the task panel for the authoritative summary.",
      },
      failure: {
        cardTitle: "Training did not complete",
        summaryLead: "Training did not complete.",
        errorReasonLine: "Details: {reason}",
        nextStepCard: "Open this task under Tasks, review the error summary, and expand Technical details if you need diagnostics.",
        nextStepSummary: "Open this task under Tasks to review the error summary.",
      },
      predictionOutcome: {
        labelMortality28d: "28-day survival",
        labelSurvival28d: "28-day survival",
        labelTreatmentImproved: "Treatment improved",
        labelTreatmentFailed: "Treatment failed",
        probabilityLine: "Predicted probability: {pct}",
        labelLine: "Predicted label: {label}",
        taskNameSingle: "Single-patient prediction job",
        uiHeadline: "Prediction complete",
        uiSubheadline: "Single-patient prediction result",
      },
    },
    trainingReceipt: {
      featureSource: {
        clauseSep: "; ",
        finalFeatures: "Final modeling columns (final_features), {count} columns",
        namedGroup: "Named feature group (feature_set={name})",
        candidatePool: "Candidate feature pool (selected_features), {count} items",
        none: "(none)",
        extraNamedAlso:
          "A named feature group (feature_set={name}) was also provided",
        extraPoolAlsoFinal: "Candidate pool (selected_features) also submitted with {count} items",
        extraPoolOnly: "Candidate pool (selected_features) also submitted with {count} items",
        multiSourceSuffix:
          ". Multiple sources were submitted; execution priority follows the backend/runtime.",
      },
      lines: {
        datasetId: "Dataset dataset_id: {value}",
        clinicalTaskId: "Clinical task clinical_task_id: {value}",
        mlTaskType: "ML type ml_task_type: {value}",
        targetColumn: "Target column target_column: {value}",
        featureSourceLine: "Feature source: {summary}",
        phaseHint:
          "Initial training setup was submitted; model choice, metrics, final modeling columns, and release are confirmed in later chat steps.",
        optionalPrefill: "(Optional prefill) model_type: {modelType}; objective_metric: {objective}",
      },
    },
  },
  models: {
    presentation: {
      publishState: {
        published: "Published",
        draft: "Draft",
        archived: "Archived",
        unknown: "Publish status unknown",
        unpublished: "Not published",
      },
      missingName: "-",
      taskOriented: {
        mortality_28d: "28-day survival prediction model",
        clinical_efficacy: "Clinical efficacy prediction model",
        polymyxin_resistance: "Polymyxin resistance prediction model",
        treatment_duration: "Treatment duration prediction model",
      },
    },
  },
  /** Clinical task type labels (datasets upload + context chips); aligned with pages.datasets.taskLabels. */
  taskKinds: {
    clinical_efficacy: "Clinical efficacy",
    mortality_28d: "Survival related",
    polymyxin_resistance: "Polymyxin resistance",
    treatment_duration: "Treatment duration",
  },
  panels: {
    context: {
      current: {
        configurationTitle: "Current configuration",
        dataset: "Current dataset",
        model: "Current model",
        task: "Current task",
        status: "Current status",
      },
      recentResult: {
        title: "Recent result",
        lastTraining: "Last training",
        lastSinglePrediction: "Last single-patient prediction",
        lastBatchPrediction: "Last batch prediction",
        emptyPredictionSession: "No prediction result in the current session.",
        emptySingleHint: "No single-patient prediction in this session.",
        emptyBatchHint: "No batch prediction in this session.",
      },
      recommendationSummary: {
        title: "Regimen recommendation",
        runningHint: "Scoring regimens—results will appear in chat when finished.",
        emptyHint: "After a regimen recommendation completes, the top-ranked option and model-estimated probability will appear here.",
        topRankLine: "Top-ranked regimen: {name}",
        topProbShort: "Model-estimated survival probability {prob}",
      },
      batchPredictionSummary: {
        counts: "{displayName} · Total {total} rows · {succeeded} succeeded",
        countsWithFailed:
          "{displayName} · Total {total} rows · {succeeded} succeeded · {failed} failed",
      },
      taskValue: {
        withCompanion: "{jobType} · {status} ({companion})",
      },
      taskDetails: { title: "Task details" },
      datasetDetails: { title: "Dataset details" },
      modelDetails: { title: "Model details" },
      regimenDetails: { title: "Regimen details" },
      historyDetails: { title: "Record details" },
      cards: {
        datasetSummary: "Dataset summary",
        dataAccess: "Data access",
      },
      datasetSummaryLabels: {
        name: "Name",
        status: "Status",
        datasetId: "Dataset ID",
        fileFormat: "File format",
        uploadedAt: "Uploaded",
        description: "Description",
      },
      badges: {
        current: "Current",
      },
      labels: {
        progress: "Task progress",
        time: "Time",
        timeWithValue: "Time: {time}",
        overview: "Overview",
        safePreview: "Safe preview",
        technicalDetails: "Technical details",
        internalId: "Internal ID",
        datasetId: "Dataset ID",
        currentDataset: "Current dataset",
        statusNotCurrent: "Not current",
        availableTasks: "Available tasks",
        name: "Name",
        fileFormat: "File format",
        uploadedAt: "Uploaded",
        description: "Description",
      },
      datasetAccess: {
        loading: "Loading…",
        rowCount: "Rows",
        columnCount: "Columns",
        fieldNames: "Field names",
        sampleRows: "Sample rows",
        noSampleRows: "No sample rows could be shown for this file.",
        schemaColumn: "Column",
        schemaDtype: "Data type",
        schemaNumeric: "Numeric",
        missingId: "No dataset is selected.",
        dialogSubtitleId: "Dataset ID: {id}",
        shortPrivacyNote:
          "Preview shows field names, table dimensions and a small row sample only. Full patient-level data are not sent to the chat context.",
        previewUnavailableTitle: "Preview is unavailable for this dataset.",
      },
      actions: {
        setCurrentDataset: "Set as current",
        currentDataset: "Current dataset",
        startTraining: "Start training",
        viewDetails: "View details",
        generatePreview: "Generate preview (coming soon)",
        previewDataset: "Preview dataset",
        downloadFile: "Download file",
        viewFieldSchema: "View field schema",
      },
      empty: {
        noDataset: "No dataset bound",
        noModel: "No model selected",
        noTask: "No active task",
        selectTaskHint: "Select a task from the task list",
        unspecified: "Unspecified",
        datasetDetailsHint:
          "Select a dataset from the list on the left to view its overview, available task types, and related actions here.",
        historyDetailsHint: "History uses a two-column layout. Please view full details inside the page.",
      },
      safePreview: {
        note:
          "Preview shows field names, table dimensions and a small row sample only. Full patient-level data are not sent to the chat context.",
      },
    },
    taskDetail: {
      tabs: {
        summary: "Summary",
        logs: "Logs",
      },
      emptyPick: "Select a task from the list.",
      loading: "Loading…",
      loadFailed: "Failed to load details:",
      loadErrorWithCode: "{message} ({code})",
      loadErrorGeneric: "{message}",
      pending: {
        foldSummary: "Note: awaiting your confirmation (not running in the backend)",
        trainingTitle: "Model training — awaiting confirmation",
        currentStepLabel: "Current step:",
        filterSummaryLabel: "Feature filter summary:",
        callout:
          "Switch to the Workbench chat and complete this step using the confirmation card pushed above. This panel is read-only and cannot submit on your behalf.",
        phase3Title: "Feature confirmation",
        phase3Hint: "(Open the chat card to review figures and confirm features.)",
      },
      trainingConfig: {
        sectionTitle: "Training configuration",
        modelType: "Model type",
        objectiveMetric: "Primary metric",
        enableSearch: "Enable hyperparameter search",
        confirmTrainInChatHint: "(Confirm in chat to start training)",
      },
      release: {
        sectionTitle: "Release (training report and charts are ready)",
        publishCheckbox: "Release this model for prediction and regimen recommendation",
        releaseModelIdOptional: "Release model ID (optional)",
        notesOptional: "Notes (optional)",
        modelIdPlaceholder: "Leave blank to use the system default ID",
        confirmReleaseInChatHint: "(Confirm release or skip in the chat card)",
      },
      recommendation: {
        modelLabel: "Model:",
        headlineLabel: "Result summary:",
        top1Label: "Top-ranked regimen:",
        top1ProbLabel: "Model-estimated survival probability (that regimen):",
        deltaLabel: "Change vs baseline:",
        viewStructured: "View structured regimen recommendation",
        emptyStructured:
          "No structured summary is available yet. Check artifacts or logs below.",
        regimenPair: "{name} ({id})",
      },
      basic: {
        title: "Basic info",
        jobType: "Job type:",
        status: "Status:",
        progressNote: "Progress note:",
        primaryNote: "Primary note:",
        supplement: "Supplement",
        createdAt: "Created:",
        startedAt: "Started:",
        completedAt: "Completed:",
      },
      trainingSummary: {
        title: "Training summary",
        empty: "No training summary.",
        datasetId: "Dataset:",
        scenario: "Clinical scenario:",
        taskType: "Task type:",
        algorithm: "Algorithm:",
        target: "Target:",
        primaryMetric: "Primary metric:",
        featureSource: "Feature source:",
      },
      result: {
        title: "Result overview",
        empty: "No displayable result is available.",
        goToModels: "Open in Models",
        predictionMode: "Prediction mode:",
        currentStatus: "Current status:",
        uploadedTable: "Uploaded table:",
        generationStatus: "Generation status:",
        downloadPredictionFile: "Download prediction result file",
        historyRecordHint:
          "You can find the same result in Prediction / Report History by record ID {recordId}.",
        batchCounts: "Total {total} records · {succeeded} succeeded · {failed} failed",
        modeSingle: "Single-patient prediction",
        modeBatch: "Batch prediction",
        modelId: "Model ID:",
        headlineFoldTitle: "More details · Task summary",
        singleOutcome: "Outcome:",
        predictedProbability: "Predicted probability:",
        modelOutput: "Model output:",
        noReadablePredictionOverview:
          "No readable prediction overview is available. Please check the logs or artifacts below.",
        reportGenerationFailedNotice:
          "The model and metrics have been saved, but the report or PDF was not generated successfully. Please check the task logs.",
        artifactLabels: {
          allModelMetrics: "All model metrics summary",
          cvResults: "Cross-validation results",
          finalFeatures: "Final feature list",
          phase2FeatureSummary: "Feature selection summary",
          configSnapshot: "Training config snapshot",
          metrics: "Training metrics",
          trainingReport: "Training report",
          shapArtifacts: "SHAP artifacts",
          chart: "Chart",
          recommendationJson: "Recommendation (structured)",
          performanceCurves: "Performance curves",
          default: "Result file",
        },
      },
      delete: {
        canceling: "Canceling…",
        deleting: "Deleting…",
        deleteCurrent: "Delete this task",
      },
      failure: {
        title: "Failure / cancellation",
        missingErrorMessage: 'Status is "{status}", but no error_message is provided.',
      },
      tech: {
        detailsSummary: "Technical details (troubleshooting)",
        intro:
          "Collapsed by default. Includes internal IDs, raw fields, parameters, and logs for troubleshooting only.",
        internalJobId: "Internal job ID:",
        publishSnippetModelIdPrefix: "Release model ID: ",
        publishSnippetNotesPrefix: "Notes: ",
        publishSnippetConfigLabel: "Release config",
        releaseParams: "Release params:",
        paramsSnapshot: "Params snapshot (JSON)",
        rawSummary: "Result summary (raw fields)",
        rawHeadline: "Raw headline:",
        logs: "Logs",
        noLogs: "No logs",
      },
      artifacts: {
        summary: "Artifacts: {count}",
        expand: "Show artifacts",
        collapse: "Hide artifacts",
      },
      metrics: {
        title: "Key metrics:",
        line: "· {label}: {value}",
      },
    },
    modelDetail: {
      emptyPick: "Select a model from the list.",
      loading: "Loading…",
      loadFailed: "Failed to load model details",
      sections: {
        basic: "Basic info",
        metrics: "Summary metrics",
        notes: "Notes",
        source: "Source",
        tech: "Technical details",
      },
      fields: {
        displayName: "Display name",
        algorithm: "Algorithm",
        taskType: "Task type",
        status: "Status",
        version: "Version",
        registeredAt: "Registered",
        publishedAt: "Published",
        updatedAt: "Last updated",
        noteLabel: "Note",
        sourceJob: "Source job",
        missingMetrics: "No metric summary",
        noNotes: "No notes",
        noSourceJob: "No source job recorded",
        featureSummary: "Feature summary",
        internalId: "Internal ID",
        datasetId: "Dataset ID",
        clinicalTaskId: "Clinical task ID",
        targetColumn: "Target column",
        path: "Path",
        fullJson: "Full JSON",
        currentTag: "In use",
        currentSession: "Current session model",
      },
      actions: {
        setCurrent: "Set as current",
        edit: "Edit",
      },
    },
  },
  components: {
    datasetUpload: {
      intro:
        "Choose a local data file, select applicable clinical tasks (multi-select), then upload it to the workspace.",
      tasksTitle: "Applicable tasks",
      pickFile: "Choose file",
      uploading: "Uploading…",
      upload: "Upload to workspace",
      selected: "Selected",
      uploadSuccess: "Upload succeeded: {name}",
      uploadFailedWithCode: "Upload failed ({code}): {message}",
      uploadFailed: "Upload failed: {message}",
      taskOptions: {
        clinical_efficacy: "Clinical efficacy",
        mortality_28d: "Survival related",
        polymyxin_resistance: "Polymyxin resistance",
        treatment_duration: "Treatment duration",
      },
    },
    confirmation: {
      title: "Confirmation",
      missingParams: "Missing params: {fields}. Please fill them before confirming.",
      invalidPendingStatus: 'Current pending action status is "{status}", cannot confirm.',
      confirm: "Confirm",
      none: "none",
    },
  },
} as const;

export default enUS;

