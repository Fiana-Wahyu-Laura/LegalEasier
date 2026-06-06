"""
tests/test_chatbot.py - LegalEasier NLP Pipeline
Unit tests untuk chatbot RAG Sprint 4.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from core.config import settings
from llm._client import call_llm, call_llm_with_history
from llm.chatbot import (
    ChatResult,
    _parse_chatbot_response,
    chat_with_document,
)
from llm.prompts import (
    CHATBOT_SYSTEM_PROMPT,
    DISCLAIMER,
    build_chatbot_user_prompt,
)


# ═══════════════════════════════════════════════════════════════════════════
# Tests: prompts.py
# ═══════════════════════════════════════════════════════════════════════════


class TestChatbotPrompt:
    """Tests untuk prompt chatbot."""

    def test_chatbot_system_prompt_has_required_elements(self) -> None:
        assert "JSON" in CHATBOT_SYSTEM_PROMPT
        assert "disclaimer" in CHATBOT_SYSTEM_PROMPT.lower()
        assert "pertanyaan lanjutan" in CHATBOT_SYSTEM_PROMPT

    def test_build_chatbot_user_prompt_contains_query_and_context(self) -> None:
        prompt = build_chatbot_user_prompt(
            "Apa kewajiban penyewa?",
            ["Chunk 1", "Chunk 2"],
            [],
        )
        assert "Apa kewajiban penyewa" in prompt
        assert "Chunk 1" in prompt
        assert "Chunk 2" in prompt

    def test_build_chatbot_user_prompt_mentions_history_count(self) -> None:
        prompt = build_chatbot_user_prompt(
            "Apa sanksinya?",
            ["Chunk"],
            [{"role": "user", "content": "Halo"}],
        )
        assert "1 pesan" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# Tests: chatbot response parsing
# ═══════════════════════════════════════════════════════════════════════════


class TestChatResponseParsing:
    """Tests untuk parsing response chatbot."""

    def test_valid_response(self) -> None:
        raw = json.dumps({
            "answer": "Jawaban singkat.",
            "suggestions": ["A", "B", "C"],
            "disclaimer": DISCLAIMER,
        })
        answer, suggestions, disclaimer = _parse_chatbot_response(raw)
        assert answer == "Jawaban singkat."
        assert suggestions == ["A", "B", "C"]
        assert disclaimer == DISCLAIMER

    def test_missing_suggestions_defaults_empty(self) -> None:
        raw = json.dumps({
            "answer": "Jawaban.",
            "disclaimer": DISCLAIMER,
        })
        _, suggestions, _ = _parse_chatbot_response(raw)
        assert suggestions == []

    def test_non_list_suggestions_ignored(self) -> None:
        raw = json.dumps({
            "answer": "Jawaban.",
            "suggestions": "bukan list",
            "disclaimer": DISCLAIMER,
        })
        _, suggestions, _ = _parse_chatbot_response(raw)
        assert suggestions == []

    def test_missing_disclaimer_uses_default(self) -> None:
        raw = json.dumps({
            "answer": "Jawaban.",
            "suggestions": ["A", "B", "C"],
        })
        _, _, disclaimer = _parse_chatbot_response(raw)
        assert disclaimer == DISCLAIMER

    def test_missing_answer_raises(self) -> None:
        raw = json.dumps({"suggestions": ["A", "B", "C"]})
        with pytest.raises(ValueError, match="answer"):
            _parse_chatbot_response(raw)

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_chatbot_response("not json")


# ═══════════════════════════════════════════════════════════════════════════
# Tests: chat_with_document (LLM & retriever mocked)
# ═══════════════════════════════════════════════════════════════════════════


class TestChatWithDocument:
    """Tests untuk chat_with_document (LLM di-mock)."""

    @patch("llm.chatbot.call_llm_with_history")
    @patch("llm.chatbot.retrieve_relevant_chunks")
    def test_successful_chat(
        self, mock_retriever: MagicMock, mock_llm: MagicMock
    ) -> None:
        mock_retriever.return_value = MagicMock(chunks=["chunk-1"])
        mock_llm.return_value = json.dumps({
            "answer": "Ini jawabannya.",
            "suggestions": ["S1", "S2", "S3"],
            "disclaimer": DISCLAIMER,
        })

        result = chat_with_document(
            document_id="doc-123",
            query="Apa isi pasal 1?",
            history=[],
            top_k=5,
        )

        assert isinstance(result, ChatResult)
        assert result.answer == "Ini jawabannya."
        assert result.suggestions == ["S1", "S2", "S3"]
        assert result.context_chunks_used == 1
        mock_llm.assert_called_once()

    @patch("llm.chatbot.call_llm_with_history")
    @patch("llm.chatbot.retrieve_relevant_chunks")
    def test_history_truncated_to_max(
        self, mock_retriever: MagicMock, mock_llm: MagicMock
    ) -> None:
        mock_retriever.return_value = MagicMock(chunks=["chunk"])
        mock_llm.return_value = json.dumps({
            "answer": "Jawab.",
            "suggestions": ["S1", "S2", "S3"],
            "disclaimer": DISCLAIMER,
        })

        history = [
            {"role": "user", "content": f"u{i}"}
            for i in range(25)
        ]

        chat_with_document(
            document_id="doc-1",
            query="Q",
            history=history,
            top_k=5,
        )

        messages = mock_llm.call_args[0][1]
        assert len(messages) == 21  # 20 history + 1 user prompt

    def test_empty_document_id_raises(self) -> None:
        with pytest.raises(ValueError, match="document_id"):
            chat_with_document("", "Q")

    def test_empty_query_raises(self) -> None:
        with pytest.raises(ValueError, match="query"):
            chat_with_document("doc", " ")

    @patch("llm.chatbot.call_llm_with_history")
    @patch("llm.chatbot.retrieve_relevant_chunks")
    def test_empty_context_skips_llm(
        self, mock_retriever: MagicMock, mock_llm: MagicMock
    ) -> None:
        mock_retriever.return_value = MagicMock(chunks=[])

        result = chat_with_document(
            document_id="doc-123",
            query="Apa pasal 3?",
            history=[],
            top_k=5,
        )

        assert "belum menemukan" in result.answer
        mock_llm.assert_not_called()

    @patch("llm.chatbot.call_llm_with_history")
    @patch("llm.chatbot.retrieve_relevant_chunks")
    def test_llm_failure_returns_fallback(
        self, mock_retriever: MagicMock, mock_llm: MagicMock
    ) -> None:
        mock_retriever.return_value = MagicMock(chunks=["chunk"])
        mock_llm.side_effect = RuntimeError("LLM down")

        result = chat_with_document(
            document_id="doc-123",
            query="Apa pasal 3?",
            history=[],
            top_k=5,
        )

        assert "kendala" in result.answer

    def test_top_k_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="top_k"):
            chat_with_document("doc", "Q", top_k=0)


# ═══════════════════════════════════════════════════════════════════════════
# Tests: shared LLM client
# ═══════════════════════════════════════════════════════════════════════════


class TestLLMClient:
    """Tests untuk llm/_client.py (mocked)."""

    def test_call_llm_prefers_claude(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "claude_api_key", "key")
        monkeypatch.setattr(settings, "nim_api_key", "nim")
        with patch("llm._client._call_claude") as mock_claude, patch(
            "llm._client._call_nim"
        ) as mock_nim:
            mock_claude.return_value = "ok"
            result = call_llm("sys", "user")
            assert result == "ok"
            mock_nim.assert_not_called()

    def test_call_llm_fallback_to_nim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "claude_api_key", "key")
        monkeypatch.setattr(settings, "nim_api_key", "nim")
        with patch("llm._client._call_claude", side_effect=RuntimeError("fail")):
            with patch("llm._client._call_nim") as mock_nim:
                mock_nim.return_value = "nim-ok"
                result = call_llm("sys", "user")
                assert result == "nim-ok"

    def test_call_llm_without_keys_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "claude_api_key", "")
        monkeypatch.setattr(settings, "nim_api_key", "")
        with pytest.raises(RuntimeError, match="LLM API key"):
            call_llm("sys", "user")

    def test_call_llm_with_history_prefers_claude(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "claude_api_key", "key")
        monkeypatch.setattr(settings, "nim_api_key", "nim")
        with patch("llm._client._call_claude_with_messages") as mock_claude, patch(
            "llm._client._call_nim_with_messages"
        ) as mock_nim:
            mock_claude.return_value = "ok"
            result = call_llm_with_history(
                "sys", [{"role": "user", "content": "hi"}]
            )
            assert result == "ok"
            mock_nim.assert_not_called()

    def test_call_llm_with_history_fallback_to_nim(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "claude_api_key", "key")
        monkeypatch.setattr(settings, "nim_api_key", "nim")
        with patch(
            "llm._client._call_claude_with_messages",
            side_effect=RuntimeError("fail"),
        ):
            with patch("llm._client._call_nim_with_messages") as mock_nim:
                mock_nim.return_value = "nim-ok"
                result = call_llm_with_history(
                    "sys", [{"role": "user", "content": "hi"}]
                )
                assert result == "nim-ok"
