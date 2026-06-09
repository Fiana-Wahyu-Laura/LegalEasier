"""
Storage service for handling file uploads.
Supports local disk storage, PostgreSQL bytea storage, and S3/MinIO object storage.
"""

import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import get_settings


class StorageService:
    """
    Storage handler supporting:
    - Local disk storage (legacy)
    - PostgreSQL bytea storage (new default)
    """

    def __init__(self, storage_root: str | Path | None = None, use_bytea: bool = True):
        self.settings = get_settings()
        self.storage_root = Path(storage_root or self.settings.storage_root)
        self.use_bytea = use_bytea  # If True, return file content; if False, return storage path
        if not use_bytea:
            self.storage_root.mkdir(parents=True, exist_ok=True)

    def _get_storage_path(self, original_filename: str, document_id: uuid.UUID) -> Tuple[str, Path]:
        """
        Generate storage path and relative path for a document.
        Format: YYYY/MM/DD/<document_id>.<extension>
        Returns: (relative_path_for_db, absolute_path_on_disk)

        Note: When using bytea storage, the relative path is still generated for metadata
        but the file content is stored in the database as binary.
        """
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")

        # Extract file extension
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".bin"  # Default if no extension

        # Build relative path for database storage_path column
        relative_path = f"{year}/{month}/{day}/{document_id}{ext}"

        # Build absolute filesystem path
        abs_path = self.storage_root / relative_path

        return relative_path, abs_path

    def save_file(
        self, file_path: str, original_filename: str, document_id: uuid.UUID
    ) -> Tuple[str, Optional[bytes]]:
        """
        Save uploaded file to storage.

        Args:
            file_path: Temporary path where file was saved
            original_filename: Original filename from upload
            document_id: UUID of document record

        Returns:
            Tuple of (relative_path, file_content)
            - relative_path: Path to store in storage_path column (e.g., "2026/05/11/<uuid>.pdf")
            - file_content: Binary content if use_bytea=True, else None
        """
        relative_path, abs_path = self._get_storage_path(original_filename, document_id)

        if self.use_bytea:
            # Read file content and return it for bytea storage
            with open(file_path, 'rb') as f:
                file_content = f.read()
            return relative_path, file_content
        else:
            # Save to local disk (legacy behavior)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, abs_path)
            return relative_path, None

    def get_file_path(self, storage_path: str) -> Path:
        """
        Get absolute path for a stored file (local disk only).
        Args:
            storage_path: Relative path from database (e.g., "2026/05/11/<uuid>.pdf")

        Returns:
            Absolute path on filesystem
        """
        return self.storage_root / storage_path

    def delete_file(self, storage_path: str) -> bool:
        """Delete a file from local disk storage."""
        if self.use_bytea:
            # No-op for bytea storage; deletion happens at database level
            return True

        file_path = self.get_file_path(storage_path)
        try:
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception:
            pass
        return False

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in local disk storage."""
        if self.use_bytea:
            # For bytea, check database level (handled elsewhere)
            return True
        return self.get_file_path(storage_path).exists()


class S3StorageService:
    """
    Storage handler using S3-compatible MinIO object storage.

    Documents are stored as objects in a MinIO bucket.  The storage_path
    column in the documents table holds the object key (e.g.
    "2026/06/09/<uuid>.pdf").  No binary data is stored in PostgreSQL.
    """

    def __init__(self):
        from minio import Minio

        self.settings = get_settings()
        self.client = Minio(
            self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )
        self.bucket = self.settings.minio_bucket_name

    def _get_object_key(self, original_filename: str, document_id: uuid.UUID) -> str:
        """
        Generate S3 object key for a document.
        Format: YYYY/MM/DD/<document_id>.<extension>
        """
        now = datetime.now(timezone.utc)
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".bin"
        return f"{now:%Y/%m/%d}/{document_id}{ext}"

    def save_file(
        self, file_path: str, original_filename: str, document_id: uuid.UUID
    ) -> Tuple[str, Optional[bytes]]:
        """
        Upload file to MinIO bucket.

        Returns:
            Tuple of (object_key, None)
            - object_key: S3 key to store in storage_path column
            - None: no bytea content (file lives in MinIO)
        """
        import io
        import mimetypes

        object_key = self._get_object_key(original_filename, document_id)

        # Read file bytes first — avoids streaming signature issues with minio-py 7.x
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Detect content type
        content_type, _ = mimetypes.guess_type(original_filename)

        self.client.put_object(
            self.bucket,
            object_key,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type or "application/octet-stream",
        )
        return object_key, None

    def get_file(self, storage_path: str) -> bytes:
        """
        Download file bytes from MinIO.

        Args:
            storage_path: S3 object key (e.g., "2026/06/09/<uuid>.pdf")

        Returns:
            File bytes
        """
        response = self.client.get_object(self.bucket, storage_path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, storage_path: str) -> bool:
        """
        Remove object from MinIO.  Best-effort — errors are logged but not raised.
        """
        import logging
        logger = logging.getLogger(__name__)
        try:
            self.client.remove_object(self.bucket, storage_path)
            return True
        except Exception as exc:
            logger.warning("Failed to delete S3 object %s: %s", storage_path, exc)
            return False

    def get_presigned_download_url(
        self, storage_path: str, expiry_seconds: int = 3600
    ) -> str:
        """
        Generate a presigned GET URL for temporary direct access.

        Args:
            storage_path: S3 object key
            expiry_seconds: URL lifetime (default 1 hour, max 7 days)

        Returns:
            Presigned URL string
        """
        return self.client.presigned_get_object(
            self.bucket,
            storage_path,
            expires=timedelta(seconds=expiry_seconds),
        )


def get_storage_service():
    """
    Dependency injection for storage service.

    Returns S3StorageService when USE_S3_STORAGE=true,
    otherwise the legacy StorageService (bytea mode).
    """
    settings = get_settings()
    if settings.use_s3_storage:
        return S3StorageService()
    return StorageService(use_bytea=True)
