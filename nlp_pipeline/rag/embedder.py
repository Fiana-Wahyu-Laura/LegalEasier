"""
embedder.py — LegalEasier NLP Pipeline
Embedding teks menggunakan sentence-transformers.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Langkah 5 dari pipeline: Embedding dengan all-MiniLM-L6-v2.

Model:
- all-MiniLM-L6-v2: model ringan, 384 dimensi, cocok untuk semantic search.
- Model di-load sebagai singleton (lazy loading) agar tidak reload per request.
- Model pertama kali di-load akan otomatis didownload (~80MB).

Aturan:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model singleton — lazy loading
# ---------------------------------------------------------------------------

_embedding_model: Optional[SentenceTransformer] = None

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimensi output model all-MiniLM-L6-v2


def get_embedding_model() -> SentenceTransformer:
    """Muat model embedding sekali dan simpan sebagai singleton.

    Model akan didownload otomatis (~80MB) saat pertama kali dipakai.

    Returns:
        SentenceTransformer model yang sudah dimuat.

    Raises:
        RuntimeError: Jika model gagal dimuat.
    """
    global _embedding_model
    if _embedding_model is None:
        try:
            logger.info(
                "Memuat embedding model '%s'...", EMBEDDING_MODEL_NAME
            )
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info(
                "Embedding model '%s' berhasil dimuat (dimensi=%d).",
                EMBEDDING_MODEL_NAME,
                EMBEDDING_DIMENSION,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Gagal memuat embedding model '{EMBEDDING_MODEL_NAME}': {exc}"
            ) from exc
    return _embedding_model


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------


def embed_text(text: str) -> list[float]:
    """Embed satu teks menjadi vektor float.

    Args:
        text: Teks yang akan di-embed (sebaiknya sudah dibersihkan).

    Returns:
        List float dengan panjang EMBEDDING_DIMENSION (384).

    Raises:
        ValueError: Jika text bukan string atau kosong.
        RuntimeError: Jika model gagal dijalankan.
    """
    if not isinstance(text, str):
        raise ValueError(
            f"text harus bertipe str, bukan {type(text).__name__}."
        )
    if not text.strip():
        raise ValueError("text tidak boleh kosong.")

    model = get_embedding_model()

    try:
        embedding: NDArray[np.float32] = model.encode(
            text,
            normalize_embeddings=True,  # Cosine similarity tanpa perlu normalize ulang
            show_progress_bar=False,
        )
        return embedding.tolist()
    except Exception as exc:
        raise RuntimeError(f"Gagal melakukan embedding: {exc}") from exc


def embed_chunks(chunks: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed banyak chunk sekaligus menggunakan batch processing.

    Lebih efisien dibanding memanggil embed_text satu per satu.
    Ini adalah fungsi utama yang dipanggil dari pipeline (langkah 5).

    Args:
        chunks: List teks chunk (output dari chunker.chunk_text).
        batch_size: Jumlah chunk yang diproses per batch GPU/CPU.
            Default: 32 (balance antara kecepatan dan memori).

    Returns:
        List of list float — satu embedding per chunk.
        Urutan sesuai dengan urutan input chunks.

    Raises:
        ValueError: Jika chunks kosong atau mengandung item bukan string.
        RuntimeError: Jika model gagal dijalankan.
    """
    if not chunks:
        raise ValueError("chunks tidak boleh kosong.")

    for i, chunk in enumerate(chunks):
        if not isinstance(chunk, str):
            raise ValueError(
                f"chunks[{i}] harus bertipe str, bukan {type(chunk).__name__}."
            )

    model = get_embedding_model()

    # Filter chunk kosong sebelum encoding
    valid_chunks = [c for c in chunks if c.strip()]
    if not valid_chunks:
        raise ValueError("Semua chunk kosong setelah di-filter.")

    try:
        logger.info(
            "Embedding %d chunk dengan model '%s' (batch_size=%d)...",
            len(valid_chunks),
            EMBEDDING_MODEL_NAME,
            batch_size,
        )
        embeddings: NDArray[np.float32] = model.encode(
            valid_chunks,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        result = embeddings.tolist()
        logger.info("Embedding selesai: %d vektor (dim=%d).", len(result), EMBEDDING_DIMENSION)
        return result
    except Exception as exc:
        raise RuntimeError(f"Gagal melakukan batch embedding: {exc}") from exc


def compute_similarity(embedding_a: list[float], embedding_b: list[float]) -> float:
    """Hitung cosine similarity antara dua vektor embedding.

    Karena embedding sudah dinormalisasi (normalize_embeddings=True),
    cosine similarity = dot product.

    Args:
        embedding_a: Vektor pertama (list float, panjang 384).
        embedding_b: Vektor kedua (list float, panjang 384).

    Returns:
        Cosine similarity antara 0.0 dan 1.0.

    Raises:
        ValueError: Jika panjang kedua vektor tidak sama.
    """
    if len(embedding_a) != len(embedding_b):
        raise ValueError(
            f"Panjang embedding tidak sama: {len(embedding_a)} vs {len(embedding_b)}."
        )
    a = np.array(embedding_a, dtype=np.float32)
    b = np.array(embedding_b, dtype=np.float32)
    return float(np.dot(a, b))
