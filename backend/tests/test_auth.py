"""
Unit tests for authentication endpoints and Firebase token verification.
Tests mock Firebase token verification per CLAUDE.md Section 14 (What NOT to test: Firebase SDK calls).

Updated to validate StandardResponse wrapper (CLAUDE.md §8):
  { "success": true/false, "data": <T>, "message": "..." }
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import AuthUser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_USER_ID = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")


@pytest.fixture()
def mock_current_user():
    """Mock get_current_user to return a test user."""
    async def _mock_get_current_user():
        return AuthUser(
            id=MOCK_USER_ID,
            email="test@example.com",
            display_name="Test User",
            is_active=True,
        )

    return _mock_get_current_user


@pytest.fixture()
def client_with_auth(mock_current_user):
    """Test client with mocked get_current_user dependency."""
    app.dependency_overrides[get_current_user] = mock_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth header validation tests (no DB needed — fail before hitting deps.get_db)
# ---------------------------------------------------------------------------

def test_get_current_user_without_token():
    """Test get_current_user() without authorization header returns 401."""
    client = TestClient(app)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Authorization header missing" in response.json()["detail"]


def test_get_current_user_invalid_header_format():
    """Test get_current_user() with invalid Bearer format returns 401."""
    client = TestClient(app)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "InvalidFormat token-here"}
    )
    assert response.status_code == 401
    assert "Invalid authorization header format" in response.json()["detail"]


# ---------------------------------------------------------------------------
# /auth/me — wrapped in StandardResponse
# ---------------------------------------------------------------------------

def test_get_me_with_valid_user(client_with_auth: TestClient):
    """Test /auth/me endpoint returns StandardResponse with user data."""
    response = client_with_auth.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer mock-token"},
    )

    assert response.status_code == 200
    body = response.json()

    # StandardResponse wrapper
    assert body["success"] is True
    assert body["message"] == "User profile retrieved."

    # Actual data
    data = body["data"]
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert data["is_active"] is True


def test_get_current_user_auto_provisions_missing_user(monkeypatch):
    """Verified Firebase users without a local row should be auto-created."""

    class FakeResult:
        def __init__(self, user):
            self._user = user

        def scalar_one_or_none(self):
            return self._user

    class FakeDB:
        def __init__(self):
            self.queries: list[str] = []
            self.added_user = None
            self.committed = False
            self.refreshed_user = None

        async def execute(self, stmt):
            self.queries.append(str(stmt))
            return FakeResult(None)

        def add(self, user):
            self.added_user = user

        async def commit(self):
            self.committed = True

        async def refresh(self, user):
            self.refreshed_user = user

    async def fake_verify_firebase_token(token: str):
        assert token == "test-token"
        return {
            "uid": "firebase-uid-123",
            "email": "new-user@example.com",
            "name": "New User",
        }

    monkeypatch.setattr("app.api.deps.is_mock_mode", lambda: False)
    monkeypatch.setattr("app.api.deps.verify_firebase_token", fake_verify_firebase_token)

    db = FakeDB()
    user = asyncio.run(get_current_user(authorization="Bearer test-token", db=db))

    assert user.email == "new-user@example.com"
    assert user.display_name == "New User"
    assert user.is_active is True
    assert db.added_user is not None
    assert db.added_user.firebase_uid == "firebase-uid-123"
    assert db.committed is True
    assert db.refreshed_user is db.added_user
    assert len(db.queries) == 2
