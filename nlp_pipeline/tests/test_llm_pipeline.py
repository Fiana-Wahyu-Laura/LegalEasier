"""
tests/test_llm_pipeline.py — LegalEasier NLP Pipeline
Unit tests untuk modul LLM Sprint 3: analyzer, translator, risk_scorer, prompts.

Rules (CLAUDE.md §14):
- LLM API responses harus di-mock — jangan panggil API asli saat testing.
- Semua fungsi publik harus punya test.
- Test file naming: tests/test_*.py
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from llm.analyzer import (
    AnalysisResult,
    RiskClause,
    _extract_json_from_response,
    _parse_analysis_response,
    _validate_risk_clause,
    analyze_document,
)
from llm.prompts import (
    DISCLAIMER,
    RISK_ANALYSIS_SYSTEM_PROMPT,
    TRANSLATION_SYSTEM_PROMPT,
    build_risk_analysis_user_prompt,
    build_translation_user_prompt,
)
from llm.risk_scorer import RISK_LEVEL_WEIGHTS, compute_risk_score
from llm.translator import translate_clause, translate_clauses_batch


# ═══════════════════════════════════════════════════════════════════════════
# Tests: prompts.py
# ═══════════════════════════════════════════════════════════════════════════


class TestPrompts:
    """Tests untuk prompt templates."""

    def test_disclaimer_not_empty(self) -> None:
        assert DISCLAIMER
        assert "informatif" in DISCLAIMER
        assert "konsultasi hukum" in DISCLAIMER

    def test_risk_analysis_system_prompt_has_required_elements(self) -> None:
        assert "Tinggi" in RISK_ANALYSIS_SYSTEM_PROMPT
        assert "Sedang" in RISK_ANALYSIS_SYSTEM_PROMPT
        assert "Rendah" in RISK_ANALYSIS_SYSTEM_PROMPT
        assert "Aman" in RISK_ANALYSIS_SYSTEM_PROMPT
        assert "JSON" in RISK_ANALYSIS_SYSTEM_PROMPT
        assert "Indonesia" in RISK_ANALYSIS_SYSTEM_PROMPT

    def test_translation_system_prompt_has_required_elements(self) -> None:
        assert "Indonesia" in TRANSLATION_SYSTEM_PROMPT
        assert "sederhana" in TRANSLATION_SYSTEM_PROMPT

    def test_build_risk_analysis_user_prompt(self) -> None:
        prompt = build_risk_analysis_user_prompt(
            "test-doc-123",
            ["chunk 1", "chunk 2"],
        )
        assert "test-doc-123" in prompt
        assert "chunk 1" in prompt
        assert "chunk 2" in prompt
        assert "ISI DOKUMEN" in prompt

    def test_build_risk_analysis_user_prompt_empty_chunks(self) -> None:
        prompt = build_risk_analysis_user_prompt("doc-1", [])
        assert "doc-1" in prompt

    def test_build_translation_user_prompt(self) -> None:
        prompt = build_translation_user_prompt("Pasal 1 ayat 2")
        assert "Pasal 1 ayat 2" in prompt

    def test_build_translation_user_prompt_with_context(self) -> None:
        prompt = build_translation_user_prompt(
            "Pasal 1 ayat 2",
            context="Ini adalah kontrak sewa menyewa.",
        )
        assert "Pasal 1 ayat 2" in prompt
        assert "kontrak sewa" in prompt

    def test_build_translation_user_prompt_empty_context_ignored(self) -> None:
        prompt = build_translation_user_prompt("Pasal 1", context="   ")
        assert "Konteks dokumen" not in prompt


# ═══════════════════════════════════════════════════════════════════════════
# Tests: analyzer.py — JSON extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractJson:
    """Tests untuk _extract_json_from_response."""

    def test_direct_json(self) -> None:
        raw = '{"summary": "test", "risk_clauses": []}'
        result = _extract_json_from_response(raw)
        assert result["summary"] == "test"

    def test_json_in_code_block(self) -> None:
        raw = '```json\n{"summary": "test", "risk_clauses": []}\n```'
        result = _extract_json_from_response(raw)
        assert result["summary"] == "test"

    def test_json_in_code_block_no_lang(self) -> None:
        raw = '```\n{"summary": "test", "risk_clauses": []}\n```'
        result = _extract_json_from_response(raw)
        assert result["summary"] == "test"

    def test_json_with_surrounding_text(self) -> None:
        raw = 'Here is the result:\n{"summary": "test", "risk_clauses": []}\nDone.'
        result = _extract_json_from_response(raw)
        assert result["summary"] == "test"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Gagal meng-extract JSON"):
            _extract_json_from_response("this is not json at all")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError):
            _extract_json_from_response("")


# ═══════════════════════════════════════════════════════════════════════════
# Tests: analyzer.py — RiskClause validation
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateRiskClause:
    """Tests untuk _validate_risk_clause."""

    def test_valid_clause(self) -> None:
        data = {
            "clause_text": "Pihak kedua wajib membayar",
            "plain_language": "Kamu harus bayar",
            "risk_level": "Sedang",
            "confidence": 0.85,
        }
        clause = _validate_risk_clause(data)
        assert clause.clause_text == "Pihak kedua wajib membayar"
        assert clause.risk_level == "Sedang"
        assert clause.confidence == 0.85

    def test_all_valid_risk_levels(self) -> None:
        for level in ["Tinggi", "Sedang", "Rendah", "Aman"]:
            data = {
                "clause_text": "test",
                "plain_language": "test",
                "risk_level": level,
                "confidence": 0.5,
            }
            clause = _validate_risk_clause(data)
            assert clause.risk_level == level

    def test_invalid_risk_level_raises(self) -> None:
        data = {
            "clause_text": "test",
            "plain_language": "test",
            "risk_level": "High",  # English — not allowed
            "confidence": 0.5,
        }
        with pytest.raises(ValueError, match="risk_level"):
            _validate_risk_clause(data)

    def test_empty_clause_text_raises(self) -> None:
        data = {
            "clause_text": "",
            "plain_language": "test",
            "risk_level": "Aman",
            "confidence": 0.5,
        }
        with pytest.raises(ValueError, match="clause_text"):
            _validate_risk_clause(data)

    def test_empty_plain_language_raises(self) -> None:
        data = {
            "clause_text": "test",
            "plain_language": "",
            "risk_level": "Aman",
            "confidence": 0.5,
        }
        with pytest.raises(ValueError, match="plain_language"):
            _validate_risk_clause(data)

    def test_confidence_clamped_above_1(self) -> None:
        data = {
            "clause_text": "test",
            "plain_language": "test",
            "risk_level": "Aman",
            "confidence": 1.5,
        }
        clause = _validate_risk_clause(data)
        assert clause.confidence == 1.0

    def test_confidence_clamped_below_0(self) -> None:
        data = {
            "clause_text": "test",
            "plain_language": "test",
            "risk_level": "Aman",
            "confidence": -0.5,
        }
        clause = _validate_risk_clause(data)
        assert clause.confidence == 0.0

    def test_non_numeric_confidence_defaults(self) -> None:
        data = {
            "clause_text": "test",
            "plain_language": "test",
            "risk_level": "Aman",
            "confidence": "abc",
        }
        clause = _validate_risk_clause(data)
        assert clause.confidence == 0.5  # default


# ═══════════════════════════════════════════════════════════════════════════
# Tests: analyzer.py — parse_analysis_response
# ═══════════════════════════════════════════════════════════════════════════


class TestParseAnalysisResponse:
    """Tests untuk _parse_analysis_response."""

    def _make_response(
        self,
        summary: str = "Ringkasan dokumen.",
        clauses: list[dict] | None = None,
    ) -> str:
        if clauses is None:
            clauses = [
                {
                    "clause_text": "Pasal 5",
                    "plain_language": "Ini artinya kamu harus bayar.",
                    "risk_level": "Tinggi",
                    "confidence": 0.9,
                }
            ]
        return json.dumps({
            "summary": summary,
            "risk_clauses": clauses,
            "disclaimer": DISCLAIMER,
        })

    def test_valid_response(self) -> None:
        raw = self._make_response()
        result = _parse_analysis_response(raw)
        assert result.summary == "Ringkasan dokumen."
        assert len(result.risk_clauses) == 1
        assert result.risk_clauses[0].risk_level == "Tinggi"
        assert result.disclaimer == DISCLAIMER

    def test_empty_clauses_ok(self) -> None:
        raw = self._make_response(clauses=[])
        result = _parse_analysis_response(raw)
        assert len(result.risk_clauses) == 0

    def test_invalid_clause_skipped(self) -> None:
        raw = self._make_response(clauses=[
            {
                "clause_text": "valid",
                "plain_language": "valid",
                "risk_level": "Tinggi",
                "confidence": 0.9,
            },
            {
                "clause_text": "",  # invalid — empty
                "plain_language": "test",
                "risk_level": "Aman",
                "confidence": 0.5,
            },
        ])
        result = _parse_analysis_response(raw)
        assert len(result.risk_clauses) == 1

    def test_missing_summary_defaults_empty(self) -> None:
        raw = json.dumps({"risk_clauses": [], "disclaimer": DISCLAIMER})
        result = _parse_analysis_response(raw)
        assert result.summary == ""

    def test_multiple_clauses(self) -> None:
        clauses = [
            {
                "clause_text": f"Pasal {i}",
                "plain_language": f"Penjelasan {i}",
                "risk_level": level,
                "confidence": 0.8,
            }
            for i, level in enumerate(["Tinggi", "Sedang", "Rendah", "Aman"])
        ]
        raw = self._make_response(clauses=clauses)
        result = _parse_analysis_response(raw)
        assert len(result.risk_clauses) == 4


# ═══════════════════════════════════════════════════════════════════════════
# Tests: analyzer.py — analyze_document (mocked LLM)
# ═══════════════════════════════════════════════════════════════════════════


class TestAnalyzeDocument:
    """Tests untuk analyze_document (LLM di-mock)."""

    MOCK_LLM_RESPONSE = json.dumps({
        "summary": "Dokumen ini adalah kontrak sewa.",
        "risk_clauses": [
            {
                "clause_text": "Penyewa wajib membayar denda 10%",
                "plain_language": "Kamu harus bayar denda 10% jika telat.",
                "risk_level": "Tinggi",
                "confidence": 0.92,
            },
            {
                "clause_text": "Pemilik berhak mengakhiri kontrak",
                "plain_language": "Pemilik bisa putus kontrak kapan saja.",
                "risk_level": "Sedang",
                "confidence": 0.78,
            },
        ],
        "disclaimer": DISCLAIMER,
    })

    @patch("llm.analyzer.call_llm")
    def test_successful_analysis(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = self.MOCK_LLM_RESPONSE
        result = analyze_document("doc-123", ["chunk 1", "chunk 2"])
        assert result.summary == "Dokumen ini adalah kontrak sewa."
        assert len(result.risk_clauses) == 2
        assert result.risk_clauses[0].risk_level == "Tinggi"
        assert result.disclaimer == DISCLAIMER
        mock_llm.assert_called_once()

    @patch("llm.analyzer.call_llm")
    def test_retry_on_parse_error(self, mock_llm: MagicMock) -> None:
        # First call returns invalid JSON, second call returns valid
        mock_llm.side_effect = [
            "this is not valid json",
            self.MOCK_LLM_RESPONSE,
        ]
        result = analyze_document("doc-456", ["chunk"])
        assert len(result.risk_clauses) == 2
        assert mock_llm.call_count == 2

    @patch("llm.analyzer.call_llm")
    def test_returns_empty_after_max_retries(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = "invalid json forever"
        result = analyze_document("doc-789", ["chunk"])
        assert len(result.risk_clauses) == 0
        assert result.summary == ""
        assert mock_llm.call_count == 2

    @patch("llm.analyzer.call_llm")
    def test_runtime_error_returns_empty(self, mock_llm: MagicMock) -> None:
        mock_llm.side_effect = RuntimeError("API down")
        result = analyze_document("doc-err", ["chunk"])
        assert len(result.risk_clauses) == 0
        assert result.summary == ""

    def test_empty_document_id(self) -> None:
        result = analyze_document("", ["chunk"])
        assert len(result.risk_clauses) == 0

    def test_empty_chunks_returns_empty(self) -> None:
        result = analyze_document("doc-no-chunks", [])
        assert len(result.risk_clauses) == 0

    @patch("llm.analyzer.call_llm")
    def test_whitespace_document_id(self, mock_llm: MagicMock) -> None:
        result = analyze_document("   ", ["chunk"])
        assert len(result.risk_clauses) == 0
        mock_llm.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Tests: risk_scorer.py
# ═══════════════════════════════════════════════════════════════════════════


class TestComputeRiskScore:
    """Tests untuk compute_risk_score."""

    def test_empty_clauses_returns_0(self) -> None:
        assert compute_risk_score([]) == 0

    def test_single_tinggi_high_confidence(self) -> None:
        clauses = [RiskClause("text", "plain", "Tinggi", 1.0)]
        score = compute_risk_score(clauses)
        assert score == 100

    def test_single_aman_returns_0(self) -> None:
        clauses = [RiskClause("text", "plain", "Aman", 1.0)]
        score = compute_risk_score(clauses)
        assert score == 0

    def test_single_sedang_high_confidence(self) -> None:
        clauses = [RiskClause("text", "plain", "Sedang", 1.0)]
        score = compute_risk_score(clauses)
        assert score == 60

    def test_single_rendah_high_confidence(self) -> None:
        clauses = [RiskClause("text", "plain", "Rendah", 1.0)]
        score = compute_risk_score(clauses)
        assert score == 25

    def test_mixed_levels(self) -> None:
        clauses = [
            RiskClause("t1", "p1", "Tinggi", 0.9),
            RiskClause("t2", "p2", "Rendah", 0.8),
            RiskClause("t3", "p3", "Aman", 1.0),
        ]
        score = compute_risk_score(clauses)
        # (1.0*0.9*100 + 0.25*0.8*100 + 0.0*1.0*100) / 3 = (90 + 20 + 0) / 3 ≈ 36.67
        assert 35 <= score <= 40

    def test_scaling_3_tinggi(self) -> None:
        clauses = [
            RiskClause("t1", "p1", "Tinggi", 0.9),
            RiskClause("t2", "p2", "Tinggi", 0.8),
            RiskClause("t3", "p3", "Tinggi", 0.7),
        ]
        score = compute_risk_score(clauses)
        # avg = (90+80+70)/3 = 80. scaled = 80*1.2 = 96
        assert score == 96

    def test_scaling_5_tinggi(self) -> None:
        clauses = [
            RiskClause(f"t{i}", f"p{i}", "Tinggi", 0.7)
            for i in range(5)
        ]
        score = compute_risk_score(clauses)
        # avg = 70. scaled = 70*1.4 = 98
        assert score == 98

    def test_score_capped_at_100(self) -> None:
        clauses = [
            RiskClause(f"t{i}", f"p{i}", "Tinggi", 1.0)
            for i in range(6)
        ]
        score = compute_risk_score(clauses)
        assert score <= 100

    def test_confidence_0_means_no_contribution(self) -> None:
        clauses = [RiskClause("text", "plain", "Tinggi", 0.0)]
        score = compute_risk_score(clauses)
        assert score == 0

    def test_low_confidence_reduces_score(self) -> None:
        high_conf = [RiskClause("t", "p", "Tinggi", 1.0)]
        low_conf = [RiskClause("t", "p", "Tinggi", 0.3)]
        assert compute_risk_score(high_conf) > compute_risk_score(low_conf)

    def test_risk_level_weights_valid(self) -> None:
        assert RISK_LEVEL_WEIGHTS["Tinggi"] == 1.0
        assert RISK_LEVEL_WEIGHTS["Sedang"] == 0.6
        assert RISK_LEVEL_WEIGHTS["Rendah"] == 0.25
        assert RISK_LEVEL_WEIGHTS["Aman"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Tests: translator.py (mocked LLM)
# ═══════════════════════════════════════════════════════════════════════════


class TestTranslateClause:
    """Tests untuk translate_clause (LLM di-mock)."""

    @patch("llm.translator.call_llm")
    def test_successful_translation(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = "Artinya kamu harus bayar denda jika telat."
        result = translate_clause("Pihak kedua wajib membayar denda")
        assert "bayar denda" in result
        mock_llm.assert_called_once()

    @patch("llm.translator.call_llm")
    def test_with_context(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = "Penjelasan klausul."
        result = translate_clause("Pasal 1", context="Kontrak sewa")
        assert result == "Penjelasan klausul."

    def test_empty_clause_returns_empty(self) -> None:
        result = translate_clause("")
        assert result == ""

    def test_whitespace_clause_returns_empty(self) -> None:
        result = translate_clause("   ")
        assert result == ""

    @patch("llm.translator.call_llm")
    def test_llm_error_returns_empty(self, mock_llm: MagicMock) -> None:
        mock_llm.side_effect = RuntimeError("API down")
        result = translate_clause("Pasal 1")
        assert result == ""


class TestTranslateClausesBatch:
    """Tests untuk translate_clauses_batch."""

    @patch("llm.translator.call_llm")
    def test_batch_translation(self, mock_llm: MagicMock) -> None:
        mock_llm.side_effect = [
            "Terjemahan 1",
            "Terjemahan 2",
            "Terjemahan 3",
        ]
        results = translate_clauses_batch(["A", "B", "C"])
        assert len(results) == 3
        assert results[0] == "Terjemahan 1"
        assert mock_llm.call_count == 3

    @patch("llm.translator.call_llm")
    def test_empty_batch(self, mock_llm: MagicMock) -> None:
        results = translate_clauses_batch([])
        assert results == []
        mock_llm.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Tests: AnalysisResult dataclass
# ═══════════════════════════════════════════════════════════════════════════


class TestAnalysisResult:
    """Tests untuk AnalysisResult dataclass."""

    def test_default_values(self) -> None:
        result = AnalysisResult()
        assert result.risk_clauses == []
        assert result.summary == ""
        assert result.disclaimer == DISCLAIMER

    def test_custom_values(self) -> None:
        clauses = [RiskClause("text", "plain", "Tinggi", 0.9)]
        result = AnalysisResult(
            risk_clauses=clauses,
            summary="Summary test",
        )
        assert len(result.risk_clauses) == 1
        assert result.summary == "Summary test"


class TestRiskClause:
    """Tests untuk RiskClause dataclass."""

    def test_creation(self) -> None:
        clause = RiskClause(
            clause_text="Pasal 1",
            plain_language="Artinya...",
            risk_level="Tinggi",
            confidence=0.95,
        )
        assert clause.clause_text == "Pasal 1"
        assert clause.risk_level == "Tinggi"
        assert clause.confidence == 0.95
