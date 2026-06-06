"""
tests/test_preprocessing.py — LegalEasier NLP Pipeline
Unit tests untuk modul preprocessing Sprint 2:
    - cleaner.clean_legal_text
    - splitter.split_text
    - tokenizer (ditest dengan mock SpaCy untuk menghindari dependency model)

Jalankan: pytest tests/test_preprocessing.py -v
"""

import pytest

from preprocessing.cleaner import (
    clean_legal_text,
    expand_common_abbreviations,
    fix_hyphenation,
    normalize_dashes,
    normalize_quotes,
    normalize_unicode,
    normalize_whitespace,
    remove_control_characters,
    remove_page_markers,
)
from preprocessing.splitter import (
    SplitResult,
    split_by_legal_structure,
    split_sentences_regex,
    split_text,
)


# ---------------------------------------------------------------------------
# Tests: cleaner.py
# ---------------------------------------------------------------------------


class TestNormalizeUnicode:
    def test_nfc_normalization(self) -> None:
        # Karakter yang sama tapi representasi berbeda
        text_nfd = "cafe\u0301"  # e + combining acute accent (NFD)
        result = normalize_unicode(text_nfd)
        assert result == "caf\u00e9"  # NFC: é sebagai satu karakter

    def test_regular_string_unchanged(self) -> None:
        text = "Pasal 1 ayat (1) menjelaskan tentang perjanjian."
        assert normalize_unicode(text) == text


class TestRemoveControlCharacters:
    def test_removes_null_bytes(self) -> None:
        text = "Perjanjian\x00ini\x01sah."
        result = remove_control_characters(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "Perjanjian" in result

    def test_preserves_newline_and_tab(self) -> None:
        text = "Baris 1\nBaris 2\tTab"
        result = remove_control_characters(text)
        assert "\n" in result
        assert "\t" in result


class TestRemovePageMarkers:
    def test_removes_halaman_marker(self) -> None:
        text = "Isi dokumen.\nHalaman 1 dari 10\nLanjutan isi."
        result = remove_page_markers(text)
        assert "Halaman 1 dari 10" not in result
        assert "Isi dokumen." in result

    def test_removes_dash_page_number(self) -> None:
        text = "Kalimat.\n- 2 -\nKalimat berikutnya."
        result = remove_page_markers(text)
        assert "- 2 -" not in result


class TestNormalizeWhitespace:
    def test_removes_excess_spaces(self) -> None:
        text = "Kata   satu    dua    tiga."
        result = normalize_whitespace(text)
        assert "   " not in result

    def test_reduces_excess_newlines(self) -> None:
        text = "Paragraf satu.\n\n\n\n\nParagraf dua."
        result = normalize_whitespace(text)
        assert "\n\n\n" not in result

    def test_strips_leading_trailing_whitespace(self) -> None:
        text = "   Teks dengan spasi.   "
        result = normalize_whitespace(text)
        assert result == "Teks dengan spasi."


class TestFixHyphenation:
    def test_joins_hyphenated_word(self) -> None:
        text = "per-\njanjian ini"
        result = fix_hyphenation(text)
        assert "perjanjian" in result

    def test_does_not_join_normal_newline(self) -> None:
        text = "Baris pertama.\nBaris kedua."
        result = fix_hyphenation(text)
        # Newline tanpa hyphen sebelumnya tidak terpengaruh
        assert "\n" in result


class TestNormalizeQuotes:
    def test_replaces_smart_single_quotes(self) -> None:
        text = "\u2018kata\u2019"
        result = normalize_quotes(text)
        assert result == "'kata'"

    def test_replaces_smart_double_quotes(self) -> None:
        text = "\u201Ckalimat\u201D"
        result = normalize_quotes(text)
        assert result == '"kalimat"'


class TestNormalizeDashes:
    def test_replaces_en_dash(self) -> None:
        text = "Pasal 1\u20133"
        result = normalize_dashes(text)
        assert "\u2013" not in result
        assert "-" in result

    def test_replaces_em_dash(self) -> None:
        text = "Syarat\u2014Ketentuan"
        result = normalize_dashes(text)
        assert "\u2014" not in result


class TestExpandAbbreviations:
    def test_expands_pt(self) -> None:
        text = "PT Maju Bersama menandatangani perjanjian."
        result = expand_common_abbreviations(text)
        assert "Perseroan Terbatas" in result

    def test_expands_uu(self) -> None:
        text = "Berdasarkan UU No. 40 Tahun 2007."
        result = expand_common_abbreviations(text)
        assert "Undang-Undang" in result


class TestCleanLegalText:
    """Tests untuk fungsi utama pipeline cleaning."""

    SAMPLE_TEXT = (
        "Perjanjian Sewa Menyewa\r\n\r\n"
        "Pasal 1\n"
        "Pihak per-\ntama adalah PT Sinar Jaya.\n"
        "Halaman 1 dari 5\n\n\n"
        "Pasal 2\n"
        "Pembayaran sebesar Rp. 5.000.000,- per bulan."
    )

    def test_output_is_string(self) -> None:
        result = clean_legal_text(self.SAMPLE_TEXT)
        assert isinstance(result, str)

    def test_removes_page_markers(self) -> None:
        result = clean_legal_text(self.SAMPLE_TEXT)
        assert "Halaman 1 dari 5" not in result

    def test_fixes_hyphenation(self) -> None:
        result = clean_legal_text(self.SAMPLE_TEXT)
        assert "pertama" in result

    def test_no_excess_newlines(self) -> None:
        result = clean_legal_text(self.SAMPLE_TEXT)
        assert "\n\n\n" not in result

    def test_raises_on_non_string(self) -> None:
        with pytest.raises(ValueError, match="harus bertipe str"):
            clean_legal_text(12345)  # type: ignore[arg-type]

    def test_expand_abbreviations_optional(self) -> None:
        text = "PT Maju Bersama."
        # Tanpa expand
        result_no_expand = clean_legal_text(text, expand_abbreviations=False)
        assert "PT" in result_no_expand

        # Dengan expand
        result_expand = clean_legal_text(text, expand_abbreviations=True)
        assert "Perseroan Terbatas" in result_expand


# ---------------------------------------------------------------------------
# Tests: splitter.py
# ---------------------------------------------------------------------------


class TestSplitSentencesRegex:
    def test_basic_splitting(self) -> None:
        text = "Pasal 1 berisi ketentuan umum. Pasal 2 mengatur kewajiban."
        result = split_sentences_regex(text)
        assert len(result) >= 2

    def test_returns_list_of_strings(self) -> None:
        text = "Kalimat pertama. Kalimat kedua."
        result = split_sentences_regex(text)
        assert all(isinstance(s, str) for s in result)

    def test_filters_empty_strings(self) -> None:
        text = "Kalimat. "
        result = split_sentences_regex(text)
        assert all(s.strip() for s in result)


class TestSplitByLegalStructure:
    def test_splits_on_pasal(self) -> None:
        text = "Pasal 1\nKetentuan umum.\nPasal 2\nKewajiban para pihak."
        result = split_by_legal_structure(text)
        assert any("Pasal 1" in s for s in result)
        assert any("Pasal 2" in s for s in result)

    def test_splits_on_ayat(self) -> None:
        text = "Kontrak ini.(1) Pihak pertama.(2) Pihak kedua."
        result = split_by_legal_structure(text)
        assert len(result) >= 2


class TestSplitText:
    VALID_TEXT = (
        "Perjanjian ini dibuat oleh Pihak Pertama. "
        "Pihak Kedua menyetujui semua ketentuan. "
        "Pembayaran dilakukan setiap bulan. "
        "Denda berlaku jika terlambat."
    )

    def test_returns_split_result(self) -> None:
        result = split_text(self.VALID_TEXT)
        assert isinstance(result, SplitResult)

    def test_sentences_not_empty(self) -> None:
        result = split_text(self.VALID_TEXT)
        assert result.sentence_count > 0
        assert len(result.sentences) == result.sentence_count

    def test_min_sentence_length_filter(self) -> None:
        text = "OK. " + "Kalimat yang lebih panjang ini harus melewati filter. " * 3
        result = split_text(text, min_sentence_length=20)
        assert all(len(s) >= 20 for s in result.sentences)

    def test_method_nltk(self) -> None:
        result = split_text(self.VALID_TEXT, method="nltk")
        assert result.method_used in {"nltk", "regex_fallback"}

    def test_method_legal(self) -> None:
        text = "Pasal 1\nIsi pasal satu yang cukup panjang.\nPasal 2\nIsi pasal dua yang panjang juga."
        result = split_text(text, method="legal")
        assert result.method_used == "legal"

    def test_method_regex(self) -> None:
        result = split_text(self.VALID_TEXT, method="regex")
        assert result.method_used == "regex"

    def test_raises_on_empty_text(self) -> None:
        with pytest.raises(ValueError, match="tidak boleh kosong"):
            split_text("")

    def test_raises_on_non_string(self) -> None:
        with pytest.raises(ValueError, match="harus bertipe str"):
            split_text(None)  # type: ignore[arg-type]

    def test_raises_on_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="tidak valid"):
            split_text(self.VALID_TEXT, method="unknown")
