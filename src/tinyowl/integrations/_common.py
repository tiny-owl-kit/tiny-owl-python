"""Shared request-reporting logic for the framework middleware."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

from ..client import Severity, TinyOwl

logger = logging.getLogger(__name__)

_QUEUE_SIZE = 1000

_Event = tuple[TinyOwl, str, Severity, dict[str, Any]]


class _EventDispatcher:
    """Sends events on one daemon thread so the request path never waits for the network."""

    def __init__(self, maxsize: int) -> None:
        self._queue: queue.Queue[_Event] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._dropping = False

    def submit(self, event: _Event) -> None:
        self._ensure_worker()
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            if not self._dropping:
                self._dropping = True
                logger.warning("TinyOwl SDK: event queue is full, dropping events.")
            return
        self._dropping = False

    def flush(self) -> None:
        self._queue.join()

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="tinyowl-dispatcher", daemon=True
                )
                self._thread.start()

    def _run(self) -> None:
        while True:
            client, message, severity, context = self._queue.get()
            try:
                client.log(message, severity=severity, context=context)
            except Exception:
                logger.warning("TinyOwl SDK: could not send request event.")
            finally:
                self._queue.task_done()


_dispatcher = _EventDispatcher(maxsize=_QUEUE_SIZE)


def flush_events() -> None:
    """Block until every queued event has been handed to its client. Intended for tests."""
    _dispatcher.flush()


def elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def report_request(
    client: TinyOwl,
    *,
    method: str,
    path: str,
    route_template: str | None,
    status_code: int,
    duration_ms: float,
    error_type: str | None = None,
) -> None:
    """Queue one event for an uncaught exception or a response with status >= 400.

    ``error_type`` is the exception class name for uncaught exceptions. Only request
    metadata is sent. Never pass the body, query string, headers or cookies.
    Returns immediately; SDK failures are handled on the dispatcher thread.
    """
    uncaught = error_type is not None
    if not uncaught and status_code < 400:
        return

    severity: Severity = "error" if uncaught or status_code >= 500 else "warning"
    message = f"Unhandled exception: {error_type}" if uncaught else f"HTTP {status_code}"
    context: dict[str, Any] = {
        "method": method,
        "endpoint": route_template or path,
        "statusCode": status_code,
        "durationMs": round(duration_ms, 2),
    }
    if route_template is not None:
        context["routeTemplate"] = route_template

    try:
        _dispatcher.submit((client, message, severity, context))
    except Exception:
        logger.warning("TinyOwl SDK: could not queue request event.")
