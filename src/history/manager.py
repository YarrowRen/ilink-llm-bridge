from __future__ import annotations
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..util.logger import logger


@dataclass
class HistoryEntry:
    role: str           # "user" | "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    image_base64: str = ""
    image_mime: str = ""


@dataclass
class ConversationHistory:
    user_id: str
    entries: list[HistoryEntry] = field(default_factory=list)
    last_active_at: float = field(default_factory=time.time)


class HistoryManager:
    def __init__(self, history_dir: str, max_length: int = 20) -> None:
        self.history_dir = Path(history_dir)
        self.max_length = max_length
        self._cache: dict[str, ConversationHistory] = {}
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, user_id: str) -> str:
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    def _path(self, user_id: str) -> Path:
        return self.history_dir / f"{self._key(user_id)}.json"

    def get(self, user_id: str) -> ConversationHistory:
        if user_id in self._cache:
            return self._cache[user_id]
        path = self._path(user_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entries = [HistoryEntry(**e) for e in data.get("entries", [])]
                h = ConversationHistory(
                    user_id=user_id,
                    entries=entries,
                    last_active_at=data.get("last_active_at", time.time()),
                )
                self._cache[user_id] = h
                return h
            except Exception as e:
                logger.warning(f"history: failed to load {path}: {e}")
        h = ConversationHistory(user_id=user_id)
        self._cache[user_id] = h
        return h

    def append_user(self, user_id: str, text: str, image_base64: str = "", image_mime: str = "") -> None:
        h = self.get(user_id)
        h.entries.append(HistoryEntry(role="user", content=text, image_base64=image_base64, image_mime=image_mime))
        h.last_active_at = time.time()
        self._trim(h)

    def append_assistant(self, user_id: str, text: str) -> None:
        h = self.get(user_id)
        h.entries.append(HistoryEntry(role="assistant", content=text))
        h.last_active_at = time.time()
        self._trim(h)
        self._save(h)

    def _trim(self, h: ConversationHistory) -> None:
        if len(h.entries) > self.max_length:
            h.entries = h.entries[-self.max_length:]

    def _save(self, h: ConversationHistory) -> None:
        try:
            data = {"user_id": h.user_id, "entries": [asdict(e) for e in h.entries],
                    "last_active_at": h.last_active_at}
            self._path(h.user_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"history: failed to save for {h.user_id}: {e}")

    def build_messages(self, user_id: str, system_prompt: str) -> list[dict]:
        """Build the message list to send to the LLM."""
        msgs: list[dict] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        h = self.get(user_id)
        for e in h.entries:
            if e.image_base64:
                content = [
                    {"type": "text", "text": e.content},
                    {"type": "image_url", "image_url": {"url": f"data:{e.image_mime};base64,{e.image_base64}"}},
                ]
            else:
                content = e.content
            msgs.append({"role": e.role, "content": content})
        return msgs
