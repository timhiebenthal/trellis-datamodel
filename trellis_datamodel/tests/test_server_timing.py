"""Tests for request-level timing and request-id response headers."""

import asyncio
import re
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from trellis_datamodel import observability
from trellis_datamodel.exceptions import NotFoundError
from trellis_datamodel.server import create_app


def _app_with_test_routes():
    app = create_app()

    def register(path, endpoint):
        app.add_api_route(path, endpoint)
        route = app.router.routes.pop()
        app.router.routes.insert(0, route)

    async def timed():
        with observability.timed_phase("schema_read"):
            await asyncio.sleep(0)
        return {"ok": True}

    register("/test/timed", timed)

    async def handled():
        raise NotFoundError("private detail")

    register("/test/handled", handled)

    async def unhandled():
        raise RuntimeError("private payload")

    register("/test/unhandled", unhandled)

    async def concurrent(phase: str):
        with observability.timed_phase(phase):
            await asyncio.sleep(0.01)
        return {"phase": phase}

    register("/test/concurrent/{phase}", concurrent)

    return app


def _header_response(response):
    request_id = response.headers.get("X-Trellis-Request-Id")
    server_timing = response.headers.get("Server-Timing")
    assert request_id is not None
    assert server_timing is not None
    uuid.UUID(request_id)
    assert re.search(r"request;dur=\d+\.\d{3};desc=\"request\"", server_timing)
    return request_id, server_timing


def test_success_response_has_request_id_and_server_timing():
    app = _app_with_test_routes()

    with TestClient(app) as client:
        response = client.get("/test/timed")

    assert response.status_code == 200
    request_id, server_timing = _header_response(response)
    assert request_id not in server_timing
    assert "schema_read;dur=" in server_timing


def test_handled_error_response_has_request_id_and_server_timing():
    app = _app_with_test_routes()

    with TestClient(app) as client:
        response = client.get("/test/handled")

    assert response.status_code == 404
    assert response.json() == {"detail": "private detail", "error": "not_found"}
    _header_response(response)


def test_unhandled_error_response_retains_request_id():
    app = _app_with_test_routes()

    with TestClient(app) as client:
        with pytest.raises(RuntimeError, match="private payload"):
            client.get("/test/unhandled")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/unhandled")

    assert response.status_code == 500
    _header_response(response)
    assert "private payload" not in response.text


def test_supplied_request_id_is_not_trusted_or_reflected():
    app = _app_with_test_routes()
    supplied_id = "attacker-id/model=customer_orders?payload=secret"

    with TestClient(app) as client:
        response = client.get(
            "/test/timed?model=customer_orders&payload=secret/path",
            headers={"X-Trellis-Request-Id": supplied_id},
        )

    request_id, server_timing = _header_response(response)
    assert request_id != supplied_id
    assert supplied_id not in response.headers.values()
    assert "customer_orders" not in server_timing
    assert "secret" not in server_timing
    assert "test/timed" not in server_timing


def test_concurrent_requests_do_not_share_phase_counts():
    app = _app_with_test_routes()

    def request(phase):
        with TestClient(app) as client:
            return client.get(f"/test/concurrent/{phase}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(request, ("schema_read", "relationship_scan")))

    for response, phase, other_phase in zip(
        responses,
        ("schema_read", "relationship_scan"),
        ("relationship_scan", "schema_read"),
    ):
        assert response.status_code == 200
        _header_response(response)
        assert response.headers["Server-Timing"].count(f"{phase};dur=") == 1
        assert f"{other_phase};dur=" not in response.headers["Server-Timing"]
