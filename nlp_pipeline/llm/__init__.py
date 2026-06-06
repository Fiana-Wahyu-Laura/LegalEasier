"""
llm/ — LegalEasier NLP Pipeline
Modul LLM untuk analisis risiko, terjemahan bahasa hukum, dan RAG chatbot.

Sprint 3:
    - prompts.py      → semua prompt template untuk LLM
    - analyzer.py     → deteksi dan klasifikasi klausul berisiko
    - translator.py   → terjemahan klausul ke bahasa sederhana
    - risk_scorer.py  → skor risiko 0–100 berbasis weighted average

Sprint 4:
    - chatbot.py      → RAG chatbot berbasis LangGraph + ChromaDB
"""

from llm.analyzer import AnalysisResult, RiskClause, analyze_document
from llm.chatbot import ChatResult, chat_with_document
from llm.risk_scorer import compute_risk_score
from llm.translator import translate_clause, translate_clauses_batch

__all__ = [
    "AnalysisResult",
    "RiskClause",
    "analyze_document",
    "ChatResult",
    "chat_with_document",
    "compute_risk_score",
    "translate_clause",
    "translate_clauses_batch",
]
