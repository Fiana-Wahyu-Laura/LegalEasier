"""
main.py — LegalEasier NLP Pipeline
FastAPI entry point untuk NLP microservice (port 8001).

Menjalankan:
    uvicorn main:app --reload --port 8001

Endpoints Sprint 1:
    GET  /health           → health check
    POST /ocr/extract      → OCR extraction (PyMuPDF + Tesseract fallback)

Endpoints Sprint 2:
    POST /nlp/process      → Pipeline lengkap: OCR → preprocess → chunk → embed → store → LLM
    POST /nlp/retrieve     → Semantic search untuk RAG context (debug/internal)
    GET  /nlp/info/{id}    → Info collection ChromaDB untuk satu dokumen
    DELETE /nlp/{id}       → Hapus collection ChromaDB saat dokumen dihapus

Sprint 3:
    Langkah 7 ditambahkan ke POST /nlp/process:
    → LLM analysis (risk detection, plain language, summary, score)

Rules (CLAUDE.md):
- Semua endpoint kecuali /health memerlukan validasi dari backend (Sprint 2+).
- Semua response menggunakan format standar { success, data, message }.
- Error handling: jangan expose stack trace ke response.
- Pydantic models untuk semua request/response — no raw dicts.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from core.config import settings
from ocr.image_ocr import extract_text_from_image, extract_text_from_pdf_scan
from ocr.pdf_extractor import extract_text_from_pdf
from preprocessing.cleaner import clean_legal_text
from preprocessing.splitter import split_text
from rag.chunker import chunk_text
from rag.embedder import embed_chunks, warmup_embedding_model
from rag.retriever import retrieve_all_chunks, retrieve_relevant_chunks
from rag.vector_store import delete_document_collection, get_collection_info, store_chunks
from llm.analyzer import analyze_document
from llm.chatbot import chat_with_document
from llm.risk_scorer import compute_risk_score
from schemas import (
    ChatRequest,
    ChatResponse,
    EmbedStoreResult,
    HealthResponse,
    OCRResponse,
    PreprocessingResult,
    ProcessResponse,
    RetrieveRequest,
    RetrieveResponse,
    RiskClauseSchema,
    StandardResponse,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Jalankan startup/shutdown tasks."""
    logger.info("NLP Pipeline service dimulai di port %d.", settings.service_port)
    # Warmup embedding model to avoid cold-start latency
    warmup_embedding_model()
    yield
    logger.info("NLP Pipeline service dihentikan.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LegalEasier NLP Pipeline",
    description=(
        "Microservice untuk OCR, preprocessing, RAG, dan analisis dokumen hukum Indonesia. "
        "Sprint 1: OCR extraction. Sprint 2: Preprocessing + RAG pipeline."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — izinkan backend memanggil service ini (localhost dev + Docker network)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://170.30.0.3:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Timing middleware — log dan return processing time
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_processing_time(request: Request, call_next) -> Response:
    """Add X-Processing-Time header to all responses."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Processing-Time"] = f"{elapsed_ms:.0f}ms"
    logger.info(
        "%s %s — %.0fms",
        request.method, request.url.path, elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Allowed file types
# ---------------------------------------------------------------------------

ALLOWED_FILE_TYPES = {"pdf", "jpg", "jpeg", "png", "tiff", "tif"}


def _validate_file_type(file_type: str) -> str:
    """Validasi dan normalisasi tipe file."""
    normalized = file_type.lower().lstrip(".")
    if normalized not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipe file tidak didukung: '{file_type}'. "
                   f"Gunakan salah satu dari: {', '.join(ALLOWED_FILE_TYPES)}.",
        )
    return normalized


def _validate_file_size(file_bytes: bytes) -> None:
    """Validasi ukuran file tidak melebihi batas maksimum."""
    if len(file_bytes) > settings.max_file_size_bytes:
        max_mb = settings.max_file_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ukuran file melebihi batas maksimum {max_mb}MB.",
        )




# ---------------------------------------------------------------------------
# Helper: OCR extraction (shared logic)
# ---------------------------------------------------------------------------

async def _run_ocr(
    file_bytes: bytes,
    normalized_type: str,
    doc_id: str,
) -> OCRResponse:
    """Jalankan OCR pipeline dan kembalikan OCRResponse.

    Args:
        file_bytes: Bytes konten file.
        normalized_type: Tipe file yang sudah dinormalisasi ('pdf', 'jpg', dll.).
        doc_id: UUID dokumen.

    Returns:
        OCRResponse dengan full_text dan metadata.

    Raises:
        HTTPException: Jika file tidak valid atau OCR gagal.
    """
    try:
        if normalized_type == "pdf":
            pdf_result = extract_text_from_pdf(file_bytes)

            if pdf_result.full_text:
                return OCRResponse(
                    document_id=doc_id,
                    full_text=pdf_result.full_text,
                    page_count=pdf_result.page_count,
                    ocr_used=False,
                    char_count=len(pdf_result.full_text),
                    file_type=normalized_type,
                )
            else:
                logger.info(
                    "PyMuPDF tidak menemukan teks pada '%s'. Fallback ke Tesseract OCR.",
                    doc_id,
                )
                ocr_result = extract_text_from_pdf_scan(file_bytes)
                return OCRResponse(
                    document_id=doc_id,
                    full_text=ocr_result.full_text,
                    page_count=ocr_result.page_count,
                    ocr_used=True,
                    char_count=len(ocr_result.full_text),
                    file_type=normalized_type,
                )
        else:
            ocr_result = extract_text_from_image(file_bytes, file_type=normalized_type)
            return OCRResponse(
                document_id=doc_id,
                full_text=ocr_result.full_text,
                page_count=ocr_result.page_count,
                ocr_used=True,
                char_count=len(ocr_result.full_text),
                file_type=normalized_type,
            )

    except ValueError as exc:
        logger.warning("File tidak valid untuk dokumen '%s': %s", doc_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        logger.error("Runtime error saat OCR dokumen '%s': %s", doc_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memproses dokumen. Silakan coba lagi atau hubungi administrator.",
        ) from exc


# ---------------------------------------------------------------------------
# Routes — Sprint 1
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Cek status NLP service. Tidak memerlukan autentikasi."""
    return HealthResponse(
        status="ok",
        service="legaleasier-nlp-pipeline",
        version="0.2.0",
    )


@app.post(
    "/ocr/extract",
    response_model=StandardResponse,
    summary="OCR Extraction Only",
    tags=["OCR"],
    status_code=status.HTTP_200_OK,
)
async def ocr_extract(
    file: UploadFile = File(..., description="File dokumen (PDF, JPG, PNG)."),
    file_type: str = Form(..., description="Tipe file: 'pdf', 'jpg', 'jpeg', 'png', 'tiff'."),
    document_id: str = Form(
        default="",
        description="UUID dokumen dari backend (opsional, untuk tracking).",
    ),
) -> StandardResponse:
    """
    Ekstrak teks dari dokumen menggunakan OCR pipeline:
    1. Untuk PDF → coba PyMuPDF terlebih dahulu (teks digital).
    2. Jika PyMuPDF gagal / teks kosong → fallback ke Tesseract OCR.
    3. Untuk gambar (JPG/PNG) → langsung Tesseract OCR.

    Endpoint ini hanya melakukan OCR (langkah 1).
    Untuk pipeline lengkap (OCR + preprocess + RAG), gunakan POST /nlp/process.
    """
    doc_id = document_id if document_id else str(uuid.uuid4())
    file_bytes: bytes = await file.read()

    normalized_type = _validate_file_type(file_type)
    _validate_file_size(file_bytes)

    logger.info(
        "Memproses OCR dokumen '%s' (tipe=%s, ukuran=%d bytes).",
        doc_id,
        normalized_type,
        len(file_bytes),
    )

    ocr_data = await _run_ocr(file_bytes, normalized_type, doc_id)

    method = "Tesseract OCR" if ocr_data.ocr_used else "PyMuPDF (teks digital)"
    logger.info(
        "Dokumen '%s' berhasil diproses via %s: %d karakter.",
        doc_id,
        method,
        ocr_data.char_count,
    )

    return StandardResponse(
        success=True,
        data=ocr_data.model_dump(),
        message=f"Ekstraksi teks berhasil menggunakan {method}.",
    )


# ---------------------------------------------------------------------------
# Routes — Sprint 2
# ---------------------------------------------------------------------------

@app.post(
    "/nlp/process",
    response_model=ProcessResponse,
    summary="Full NLP Pipeline (OCR → Preprocess → Chunk → Embed → Store → LLM Analysis)",
    tags=["NLP Pipeline"],
    status_code=status.HTTP_200_OK,
)
async def nlp_process(
    file: UploadFile = File(..., description="File dokumen (PDF, JPG, PNG, TIFF)."),
    file_type: str = Form(..., description="Tipe file: 'pdf', 'jpg', 'jpeg', 'png', 'tiff'."),
    document_id: str = Form(..., description="UUID dokumen dari backend (wajib)."),
) -> ProcessResponse:
    """
    Pipeline NLP lengkap untuk satu dokumen (CLAUDE.md §9).

    Langkah 1: OCR / text extraction (PyMuPDF + Tesseract fallback)
    Langkah 2: Cleaning & normalization (cleaner.clean_legal_text)
    Langkah 3: Tokenization & sentence splitting (SpaCy + NLTK)
    Langkah 4: Chunking (LangChain, 512 karakter, overlap 50)
    Langkah 5: Embedding (sentence-transformers all-MiniLM-L6-v2)
    Langkah 6: Store vectors ke ChromaDB (collection: doc_{uuid})
    Langkah 7: LLM analysis (risk detection, plain language, summary, score)

    Response: flat JSON sesuai API contract Backend ↔ NLP (CLAUDE.md §18).
    Tidak menggunakan StandardResponse wrapper — ini internal service-to-service call.
    """
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_id wajib diisi.",
        )

    file_bytes: bytes = await file.read()
    normalized_type = _validate_file_type(file_type)
    _validate_file_size(file_bytes)

    logger.info(
        "Memulai NLP pipeline untuk dokumen '%s' (tipe=%s, ukuran=%d bytes).",
        document_id,
        normalized_type,
        len(file_bytes),
    )

    # ── Langkah 1: OCR ──────────────────────────────────────────────────
    logger.info("[%s] Langkah 1/7: OCR extraction...", document_id)
    ocr_data = await _run_ocr(file_bytes, normalized_type, document_id)

    if not ocr_data.full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Teks tidak berhasil diekstrak dari dokumen. "
                "Pastikan dokumen tidak kosong atau tidak rusak."
            ),
        )

    # ── Langkah 2: Cleaning ─────────────────────────────────────────────
    logger.info("[%s] Langkah 2/7: Text cleaning...", document_id)
    try:
        cleaned_text = clean_legal_text(ocr_data.full_text, expand_abbreviations=False)
    except ValueError as exc:
        logger.error("[%s] Gagal cleaning teks: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membersihkan teks dokumen.",
        ) from exc

    # ── Langkah 3: Sentence Splitting (lightweight — no SpaCy) ────────────
    logger.info("[%s] Langkah 3/7: Sentence splitting...", document_id)
    try:
        split_result = split_text(cleaned_text, method="nltk")
    except (ValueError, RuntimeError) as exc:
        logger.error("[%s] Gagal splitting: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memproses teks: sentence splitting gagal.",
        ) from exc

    # Lightweight token count (word-based, avoids SpaCy overhead)
    token_count = len(cleaned_text.split())

    preprocessing_result = PreprocessingResult(
        cleaned_text=cleaned_text,
        token_count=token_count,
        sentence_count=split_result.sentence_count,
        char_count=len(cleaned_text),
    )

    # ── Langkah 4: Chunking ──────────────────────────────────────────────
    logger.info("[%s] Langkah 4/7: Chunking...", document_id)
    try:
        chunk_result = chunk_text(cleaned_text)
    except ValueError as exc:
        logger.error("[%s] Gagal chunking: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membagi teks menjadi chunk.",
        ) from exc

    # ── Langkah 5: Embedding ─────────────────────────────────────────────
    logger.info(
        "[%s] Langkah 5/7: Embedding %d chunk...", document_id, chunk_result.chunk_count
    )
    try:
        embeddings = embed_chunks(chunk_result.chunks)
    except (ValueError, RuntimeError) as exc:
        logger.error("[%s] Gagal embedding: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal melakukan embedding teks.",
        ) from exc

    # ── Langkah 6: Store ke ChromaDB ─────────────────────────────────────
    logger.info("[%s] Langkah 6/7: Storing ke ChromaDB...", document_id)
    collection_name = f"doc_{document_id.replace('-', '_')}"
    try:
        stored_count = store_chunks(
            document_id=document_id,
            chunks=chunk_result.chunks,
            embeddings=embeddings,
        )
    except (ValueError, RuntimeError) as exc:
        logger.error("[%s] Gagal store ke ChromaDB: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyimpan embedding ke vector store.",
        ) from exc

    embed_store_result = EmbedStoreResult(
        document_id=document_id,
        chunk_count=stored_count,
        chunk_size=chunk_result.chunk_size,
        chunk_overlap=chunk_result.chunk_overlap,
        collection_name=collection_name,
    )

    # ── Langkah 7: LLM Analysis (Sprint 3) ──────────────────────────────
    logger.info("[%s] Langkah 7/7: LLM risk analysis...", document_id)

    # Ambil semua chunk dari ChromaDB sebagai context untuk LLM
    # (CLAUDE.md §9: "never ask LLM about document without providing chunks")
    all_chunks = retrieve_all_chunks(document_id)
    if not all_chunks:
        # Fallback: gunakan chunk_result.chunks jika retrieve gagal
        all_chunks = chunk_result.chunks

    analysis_result = analyze_document(
        document_id=document_id,
        context_chunks=all_chunks,
    )

    # Hitung risk score dari klausul berisiko
    risk_score = compute_risk_score(analysis_result.risk_clauses)

    # Konversi RiskClause dataclass → RiskClauseSchema Pydantic model
    risk_clause_schemas = [
        RiskClauseSchema(
            clause_text=rc.clause_text,
            plain_language=rc.plain_language,
            risk_level=rc.risk_level,
            confidence=rc.confidence,
        )
        for rc in analysis_result.risk_clauses
    ]

    # ── Compose response ───────────────────────────────────────────
    process_response = ProcessResponse(
        document_id=document_id,
        ocr_used=ocr_data.ocr_used,
        full_text=cleaned_text,
        preprocessing=preprocessing_result,
        embed_store=embed_store_result,
        summary=analysis_result.summary,
        risk_score=risk_score,
        risk_clauses=risk_clause_schemas,
        disclaimer=analysis_result.disclaimer,
    )

    logger.info(
        "[%s] NLP pipeline selesai: %d token, %d kalimat, %d chunk, "
        "%d klausul berisiko, risk_score=%d.",
        document_id,
        token_count,
        split_result.sentence_count,
        stored_count,
        len(risk_clause_schemas),
        risk_score,
    )

    # Return flat JSON — sesuai API contract Backend ↔ NLP (CLAUDE.md §18).
    return process_response


@app.post(
    "/nlp/retrieve",
    response_model=StandardResponse,
    summary="Semantic Search (RAG Retrieval)",
    tags=["NLP Pipeline"],
    status_code=status.HTTP_200_OK,
)
async def nlp_retrieve(request: RetrieveRequest) -> StandardResponse:
    """
    Semantic search di ChromaDB untuk satu dokumen.

    Endpoint ini untuk:
    - Backend memanggil NLP service saat user bertanya tentang dokumen (Sprint 4).
    - Testing dan debug pipeline RAG secara mandiri.

    Rules (CLAUDE.md §9):
    - JANGAN panggil LLM tanpa context dari endpoint ini.
    """
    try:
        result = retrieve_relevant_chunks(
            document_id=request.document_id,
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error(
            "Gagal retrieval untuk dokumen '%s': %s", request.document_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal melakukan semantic search.",
        ) from exc

    response_data = RetrieveResponse(
        document_id=request.document_id,
        query=request.query,
        chunks=result.chunks,
        similarities=result.similarities,
        found_count=result.found_count,
    )

    return StandardResponse(
        success=True,
        data=response_data.model_dump(),
        message=f"Ditemukan {result.found_count} chunk relevan untuk query.",
    )


@app.post(
    "/nlp/chat",
    response_model=ChatResponse,
    summary="RAG Chatbot — Tanya Jawab Dokumen",
    tags=["Chatbot"],
    status_code=status.HTTP_200_OK,
)
async def nlp_chat(request: ChatRequest) -> ChatResponse:
    """
    RAG chatbot untuk tanya jawab tentang dokumen hukum (Sprint 4).

    Flow:
    1. Retrieve chunk relevan dari ChromaDB berdasarkan query user
    2. Kirim context + history + query ke LLM (Claude/NIM)
    3. Return jawaban + suggestion chips

    Stateless: backend mengirim history di setiap request.
    """
    document_id = request.document_id.strip()
    query = request.query.strip()

    try:
        result = chat_with_document(
            document_id=document_id,
            query=query,
            history=[m.model_dump() for m in request.history],
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        document_id=document_id,
        query=query,
        answer=result.answer,
        context_chunks_used=result.context_chunks_used,
        context_chunks=result.context_chunks,
        suggestions=result.suggestions,
        disclaimer=result.disclaimer,
    )


@app.get(
    "/nlp/info/{document_id}",
    response_model=StandardResponse,
    summary="Info ChromaDB Collection",
    tags=["NLP Pipeline"],
)
async def nlp_collection_info(document_id: str) -> StandardResponse:
    """Dapatkan informasi collection ChromaDB untuk satu dokumen.

    Berguna untuk memverifikasi apakah dokumen sudah diproses dan
    berapa chunk yang tersimpan.
    """
    if not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_id tidak boleh kosong.",
        )

    info = get_collection_info(document_id)
    return StandardResponse(
        success=True,
        data=info,
        message=(
            f"Collection '{info['collection_name']}' "
            f"{'ditemukan' if info['exists'] else 'tidak ditemukan'}."
        ),
    )


@app.delete(
    "/nlp/{document_id}",
    response_model=StandardResponse,
    summary="Hapus ChromaDB Collection",
    tags=["NLP Pipeline"],
)
async def nlp_delete_collection(document_id: str) -> StandardResponse:
    """Hapus collection ChromaDB saat dokumen dihapus dari backend.

    Dipanggil oleh backend saat user menghapus dokumen mereka.
    Rules (CLAUDE.md §9): hapus collection saat dokumen dihapus.
    """
    if not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_id tidak boleh kosong.",
        )

    try:
        deleted = delete_document_collection(document_id)
    except (ValueError, RuntimeError) as exc:
        logger.error(
            "Gagal menghapus collection untuk dokumen '%s': %s", document_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menghapus vector store dokumen.",
        ) from exc

    return StandardResponse(
        success=True,
        data={"document_id": document_id, "deleted": deleted},
        message=(
            "Collection berhasil dihapus."
            if deleted
            else "Collection tidak ditemukan (mungkin sudah terhapus)."
        ),
    )
