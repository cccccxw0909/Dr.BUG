/**
 * Legacy backend / worker status lines (Chinese) — matching tokens only.
 * User-facing replacement text comes from i18n keys in messageSanitizer.ts.
 */

export const ZH_STATUS_COMPLETED_EXACT = "已完成";
export const ZH_STATUS_FAILED_EXACT = "失败";
export const ZH_STATUS_CANCELED_EXACT = "已取消";
export const ZH_STATUS_ABORTED_EXACT = "已中止";

export const RE_PREFIX_PREDICTION_COMPLETED = /^预测已完成\s*/;
export const RE_PREFIX_TRAINING_COMPLETED = /^训练已完成\s*/;
export const RE_PREFIX_RECOMMENDATION_COMPLETED = /^推荐已完成\s*/;

/** State-machine recovery diagnostics (archived lines) */
export const RE_STATE_MACHINE_RECOVERY = /恢复\s*StateMachine|流程状态恢复失败/;
