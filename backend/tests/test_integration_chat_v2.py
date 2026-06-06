"""
Integration tests for chat endpoints.

Tests POST /chat/{id}/message and GET /chat/{id}/history.
"""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from tests.conftest_integration import (
    TEST_USER_ID,
    async_client,
    async_db,
    async_engine,
    test_user,
)

pytestmark = pytest.mark.asyncio


async def _create_ready_document(client: AsyncClient, db) -> str:
    """Upload a document and mark it as 'done' so chat is usable."""
    from app.models.document import Document

    fake_file = io.BytesIO(b"%PDF-1.4 fake pdf content for testing")
    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("chat-test.pdf", fake_file, "application/pdf")},
    )
    assert response.status_code == 201
    doc_id = response.json()["data"]["id"]

    stmt = (
        update(Document)
        .where(Document.id == uuid.UUID(doc_id))
        .values(status="done", summary="Test summary")
    )
    await db.execute(stmt)
    await db.commit()
    return doc_id


class TestChatMessage:
    """Tests for POST /chat/{document_id}/message."""

    async def test_send_message_success(self, async_client: AsyncClient, async_db):
        doc_id = await _create_ready_document(async_client, async_db)

        response = await async_client.post(
            f"/api/v1/chat/{doc_id}/message",
            json={
                "message": "Apa isi pasal 5?",
                "history": [],
                "top_k": 3,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "answer" in body["data"]
        assert "suggestions" in body["data"]

    async def test_send_message_document_not_found(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/chat/{fake_id}/message",
            json={"message": "test", "history": [], "top_k": 3},
        )
        assert response.status_code == 404


class TestChatHistory:
    """Tests for GET /chat/{document_id}/history."""

    async def test_get_history_empty(self, async_client: AsyncClient, async_db):
        doc_id = await _create_ready_document(async_client, async_db)

        response = await async_client.get(f"/api/v1/chat/{doc_id}/history")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"] == []

    async def test_get_history_after_message(self, async_client: AsyncClient, async_db):
        doc_id = await _create_ready_document(async_client, async_db)

        # Send a message first
        await async_client.post(
            f"/api/v1/chat/{doc_id}/message",
            json={"message": "Apa risiko utama?", "history": [], "top_k": 3},
        )

        # Now fetch history
        response = await async_client.get(f"/api/v1/chat/{doc_id}/history")
        assert response.status_code == 200
        body = response.json()
        items = body["data"]["items"]
        assert len(items) >= 1
        assert items[0]["question"] == "Apa risiko utama?"

    async def test_history_pagination(self, async_client: AsyncClient, async_db):
        doc_id = await _create_ready_document(async_client, async_db)

        # Send 3 messages
        for i in range(3):
            await async_client.post(
                f"/api/v1/chat/{doc_id}/message",
                json={"message": f"Pertanyaan {i}", "history": [], "top_k": 3},
            )

        # Get with limit=2
        response = await async_client.get(
            f"/api/v1/chat/{doc_id}/history",
            params={"limit": 2, "offset": 0},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]["items"]) == 2

    async def test_history_document_not_found(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/chat/{fake_id}/history")
        assert response.status_code == 404
