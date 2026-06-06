"""
Shared async fixtures for integration tests.

Uses in-memory SQLite via aiosqlite so tests can run without PostgreSQL.
Overrides FastAPI dependencies (get_db, get_current_user, get_nlp_client)
to use the test database and mock services.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_current_user, get_db
from app.main import app
from app.models.base import Base
from app.schemas.auth import AuthUser
from app.services.nlp_client import get_nlp_client

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_EMAIL = "test@legaleasier.local"

SECOND_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
SECOND_USER_EMAIL = "other@legaleasier.local"


# ---------------------------------------------------------------------------
# Fake NLP client
# ---------------------------------------------------------------------------

class _FakeNLPResult:
    """Minimal object mimicking NLPServiceClient.chat_document() return."""
    answer: str = "Ini adalah jawaban tes dari NLP."
    suggestions: list[str] = ["Apa saja risiko?", "Jelaskan pasal ini"]
    context_chunks_used: int = 3
    context_chunks: list[str] = ["chunk-1", "chunk-2", "chunk-3"]
    disclaimer: str = "Hasil ini bersifat informatif."


class FakeNLPClient:
    """Fake NLP client that always returns a successful response."""

    async def chat_document(self, **kwargs):
        return _FakeNLPResult()

    async def analyze_document(self, **kwargs):
        return {
            "summary": "Ringkasan tes.",
            "risk_score": 42,
            "risk_clauses": [],
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test session."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
def test_user() -> AuthUser:
    """Primary test user."""
    return AuthUser(
        id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        display_name="Test User",
        is_active=True,
        is_guest=False,
    )


@pytest_asyncio.fixture
def second_user() -> AuthUser:
    """Secondary test user for ownership tests."""
    return AuthUser(
        id=SECOND_USER_ID,
        email=SECOND_USER_EMAIL,
        display_name="Other User",
        is_active=True,
        is_guest=False,
    )


@pytest_asyncio.fixture
async def async_client(
    async_db: AsyncSession,
    test_user: AuthUser,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient with dependency overrides."""

    async def _override_get_db():
        yield async_db

    def _override_get_current_user():
        return test_user

    def _override_get_nlp_client():
        return FakeNLPClient()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_nlp_client] = _override_get_nlp_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
