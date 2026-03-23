from __future__ import annotations
from urllib.parse import urlparse


def redact_token(token: str | None, prefix_len: int = 6) -> str:
    if not token:
        return "(none)"
    if len(token) <= prefix_len:
        return f"****(len={len(token)})"
    return f"{token[:prefix_len]}…(len={len(token)})"


def redact_body(body: str | None, max_len: int = 200) -> str:
    if not body:
        return "(empty)"
    if len(body) <= max_len:
        return body
    return f"{body[:max_len]}…(truncated, totalLen={len(body)})"


def redact_url(raw_url: str) -> str:
    try:
        u = urlparse(raw_url)
        base = f"{u.scheme}://{u.netloc}{u.path}"
        return f"{base}?<redacted>" if u.query else base
    except Exception:
        return raw_url[:80]
