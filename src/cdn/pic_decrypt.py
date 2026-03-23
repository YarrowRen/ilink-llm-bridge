"""CDN media download and AES-ECB decryption (supports AES-128/192/256)."""
from __future__ import annotations
import base64

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from ..util.logger import logger


def _parse_aes_key(aes_key_b64: str, label: str) -> bytes:
    decoded = base64.b64decode(aes_key_b64)
    if len(decoded) == 16:
        return decoded
    if len(decoded) == 32:
        # base64 of hex-encoded key: decode hex to get 16 raw bytes
        text = decoded.decode("ascii", errors="ignore")
        if all(c in "0123456789abcdefABCDEF" for c in text):
            return bytes.fromhex(text)
    raise ValueError(f"{label}: aes_key must decode to 16 raw bytes or 32-char hex string, got {len(decoded)} bytes")


async def download_and_decrypt_buffer(
    encrypted_query_param: str,
    aes_key: str,
    cdn_base_url: str,
    label: str,
) -> bytes:
    key = _parse_aes_key(aes_key, label)
    url = f"{cdn_base_url}/download?encrypted_query_param={encrypted_query_param}"
    logger.debug(f"{label}: CDN download url={url[:80]}…")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    ciphertext = resp.content
    cipher = AES.new(key, AES.MODE_ECB)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)
