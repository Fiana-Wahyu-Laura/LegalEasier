"""
tests/test_rag_pipeline.py — LegalEasier NLP Pipeline
Unit tests untuk modul RAG Sprint 2:
    - chunker.chunk_text
    - chunker.chunk_sentences
    - embedder.embed_text, embed_chunks, compute_similarity
    - vector_store (dengan ChromaDB in-memory mock)
    - retriever (dengan mock vector_store dan embedder)

Jalankan: pytest tests/test_rag_pipeline.py -v

CATATAN:
- Embedding tests menggunakan sentence-transformers secara langsung
  (akan download model ~80MB saat pertama kali dijalankan).
- ChromaDB tests menggunakan in-memory client (tidak menyentuh disk).
"""

from unittest.mock import MagicMock, patch

import pytest

from rag.chunker import ChunkResult, chunk_sentences, chunk_text
from rag.embedder import compute_similarity, embed_chunks, embed_text
from rag.retriever import RetrievalResult


# ---------------------------------------------------------------------------
# Tests: chunker.py
# ---------------------------------------------------------------------------


class TestChunkText:
    VALID_TEXT = (
        "Pasal 1 mengatur tentang ketentuan umum perjanjian sewa menyewa ini. "
        "Pihak pertama adalah pemilik properti yang terletak di Jakarta. "
        "Pihak kedua adalah penyewa yang setuju untuk membayar uang sewa. "
        "Pembayaran dilakukan setiap tanggal 5 di awal bulan. "
        "Keterlambatan pembayaran dikenakan denda sebesar 2% per hari. "
        "Pasal 2 mengatur tentang kewajiban pihak kedua sebagai penyewa properti. "
        "Penyewa wajib menjaga kebersihan dan keamanan properti yang disewa. "
        "Penyewa tidak diperbolehkan melakukan renovasi tanpa izin tertulis dari pemilik. "
    ) * 5  # Buat teks cukup panjang untuk diuji chunk

    def test_returns_chunk_result(self) -> None:
        result = chunk_text(self.VALID_TEXT)
        assert isinstance(result, ChunkResult)

    def test_chunk_count_positive(self) -> None:
        result = chunk_text(self.VALID_TEXT)
        assert result.chunk_count > 0

    def test_chunks_not_exceed_size(self) -> None:
        chunk_size = 200
        result = chunk_text(self.VALID_TEXT, chunk_size=chunk_size)
        # Setiap chunk tidak melebihi chunk_size + sedikit toleransi
        # (LangChain bisa sedikit melebihi karena pemisah)
        for chunk in result.chunks:
            assert len(chunk) <= chunk_size + 50, (
                f"Chunk terlalu panjang: {len(chunk)} > {chunk_size + 50}"
            )

    def test_custom_chunk_size(self) -> None:
        result_small = chunk_text(self.VALID_TEXT, chunk_size=100, chunk_overlap=20)
        result_large = chunk_text(self.VALID_TEXT, chunk_size=1000, chunk_overlap=50)
        # Chunk lebih kecil → lebih banyak chunk
        assert result_small.chunk_count >= result_large.chunk_count

    def test_metadata_preserved(self) -> None:
        result = chunk_text(self.VALID_TEXT, chunk_size=300, chunk_overlap=30)
        assert result.chunk_size == 300
        assert result.chunk_overlap == 30

    def test_all_chunks_are_strings(self) -> None:
        result = chunk_text(self.VALID_TEXT)
        assert all(isinstance(c, str) for c in result.chunks)

    def test_no_empty_chunks(self) -> None:
        result = chunk_text(self.VALID_TEXT)
        assert all(c.strip() for c in result.chunks)

    def test_raises_on_empty_text(self) -> None:
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            chunk_text("")

    def test_raises_on_non_string(self) -> None:
        with pytest.raises(ValueError, match="harus bertipe str"):
            chunk_text(None)  # type: ignore[arg-type]

    def test_raises_when_size_lte_overlap(self) -> None:
        with pytest.raises(ValueError, match="harus lebih besar"):
            chunk_text(self.VALID_TEXT, chunk_size=50, chunk_overlap=50)


class TestChunkSentences:
    SENTENCES = [
        "Pihak pertama adalah pemilik properti yang terletak di Jakarta.",
        "Pihak kedua adalah penyewa yang setuju untuk membayar uang sewa.",
        "Pembayaran dilakukan setiap tanggal 5 di awal bulan.",
        "Keterlambatan pembayaran dikenakan denda sebesar 2% per hari.",
        "Penyewa wajib menjaga kebersihan dan keamanan properti yang disewa.",
    ] * 10

    def test_returns_chunk_result(self) -> None:
        result = chunk_sentences(self.SENTENCES)
        assert isinstance(result, ChunkResult)

    def test_produces_chunks(self) -> None:
        result = chunk_sentences(self.SENTENCES)
        assert result.chunk_count > 0

    def test_raises_on_empty_sentences(self) -> None:
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            chunk_sentences([])


# ---------------------------------------------------------------------------
# Tests: embedder.py
# ---------------------------------------------------------------------------


class TestEmbedText:
    """Tests embed_text — memerlukan model sentence-transformers."""

    def test_returns_list_of_floats(self) -> None:
        result = embed_text("Perjanjian sewa menyewa ini dibuat oleh kedua pihak.")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_correct_dimension(self) -> None:
        from rag.embedder import EMBEDDING_DIMENSION
        result = embed_text("Teks untuk embedding.")
        assert len(result) == EMBEDDING_DIMENSION

    def test_raises_on_empty_text(self) -> None:
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            embed_text("")

    def test_raises_on_non_string(self) -> None:
        with pytest.raises(ValueError, match="harus bertipe str"):
            embed_text(123)  # type: ignore[arg-type]

    def test_normalized_embedding_length_approx_one(self) -> None:
        """Embedding yang sudah dinormalisasi harus memiliki L2 norm ≈ 1.0."""
        import math
        result = embed_text("Kontrak ini mengikat kedua belah pihak.")
        norm = math.sqrt(sum(v * v for v in result))
        assert abs(norm - 1.0) < 0.01, f"Norm tidak mendekati 1.0: {norm}"


class TestEmbedChunks:
    CHUNKS = [
        "Pasal 1 mengatur tentang ketentuan umum perjanjian.",
        "Pasal 2 mengatur tentang kewajiban pihak penyewa.",
        "Pasal 3 mengatur tentang sanksi dan denda keterlambatan.",
    ]

    def test_returns_list_of_embeddings(self) -> None:
        result = embed_chunks(self.CHUNKS)
        assert isinstance(result, list)
        assert len(result) == len(self.CHUNKS)

    def test_each_embedding_is_list_of_floats(self) -> None:
        result = embed_chunks(self.CHUNKS)
        for emb in result:
            assert isinstance(emb, list)
            assert all(isinstance(v, float) for v in emb)

    def test_raises_on_empty_chunks(self) -> None:
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            embed_chunks([])

    def test_raises_on_non_string_item(self) -> None:
        with pytest.raises(ValueError, match="harus bertipe str"):
            embed_chunks(["valid text", 123])  # type: ignore[list-item]


class TestComputeSimilarity:
    def test_identical_embeddings_similarity_one(self) -> None:
        emb = embed_text("Perjanjian sewa menyewa.")
        similarity = compute_similarity(emb, emb)
        assert abs(similarity - 1.0) < 0.01

    def test_similar_texts_higher_similarity(self) -> None:
        emb_a = embed_text("Perjanjian sewa properti di Jakarta.")
        emb_b = embed_text("Kontrak sewa gedung di Jakarta.")
        emb_c = embed_text("Resep masakan ayam goreng spesial.")

        sim_related = compute_similarity(emb_a, emb_b)
        sim_unrelated = compute_similarity(emb_a, emb_c)
        assert sim_related > sim_unrelated

    def test_raises_on_mismatched_dimensions(self) -> None:
        emb_a = [0.1, 0.2, 0.3]
        emb_b = [0.1, 0.2]
        with pytest.raises(ValueError, match="Panjang embedding tidak sama"):
            compute_similarity(emb_a, emb_b)


# ---------------------------------------------------------------------------
# Tests: vector_store.py (menggunakan in-memory ChromaDB)
# ---------------------------------------------------------------------------


class TestVectorStore:
    """Tests vector_store menggunakan ChromaDB in-memory agar tidak menyentuh disk."""

    @pytest.fixture(autouse=True)
    def patch_chroma_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ganti PersistentClient dengan EphemeralClient (in-memory) untuk testing."""
        import chromadb
        from rag import vector_store

        # Reset singleton
        vector_store._chroma_client = None

        # Mock get_chroma_client agar mengembalikan in-memory client
        in_memory_client = chromadb.EphemeralClient()
        monkeypatch.setattr(vector_store, "_chroma_client", in_memory_client)

    def test_store_and_retrieve_chunks(self) -> None:
        from rag.vector_store import get_collection_info, store_chunks

        doc_id = "test-doc-sprint2-001"
        chunks = ["Klausul pertama perjanjian.", "Klausul kedua perjanjian."]
        embeddings = embed_chunks(chunks)

        stored = store_chunks(doc_id, chunks, embeddings)
        assert stored == 2

        info = get_collection_info(doc_id)
        assert info["exists"] is True
        assert info["chunk_count"] == 2

    def test_delete_collection(self) -> None:
        from rag.vector_store import delete_document_collection, get_collection_info, store_chunks

        doc_id = "test-doc-sprint2-002"
        chunks = ["Klausul perjanjian sewa."]
        embeddings = embed_chunks(chunks)

        store_chunks(doc_id, chunks, embeddings)
        deleted = delete_document_collection(doc_id)
        assert deleted is True

        info = get_collection_info(doc_id)
        assert info["exists"] is False

    def test_delete_nonexistent_collection(self) -> None:
        from rag.vector_store import delete_document_collection
        result = delete_document_collection("nonexistent-doc-id-999")
        assert result is False

    def test_store_raises_on_mismatched_lengths(self) -> None:
        from rag.vector_store import store_chunks
        with pytest.raises(ValueError, match="harus sama"):
            store_chunks(
                "test-doc-mismatch",
                chunks=["Chunk satu.", "Chunk dua."],
                embeddings=[[0.1] * 384],  # Hanya 1 embedding untuk 2 chunks
            )

    def test_store_raises_on_empty_document_id(self) -> None:
        from rag.vector_store import store_chunks
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            store_chunks("", chunks=["Teks"], embeddings=[[0.1] * 384])


# ---------------------------------------------------------------------------
# Tests: retriever.py (dengan mock vector_store dan embedder)
# ---------------------------------------------------------------------------


class TestRetriever:
    """Tests retriever menggunakan mock agar tidak bergantung pada ChromaDB dan model."""

    @pytest.fixture
    def mock_collection(self) -> MagicMock:
        """Buat mock ChromaDB collection."""
        mock = MagicMock()
        mock.query.return_value = {
            "documents": [["Klausul satu.", "Klausul dua.", "Klausul tiga."]],
            "distances": [[0.1, 0.3, 0.6]],
            "metadatas": [
                [
                    {"document_id": "test-doc", "chunk_index": 0},
                    {"document_id": "test-doc", "chunk_index": 1},
                    {"document_id": "test-doc", "chunk_index": 2},
                ]
            ],
        }
        return mock

    def test_retrieve_returns_result(self, mock_collection: MagicMock) -> None:
        with (
            patch("rag.retriever.get_collection_if_exists", return_value=mock_collection),
            patch("rag.retriever.embed_text", return_value=[0.1] * 384),
        ):
            from rag.retriever import retrieve_relevant_chunks
            result = retrieve_relevant_chunks("test-doc", "pembayaran denda")
            assert isinstance(result, RetrievalResult)
            assert result.found_count == 3

    def test_returns_empty_when_collection_missing(self) -> None:
        with (
            patch("rag.retriever.get_collection_if_exists", return_value=None),
            patch("rag.retriever.embed_text") as mock_embed,
        ):
            from rag.retriever import retrieve_relevant_chunks
            result = retrieve_relevant_chunks("test-doc", "pembayaran denda")
            assert result.found_count == 0
            assert result.chunks == []
            mock_embed.assert_not_called()

    def test_retrieve_filters_by_min_similarity(self, mock_collection: MagicMock) -> None:
        with (
            patch("rag.retriever.get_collection_if_exists", return_value=mock_collection),
            patch("rag.retriever.embed_text", return_value=[0.1] * 384),
        ):
            from rag.retriever import retrieve_relevant_chunks
            # distance=0.6 → similarity=0.4 → di bawah threshold 0.5
            result = retrieve_relevant_chunks("test-doc", "pembayaran", min_similarity=0.5)
            assert result.found_count == 2  # Hanya 2 yang lolos (distance 0.1 dan 0.3)

    def test_context_text_joins_chunks(self, mock_collection: MagicMock) -> None:
        with (
            patch("rag.retriever.get_collection_if_exists", return_value=mock_collection),
            patch("rag.retriever.embed_text", return_value=[0.1] * 384),
        ):
            from rag.retriever import retrieve_relevant_chunks
            result = retrieve_relevant_chunks("test-doc", "klausul")
            assert "---" in result.context_text  # Pemisah antar chunk

    def test_raises_on_empty_query(self) -> None:
        from rag.retriever import retrieve_relevant_chunks
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            retrieve_relevant_chunks("test-doc", "")

    def test_raises_on_empty_document_id(self) -> None:
        from rag.retriever import retrieve_relevant_chunks
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            retrieve_relevant_chunks("", "query")

    def test_raises_on_invalid_min_similarity(self) -> None:
        from rag.retriever import retrieve_relevant_chunks
        with pytest.raises(ValueError, match="antara 0.0 dan 1.0"):
            retrieve_relevant_chunks("test-doc", "query", min_similarity=1.5)

    def test_similarities_property(self, mock_collection: MagicMock) -> None:
        """Similarity harus = 1 - distance, min 0.0."""
        with (
            patch("rag.retriever.get_collection_if_exists", return_value=mock_collection),
            patch("rag.retriever.embed_text", return_value=[0.1] * 384),
        ):
            from rag.retriever import retrieve_relevant_chunks
            result = retrieve_relevant_chunks("test-doc", "klausul")
            expected_sims = [0.9, 0.7, 0.4]
            for actual, expected in zip(result.similarities, expected_sims):
                assert abs(actual - expected) < 0.01
