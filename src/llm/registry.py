from __future__ import annotations

from ..config.types import ProviderConfig
from .types import LLMProvider
from .providers.openai_compat import OpenAICompatProvider
from .providers.claude import ClaudeProvider
from .providers.gemini import GeminiProvider
from .providers.dify import DifyProvider

# OpenAI-compatible providers — only differ by base_url
_OPENAI_COMPAT = {"openai", "qwen", "grok", "seed"}


def create_provider(config: ProviderConfig) -> LLMProvider:
    name = config.name
    if name in _OPENAI_COMPAT:
        return OpenAICompatProvider(
            provider_name=name,
            base_url=config.resolved_base_url(),
            api_key=config.api_key,
        )
    if name == "claude":
        return ClaudeProvider(api_key=config.api_key)
    if name == "gemini":
        return GeminiProvider(api_key=config.api_key)
    if name == "dify":
        return DifyProvider(base_url=config.resolved_base_url(), api_key=config.api_key)
    raise ValueError(f"Unknown provider: {name!r}. Supported: openai, claude, gemini, dify, qwen, grok, seed")
