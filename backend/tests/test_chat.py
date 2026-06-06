"""
Unit tests for chat endpoint (Sprint 4 skeleton).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.main import app
from app.schemas.auth import AuthUser
from app.services.nlp_client import get_nlp_client


class _FakeResult:
    def __init__(self, document):
        self._document = document

    def scalar_one_or_none(self):
        return self._document


class _FakeQuotaResult:
    def __init__(self, quota):
        self._quota = quota

    def scalar_one_or_none(self):
        return self._quota


class _FakeHistoryResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, document, quota=None):
        self._document = document
        self._quota = quota or SimpleNamespace(user_id=None, remaining_quota=5)
        self._execute_count = 0
        self.added_objects = []
        self.committed = False
        self.refreshed_objects = []

    async def execute(self, _stmt):
        self._execute_count += 1
        if self._execute_count == 1:
            return _FakeResult(self._document)
        return _FakeQuotaResult(self._quota)

    def add(self, obj):
        self.added_objects.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed_objects.append(obj)


class _FakeDBWithHistory:
    def __init__(self, document, rows):
        self._document = document
        self._rows = rows
        self._calls = 0

    async def execute(self, _stmt):
        self._calls += 1
        if self._calls == 1:
            return _FakeResult(self._document)
        return _FakeHistoryResult(self._rows)


class _FakeNLPClient:
    async def chat_document(self, document_id, query, history, top_k):
        return SimpleNamespace(
            answer=f"Jawaban untuk: {query}",
            suggestions=["Apa risiko terbesar?", "Bagian mana paling penting?"],
            context_chunks_used=2,
            context_chunks=["chunk-1", "chunk-2"],
            disclaimer="Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional.",
        )


@pytest.fixture
def client_with_doc_owner_match() -> Generator[TestClient, None, None]:
    user_id = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")
    doc_id = uuid.UUID("bbbbbbbb-1111-2222-3333-444444444444")

    async def _mock_current_user():
        return AuthUser(id=user_id, email="test@example.com", display_name="Tester", is_active=True)

    async def _mock_get_db():
        yield _FakeDB(
            SimpleNamespace(
                id=doc_id,
                owner_id=user_id,
            )
        )

    def _mock_nlp_client():
        return _FakeNLPClient()

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_nlp_client] = _mock_nlp_client

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_chat_message_success(client_with_doc_owner_match: TestClient):
    response = client_with_doc_owner_match.post(
        "/api/v1/chat/bbbbbbbb-1111-2222-3333-444444444444/message",
        json={
            "message": "Apa isi pasal ini?",
            "history": [{"role": "user", "content": "Halo"}],
            "top_k": 5,
        },
        headers={"Authorization": "Bearer mock-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Chat response generated."
    assert body["data"]["answer"].startswith("Jawaban untuk")
    assert len(body["data"]["sources"]) == 2
    assert body["data"]["remaining_quota"] == 4


def test_chat_message_document_not_found():
    user_id = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")

    async def _mock_current_user():
        return AuthUser(id=user_id, email="test@example.com", display_name="Tester", is_active=True)

    async def _mock_get_db():
        yield _FakeDB(None)

    def _mock_nlp_client():
        return _FakeNLPClient()

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_nlp_client] = _mock_nlp_client

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/cccccccc-1111-2222-3333-444444444444/message",
        json={"message": "cek"},
        headers={"Authorization": "Bearer mock-token"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_chat_message_forbidden_owner_mismatch():
    user_id = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")
    doc_owner_id = uuid.UUID("dddddddd-1111-2222-3333-444444444444")

    async def _mock_current_user():
        return AuthUser(id=user_id, email="test@example.com", display_name="Tester", is_active=True)

    async def _mock_get_db():
        yield _FakeDB(
            SimpleNamespace(
                id=uuid.UUID("eeeeeeee-1111-2222-3333-444444444444"),
                owner_id=doc_owner_id,
            )
        )

    def _mock_nlp_client():
        return _FakeNLPClient()

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_nlp_client] = _mock_nlp_client

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/eeeeeeee-1111-2222-3333-444444444444/message",
        json={"message": "cek"},
        headers={"Authorization": "Bearer mock-token"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_chat_history_success():
    user_id = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")
    doc_id = uuid.UUID("bbbbbbbb-1111-2222-3333-444444444444")

    async def _mock_current_user():
        return AuthUser(id=user_id, email="test@example.com", display_name="Tester", is_active=True)

    async def _mock_get_db():
        yield _FakeDBWithHistory(
            SimpleNamespace(id=doc_id, owner_id=user_id),
            [
                SimpleNamespace(
                    id=uuid.UUID("cccccccc-1111-2222-3333-444444444444"),
                    document_id=doc_id,
                    question="Pertanyaan pertama",
                    answer="Jawaban pertama",
                    sources_json='["chunk-1", "chunk-2"]',
                    created_at=SimpleNamespace(isoformat=lambda: "2026-05-26T10:00:00+00:00"),
                )
            ],
        )

    def _mock_nlp_client():
        return _FakeNLPClient()

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_nlp_client] = _mock_nlp_client

    client = TestClient(app)
    response = client.get(
        "/api/v1/chat/bbbbbbbb-1111-2222-3333-444444444444/history",
        headers={"Authorization": "Bearer mock-token"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Chat history loaded."
    assert body["data"]["document_id"] == "bbbbbbbb-1111-2222-3333-444444444444"
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["question"] == "Pertanyaan pertama"
    assert body["data"]["items"][0]["sources"][0]["text"] == "chunk-1"


def test_chat_message_guest_quota_exhausted():
    user_id = uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444")
    doc_id = uuid.UUID("bbbbbbbb-1111-2222-3333-444444444444")

    class _TrackingNLPClient:
        def __init__(self):
            self.called = False

        async def chat_document(self, document_id, query, history, top_k):
            self.called = True
            return SimpleNamespace(
                answer="tidak dipakai",
                suggestions=[],
                context_chunks_used=0,
                context_chunks=[],
                disclaimer="Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional.",
            )

    async def _mock_current_user():
        return AuthUser(id=user_id, email="test@example.com", display_name="Tester", is_active=True)

    async def _mock_get_db():
        yield _FakeDB(
            SimpleNamespace(id=doc_id, owner_id=user_id),
            quota=SimpleNamespace(user_id=user_id, remaining_quota=0),
        )

    nlp_client = _TrackingNLPClient()

    def _mock_nlp_client():
        return nlp_client

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_nlp_client] = _mock_nlp_client

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/bbbbbbbb-1111-2222-3333-444444444444/message",
        json={"message": "cek quota"},
        headers={"Authorization": "Bearer mock-token"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.json()["detail"] == "Guest quota exhausted"
    assert nlp_client.called is False
