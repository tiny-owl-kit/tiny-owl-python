"""ASGI middleware for FastAPI and Starlette. Needs no framework import at runtime."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from ..client import TinyOwl
from ._common import elapsed_ms, report_request

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def _route_template(scope: Scope) -> str | None:
    path = getattr(scope.get("route"), "path", None)
    return path if isinstance(path, str) else None


class TinyOwlASGIMiddleware:
    """Report uncaught exceptions and responses with status >= 400.

    FastAPI: ``app.add_middleware(TinyOwlASGIMiddleware, client=client)``
    """

    def __init__(self, app: ASGIApp, client: TinyOwl) -> None:
        self.app = app
        self.client = client

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        started = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            report_request(
                self.client,
                method=scope["method"],
                path=scope["path"],
                route_template=_route_template(scope),
                status_code=500,
                duration_ms=elapsed_ms(started),
                error_type=type(exc).__name__,
            )
            raise

        report_request(
            self.client,
            method=scope["method"],
            path=scope["path"],
            route_template=_route_template(scope),
            status_code=status_code,
            duration_ms=elapsed_ms(started),
        )
