"""TinyOwl error hierarchy."""

from __future__ import annotations


class TinyOwlError(Exception):
    """Base class for all TinyOwl SDK errors."""


class TinyOwlValidationError(TinyOwlError):
    """Raised when input validation fails (bad message, severity, traceId…)."""


class TinyOwlAuthError(TinyOwlError):
    """Raised on 401/403 responses — invalid API key, signature mismatch, etc."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


class TinyOwlTimeoutError(TinyOwlError):
    """Raised when the HTTP request times out."""


class TinyOwlNetworkError(TinyOwlError):
    """Raised for connection-level failures (DNS, refused, etc.)."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class TinyOwlServerError(TinyOwlError):
    """Raised on 5xx responses."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
