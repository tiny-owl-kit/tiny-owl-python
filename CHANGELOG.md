# Changelog

All notable changes to `tinyowl-observability` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-10-28

### Added

- Optional `service` and `environment` constructor arguments (JS SDK parity). They are sent top-level with each event and included in the HMAC signature only when set. `with_context()` keeps them.

## [0.1.1] — 2026-08-22

### Changed

- Minimum supported Python bumped to **3.10** (Python 3.9 reached EOL 2025-10-05).
- CI matrix updated to Python 3.10–3.13.
- Runtime dependency `requests` bumped to `>=2.33.0` (patched against PYSEC-2026-2275).
- Security audit (`pip-audit`) now scopes to SDK runtime deps only (`--path .`), excluding dev tools.

## [0.1.0] — 2026-08-19

### Added

- `TinyOwl` client with `info()`, `warning()`, `error()`, and `log()` methods.
- HMAC-SHA256 mandatory signing per the TinyOwl wire contract — full parity with the JavaScript SDK.
- `with_context()` for creating immutable child scopes with fresh trace IDs.
- `auto_trace_id` (default `True`) — UUID v4 stable per instance, top-level `traceId` field.
- `default_context` merged into every event; call-site context wins on key conflicts.
- `get_config()` introspection — never exposes secrets or API keys.
- `TinyOwlError` hierarchy: `TinyOwlAuthError`, `TinyOwlTimeoutError`, `TinyOwlNetworkError`,
  `TinyOwlValidationError`, `TinyOwlServerError`.
- Node-compatible canonical JSON: compact, insertion-order, literal UTF-8, no ASCII escaping.
- Warning on non-HTTPS `base_url` over non-localhost (OWASP A02/A05).
- CI: pytest on Python 3.9–3.12, mypy strict, ruff, pip-audit.
- Full test suite: 60 tests covering HMAC parity, canonical JSON edge cases, API, transport errors.

[Unreleased]: https://github.com/tiny-owl-kit/tiny-owl-python/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/tiny-owl-kit/tiny-owl-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/tiny-owl-kit/tiny-owl-python/releases/tag/v0.1.0
