"""Google Gemini provider."""
from __future__ import annotations

import httpx

from ..types import LLMProvider, LLMRequest, LLMResponse
from ...util.logger import logger

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _to_parts(content) -> list[dict]:
    if isinstance(content, str):
        return [{"text": content}]
    parts = []
    for p in content:
        if p.get("type") == "text":
            parts.append({"text": p["text"]})
        elif p.get("type") == "image_url":
            url: str = p["image_url"]["url"]
            if url.startswith("data:"):
                meta, data = url[5:].split(",", 1)
                mime = meta.split(";")[0]
                parts.append({"inline_data": {"mime_type": mime, "data": data}})
    return parts or [{"text": ""}]


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "gemini"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system_instruction = None
        contents = []
        for m in request.messages:
            if m["role"] == "system":
                system_instruction = {"parts": [{"text": m["content"]}]}
            else:
                # Gemini uses "model" not "assistant"
                role = "model" if m["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": _to_parts(m["content"])})

        body: dict = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": request.max_tokens},
        }
        if system_instruction:
            body["system_instruction"] = system_instruction

        url = f"{BASE}/{request.model}:generateContent?key={self.api_key}"
        logger.debug(f"[gemini] POST model={request.model}")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=body, headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0].get("text", "")
                return LLMResponse(text=text)
        except httpx.HTTPStatusError as e:
            msg = f"Gemini API error {e.response.status_code}: {e.response.text[:200]}"
            logger.error(msg)
            return LLMResponse(text="", error=msg)
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return LLMResponse(text="", error=str(e))
