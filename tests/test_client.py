"""Tests for TinyOwl client: API, context precedence, traceId, getConfig."""

import pytest
import responses

from tinyowl import TinyOwl
from tinyowl.errors import TinyOwlValidationError

INGEST_URL = "https://be.tiny-owl-kit.io/api/ingest"
API_KEY = "test-api-key"
SECRET = "test-project-secret"  # noqa: S105


def make_client(**kwargs: object) -> TinyOwl:
    return TinyOwl(api_key=API_KEY, project_secret=SECRET, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(TinyOwlValidationError, match="api_key"):
            TinyOwl(api_key="", project_secret=SECRET)

    def test_missing_secret_raises(self) -> None:
        with pytest.raises(TinyOwlValidationError, match="project_secret"):
            TinyOwl(api_key=API_KEY, project_secret="")

    def test_auto_trace_id_default_on(self) -> None:
        client = make_client()
        cfg = client.get_config()
        assert cfg["auto_trace_id"] is True
        assert "instance_trace_id" in cfg
        assert len(cfg["instance_trace_id"]) == 36  # UUID v4

    def test_auto_trace_id_false(self) -> None:
        client = make_client(auto_trace_id=False)
        cfg = client.get_config()
        assert "instance_trace_id" not in cfg

    def test_get_config_never_leaks_secrets(self) -> None:
        client = make_client()
        cfg = client.get_config()
        assert "api_key" not in cfg
        assert "project_secret" not in cfg
        assert cfg["has_api_key"] is True
        assert cfg["has_project_secret"] is True

    def test_base_url_default(self) -> None:
        client = make_client()
        assert client.get_config()["base_url"] == "https://be.tiny-owl-kit.io/api"

    def test_custom_base_url_trailing_slash_stripped(self) -> None:
        client = make_client(base_url="http://localhost:5001/api/")
        assert client.get_config()["base_url"] == "http://localhost:5001/api"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_empty_message_raises(self) -> None:
        client = make_client()
        with pytest.raises(TinyOwlValidationError, match="message"):
            client.log("")

    def test_invalid_severity_raises(self) -> None:
        client = make_client()
        with pytest.raises(TinyOwlValidationError, match="severity"):
            client.log("msg", severity="debug")  # type: ignore[arg-type]

    def test_valid_severities_accepted(self) -> None:
        # These must not raise before the HTTP call is made
        client = make_client()
        for sev in ("info", "warning", "error"):
            with responses.RequestsMock() as rsps:
                rsps.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
                client.log("msg", severity=sev)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Context precedence
# ---------------------------------------------------------------------------

class TestContextPrecedence:
    @responses.activate
    def test_default_context_merged(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client(default_context={"service": "billing", "env": "prod"})
        client.info("msg", {"env": "staging"})  # call-site wins on conflict
        body = responses.calls[0].request.body
        import json
        payload = json.loads(body)
        assert payload["context"]["service"] == "billing"
        assert payload["context"]["env"] == "staging"  # call-site overrides

    @responses.activate
    def test_call_context_wins_over_default(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client(default_context={"key": "default"})
        client.info("msg", {"key": "override"})
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["context"]["key"] == "override"

    @responses.activate
    def test_empty_context_sent_as_empty_dict(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client()
        client.info("msg")
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["context"] == {}


# ---------------------------------------------------------------------------
# TraceId handling
# ---------------------------------------------------------------------------

class TestTraceId:
    @responses.activate
    def test_instance_trace_id_sent_top_level(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client(auto_trace_id=True)
        expected_tid = client.get_config()["instance_trace_id"]
        client.info("msg")
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["traceId"] == expected_tid
        assert "traceId" not in payload["context"]

    @responses.activate
    def test_no_trace_id_when_auto_off(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client(auto_trace_id=False)
        client.info("msg")
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert "traceId" not in payload

    @responses.activate
    def test_invalid_trace_id_in_context_ignored(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client(auto_trace_id=False)
        client.info("msg", {"traceId": "bad trace!!"})
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert "traceId" not in payload
        assert "traceId" not in payload["context"]

    @responses.activate
    def test_valid_trace_id_in_context_promoted(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        client = make_client(auto_trace_id=False)
        client.info("msg", {"traceId": "req-abc-1"})
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["traceId"] == "req-abc-1"
        assert "traceId" not in payload["context"]


# ---------------------------------------------------------------------------
# withContext / with_context
# ---------------------------------------------------------------------------

class TestWithContext:
    def test_returns_new_instance(self) -> None:
        client = make_client()
        child = client.with_context({"x": 1})
        assert child is not client

    def test_parent_unchanged(self) -> None:
        client = make_client(default_context={"k": "v"})
        client.with_context({"extra": "yes"})
        assert client.get_config()["base_url"] == "https://be.tiny-owl-kit.io/api"
        # parent's defaultContext not contaminated — verified via sending
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
            client.info("msg")
            import json
            payload = json.loads(rsps.calls[0].request.body)
            assert "extra" not in payload["context"]

    def test_child_gets_fresh_trace_id(self) -> None:
        client = make_client(auto_trace_id=True)
        child = client.with_context({"x": 1})
        parent_tid = client.get_config()["instance_trace_id"]
        child_tid = child.get_config()["instance_trace_id"]
        assert parent_tid != child_tid

    def test_child_merges_context(self) -> None:
        client = make_client(default_context={"service": "billing"})
        child = client.with_context({"request_id": "r-1"})
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
            child.info("msg")
            import json
            payload = json.loads(rsps.calls[0].request.body)
            assert payload["context"]["service"] == "billing"
            assert payload["context"]["request_id"] == "r-1"

    def test_explicit_trace_id_in_with_context(self) -> None:
        client = make_client()
        child = client.with_context({"traceId": "custom-trace-1"})
        assert child.get_config()["instance_trace_id"] == "custom-trace-1"

    def test_invalid_trace_id_in_with_context_generates_fresh(self) -> None:
        client = make_client(auto_trace_id=True)
        child = client.with_context({"traceId": "bad trace!!"})
        tid = child.get_config()["instance_trace_id"]
        assert len(tid) == 36  # fresh UUID v4

    def test_auto_trace_id_false_no_instance_trace(self) -> None:
        client = make_client(auto_trace_id=False)
        child = client.with_context({"x": 1})
        assert "instance_trace_id" not in child.get_config()


# ---------------------------------------------------------------------------
# Wire payload structure
# ---------------------------------------------------------------------------

class TestWirePayload:
    @responses.activate
    def test_api_key_in_body(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client().info("msg")
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["apiKey"] == API_KEY

    @responses.activate
    def test_severity_defaults_to_info(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client().log("msg")
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert payload["severity"] == "info"

    @responses.activate
    def test_security_headers_present(self) -> None:
        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client().info("msg")
        req_headers = responses.calls[0].request.headers
        assert "x-signature" in req_headers
        assert "x-timestamp" in req_headers
        assert "x-nonce" in req_headers
        assert len(req_headers["x-nonce"]) == 32
        assert len(req_headers["x-signature"]) == 64


class TestServiceEnvironment:
    @responses.activate
    def test_service_and_environment_sent_top_level(self) -> None:
        import json

        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client(service="checkout-api", environment="production").info("msg")
        payload = json.loads(responses.calls[0].request.body)
        assert payload["service"] == "checkout-api"
        assert payload["environment"] == "production"
        assert "service" not in payload["context"]

    @responses.activate
    def test_omitted_when_not_configured(self) -> None:
        import json

        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client().info("msg")
        payload = json.loads(responses.calls[0].request.body)
        assert "service" not in payload
        assert "environment" not in payload

    @responses.activate
    def test_propagated_through_with_context(self) -> None:
        import json

        responses.add(responses.POST, INGEST_URL, json={"success": True}, status=201)
        make_client(service="api", environment="staging").with_context({"job": "x"}).info("msg")
        payload = json.loads(responses.calls[0].request.body)
        assert payload["service"] == "api"
        assert payload["environment"] == "staging"
