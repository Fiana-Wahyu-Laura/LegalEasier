"""
ocr/image_ocr.py — LegalEasier NLP Pipeline
Ekstraksi teks dari gambar (JPG, PNG, TIFF) atau PDF scan menggunakan Tesseract OCR.

Digunakan sebagai fallback ketika PyMuPDF tidak menghasilkan teks yang valid.
Mendukung input berupa:
- File gambar langsung (JPG/PNG/TIFF)
- PDF scan (setiap halaman dikonversi ke gambar terlebih dahulu via PyMuPDF)

Rules (CLAUDE.md §9 - OCR):
- Set flag ocr_used=True jika Tesseract digunakan.
- Tesseract path dikonfigurasi via settings.tesseract_cmd.
- Bahasa OCR: Indonesian + English (ind+eng).
"""

import logging
from dataclasses import dataclass, field
from io import BytesIO

import fitz  # PyMuPDF — untuk rasterisasi PDF scan ke gambar
import pytesseract
from PIL import Image

from core.config import settings

logger = logging.getLogger(__name__)

# Konfigurasi path Tesseract dari settings (CLAUDE.md §11: no hardcoded paths)
pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


@dataclass
class OCRResult:
    """Hasil ekstraksi teks via Tesseract OCR."""

    full_text: str
    page_count: int
    ocr_used: bool = True   # Selalu True karena modul ini menggunakan Tesseract
    pages: list[str] = field(default_factory=list)
    error: str | None = None


def _image_to_text(image: Image.Image) -> str:
    """
    Jalankan Tesseract OCR pada satu objek PIL Image.

    Args:
        image: Objek PIL Image (RGB atau grayscale).

    Returns:
        String teks hasil OCR. Kosong jika OCR gagal.
    """
    try:
        # --oem 3  → LSTM engine (paling akurat)
        # --psm 6  → Asumsikan satu blok teks seragam
        custom_config = f"--oem 3 --psm 6 -l {settings.tesseract_lang}"
        text: str = pytesseract.image_to_string(image, config=custom_config)
        return text.strip()
    except pytesseract.TesseractNotFoundError as exc:
        logger.error(
            "Tesseract tidak ditemukan di '%s'. Pastikan sudah terinstall dan "
            "path sudah benar di .env (TESSERACT_CMD). Error: %s",
            settings.tesseract_cmd,
            exc,
        )
        raise RuntimeError(
            f"Tesseract tidak ditemukan. Cek TESSERACT_CMD di .env: {exc}"
        ) from exc
    except Exception as exc:
        logger.warning("Tesseract gagal memproses halaman: %s", exc)
        return ""


def extract_text_from_image(file_bytes: bytes, file_type: str = "jpg") -> OCRResult:
    """
    Ekstrak teks dari file gambar (JPG/PNG/TIFF) menggunakan Tesseract OCR.

    Args:
        file_bytes: Konten file gambar dalam bytes.
        file_type: Tipe file — "jpg", "jpeg", "png", "tiff", atau "tif".

    Returns:
        OCRResult dengan teks hasil OCR dan ocr_used=True.

    Raises:
        ValueError: Jika file_bytes bukan gambar yang valid.
        RuntimeError: Jika Tesseract tidak ditemukan / gagal dijalankan.
    """
    logger.info("Memulai OCR gambar (tipe: %s).", file_type)

    try:
        image = Image.open(BytesIO(file_bytes)).convert("RGB")
    except Exception as exc:
        logger.error("Gagal membuka file gambar: %s", exc)
        raise ValueError(f"File bukan gambar yang valid: {exc}") from exc

    page_text = _image_to_text(image)
    full_text = page_text.strip()

    logger.info("OCR gambar selesai: %d karakter.", len(full_text))
    return OCRResult(
        full_text=full_text,
        page_count=1,
        ocr_used=True,
        pages=[full_text],
    )


def extract_text_from_pdf_scan(file_bytes: bytes, dpi: int = 200) -> OCRResult:
    """
    Ekstrak teks dari PDF scan menggunakan Tesseract OCR.
    Setiap halaman PDF dirasterisasi terlebih dahulu ke gambar via PyMuPDF.

    Args:
        file_bytes: Konten file PDF dalam bytes.
        dpi: Resolusi rasterisasi (default 200 DPI — keseimbangan kecepatan vs akurasi).
             Gunakan 300 DPI untuk dokumen dengan teks kecil.

    Returns:
        OCRResult dengan teks gabungan semua halaman dan ocr_used=True.

    Raises:
        ValueError: Jika file_bytes bukan PDF yang valid.
        RuntimeError: Jika Tesseract tidak ditemukan / gagal dijalankan.
    """
    logger.info("Memulai OCR PDF scan (DPI=%d).", dpi)

    try:
        doc: fitz.Document = fitz.open(stream=file_bytes, filetype="pdf")
    except fitz.FileDataError as exc:
        logger.error("PyMuPDF gagal membuka PDF scan: %s", exc)
        raise ValueError(f"File bukan PDF yang valid: {exc}") from exc

    page_count = doc.page_count
    pages: list[str] = []

    # Matrix untuk scaling (DPI default PyMuPDF = 72; scale factor = dpi/72)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    try:
        for page_num in range(page_count):
            page: fitz.Page = doc[page_num]

            # Rasterisasi halaman ke pixmap (format RGB)
            pixmap: fitz.Pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)  # type: ignore[attr-defined]

            # Konversi pixmap ke PIL Image
            img_bytes = pixmap.tobytes("png")
            image = Image.open(BytesIO(img_bytes)).convert("RGB")

            page_text = _image_to_text(image)
            pages.append(page_text)

            logger.debug(
                "Halaman %d/%d diproses OCR: %d karakter.",
                page_num + 1,
                page_count,
                len(page_text),
            )
    except RuntimeError:
        # Tesseract error — propagate langsung
        raise
    except Exception as exc:
        logger.error("Gagal memproses halaman PDF scan: %s", exc)
        raise RuntimeError(f"Gagal memproses halaman PDF scan: {exc}") from exc
    finally:
        doc.close()

    full_text = "\n\n".join(pages).strip()

    logger.info(
        "OCR PDF scan selesai: %d halaman, %d karakter total.",
        page_count,
        len(full_text),
    )
    return OCRResult(
        full_text=full_text,
        page_count=page_count,
        ocr_used=True,
        pages=pages,
    )
