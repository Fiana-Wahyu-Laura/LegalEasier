"""
schemas.py — LegalEasier NLP Pipeline
Pydantic request/response schemas untuk NLP service.

Rules (CLAUDE.md §8):
- Semua endpoint harus mengembalikan format standar { success, data, message } untuk endpoint OCR legacy.
- Endpoint kontrak backend ↔ NLP memakai response JSON langsung sesuai `backend/docs/nlp_contract.md`.
- Pydantic models untuk semua request dan response schema — no raw dicts.

Sprint 1: OCR extraction schemas.
Sprint 2: Preprocessing + RAG (embed & store) schemas.
          ProcessRequest / ProcessResponse (endpoint POST /nlp/process).
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict

from llm.prompts import DISCLAIMER


# ---------------------------------------------------------------------------
# Standard response wrapper (CLAUDE.md §8)
# ---------------------------------------------------------------------------


class StandardResponse(BaseModel):
    """Wrapper standar untuk semua response NLP service."""

    success: bool
    data: Any | None = None
    message: str


# ---------------------------------------------------------------------------
# Risk Clause Schema (Sprint 3 — sesuai API contract CLAUDE.md §18)
# ---------------------------------------------------------------------------


class RiskClauseSchema(BaseModel):
    """Satu klausul berisiko — sesuai API contract Backend ↔ NLP."""

    clause_text: str = Field(
        description="Teks asli klausul dari dokumen."
    )
    plain_language: str = Field(
        description="Penjelasan dalam bahasa sederhana untuk pengguna."
    )
    risk_level: Literal["Tinggi", "Sedang", "Rendah", "Aman"] = Field(
        description="Level risiko klausul."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score analisis (0.0–1.0).",
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response untuk endpoint health check."""

    status: str
    service: str
    version: str


# ---------------------------------------------------------------------------
# OCR Schemas (Sprint 1)
# ---------------------------------------------------------------------------


class OCRResponse(BaseModel):
    """Response data untuk endpoint OCR extraction."""

    document_id: str = Field(
        description="UUID dokumen yang diproses (dikirim oleh backend)."
    )
    full_text: str = Field(
        description="Teks lengkap hasil ekstraksi / OCR."
    )
    page_count: int = Field(
        description="Jumlah halaman dokumen yang diproses."
    )
    ocr_used: bool = Field(
        description=(
            "True jika Tesseract OCR digunakan (PDF scan / gambar). "
            "False jika teks diekstrak langsung dari PDF digital via PyMuPDF."
        )
    )
    char_count: int = Field(
        description="Jumlah karakter pada full_text (untuk monitoring kualitas OCR)."
    )
    file_type: str = Field(
        description="Tipe file yang diproses: 'pdf', 'jpg', 'jpeg', 'png'."
    )


# ---------------------------------------------------------------------------
# Preprocessing Schemas (Sprint 2)
# ---------------------------------------------------------------------------


class PreprocessingResult(BaseModel):
    """Hasil preprocessing satu teks (cleaning + tokenization + splitting)."""

    cleaned_text: str = Field(
        description="Teks setelah normalisasi dan pembersihan."
    )
    token_count: int = Field(
        description="Jumlah token setelah tokenisasi SpaCy."
    )
    sentence_count: int = Field(
        description="Jumlah kalimat setelah sentence splitting."
    )
    char_count: int = Field(
        description="Jumlah karakter teks yang sudah dibersihkan."
    )


# ---------------------------------------------------------------------------
# RAG / Embedding Schemas (Sprint 2)
# ---------------------------------------------------------------------------


class EmbedStoreResult(BaseModel):
    """Hasil proses chunking + embedding + store ke ChromaDB."""

    document_id: str = Field(
        description="UUID dokumen yang diproses."
    )
    chunk_count: int = Field(
        description="Jumlah chunk yang berhasil di-embed dan disimpan ke ChromaDB."
    )
    chunk_size: int = Field(
        description="Ukuran chunk yang digunakan (karakter)."
    )
    chunk_overlap: int = Field(
        description="Overlap antar chunk (karakter)."
    )
    collection_name: str = Field(
        description="Nama collection ChromaDB yang digunakan."
    )


# ---------------------------------------------------------------------------
# Full NLP Process Schemas (Sprint 2 — API contract Backend ↔ NLP)
# ---------------------------------------------------------------------------
# Sesuai dengan API contract di CLAUDE.md §18 (Backend ↔ NLP Service)
# Endpoint: POST /nlp/process
# ---------------------------------------------------------------------------


class ProcessResponse(BaseModel):
    """Response POST /nlp/process — sesuai API contract Backend ↔ NLP (CLAUDE.md §18).

    Endpoint ini return flat JSON (bukan StandardResponse wrapper) karena
    dikonsumsi oleh Backend sebagai internal service-to-service call.
    HTTP status code sudah cukup untuk sinyal sukses/gagal.

    Sprint 2: document_id, ocr_used, full_text, preprocessing, embed_store.
    Sprint 3: summary, risk_score, risk_clauses diisi dengan nilai nyata dari LLM.
    """

    document_id: str = Field(
        description="UUID dokumen dari backend."
    )
    ocr_used: bool = Field(
        description="True jika Tesseract OCR digunakan saat ekstraksi."
    )
    full_text: str = Field(
        description="Teks lengkap dokumen setelah OCR dan cleaning."
    )

    # Sprint 2 — metadata pipeline
    preprocessing: PreprocessingResult = Field(
        description="Hasil preprocessing (cleaning + tokenization + splitting)."
    )
    embed_store: EmbedStoreResult = Field(
        description="Hasil chunking + embedding + store ke ChromaDB."
    )

    # Sprint 3 — LLM analysis fields
    summary: str = Field(
        default="",
        description="Ringkasan singkat dokumen dalam bahasa Indonesia.",
    )
    risk_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Skor risiko 0–100. Default 0 = belum dianalisis.",
    )
    risk_clauses: list[RiskClauseSchema] = Field(
        default_factory=list,
        description="Daftar klausul berisiko dengan penjelasan.",
    )
    disclaimer: str = Field(
        default="Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional.",
        description="Disclaimer wajib pada setiap output NLP (CLAUDE.md §6).",
    )


# ---------------------------------------------------------------------------
# Retrieval Schemas (Sprint 2 — untuk endpoint debug/internal)
# ---------------------------------------------------------------------------


class RetrieveRequest(BaseModel):
    """Request untuk semantic search di ChromaDB."""

    document_id: str = Field(description="UUID dokumen yang akan di-search.")
    query: str = Field(description="Query untuk semantic search.")
    top_k: int = Field(default=5, ge=1, le=20, description="Jumlah chunk yang diambil.")
    min_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Threshold similarity minimum (0.0–1.0).",
    )


class RetrieveResponse(BaseModel):
    """Response untuk semantic search di ChromaDB."""

    document_id: str
    query: str
    chunks: list[str] = Field(description="Chunk yang relevan, urut dari paling relevan.")
    similarities: list[float] = Field(description="Similarity score tiap chunk (0.0–1.0).")
    found_count: int


# ---------------------------------------------------------------------------
# Chatbot Schemas (Sprint 4)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Satu pesan dalam conversation history."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, description="Isi pesan.")

    model_config = ConfigDict(extra="forbid")


class ChatRequest(BaseModel):
    """Request untuk POST /nlp/chat."""

    document_id: str = Field(min_length=1, description="UUID dokumen yang dibahas.")
    query: str = Field(min_length=1, description="Pertanyaan user saat ini.")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Conversation history (max 20 pesan terakhir).",
        max_length=20,
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Jumlah chunk konteks.")

    model_config = ConfigDict(extra="forbid")


class ChatResponse(BaseModel):
    """Response untuk POST /nlp/chat."""

    document_id: str
    query: str
    answer: str = Field(description="Jawaban chatbot dalam bahasa Indonesia.")
    context_chunks_used: int = Field(description="Jumlah chunk konteks yang digunakan.")
    context_chunks: list[str] = Field(default_factory=list, description="Teks asli potongan dokumen yang menjadi konteks.")
    suggestions: list[str] = Field(
        default_factory=list,
        description="3 pertanyaan lanjutan yang disarankan.",
    )
    disclaimer: str = Field(default=DISCLAIMER)
