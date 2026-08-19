"""Trace ID generation and validation."""

import logging
import re
import uuid

logger = logging.getLogger(__name__)

TRACE_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,128}$")


def new_trace_id() -> str:
    """Generate a UUID v4 trace ID."""
    return str(uuid.uuid4())


def validate_trace_id(trace_id: str) -> bool:
    """Return True if *trace_id* matches the allowed pattern."""
    return bool(TRACE_ID_RE.match(trace_id))
