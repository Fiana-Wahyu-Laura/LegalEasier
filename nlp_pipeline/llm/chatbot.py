"""
llm/chatbot.py - LegalEasier NLP Pipeline
RAG chatbot berbasis LangGraph + ChromaDB (Sprint 4).
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from llm._client import call_llm_with_history
from llm.prompts import CHATBOT_SYSTEM_PROMPT, DISCLAIMER, build_chatbot_user_prompt
from rag.retriever import DEFAULT_TOP_K, retrieve_relevant_chunks

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20
MAX_SUGGESTIONS = 3
MAX_TOP_K = 10


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ChatState(TypedDict, total=False):
    document_id: str
    query: str
    history: list[ChatMessage]
    top_k: int
    context_chunks: list[str]
    response: str
    suggestions: list[str]
    disclaimer: str
    error: str


@dataclass
class ChatResult:
    """Hasil chat untuk satu pertanyaan user."""

    answer: str
    suggestions: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER
    context_chunks_used: int = 0
    context_chunks: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing & validation helpers
# ---------------------------------------------------------------------------


def _extract_json_from_response(raw: str) -> dict:
    """Ekstrak JSON dari response LLM (toleransi code block)."""
    text = raw.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Gagal meng-extract JSON dari response LLM.")


def _normalize_suggestions(raw_suggestions: object) -> list[str]:
    if not isinstance(raw_suggestions, list):
        return []

    cleaned: list[str] = []
    for item in raw_suggestions:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())

    return cleaned[:MAX_SUGGESTIONS]


def _ensure_three_suggestions(suggestions: list[str]) -> list[str]:
    defaults = [
        "Apa ringkasan singkat dokumen ini?",
        "Apa kewajiban utama pihak-pihak di dokumen?",
        "Apa sanksi jika ada pelanggaran?",
    ]
    filled = suggestions[:MAX_SUGGESTIONS]
    for suggestion in defaults:
        if len(filled) >= MAX_SUGGESTIONS:
            break
        if suggestion not in filled:
            filled.append(suggestion)
    return filled


def _parse_chatbot_response(raw: str) -> tuple[str, list[str], str]:
    data = _extract_json_from_response(raw)

    answer = str(data.get("answer", "")).strip()
    if not answer:
        raise ValueError("answer tidak boleh kosong.")

    suggestions = _normalize_suggestions(data.get("suggestions", []))
    disclaimer = str(data.get("disclaimer", "")).strip() or DISCLAIMER

    return answer, suggestions, disclaimer


def _normalize_history(history: list[ChatMessage]) -> list[ChatMessage]:
    cleaned: list[ChatMessage] = []
    for item in history:
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})

    if len(cleaned) > MAX_HISTORY_MESSAGES:
        cleaned = cleaned[-MAX_HISTORY_MESSAGES:]

    return cleaned


def _build_messages(
    history: list[ChatMessage],
    user_prompt: str,
) -> list[ChatMessage]:
    return [*history, {"role": "user", "content": user_prompt}]


def _fallback_answer(reason: str) -> str:
    return (
        "Maaf, saya belum bisa menjawab pertanyaan ini. "
        f"{reason}"
    )


# ---------------------------------------------------------------------------
# LangGraph nodes
# ---------------------------------------------------------------------------


def retrieve_context(state: ChatState) -> ChatState:
    document_id = state.get("document_id", "")
    query = state.get("query", "")
    top_k = state.get("top_k", DEFAULT_TOP_K)

    try:
        result = retrieve_relevant_chunks(
            document_id=document_id,
            query=query,
            top_k=top_k,
        )
    except Exception as exc:
        logger.error("[%s] Retrieval gagal: %s", document_id, exc)
        return {"context_chunks": [], "error": str(exc)}

    return {"context_chunks": result.chunks}


def generate_response(state: ChatState) -> ChatState:
    document_id = state.get("document_id", "")
    query = state.get("query", "")
    history = state.get("history", [])
    context_chunks = state.get("context_chunks", [])

    if not context_chunks:
        answer = _fallback_answer(
            "Saya belum menemukan bagian dokumen yang relevan. "
            "Coba ubah pertanyaan atau pastikan dokumen sudah diproses."
        )
        return {
            "response": answer,
            "suggestions": _ensure_three_suggestions([]),
            "disclaimer": DISCLAIMER,
        }

    user_prompt = build_chatbot_user_prompt(query, context_chunks, history)
    messages = _build_messages(history, user_prompt)

    try:
        raw_response = call_llm_with_history(CHATBOT_SYSTEM_PROMPT, messages)
        answer, suggestions, disclaimer = _parse_chatbot_response(raw_response)
        return {
            "response": answer,
            "suggestions": _ensure_three_suggestions(suggestions),
            "disclaimer": disclaimer,
        }
    except (RuntimeError, ValueError) as exc:
        logger.error("[%s] Chatbot gagal: %s", document_id, exc)
        answer = _fallback_answer(
            "Terjadi kendala saat memproses pertanyaan. Silakan coba lagi."
        )
        return {
            "response": answer,
            "suggestions": _ensure_three_suggestions([]),
            "disclaimer": DISCLAIMER,
        }


# ---------------------------------------------------------------------------
# Graph builder & public API
# ---------------------------------------------------------------------------


def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_response", generate_response)
    graph.set_entry_point("retrieve_context")
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("generate_response", END)
    return graph.compile()


_CHAT_GRAPH = build_chat_graph()


def chat_with_document(
    document_id: str,
    query: str,
    history: list[ChatMessage] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> ChatResult:
    """Jalankan RAG chatbot untuk satu dokumen dan satu query."""
    if not document_id or not document_id.strip():
        raise ValueError("document_id tidak boleh kosong.")
    if not query or not query.strip():
        raise ValueError("query tidak boleh kosong.")
    if not (1 <= top_k <= MAX_TOP_K):
        raise ValueError("top_k harus antara 1 dan 10.")

    normalized_history = _normalize_history(history or [])

    state = {
        "document_id": document_id,
        "query": query.strip(),
        "history": normalized_history,
        "top_k": top_k,
    }

    final_state = _CHAT_GRAPH.invoke(state)
    answer = str(final_state.get("response", "")).strip()
    suggestions = final_state.get("suggestions", []) or []
    disclaimer = str(final_state.get("disclaimer", "")).strip() or DISCLAIMER
    context_chunks = final_state.get("context_chunks", []) or []

    return ChatResult(
        answer=answer,
        suggestions=suggestions,
        disclaimer=disclaimer,
        context_chunks_used=len(context_chunks),
        context_chunks=context_chunks,
    )
