from __future__ import annotations
import base64
import json
import os
import struct
import time
from typing import Any

import httpx

from .types import CHANNEL_VERSION, SESSION_EXPIRED_ERRCODE, parse_message, WeixinMessage
from ..util.logger import logger
from ..util.redact import redact_url, redact_body

DEFAULT_LONG_POLL_TIMEOUT = 38.0   # slightly above server's 35s
DEFAULT_API_TIMEOUT       = 15.0
DEFAULT_CONFIG_TIMEOUT    = 10.0


def _random_wechat_uin() -> str:
    uint32 = struct.unpack(">I", os.urandom(4))[0]
    return base64.b64encode(str(uint32).encode()).decode()


def _build_headers(token: str, route_tag: str = "") -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_wechat_uin(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if route_tag:
        headers["SKRouteTag"] = route_tag
    return headers


def _base(url: str) -> str:
    return url.rstrip("/") + "/"


class ILinkClient:
    """Async iLink HTTP client wrapping all bot API endpoints."""

    def __init__(self, base_url: str, token: str, cdn_base_url: str = "", route_tag: str = "") -> None:
        self.base_url = base_url
        self.token = token
        self.cdn_base_url = cdn_base_url
        self.route_tag = route_tag

    def _headers(self) -> dict[str, str]:
        return _build_headers(self.token, self.route_tag)

    def _url(self, path: str) -> str:
        return _base(self.base_url) + path

    async def get_updates(self, get_updates_buf: str = "", timeout: float = DEFAULT_LONG_POLL_TIMEOUT) -> dict[str, Any]:
        body = {"get_updates_buf": get_updates_buf, "base_info": {"channel_version": CHANNEL_VERSION}}
        logger.debug(f"getUpdates buf_len={len(get_updates_buf)}")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self._url("ilink/bot/getupdates"), json=body, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            logger.debug("getUpdates: client-side timeout, returning empty")
            return {"ret": 0, "msgs": [], "get_updates_buf": get_updates_buf}

    async def send_message(self, msg: dict[str, Any]) -> None:
        body = {"msg": msg, "base_info": {"channel_version": CHANNEL_VERSION}}
        logger.debug(f"sendMessage to={msg.get('to_user_id')} body={redact_body(json.dumps(body))}")
        async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client:
            resp = await client.post(self._url("ilink/bot/sendmessage"), json=body, headers=self._headers())
            resp.raise_for_status()

    async def get_upload_url(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {**payload, "base_info": {"channel_version": CHANNEL_VERSION}}
        async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client:
            resp = await client.post(self._url("ilink/bot/getuploadurl"), json=body, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def get_config(self, ilink_user_id: str, context_token: str = "") -> dict[str, Any]:
        body = {"ilink_user_id": ilink_user_id, "context_token": context_token,
                "base_info": {"channel_version": CHANNEL_VERSION}}
        async with httpx.AsyncClient(timeout=DEFAULT_CONFIG_TIMEOUT) as client:
            resp = await client.post(self._url("ilink/bot/getconfig"), json=body, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def send_typing(self, ilink_user_id: str, typing_ticket: str, status: int) -> None:
        body = {"ilink_user_id": ilink_user_id, "typing_ticket": typing_ticket, "status": status,
                "base_info": {"channel_version": CHANNEL_VERSION}}
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CONFIG_TIMEOUT) as client:
                resp = await client.post(self._url("ilink/bot/sendtyping"), json=body, headers=self._headers())
                resp.raise_for_status()
        except Exception as e:
            logger.debug(f"sendTyping failed (non-fatal): {e}")
