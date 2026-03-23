from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Credentials:
    token: str
    base_url: str
    bot_id: str = ""
    user_id: str = ""
    saved_at: str = ""

    def save(self, path: str = "credentials.json") -> None:
        self.saved_at = datetime.now(timezone.utc).isoformat()
        Path(path).write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Credentials saved to {path}")

    @classmethod
    def load(cls, path: str = "credentials.json") -> "Credentials":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
