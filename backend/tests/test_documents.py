"""
Unit tests for document endpoints.

Updated for:
- StandardResponse wrapper (CLAUDE.md §8): { success, data, message }
- Auth enforcement: all document routes require Bearer JWT (mocked via get_current_user)

Note: Integration tests (upload with DB, background task) require a running
PostgreSQL database. Those tests are marked with @pytest.mark.integration.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import AuthUser


# ---------------------------------------------------------------------------
# Fixtures — shared mock user for ownership checks
# ---------------------------------------------------------------------------

MOCK_USER_ID = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")


@pytest.fixture(autouse=True)
def override_auth():
    """Mock get_current_user for all tests in this module."""
    async def mock_get_current_user():
        return AuthUser(
            id=MOCK_USER_ID,
            email="test@example.com",
            display_name="Test User",
            is_active=True,
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests — Health endpoint (StandardResponse, no auth needed)
# ---------------------------------------------------------------------------

def test_health_endpoint_returns_standard_response(client: TestClient):
    """Health check should return StandardResponse wrapper."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["message"] == "Service is healthy."


# ---------------------------------------------------------------------------
# Tests — Upload rejection (invalid type)
# ---------------------------------------------------------------------------

def test_upload_invalid_mime_type(client: TestClient):
    """Upload with unsupported MIME type should return 400."""
    files = {"file": ("readme.txt", b"hello", "text/plain")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests — Unauthenticated access
# ---------------------------------------------------------------------------

def test_documents_without_auth_returns_401():
    """Endpoints without auth header should return 401."""
    # Clear dependency overrides to test real auth path
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.get("/api/v1/documents")
    assert response.status_code == 401


def test_upload_without_auth_returns_401():
    """Upload without auth should return 401."""
    app.dependency_overrides.clear()
    client = TestClient(app)
    files = {"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests — StandardResponse format on list (requires DB, may be skipped)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    True,  # Set to False when running with a live database
    reason="Integration test: requires PostgreSQL database connection",
)
def test_list_documents_returns_standard_response(client: TestClient):
    """List should return StandardResponse with array data."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "document(s) found" in body["message"]
