"""Flask integration. Requires the ``flask`` extra."""

from __future__ import annotations

import time
from typing import Any

from flask import Flask, Response, g, request
from flask.signals import got_request_exception

from ..client import TinyOwl
from ._common import elapsed_ms, report_request

_STARTED_ATTR = "tinyowl_started"
_ERROR_ATTR = "tinyowl_error"


class TinyOwlFlask:
    """Report uncaught exceptions and responses with status >= 400.

    ``TinyOwlFlask(app, client)`` registers the hooks on *app*. Use
    ``TinyOwlFlask(None, client)`` and call ``init_app(app)`` later for the factory pattern.
    """

    def __init__(self, app: Flask | None, client: TinyOwl) -> None:
        self.client = client
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.before_request(self._start)
        app.after_request(self._finish)
        got_request_exception.connect(self._on_exception, app)

    def _start(self) -> None:
        setattr(g, _STARTED_ATTR, time.perf_counter())

    def _on_exception(self, sender: Any, exception: BaseException, **extra: Any) -> None:
        setattr(g, _ERROR_ATTR, exception)

    def _finish(self, response: Response) -> Response:
        started = getattr(g, _STARTED_ATTR, None)
        error = getattr(g, _ERROR_ATTR, None)
        rule = request.url_rule
        report_request(
            self.client,
            method=request.method,
            path=request.path,
            route_template=rule.rule if rule is not None else None,
            status_code=response.status_code,
            duration_ms=elapsed_ms(started) if started is not None else 0.0,
            error_type=type(error).__name__ if error is not None else None,
        )
        return response
