from __future__ import annotations
import uuid

from .api import ILinkClient
from .types import (
    ITEM_TYPE_TEXT, MSG_STATE_FINISH, MSG_TYPE_BOT,
    TYPING_STATUS_CANCEL, TYPING_STATUS_TYPING,
)
from ..util.logger import logger

# Per-user typing ticket cache
_typing_tickets: dict[str, str] = {}


async def send_text(client: ILinkClient, to_user_id: str, text: str, context_token: str) -> None:
    if not context_token:
        logger.error(f"send_text: missing context_token for {to_user_id}, cannot send")
        return
    msg = {
        "to_user_id": to_user_id,
        "client_id": str(uuid.uuid4()),
        "message_type": MSG_TYPE_BOT,
        "message_state": MSG_STATE_FINISH,
        "context_token": context_token,
        "item_list": [{"type": ITEM_TYPE_TEXT, "text_item": {"text": text}}],
    }
    await client.send_message(msg)


async def start_typing(client: ILinkClient, user_id: str, context_token: str) -> None:
    ticket = await _get_typing_ticket(client, user_id, context_token)
    if ticket:
        await client.send_typing(user_id, ticket, TYPING_STATUS_TYPING)


async def stop_typing(client: ILinkClient, user_id: str, context_token: str) -> None:
    ticket = _typing_tickets.get(user_id)
    if ticket:
        await client.send_typing(user_id, ticket, TYPING_STATUS_CANCEL)


async def _get_typing_ticket(client: ILinkClient, user_id: str, context_token: str) -> str:
    if user_id in _typing_tickets:
        return _typing_tickets[user_id]
    try:
        resp = await client.get_config(user_id, context_token)
        ticket = resp.get("typing_ticket", "")
        if ticket:
            _typing_tickets[user_id] = ticket
        return ticket
    except Exception as e:
        logger.debug(f"get_config failed (non-fatal): {e}")
        return ""
