"""
tests/test_ocr_extractor.py — LegalEasier NLP Pipeline
Unit tests untuk OCR extraction pipeline (Sprint 1).

Menguji:
- pdf_extractor.py: PDFExtractionResult, _is_text_valid
- image_ocr.py: extract_text_from_image, extract_text_from_pdf_scan
- main.py FastAPI endpoints via TestClient

Rules (CLAUDE.md §14):
- Mock semua Tesseract OCR calls — jangan panggil Tesseract asli di unit test.
- Mock semua PyMuPDF calls — jangan butuh file PDF nyata untuk unit test.
- Test file: tests/test_ocr_extractor.py
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from ocr.pdf_extractor import PDFExtractionResult, _is_text_valid, extract_text_from_pdf

client = TestClient(app)


# ===========================================================================
# Tests: _is_text_valid
# ===========================================================================

class TestIsTextValid:
    """Unit tests untuk fungsi validasi kualitas teks."""

    def test_valid_text_returns_true(self) -> None:
        """Teks normal cukup panjang harus dianggap valid."""
        text = "Ini adalah kontrak sewa menyewa antara pihak A dan pihak B." * 3
        assert _is_text_valid(text) is True

    def test_empty_text_returns_false(self) -> None:
        """String kosong harus dianggap tidak valid."""
        assert _is_text_valid("") is False

    def test_text_below_min_length_returns_false(self) -> None:
        """Teks yang lebih pendek dari threshold harus dianggap tidak valid."""
        assert _is_text_valid("Teks singkat") is False

    def test_garbled_text_returns_false(self) -> None:
        """Teks berisi banyak karakter non-printable harus dianggap tidak valid."""
        garbled = "\x00\x01\x02\x03\x04\x05\x06\x07\x08" * 20
        assert _is_text_valid(garbled) is False

    def test_text_exactly_at_threshold_returns_true(self) -> None:
        """Teks tepat di batas threshold harus dianggap valid."""
        text = "a" * 50  # settings.min_text_length = 50
        assert _is_text_valid(text) is True


# ===========================================================================
# Tests: extract_text_from_pdf
# ===========================================================================

class TestExtractTextFromPdf:
    """Unit tests untuk PyMuPDF PDF extractor."""

    @patch("ocr.pdf_extractor.fitz.open")
    def test_digital_pdf_returns_text(self, mock_fitz_open: MagicMock) -> None:
        """PDF digital harus mengembalikan teks dengan ocr_used=False."""
        # Setup mock dokumen PyMuPDF
        mock_page = MagicMock()
        long_text = "Pasal 1: Pihak pertama setuju untuk menyewakan properti." * 5
        mock_page.get_text.return_value = long_text

        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page, mock_page]))
        mock_fitz_open.return_value = mock_doc

        result = extract_text_from_pdf(b"fake-pdf-bytes")

        assert result.ocr_used is False
        assert len(result.full_text) > 0
        assert result.page_count == 2
        assert result.error is None

    @patch("ocr.pdf_extractor.fitz.open")
    def test_scanned_pdf_returns_empty_text(self, mock_fitz_open: MagicMock) -> None:
        """PDF scan (teks sangat sedikit) harus mengembalikan full_text kosong."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "  # Hampir kosong

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc

        result = extract_text_from_pdf(b"fake-scan-pdf-bytes")

        assert result.full_text == ""
        assert result.ocr_used is False   # Tesseract belum dijalankan, caller yang putuskan
        assert result.error is not None   # Harus ada pesan error/info

    @patch("ocr.pdf_extractor.fitz.open")
    def test_invalid_pdf_raises_value_error(self, mock_fitz_open: MagicMock) -> None:
        """File bukan PDF harus raise ValueError."""
        import fitz as fitz_module
        mock_fitz_open.side_effect = fitz_module.FileDataError("bukan PDF")

        with pytest.raises(ValueError, match="File bukan PDF"):
            extract_text_from_pdf(b"bukan-pdf")


# ===========================================================================
# Tests: FastAPI endpoints
# ===========================================================================

class TestHealthEndpoint:
    """Unit tests untuk endpoint health check."""

    def test_health_check_returns_ok(self) -> None:
        """Health check harus mengembalikan status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "legaleasier-nlp-pipeline"


class TestOcrExtractEndpoint:
    """Unit tests untuk endpoint /ocr/extract."""

    @patch("main.extract_text_from_pdf")
    def test_pdf_digital_success(self, mock_extract: MagicMock) -> None:
        """PDF digital harus mengembalikan success=True dan ocr_used=False."""
        long_text = "Kontrak kerja sama antara PT A dan PT B untuk proyek X." * 5
        mock_extract.return_value = PDFExtractionResult(
            full_text=long_text,
            page_count=3,
            ocr_used=False,
            pages=[long_text],
        )

        fake_pdf = io.BytesIO(b"fake-pdf-content")
        response = client.post(
            "/ocr/extract",
            files={"file": ("dokumen.pdf", fake_pdf, "application/pdf")},
            data={"file_type": "pdf", "document_id": "test-uuid-001"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["ocr_used"] is False
        assert body["data"]["document_id"] == "test-uuid-001"
        assert body["data"]["page_count"] == 3

    @patch("main.extract_text_from_pdf_scan")
    @patch("main.extract_text_from_pdf")
    def test_pdf_scan_triggers_tesseract_fallback(
        self,
        mock_pdf_extract: MagicMock,
        mock_ocr_scan: MagicMock,
    ) -> None:
        """PDF scan harus memicu fallback ke Tesseract dan ocr_used=True."""
        # PyMuPDF mengembalikan teks kosong
        mock_pdf_extract.return_value = PDFExtractionResult(
            full_text="",
            page_count=2,
            ocr_used=False,
            error="PDF scan",
        )
        # Tesseract berhasil mengekstrak teks
        from ocr.image_ocr import OCRResult
        ocr_text = "Perjanjian ini dibuat pada tanggal satu bulan Januari." * 5
        mock_ocr_scan.return_value = OCRResult(
            full_text=ocr_text,
            page_count=2,
            ocr_used=True,
            pages=[ocr_text],
        )

        fake_pdf = io.BytesIO(b"fake-scan-pdf")
        response = client.post(
            "/ocr/extract",
            files={"file": ("scan.pdf", fake_pdf, "application/pdf")},
            data={"file_type": "pdf", "document_id": "test-uuid-002"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["ocr_used"] is True

    @patch("main.extract_text_from_image")
    def test_jpg_image_uses_tesseract(self, mock_extract: MagicMock) -> None:
        """File JPG harus langsung menggunakan Tesseract OCR."""
        from ocr.image_ocr import OCRResult
        ocr_text = "Surat keterangan kerja dari perusahaan ABC." * 5
        mock_extract.return_value = OCRResult(
            full_text=ocr_text,
            page_count=1,
            ocr_used=True,
            pages=[ocr_text],
        )

        fake_jpg = io.BytesIO(b"fake-jpg-content")
        response = client.post(
            "/ocr/extract",
            files={"file": ("foto.jpg", fake_jpg, "image/jpeg")},
            data={"file_type": "jpg"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["ocr_used"] is True
        assert body["data"]["file_type"] == "jpg"

    def test_invalid_file_type_returns_422(self) -> None:
        """Tipe file yang tidak didukung harus mengembalikan 422."""
        fake_file = io.BytesIO(b"fake-docx")
        response = client.post(
            "/ocr/extract",
            files={"file": ("doc.docx", fake_file, "application/vnd.openxmlformats")},
            data={"file_type": "docx"},
        )
        assert response.status_code == 422

    def test_oversized_file_returns_413(self) -> None:
        """File melebihi 25MB harus mengembalikan 413."""
        large_file = io.BytesIO(b"x" * (26 * 1024 * 1024))  # 26MB
        response = client.post(
            "/ocr/extract",
            files={"file": ("besar.pdf", large_file, "application/pdf")},
            data={"file_type": "pdf"},
        )
        assert response.status_code == 413


class TestNlpProcessContractEndpoint:
    """Unit tests untuk endpoint kontrak backend ↔ NLP (/nlp/process)."""

    @patch("main.extract_text_from_pdf")
    def test_pdf_digital_returns_contract_payload(self, mock_extract: MagicMock) -> None:
        """Endpoint kontrak harus mengembalikan JSON raw sesuai backend contract."""
        long_text = "Kontrak kerja sama antara PT A dan PT B untuk proyek X." * 5
        mock_extract.return_value = PDFExtractionResult(
            full_text=long_text,
            page_count=3,
            ocr_used=False,
            pages=[long_text],
        )

        fake_pdf = io.BytesIO(b"fake-pdf-content")
        response = client.post(
            "/nlp/process",
            files={"file": ("dokumen.pdf", fake_pdf, "application/pdf")},
            data={"file_type": "pdf", "document_id": "12345678-1234-5678-1234-567812345678"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["document_id"] == "12345678-1234-5678-1234-567812345678"
        assert body["ocr_used"] is False
        assert body["full_text"] == long_text
        # Sprint 2: LLM fields return empty/zero defaults (Sprint 3 akan isi nilai nyata)
        assert isinstance(body["summary"], str)       # "" — Sprint 3 belum jalan
        assert body["risk_score"] == 0                # 0 — belum dianalisis
        assert body["risk_clauses"] == []             # [] — belum ada klausul
        assert body["disclaimer"].startswith("Hasil ini bersifat informatif")
