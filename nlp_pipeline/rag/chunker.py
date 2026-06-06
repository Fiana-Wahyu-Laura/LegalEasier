"""
chunker.py — LegalEasier NLP Pipeline
Chunking teks menggunakan LangChain RecursiveCharacterTextSplitter.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Langkah 4 dari pipeline: Chunking 512 tokens, overlap 50.

Strategi chunking:
- Gunakan RecursiveCharacterTextSplitter dari LangChain.
- Pemisah hierarkis: paragraf → kalimat → kata
  untuk menjaga konteks semantik tetap utuh.
- Ukuran chunk: 512 karakter (bukan token — sentence-transformers
  menghitung per karakter, bukan subword token).
- Overlap: 50 karakter untuk menjaga konteks antar chunk.

Aturan:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Konstanta chunking (CLAUDE.md §9)
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 512     # karakter per chunk
DEFAULT_CHUNK_OVERLAP = 50   # karakter overlap antar chunk

# Pemisah hierarkis — dari yang paling diutamakan ke paling kasar
# Disesuaikan untuk dokumen hukum Indonesia
_LEGAL_SEPARATORS = [
    "\n\n",       # Paragraf terpisah (paling diutamakan)
    "\nPasal ",   # Penanda pasal baru
    "\n(",        # Penanda ayat baru: (1), (2), dst.
    "\n",         # Baris baru
    ". ",         # Akhir kalimat
    " ",          # Kata
    "",           # Karakter (fallback terakhir)
]


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class ChunkResult:
    """Hasil chunking dari satu dokumen."""

    chunks: list[str] = field(default_factory=list)
    """Daftar teks chunk."""

    chunk_count: int = 0
    """Jumlah chunk yang dihasilkan."""

    chunk_size: int = DEFAULT_CHUNK_SIZE
    """Ukuran chunk yang digunakan (dalam karakter)."""

    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    """Overlap yang digunakan (dalam karakter)."""


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> ChunkResult:
    """Split teks menjadi chunk menggunakan LangChain RecursiveCharacterTextSplitter.

    Ini adalah langkah 4 pipeline NLP (CLAUDE.md §9).

    LangChain RecursiveCharacterTextSplitter membagi teks secara hierarkis:
    coba pisahkan di paragraf dulu, lalu kalimat, lalu kata, terakhir karakter.
    Ini menjaga konteks semantik teks hukum lebih baik dari splitter naif.

    Args:
        text: Teks yang sudah dibersihkan dan di-split (cleaned text).
        chunk_size: Ukuran maksimum satu chunk dalam karakter.
            Default: 512 (CLAUDE.md §9).
        chunk_overlap: Jumlah karakter yang overlap antar chunk berturutan.
            Default: 50 (CLAUDE.md §9).

    Returns:
        ChunkResult berisi daftar chunk dan metadata.

    Raises:
        ValueError: Jika text bukan string atau kosong.
        ValueError: Jika chunk_size <= chunk_overlap.
    """
    if not isinstance(text, str):
        raise ValueError(
            f"text harus bertipe str, bukan {type(text).__name__}."
        )
    if not text.strip():
        raise ValueError("text tidak boleh kosong.")
    if chunk_size <= chunk_overlap:
        raise ValueError(
            f"chunk_size ({chunk_size}) harus lebih besar dari "
            f"chunk_overlap ({chunk_overlap})."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_LEGAL_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = splitter.split_text(text)

    # Filter chunk kosong atau terlalu pendek (< 10 karakter)
    chunks = [c.strip() for c in chunks if c.strip() and len(c.strip()) >= 10]

    logger.info(
        "Chunking selesai: %d chunk dari teks %d karakter "
        "(chunk_size=%d, overlap=%d).",
        len(chunks),
        len(text),
        chunk_size,
        chunk_overlap,
    )

    return ChunkResult(
        chunks=chunks,
        chunk_count=len(chunks),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def chunk_sentences(
    sentences: list[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> ChunkResult:
    """Chunk dari list kalimat (output dari splitter.split_text).

    Gabungkan kalimat-kalimat menjadi satu teks, lalu chunk.
    Digunakan ketika sentence splitting sudah dilakukan sebelumnya.

    Args:
        sentences: List kalimat dari splitter.
        chunk_size: Ukuran maksimum satu chunk dalam karakter.
        chunk_overlap: Overlap antar chunk dalam karakter.

    Returns:
        ChunkResult berisi daftar chunk dan metadata.

    Raises:
        ValueError: Jika sentences kosong.
    """
    if not sentences:
        raise ValueError("sentences tidak boleh kosong.")

    combined_text = "\n".join(sentences)
    return chunk_text(combined_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
