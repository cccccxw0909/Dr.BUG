/**
 * Chinese phrases and patterns for chat-side intent detection (user-typed commands).
 * Not Vue i18n locale strings; kept separate so runtime matchers stay explicit.
 */

export const ZH_TRAINING = "训练";

/** Exact phrases: exit prediction workspace */
export const ZH_PREDICTION_EXIT_PHRASES: ReadonlySet<string> = new Set(["结束预测", "退出预测"]);

/** Exact phrases: execute prediction */
export const ZH_PREDICTION_EXECUTE_PHRASES: ReadonlySet<string> = new Set(["执行预测", "确认预测", "开始预测"]);

export const ZH_PREDICTION_WORD = "预测";
export const ZH_I_WANT_PREDICT = "我要预测";
export const ZH_PREDICTION_CONFIG = "预测配置";
export const ZH_I_THINK_PREDICT = "我想预测";
export const ZH_DO_A_PREDICT = "做个预测";
export const ZH_PREDICT_A_BIT = "预测一下";

export const ZH_BATCH_PREDICTION = "批量预测";
export const ZH_I_WANT_BATCH_PREDICTION = "我要做批量预测";
export const ZH_BATCH_INFERENCE = "批量推理";

/** Quick entry alignment: exact "start prediction" when opening workspace without a card */
export const ZH_START_PREDICTION_EXACT = "开始预测";

/** Trailing Latin + CJK sentence punctuation stripped before English shortcut checks */
export const TRAILING_CHAT_PUNCT_RE = /[.!?…。！？\s]+$/u;

/** Single-sample prediction wording */
export const RE_SINGLE_SAMPLE_PREDICTION = /单样本预测|单个患者预测/;

/** Natural clinical prediction entry: predict [optional quantifier] patient */
export const RE_PREDICT_PATIENT = /预测\s*(一个|某位|该|此|这名)?\s*患者/;

/** Clinical outcome keywords after "预测" within a window */
export const RE_PREDICT_OUTCOME_WINDOW = /预测.{0,40}(生存|死亡|疗效|耐药|疗程|预后)/;

/** Draft route: prefer batch panel from legacy wording */
export const RE_BATCH_PANEL_HINT = /批量预测|批量推理|文件上传/i;
export const RE_BATCH_PREFIX = /^批量/;

/** User asks for recommendation *results* — do not open recommendation workspace card */
export const NEEDLES_RECOMMENDATION_RESULT_SUMMARY_ZH: readonly string[] = [
  "推荐结果",
  "用药推荐结果",
  "推荐任务结果",
  "候选方案排序",
  "top1方案",
  "排名第一的方案",
  "推荐排序结果",
];

/**
 * Compact (whitespace removed) zh-only open-regimen patterns.
 * Examples: 打开用药推荐, 请打开用药推荐
 */
export const RE_OPEN_MEDICATION_RECOMMENDATION = /^(请)?(打开|我要|我想|帮我)?用药推荐[。！!…]*$/;

/** e.g. 打开推荐用药方案 */
export const RE_OPEN_REGIMEN_PLAN = /^(请)?(打开|我要|我想|帮我)?推荐用药方案[。！!…]*$/;
