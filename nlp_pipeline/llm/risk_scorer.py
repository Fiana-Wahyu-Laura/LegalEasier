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

Aturan kode:
- Tidak ada hardcoded API key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

from __future__ import annotations

import logging
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


def compute_risk_score(risk_clauses: list[RiskClause]) -> int:
    """Hitung skor risiko agregat 0–100 dari daftar klausul berisiko.

    Algoritma:
    1. Untuk setiap klausul, hitung weighted score:
       clause_score = risk_level_weight × confidence × 100
    2. Skor final = rata-rata weighted score semua klausul,
       di-scale naik jika ada banyak klausul Tinggi.

    Scaling factor:
    - Jika ≥ 3 klausul Tinggi → skor × 1.2 (capped at 100)
    - Jika ≥ 5 klausul Tinggi → skor × 1.4 (capped at 100)

    Args:
        risk_clauses: Hasil dari analyzer.analyze_document().

    Returns:
        Integer 0–100. 0 = tidak ada risiko, 100 = risiko tertinggi.
    """
    if not risk_clauses:
        return 0

    total_weighted = 0.0
    high_risk_count = 0

    for clause in risk_clauses:
        weight = RISK_LEVEL_WEIGHTS.get(clause.risk_level, 0.0)
        confidence = max(0.0, min(1.0, clause.confidence))
        clause_score = weight * confidence * 100
        total_weighted += clause_score

        if clause.risk_level == "Tinggi":
            high_risk_count += 1

    # Rata-rata weighted score
    avg_score = total_weighted / len(risk_clauses)

    # Scaling factor berdasarkan jumlah klausul Tinggi
    if high_risk_count >= 5:
        avg_score *= 1.4
    elif high_risk_count >= 3:
        avg_score *= 1.2

    # Clamp ke 0–100 dan bulatkan ke integer
    final_score = int(round(max(0.0, min(100.0, avg_score))))

    logger.info(
        "Risk score dihitung: %d (dari %d klausul, %d Tinggi).",
        final_score,
        len(risk_clauses),
        high_risk_count,
    )

    return final_score
