"""
Unit test for the backend ↔ NLP service contract.

Validates:
- NLP client sends correct multipart fields (document_id, file_type, file)
- NLP client correctly parses ProcessResponse from NLP service
- File type detection and MIME mapping work correctly
"""

from __future__ import annotations

import uuid

import asyncio

import pytest

import app.services.nlp_client as nlp_client_module
from app.services.nlp_client import NLPServiceClient


class DummyResponse:
    status_code = 200
    text = "ok"

    def json(self):
        return {
            "document_id": str(uuid.UUID("12345678-1234-5678-1234-567812345678")),
            "ocr_used": True,
            "full_text": "full text from nlp",
            "summary": "summary from nlp",
            "risk_score": 42,
            "risk_clauses": [
                {
                    "clause_text": "clause",
                    "plain_language": "plain",
                    "risk_level": "Sedang",
                    "confidence": 0.88,
                }
            ],
            "disclaimer": "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional.",
        }


class DummyAsyncClient:
    captured = {}

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, files=None, data=None):
        DummyAsyncClient.captured = {"url": url, "files": files, "data": data}
        return DummyResponse()


def test_nlp_client_sends_expected_contract(monkeypatch):
    """NLP client sends correct multipart fields per CLAUDE.md §18."""
    monkeypatch.setattr(nlp_client_module.httpx, "AsyncClient", DummyAsyncClient)

    sample_content = b"%PDF-1.4\ncontract test"

    client = NLPServiceClient()
    result = asyncio.run(
        client.process_document(
            document_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            file_content=sample_content,
            filename="sample.pdf",
        )
    )

    assert result is not None
    assert result.full_text == "full text from nlp"
    assert DummyAsyncClient.captured["url"].endswith("/nlp/process")
    assert DummyAsyncClient.captured["data"]["document_id"] == "12345678-1234-5678-1234-567812345678"
    assert DummyAsyncClient.captured["data"]["file_type"] == "pdf"
    assert "file" in DummyAsyncClient.captured["files"]
    assert DummyAsyncClient.captured["files"]["file"][0] == "sample.pdf"


def test_nlp_client_detects_tiff_file_type(monkeypatch):
    """NLP client normalizes .tif → tiff for FileType literal."""
    monkeypatch.setattr(nlp_client_module.httpx, "AsyncClient", DummyAsyncClient)

    client = NLPServiceClient()
    result = asyncio.run(
        client.process_document(
            document_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            file_content=b"fake tiff content",
            filename="scan.tif",
        )
    )

    assert result is not None
    assert DummyAsyncClient.captured["data"]["file_type"] == "tiff"


def test_nlp_client_detects_image_file_type(monkeypatch):
    """NLP client detects jpg file type correctly."""
    monkeypatch.setattr(nlp_client_module.httpx, "AsyncClient", DummyAsyncClient)

    client = NLPServiceClient()
    result = asyncio.run(
        client.process_document(
            document_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            file_content=b"fake jpg content",
            filename="photo.jpg",
        )
    )

    assert result is not None
    assert DummyAsyncClient.captured["data"]["file_type"] == "jpg"
