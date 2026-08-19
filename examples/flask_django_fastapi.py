"""Web framework integration examples for Flask, Django, and FastAPI."""

import os

from tinyowl import TinyOwl

# Shared client — construct once at startup
_client = TinyOwl(
    api_key=os.environ["TINYOWL_API_KEY"],
    project_secret=os.environ["TINYOWL_PROJECT_SECRET"],
    default_context={"service": "web"},
)


# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------

def create_flask_app():  # type: ignore[return]
    try:
        from flask import Flask, g, request

        app = Flask(__name__)

        @app.before_request
        def _attach_logger():
            g.logger = _client.with_context({
                "request_id": request.headers.get("X-Request-Id", ""),
                "method": request.method,
                "path": request.path,
            })

        @app.route("/")
        def index():
            g.logger.info("Index hit")
            return "OK"

        @app.errorhandler(Exception)
        def _handle_error(exc):
            g.logger.error("Unhandled exception", {"error": str(exc)})
            raise exc

        return app
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

def create_fastapi_app():  # type: ignore[return]
    try:
        from fastapi import FastAPI, Request

        app = FastAPI()

        @app.middleware("http")
        async def observability_middleware(request: Request, call_next):
            req_logger = _client.with_context({
                "request_id": request.headers.get("x-request-id", ""),
                "method": request.method,
                "path": request.url.path,
            })
            req_logger.info("Request started")
            response = await call_next(request)
            req_logger.info("Request finished", {"status": response.status_code})
            return response

        return app
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Django middleware
# ---------------------------------------------------------------------------

class TinyOwlDjangoMiddleware:
    """Add to MIDDLEWARE in settings.py."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        req_logger = _client.with_context({
            "request_id": request.headers.get("X-Request-Id", ""),
            "method": request.method,
            "path": request.path,
        })
        request.tinyowl = req_logger
        req_logger.info("Request started")
        response = self.get_response(request)
        req_logger.info("Request finished", {"status": response.status_code})
        return response
