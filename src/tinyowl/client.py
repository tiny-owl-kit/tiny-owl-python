"""Main TinyOwl client class."""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from .errors import TinyOwlValidationError
from .security import create_secure_headers
from .trace import new_trace_id, validate_trace_id
from .transport import _warn_if_insecure, send_event

logger = logging.getLogger(__name__)

Severity = Literal["info", "warning", "error"]
_VALID_SEVERITIES: tuple[str, ...] = ("info", "warning", "error")

_DEFAULT_BASE_URL = "https://be.tiny-owl-kit.io/api"
_DEFAULT_TIMEOUT = 5.0


class TinyOwl:
    """TinyOwl observability client.

    Usage::

        import os
        from tinyowl import TinyOwl

        client = TinyOwl(
            api_key=os.environ["TINYOWL_API_KEY"],
            project_secret=os.environ["TINYOWL_PROJECT_SECRET"],
        )
        client.info("App started", {"version": "1.0.0"})
    """

    def __init__(
        self,
        api_key: str,
        project_secret: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        auto_trace_id: bool = True,
        default_context: Optional[Dict[str, Any]] = None,
        # internal — used by with_context()
        _instance_trace_id: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise TinyOwlValidationError("api_key is required")
        if not project_secret:
            raise TinyOwlValidationError("project_secret is required")

        self._api_key = api_key
        self._project_secret = project_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._auto_trace_id = auto_trace_id
        self._default_context: Dict[str, Any] = dict(default_context or {})

        _warn_if_insecure(self._base_url)

        if _instance_trace_id is not None:
            self._instance_trace_id: Optional[str] = _instance_trace_id
        else:
            self._instance_trace_id = new_trace_id() if auto_trace_id else None

    # ------------------------------------------------------------------
    # Convenience severity methods
    # ------------------------------------------------------------------

    def info(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log an *info* severity event."""
        return self.log(message, severity="info", context=context)

    def warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a *warning* severity event."""
        return self.log(message, severity="warning", context=context)

    def error(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log an *error* severity event."""
        return self.log(message, severity="error", context=context)

    # ------------------------------------------------------------------
    # Core log method
    # ------------------------------------------------------------------

    def log(
        self,
        message: str,
        *,
        severity: Severity = "info",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send an event to TinyOwl.

        Args:
            message:  Human-readable description of the event (required).
            severity: One of ``"info"``, ``"warning"``, or ``"error"``.
            context:  Arbitrary key/value pairs merged with ``default_context``.
                      Call-site keys win on conflict.

        Returns:
            Parsed JSON response from the backend.

        Raises:
            TinyOwlValidationError: On invalid inputs.
            TinyOwlAuthError:       On 401/403 responses.
            TinyOwlTimeoutError:    On request timeout.
            TinyOwlNetworkError:    On connection failure.
        """
        if not message or not isinstance(message, str):
            raise TinyOwlValidationError("message is required and must be a non-empty string")
        if severity not in _VALID_SEVERITIES:
            raise TinyOwlValidationError(
                f"Invalid severity '{severity}'. Must be one of: {', '.join(_VALID_SEVERITIES)}"
            )

        call_context = dict(context or {})
        merged_context: Dict[str, Any] = {**self._default_context, **call_context}

        # Resolve traceId: explicit in merged_context > instance traceId
        raw_trace_id = merged_context.pop("traceId", None)
        resolved_trace_id: Optional[str] = None

        if isinstance(raw_trace_id, str):
            if validate_trace_id(raw_trace_id):
                resolved_trace_id = raw_trace_id
            else:
                logger.warning(
                    "TinyOwl SDK: Invalid traceId format '%s' — ignored. "
                    "Must match [A-Za-z0-9._:-]{1,128}.",
                    raw_trace_id[:40],
                )
        elif self._instance_trace_id is not None:
            resolved_trace_id = self._instance_trace_id

        # Build wire body
        payload: Dict[str, Any] = {
            "apiKey": self._api_key,
            "message": message,
            "severity": severity,
            "context": merged_context,
        }
        if resolved_trace_id is not None:
            payload["traceId"] = resolved_trace_id

        # Build HMAC security headers (signs message/severity/context/[traceId])
        headers = {
            "Content-Type": "application/json",
            **create_secure_headers(
                message=message,
                severity=severity,
                context=merged_context,
                project_secret=self._project_secret,
                trace_id=resolved_trace_id,
            ),
        }

        return send_event(
            base_url=self._base_url,
            payload=payload,
            headers=headers,
            timeout=self._timeout,
        )

    # ------------------------------------------------------------------
    # Child scope
    # ------------------------------------------------------------------

    def with_context(self, partial: Dict[str, Any]) -> "TinyOwl":
        """Return a new child client with merged default context and a fresh traceId.

        The parent instance is never modified.  If *partial* contains a ``traceId``
        key it is used as the child's instance trace ID (after validation); otherwise
        a fresh UUID v4 is generated.
        """
        raw_trace_id = partial.get("traceId")
        child_trace_id: Optional[str] = None

        if isinstance(raw_trace_id, str):
            if validate_trace_id(raw_trace_id):
                child_trace_id = raw_trace_id
            else:
                logger.warning(
                    "TinyOwl SDK: Invalid traceId in with_context '%s' — "
                    "a fresh traceId will be generated.",
                    str(raw_trace_id)[:40],
                )
                child_trace_id = new_trace_id() if self._auto_trace_id else None
        elif self._auto_trace_id:
            child_trace_id = new_trace_id()

        partial_without_trace = {k: v for k, v in partial.items() if k != "traceId"}
        merged_default: Dict[str, Any] = {**self._default_context, **partial_without_trace}

        return TinyOwl(
            api_key=self._api_key,
            project_secret=self._project_secret,
            base_url=self._base_url,
            timeout=self._timeout,
            auto_trace_id=self._auto_trace_id,
            default_context=merged_default,
            _instance_trace_id=child_trace_id,
        )

    # ------------------------------------------------------------------
    # Introspection (no secrets leaked)
    # ------------------------------------------------------------------

    def get_config(self) -> Dict[str, Any]:
        """Return SDK configuration for debugging. Never exposes secrets or API keys."""
        cfg: Dict[str, Any] = {
            "base_url": self._base_url,
            "timeout": self._timeout,
            "auto_trace_id": self._auto_trace_id,
            "has_api_key": bool(self._api_key),
            "has_project_secret": bool(self._project_secret),
        }
        if self._instance_trace_id is not None:
            cfg["instance_trace_id"] = self._instance_trace_id
        return cfg
