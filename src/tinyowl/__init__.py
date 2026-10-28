"""TinyOwl Python SDK — public surface."""

from .client import TinyOwl
from .errors import (
    TinyOwlAuthError,
    TinyOwlError,
    TinyOwlNetworkError,
    TinyOwlTimeoutError,
    TinyOwlValidationError,
)

__version__ = "0.2.0"
__all__ = [
    "TinyOwl",
    "TinyOwlError",
    "TinyOwlAuthError",
    "TinyOwlTimeoutError",
    "TinyOwlNetworkError",
    "TinyOwlValidationError",
    "__version__",
]
