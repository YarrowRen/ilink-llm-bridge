"""Per-message handler: history → LLM → chunked reply."""
from __future__ import annotations
import asyncio
import base64
from pathlib import Path

from ..config.types import BotConfig, ProviderConfig
from ..history.manager import HistoryManager
from ..ilink.api import ILinkClient
from ..ilink.outbound import send_text, start_typing, stop_typing
from ..ilink.types import ITEM_TYPE_IMAGE, ITEM_TYPE_VOICE, WeixinMessage
from ..llm.types import LLMProvider, LLMRequest
from ..util.logger import logger
from .chunker import split_chunks

CHUNK_DELAY = 0.3  # seconds between chunks


class MessageHandler:
    def __init__(
        self,
        client: ILinkClient,
        provider: LLMProvider,
        provider_cfg: ProviderConfig,
        bot_cfg: BotConfig,
        history: HistoryManager,
        media_dir: str,
    ) -> None:
        self.client = client
        self.provider = provider
        self.provider_cfg = provider_cfg
        self.bot_cfg = bot_cfg
        self.history = history
        self.media_dir = media_dir
        # Per-user serialization queue
        self._queues: dict[str, asyncio.Task] = {}

    def enqueue(self, msg: WeixinMessage) -> None:
        """Fire-and-forget per-user serialized processing."""
        user_id = msg.from_user_id
        prev = self._queues.get(user_id)
        task = asyncio.ensure_future(self._chain(prev, msg))
        self._queues[user_id] = task

    async def _chain(self, prev: asyncio.Task | None, msg: WeixinMessage) -> None:
        if prev and not prev.done():
            try:
                await prev
            except Exception:
                pass
        await self._handle(msg)

    async def _handle(self, msg: WeixinMessage) -> None:
        user_id = msg.from_user_id
        context_token = msg.context_token

        if not context_token:
            logger.warning(f"handler: no context_token from {user_id}, skipping")
            return

        # Allow-list check
        if self.bot_cfg.allow_from and user_id not in self.bot_cfg.allow_from:
            logger.info(f"handler: {user_id} not in allow_from, dropping")
            return

        # Extract text
        text = ""
        for item in msg.item_list:
            if item.type == 1 and item.text_item:
                text = item.text_item.get("text", "")
                break
        if not text:
            text = "[用户发送了非文字内容]"

        # Extract image if present
        image_base64 = ""
        image_mime = ""
        for item in msg.item_list:
            if item.type == ITEM_TYPE_IMAGE and item.image_item and item.image_item.media:
                image_base64, image_mime = await self._download_image(item, user_id)
                break

        logger.info(f"← {user_id}: {text[:60]}{'…' if len(text) > 60 else ''}")

        # Typing indicator
        await start_typing(self.client, user_id, context_token)

        try:
            # Build history + LLM request
            self.history.append_user(user_id, text, image_base64, image_mime)
            messages = self.history.build_messages(user_id, self.bot_cfg.system_prompt)

            # For Dify: pass user_id via model field so provider can key conversation_id
            model = self.provider_cfg.model if self.provider_cfg.name != "dify" else user_id
            req = LLMRequest(messages=messages, model=model, max_tokens=self.provider_cfg.max_tokens)

            response = await self.provider.complete(req)

            if response.error and not response.text:
                error_msg = f"⚠️ AI 服务暂时不可用，请稍后重试。\n({response.error[:80]})"
                await send_text(self.client, user_id, error_msg, context_token)
                return

            reply_text = response.text or "（无回复）"
            self.history.append_assistant(user_id, reply_text)

            # Send in chunks
            chunks = split_chunks(reply_text, self.bot_cfg.chunk_size)
            for i, chunk in enumerate(chunks):
                await send_text(self.client, user_id, chunk, context_token)
                logger.info(f"→ {user_id} chunk {i+1}/{len(chunks)}: {chunk[:40]}…")
                if i < len(chunks) - 1:
                    await asyncio.sleep(CHUNK_DELAY)

        except Exception as e:
            logger.error(f"handler error for {user_id}: {e}")
            try:
                await send_text(self.client, user_id, f"⚠️ 处理消息时出错：{str(e)[:100]}", context_token)
            except Exception:
                pass
        finally:
            await stop_typing(self.client, user_id, context_token)

    async def _download_image(self, item, user_id: str) -> tuple[str, str]:
        """Download and base64-encode an inbound image for multimodal LLMs."""
        try:
            from ..cdn.pic_decrypt import download_and_decrypt_buffer
            img = item.image_item
            media = img.media
            if not media or not media.encrypt_query_param:
                return "", ""
            # img.aeskey is a hex string (32 hex chars = 16 bytes); convert to base64
            # img.media.aes_key is already base64-encoded
            if img.aeskey:
                aes_key = base64.b64encode(bytes.fromhex(img.aeskey)).decode()
            else:
                aes_key = media.aes_key
            if not aes_key:
                return "", ""
            buf = await download_and_decrypt_buffer(
                media.encrypt_query_param, aes_key, self.client.cdn_base_url, f"img:{user_id}"
            )
            encoded = base64.b64encode(buf).decode()
            return encoded, "image/jpeg"
        except Exception as e:
            logger.warning(f"handler: image download failed: {e}")
            return "", ""
