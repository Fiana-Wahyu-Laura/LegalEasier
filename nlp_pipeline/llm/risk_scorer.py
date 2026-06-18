"""
llm/risk_scorer.py — LegalEasier NLP Pipeline
Hitung skor risiko dokumen 0–100 berbasis analisis LLM (Sprint 3).

Skor risiko:
    0–20   : Aman — tidak ada klausul yang merugikan
    21–40  : Rendah — ada beberapa catatan minor
    41–70  : Sedang — ada klausul yang perlu diperhatikan
    71–100 : Tinggi — ada klausul yang berpotensi sangat merugikan

Rules (CLAUDE.md §9):
- risk_score harus integer antara 0–100.
- Skor dihitung dari kombinasi: jumlah klausul berisiko, level,
  dan confidence score masing-masing klausul.
- Tidak boleh null — default ke 0 jika analisis gagal.

Optimizations:
- Continuous scaling (replaces binary cutoffs)
- Clause coverage factor (more risky clauses = higher score)
- Detailed breakdown for UI display
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm.analyzer import RiskClause

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bobot per risk level (digunakan untuk weighted average)
# ---------------------------------------------------------------------------

RISK_LEVEL_WEIGHTS: dict[str, float] = {
    "Tinggi": 1.0,
    "Sedang": 0.6,
    "Rendah": 0.25,
    "Aman": 0.0,
}


@dataclass
class RiskBreakdown:
    """Detailed breakdown of risk score computation."""

    total_score: int
    clause_count: int
    tinggi_count: int
    sedang_count: int
    rendah_count: int
    aman_count: int
    base_score: float
    coverage_multiplier: float
    final_score: float


def compute_risk_score(risk_clauses: list[RiskClause]) -> int:
    """Hitung skor risiko agregat 0–100 dari daftar klausul berisiko.

    Algoritma (v2 — continuous scaling):
    1. Untuk setiap klausul, hitung weighted score:
       clause_score = risk_level_weight × confidence × 100
    2. Base score = rata-rata weighted score semua klausul.
    3. Coverage factor: skor meningkat proporsional dengan jumlah klausul
       berisiko (Tinggi/Sedang) relatif terhadap total klausul.
       coverage_multiplier = 1.0 + (risky_ratio * 0.5)
       Ini artinya dokumen dengan 80% klausul berisiko mendapat 1.4x boost.
    4. Final = base_score * coverage_multiplier, clamped to 0–100.

    Args:
        risk_clauses: Hasil dari analyzer.analyze_document().

    Returns:
        Integer 0–100. 0 = tidak ada risiko, 100 = risiko tertinggi.
    """
    if not risk_clauses:
        return 0

    total_weighted = 0.0
    tinggi_count = 0
    sedang_count = 0
    rendah_count = 0
    aman_count = 0

    for clause in risk_clauses:
        weight = RISK_LEVEL_WEIGHTS.get(clause.risk_level, 0.0)
        confidence = max(0.0, min(1.0, clause.confidence))
        clause_score = weight * confidence * 100
        total_weighted += clause_score

        if clause.risk_level == "Tinggi":
            tinggi_count += 1
        elif clause.risk_level == "Sedang":
            sedang_count += 1
        elif clause.risk_level == "Rendah":
            rendah_count += 1
        else:
            aman_count += 1

    # Base score: rata-rata weighted score
    base_score = total_weighted / len(risk_clauses)

    # Coverage factor: continuous scaling based on proportion of risky clauses
    risky_count = tinggi_count + sedang_count
    risky_ratio = risky_count / len(risk_clauses)
    coverage_multiplier = 1.0 + (risky_ratio * 0.5)  # max 1.5x boost

    # Final score
    final_score = base_score * coverage_multiplier

    # Clamp ke 0–100 dan bulatkan ke integer
    final_score_clamped = int(round(max(0.0, min(100.0, final_score))))

    logger.info(
        "Risk score dihitung: %d (dari %d klausul: %d Tinggi, %d Sedang, "
        "%d Rendah, %d Aman | base=%.1f, coverage=%.2fx).",
        final_score_clamped,
        len(risk_clauses),
        tinggi_count,
        sedang_count,
        rendah_count,
        aman_count,
        base_score,
        coverage_multiplier,
    )

    return final_score_clamped


def compute_risk_score_detailed(risk_clauses: list[RiskClause]) -> RiskBreakdown:
    """Compute risk score with detailed breakdown (for UI display).

    Same algorithm as compute_risk_score but returns full breakdown.
    """
    if not risk_clauses:
        return RiskBreakdown(
            total_score=0, clause_count=0,
            tinggi_count=0, sedang_count=0, rendah_count=0, aman_count=0,
            base_score=0.0, coverage_multiplier=1.0, final_score=0.0,
        )

    total_weighted = 0.0
    tinggi_count = 0
    sedang_count = 0
    rendah_count = 0
    aman_count = 0

    for clause in risk_clauses:
        weight = RISK_LEVEL_WEIGHTS.get(clause.risk_level, 0.0)
        confidence = max(0.0, min(1.0, clause.confidence))
        total_weighted += weight * confidence * 100

        if clause.risk_level == "Tinggi":
            tinggi_count += 1
        elif clause.risk_level == "Sedang":
            sedang_count += 1
        elif clause.risk_level == "Rendah":
            rendah_count += 1
        else:
            aman_count += 1

    base_score = total_weighted / len(risk_clauses)
    risky_count = tinggi_count + sedang_count
    risky_ratio = risky_count / len(risk_clauses)
    coverage_multiplier = 1.0 + (risky_ratio * 0.5)
    final_score = max(0.0, min(100.0, base_score * coverage_multiplier))

    return RiskBreakdown(
        total_score=int(round(final_score)),
        clause_count=len(risk_clauses),
        tinggi_count=tinggi_count,
        sedang_count=sedang_count,
        rendah_count=rendah_count,
        aman_count=aman_count,
        base_score=base_score,
        coverage_multiplier=coverage_multiplier,
        final_score=final_score,
    )
