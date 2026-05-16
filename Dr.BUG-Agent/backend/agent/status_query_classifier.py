"""LLM fallback classifier for status-like questions when rules miss (labels only; no actions)."""

from __future__ import annotations

import json
from typing import Any, Dict, Literal

from backend.agent.i18n.lexicons.zh_status_query_classifier import STATUS_QUERY_CLASSIFIER_SYSTEM_PROMPT_ZH
from backend.llm.base import LLMProviderError

StatusQueryLabel = Literal[
    "status_query_progress",
    "status_query_completion",
    "result_explanation",
    "draft_edit",
    "general_chat",
    "not_status_query",
]

ALLOWED_LABELS = {
    "status_query_progress",
    "status_query_completion",
    "result_explanation",
    "draft_edit",
    "general_chat",
    "not_status_query",
}


def _default_result() -> Dict[str, Any]:
    return {
        "label": "not_status_query",
        "confidence": 0.0,
        "rationale": "fallback unavailable",
        "source": "llm_fallback",
        "used": False,
    }


def classify_status_query_with_llm(message: str, qwen_provider: Any) -> Dict[str, Any]:
    """
    Returns a uniform dict:
    {label, confidence, rationale, source, used}
    - source is always llm_fallback
    - used is decided by the orchestrator; always False here
    """
    prompt = STATUS_QUERY_CLASSIFIER_SYSTEM_PROMPT_ZH
    try:
        raw = qwen_provider.chat(
            messages=[{"role": "user", "content": str(message or "")}],
            system_prompt=prompt,
            temperature=0.0,
            stream=False,
        )
    except LLMProviderError:
        return _default_result()

    try:
        obj = json.loads(str(raw or "").strip())
    except Exception:
        return _default_result()

    label = str(obj.get("label") or "not_status_query")
    if label not in ALLOWED_LABELS:
        label = "not_status_query"
    try:
        confidence = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < 0:
        confidence = 0.0
    if confidence > 1:
        confidence = 1.0
    rationale = str(obj.get("rationale") or "").strip()[:80] or "no rationale"
    return {
        "label": label,
        "confidence": confidence,
        "rationale": rationale,
        "source": "llm_fallback",
        "used": False,
    }
