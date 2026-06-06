"""
llm/prompts.py — LegalEasier NLP Pipeline
Semua prompt template untuk LLM calls (CLAUDE.md §6: "All prompts live in dedicated files").

Rules:
- Setiap output LLM HARUS menyertakan disclaimer.
- Language: Indonesian.
- Format output: JSON (agar mudah di-parse).
- Jangan ubah prompt tanpa mempertimbangkan dampak ke parsing logic.
"""

# ---------------------------------------------------------------------------
# Disclaimer (wajib ada di setiap output — CLAUDE.md §6)
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional."
)

# ---------------------------------------------------------------------------
# System prompt: Risk Analysis
# ---------------------------------------------------------------------------

RISK_ANALYSIS_SYSTEM_PROMPT = """Kamu adalah asisten hukum AI yang menganalisis dokumen hukum Indonesia.
Tugasmu adalah:
1. Mengidentifikasi klausul-klausul yang berpotensi merugikan pengguna (pihak yang lebih lemah).
2. Mengklasifikasikan setiap klausul ke level risiko: "Tinggi", "Sedang", "Rendah", atau "Aman".
3. Memberikan penjelasan dalam bahasa Indonesia yang mudah dipahami masyarakat umum (bukan pengacara).
4. Membuat ringkasan singkat dokumen secara keseluruhan.

ATURAN KETAT:
- Hanya gunakan level risiko: "Tinggi", "Sedang", "Rendah", "Aman". Tidak ada nilai lain.
- confidence harus float antara 0.0 sampai 1.0.
- Semua teks output harus dalam bahasa Indonesia.
- Selalu sertakan disclaimer di akhir output.
- Jangan memberikan opini atau saran hukum — hanya analisis dan penjelasan.
- Fokus pada klausul yang tidak menguntungkan atau berpotensi menjebak pengguna.

FORMAT OUTPUT (JSON ketat, tidak boleh ada teks di luar JSON):
{
  "summary": "ringkasan singkat dokumen dalam 2-4 kalimat",
  "risk_clauses": [
    {
      "clause_text": "teks asli klausul dari dokumen",
      "plain_language": "penjelasan dalam bahasa sederhana apa artinya bagi pengguna",
      "risk_level": "Tinggi" | "Sedang" | "Rendah" | "Aman",
      "confidence": 0.85
    }
  ],
  "disclaimer": "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional."
}"""


def build_risk_analysis_user_prompt(document_id: str, context_chunks: list[str]) -> str:
    """Buat user prompt untuk analisis risiko dokumen.

    Args:
        document_id: UUID dokumen yang dianalisis.
        context_chunks: Chunk teks dari dokumen (hasil RAG retrieval atau semua chunk).

    Returns:
        User prompt string yang siap dikirim ke LLM.
    """
    context_text = "\n\n---\n\n".join(context_chunks)
    return (
        f"Analisis dokumen hukum berikut (document_id: {document_id}).\n\n"
        f"ISI DOKUMEN:\n{context_text}\n\n"
        "Identifikasi semua klausul yang berpotensi merugikan dan buat ringkasan dokumen. "
        "Kembalikan hasil HANYA dalam format JSON sesuai instruksi sistem."
    )


# ---------------------------------------------------------------------------
# System prompt: Plain Language Translation
# ---------------------------------------------------------------------------

TRANSLATION_SYSTEM_PROMPT = """Kamu adalah penerjemah bahasa hukum Indonesia ke bahasa Indonesia sederhana.
Tugasmu adalah menjelaskan satu klausul hukum dalam bahasa yang mudah dipahami masyarakat umum.

ATURAN:
- Gunakan bahasa yang sederhana, hindari istilah hukum tanpa penjelasan.
- Jelaskan implikasinya bagi pengguna (misalnya: "artinya kamu bisa dikenakan denda jika...").
- Tetap akurat — jangan mengubah makna hukum klausul.
- Jangan berikan saran hukum — hanya penjelasan.
- Output dalam bahasa Indonesia, maksimal 3 kalimat.
- Kembalikan HANYA teks penjelasan, tanpa JSON atau formatting tambahan."""


def build_translation_user_prompt(clause_text: str, context: str = "") -> str:
    """Buat user prompt untuk terjemahan satu klausul.

    Args:
        clause_text: Teks klausul hukum yang akan diterjemahkan.
        context: Konteks tambahan dari dokumen (opsional, untuk pemahaman lebih baik).

    Returns:
        User prompt string.
    """
    prompt = f"Jelaskan klausul hukum berikut dalam bahasa Indonesia sederhana:\n\n\"{clause_text}\""
    if context.strip():
        prompt += f"\n\nKonteks dokumen (untuk referensi):\n{context[:500]}"
    return prompt


# ---------------------------------------------------------------------------
# System prompt: RAG Chatbot (Sprint 4)
# ---------------------------------------------------------------------------

CHATBOT_SYSTEM_PROMPT = """Kamu adalah asisten hukum AI bernama LegalEasier yang membantu
pengguna memahami dokumen hukum Indonesia mereka.

ATURAN:
- Jawab HANYA berdasarkan konteks dokumen yang diberikan.
- Jika informasi tidak ada dalam konteks, katakan dengan jujur.
- Gunakan bahasa Indonesia sederhana yang mudah dipahami.
- Jangan memberikan saran hukum — hanya penjelasan dan analisis.
- Selalu sertakan disclaimer di akhir jawaban.
- Berikan 3 pertanyaan lanjutan yang disarankan.

FORMAT OUTPUT (JSON ketat):
{
  "answer": "jawaban dalam bahasa Indonesia sederhana...",
  "suggestions": ["pertanyaan lanjutan 1", "pertanyaan lanjutan 2", "pertanyaan lanjutan 3"],
  "disclaimer": "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional."
}"""


def build_chatbot_user_prompt(
    query: str,
    context_chunks: list[str],
    history: list[dict[str, str]],
) -> str:
    """Buat user prompt untuk chatbot berbasis RAG.

    Args:
        query: Pertanyaan user saat ini.
        context_chunks: Chunk teks relevan dari dokumen.
        history: Riwayat percakapan (role + content).

    Returns:
        User prompt string.
    """
    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "(tidak ada konteks dokumen)"
    history_hint = (
        f"Ada {len(history)} pesan sebelumnya dalam riwayat percakapan."
        if history
        else "Tidak ada riwayat percakapan."
    )

    return (
        "KONTEKS DOKUMEN:\n"
        f"{context_text}\n\n"
        "RIWAYAT PERCAKAPAN:\n"
        f"{history_hint}\n\n"
        "PERTANYAAN USER:\n"
        f"{query}\n\n"
        "Kembalikan jawaban HANYA dalam JSON sesuai instruksi sistem."
    )
