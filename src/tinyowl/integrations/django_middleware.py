"""Django middleware. Requires the ``django`` extra."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpRequest, HttpResponse

from ..client import TinyOwl
from ._common import elapsed_ms, report_request

_ERROR_ATTR = "_tinyowl_error"
_HANDLED_EXCEPTIONS = (Http404, PermissionDenied, SuspiciousOperation)


def _client_from_settings() -> TinyOwl:
    client: Any = getattr(settings, "TINYOWL_CLIENT", None)
    if client is not None:
        return client  # type: ignore[no-any-return]
    options: Any = getattr(settings, "TINYOWL", None)
    if isinstance(options, dict):
        return TinyOwl(**options)
    raise ImproperlyConfigured(
        "Set TINYOWL_CLIENT (a TinyOwl instance) or TINYOWL (TinyOwl kwargs) "
        "in settings to use TinyOwlDjangoMiddleware."
    )


def _route_template(request: HttpRequest) -> str | None:
    match = request.resolver_match
    route = getattr(match, "route", None) if match is not None else None
    if not isinstance(route, str) or route.startswith("^"):
        return None
    return "/" + route.lstrip("/")


class TinyOwlDjangoMiddleware:
    """Add to ``MIDDLEWARE``. Reports responses with status >= 400.

    Configure ``TINYOWL_CLIENT`` (a TinyOwl instance) or ``TINYOWL`` (a dict of TinyOwl kwargs).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.client = _client_from_settings()

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        if not isinstance(exception, _HANDLED_EXCEPTIONS):
            setattr(request, _ERROR_ATTR, exception)
        return None

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started = time.perf_counter()
        response = self.get_response(request)
        error: Exception | None = getattr(request, _ERROR_ATTR, None)
        report_request(
            self.client,
            method=request.method or "",
            path=request.path,
            route_template=_route_template(request),
            status_code=response.status_code,
            duration_ms=elapsed_ms(started),
            error_type=type(error).__name__ if error is not None else None,
        )
        return response
