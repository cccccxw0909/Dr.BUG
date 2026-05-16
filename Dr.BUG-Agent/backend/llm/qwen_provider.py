from __future__ import annotations

from typing import Dict, Optional

from backend.config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL
from backend.llm.base import BaseLLMProvider, LLMProviderError


class QwenProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = (api_key or QWEN_API_KEY or "").strip()
        self.base_url = (base_url or QWEN_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        self.model = (model or QWEN_MODEL or "qwen-plus").strip()

    def _build_client(self):
        if not self.api_key:
            raise LLMProviderError(
                "LLM response failed; check the API configuration or network.",
                "QWEN_CONFIG_MISSING",
            )
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise LLMProviderError(
                "The model service is currently unavailable.",
                "QWEN_SDK_UNAVAILABLE",
                cause=exc,
            ) from exc
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _normalize_messages(
        self,
        messages: list[Dict[str, str]],
        system_prompt: Optional[str],
    ) -> list[Dict[str, str]]:
        normalized: list[Dict[str, str]] = []
        if system_prompt:
            normalized.append({"role": "system", "content": system_prompt})
        for m in messages:
            role = str(m.get("role") or "").strip()
            content = str(m.get("content") or "").strip()
            if role in {"system", "user", "assistant"} and content:
                normalized.append({"role": role, "content": content})
        return normalized

    def chat(
        self,
        messages: list[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> str:
        payload_messages = self._normalize_messages(messages, system_prompt)
        if not payload_messages:
            raise LLMProviderError("The model service is currently unavailable.", "QWEN_EMPTY_MESSAGE")

        client = self._build_client()
        kwargs = {
            "model": self.model,
            "messages": payload_messages,
            "stream": stream,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            if stream:
                chunks = client.chat.completions.create(**kwargs)
                parts: list[str] = []
                for chunk in chunks:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        parts.append(delta)
                text = "".join(parts).strip()
            else:
                resp = client.chat.completions.create(**kwargs)
                text = (resp.choices[0].message.content if resp.choices else "") or ""
                text = text.strip()
            if not text:
                raise LLMProviderError("The model service is currently unavailable.", "QWEN_EMPTY_RESPONSE")
            return text
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                "LLM response failed; check the API configuration or network.",
                "QWEN_CHAT_FAILED",
                cause=exc,
            ) from exc
