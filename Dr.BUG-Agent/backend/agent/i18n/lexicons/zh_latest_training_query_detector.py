"""Regex fragments for backend.agent.latest_training_query_detector (narrow MCP training summary)."""

from __future__ import annotations

from typing import Final

# Looks like data/concept/action initiation; skip this path.
LATEST_TRAINING_NEGATIVE_RE: Final[str] = (
    r"(患者|病历|样本|逐行|列名|字段清单|原始表|上传|数据集怎么|超参数怎么调|"
    r"是什么意思|什么是|定义|含义|如何开始|怎么开始|发起训练|创建训练|准备训练草稿|"
    r"开始训练|教我训练|训练流程介绍)"
)

# Must hit a "training" context plus one of the patterns below.
LATEST_TRAINING_FOCUS_RE: Final[str] = (
    r"(最近|刚才|刚刚|最新|上次|上一次|最近一次).{0,12}训练|"
    r"训练.{0,12}(结果|状态|怎么样|如何|完成了吗|完成没|好了吗|表现|效果|注册|下一步|指标|概况|摘要)|"
    r"训练.{0,12}模型.{0,10}(注册|表现|结果|怎么样)"
)

# Progress / queue phrasing belongs to concise_progress / workflow, not this detector.
WORKFLOW_OR_STEP_PROBE_RE: Final[str] = r"(哪一步|第几步|卡在哪|排队|还在跑)"
