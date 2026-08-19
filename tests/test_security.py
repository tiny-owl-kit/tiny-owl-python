"""Tests for HMAC signing, canonical JSON, and the shared parity vector."""

import json
import unittest.mock as mock

from tinyowl.security import (
    build_signable_payload,
    canonical_json,
    create_secure_headers,
    generate_nonce,
    js_iso_timestamp,
    sign_payload,
)

# ---------------------------------------------------------------------------
# Shared HMAC parity test vector
#
# These values are fixed.  Every SDK in every language MUST reproduce the same
# expected_signature given the same inputs.  Do not change these constants.
# ---------------------------------------------------------------------------
PARITY_MESSAGE = "Payment processed"
PARITY_SEVERITY = "info"
PARITY_CONTEXT = {"order_id": "ORD-9", "amount": 49.99}
PARITY_TRACE_ID = "req-abc-123"
PARITY_TIMESTAMP = "2026-08-19T10:20:30.000Z"
PARITY_NONCE = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
PARITY_SECRET = "super-secret-project-key-for-testing"  # noqa: S105

# Verified against Node.js:
#   node -e "
#     const c=require('crypto');
#     const p={message:'Payment processed',severity:'info',
#       context:{order_id:'ORD-9',amount:49.99},traceId:'req-abc-123',
#       timestamp:'2026-08-19T10:20:30.000Z',
#       nonce:'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'};
#     console.log(JSON.stringify(p));
#     console.log(c.createHmac('sha256','super-secret-project-key-for-testing')
#       .update(JSON.stringify(p)).digest('hex'));
#   "
PARITY_CANONICAL = (
    '{"message":"Payment processed","severity":"info",'
    '"context":{"order_id":"ORD-9","amount":49.99},'
    '"traceId":"req-abc-123",'
    '"timestamp":"2026-08-19T10:20:30.000Z",'
    '"nonce":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"}'
)
PARITY_SIGNATURE = "cee771d25dcfb623fcefe37860dbac955fa10bf717e1de789cbbf2865a59b3e8"


class TestCanonicalJson:
    def test_compact_no_whitespace(self) -> None:
        assert canonical_json({"a": 1}) == '{"a":1}'

    def test_insertion_order_preserved(self) -> None:
        obj = {"z": 1, "a": 2, "m": 3}
        assert canonical_json(obj) == '{"z":1,"a":2,"m":3}'

    def test_unicode_not_escaped(self) -> None:
        result = canonical_json({"msg": "héllo wörld"})
        assert "héllo wörld" in result
        assert "\\u" not in result

    def test_slash_not_escaped(self) -> None:
        result = canonical_json({"url": "https://example.com/path"})
        assert "https://example.com/path" in result
        assert "\\/" not in result

    def test_ampersand_and_angle_brackets_not_escaped(self) -> None:
        result = canonical_json({"q": "<script>alert(1)&x=y</script>"})
        assert "<script>" in result
        assert "\\u003c" not in result
        assert "\\u0026" not in result

    def test_nested_context(self) -> None:
        obj = {"context": {"user": "alice", "meta": {"env": "prod"}}}
        result = canonical_json(obj)
        parsed = json.loads(result)
        assert parsed["context"]["meta"]["env"] == "prod"

    def test_empty_context(self) -> None:
        assert canonical_json({"context": {}}) == '{"context":{}}'

    def test_parity_canonical_string(self) -> None:
        payload = build_signable_payload(
            PARITY_MESSAGE,
            PARITY_SEVERITY,
            PARITY_CONTEXT,
            PARITY_TIMESTAMP,
            PARITY_NONCE,
            PARITY_TRACE_ID,
        )
        assert canonical_json(payload) == PARITY_CANONICAL


class TestSignPayload:
    def test_parity_vector(self) -> None:
        """The computed signature MUST match the known Node.js reference value."""
        payload = build_signable_payload(
            PARITY_MESSAGE,
            PARITY_SEVERITY,
            PARITY_CONTEXT,
            PARITY_TIMESTAMP,
            PARITY_NONCE,
            PARITY_TRACE_ID,
        )
        sig = sign_payload(payload, PARITY_SECRET)
        assert sig == PARITY_SIGNATURE, (
            f"HMAC parity failure!\n"
            f"  got:      {sig}\n"
            f"  expected: {PARITY_SIGNATURE}\n"
            f"  payload:  {canonical_json(payload)}"
        )

    def test_without_trace_id(self) -> None:
        payload = build_signable_payload("msg", "info", {}, PARITY_TIMESTAMP, PARITY_NONCE)
        sig = sign_payload(payload, PARITY_SECRET)
        assert isinstance(sig, str) and len(sig) == 64

    def test_returns_lowercase_hex(self) -> None:
        payload = build_signable_payload("msg", "info", {}, PARITY_TIMESTAMP, PARITY_NONCE)
        sig = sign_payload(payload, PARITY_SECRET)
        assert sig == sig.lower()
        assert all(c in "0123456789abcdef" for c in sig)

    def test_different_secret_gives_different_sig(self) -> None:
        payload = build_signable_payload("msg", "info", {}, PARITY_TIMESTAMP, PARITY_NONCE)
        s1 = sign_payload(payload, "secret-a")
        s2 = sign_payload(payload, "secret-b")
        assert s1 != s2


class TestBuildSignablePayload:
    def test_key_order_without_trace_id(self) -> None:
        p = build_signable_payload("msg", "info", {"k": "v"}, "ts", "nn")
        assert list(p.keys()) == ["message", "severity", "context", "timestamp", "nonce"]

    def test_key_order_with_trace_id(self) -> None:
        p = build_signable_payload("msg", "info", {}, "ts", "nn", "trace-1")
        assert list(p.keys()) == ["message", "severity", "context", "traceId", "timestamp", "nonce"]

    def test_trace_id_position_before_timestamp(self) -> None:
        p = build_signable_payload("m", "info", {}, "ts", "nn", "tr")
        keys = list(p.keys())
        assert keys.index("traceId") < keys.index("timestamp")


class TestGenerateNonce:
    def test_length_is_32(self) -> None:
        assert len(generate_nonce()) == 32

    def test_hex_chars_only(self) -> None:
        n = generate_nonce()
        assert all(c in "0123456789abcdef" for c in n)

    def test_unique(self) -> None:
        nonces = {generate_nonce() for _ in range(1000)}
        assert len(nonces) == 1000


class TestJsIsoTimestamp:
    def test_format(self) -> None:
        ts = js_iso_timestamp()
        # e.g. 2026-08-19T10:20:30.000Z
        import re
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", ts), ts

    def test_ends_with_z(self) -> None:
        assert js_iso_timestamp().endswith("Z")

    def test_milliseconds_exactly_3_digits(self) -> None:
        ts = js_iso_timestamp()
        ms_part = ts.split(".")[1]
        assert len(ms_part) == 4  # "mmmZ"
        assert ms_part.endswith("Z")


class TestCreateSecureHeaders:
    def test_returns_three_headers(self) -> None:
        h = create_secure_headers("msg", "info", {}, "secret")
        assert set(h.keys()) == {"x-signature", "x-timestamp", "x-nonce"}

    def test_nonce_is_32_chars(self) -> None:
        h = create_secure_headers("msg", "info", {}, "secret")
        assert len(h["x-nonce"]) == 32

    def test_signature_is_lowercase_hex_64(self) -> None:
        h = create_secure_headers("msg", "info", {}, "secret")
        sig = h["x-signature"]
        assert len(sig) == 64
        assert sig == sig.lower()

    def test_with_trace_id(self) -> None:
        h = create_secure_headers("msg", "info", {}, "secret", trace_id="trace-1")
        assert len(h["x-signature"]) == 64

    def test_signature_differs_with_and_without_trace_id(self) -> None:
        # pin timestamp and nonce to isolate traceId impact
        with mock.patch("tinyowl.security.js_iso_timestamp", return_value=PARITY_TIMESTAMP), \
             mock.patch("tinyowl.security.generate_nonce", return_value=PARITY_NONCE):
            h_with = create_secure_headers("msg", "info", {}, PARITY_SECRET, trace_id="tr")
            h_without = create_secure_headers("msg", "info", {}, PARITY_SECRET)
        assert h_with["x-signature"] != h_without["x-signature"]
