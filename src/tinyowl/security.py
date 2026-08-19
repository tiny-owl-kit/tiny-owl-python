"""HMAC-SHA256 signing, nonce generation, and canonical JSON serialization."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def generate_nonce() -> str:
    """Return 32 cryptographically-random hex characters (16 bytes)."""
    return secrets.token_hex(16)


def js_iso_timestamp() -> str:
    """Return an ISO-8601 timestamp that matches Node's ``new Date().toISOString()``.

    Format: ``YYYY-MM-DDTHH:MM:SS.mmmZ`` (exactly 3 ms digits, Z suffix).
    """
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    return now.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}Z")


def canonical_json(obj: Any) -> str:
    """Serialize *obj* to compact JSON that round-trips through Node's JSON.stringify.

    Rules:
    - No whitespace (``separators=(",", ":")``)
    - Literal UTF-8, no ASCII escaping (``ensure_ascii=False``)
    - Insertion-order preserved (Python 3.7+ dicts are ordered)
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def build_signable_payload(
    message: str,
    severity: str,
    context: Dict[str, Any],
    timestamp: str,
    nonce: str,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the ordered dict that is HMAC-signed.

    Key order is fixed: message → severity → context → [traceId] → timestamp → nonce.
    This must exactly match the order used by the backend and JS SDK.
    """
    payload: Dict[str, Any] = {
        "message": message,
        "severity": severity,
        "context": context,
    }
    if trace_id is not None:
        payload["traceId"] = trace_id
    payload["timestamp"] = timestamp
    payload["nonce"] = nonce
    return payload


def sign_payload(payload: Dict[str, Any], project_secret: str) -> str:
    """HMAC-SHA256 over the canonical JSON of *payload*; returns lowercase hex."""
    data = canonical_json(payload).encode("utf-8")
    return hmac.new(project_secret.encode("utf-8"), data, hashlib.sha256).hexdigest()


def create_secure_headers(
    message: str,
    severity: str,
    context: Dict[str, Any],
    project_secret: str,
    trace_id: Optional[str] = None,
) -> Dict[str, str]:
    """Generate the three HMAC security headers required by the backend."""
    timestamp = js_iso_timestamp()
    nonce = generate_nonce()
    signable = build_signable_payload(message, severity, context, timestamp, nonce, trace_id)
    signature = sign_payload(signable, project_secret)
    return {
        "x-signature": signature,
        "x-timestamp": timestamp,
        "x-nonce": nonce,
    }
