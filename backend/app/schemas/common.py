"""
Standard response wrapper for all backend API endpoints.

Per CLAUDE.md §8: All endpoints must return:
{
  "success": true/false,
  "data": <T> | null,
  "message": "descriptive message"
}
"""

from typing import Any

from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """Wrapper standar untuk semua response backend API (CLAUDE.md §8)."""

    success: bool = Field(description="True jika request berhasil, False jika gagal.")
    data: Any | None = Field(default=None, description="Data payload response.")
    message: str = Field(description="Pesan deskriptif tentang hasil request.")
