# TinyOwl Python SDK

[![PyPI version](https://badge.fury.io/py/tinyowl-observability.svg)](https://pypi.org/project/tinyowl-observability/)
[![Python](https://img.shields.io/pypi/pyversions/tinyowl-observability)](https://pypi.org/project/tinyowl-observability/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Official Python SDK for [TinyOwl](https://tiny-owl-kit.io) — lightweight observability and event logging with enterprise-grade HMAC-SHA256 security.

## Installation

```bash
pip install tinyowl-observability
```

## Quick start

```python
import os
from tinyowl import TinyOwl

client = TinyOwl(
    api_key=os.environ["TINYOWL_API_KEY"],
    project_secret=os.environ["TINYOWL_PROJECT_SECRET"],
)

client.info("App started", {"version": "1.0.0"})
client.warning("Disk space low", {"available_gb": 1.2})
client.error("Payment failed", {"order_id": "ORD-9", "reason": "declined"})
```

## Configuration

| Parameter         | Type    | Default                              | Description                                        |
| ----------------- | ------- | ------------------------------------ | -------------------------------------------------- |
| `api_key`         | `str`   | **required**                         | Your project API key from the TinyOwl dashboard.   |
| `project_secret`  | `str`   | **required**                         | Your project secret for HMAC signing.              |
| `base_url`        | `str`   | `https://be.tiny-owl-kit.io/api`     | TinyOwl API base URL.                              |
| `timeout`         | `float` | `5.0`                                | HTTP request timeout in seconds.                   |
| `auto_trace_id`   | `bool`  | `True`                               | Attach a stable UUID v4 trace ID to every event.  |
| `default_context` | `dict`  | `{}`                                 | Key/value pairs merged into every log call.        |
| `service`         | `str`   | `None`                               | Service name sent top-level and included in the HMAC signature when set. |
| `environment`     | `str`   | `None`                               | Deployment environment (e.g. `"production"`), sent and signed when set. |

## Logging events

```python
# Severity shortcuts
client.info("User signed in", {"user_id": "u-123"})
client.warning("Rate limit approaching", {"pct": 90})
client.error("Database unreachable", {"host": "db.prod"})

# Generic method
client.log("Order created", severity="info", context={"order_id": "ORD-1"})
```

## Scoped loggers with `with_context()`

```python
# Create a child scope — gets its own fresh trace ID automatically
req_logger = client.with_context({"request_id": "req-xyz", "user_id": "u-123"})
req_logger.info("Request received")
req_logger.error("Validation failed", {"field": "email"})
# Both events share the same trace ID → easy correlation in the dashboard
```

The parent client is **never modified**.

## Default context

```python
client = TinyOwl(
    api_key=...,
    project_secret=...,
    default_context={"service": "billing", "env": "prod"},
)
client.info("Invoice generated")
# Sent with context: {"service": "billing", "env": "prod"}
```

Call-site context keys override `default_context` on conflict.

## Auto trace ID

By default each `TinyOwl` instance generates a UUID v4 on construction and attaches it as
`traceId` to every event — making all events from the same client instance easy to correlate.

Child instances created with `with_context()` receive their own fresh trace ID.

Opt out:

```python
client = TinyOwl(..., auto_trace_id=False)
```

## Error handling

```python
from tinyowl import TinyOwl, TinyOwlAuthError, TinyOwlTimeoutError, TinyOwlNetworkError

try:
    client.info("Hello")
except TinyOwlAuthError as e:
    print(f"Auth failed ({e.status_code}): {e}")
except TinyOwlTimeoutError:
    print("Request timed out")
except TinyOwlNetworkError as e:
    print(f"Network error: {e}")
```

## Introspection

```python
config = client.get_config()
# {
#   "base_url": "https://be.tiny-owl-kit.io/api",
#   "timeout": 5.0,
#   "auto_trace_id": True,
#   "has_api_key": True,
#   "has_project_secret": True,
#   "instance_trace_id": "550e8400-...",
# }
# Note: API key and project secret are never included.
```

## Security

Every request is signed with **HMAC-SHA256**:

- A cryptographically-random 32-hex-char nonce is generated per request (`secrets.token_hex`).
- The current UTC timestamp (ISO-8601, milliseconds) is included to prevent replay attacks.
- The backend rejects requests outside a ±60-second window and rejects reused nonces.
- `project_secret` is never logged or included in `get_config()`.
- Plain-HTTP `base_url` over a non-localhost host emits a warning (OWASP A02).

## Requirements

- Python 3.9+
- `requests` (only runtime dependency)

## License

MIT — see [LICENSE](LICENSE).

## Links

- [TinyOwl dashboard](https://tiny-owl-kit.io)
- [Changelog](CHANGELOG.md)
- [Issues](https://github.com/tiny-owl-kit/tiny-owl-python/issues)
