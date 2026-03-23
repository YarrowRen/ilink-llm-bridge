from __future__ import annotations
import json
import os
from pathlib import Path

import yaml

from .types import BotConfig, BridgeConfig, ILinkConfig, LogConfig, ProviderConfig, StorageConfig


def load_config(config_path: str = "config.yaml", credentials_path: str = "credentials.json") -> BridgeConfig:
    """Load config.yaml and merge credentials.json on top."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}\nCopy config.example.yaml to config.yaml and edit it.")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # Merge credentials.json (written by login.py) — takes precedence over config.yaml
    cred_path = Path(credentials_path)
    credentials: dict = {}
    if cred_path.exists():
        with open(cred_path, encoding="utf-8") as f:
            credentials = json.load(f)

    # iLink section
    ilink_raw = raw.get("ilink", {}) or {}
    ilink = ILinkConfig(
        base_url=credentials.get("base_url") or ilink_raw.get("base_url", "") or "https://ilinkai.weixin.qq.com",
        cdn_base_url=ilink_raw.get("cdn_base_url", "https://novac2c.cdn.weixin.qq.com/c2c"),
        token=credentials.get("token") or ilink_raw.get("token", ""),
        route_tag=ilink_raw.get("route_tag", ""),
    )
    if not ilink.token:
        raise ValueError("No iLink token found. Run `python login.py` first to authenticate.")

    # Provider section
    prov_raw = raw.get("provider", {}) or {}
    name = prov_raw.get("name", "openai")
    provider = ProviderConfig(
        name=name,
        api_key=os.environ.get("LLM_API_KEY") or prov_raw.get("api_key", ""),
        model=prov_raw.get("model", ""),
        max_tokens=int(prov_raw.get("max_tokens", 2048)),
        base_url=prov_raw.get("base_url", ""),
    )
    if not provider.api_key:
        raise ValueError(f"No API key for provider '{name}'. Set api_key in config.yaml or LLM_API_KEY env var.")
    if name == "claude" and provider.max_tokens <= 0:
        raise ValueError("Claude provider requires max_tokens > 0 in config.yaml.")
    if name == "dify" and not provider.resolved_base_url():
        raise ValueError("Dify provider requires base_url in config.yaml (e.g. https://api.dify.ai/v1).")

    # Bot section
    bot_raw = raw.get("bot", {}) or {}
    bot = BotConfig(
        system_prompt=bot_raw.get("system_prompt", "You are a helpful assistant."),
        max_history_length=int(bot_raw.get("max_history_length", 20)),
        chunk_size=int(bot_raw.get("chunk_size", 1000)),
        allow_from=bot_raw.get("allow_from") or [],
    )

    # Storage section
    storage_raw = raw.get("storage", {}) or {}
    storage = StorageConfig(
        history_dir=storage_raw.get("history_dir", "./data/history"),
        media_dir=storage_raw.get("media_dir", "./data/media"),
    )

    # Log section
    log_raw = raw.get("log", {}) or {}
    log = LogConfig(level=log_raw.get("level", "info"))

    return BridgeConfig(ilink=ilink, provider=provider, bot=bot, storage=storage, log=log)
