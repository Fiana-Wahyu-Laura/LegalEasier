"""
llm/translator.py — LegalEasier NLP Pipeline
Terjemahan klausul hukum ke bahasa sederhana Indonesia (Sprint 3).

Tugasnya:
    Terima satu klausul hukum → kembalikan penjelasan dalam bahasa
    Indonesia yang mudah dipahami oleh masyarakat umum (bukan pengacara).

Rules:
- Output harus dalam bahasa Indonesia.
- Jangan tambahkan opini hukum — hanya parafrase/penjelasan.
- Wajib sertakan disclaimer pada setiap output.
- Primary LLM: Claude API. Fallback: NVIDIA NIM.

Aturan kode:
- Tidak ada hardcoded API key.
- Semua fungsi harus punya type hints.
- Tidak ada bare except.
"""

import logging

from llm._client import call_llm
from llm.prompts import (
    TRANSLATION_SYSTEM_PROMPT,
    build_translation_user_prompt,
)

logger = logging.getLogger(__name__)


def translate_clause(clause_text: str, context: str = "") -> str:
    """Terjemahkan satu klausul hukum ke bahasa sederhana Indonesia.

    Menggunakan LLM (Claude primary, NVIDIA NIM fallback) untuk menjelaskan
    klausul dalam bahasa yang mudah dipahami masyarakat umum.

    Args:
        clause_text: Teks klausul hukum yang akan diterjemahkan.
        context: Konteks tambahan dari dokumen (opsional).

    Returns:
        Penjelasan dalam bahasa Indonesia sederhana.
        Jika LLM gagal, kembalikan string kosong.
    """
    if not clause_text or not clause_text.strip():
        logger.warning("clause_text kosong, return string kosong.")
        return ""

    user_prompt = build_translation_user_prompt(clause_text, context)

    try:
        result = call_llm(TRANSLATION_SYSTEM_PROMPT, user_prompt)
        return result.strip()
    except RuntimeError as exc:
        logger.error("Gagal menerjemahkan klausul: %s", exc)
        return ""


def translate_clauses_batch(
    clauses: list[str], context: str = ""
) -> list[str]:
    """Terjemahkan banyak klausul sekaligus.

    Untuk saat ini memanggil translate_clause satu per satu.
    Di masa depan bisa dioptimasi dengan batch API call.

    Args:
        clauses: List teks klausul hukum.
        context: Konteks tambahan dari dokumen (opsional).

    Returns:
        List penjelasan dalam bahasa Indonesia sederhana, urut sesuai input.
    """
    results: list[str] = []
    for i, clause in enumerate(clauses):
        logger.info("Translating clause %d/%d...", i + 1, len(clauses))
        translated = translate_clause(clause, context)
        results.append(translated)
    return results
