"""
llm/_client.py - LegalEasier NLP Pipeline
Shared LLM client (Claude primary, NVIDIA NIM fallback).
"""

import logging
from typing import Iterable

from core.config import settings

logger = logging.getLogger(__name__)


def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """Panggil Claude API (primary LLM)."""
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "Package 'anthropic' belum terinstall. Jalankan: pip install anthropic"
        ) from exc

    if not settings.claude_api_key:
        raise RuntimeError("CLAUDE_API_KEY belum di-set di .env.")

    client = anthropic.Anthropic(api_key=settings.claude_api_key)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except anthropic.APIError as exc:
        raise RuntimeError(f"Claude API error: {exc}") from exc


def _call_claude_with_messages(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    """Panggil Claude API dengan multi-turn messages."""
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "Package 'anthropic' belum terinstall. Jalankan: pip install anthropic"
        ) from exc

    if not settings.claude_api_key:
        raise RuntimeError("CLAUDE_API_KEY belum di-set di .env.")

    client = anthropic.Anthropic(api_key=settings.claude_api_key)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )
        return message.content[0].text
    except anthropic.APIError as exc:
        raise RuntimeError(f"Claude API error: {exc}") from exc


def _call_nim(system_prompt: str, user_prompt: str) -> str:
    """Panggil NVIDIA NIM API (fallback LLM, OpenAI-compatible)."""
    try:
        import openai
    except ImportError as exc:
        raise RuntimeError(
            "Package 'openai' belum terinstall. Jalankan: pip install openai"
        ) from exc

    if not settings.nim_api_key:
        raise RuntimeError("NIM_API_KEY belum di-set di .env.")

    client = openai.OpenAI(
        api_key=settings.nim_api_key,
        base_url=settings.nim_base_url,
    )

    try:
        response = client.chat.completions.create(
            model=settings.nim_model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
    except openai.APIError as exc:
        raise RuntimeError(f"NIM API error: {exc}") from exc


def _call_nim_with_messages(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    """Panggil NVIDIA NIM API dengan multi-turn messages."""
    try:
        import openai
    except ImportError as exc:
        raise RuntimeError(
            "Package 'openai' belum terinstall. Jalankan: pip install openai"
        ) from exc

    if not settings.nim_api_key:
        raise RuntimeError("NIM_API_KEY belum di-set di .env.")

    client = openai.OpenAI(
        api_key=settings.nim_api_key,
        base_url=settings.nim_base_url,
    )

    try:
        response = client.chat.completions.create(
            model=settings.nim_model,
            max_tokens=4096,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content or ""
    except openai.APIError as exc:
        raise RuntimeError(f"NIM API error: {exc}") from exc


def _normalize_messages(messages: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        role = (message.get("role") or "").strip()
        content = (message.get("content") or "").strip()
        if role not in {"user", "assistant"}:
            raise ValueError("role harus 'user' atau 'assistant'.")
        if not content:
            raise ValueError("content pesan tidak boleh kosong.")
        normalized.append({"role": role, "content": content})
    if not normalized:
        raise ValueError("messages tidak boleh kosong.")
    return normalized


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Panggil LLM dengan fallback: Claude → NVIDIA NIM."""
    if settings.claude_api_key:
        try:
            logger.info("Memanggil Claude API (primary)...")
            return _call_claude(system_prompt, user_prompt)
        except RuntimeError as exc:
            logger.warning("Claude API gagal: %s. Mencoba fallback NVIDIA NIM...", exc)

    if settings.nim_api_key:
        try:
            logger.info("Memanggil NVIDIA NIM (fallback)...")
            return _call_nim(system_prompt, user_prompt)
        except RuntimeError as exc:
            logger.error("NIM fallback juga gagal: %s", exc)
            raise

    raise RuntimeError(
        "Tidak ada LLM API key yang tersedia. "
        "Set CLAUDE_API_KEY atau NIM_API_KEY di .env."
    )


def call_llm_with_history(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    """Panggil LLM multi-turn dengan fallback: Claude → NVIDIA NIM."""
    normalized_messages = _normalize_messages(messages)

    if settings.claude_api_key:
        try:
            logger.info("Memanggil Claude API (primary) dengan history...")
            return _call_claude_with_messages(system_prompt, normalized_messages)
        except RuntimeError as exc:
            logger.warning("Claude API gagal: %s. Mencoba fallback NVIDIA NIM...", exc)

    if settings.nim_api_key:
        try:
            logger.info("Memanggil NVIDIA NIM (fallback) dengan history...")
            return _call_nim_with_messages(system_prompt, normalized_messages)
        except RuntimeError as exc:
            logger.error("NIM fallback juga gagal: %s", exc)
            raise

    raise RuntimeError(
        "Tidak ada LLM API key yang tersedia. "
        "Set CLAUDE_API_KEY atau NIM_API_KEY di .env."
    )
