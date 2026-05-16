"""
Centralized Chinese (and mixed CJK) phrases used only for user-message intent / routing detection.

Do not import heavy agent modules here (avoid cycles). Callers keep routing logic; this module holds literals only.
"""

from __future__ import annotations

import re
from typing import FrozenSet, Pattern, Tuple

# --- status_query_router ---

ZH_VIEW_VERBS_TASK_STATUS_CONCEPT: Tuple[str, ...] = (
    "查",
    "查看",
    "看",
    "显示",
    "列出",
    "给我",
    "帮我查",
    "帮我",
)

ZH_VIEW_VERBS_CONCEPT_EXPLANATION: Tuple[str, ...] = (
    "查",
    "查看",
    "看",
    "显示",
    "列出",
    "给我",
    "帮我查",
)

ZH_STATUS_CONCEPT_ANCHOR_TERMS: Tuple[str, ...] = (
    "任务",
    "job_",
    "进度",
    "失败",
    "状态",
    "上下文",
    "模型",
    "队列",
    "job",
    "报错",
    "预测结果",
    "预测",
    "解释",
    "批量",
    "SHAP",
)

ZH_FAILURE_QUERY_TERMS: Tuple[str, ...] = (
    "失败原因",
    "为何失败",
    "为什么失败",
    "报错",
    "错误信息",
    "最近失败",
    "最后一次失败",
    "最新失败",
    "卡在哪",
    "主要卡",
    "先检查什么",
)

ZH_CONTEXT_QUERY_TERMS: Tuple[str, ...] = (
    "当前上下文",
    "当前模型",
    "用的什么模型",
    "什么大模型",
    "chat 模型",
    "对话模型",
    "页面模式",
    "工作台状态",
)

ZH_BROAD_LIST_QUERY_TERMS: Tuple[str, ...] = (
    "任务列表",
    "有哪些任务",
    "全部任务",
    "当前进度",
    "运行进度",
    "进行到哪",
    "排队",
    "运行情况",
)

ZH_TRAINING_RESULT_CONCEPT_MARKERS: Tuple[str, ...] = ("什么是训练结果", "训练结果是啥")

ZH_TRAINING_SUMMARY_TERMS: Tuple[str, ...] = (
    "训练结果",
    "最近训练",
    "训练完成了吗",
    "训练完了吗",
    "训练结束了吗",
    "模型训练完成了吗",
    "模型训练完了吗",
    "训练结束了没",
    "训练怎么样",
    "训练好了吗",
    "训练指标",
    "模型效果",
    "刚训练",
    "刚才训练",
    "训练跑",
    "训练是否完成",
    "训练结束",
    "模型训练好",
    "训练表现",
    "值得注意",
    "哪个模型最好",
    "模型最好",
    "最优模型",
)

ZH_TRAINING_RESULT_INTERROGATIVE_PARTICLES: Tuple[str, ...] = ("怎么", "怎样", "如何", "查看", "看", "查", "样")

ZH_TRAINING_METRIC_TOKENS: Tuple[str, ...] = ("auc", "AUC", "准确率", "指标")

ZH_TRAINING_QUALITY_TOKENS: Tuple[str, ...] = ("表现", "好不好", "值得注意", "最好", "最优")

ZH_MODEL_SUPERLATIVE_TERMS: Tuple[str, ...] = ("最好", "最优")

ZH_PREDICTION_EXPLANATION_PHRASES: Tuple[str, ...] = (
    "为什么这样预测",
    "解释一下这次预测",
    "解释这次预测",
    "SHAP 摘要",
    "shap 摘要",
    "这个结果是怎么来的",
    "模型解释是什么",
    "预测解释",
    "解释一下预测",
    "请解释一下这次预测",
    "SHAP 摘要是什么",
)

ZH_PREDICTION_SUMMARY_HEAD_TERMS: Tuple[str, ...] = (
    "预测结果",
    "最近一次预测",
    "刚才那个预测",
    "单样本预测结果",
    "批量预测结果",
)

ZH_PREDICTION_SUMMARY_FOLLOWUP_TERMS: Tuple[str, ...] = ("怎么样", "如何", "结果", "好不好", "行吗")

ZH_PREDICTION_RISK_INTERP_TERMS: Tuple[str, ...] = (
    "说明什么",
    "意味着什么",
    "风险高不高",
    "为什么会",
    "要注意什么",
    "要注意的",
)

ZH_PREDICTION_BATCH_SCOPE_TERMS: Tuple[str, ...] = ("这批", "整批", "批量")

ZH_PREDICTION_BATCH_EVAL_TERMS: Tuple[str, ...] = (
    "怎么样",
    "异常",
    "高风险",
    "先看什么",
    "风险多",
    "值得关注",
)

ZH_PREDICTION_BATCH_TAIL_TERMS: Tuple[str, ...] = ("高风险", "风险多", "异常", "先看", "值得关注", "怎么样")

ZH_PREDICTION_LABEL_PROX_TERMS: Tuple[str, ...] = ("刚才", "这次", "上次", "最近", "刚刚")

ZH_READONLY_TRAINING_OVERRIDE_PHRASES: Tuple[str, ...] = (
    "查看训练结果",
    "训练结果是什么意思",
    "什么是训练结果",
    "训练指标是什么",
    "什么是训练指标",
    "训练状态是什么",
    "什么是训练状态",
    "训练结果怎么样",
    "训练为什么失败",
    "为什么训练失败",
    "训练完成了吗",
    "训练完了吗",
    "训练结束了吗",
    "模型训练完成了吗",
    "模型训练完了吗",
    "训练好了吗",
    "训练结束了没",
)

ZH_READONLY_OVERRIDE_TRIGGER_TERMS: Tuple[str, ...] = (
    "进度",
    "状态",
    "失败",
    "报错",
    "错误信息",
    "错误原因",
    "列表",
    "排队",
    "运行情况",
    "上下文",
    "有哪些任务",
    "全部任务",
    "进行到哪",
    "运行进度",
    "当前进度",
    "任务列表",
    "最新失败",
    "最近失败",
    "最后一次失败",
    "训练结果",
    "预测结果",
    "刚才预测",
    "预测出来了吗",
    "训练怎么样",
    "预测怎么样",
    "训练好了吗",
    "预测好了吗",
    "最近一次预测",
    "训练指标",
    "模型效果",
    "最近训练",
    "训练表现",
    "模型最好",
    "值得注意",
    "说明什么",
    "为什么会",
    "风险高不高",
    "这批",
    "批量",
    "先检查什么",
    "卡在哪",
    "解释一下这次预测",
    "SHAP 摘要",
    "模型解释是什么",
    "刚才的预测",
    "结果和解释",
    "这次批量预测",
    "预测标签",
    "预测概率",
)

# --- concise_progress ---

ZH_COMPLETION_QUERY_HINTS: Tuple[str, ...] = (
    "完了吗",
    "完了没",
    "完没",
    "训练完没",
    "现在训练完没",
    "好了吗",
    "好了没有",
    "好没有",
    "好了没",
    "还没好吗",
    "还没好",
    "结束了吗",
    "结束了没",
    "结束没",
    "完成了吗",
    "完成了没",
    "完成没",
    "出来了吗",
    "出来没",
    "出了没有",
    "结果出了没有",
    "有结果了吗",
    "好没好",
)

ZH_TRAIN_PIPELINE_SURFACE_TERMS: Tuple[str, ...] = (
    "特征筛选",
    "筛选特征",
    "入模",
    "特征确认",
    "训练配置",
    "release",
    "建模",
    "训练任务",
)

ZH_FILTER_STAGE_TIME_HINT_TERMS: Tuple[str, ...] = ("多久", "多长", "要等", "什么时候", "啥时候", "完", "好没")

ZH_COMPLETION_CONJUNCTION_BLOCKERS: Tuple[str, ...] = ("然后", "并且", "同时", "接着", "之后还要", "之后要")

ZH_TRAIN_ETA_KEYWORDS: Tuple[str, ...] = (
    "多久",
    "多长",
    "还要等",
    "要等",
    "什么时候",
    "啥时候",
    "多久能",
    "啥时候完",
    "预计",
    "时间",
)

ZH_TRAIN_PHASE_PROGRESS_KEYWORDS: Tuple[str, ...] = (
    "哪一步",
    "到哪了",
    "什么阶段",
    "进度",
    "进展",
    "卡在哪",
    "卡住",
    "怎么样了",
    "如何了",
    "怎样了",
)

ZH_CONCISE_PROGRESS_BLOCK_TERMS: Tuple[str, ...] = (
    "任务列表",
    "有哪些任务",
    "全部任务",
    "失败原因",
    "为何失败",
    "为什么失败",
    "报错",
    "错误信息",
    "上下文",
    "当前模型",
    "用的什么模型",
    "训练结果",
    "预测结果",
    "最近一次预测",
    "最近训练",
)

ZH_CONCISE_PROGRESS_TRIGGER_TERMS: Tuple[str, ...] = (
    "进度",
    "进展",
    "哪一步",
    "到哪一步",
    "到哪了",
    "什么阶段",
    "多久",
    "多长",
    "还要等",
    "什么时候",
    "啥时候",
    "预计",
    "卡在哪",
    "卡住",
)

ZH_CONCISE_PLAIN_STATUS_SHORT: Tuple[str, ...] = ("怎么样了", "如何了", "怎样了")

ZH_CONCISE_PLAIN_STATUS_LONG: Tuple[str, ...] = ("现在怎么样了", "现在如何了", "到哪一步了", "现在到哪一步了")

ZH_TRAIN_DEMONSTRATIVE_PREFIX_RE: Pattern[str] = re.compile(r"(这个|现在|当前|本轮|那|这|该)训练")

# --- intent_parser ---

PRED_ENTRY_CLINICAL_TOPIC_RE: Pattern[str] = re.compile(
    r"(生存|死亡|死亡风险|预后|疗效|临床疗效|耐药|多黏菌素|疗程|患者|批量|表格|excel|csv|\.xlsx|\.xls|28天|"
    r"survival|mortality|prognosis|efficacy|resistance|polymyxin|\bmic\b|patient|batch|cohort)",
    re.IGNORECASE,
)

ZH_TRAINING_CONCEPT_READONLY_PHRASES: Tuple[str, ...] = (
    "训练指标是什么",
    "什么是训练指标",
    "训练指标是什么意思",
    "训练状态是什么",
    "什么是训练状态",
    "训练状态是什么意思",
    "查看训练结果",
    "看下训练结果",
    "看看训练结果",
    "训练结果怎么样",
    "训练结果如何",
    "训练结果怎样",
    "训练为什么失败",
    "训练为何失败",
    "为什么训练失败",
    "为何训练失败",
    "训练失败原因",
    "训练失败是怎么回事",
    "训练到哪一步了",
    "训练到哪一步",
    "训练到第几步",
    "训练完了吗",
    "训练完成了吗",
    "训练结束了吗",
    "模型训练完成了吗",
    "模型训练完了吗",
    "训练好了吗",
    "训练结束了没",
)

ZH_TRAINING_COMMAND_TOKENS: Tuple[str, ...] = (
    "训练模型",
    "帮我训练",
    "我要训练",
    "请训练",
    "开始训练",
    "新建训练",
    "跑训练",
    "发起训练",
    "创建训练",
    "准备训练草稿",
    "起草训练",
    "训练草稿",
    "继续训练",
    "准备训练",
    "帮我起草训练",
    "起草训练草稿",
)

ZH_TRAINING_SURVIVAL_SPAN_RE: Pattern[str] = re.compile(r"训练.{0,8}生存")

ZH_WHAT_IS_TRAINING_TRIO_RE: Pattern[str] = re.compile(r"什么是训练(结果|指标|状态)")

ZH_PREDICTION_ENTRY_EXACT_CMDS: FrozenSet[str] = frozenset(
    {
        "预测",
        "单样本预测",
        "批量预测",
        "批量推理",
        "我要做批量预测",
        "预测配置",
        "统一预测入口",
        "执行预测",
        "确认预测",
        "开始预测",
    }
)

ZH_PREDICTION_DRAFT_SIGNAL_TERMS: Tuple[str, ...] = ("预测草稿", "单样本预测草稿", "准备单样本预测")

ZH_PREDICTION_DRAFT_SINGLE_SAMPLE_RE: Pattern[str] = re.compile(r"(帮我|给我|替我|我要).{0,8}单样本预测")

# --- prediction_followup ---

ZH_TEMPORAL_ANCHORS: FrozenSet[str] = frozenset(
    (
        "刚才",
        "这次",
        "上一次",
        "上次",
        "最近",
        "刚刚",
        "今早",
        "昨晚",
        "之前",
        "上一轮",
    )
)

ZH_PREDICTION_FOLLOWUP_TOPICS: FrozenSet[str] = frozenset(
    (
        "结果",
        "解释",
        "标签",
        "概率",
        "怎么样",
        "如何",
        "为什么",
        "shap",
        "怎么来的",
        "意味着什么",
        "说明什么",
    )
)

ZH_PREDICTION_FOLLOWUP_EXPLAIN_PHRASES: Tuple[str, ...] = (
    "为什么这样预测",
    "请解释一下这次预测",
    "解释一下这次预测",
    "解释这次预测",
    "这个结果是怎么来的",
    "模型解释是什么",
)

ZH_PREDICTION_FOLLOWUP_RECENT_PHRASES: Tuple[str, ...] = ("刚才的预测", "这次预测", "这次批量预测")

ZH_PREDICTION_ENTRY_EXACT_FOLLOWUP: Tuple[str, ...] = (
    "单样本预测",
    "批量预测",
    "我要做批量预测",
    "批量推理",
)

ZH_PREDICTION_COMBINED_RESULT_CONJ: Tuple[str, ...] = ("都说", "都说一下", "一起", "分别", "和", "还有", "以及")

ZH_SUPPRESS_RESULT_EXPLAIN_EXTRA: Tuple[str, ...] = ("都说", "一起")

ZH_PRED_FOLLOWUP_LABEL_PROB_MARKERS: Tuple[str, ...] = ("预测标签", "预测概率", "标签是什么", "概率是什么")

# --- terminal_result_query ---

ZH_TERMINAL_FAIL_CHECK_TERMS: Tuple[str, ...] = ("先检查什么", "先查什么", "先要检查什么")

ZH_TERMINAL_FAIL_WHERE_TERMS: Tuple[str, ...] = ("卡在哪", "卡在哪里", "主要卡", "失败主要", "失败卡")

ZH_TERMINAL_RELEASE_COLLOQUIAL_TERMS: Tuple[str, ...] = ("release了吗", "release了没", "release没有", "release么")

ZH_TERMINAL_RELEASE_QUESTION_PARTICLES: Tuple[str, ...] = ("吗", "没", "没有", "是否")

ZH_TRAIN_RELEASE_STATUS_TERMS: Tuple[str, ...] = (
    "已经发布了吗",
    "发布了吗",
    "上线了吗",
    "有没有发布",
    "是否发布",
)

ZH_TRAIN_RELEASE_LIBRARY_TERMS: Tuple[str, ...] = (
    "写入模型库",
    "进模型库",
    "注册到模型库",
    "发布到模型库",
)

ZH_TRAIN_RELEASE_INLINE_TERMS: Tuple[str, ...] = (
    "发布了吗",
    "是否发布",
    "有没有发布",
    "release了吗",
    "release了没",
    "release没有",
    "上线了吗",
    "上线没有",
)

ZH_TRAIN_RELEASE_CONTEXT_TERMS: Tuple[str, ...] = ("模型", "训练", "这次", "本轮", "刚才", "任务", "刚训练")

ZH_TRAIN_USABILITY_TERMS: Tuple[str, ...] = ("能直接用", "可以直接用", "能用吗", "现在能用")

ZH_TRAIN_BEST_MODEL_TERMS: Tuple[str, ...] = ("哪个模型最好", "模型最好", "最优模型", "最好的是哪个", "哪个最好")

ZH_TRAIN_NOTABLE_TERMS: Tuple[str, ...] = ("值得注意", "需要注意", "注意什么")

ZH_TRAIN_COMPLETION_SHORT_TERMS: Tuple[str, ...] = ("训练完成了吗", "训练结束了吗", "训练好了吗")

ZH_TRAIN_RESULT_QUALITY_TERMS: Tuple[str, ...] = ("怎么样", "如何", "好不好")

ZH_TRAIN_METRIC_QUALITY_TERMS: Tuple[str, ...] = ("怎么样", "如何", "多少", "高不高")

ZH_TRAIN_MODEL_READY_TERMS: Tuple[str, ...] = ("训练好了吗", "已经训练好", "训练好没有", "训练完了吗")

ZH_PRED_BATCH_SCOPE_TERMS: Tuple[str, ...] = ("批量", "这批", "整批")

ZH_PRED_BATCH_HIGH_RISK_TERMS: Tuple[str, ...] = ("高风险多不多", "高风险多吗", "风险多不多", "多少高风险")

ZH_PRED_BATCH_ANOMALY_TERMS: Tuple[str, ...] = ("异常", "值得关注", "需要注意")

ZH_PRED_BATCH_NEXT_TERMS: Tuple[str, ...] = ("先看什么", "接下来先看", "接下来怎么")

ZH_PRED_BATCH_OVERVIEW_TERMS: Tuple[str, ...] = ("怎么样", "如何", "好不好")

ZH_PRED_LABEL_QUESTION_TERMS: Tuple[str, ...] = ("标签是什么", "预测标签是什么", "输出标签是什么")

ZH_PRED_PROB_QUESTION_TERMS: Tuple[str, ...] = ("概率是多少", "预测概率是多少", "可能性是多少")

ZH_PRED_CLINICAL_MEANING_TERMS: Tuple[str, ...] = ("能直接当临床结论", "当成临床结论", "当作临床结论")

ZH_PRED_LABEL_PROB_COMBO_TERMS: Tuple[str, ...] = ("多少", "分别", "各是多少")

ZH_PRED_SINGLE_SAMPLE_RESULT_TERMS: Tuple[str, ...] = ("结果是什么", "结果呢", "结果怎么样")

ZH_PRED_EXPLAIN_AVAIL_TERMS: Tuple[str, ...] = (
    "解释结果可以看吗",
    "解释可以看吗",
    "有解释可以看",
    "有没有解释可看",
)

ZH_PRED_WHY_TERMS: Tuple[str, ...] = ("为什么会", "怎么会", "为什么这样预测")

ZH_PRED_RISK_LEVEL_TERMS: Tuple[str, ...] = ("高不高", "高吗", "低吗")

ZH_PRED_MEANING_TERMS: Tuple[str, ...] = ("说明什么", "意味着什么")

ZH_PRED_READING_TERMS: Tuple[str, ...] = ("预测结果怎么看", "这个预测结果怎么看", "这个预测怎么看", "结果怎么看")

ZH_PRED_CAUTION_TERMS: Tuple[str, ...] = ("要注意什么", "要注意的", "有什么要注意")

ZH_PRED_RESULT_CONCEPT_PHRASES: Tuple[str, ...] = ("什么是预测结果", "预测结果是啥")

ZH_PRED_RESULT_CONCEPT_TEMPORAL_RE: Pattern[str] = re.compile(r"刚才.*预测|预测.*刚才")

# --- continue_intent ---

ZH_CONTINUE_EXPLAIN_SUFFIXES: Tuple[str, ...] = (
    "继续解释",
    "继续解释一下",
    "继续说明",
    "继续介绍",
    "继续说",
    "说一下",
    "详细说",
    "为什么是这一步",
    "为什么这一步",
    "讲讲",
    "展开",
)

ZH_CONTINUE_EXPLAIN_STANDALONE: Tuple[str, ...] = (
    "为什么是这一步",
    "为啥是这一步",
    "为什么建议",
    "详细说说这个建议",
)

ZH_CONTINUE_ACT_BLOCKLIST: Tuple[str, ...] = ("起草训练草稿", "起草训练任务")

ZH_CONTINUE_ACT_ACK_TOKENS: FrozenSet[str] = frozenset(
    {
        "继续",
        "继续。",
        "继续？",
        "继续?",
        "好",
        "好的",
        "行",
        "行的",
        "嗯",
        "嗯好",
    }
)

ZH_CONTINUE_ACT_PHRASES: Tuple[str, ...] = (
    "那就继续",
    "那就按",
    "按这个来",
    "按你说的",
    "照你说的",
    "帮我准备下一步",
    "帮我起草",
    "那你先起草",
    "先起草",
    "起草吧",
    "往下走",
    "往下做",
    "就这样",
    "可以就这样",
    "去执行吧",
    "开干",
)

# --- context_query_detector ---

NEG_PROGRESS_CONTEXT_RE: Pattern[str] = re.compile(
    r"(哪一步|第几步|进度|完成了吗|跑完了吗|还在跑|eta|耗时|阶段|训练结果|预测结果|失败原因|报错|"
    r"auc|c-index|准确率|指标|系数|shap|效果怎么|准不准|loss|曲线)",
    re.IGNORECASE,
)

STRONG_CONTEXT_PATTERNS: Tuple[Pattern[str], ...] = (
    re.compile(r"(当前|现在).{0,6}上下文"),
    re.compile(r"工作台状态"),
    re.compile(r"页面模式"),
    re.compile(r"(我)?(现在|当前).{0,8}(什么|啥|哪种).{0,6}状态"),
    re.compile(r"(有|有没有|是否).{0,8}待确认"),
    re.compile(r"\bpending\b", re.IGNORECASE),
    re.compile(r"(当前|现在).{0,6}焦点.{0,6}任务"),
    re.compile(r"(能|可以).{0,4}继续.{0,8}(什么|做啥|做什么)"),
    re.compile(r"(当前|现在).{0,6}(页面|界面)"),
    re.compile(r"(当前|现在).{0,4}mode\b", re.IGNORECASE),
)

MODEL_SELECTION_CONTEXT_EXCLUDE_RE: Pattern[str] = re.compile(r"(预测|训练).{0,12}(模型|model)", re.IGNORECASE)

MODEL_SELECTION_METRICS_EXCLUDE_RE: Pattern[str] = re.compile(
    r"(auc|指标|准确率|c-index|shap|效果|误差|loss)", re.IGNORECASE
)

MODEL_SELECTION_CONTEXT_RE: Pattern[str] = re.compile(
    r"(现在|当前|我).{0,10}(选|使用|选中).{0,10}(的|是|哪个|什么).{0,6}模型"
)

MODEL_SELECTION_WHICH_MODEL_RE: Pattern[str] = re.compile(r"(哪个|什么)模型.{0,6}(选|当前|现在|我用|工作台)")

BARE_CURRENT_MODEL_METRICS_EXCLUDE_RE: Pattern[str] = re.compile(
    r"(预测|训练|auc|指标|准确率|效果|shap)", re.IGNORECASE
)

ZH_BARE_CURRENT_MODEL_TERMS: Tuple[str, ...] = ("当前模型", "现在模型")

ZH_LLM_MODEL_QUERY_TERMS: Tuple[str, ...] = ("什么大模型", "对话模型", "chat 模型", "用的什么模型")
