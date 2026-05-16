from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMProviderError(Exception):
    def __init__(self, user_message: str, error_code: str = "LLM_PROVIDER_ERROR", *, cause: Exception | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.error_code = error_code
        self.cause = cause


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> str:
        raise NotImplementedError

    def health_check(self) -> Dict[str, Any]:
        """
        Minimal availability check: validate configuration and send one lightweight chat request.
        """
        reply = self.chat(
            [{"role": "user", "content": "ping"}],
            system_prompt="Reply with a short pong.",
            temperature=0.0,
            stream=False,
        )
        return {"ok": True, "reply_preview": reply[:100]}
