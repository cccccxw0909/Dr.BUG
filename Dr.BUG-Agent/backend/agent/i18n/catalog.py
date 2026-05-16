"""Merge locale message fragments and resolve keys to zh or en strings."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.agent.chat_output_locale import is_english_output_locale
from backend.agent.i18n import messages_api as _mapi
from backend.agent.i18n import messages_narrative_polish as _mnp
from backend.agent.i18n import messages_onboarding as _mob
from backend.agent.i18n import messages_orchestrator as _morch
from backend.agent.i18n import messages_payloads as _mp
from backend.agent.i18n import messages_prediction_answerability as _mpa
from backend.agent.i18n import messages_reply_composer as _mrc
from backend.agent.i18n import messages_reply_semantics as _mrs
from backend.agent.i18n import messages_response_verbalizer as _mrv
from backend.agent.i18n import messages_result_presentation as _mrp
from backend.agent.i18n import messages_status as _ms
from backend.agent.i18n import messages_workflow_continue as _mwc
from backend.agent.i18n import messages_workflow_guidance as _mwg
from backend.agent.i18n import messages_workflow_rules as _mwfr

MESSAGES: Dict[str, Tuple[str, str]] = {
    **_ms.MESSAGES,
    **_morch.MESSAGES,
    **_mnp.MESSAGES,
    **_mp.MESSAGES,
    **_mpa.MESSAGES,
    **_mwc.MESSAGES,
    **_mwg.MESSAGES,
    **_mwfr.MESSAGES,
    **_mrc.MESSAGES,
    **_mrs.MESSAGES,
    **_mrp.MESSAGES,
    **_mrv.MESSAGES,
    **_mapi.MESSAGES,
    **_mob.MESSAGES,
}


def chat_msg(locale: Optional[str], key: str, **kwargs: Any) -> str:
    """Return catalog string for locale; English when locale is missing or non-Chinese."""
    pair = MESSAGES[key]
    text = pair[1] if is_english_output_locale(locale) else pair[0]
    return text.format(**kwargs) if kwargs else text