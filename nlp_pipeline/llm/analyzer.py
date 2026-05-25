"""
llm/analyzer.py — LegalEasier NLP Pipeline
Deteksi dan klasifikasi klausul berisiko menggunakan LLM (Sprint 3).

Tugasnya (sesuai CLAUDE.md §9):
    Langkah 7 dari pipeline — LLM analysis:
    - Deteksi klausul yang berpotensi merugikan user
    - Klasifikasikan ke level: "Tinggi", "Sedang", "Rendah", "Aman"
    - Sertakan penjelasan dalam bahasa Indonesia sederhana

Rules (CLAUDE.md §9 LLM Calls):
- SELALU gunakan RAG context dari retriever — JANGAN tanya LLM tanpa dokumen.
- Validasi JSON output LLM sebelum disimpan — retry sekali jika parse error.
- Risk levels HANYA boleh: "Tinggi", "Sedang", "Rendah", "Aman".
- Setiap output wajib sertakan confidence score (float 0.0–1.0).
- Primary LLM: Claude API. Fallback: NVIDIA NIM (OpenAI-compatible).
- Semua LLM error harus di-catch — jangan crash pipeline.

Aturan kode:
- Tidak ada hardcoded API key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from llm._client import call_llm
from llm.prompts import (
    DISCLAIMER,
    RISK_ANALYSIS_SYSTEM_PROMPT,
    build_risk_analysis_user_prompt,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types & data classes
# ---------------------------------------------------------------------------

RiskLevel = Literal["Tinggi", "Sedang", "Rendah", "Aman"]
VALID_RISK_LEVELS: set[str] = {"Tinggi", "Sedang", "Rendah", "Aman"}


@dataclass
class RiskClause:
    """Satu klausul berisiko hasil analisis LLM."""

    clause_text: str
    plain_language: str
    risk_level: RiskLevel
    confidence: float  # 0.0–1.0


@dataclass
class AnalysisResult:
    """Hasil lengkap analisis risiko satu dokumen."""

    risk_clauses: list[RiskClause] = field(default_factory=list)
    summary: str = ""
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------------------
# JSON parsing & validation
# ---------------------------------------------------------------------------


def _extract_json_from_response(raw: str) -> dict:
    """Ekstrak dan parse JSON dari response LLM.

    LLM kadang menambahkan teks sebelum/sesudah JSON, atau membungkus
    dalam markdown code block. Fungsi ini menangani semua kasus tersebut.

    Args:
        raw: Raw response text dari LLM.

    Returns:
        Parsed dict dari JSON.

    Raises:
        ValueError: Jika JSON tidak bisa di-parse.
    """
    text = raw.strip()

    # Coba langsung parse dulu
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Coba extract dari markdown code block ```json ... ```
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Coba cari JSON object pattern { ... }
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Gagal meng-extract JSON dari response LLM: {text[:200]}...")


def _validate_risk_clause(clause_data: dict) -> RiskClause:
    """Validasi dan buat RiskClause dari dict.

    Args:
        clause_data: Dict dari JSON response LLM.

    Returns:
        RiskClause yang sudah divalidasi.

    Raises:
        ValueError: Jika data tidak valid.
    """
    clause_text = clause_data.get("clause_text", "").strip()
    plain_language = clause_data.get("plain_language", "").strip()
    risk_level = clause_data.get("risk_level", "").strip()
    confidence = clause_data.get("confidence", 0.0)

    if not clause_text:
        raise ValueError("clause_text tidak boleh kosong.")
    if not plain_language:
        raise ValueError("plain_language tidak boleh kosong.")
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            f"risk_level '{risk_level}' tidak valid. "
            f"Harus salah satu dari: {VALID_RISK_LEVELS}"
        )

    # Clamp confidence ke 0.0–1.0
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return RiskClause(
        clause_text=clause_text,
        plain_language=plain_language,
        risk_level=risk_level,
        confidence=confidence,
    )


def _parse_analysis_response(raw: str) -> AnalysisResult:
    """Parse dan validasi response LLM menjadi AnalysisResult.

    Args:
        raw: Raw response text dari LLM.

    Returns:
        AnalysisResult yang sudah divalidasi.

    Raises:
        ValueError: Jika response tidak bisa di-parse atau tidak valid.
    """
    data = _extract_json_from_response(raw)

    summary = data.get("summary", "").strip()
    if not summary:
        logger.warning("LLM tidak menghasilkan summary. Menggunakan default kosong.")

    raw_clauses = data.get("risk_clauses", [])
    if not isinstance(raw_clauses, list):
        raise ValueError("risk_clauses harus berupa array/list.")

    risk_clauses: list[RiskClause] = []
    for i, clause_data in enumerate(raw_clauses):
        try:
            clause = _validate_risk_clause(clause_data)
            risk_clauses.append(clause)
        except ValueError as exc:
            logger.warning(
                "Klausul index %d tidak valid, dilewati: %s", i, exc
            )
            continue

    return AnalysisResult(
        risk_clauses=risk_clauses,
        summary=summary,
        disclaimer=DISCLAIMER,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_document(
    document_id: str,
    context_chunks: list[str],
) -> AnalysisResult:
    """Analisis dokumen hukum menggunakan LLM dengan RAG context.

    Langkah (CLAUDE.md §9 Processing Order — langkah 7):
    1. Bangun prompt dari context_chunks (RAG context).
    2. Kirim ke LLM (Claude primary, NVIDIA NIM fallback).
    3. Parse dan validasi JSON response.
    4. Retry sekali jika parse error (CLAUDE.md §9).
    5. Return AnalysisResult dengan risk_clauses, summary, disclaimer.

    Args:
        document_id: UUID dokumen yang dianalisis.
        context_chunks: Chunk teks dari dokumen — WAJIB ada, tidak boleh kosong
            (CLAUDE.md §9: "never ask LLM about document without providing chunks").

    Returns:
        AnalysisResult berisi risk_clauses, summary, dan disclaimer.
        Jika semua LLM gagal, return AnalysisResult kosong (tidak crash pipeline).
    """
    if not document_id or not document_id.strip():
        logger.error("document_id kosong, return AnalysisResult kosong.")
        return AnalysisResult()

    if not context_chunks:
        logger.error(
            "[%s] context_chunks kosong — CLAUDE.md melarang panggil LLM tanpa context. "
            "Return AnalysisResult kosong.",
            document_id,
        )
        return AnalysisResult()

    user_prompt = build_risk_analysis_user_prompt(document_id, context_chunks)
    max_attempts = 2  # CLAUDE.md §9: retry sekali pada parse error

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "[%s] LLM analysis attempt %d/%d...",
                document_id, attempt, max_attempts,
            )
            raw_response = call_llm(RISK_ANALYSIS_SYSTEM_PROMPT, user_prompt)
            result = _parse_analysis_response(raw_response)

            logger.info(
                "[%s] Analisis selesai: %d klausul berisiko ditemukan.",
                document_id,
                len(result.risk_clauses),
            )
            return result

        except ValueError as exc:
            logger.warning(
                "[%s] Parse error attempt %d: %s",
                document_id, attempt, exc,
            )
            if attempt < max_attempts:
                logger.info("[%s] Retry sekali sesuai CLAUDE.md §9...", document_id)
                continue
            logger.error(
                "[%s] Parse error setelah %d attempt, return AnalysisResult kosong.",
                document_id, max_attempts,
            )
            return AnalysisResult()

        except RuntimeError as exc:
            logger.error(
                "[%s] LLM call gagal: %s. Return AnalysisResult kosong.",
                document_id, exc,
            )
            return AnalysisResult()

    return AnalysisResult()
