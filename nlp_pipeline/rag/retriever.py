"""
retriever.py — LegalEasier NLP Pipeline
Semantic search atas ChromaDB untuk RAG context retrieval.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Dipakai di langkah 7 (LLM analysis) — mengambil chunk yang relevan
    sebagai context untuk LLM agar tidak menjawab tanpa dokumen.

Rules (CLAUDE.md §9 LLM Calls):
- Selalu gunakan RAG context — JANGAN tanya LLM tanpa context dari dokumen.
- System prompt harus menyertakan context dari hasil retrieval ini.

Aturan kode:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging
from dataclasses import dataclass, field

from rag.embedder import embed_text
from rag.vector_store import get_collection_if_exists

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------

DEFAULT_TOP_K = 5  # Jumlah chunk paling relevan yang diambil per query


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """Hasil semantic search dari ChromaDB."""

    query: str
    """Query yang digunakan untuk retrieval."""

    chunks: list[str] = field(default_factory=list)
    """Daftar chunk teks yang paling relevan, urut dari paling relevan."""

    distances: list[float] = field(default_factory=list)
    """Cosine distance tiap chunk (lebih kecil = lebih relevan)."""

    metadatas: list[dict] = field(default_factory=list)
    """Metadata tiap chunk (chunk_index, document_id, dll.)."""

    top_k: int = DEFAULT_TOP_K
    """Jumlah chunk yang diminta."""

    found_count: int = 0
    """Jumlah chunk yang benar-benar ditemukan (≤ top_k)."""

    @property
    def context_text(self) -> str:
        """Gabungkan semua chunk menjadi satu blok teks untuk LLM context.

        Returns:
            Teks gabungan semua chunk dengan pemisah "\n\n---\n\n".
        """
        return "\n\n---\n\n".join(self.chunks)

    @property
    def similarities(self) -> list[float]:
        """Konversi cosine distance ke similarity score (0.0–1.0).

        ChromaDB mengembalikan cosine distance (bukan similarity).
        Similarity = 1 - distance.

        Returns:
            List similarity score.
        """
        return [max(0.0, 1.0 - d) for d in self.distances]


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------


def retrieve_relevant_chunks(
    document_id: str,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_similarity: float = 0.0,
) -> RetrievalResult:
    """Ambil chunk paling relevan dari ChromaDB untuk satu query.

    Langkah:
        1. Embed query menggunakan embedder.embed_text (model yang sama
           dengan saat chunks di-embed — all-MiniLM-L6-v2).
        2. Query ChromaDB collection dokumen tersebut.
        3. Filter hasil berdasarkan min_similarity (opsional).

    Args:
        document_id: UUID dokumen yang akan di-search.
        query: Teks query / pertanyaan untuk semantic search.
        top_k: Jumlah chunk yang diambil. Default: 5.
        min_similarity: Threshold minimum similarity (0.0–1.0).
            Chunk dengan similarity di bawah ini akan difilter.
            Default: 0.0 (ambil semua top_k tanpa filter).

    Returns:
        RetrievalResult berisi chunk, distances, dan metadata.

    Raises:
        ValueError: Jika document_id atau query kosong.
        RuntimeError: Jika embedding atau ChromaDB gagal.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")
    if not query or not query.strip():
        raise ValueError("query tidak boleh kosong.")
    if not (0.0 <= min_similarity <= 1.0):
        raise ValueError(
            f"min_similarity harus antara 0.0 dan 1.0, bukan {min_similarity}."
        )

    collection = get_collection_if_exists(document_id)
    if collection is None:
        logger.warning(
            "Collection untuk dokumen '%s' belum tersedia; retrieval dilewati.",
            document_id,
        )
        return RetrievalResult(
            query=query,
            top_k=top_k,
            found_count=0,
        )

    # Langkah 1: Embed query dengan model yang sama
    try:
        query_embedding = embed_text(query)
    except RuntimeError as exc:
        raise RuntimeError(f"Gagal meng-embed query: {exc}") from exc

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )
    except Exception as exc:
        raise RuntimeError(
            f"Gagal query ChromaDB untuk dokumen '{document_id}': {exc}"
        ) from exc

    # Ekstrak hasil (ChromaDB mengembalikan nested list)
    raw_chunks: list[str] = results.get("documents", [[]])[0] or []
    raw_distances: list[float] = results.get("distances", [[]])[0] or []
    raw_metadatas: list[dict] = results.get("metadatas", [[]])[0] or []

    # Langkah 3: Filter berdasarkan min_similarity
    filtered_chunks: list[str] = []
    filtered_distances: list[float] = []
    filtered_metadatas: list[dict] = []

    for chunk, distance, meta in zip(raw_chunks, raw_distances, raw_metadatas):
        similarity = max(0.0, 1.0 - distance)
        if similarity >= min_similarity:
            filtered_chunks.append(chunk)
            filtered_distances.append(distance)
            filtered_metadatas.append(meta)

    logger.info(
        "Retrieval untuk dokumen '%s': query='%s...', ditemukan %d/%d chunk "
        "(min_similarity=%.2f).",
        document_id,
        query[:50],
        len(filtered_chunks),
        top_k,
        min_similarity,
    )

    return RetrievalResult(
        query=query,
        chunks=filtered_chunks,
        distances=filtered_distances,
        metadatas=filtered_metadatas,
        top_k=top_k,
        found_count=len(filtered_chunks),
    )


def retrieve_all_chunks(document_id: str) -> list[str]:
    """Ambil semua chunk dari satu dokumen (tanpa semantic search).

    Digunakan untuk analisis menyeluruh dokumen — misalnya saat LLM
    perlu membaca seluruh dokumen untuk membuat ringkasan.

    Args:
        document_id: UUID dokumen.

    Returns:
        List semua chunk teks, urut berdasarkan chunk_index.

    Raises:
        ValueError: Jika document_id kosong.
        RuntimeError: Jika ChromaDB gagal.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")

    collection = get_collection_if_exists(document_id)
    if collection is None:
        logger.warning(
            "Collection untuk dokumen '%s' belum tersedia.",
            document_id,
        )
        return []

    try:
        count = collection.count()
        if count == 0:
            logger.warning(
                "Collection untuk dokumen '%s' kosong.", document_id
            )
            return []

        results = collection.get(
            include=["documents", "metadatas"],
        )
        chunks_with_index: list[tuple[int, str]] = []

        for doc, meta in zip(
            results.get("documents") or [],
            results.get("metadatas") or [],
        ):
            chunk_index = meta.get("chunk_index", 0) if meta else 0
            chunks_with_index.append((chunk_index, doc))

        # Urutkan berdasarkan chunk_index
        chunks_with_index.sort(key=lambda x: x[0])
        return [chunk for _, chunk in chunks_with_index]

    except Exception as exc:
        raise RuntimeError(
            f"Gagal mengambil semua chunk untuk dokumen '{document_id}': {exc}"
        ) from exc
