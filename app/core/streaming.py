"""Request-scoped token sink for SSE token events during generate_node."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token

TokenSink = Callable[[str], Awaitable[None]]

_token_sink: ContextVar[TokenSink | None] = ContextVar("token_sink", default=None)


def get_token_sink() -> TokenSink | None:
    return _token_sink.get()


def set_token_sink(sink: TokenSink | None) -> Token:
    return _token_sink.set(sink)


def reset_token_sink(token: Token) -> None:
    _token_sink.reset(token)
