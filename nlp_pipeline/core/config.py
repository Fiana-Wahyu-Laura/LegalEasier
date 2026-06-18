"""
core/config.py — LegalEasier NLP Pipeline
Semua konfigurasi dibaca dari .env via pydantic-settings.
Jangan pernah hardcode nilai apapun di luar file ini.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi NLP Pipeline dari environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM API Keys (Sprint 3+)
    claude_api_key: str = ""
    openai_api_key: str = ""
    nim_api_key: str = ""

    # NVIDIA NIM (OpenAI-compatible)
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"

    # ChromaDB (Sprint 2+)
    chroma_persist_dir: str = "./chroma_db"

    # OCR
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # Service config
    service_host: str = "0.0.0.0"
    service_port: int = 8001

    # OCR config
    tesseract_lang: str = "ind+eng"          # Indonesian + English
    min_text_length: int = 50                # Threshold: teks dianggap valid jika >= 50 karakter
    max_file_size_bytes: int = 25 * 1024 * 1024  # 25MB (CLAUDE.md §8)

    # ── Embedding model ──────────────────────────────────────────────────
    embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # ── Chunking ─────────────────────────────────────────────────────────
    chunk_size: int = 1024           # karakter per chunk (was 512)
    chunk_overlap: int = 128         # overlap antar chunk (was 50)

    # ── LLM tuning ───────────────────────────────────────────────────────
    llm_max_tokens_analysis: int = 8192   # output token limit for document analysis
    llm_max_tokens_chat: int = 4096       # output token limit for chatbot
    llm_temperature_analysis: float = 0.1  # deterministic for legal analysis
    llm_temperature_chat: float = 0.3      # slightly creative for chatbot
    llm_timeout_seconds: int = 120         # max wait for LLM response

    # ── LLM response cache ───────────────────────────────────────────────
    llm_cache_enabled: bool = True
    llm_cache_max_size: int = 100

    # ── Retrieval ────────────────────────────────────────────────────────
    retrieval_top_k: int = 8         # default chunks retrieved (was 5)


settings = Settings()
