"""Tests for HTTP transport: timeout, non-2xx errors, connection failures."""

import unittest.mock as mock

import pytest
import requests as req_lib
import responses

from tinyowl import TinyOwl
from tinyowl.errors import (
    TinyOwlAuthError,
    TinyOwlNetworkError,
    TinyOwlServerError,
    TinyOwlTimeoutError,
)

INGEST_URL = "https://be.tiny-owl-kit.io/api/ingest"


def make_client(**kwargs: object) -> TinyOwl:
    return TinyOwl(api_key="key", project_secret="secret", **kwargs)  # type: ignore[arg-type]  # noqa: S106


class TestTransportErrors:
    @responses.activate
    def test_401_raises_auth_error(self) -> None:
        responses.add(
            responses.POST, INGEST_URL,
            json={"message": "Invalid signature"}, status=401,
        )
        with pytest.raises(TinyOwlAuthError) as exc_info:
            make_client().info("msg")
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in str(exc_info.value)

    @responses.activate
    def test_403_raises_auth_error(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"message": "Forbidden"}, status=403)
        with pytest.raises(TinyOwlAuthError) as exc_info:
            make_client().info("msg")
        assert exc_info.value.status_code == 403

    @responses.activate
    def test_500_raises_server_error(self) -> None:
        responses.add(responses.POST, INGEST_URL, body="Internal Server Error", status=500)
        with pytest.raises(TinyOwlServerError) as exc_info:
            make_client().info("msg")
        assert exc_info.value.status_code == 500

    @responses.activate
    def test_201_returns_json(self) -> None:
        payload = {"success": True, "data": {"eventId": "evt-1", "hmacVerified": True}}
        responses.add(responses.POST, INGEST_URL, json=payload, status=201)
        result = make_client().info("msg")
        assert result["success"] is True
        assert result["data"]["hmacVerified"] is True

    def test_connection_error_raises_network_error(self) -> None:
        with mock.patch("requests.post", side_effect=req_lib.exceptions.ConnectionError("refused")):
            with pytest.raises(TinyOwlNetworkError):
                make_client().info("msg")

    def test_timeout_raises_timeout_error(self) -> None:
        with mock.patch("requests.post", side_effect=req_lib.exceptions.Timeout()):
            with pytest.raises(TinyOwlTimeoutError):
                make_client(timeout=0.001).info("msg")

    @responses.activate
    def test_content_type_header_set(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client().info("msg")
        assert responses.calls[0].request.headers["Content-Type"] == "application/json"
