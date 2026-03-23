"""OpenAI-compatible provider — covers OpenAI, Qwen, Grok, Seed/Doubao."""
from __future__ import annotations

import httpx

from ..types import LLMProvider, LLMRequest, LLMResponse
from ...util.logger import logger


class OpenAICompatProvider(LLMProvider):
    def __init__(self, provider_name: str, base_url: str, api_key: str) -> None:
        self._name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @property
    def name(self) -> str:
        return self._name

    async def complete(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
        }
        logger.debug(f"[{self._name}] POST {url} model={request.model}")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"] or ""
                return LLMResponse(text=text)
        except httpx.HTTPStatusError as e:
            msg = f"{self._name} API error {e.response.status_code}: {e.response.text[:200]}"
            logger.error(msg)
            return LLMResponse(text="", error=msg)
        except Exception as e:
            logger.error(f"{self._name} error: {e}")
            return LLMResponse(text="", error=str(e))
