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
        self.use_bytea = use_bytea
        if not use_bytea:
            self.storage_root.mkdir(parents=True, exist_ok=True)

    def _get_storage_path(self, original_filename: str, document_id: uuid.UUID) -> Tuple[str, Path]:
        now = datetime.now(timezone.utc)
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".bin"
        relative_path = f"{now:%Y/%m/%d}/{document_id}{ext}"
        abs_path = self.storage_root / relative_path
        return relative_path, abs_path

    def save_file(
        self, file_path: str, original_filename: str, document_id: uuid.UUID
    ) -> Tuple[str, Optional[bytes]]:
        relative_path, abs_path = self._get_storage_path(original_filename, document_id)
        if self.use_bytea:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            return relative_path, file_content
        else:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, abs_path)
            return relative_path, None

    def get_file_path(self, storage_path: str) -> Path:
        return self.storage_root / storage_path

    def delete_file(self, storage_path: str) -> bool:
        if self.use_bytea:
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
        if self.use_bytea:
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
        now = datetime.now(timezone.utc)
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".bin"
        return f"{now:%Y/%m/%d}/{document_id}{ext}"

    def save_file(
        self, file_path: str, original_filename: str, document_id: uuid.UUID
    ) -> Tuple[str, Optional[bytes]]:
        """Upload file to MinIO bucket. Returns (object_key, None)."""
        import mimetypes

        object_key = self._get_object_key(original_filename, document_id)
        content_type, _ = mimetypes.guess_type(original_filename)

        self.client.fput_object(
            self.bucket,
            object_key,
            file_path,
            content_type=content_type or "application/octet-stream",
        )
        return object_key, None

    def get_file(self, storage_path: str) -> bytes:
        """Download file bytes from MinIO."""
        response = self.client.get_object(self.bucket, storage_path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, storage_path: str) -> bool:
        """Remove object from MinIO. Best-effort."""
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
        """Generate a presigned GET URL for temporary direct access."""
        return self.client.presigned_get_object(
            self.bucket,
            storage_path,
            expires=timedelta(seconds=expiry_seconds),
        )


def get_storage_service():
    """Dependency injection for storage service."""
    settings = get_settings()
    if settings.use_s3_storage:
        return S3StorageService()
    return StorageService(use_bytea=True)
