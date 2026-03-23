"""Dify provider — SSE streaming, conversation_id per user."""
from __future__ import annotations

import json

import httpx

from ..types import LLMProvider, LLMRequest, LLMResponse
from ...util.logger import logger


class DifyProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # Per-user conversation IDs (in-memory)
        self._conversation_ids: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "dify"

    def _user_id_from_messages(self, messages: list[dict]) -> str:
        """Extract a stable user identifier from the messages list (last user message role)."""
        return "default-user"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Extract the last user message text
        query = ""
        for m in reversed(request.messages):
            if m["role"] == "user":
                content = m["content"]
                query = content if isinstance(content, str) else (content[0].get("text", "") if content else "")
                break

        # Use a stable key — caller should pass user_id via model field convention or we use a default
        user_key = request.model or "user"
        conversation_id = self._conversation_ids.get(user_key, "")

        body = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming",
            "user": user_key,
        }
        if conversation_id:
            body["conversation_id"] = conversation_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat-messages"
        logger.debug(f"[dify] POST {url} conversation_id={conversation_id or 'new'}")

        try:
            accumulated = ""
            new_conversation_id = conversation_id

            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    if resp.status_code == 404 and conversation_id:
                        # Stale conversation_id — retry as new conversation
                        logger.warning("[dify] conversation_id stale, retrying as new")
                        self._conversation_ids.pop(user_key, None)
                        body.pop("conversation_id", None)
                        new_conversation_id = ""
                        async with client.stream("POST", url, json=body, headers=headers) as resp2:
                            resp2.raise_for_status()
                            accumulated, new_conversation_id = await self._parse_sse(resp2, accumulated)
                    else:
                        resp.raise_for_status()
                        accumulated, new_conversation_id = await self._parse_sse(resp, accumulated)

            if new_conversation_id:
                self._conversation_ids[user_key] = new_conversation_id

            return LLMResponse(text=accumulated)

        except httpx.HTTPStatusError as e:
            msg = f"Dify API error {e.response.status_code}: {e.response.text[:200]}"
            logger.error(msg)
            return LLMResponse(text="", error=msg)
        except Exception as e:
            logger.error(f"Dify error: {e}")
            return LLMResponse(text="", error=str(e))

    @staticmethod
    async def _parse_sse(resp: httpx.Response, accumulated: str) -> tuple[str, str]:
        conversation_id = ""
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event = data.get("event", "")
            if cid := data.get("conversation_id"):
                conversation_id = cid
            if event == "message":
                accumulated += data.get("answer", "")
            elif event == "message_end":
                break
            elif event == "error":
                raise RuntimeError(f"Dify stream error: {data.get('message', 'unknown')}")
        return accumulated, conversation_id
