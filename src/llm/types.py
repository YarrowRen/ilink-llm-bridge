from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMRequest:
    messages: list[dict]
    model: str
    max_tokens: int = 2048


@dataclass
class LLMResponse:
    text: str
    error: str = ""


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
