"""
splitter.py — LegalEasier NLP Pipeline
Sentence splitting untuk teks hukum Indonesia.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Langkah 3 dari pipeline: Tokenization & sentence splitting.

Strategi:
- NLTK sentence tokenizer (punkt) sebagai metode utama.
- Fallback sederhana berbasis regex jika NLTK gagal.
- Khusus untuk dokumen hukum: Pasal, Ayat, huruf (a), (b), (c)
  diperlakukan sebagai unit pemisah alami.

Aturan:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging
import re
from dataclasses import dataclass, field

import nltk

logger = logging.getLogger(__name__)

# Pastikan resource NLTK tersedia
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ---------------------------------------------------------------------------
# Pola struktur dokumen hukum Indonesia
# ---------------------------------------------------------------------------

# Penanda awal pasal/ayat: "Pasal 1", "(1)", "a.", "b)", dst.
_RE_LEGAL_BREAK = re.compile(
    r"(?<!\w)("
    r"Pasal\s+\d+[A-Za-z]?"       # Pasal 1, Pasal 10A
    r"|\(\d+\)"                    # (1), (2), (10)
    r"|[a-z]\.\s+"                 # a. b. c.
    r"|[a-z]\)\s+"                 # a) b) c)
    r"|\d+\.\s+"                   # 1. 2. 3.
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class SplitResult:
    """Hasil sentence splitting dari satu teks."""

    sentences: list[str] = field(default_factory=list)
    """Daftar kalimat hasil splitting."""

    sentence_count: int = 0
    """Jumlah total kalimat."""

    method_used: str = "nltk"
    """Metode yang digunakan: 'nltk' atau 'regex_fallback'."""


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------


def split_sentences_nltk(text: str) -> list[str]:
    """Split teks menjadi kalimat menggunakan NLTK punkt tokenizer.

    Untuk dokumen hukum Indonesia, tokenizer ini dipakai dengan bahasa
    default (English) karena tidak ada model bahasa Indonesia yang resmi
    — hasilnya tetap wajar untuk dokumen formal.

    Args:
        text: Teks yang sudah dibersihkan.

    Returns:
        List kalimat.

    Raises:
        RuntimeError: Jika NLTK punkt tokenizer tidak tersedia.
    """
    try:
        sentences = nltk.sent_tokenize(text)
        return [s.strip() for s in sentences if s.strip()]
    except LookupError as exc:
        raise RuntimeError(
            "NLTK punkt tokenizer tidak tersedia. "
            "Jalankan: python -c \"import nltk; nltk.download('punkt')\""
        ) from exc


def split_sentences_regex(text: str) -> list[str]:
    """Split teks menjadi kalimat menggunakan regex sebagai fallback.

    Dipakai jika NLTK tidak tersedia atau hasilnya tidak memuaskan.

    Args:
        text: Teks yang sudah dibersihkan.

    Returns:
        List kalimat.
    """
    # Split pada titik/tanda tanya/seru yang diikuti spasi + huruf kapital
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚ])", text)
    return [s.strip() for s in raw_sentences if s.strip()]


def split_by_legal_structure(text: str) -> list[str]:
    """Split teks berdasarkan struktur dokumen hukum Indonesia.

    Gunakan untuk dokumen yang sangat terstruktur (kontrak, peraturan)
    di mana Pasal/Ayat/huruf adalah unit semantik utama.

    Setiap penanda (Pasal, (1), a., dll.) akan memulai segmen baru.

    Args:
        text: Teks yang sudah dibersihkan.

    Returns:
        List segmen berdasarkan struktur hukum.
    """
    # Masukkan marker pemisah sebelum setiap penanda struktur
    marked = _RE_LEGAL_BREAK.sub(r"\n\1", text)
    segments = marked.split("\n")
    return [s.strip() for s in segments if s.strip()]


def split_text(
    text: str,
    method: str = "nltk",
    min_sentence_length: int = 10,
) -> SplitResult:
    """Split teks menjadi kalimat — fungsi utama modul ini.

    Ini adalah langkah 3 pipeline NLP (CLAUDE.md §9).

    Args:
        text: Teks yang sudah dibersihkan (output cleaner.clean_legal_text).
        method: Metode splitting:
            - 'nltk'         → NLTK punkt tokenizer (default)
            - 'legal'        → Berdasarkan struktur Pasal/Ayat/huruf
            - 'regex'        → Regex sederhana (fallback)
        min_sentence_length: Panjang minimum kalimat dalam karakter.
            Kalimat lebih pendek dari ini akan dibuang.

    Returns:
        SplitResult berisi daftar kalimat dan metadata.

    Raises:
        ValueError: Jika text bukan string atau kosong.
        ValueError: Jika method tidak valid.
    """
    if not isinstance(text, str):
        raise ValueError(
            f"text harus bertipe str, bukan {type(text).__name__}."
        )
    if not text.strip():
        raise ValueError("text tidak boleh kosong.")

    valid_methods = {"nltk", "legal", "regex"}
    if method not in valid_methods:
        raise ValueError(
            f"method '{method}' tidak valid. Pilih dari: {valid_methods}."
        )

    method_used = method
    sentences: list[str] = []

    if method == "nltk":
        try:
            sentences = split_sentences_nltk(text)
        except RuntimeError:
            logger.warning(
                "NLTK tidak tersedia, fallback ke regex splitting."
            )
            sentences = split_sentences_regex(text)
            method_used = "regex_fallback"

    elif method == "legal":
        sentences = split_by_legal_structure(text)

    elif method == "regex":
        sentences = split_sentences_regex(text)

    # Filter kalimat terlalu pendek
    sentences = [s for s in sentences if len(s) >= min_sentence_length]

    return SplitResult(
        sentences=sentences,
        sentence_count=len(sentences),
        method_used=method_used,
    )
