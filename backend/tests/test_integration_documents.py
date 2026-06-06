"""
Integration tests for document endpoints.

Tests the full upload → list → get → search → count → delete lifecycle.
"""

from __future__ import annotations

import io
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest_integration import (
    TEST_USER_ID,
    SECOND_USER_ID,
    async_client,
    async_db,
    async_engine,
    test_user,
    second_user,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _upload_document(client: AsyncClient, filename: str = "test.pdf") -> dict:
    """Upload a fake document and return the response data."""
    fake_file = io.BytesIO(b"%PDF-1.4 fake pdf content for testing")
    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, fake_file, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDocumentLifecycle:
    """Full CRUD lifecycle for documents."""

    async def test_upload_document(self, async_client: AsyncClient):
        data = await _upload_document(async_client)
        assert "id" in data
        assert data["filename"] == "test.pdf"

    async def test_list_documents(self, async_client: AsyncClient):
        await _upload_document(async_client, "doc1.pdf")
        await _upload_document(async_client, "doc2.pdf")

        response = await async_client.get("/api/v1/documents")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        payload = body["data"]
        # New paginated response format
        assert "items" in payload
        assert "total_count" in payload
        assert payload["total_count"] >= 2

    async def test_get_document_by_id(self, async_client: AsyncClient):
        data = await _upload_document(async_client)
        doc_id = data["id"]

        response = await async_client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["id"] == doc_id

    async def test_get_document_count(self, async_client: AsyncClient):
        await _upload_document(async_client)
        response = await async_client.get("/api/v1/documents/count")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["count"] >= 1

    async def test_search_documents(self, async_client: AsyncClient):
        await _upload_document(async_client, "kontrak-sewa.pdf")

        response = await async_client.get(
            "/api/v1/documents/search",
            params={"q": "kontrak"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["data"]) >= 1

    async def test_search_empty_query(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/documents/search",
            params={"q": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []

    async def test_delete_document(self, async_client: AsyncClient):
        data = await _upload_document(async_client)
        doc_id = data["id"]

        response = await async_client.delete(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200

        # Verify deleted
        response = await async_client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 404

    async def test_document_not_found(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/documents/{fake_id}")
        assert response.status_code == 404

    async def test_pagination(self, async_client: AsyncClient):
        # Upload 3 documents
        for i in range(3):
            await _upload_document(async_client, f"page-test-{i}.pdf")

        # Get page 1 with limit 2
        response = await async_client.get(
            "/api/v1/documents",
            params={"page": 1, "limit": 2},
        )
        assert response.status_code == 200
        body = response.json()
        payload = body["data"]
        assert len(payload["items"]) == 2
        assert payload["has_more"] is True
