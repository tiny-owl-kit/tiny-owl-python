"""Low-level HTTP transport to the TinyOwl ingest endpoint."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, Timeout

from .errors import TinyOwlAuthError, TinyOwlError, TinyOwlNetworkError, TinyOwlServerError, TinyOwlTimeoutError

logger = logging.getLogger(__name__)

_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _warn_if_insecure(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme == "http" and parsed.hostname not in _LOCALHOST_HOSTS:
        logger.warning(
            "TinyOwl SDK: base_url uses plain HTTP over a non-localhost host. "
            "Use HTTPS in production to protect your credentials (OWASP A02)."
        )


def send_event(
    base_url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout: float,
) -> Dict[str, Any]:
    """POST *payload* to ``{base_url}/ingest`` and return the parsed JSON response.

    Raises:
        TinyOwlAuthError:    on 401/403
        TinyOwlServerError:  on 5xx
        TinyOwlTimeoutError: on request timeout
        TinyOwlNetworkError: on connection failure
    """
    url = base_url.rstrip("/") + "/ingest"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except Timeout as exc:
        raise TinyOwlTimeoutError(f"Request timed out after {timeout}s") from exc
    except ConnectionError as exc:
        raise TinyOwlNetworkError(f"Connection failed: {exc}", cause=exc) from exc

    if response.status_code in (401, 403):
        body = _try_json(response)
        msg = body.get("message", response.text) if body else response.text
        raise TinyOwlAuthError(str(msg), status_code=response.status_code)

    if response.status_code >= 500:
        raise TinyOwlServerError(
            f"Server error {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
        )

    if not response.ok:
        body = _try_json(response)
        msg = body.get("message", response.text) if body else response.text
        raise TinyOwlError(f"HTTP {response.status_code}: {msg}")

    result: Dict[str, Any] = response.json()
    return result


def _try_json(response: requests.Response) -> Optional[Dict[str, Any]]:
    try:
        return response.json()  # type: ignore[no-any-return]
    except Exception:
        return None
