# TinyOwl Python SDK — AI Agent Instructions

This file provides guidance for AI coding assistants (GitHub Copilot, etc.)
working inside the `tiny-owl-python` repository.

---

## Project purpose

`tinyowl-observability` is the official Python SDK for the [TinyOwl](https://tiny-owl-kit.io)
observability platform. It mirrors the public API and wire contract of the reference
JavaScript SDK (`@tiny-owl-kit/observability` / `tiny-owl-js`).

---

## Key design constraints — never violate these

1. **Wire parity with the JS SDK is non-negotiable.**
   - The signed payload key order is fixed: `message → severity → context → [traceId] → timestamp → nonce`.
   - `canonical_json()` uses `ensure_ascii=False, separators=(",", ":")` — no whitespace, no ASCII escaping.
   - The HMAC parity test vector in `tests/test_security.py` (`PARITY_SIGNATURE`) MUST always pass.

2. **`traceId` is a top-level wire field — never nested inside `context`.**

3. **Secrets are never logged, never returned by `get_config()`.**
   `get_config()` returns `has_api_key` and `has_project_secret` booleans only.

4. **HMAC signing is mandatory.** There is no "disable signing" path.

5. **`with_context()` returns a new immutable instance.** Parent is never modified.

6. **Python 3.9+ compatibility.** Use `from __future__ import annotations` for
   union types; avoid `X | Y` syntax without it on 3.9.

---

## Project layout

```
src/tinyowl/
  __init__.py   — public exports (TinyOwl class + error types)
  client.py     — TinyOwl class: log/info/warning/error/with_context/get_config
  security.py   — HMAC signing, nonce, canonical JSON, timestamp
  transport.py  — HTTP send via requests, error mapping
  trace.py      — UUID v4 generation, TRACE_ID_RE validation
  errors.py     — TinyOwlError hierarchy
tests/
  test_security.py  — HMAC parity vector + canonical JSON edge cases
  test_client.py    — API, context precedence, traceId, with_context
  test_transport.py — timeout, non-2xx errors, connection failures
examples/
  basic.py
  flask_django_fastapi.py
```

---

## Canonical HMAC parity test vector

**Fixed inputs** (must never change):

| Field      | Value                                      |
| ---------- | ------------------------------------------ |
| message    | `Payment processed`                        |
| severity   | `info`                                     |
| context    | `{"order_id": "ORD-9", "amount": 49.99}`   |
| traceId    | `req-abc-123`                              |
| timestamp  | `2026-08-19T10:20:30.000Z`                 |
| nonce      | `a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4`       |
| secret     | `super-secret-project-key-for-testing`     |

**Expected signature**: `cee771d25dcfb623fcefe37860dbac955fa10bf717e1de789cbbf2865a59b3e8`

Verified against Node.js `crypto.createHmac`.

---

## Coding conventions

- **English only** — all code, comments, docs, commits.
- **No secrets in code** — read from environment variables only.
- **Minimal dependencies** — stdlib `hmac`/`hashlib`/`secrets`/`json` for crypto;
  `requests` for HTTP; nothing else at runtime.
- **mypy strict mode** — all public functions must be fully typed.
- **ruff** for linting.
- Run `pytest` and mypy before every commit.

---

## Running tests

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ -v
.venv/bin/mypy src/tinyowl
.venv/bin/ruff check src/ tests/
```

---

## End-to-end smoke test

Requires a running local backend and a real project:

```bash
export TINYOWL_API_KEY="<your project api key>"
export TINYOWL_PROJECT_SECRET="<your project secret>"
python examples/basic.py
# Look for hmacVerified: true in the response
```

---

## Release process

```bash
git tag v0.1.0
git push origin v0.1.0   # triggers CI publish.yml → uploads to PyPI
```
