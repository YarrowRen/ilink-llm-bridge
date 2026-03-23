"""Split long text into WeChat-friendly chunks."""
from __future__ import annotations


def split_chunks(text: str, max_len: int = 1000) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_len:
        # Try paragraph boundary first
        idx = remaining.rfind("\n\n", 0, max_len)
        if idx <= 0:
            # Try sentence boundary
            for sep in ("。", "！", "？", ".", "!", "?", "\n"):
                idx = remaining.rfind(sep, 0, max_len)
                if idx > 0:
                    idx += len(sep)
                    break
        if idx <= 0:
            # Try last space
            idx = remaining.rfind(" ", 0, max_len)
        if idx <= 0:
            idx = max_len
        chunks.append(remaining[:idx].strip())
        remaining = remaining[idx:].strip()

    if remaining:
        chunks.append(remaining)

    return [c for c in chunks if c]
