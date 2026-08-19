"""Basic usage example."""

import os

from tinyowl import TinyOwl

client = TinyOwl(
    api_key=os.environ["TINYOWL_API_KEY"],
    project_secret=os.environ["TINYOWL_PROJECT_SECRET"],
    # base_url defaults to https://be.tiny-owl-kit.io/api
    default_context={"service": "my-app", "env": "production"},
)

# Basic severity methods
client.info("Application started", {"version": "1.0.0"})
client.warning("Memory usage high", {"used_pct": 85})
client.error("Unhandled exception", {"code": "ERR_UNKNOWN"})

# Generic log method
client.log("Custom event", severity="info", context={"custom": True})

# Scoped logger — fresh trace ID, inherits default_context
req_logger = client.with_context({"request_id": "req-xyz-123", "user_id": "u-456"})
req_logger.info("Request received")
req_logger.info("Processing started")
req_logger.error("Downstream timeout", {"service": "payments"})

# Introspect config (no secrets exposed)
print(client.get_config())
