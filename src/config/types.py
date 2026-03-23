from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ProviderName = Literal["openai", "claude", "gemini", "dify", "qwen", "grok", "seed"]

PROVIDER_DEFAULT_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "qwen":   "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "grok":   "https://api.x.ai/v1",
    "seed":   "https://ark.cn-beijing.volces.com/api/v3",
    "claude": "https://api.anthropic.com/v1/messages",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
    "dify":   "",  # must be provided by user
}


@dataclass
class ProviderConfig:
    name: ProviderName
    api_key: str
    model: str = ""
    max_tokens: int = 2048
    base_url: str = ""

    def resolved_base_url(self) -> str:
        return self.base_url or PROVIDER_DEFAULT_URLS.get(self.name, "")


@dataclass
class ILinkConfig:
    base_url: str = "https://ilinkai.weixin.qq.com"
    cdn_base_url: str = "https://novac2c.cdn.weixin.qq.com/c2c"
    token: str = ""
    route_tag: str = ""


@dataclass
class BotConfig:
    system_prompt: str = "You are a helpful assistant."
    max_history_length: int = 20
    chunk_size: int = 1000
    allow_from: list[str] = field(default_factory=list)


@dataclass
class StorageConfig:
    history_dir: str = "./data/history"
    media_dir: str = "./data/media"


@dataclass
class LogConfig:
    level: str = "info"


@dataclass
class BridgeConfig:
    ilink: ILinkConfig
    provider: ProviderConfig
    bot: BotConfig
    storage: StorageConfig
    log: LogConfig
