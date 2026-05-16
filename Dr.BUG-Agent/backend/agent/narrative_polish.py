"""
Optional LLM narrative polish for chat assistant text (training_completed only in phase 1).

- Does not affect routing, task execution, or frontend cards.
- Default off (USE_LLM_NARRATIVE_POLISH); scenario allow-list via LLM_NARRATIVE_POLISH_SCENARIOS.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import LLM_NARRATIVE_POLISH_SCENARIOS, USE_LLM_NARRATIVE_POLISH
from backend.llm.base import LLMProviderError
from backend.schemas.agent import ChatTurnRequest

from backend.agent.chat_output_locale import is_english_output_locale, normalize_chat_output_locale
from backend.agent.i18n.catalog import chat_msg
from backend.agent.i18n.lexicons.zh_narrative_safety import FORBIDDEN_ZH_TERMS
from backend.agent.i18n.lexicons.zh_typography import ZH_CONJUNCTION_AND, ZH_IDEOGRAPHIC_COMMA
from backend.agent.response_payloads import ResponsePayload

logger = logging.getLogger(__name__)

_WS = re.compile(r"\s+")

SCENARIO_TRAINING_COMPLETED = "training_completed"

NARRATIVE_POLISH_SYSTEM = (
    "You rewrite structured facts into one concise Dr.BUG narrative.\n"
    "Do not add facts.\n"
    "Do not change numbers.\n"
    "Do not round values.\n"
    "Do not convert decimals to percentages.\n"
    "Do not infer causality.\n"
    "Do not give treatment or prescribing instructions.\n"
    "Do not claim clinical superiority.\n"
    "Do not mention patient-level data.\n"
    "Do not expose internal identifiers.\n"
    "Preserve metric names and values exactly.\n"
    "If information is missing, omit it rather than guessing.\n"
    "Use the requested language.\n"
    "Return plain text only."
)

_FORBIDDEN_EN = (
    "causal",
    "proven",
    "prescribe",
    "recommendation is clinically superior",
    "patient row",
    "dataset_id",
    "job_id",
    "phase",
)

_DECIMAL_RE = re.compile(r"\d+\.\d+")
_NUM_TOKEN_RE = re.compile(r"\d+\.\d+|\d+")

_PHASE_EN_RE = re.compile(r"\bphase\b", re.I)


def use_narrative_polish_for_scenario(scenario: str) -> bool:
    if not USE_LLM_NARRATIVE_POLISH:
        return False
    s = str(scenario or "").strip()
    return s in LLM_NARRATIVE_POLISH_SCENARIOS


def _resolve_language(req: ChatTurnRequest) -> str:
    ctx = req.chat_context or {}
    al = ctx.get("accept_language") or ctx.get("http_accept_language")
    raw = normalize_chat_output_locale(
        chat_context=ctx,
        message=req.message,
        accept_language=str(al) if al is not None else None,
        default="en",
    )
    return "en-US" if is_english_output_locale(raw) else "zh-CN"


def _next_step_token(release_state: str) -> str:
    rel = str(release_state or "").strip()
    if rel == "released":
        return "available_for_prediction_and_regimen_comparison"
    if rel == "not_released":
        return "review_metrics_consider_publishing"
    return "check_task_and_registry"


def _next_step_sentence(token: str, language: str) -> str:
    return chat_msg(language, f"narrative_polish.next_step.{token}")


def build_training_completed_narrative_facts(
    payload: ResponsePayload,
    req: ChatTurnRequest,
) -> Dict[str, Any]:
    """
    Safe fact payload for narrative polish only (no job_id, dataset_id, params, raw summary).
    """
    raw = dict(payload.facts or {})
    language = _resolve_language(req)
    pm_n = raw.get("primary_metric_name")
    pm_v = raw.get("primary_metric_value")
    primary_metric = str(pm_n).strip() if pm_n is not None and str(pm_n).strip() else ""
    primary_metric_value = "" if pm_v is None else str(pm_v).strip()

    metrics_in = raw.get("narrative_metrics_flat")
    metrics: Dict[str, str] = {}
    if isinstance(metrics_in, dict):
        for k, v in list(metrics_in.items())[:32]:
            ks = str(k).strip()[:80]
            vs = str(v).strip()[:80]
            if ks:
                metrics[ks] = vs

    dataset_name = raw.get("narrative_dataset_display")
    dataset_s = str(dataset_name).strip()[:200] if dataset_name else ""

    algo = raw.get("narrative_algorithm")
    algorithm = str(algo).strip()[:120] if algo else ""

    has_shap = raw.get("narrative_has_shap_beeswarm")
    has_shap_beeswarm = bool(has_shap) if has_shap is not None else False

    mr = raw.get("model_registered")
    model_registered: Optional[bool]
    if isinstance(mr, bool):
        model_registered = mr
    elif mr is None:
        model_registered = None
    else:
        model_registered = bool(mr)

    rel = str(raw.get("release_state") or "unknown").strip()
    nxt = _next_step_token(rel)

    task_name = str(raw.get("task_name") or "").strip()[:240]
    mname = raw.get("model_name")
    model_display_name = str(mname).strip()[:200] if mname is not None and str(mname).strip() else None

    feature_count: Optional[int] = None
    feature_names: Optional[List[str]] = None
    nfc_raw = raw.get("narrative_feature_count")
    nfn_raw = raw.get("narrative_feature_names")
    all_clean: List[str] = []
    if isinstance(nfn_raw, list) and nfn_raw:
        all_clean = [str(x).strip()[:80] for x in nfn_raw if str(x).strip()]
        if all_clean:
            feature_names = all_clean[:8]
    if nfc_raw is not None:
        try:
            feature_count = int(nfc_raw)
        except (TypeError, ValueError):
            feature_count = None
    if feature_count is None and all_clean:
        feature_count = len(all_clean)

    out: Dict[str, Any] = {
        "language": language,
        "scenario": SCENARIO_TRAINING_COMPLETED,
        "task_name": task_name or None,
        "dataset_name": dataset_s or None,
        "algorithm": algorithm or None,
        "model_display_name": model_display_name,
        "model_registered": model_registered,
        "feature_count": feature_count,
        "feature_names": feature_names,
        "primary_metric": primary_metric or None,
        "primary_metric_value": primary_metric_value or None,
        "metrics": metrics,
        "has_shap_beeswarm": has_shap_beeswarm,
        "next_step": nxt,
        "release_state": rel,
    }
    return out


def _non_primary_metric_pairs(facts: Dict[str, Any]) -> List[Tuple[str, str]]:
    pm = facts.get("primary_metric")
    m = facts.get("metrics")
    if not isinstance(m, dict) or not m:
        return []
    pm_s = str(pm).strip() if pm is not None else ""
    out: List[Tuple[str, str]] = []
    for k, v in list(m.items())[:12]:
        ks = str(k).strip()
        vs = str(v).strip()
        if not ks:
            continue
        if pm_s and ks == pm_s:
            continue
        out.append((ks, vs))
    return out


def _other_metrics_sentence_en(pairs: List[Tuple[str, str]]) -> str:
    if not pairs:
        return ""
    chunks = [f"{k} {v}" for k, v in pairs]
    if len(chunks) == 1:
        inner = chunks[0]
    elif len(chunks) == 2:
        inner = f"{chunks[0]} and {chunks[1]}"
    else:
        inner = ", ".join(chunks[:-1]) + f", and {chunks[-1]}"
    return f"Additional metrics included {inner}."


def _other_metrics_sentence_zh(language: str, pairs: List[Tuple[str, str]]) -> str:
    if not pairs:
        return ""
    chunks = [f"{k} {v}" for k, v in pairs]
    if len(chunks) == 1:
        inner = chunks[0]
    elif len(chunks) == 2:
        inner = f"{chunks[0]}{ZH_CONJUNCTION_AND}{chunks[1]}"
    else:
        inner = ZH_IDEOGRAPHIC_COMMA.join(chunks[:-1]) + f"{ZH_CONJUNCTION_AND}{chunks[-1]}"
    return chat_msg(language, "narrative_polish.other_metrics.sentence", inner=inner)


def _feature_sentence_en(facts: Dict[str, Any]) -> Optional[str]:
    names = facts.get("feature_names")
    fc = facts.get("feature_count")
    if isinstance(names, list) and names:
        picked = [str(x).strip() for x in names if str(x).strip()]
        if not picked:
            return None
        count = fc if isinstance(fc, int) else len(picked)
        joined = ", ".join(picked)
        return f"The final model used {count} input features: {joined}."
    if isinstance(fc, int) and fc > 0:
        return f"The final model used {fc} input features."
    return None


def _feature_sentence_zh(facts: Dict[str, Any]) -> Optional[str]:
    language = str(facts.get("language") or "zh-CN")
    names = facts.get("feature_names")
    fc = facts.get("feature_count")
    if isinstance(names, list) and names:
        picked = [str(x).strip() for x in names if str(x).strip()]
        if not picked:
            return None
        count = fc if isinstance(fc, int) else len(picked)
        joined = ZH_IDEOGRAPHIC_COMMA.join(picked)
        return chat_msg(language, "narrative_polish.feature.list", count=count, joined=joined)
    if isinstance(fc, int) and fc > 0:
        return chat_msg(language, "narrative_polish.feature.count_only", count=fc)
    return None


def render_training_completed_template(facts: Dict[str, Any]) -> str:
    """
    Deterministic user-facing training summary (no debug bullets). Preserves primary metric strings verbatim.
    """
    language = str(facts.get("language") or "en-US")
    en = is_english_output_locale(language)
    task_raw = facts.get("task_name")
    task_name = (str(task_raw).strip() if task_raw else "") or chat_msg(language, "narrative_polish.task_fallback")
    pm = facts.get("primary_metric")
    pmv = facts.get("primary_metric_value")
    algo_raw = facts.get("algorithm")
    algorithm = str(algo_raw).strip() if algo_raw else ""
    mr = facts.get("model_registered")
    has_shap = bool(facts.get("has_shap_beeswarm"))
    pairs = _non_primary_metric_pairs(facts)

    if en:
        parts1: List[str] = ["Training was completed successfully."]
        if algorithm:
            core = f"a {algorithm} model for {task_name}"
        else:
            core = f"a model for {task_name}"
        if mr is True:
            parts1.append(f"Dr.BUG trained {core} and registered it in the model library.")
        elif mr is False:
            parts1.append(f"Dr.BUG trained {core} and saved it without publishing.")
        else:
            parts1.append(f"Dr.BUG trained {core}.")

        fs = _feature_sentence_en(facts)
        if fs:
            parts1.append(fs)

        para1 = " ".join(parts1)

        parts2: List[str] = []
        if pm is not None and str(pm).strip() and pmv is not None and str(pmv).strip():
            parts2.append(
                f"In the final evaluation, the primary metric was {str(pm).strip()}, "
                f"with a value of {str(pmv).strip()}."
            )
        elif pm is not None and str(pm).strip():
            parts2.append(
                f"The primary metric name recorded for this run was {str(pm).strip()}; "
                "a stable headline value was not included in this summary."
            )
        else:
            parts2.append(
                "This summary does not include a single headline metric; open the task detail for the full metric table."
            )

        om = _other_metrics_sentence_en(pairs)
        if om:
            parts2.append(om)

        if has_shap:
            parts2.append(
                "A SHAP beeswarm plot is available to show model-based feature attribution."
            )

        if mr is True:
            parts2.append(
                "The model can now be used for prediction and regimen comparison in Dr.BUG."
            )
        elif mr is False:
            parts2.append(
                "The training outputs were saved, but the model will not appear in the prediction model list."
            )
        else:
            parts2.append(
                "Confirm publication status in the task detail and model library before selecting this model for prediction."
            )

        return "\n\n".join([para1, " ".join(parts2)]).strip()

    # zh-CN: concatenate sentences without inserting ASCII whitespace after a fullwidth sentence terminator.
    para1_parts: List[str] = [chat_msg(language, "narrative_polish.zh.opening_done")]
    if algorithm:
        base = chat_msg(language, "narrative_polish.zh.base_algo", task_name=task_name, algorithm=algorithm)
    else:
        base = chat_msg(language, "narrative_polish.zh.base_plain", task_name=task_name)
    if mr is True:
        para1_parts.append(base + chat_msg(language, "narrative_polish.zh.suffix_registered"))
    elif mr is False:
        para1_parts.append(base + chat_msg(language, "narrative_polish.zh.suffix_saved_unpublished"))
    else:
        para1_parts.append(base + chat_msg(language, "narrative_polish.zh.suffix_period"))

    fz = _feature_sentence_zh(facts)
    if fz:
        para1_parts.append(fz)

    para1_zh = "".join(para1_parts)

    para2_parts: List[str] = []
    if pm is not None and str(pm).strip() and pmv is not None and str(pmv).strip():
        para2_parts.append(
            chat_msg(
                language,
                "narrative_polish.zh.primary_metric_with_value",
                pm=str(pm).strip(),
                pmv=str(pmv).strip(),
            )
        )
    elif pm is not None and str(pm).strip():
        para2_parts.append(
            chat_msg(language, "narrative_polish.zh.primary_metric_name_only", pm=str(pm).strip())
        )
    else:
        para2_parts.append(chat_msg(language, "narrative_polish.zh.primary_metric_none"))

    oz = _other_metrics_sentence_zh(language, pairs)
    if oz:
        para2_parts.append(oz)

    if has_shap:
        para2_parts.append(chat_msg(language, "narrative_polish.zh.shap_beeswarm"))

    if mr is True:
        para2_parts.append(chat_msg(language, "narrative_polish.zh.model_ready_use"))
    elif mr is False:
        para2_parts.append(chat_msg(language, "narrative_polish.zh.model_saved_not_listed"))
    else:
        para2_parts.append(chat_msg(language, "narrative_polish.zh.confirm_publish_before_predict"))

    para2_zh = "".join(para2_parts)
    return "\n\n".join([para1_zh, para2_zh]).strip()


def polish_narrative_with_llm(facts: Dict[str, Any], llm_provider: Any) -> str:
    # Align with app default (English) when language is missing; facts from the builder always set this.
    lang = str(facts.get("language") or "en-US")
    user = json.dumps(facts, ensure_ascii=False, indent=2)
    user_block = f"Requested language: {lang}\nStructured facts (JSON):\n{user}"
    text = llm_provider.chat(
        [{"role": "user", "content": user_block}],
        system_prompt=NARRATIVE_POLISH_SYSTEM,
        temperature=0.2,
        stream=False,
    )
    return _WS.sub(" ", str(text or "").strip())


def _allowed_numeric_tokens(facts: Dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    pmv = facts.get("primary_metric_value")
    if pmv is not None and str(pmv).strip():
        allowed.add(str(pmv).strip())
        for m in _NUM_TOKEN_RE.findall(str(pmv)):
            allowed.add(m)
    fc = facts.get("feature_count")
    if fc is not None and str(fc).strip():
        allowed.add(str(fc).strip())
    mets = facts.get("metrics")
    if isinstance(mets, dict):
        for v in mets.values():
            s = str(v).strip()
            if not s:
                continue
            allowed.add(s)
            for m in _NUM_TOKEN_RE.findall(s):
                allowed.add(m)
    return allowed


def _decimal_appears_in_allowed(decimal: str, allowed: set[str]) -> bool:
    for a in allowed:
        if decimal in a:
            return True
    return False


def validate_polished_narrative(text: str, facts: Dict[str, Any]) -> Tuple[bool, str]:
    if not text or not str(text).strip():
        return False, "empty_text"
    pm = facts.get("primary_metric")
    pmv = facts.get("primary_metric_value")
    if pm is None or str(pm).strip() == "":
        return False, "missing_primary_metric_in_facts"
    if pmv is None or str(pmv).strip() == "":
        return False, "missing_primary_metric_value_in_facts"
    pm_s = str(pm).strip()
    pmv_s = str(pmv).strip()
    if pm_s not in text:
        return False, "primary_metric_not_in_output"
    if pmv_s not in text:
        return False, "primary_metric_value_not_in_output"

    low = text.lower()
    for term in _FORBIDDEN_EN:
        if term == "phase":
            if _PHASE_EN_RE.search(text):
                return False, "forbidden_en:phase"
            continue
        if term.lower() in low:
            return False, f"forbidden_en:{term}"
    for term in FORBIDDEN_ZH_TERMS:
        if term in text:
            return False, f"forbidden_zh:{term}"

    allowed_nums = _allowed_numeric_tokens(facts)
    for dec in _DECIMAL_RE.findall(text):
        if not _decimal_appears_in_allowed(dec, allowed_nums):
            return False, f"disallowed_decimal:{dec}"
    return True, "ok"


def maybe_polish_training_completed_narrative(
    payload: ResponsePayload,
    req: ChatTurnRequest,
    llm_provider: Any,
    *,
    trace_entries: Optional[List[Dict[str, Any]]] = None,
) -> str:
    facts = build_training_completed_narrative_facts(payload, req)
    base = render_training_completed_template(facts)

    entry: Dict[str, Any] = {
        "narrative_polish_scenario": SCENARIO_TRAINING_COMPLETED,
        "narrative_polish_attempted": False,
        "narrative_polish_used": False,
        "narrative_polish_fallback_reason": None,
    }

    if not use_narrative_polish_for_scenario(SCENARIO_TRAINING_COMPLETED):
        entry["narrative_polish_used"] = False
        entry["narrative_polish_fallback_reason"] = "flag_off_or_scenario_disabled"
        if trace_entries is not None:
            trace_entries.append(entry)
        return base

    entry["narrative_polish_attempted"] = True
    try:
        polished = polish_narrative_with_llm(facts, llm_provider)
        ok, reason = validate_polished_narrative(polished, facts)
        if not ok:
            logger.info("training_completed narrative polish rejected: %s", reason)
            entry["narrative_polish_fallback_reason"] = reason
            if trace_entries is not None:
                trace_entries.append(entry)
            return base
        entry["narrative_polish_used"] = True
        if trace_entries is not None:
            trace_entries.append(entry)
        return polished
    except LLMProviderError as exc:
        logger.info("training_completed narrative polish LLM error: %s", getattr(exc, "error_code", "LLM_PROVIDER_ERROR"))
        entry["narrative_polish_fallback_reason"] = f"llm_error:{getattr(exc, 'error_code', 'LLM_PROVIDER_ERROR')}"
        if trace_entries is not None:
            trace_entries.append(entry)
        return base
    except Exception as exc:
        logger.info("training_completed narrative polish exception: %s", type(exc).__name__)
        entry["narrative_polish_fallback_reason"] = f"exception:{type(exc).__name__}"
        if trace_entries is not None:
            trace_entries.append(entry)
        return base
