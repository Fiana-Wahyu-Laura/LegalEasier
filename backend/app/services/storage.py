"""
Storage service for handling file uploads.
Supports both local disk storage and PostgreSQL bytea storage.
"""

import os
import shutil
import uuid
from datetime import datetime, timezone
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


def get_storage_service() -> StorageService:
    """Dependency injection for storage service (uses bytea by default)."""
    return StorageService(use_bytea=True)
