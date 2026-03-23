"""Main long-poll loop."""
from __future__ import annotations
import asyncio
import os
from pathlib import Path

from ..config.types import BridgeConfig
from ..ilink.api import ILinkClient
from ..ilink.session_guard import (
    SESSION_EXPIRED_ERRCODE, is_session_paused, pause_session, remaining_pause_seconds
)
from ..ilink.types import MSG_TYPE_USER, parse_message
from ..util.logger import logger
from .handler import MessageHandler

MAX_CONSECUTIVE_FAILURES = 3
BACKOFF_DELAY = 30.0
RETRY_DELAY   = 2.0
BUF_FILE      = "data/sync_buf.txt"


def _load_buf() -> str:
    try:
        return Path(BUF_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _save_buf(buf: str) -> None:
    Path(BUF_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(BUF_FILE).write_text(buf, encoding="utf-8")


async def run_loop(cfg: BridgeConfig, handler: MessageHandler) -> None:
    client = handler.client
    get_updates_buf = _load_buf()
    if get_updates_buf:
        logger.info(f"Resuming from saved sync buffer ({len(get_updates_buf)} chars)")
    else:
        logger.info("Starting fresh (no saved sync buffer)")

    consecutive_failures = 0
    account_id = "default"  # single-account bridge

    logger.info(f"Bridge running — provider={cfg.provider.name} model={cfg.provider.model}")
    logger.info("Waiting for WeChat messages…")

    while True:
        if is_session_paused(account_id):
            remaining = remaining_pause_seconds(account_id)
            logger.warning(f"Session paused. Waiting {remaining/60:.0f} min…")
            await asyncio.sleep(min(remaining, 60))
            continue

        try:
            resp = await client.get_updates(get_updates_buf=get_updates_buf)
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"getUpdates error ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(f"Backing off {BACKOFF_DELAY}s after {MAX_CONSECUTIVE_FAILURES} failures")
                consecutive_failures = 0
                await asyncio.sleep(BACKOFF_DELAY)
            else:
                await asyncio.sleep(RETRY_DELAY)
            continue

        ret = resp.get("ret", 0)
        errcode = resp.get("errcode", 0)

        # Session expired
        if errcode == SESSION_EXPIRED_ERRCODE or ret == SESSION_EXPIRED_ERRCODE:
            pause_session(account_id)
            remaining = remaining_pause_seconds(account_id)
            logger.error(f"Session expired (errcode {SESSION_EXPIRED_ERRCODE}). Paused for {remaining/60:.0f} min. Re-run login.py to fix.")
            await asyncio.sleep(min(remaining, 60))
            continue

        if ret != 0 or (errcode != 0 and errcode is not None):
            consecutive_failures += 1
            logger.warning(f"getUpdates non-zero ret={ret} errcode={errcode} msg={resp.get('errmsg','')} ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                consecutive_failures = 0
                await asyncio.sleep(BACKOFF_DELAY)
            else:
                await asyncio.sleep(RETRY_DELAY)
            continue

        consecutive_failures = 0

        new_buf = resp.get("get_updates_buf", "")
        if new_buf and new_buf != get_updates_buf:
            get_updates_buf = new_buf
            _save_buf(get_updates_buf)

        for raw_msg in resp.get("msgs") or []:
            msg = parse_message(raw_msg)
            if msg.message_type != MSG_TYPE_USER:
                continue  # skip bot's own messages
            handler.enqueue(msg)
