"""
inspect_chroma.py — Lihat isi ChromaDB lokal.
Jalankan: python inspect_chroma.py
Tambahkan argumen --full-vectors untuk menampilkan seluruh nilai vector.
"""

import sys
import chromadb
from chromadb.config import Settings

CHROMA_PATH = "./chroma_db"

# Berapa banyak elemen vector yang ditampilkan dalam mode ringkas
VECTOR_PREVIEW_N = 8


def format_vector(vec: list[float], full: bool) -> str:
    """Format vector untuk ditampilkan. Mode ringkas hanya tampil N elemen pertama."""
    if full:
        return str(vec)
    preview = vec[:VECTOR_PREVIEW_N]
    return f"[{', '.join(f'{v:.4f}' for v in preview)}, ...]  ({len(vec)} dims)"


def main():
    show_full_vectors = "--full-vectors" in sys.argv

    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )

    collections = client.list_collections()
    print(f"\n{'='*60}")
    print(f"ChromaDB di: {CHROMA_PATH}")
    print(f"Total collections: {len(collections)}")
    print(f"{'='*60}\n")

    if not collections:
        print("(kosong — belum ada dokumen yang diproses)\n")
        return

    for col in collections:
        count = col.count()
        print(f"📄 {col.name}")
        print(f"   Chunks: {count}")

        if count == 0:
            print()
            continue

        # Ambil semua data + embeddings
        data = col.get(include=["embeddings", "documents", "metadatas"])
        for i, (doc_id, text, meta, emb) in enumerate(
            zip(data["ids"], data["documents"], data["metadatas"], data["embeddings"] or [])
        ):
            preview = text[:120].replace("\n", " ")
            print(f"   [{i}] {doc_id}")
            print(f"       meta: {meta}")
            print(f"       text: {preview}...")
            if emb:
                print(f"       vector: {format_vector(emb, show_full_vectors)}")
            else:
                print(f"       vector: (tidak ada)")
        print()


if __name__ == "__main__":
    main()
