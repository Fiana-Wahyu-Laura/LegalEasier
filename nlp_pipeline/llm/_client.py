"""
llm/_client.py - LegalEasier NLP Pipeline
Shared LLM client (Claude primary, NVIDIA NIM fallback).

Optimizations:
- Client singletons (connection pooling, no per-call instantiation)
- Exponential backoff retry for transient API errors (429, 500, 503)
- LRU response cache for identical prompts
- Configurable temperature, max_tokens, timeout per use case
"""

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Iterable, Literal

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response cache (LRU)
# ---------------------------------------------------------------------------

_response_cache: OrderedDict[str, str] = OrderedDict()


def _cache_key(system_prompt: str, user_prompt: str) -> str:
    """Generate cache key dari hash system + user prompt."""
    combined = f"{system_prompt}|||{user_prompt}"
    return hashlib.sha256(combined.encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    """Ambil response dari cache jika ada."""
    if not settings.llm_cache_enabled:
        return None
    if key in _response_cache:
        _response_cache.move_to_end(key)
        return _response_cache[key]
    return None


def _cache_put(key: str, value: str) -> None:
    """Simpan response ke cache."""
    if not settings.llm_cache_enabled:
        return
    _response_cache[key] = value
    _response_cache.move_to_end(key)
    while len(_response_cache) > settings.llm_cache_max_size:
        _response_cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Client singletons
# ---------------------------------------------------------------------------

_claude_client = None
_nim_client = None


def _get_claude_client():
    """Return singleton Anthropic client."""
    global _claude_client
    if _claude_client is None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Package 'anthropic' belum terinstall. Jalankan: pip install anthropic"
            ) from exc
        if not settings.claude_api_key:
            raise RuntimeError("CLAUDE_API_KEY belum di-set di .env.")
        _claude_client = anthropic.Anthropic(
            api_key=settings.claude_api_key,
            timeout=settings.llm_timeout_seconds,
        )
    return _claude_client


def _get_nim_client():
    """Return singleton OpenAI-compatible client for NVIDIA NIM."""
    global _nim_client
    if _nim_client is None:
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "Package 'openai' belum terinstall. Jalankan: pip install openai"
            ) from exc
        if not settings.nim_api_key:
            raise RuntimeError("NIM_API_KEY belum di-set di .env.")
        _nim_client = openai.OpenAI(
            api_key=settings.nim_api_key,
            base_url=settings.nim_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    return _nim_client


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503}
_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


def _is_retryable(exc: Exception) -> bool:
    """Check if exception is retryable (transient API error)."""
    exc_str = str(exc).lower()
    # Check for rate limit or server errors
    for code in _RETRYABLE_STATUS_CODES:
        if str(code) in exc_str:
            return True
    if "rate" in exc_str and "limit" in exc_str:
        return True
    if "timeout" in exc_str or "timed out" in exc_str:
        return True
    return False


def _retry_call(fn, *args, **kwargs) -> str:
    """Call fn with exponential backoff retry on transient errors."""
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES and _is_retryable(exc):
                delay = _BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "LLM call gagal (attempt %d/%d): %s. Retry dalam %.1fs...",
                    attempt, _MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Internal call functions
# ---------------------------------------------------------------------------

UseCaseType = Literal["analysis", "chat", "translation"]


def _get_llm_params(use_case: UseCaseType) -> dict:
    """Get temperature and max_tokens based on use case."""
    if use_case == "analysis":
        return {
            "temperature": settings.llm_temperature_analysis,
            "max_tokens": settings.llm_max_tokens_analysis,
        }
    elif use_case == "chat":
        return {
            "temperature": settings.llm_temperature_chat,
            "max_tokens": settings.llm_max_tokens_chat,
        }
    else:  # translation
        return {
            "temperature": settings.llm_temperature_analysis,
            "max_tokens": 1024,
        }


def _call_claude(
    system_prompt: str,
    user_prompt: str,
    use_case: UseCaseType = "analysis",
) -> str:
    """Panggil Claude API (primary LLM)."""
    import anthropic

    client = _get_claude_client()
    params = _get_llm_params(use_case)

    def _do_call():
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    try:
        return _retry_call(_do_call)
    except anthropic.APIError as exc:
        raise RuntimeError(f"Claude API error: {exc}") from exc


def _call_claude_with_messages(
    system_prompt: str,
    messages: list[dict[str, str]],
    use_case: UseCaseType = "chat",
) -> str:
    """Panggil Claude API dengan multi-turn messages."""
    import anthropic

    client = _get_claude_client()
    params = _get_llm_params(use_case)

    def _do_call():
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            system=system_prompt,
            messages=messages,
        )
        return message.content[0].text

    try:
        return _retry_call(_do_call)
    except anthropic.APIError as exc:
        raise RuntimeError(f"Claude API error: {exc}") from exc


def _call_nim(
    system_prompt: str,
    user_prompt: str,
    use_case: UseCaseType = "analysis",
) -> str:
    """Panggil NVIDIA NIM API (fallback LLM, OpenAI-compatible)."""
    import openai

    client = _get_nim_client()
    params = _get_llm_params(use_case)

    def _do_call():
        response = client.chat.completions.create(
            model=settings.nim_model,
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    try:
        return _retry_call(_do_call)
    except openai.APIError as exc:
        raise RuntimeError(f"NIM API error: {exc}") from exc


def _call_nim_with_messages(
    system_prompt: str,
    messages: list[dict[str, str]],
    use_case: UseCaseType = "chat",
) -> str:
    """Panggil NVIDIA NIM API dengan multi-turn messages."""
    import openai

    client = _get_nim_client()
    params = _get_llm_params(use_case)

    def _do_call():
        response = client.chat.completions.create(
            model=settings.nim_model,
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content or ""

    try:
        return _retry_call(_do_call)
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_llm(
    system_prompt: str,
    user_prompt: str,
    use_case: UseCaseType = "analysis",
    use_cache: bool = True,
) -> str:
    """Panggil LLM dengan fallback: Claude → NVIDIA NIM.

    Args:
        system_prompt: System prompt untuk LLM.
        user_prompt: User prompt untuk LLM.
        use_case: 'analysis', 'chat', atau 'translation' — menentukan temperature & max_tokens.
        use_cache: Gunakan cache jika enabled di settings.

    Returns:
        Response text dari LLM.
    """
    # Check cache
    if use_cache:
        key = _cache_key(system_prompt, user_prompt)
        cached = _cache_get(key)
        if cached is not None:
            logger.info("LLM response ditemukan di cache.")
            return cached

    result = None

    if settings.claude_api_key:
        try:
            logger.info("Memanggil Claude API (primary)...")
            result = _call_claude(system_prompt, user_prompt, use_case)
        except RuntimeError as exc:
            logger.warning("Claude API gagal: %s. Mencoba fallback NVIDIA NIM...", exc)

    if result is None and settings.nim_api_key:
        try:
            logger.info("Memanggil NVIDIA NIM (fallback)...")
            result = _call_nim(system_prompt, user_prompt, use_case)
        except RuntimeError as exc:
            logger.error("NIM fallback juga gagal: %s", exc)
            raise

    if result is None:
        raise RuntimeError(
            "Tidak ada LLM API key yang tersedia. "
            "Set CLAUDE_API_KEY atau NIM_API_KEY di .env."
        )

    # Store in cache
    if use_cache:
        _cache_put(key, result)

    return result


def call_llm_with_history(
    system_prompt: str,
    messages: list[dict[str, str]],
    use_case: UseCaseType = "chat",
) -> str:
    """Panggil LLM multi-turn dengan fallback: Claude → NVIDIA NIM.

    History/chat calls are NOT cached because they are conversational.
    """
    normalized_messages = _normalize_messages(messages)

    if settings.claude_api_key:
        try:
            logger.info("Memanggil Claude API (primary) dengan history...")
            return _call_claude_with_messages(system_prompt, normalized_messages, use_case)
        except RuntimeError as exc:
            logger.warning("Claude API gagal: %s. Mencoba fallback NVIDIA NIM...", exc)

    if settings.nim_api_key:
        try:
            logger.info("Memanggil NVIDIA NIM (fallback) dengan history...")
            return _call_nim_with_messages(system_prompt, normalized_messages, use_case)
        except RuntimeError as exc:
            logger.error("NIM fallback juga gagal: %s", exc)
            raise

    raise RuntimeError(
        "Tidak ada LLM API key yang tersedia. "
        "Set CLAUDE_API_KEY atau NIM_API_KEY di .env."
    )
