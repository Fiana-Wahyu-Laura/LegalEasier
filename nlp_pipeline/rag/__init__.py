"""rag — LegalEasier NLP Pipeline.

Modul RAG (Retrieval-Augmented Generation) berisi:
    1. chunker.py      → LangChain text splitter (512 tokens, overlap 50)
    2. embedder.py     → sentence-transformers embeddings
    3. vector_store.py → ChromaDB operations (store & delete)
    4. retriever.py    → semantic search untuk RAG context
"""
