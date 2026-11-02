from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi")

from fakes import FakeClient  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from tinyowl.integrations._common import flush_events  # noqa: E402
from tinyowl.integrations.asgi_middleware import TinyOwlASGIMiddleware  # noqa: E402


def make_app(client: FakeClient) -> FastAPI:
    app = FastAPI()

    @app.get("/users/{user_id}")
    def user(user_id: int) -> dict[str, int]:
        if user_id == 0:
            raise HTTPException(status_code=404)
        return {"id": user_id}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail")

    app.add_middleware(TinyOwlASGIMiddleware, client=client)  # type: ignore[arg-type]
    return app


def test_successful_response_is_not_reported(fake_client: FakeClient) -> None:
    response = TestClient(make_app(fake_client)).get("/users/1")
    flush_events()
    assert response.status_code == 200
    assert fake_client.calls == []


def test_client_error_reports_template_without_query_or_headers(fake_client: FakeClient) -> None:
    response = TestClient(make_app(fake_client)).get(
        "/users/0?token=abc", headers={"Authorization": "Bearer xyz"}
    )
    flush_events()

    assert response.status_code == 404
    (call,) = fake_client.calls
    assert call["severity"] == "warning"
    assert call["context"]["method"] == "GET"
    assert call["context"]["endpoint"] == "/users/{user_id}"
    assert call["context"]["routeTemplate"] == "/users/{user_id}"
    assert call["context"]["statusCode"] == 404
    assert isinstance(call["context"]["durationMs"], float)
    assert "abc" not in str(call) and "xyz" not in str(call)


def test_uncaught_exception_reports_error_and_returns_500(fake_client: FakeClient) -> None:
    response = TestClient(make_app(fake_client), raise_server_exceptions=False).get("/boom")
    flush_events()

    assert response.status_code == 500
    (call,) = fake_client.calls
    assert call["severity"] == "error"
    assert call["message"] == "Unhandled exception: RuntimeError"
    assert call["context"]["statusCode"] == 500
    assert "secret detail" not in str(call)


def test_slow_sdk_does_not_delay_the_request() -> None:
    client = TestClient(make_app(FakeClient(delay=1.0)))

    started = time.perf_counter()
    response = client.get("/users/0")
    elapsed = time.perf_counter() - started
    flush_events()

    assert response.status_code == 404
    assert elapsed < 0.5


def test_sdk_failure_does_not_break_the_response() -> None:
    response = TestClient(make_app(FakeClient(fail=True))).get("/users/0")
    flush_events()

    assert response.status_code == 404
