"""
Integration tests for analysis endpoints.

Tests GET /documents/{id}/analysis with various document states.
"""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest_integration import (
    async_client,
    async_db,
    async_engine,
    test_user,
)

pytestmark = pytest.mark.asyncio


async def _upload_document(client: AsyncClient, filename: str = "test.pdf") -> dict:
    """Upload a fake document and return the response data."""
    fake_file = io.BytesIO(b"%PDF-1.4 fake pdf content for testing")
    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, fake_file, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


class TestAnalysisEndpoint:
    """Tests for GET /documents/{id}/analysis."""

    async def test_analysis_pending_returns_202(self, async_client: AsyncClient, async_db):
        """Document in 'pending' status should return 202."""
        data = await _upload_document(async_client)
        doc_id = data["id"]

        response = await async_client.get(f"/api/v1/documents/{doc_id}/analysis")
        # Newly uploaded document is 'pending' — should return 202
        assert response.status_code == 202

    async def test_analysis_done_returns_200(self, async_client: AsyncClient, async_db):
        """Document in 'done' status with analysis data should return 200."""
        from app.models.document import Document
        from sqlalchemy import update

        data = await _upload_document(async_client)
        doc_id = data["id"]

        # Manually update document to 'done' status with analysis data
        stmt = (
            update(Document)
            .where(Document.id == uuid.UUID(doc_id))
            .values(
                status="done",
                summary="Ringkasan kontrak sewa.",
                risk_score=35,
                risk_clauses_json='[{"clause_text":"Pasal 5","plain_language":"Denda keterlambatan","risk_level":"Sedang","confidence":0.85}]',
            )
        )
        await async_db.execute(stmt)
        await async_db.commit()

        response = await async_client.get(f"/api/v1/documents/{doc_id}/analysis")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["summary"] == "Ringkasan kontrak sewa."
        assert body["data"]["risk_score"] == 35
        assert len(body["data"]["risk_clauses"]) == 1

    async def test_analysis_not_found(self, async_client: AsyncClient):
        """Non-existent document should return 404."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/documents/{fake_id}/analysis")
        assert response.status_code == 404
