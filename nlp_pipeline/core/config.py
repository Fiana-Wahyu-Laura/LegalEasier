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
    nim_model: str = "openai/gpt-oss-120b"

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


settings = Settings()
