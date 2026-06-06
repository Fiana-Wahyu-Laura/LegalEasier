"""
Unit tests for the analysis endpoint: GET /api/v1/documents/{id}/analysis.

Tests validate:
- StandardResponse wrapper format (CLAUDE.md §8)
- Auth + ownership enforcement
- Handling of various document statuses (pending, processing, failed, done)
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.main import app
from app.schemas.auth import AuthUser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_USER_ID = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")


@pytest.fixture()
def mock_current_user():
    """Mock get_current_user to return a test user."""
    async def _mock():
        return AuthUser(
            id=MOCK_USER_ID,
            email="test@example.com",
            display_name="Test User",
            is_active=True,
        )
    return _mock


@pytest.fixture()
def client_with_auth(mock_current_user):
    """Test client with mocked auth (no real DB/Firebase needed)."""
    app.dependency_overrides[get_current_user] = mock_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — Analysis endpoint requires auth
# ---------------------------------------------------------------------------

def test_analysis_without_auth_returns_401():
    """Analysis endpoint without auth should return 401."""
    app.dependency_overrides.clear()
    client = TestClient(app)
    fake_id = uuid.uuid4()
    response = client.get(f"/api/v1/documents/{fake_id}/analysis")
    assert response.status_code == 401
