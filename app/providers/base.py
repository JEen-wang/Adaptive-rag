from collections.abc import AsyncIterator
from typing import Protocol

from app.schemas.common import TokenUsage


class ChatMessageDict(dict):
    """OpenAI-compatible chat message: role + content."""


class LLMResponse:
    __slots__ = ("content", "usage", "model")

    def __init__(self, content: str, usage: TokenUsage | None = None, model: str = "") -> None:
        self.content = content
        self.usage = usage or TokenUsage()
        self.model = model


class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse: ...

    async def ping(self) -> bool: ...

    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> AsyncIterator[str]:
        """Yield completion tokens. Implemented by DeepSeek and Fake providers."""
        ...


class EmbeddingProvider(Protocol):
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def ping(self) -> bool: ...


class RerankProvider(Protocol):
    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        top_n: int,
    ) -> list[tuple[int, float]]:
        """Return (original_index, relevance_score) sorted by score desc."""
        ...
