from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# ── Message item types ───────────────────────────────────────
MSG_TYPE_USER = 1
MSG_TYPE_BOT  = 2

ITEM_TYPE_TEXT  = 1
ITEM_TYPE_IMAGE = 2
ITEM_TYPE_VOICE = 3
ITEM_TYPE_FILE  = 4
ITEM_TYPE_VIDEO = 5

MSG_STATE_FINISH = 2

TYPING_STATUS_TYPING = 1
TYPING_STATUS_CANCEL = 2

SESSION_EXPIRED_ERRCODE = -14

CHANNEL_VERSION = "1.0.2"


@dataclass
class CDNMedia:
    encrypt_query_param: str = ""
    aes_key: str = ""
    encrypt_type: int = 0


@dataclass
class ImageItem:
    media: CDNMedia | None = None
    thumb_media: CDNMedia | None = None
    aeskey: str = ""       # hex key (inbound)
    mid_size: int = 0


@dataclass
class VoiceItem:
    media: CDNMedia | None = None
    encode_type: int = 0
    playtime: int = 0
    text: str = ""          # voice-to-text (if available)


@dataclass
class FileItem:
    media: CDNMedia | None = None
    file_name: str = ""
    len: str = "0"


@dataclass
class VideoItem:
    media: CDNMedia | None = None
    video_size: int = 0


@dataclass
class RefMessage:
    message_item: MessageItem | None = None
    title: str = ""


@dataclass
class MessageItem:
    type: int = 0
    text_item: dict[str, Any] | None = None
    image_item: ImageItem | None = None
    voice_item: VoiceItem | None = None
    file_item: FileItem | None = None
    video_item: VideoItem | None = None
    ref_msg: RefMessage | None = None


@dataclass
class WeixinMessage:
    seq: int = 0
    message_id: int = 0
    from_user_id: str = ""
    to_user_id: str = ""
    client_id: str = ""
    create_time_ms: int = 0
    session_id: str = ""
    group_id: str = ""
    message_type: int = 0
    message_state: int = 0
    item_list: list[MessageItem] = field(default_factory=list)
    context_token: str = ""


def parse_message(raw: dict[str, Any]) -> WeixinMessage:
    items = []
    for it in raw.get("item_list") or []:
        img = it.get("image_item")
        voice = it.get("voice_item")
        file_ = it.get("file_item")
        video = it.get("video_item")
        ref = it.get("ref_msg")

        def parse_cdn(d: dict | None) -> CDNMedia | None:
            if not d:
                return None
            return CDNMedia(
                encrypt_query_param=d.get("encrypt_query_param", ""),
                aes_key=d.get("aes_key", ""),
                encrypt_type=d.get("encrypt_type", 0),
            )

        items.append(MessageItem(
            type=it.get("type", 0),
            text_item=it.get("text_item"),
            image_item=ImageItem(
                media=parse_cdn(img.get("media") if img else None),
                thumb_media=parse_cdn(img.get("thumb_media") if img else None),
                aeskey=img.get("aeskey", "") if img else "",
                mid_size=img.get("mid_size", 0) if img else 0,
            ) if img else None,
            voice_item=VoiceItem(
                media=parse_cdn(voice.get("media") if voice else None),
                encode_type=voice.get("encode_type", 0) if voice else 0,
                playtime=voice.get("playtime", 0) if voice else 0,
                text=voice.get("text", "") if voice else "",
            ) if voice else None,
            file_item=FileItem(
                media=parse_cdn(file_.get("media") if file_ else None),
                file_name=file_.get("file_name", "") if file_ else "",
                len=str(file_.get("len", "0")) if file_ else "0",
            ) if file_ else None,
            video_item=VideoItem(
                media=parse_cdn(video.get("media") if video else None),
                video_size=video.get("video_size", 0) if video else 0,
            ) if video else None,
        ))

    return WeixinMessage(
        seq=raw.get("seq", 0),
        message_id=raw.get("message_id", 0),
        from_user_id=raw.get("from_user_id", ""),
        to_user_id=raw.get("to_user_id", ""),
        client_id=raw.get("client_id", ""),
        create_time_ms=raw.get("create_time_ms", 0),
        session_id=raw.get("session_id", ""),
        group_id=raw.get("group_id", ""),
        message_type=raw.get("message_type", 0),
        message_state=raw.get("message_state", 0),
        item_list=items,
        context_token=raw.get("context_token", ""),
    )
