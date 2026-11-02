from __future__ import annotations

import pytest

pytest.importorskip("django")

from django.conf import settings  # noqa: E402

if not settings.configured:
    settings.configure()

from django.http import HttpResponse  # noqa: E402
from django.test import RequestFactory, override_settings  # noqa: E402
from django.urls import ResolverMatch  # noqa: E402
from fakes import FakeClient  # noqa: E402

from tinyowl.integrations._common import flush_events  # noqa: E402
from tinyowl.integrations.django_middleware import TinyOwlDjangoMiddleware  # noqa: E402


def test_route_template_is_reported_without_query(fake_client: FakeClient) -> None:
    with override_settings(TINYOWL_CLIENT=fake_client):
        middleware = TinyOwlDjangoMiddleware(lambda _request: HttpResponse(status=404))

    request = RequestFactory().get("/users/0/?token=abc")
    request.resolver_match = ResolverMatch(
        lambda _request: None, (), {"pk": 0}, route="users/<int:pk>/"
    )
    response = middleware(request)
    flush_events()

    assert response.status_code == 404
    (call,) = fake_client.calls
    assert call["severity"] == "warning"
    assert call["context"]["routeTemplate"] == "/users/<int:pk>/"
    assert call["context"]["endpoint"] == "/users/<int:pk>/"
    assert "abc" not in str(call)


def test_success_is_not_reported(fake_client: FakeClient) -> None:
    with override_settings(TINYOWL_CLIENT=fake_client):
        middleware = TinyOwlDjangoMiddleware(lambda _request: HttpResponse(status=200))

    middleware(RequestFactory().get("/health"))
    flush_events()

    assert fake_client.calls == []
