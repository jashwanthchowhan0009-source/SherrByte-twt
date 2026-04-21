"""Phase A smoke tests.

These run in CI without a real database. They verify:
- The app factory builds without errors
- /healthz returns 200 (doesn't hit DB)
- / returns app metadata
- Error envelope shape is correct for 404s

In Phase B we'll add a test fixture that spins up a disposable Postgres
(or uses SQLite in-memory for unit tests) so /readyz and auth flows can
be tested end-to-end.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root_returns_metadata(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "sherrbyte-api"
    assert "version" in body
    assert "env" in body


def test_healthz_returns_ok(client: TestClient) -> None:
    resp = client.get("/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_404_uses_error_envelope(client: TestClient) -> None:
    resp = client.get("/v1/nonexistent-route")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_request_id_header_is_set(client: TestClient) -> None:
    resp = client.get("/v1/healthz")
    assert "x-request-id" in {k.lower() for k in resp.headers}


def test_request_id_is_echoed_when_provided(client: TestClient) -> None:
    rid = "test-correlation-id-123"
    resp = client.get("/v1/healthz", headers={"X-Request-ID": rid})
    assert resp.headers.get("X-Request-ID") == rid
