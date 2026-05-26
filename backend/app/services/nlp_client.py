"""
NLP service client for OCR processing.
Handles communication with Indra's NLP pipeline service.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, cast
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.schemas.nlp import (
    FileType,
    NLPChatRequest,
    NLPChatResponse,
    NLPProcessRequest,
    NLPProcessResponse,
)

logger = logging.getLogger(__name__)


class NLPServiceClient:
    """Client for NLP/OCR service integration."""

    def __init__(self):
        self.settings = get_settings()
        # Remove trailing slash from base_url to avoid double slashes in endpoints
        self.base_url = str(self.settings.nlp_service_url).rstrip("/")
        self.timeout = 300  # 5 minutes for OCR processing

    @staticmethod
    def _detect_file_type(file_path: str) -> FileType:
        suffix = Path(file_path).suffix.lower().lstrip(".")
        # Normalize tif → tiff to match FileType literal
        if suffix == "tif":
            suffix = "tiff"
        if suffix in {"pdf", "jpg", "png", "tiff"}:
            return cast(FileType, suffix)

        # Default to pdf-like handling when the extension is unknown.
        return "pdf"

    @staticmethod
    def _mime_type_for_file_type(file_type: FileType) -> str:
        return {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "png": "image/png",
            "tiff": "image/tiff",
        }[file_type]

    async def process_document(
        self,
        document_id: UUID,
        file_content: bytes,
        filename: str,
    ) -> Optional[NLPProcessResponse]:
        """
        Send document to NLP service for OCR + analysis processing.

        The agreed multipart contract is:
        - document_id: UUID
        - file_type: pdf|jpg|png|docx
        - file: binary file bytes

        Args:
            document_id: UUID of the document
            file_content: Binary content of the file (from PostgreSQL BYTEA)
            filename: Original filename (for extension detection)

        Returns the parsed JSON payload from NLP or None if the service fails.
        """
        try:
            file_type = self._detect_file_type(filename)
            request = NLPProcessRequest(document_id=document_id, file_type=file_type)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                files = {
                    "file": (
                        filename,
                        file_content,
                        self._mime_type_for_file_type(request.file_type),
                    )
                }
                data = {
                    "document_id": str(request.document_id),
                    "file_type": request.file_type,
                }

                response = await client.post(
                    f"{self.base_url}/nlp/process",
                    files=files,
                    data=data,
                )

                if response.status_code == 200:
                    return NLPProcessResponse.model_validate(response.json())
                else:
                    logger.error(
                        "NLP service error for %s: %s %s",
                        document_id, response.status_code, response.text,
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("NLP service timeout for document %s", document_id)
            return None
        except Exception as e:
            logger.error("NLP service error for document %s: %s", document_id, e)
            return None

    async def chat_document(
        self,
        document_id: UUID,
        query: str,
        history: list[dict] | None = None,
        top_k: int = 5,
    ) -> NLPChatResponse | None:
        """Send a chat question to NLP RAG endpoint."""
        request = NLPChatRequest(
            document_id=str(document_id),
            query=query,
            history=history or [],
            top_k=top_k,
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/nlp/chat",
                    json=request.model_dump(mode="json"),
                )

                if response.status_code == 200:
                    return NLPChatResponse.model_validate(response.json())

                logger.error(
                    "NLP chat service error for %s: %s %s",
                    document_id,
                    response.status_code,
                    response.text,
                )
                return None

        except httpx.TimeoutException:
            logger.error("NLP chat service timeout for document %s", document_id)
            return None
        except Exception as e:
            logger.error("NLP chat service error for %s: %s", document_id, e)
            return None

    async def delete_document_collection(
        self,
        document_id: UUID,
    ) -> bool:
        """
        Delete NLP/vector collection for a document.

        Failure here should not block document deletion.
        """

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(
                    f"{self.base_url}/nlp/{document_id}"
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(
                "Failed to delete NLP collection for %s: %s",
                document_id, e,
            )

            # Do not raise error
            return False

def get_nlp_client() -> NLPServiceClient:
    """Dependency injection for NLP client."""
    return NLPServiceClient()
