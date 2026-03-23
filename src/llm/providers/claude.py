"""Anthropic Claude provider."""
from __future__ import annotations

import httpx

from ..types import LLMProvider, LLMRequest, LLMResponse
from ...util.logger import logger

ANTHROPIC_VERSION = "2023-06-01"


def _transform_content(content) -> list[dict] | str:
    """Convert generic content parts to Claude's format."""
    if isinstance(content, str):
        return content
    result = []
    for part in content:
        if part.get("type") == "text":
            result.append({"type": "text", "text": part["text"]})
        elif part.get("type") == "image_url":
            url: str = part["image_url"]["url"]
            if url.startswith("data:"):
                # data:image/jpeg;base64,xxxx
                meta, data = url[5:].split(",", 1)
                mime = meta.split(";")[0]
                result.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}})
            else:
                result.append({"type": "image", "source": {"type": "url", "url": url}})
    return result if result else ""


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "claude"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system = ""
        messages = []
        for m in request.messages:
            if m["role"] == "system":
                system = m["content"] if isinstance(m["content"], str) else str(m["content"])
            else:
                role = m["role"]  # "user" | "assistant"
                messages.append({"role": role, "content": _transform_content(m["content"])})

        body: dict = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        logger.debug(f"[claude] POST messages model={request.model}")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                text = data["content"][0]["text"] if data.get("content") else ""
                return LLMResponse(text=text)
        except httpx.HTTPStatusError as e:
            msg = f"Claude API error {e.response.status_code}: {e.response.text[:200]}"
            logger.error(msg)
            return LLMResponse(text="", error=msg)
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return LLMResponse(text="", error=str(e))
