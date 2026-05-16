/**
 * Legacy Chinese prediction-history index line parsers (archived summaries).
 */

/** "结果：…；概率：0.42" style (halfwidth or fullwidth colon) */
export const RE_HISTORY_LINE_RESULT_AND_PROB = /结果[:\uFF1A]\s*([^\uFF1B;]+)\s*[\uFF1B;]\s*概率[:\uFF1A]\s*([\d.]+|—)/;

/** Probability-only fallback */
export const RE_HISTORY_LINE_PROB_ONLY = /概率[:\uFF1A]\s*([\d.]+)/;

/** Legacy batch index: 总数 10 条；成功 9 条；失败 1 条 */
export const RE_LEGACY_BATCH_SUMMARY_COUNTS_ZH =
  /^\s*(?:总数|全部记录)\s*(\d+)\s*(?:条)?\s*[；;，,、]\s*(?:成功|已成功)\s*(\d+)\s*(?:条)?\s*[；;，,、]\s*(?:失败|未能完成)\s*(\d+)\s*(?:条)?\s*$/i;
