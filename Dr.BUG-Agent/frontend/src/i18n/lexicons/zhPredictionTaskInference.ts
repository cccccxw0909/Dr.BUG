/**
 * Chinese keyword fragments for inferring prediction task family and panel mode from free text.
 */

export const RE_SURVIVAL_DOMAIN = /生存|死亡|死亡风险|28天生存|28天死亡|预后/;

export const RE_EFFICACY_DOMAIN = /临床疗效|疗效|治疗反应|好转|改善/;

export const RE_RESISTANCE_DOMAIN = /多黏菌素耐药|多粘菌素耐药|耐药|药敏|敏感性/;

export const RE_DURATION_DOMAIN = /治疗时长|用药时长|抗生素疗程|疗程|治疗天数/;

/** Batch vs single: Chinese + file / cohort cues (English tail unchanged) */
export const RE_PANEL_BATCH_HINT = /批量|表格|excel|\.xlsx|\.xls|\.csv|一批患者|多个患者|batch|multiple\s+patients|cohort/i;

export const RE_PANEL_SINGLE_PATIENT_HINT =
  /单个患者|一个患者|该患者|这个患者|这名患者|个体|个体化|single\s+patient|one\s+patient|this\s+patient|individual\s+patient|case-level/i;
