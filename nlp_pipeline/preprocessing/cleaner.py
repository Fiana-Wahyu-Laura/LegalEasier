"""
cleaner.py — LegalEasier NLP Pipeline
Normalisasi dan pembersihan teks hukum Indonesia.

Tugasnya (sesuai CLAUDE.md §9 Processing Order):
    Langkah 2 dari pipeline: Cleaning & normalization setelah OCR extraction.

Aturan:
- Tidak ada hardcoded secret/key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import re
import unicodedata


# ---------------------------------------------------------------------------
# Pola regex yang sering muncul di dokumen hukum Indonesia
# ---------------------------------------------------------------------------

# Baris kosong berlebih (lebih dari 2 baris)
_RE_EXCESS_NEWLINES = re.compile(r"\n{3,}")

# Spasi berlebih dalam satu baris
_RE_EXCESS_SPACES = re.compile(r"[ \t]{2,}")

# Karakter kontrol (kecuali newline dan tab)
_RE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Header/footer berulang yang umum di dokumen hukum (nomor halaman, "Halaman X dari Y")
_RE_PAGE_MARKER = re.compile(
    r"(?i)\bhalaman\s+\d+\s*(dari|of)\s+\d+\b|^\s*-\s*\d+\s*-\s*$",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------


def normalize_unicode(text: str) -> str:
    """Normalisasi Unicode ke NFC agar karakter gabungan konsisten.

    Args:
        text: Teks mentah dari OCR atau PDF extractor.

    Returns:
        Teks dengan representasi Unicode yang dinormalisasi.
    """
    return unicodedata.normalize("NFC", text)


def remove_control_characters(text: str) -> str:
    """Hapus karakter kontrol yang tidak terlihat (kecuali newline/tab).

    Args:
        text: Teks input.

    Returns:
        Teks tanpa karakter kontrol.
    """
    return _RE_CONTROL_CHARS.sub("", text)


def remove_page_markers(text: str) -> str:
    """Hapus marker halaman yang muncul berulang di dokumen hukum.

    Contoh: "Halaman 1 dari 10", "- 2 -"

    Args:
        text: Teks input.

    Returns:
        Teks tanpa marker halaman.
    """
    return _RE_PAGE_MARKER.sub("", text)


def normalize_whitespace(text: str) -> str:
    """Normalisasi spasi berlebih dan baris kosong.

    Args:
        text: Teks input.

    Returns:
        Teks dengan spasi yang rapi.
    """
    # Ganti spasi berlebih dalam satu baris
    text = _RE_EXCESS_SPACES.sub(" ", text)
    # Ganti 3+ newline berturut-turut dengan 2 newline
    text = _RE_EXCESS_NEWLINES.sub("\n\n", text)
    # Strip leading/trailing whitespace per baris
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def fix_hyphenation(text: str) -> str:
    """Perbaiki kata yang terputus di akhir baris (hyph-\nenation).

    Umum terjadi pada hasil OCR dokumen fisik.

    Args:
        text: Teks input.

    Returns:
        Teks dengan hyphenation yang diperbaiki.
    """
    # Gabungkan kata yang diputus oleh hyphen + newline
    return re.sub(r"-\n(\S)", r"\1", text)


def normalize_quotes(text: str) -> str:
    """Normalisasi tanda kutip tipografi ke tanda kutip standar ASCII.

    Args:
        text: Teks input.

    Returns:
        Teks dengan tanda kutip standar.
    """
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # ' '
    text = text.replace("\u201C", '"').replace("\u201D", '"')  # " "
    return text


def normalize_dashes(text: str) -> str:
    """Normalisasi em-dash dan en-dash ke tanda hubung standar.

    Args:
        text: Teks input.

    Returns:
        Teks dengan tanda hubung standar.
    """
    text = text.replace("\u2013", "-")  # en-dash
    text = text.replace("\u2014", "-")  # em-dash
    return text


def expand_common_abbreviations(text: str) -> str:
    """Ekspansi singkatan umum dalam dokumen hukum Indonesia.

    Args:
        text: Teks input.

    Returns:
        Teks dengan singkatan yang diekspansi untuk memudahkan NLP.
    """
    abbreviations: dict[str, str] = {
        r"\bPT\b": "Perseroan Terbatas",
        r"\bCV\b": "Commanditaire Vennootschap",
        r"\bUD\b": "Usaha Dagang",
        r"\bUU\b": "Undang-Undang",
        r"\bPP\b": "Peraturan Pemerintah",
        r"\bKUHPer\b": "Kitab Undang-Undang Hukum Perdata",
        r"\bKUHP\b": "Kitab Undang-Undang Hukum Pidana",
        r"\bRp\.?\b": "Rupiah",
        r"\bNo\.\s*": "Nomor ",
        r"\bTtd\.?\b": "Tanda Tangan",
    }
    for pattern, replacement in abbreviations.items():
        text = re.sub(pattern, replacement, text)
    return text


def clean_legal_text(
    raw_text: str,
    expand_abbreviations: bool = False,
) -> str:
    """Pipeline pembersihan teks hukum Indonesia — fungsi utama modul ini.

    Urutan pembersihan:
        1. Normalisasi Unicode (NFC)
        2. Hapus karakter kontrol
        3. Normalisasi tanda kutip & dash
        4. Perbaiki hyphenation OCR
        5. Hapus page markers
        6. (Opsional) Ekspansi singkatan
        7. Normalisasi whitespace

    Args:
        raw_text: Teks mentah dari OCR atau PDF extractor.
        expand_abbreviations: Jika True, ekspansi singkatan umum.
            Nonaktifkan jika teks akan dipakai verbatim ke LLM
            (untuk menjaga konteks asli dokumen).

    Returns:
        Teks yang sudah dibersihkan dan dinormalisasi.

    Raises:
        ValueError: Jika raw_text bukan string.
    """
    if not isinstance(raw_text, str):
        raise ValueError(
            f"raw_text harus bertipe str, bukan {type(raw_text).__name__}."
        )

    text = normalize_unicode(raw_text)
    text = remove_control_characters(text)
    text = normalize_quotes(text)
    text = normalize_dashes(text)
    text = fix_hyphenation(text)
    text = remove_page_markers(text)

    if expand_abbreviations:
        text = expand_common_abbreviations(text)

    text = normalize_whitespace(text)
    return text
