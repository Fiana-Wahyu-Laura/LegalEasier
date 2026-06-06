"""
ocr/pdf_extractor.py — LegalEasier NLP Pipeline
Ekstraksi teks dari file PDF menggunakan PyMuPDF (fitz).

Strategi:
1. Coba ekstrak teks digital langsung (lebih cepat, akurasi tinggi).
2. Jika teks yang diperoleh terlalu pendek/kosong (kemungkinan PDF scan),
   kembalikan hasil kosong agar pipeline bisa fallback ke Tesseract OCR.

Rules (CLAUDE.md §9 - OCR):
- Try PyMuPDF first (faster, for digital PDFs).
- Fall back to Tesseract only if PyMuPDF returns empty/garbled text.
- Set flag ocr_used=True in result if Tesseract was used.
"""

import logging
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PDFExtractionResult:
    """Hasil ekstraksi teks dari PDF."""

    full_text: str
    page_count: int
    ocr_used: bool = False
    pages: list[str] = field(default_factory=list)
    error: str | None = None


def _is_text_valid(text: str) -> bool:
    """
    Periksa apakah teks hasil ekstraksi cukup valid.

    Teks dianggap tidak valid (kemungkinan PDF scan) jika:
    - Lebih pendek dari threshold minimum (settings.min_text_length)
    - Terlalu banyak karakter non-printable (garbled)
    """
    if len(text.strip()) < settings.min_text_length:
        return False

    # Hitung rasio karakter yang dapat dibaca
    printable_chars = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    if len(text) > 0 and (printable_chars / len(text)) < 0.85:
        return False

    return True


def extract_text_from_pdf(file_bytes: bytes) -> PDFExtractionResult:
    """
    Ekstrak teks dari file PDF menggunakan PyMuPDF (fitz).

    Args:
        file_bytes: Konten file PDF dalam format bytes.

    Returns:
        PDFExtractionResult berisi teks gabungan semua halaman,
        jumlah halaman, dan flag apakah OCR diperlukan.

    Raises:
        ValueError: Jika file_bytes bukan PDF yang valid.
        RuntimeError: Jika PyMuPDF gagal membuka dokumen.
    """
    try:
        doc: fitz.Document = fitz.open(stream=file_bytes, filetype="pdf")
    except fitz.FileDataError as exc:
        logger.error("PyMuPDF gagal membuka PDF: %s", exc)
        raise ValueError(f"File bukan PDF yang valid: {exc}") from exc
    except Exception as exc:
        logger.error("Error tidak terduga saat membuka PDF: %s", exc)
        raise RuntimeError(f"Gagal membuka PDF: {exc}") from exc

    page_count = doc.page_count
    pages: list[str] = []

    try:
        for page_num in range(page_count):
            page: fitz.Page = doc[page_num]
            page_text: str = page.get_text("text")  # type: ignore[arg-type]
            pages.append(page_text)
            logger.debug("Halaman %d/%d: %d karakter", page_num + 1, page_count, len(page_text))
    except Exception as exc:
        logger.error("Gagal membaca halaman PDF: %s", exc)
        raise RuntimeError(f"Gagal membaca halaman PDF: {exc}") from exc
    finally:
        doc.close()

    full_text: str = "\n\n".join(pages).strip()

    if not _is_text_valid(full_text):
        logger.info(
            "Teks PDF tidak valid (panjang=%d). Kemungkinan PDF scan — "
            "pipeline harus fallback ke Tesseract.",
            len(full_text),
        )
        return PDFExtractionResult(
            full_text="",
            page_count=page_count,
            ocr_used=False,   # Akan diset True oleh caller setelah Tesseract berjalan
            pages=[],
            error="PDF tampaknya berupa scan — teks digital tidak tersedia.",
        )

    logger.info(
        "Ekstraksi PDF berhasil: %d halaman, %d karakter total.",
        page_count,
        len(full_text),
    )
    return PDFExtractionResult(
        full_text=full_text,
        page_count=page_count,
        ocr_used=False,
        pages=pages,
    )
