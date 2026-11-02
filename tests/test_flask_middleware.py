from __future__ import annotations

import pytest

pytest.importorskip("flask")

from fakes import FakeClient  # noqa: E402
from flask import Flask, abort  # noqa: E402

from tinyowl.integrations._common import flush_events  # noqa: E402
from tinyowl.integrations.flask_middleware import TinyOwlFlask  # noqa: E402


def make_app(client: FakeClient) -> Flask:
    app = Flask(__name__)

    @app.get("/users/<int:user_id>")
    def user(user_id: int) -> str:
        if user_id == 0:
            abort(404)
        return "ok"

    @app.get("/boom")
    def boom() -> str:
        raise RuntimeError("secret detail")

    TinyOwlFlask(app, client)  # type: ignore[arg-type]
    return app


def test_matched_route_reports_template_and_status(fake_client: FakeClient) -> None:
    response = make_app(fake_client).test_client().get("/users/0?token=abc")
    flush_events()

    assert response.status_code == 404
    (call,) = fake_client.calls
    assert call["severity"] == "warning"
    assert call["context"]["endpoint"] == "/users/<int:user_id>"
    assert call["context"]["routeTemplate"] == "/users/<int:user_id>"
    assert "abc" not in str(call)


def test_unmatched_path_reports_path_without_query(fake_client: FakeClient) -> None:
    make_app(fake_client).test_client().get("/nope?secret=1")
    flush_events()

    (call,) = fake_client.calls
    assert call["context"]["endpoint"] == "/nope"
    assert "routeTemplate" not in call["context"]


def test_unhandled_exception_reports_error(fake_client: FakeClient) -> None:
    app = make_app(fake_client)
    app.testing = False
    response = app.test_client().get("/boom")
    flush_events()

    assert response.status_code == 500
    (call,) = fake_client.calls
    assert call["severity"] == "error"
    assert call["message"] == "Unhandled exception: RuntimeError"
    assert call["context"]["statusCode"] == 500
    assert "secret detail" not in str(call)


def test_init_app_registers_hooks_for_factory_pattern(fake_client: FakeClient) -> None:
    middleware = TinyOwlFlask(None, fake_client)  # type: ignore[arg-type]
    app = Flask(__name__)

    @app.get("/boom")
    def boom() -> str:
        raise ValueError("secret detail")

    middleware.init_app(app)
    app.testing = False
    app.test_client().get("/boom")
    flush_events()

    (call,) = fake_client.calls
    assert call["message"] == "Unhandled exception: ValueError"
