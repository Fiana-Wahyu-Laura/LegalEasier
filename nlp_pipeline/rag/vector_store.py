"""
vector_store.py — LegalEasier NLP Pipeline
Operasi ChromaDB: store, query, delete vector embeddings.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Langkah 6 dari pipeline: Store vectors in ChromaDB.

Rules (CLAUDE.md §9 ChromaDB):
- Satu collection per dokumen, dinamai: "doc_{document_uuid}"
- Hapus collection saat dokumen dihapus
- Jangan share collections antar dokumen

Aturan kode:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging
from typing import Optional

import chromadb
from chromadb import Collection
from chromadb.config import Settings as ChromaSettings

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ChromaDB client — singleton
# ---------------------------------------------------------------------------

_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Buat atau kembalikan ChromaDB PersistentClient singleton.

    Data disimpan ke direktori yang dikonfigurasi di .env (chroma_persist_dir).

    Returns:
        chromadb.PersistentClient yang sudah dikonfigurasi.

    Raises:
        RuntimeError: Jika ChromaDB gagal diinisialisasi.
    """
    global _chroma_client
    if _chroma_client is None:
        try:
            _chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(
                "ChromaDB PersistentClient diinisialisasi di '%s'.",
                settings.chroma_persist_dir,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Gagal menginisialisasi ChromaDB di '{settings.chroma_persist_dir}': {exc}"
            ) from exc
    return _chroma_client


def _collection_name(document_id: str) -> str:
    """Generate nama collection ChromaDB untuk satu dokumen.

    Format: "doc_{document_uuid}" (CLAUDE.md §9).

    Args:
        document_id: UUID dokumen dari backend.

    Returns:
        Nama collection string.
    """
    # ChromaDB mengizinkan hanya karakter alfanumerik, underscore, dan hyphen
    sanitized = document_id.replace("-", "_")
    return f"doc_{sanitized}"


def get_collection_if_exists(document_id: str) -> Optional[Collection]:
    """Ambil collection jika sudah ada (tanpa auto-create).

    Args:
        document_id: UUID dokumen dari backend.

    Returns:
        chromadb.Collection jika ada, atau None jika belum dibuat.

    Raises:
        ValueError: Jika document_id kosong.
        RuntimeError: Jika ChromaDB gagal.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")

    client = get_chroma_client()
    name = _collection_name(document_id)

    try:
        collections = client.list_collections()
    except Exception as exc:
        raise RuntimeError(
            f"Gagal mengambil daftar collection ChromaDB: {exc}"
        ) from exc

    for item in collections:
        item_name = None
        if isinstance(item, Collection):
            item_name = item.name
        elif isinstance(item, dict):
            item_name = item.get("name")
        elif isinstance(item, str):
            item_name = item

        if item_name == name:
            if isinstance(item, Collection):
                return item
            try:
                return client.get_collection(name)
            except Exception as exc:
                raise RuntimeError(
                    f"Gagal mengambil collection '{name}': {exc}"
                ) from exc

    return None


# ---------------------------------------------------------------------------
# Operasi collection
# ---------------------------------------------------------------------------


def get_or_create_collection(document_id: str) -> Collection:
    """Dapatkan atau buat collection ChromaDB untuk dokumen ini.

    Args:
        document_id: UUID dokumen dari backend.

    Returns:
        chromadb.Collection yang siap dipakai.

    Raises:
        ValueError: Jika document_id kosong.
        RuntimeError: Jika ChromaDB gagal.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")

    client = get_chroma_client()
    name = _collection_name(document_id)

    try:
        collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},  # Gunakan cosine similarity
        )
        logger.debug("Collection '%s' siap digunakan.", name)
        return collection
    except Exception as exc:
        raise RuntimeError(
            f"Gagal membuat/mengambil collection '{name}': {exc}"
        ) from exc


def store_chunks(
    document_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata_list: Optional[list[dict]] = None,
) -> int:
    """Simpan chunk teks beserta embeddingnya ke ChromaDB.

    Ini adalah langkah 6 pipeline NLP (CLAUDE.md §9).

    ID tiap chunk dibuat otomatis: "{document_id}_chunk_{index}".
    Jika collection sudah ada dengan isi lama, akan di-upsert (overwrite).

    Args:
        document_id: UUID dokumen dari backend.
        chunks: List teks chunk (output dari chunker).
        embeddings: List embedding vektor (output dari embedder).
            Harus sama panjangnya dengan chunks.
        metadata_list: Opsional — list dict metadata per chunk.
            Contoh: [{"page": 1, "pasal": "Pasal 1"}, ...]

    Returns:
        Jumlah chunk yang berhasil disimpan.

    Raises:
        ValueError: Jika panjang chunks dan embeddings tidak sama.
        ValueError: Jika document_id kosong atau chunks kosong.
        RuntimeError: Jika ChromaDB gagal.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")
    if not chunks:
        raise ValueError("chunks tidak boleh kosong.")
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Jumlah chunks ({len(chunks)}) harus sama dengan "
            f"jumlah embeddings ({len(embeddings)})."
        )

    collection = get_or_create_collection(document_id)

    # Buat ID unik per chunk
    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

    # Siapkan metadata — wajib ada document_id di setiap chunk
    if metadata_list is None:
        metadata_list = [{}] * len(chunks)

    enriched_metadata = [
        {**meta, "document_id": document_id, "chunk_index": i}
        for i, meta in enumerate(metadata_list)
    ]

    try:
        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=enriched_metadata,
        )
        logger.info(
            "Berhasil menyimpan %d chunk untuk dokumen '%s' ke ChromaDB.",
            len(chunks),
            document_id,
        )
        return len(chunks)
    except Exception as exc:
        raise RuntimeError(
            f"Gagal menyimpan chunk ke ChromaDB untuk dokumen '{document_id}': {exc}"
        ) from exc


def delete_document_collection(document_id: str) -> bool:
    """Hapus seluruh collection ChromaDB milik satu dokumen.

    Dipanggil saat dokumen dihapus dari backend (CLAUDE.md §9).

    Args:
        document_id: UUID dokumen yang akan dihapus.

    Returns:
        True jika berhasil dihapus, False jika collection tidak ditemukan.

    Raises:
        ValueError: Jika document_id kosong.
        RuntimeError: Jika ChromaDB gagal.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")

    client = get_chroma_client()
    name = _collection_name(document_id)

    try:
        client.delete_collection(name)
        logger.info(
            "Collection '%s' berhasil dihapus dari ChromaDB.", name
        )
        return True
    except ValueError:
        # ChromaDB throws ValueError jika collection tidak ditemukan
        logger.warning(
            "Collection '%s' tidak ditemukan saat dihapus — mungkin sudah terhapus.",
            name,
        )
        return False
    except Exception as exc:
        raise RuntimeError(
            f"Gagal menghapus collection '{name}': {exc}"
        ) from exc


def get_collection_info(document_id: str) -> dict:
    """Dapatkan informasi collection untuk satu dokumen.

    Args:
        document_id: UUID dokumen.

    Returns:
        Dict dengan key: 'collection_name', 'chunk_count', 'exists'.

    Raises:
        ValueError: Jika document_id kosong.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")

    name = _collection_name(document_id)

    try:
        collection = get_collection_if_exists(document_id)
        if collection is None:
            return {
                "collection_name": name,
                "chunk_count": 0,
                "exists": False,
            }

        return {
            "collection_name": name,
            "chunk_count": collection.count(),
            "exists": True,
        }
    except Exception:
        return {
            "collection_name": name,
            "chunk_count": 0,
            "exists": False,
        }
