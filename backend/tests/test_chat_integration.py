"""
Integration tests for chat endpoint (Sprint 4) — requires real PostgreSQL.

Cara jalankan (dari direktori backend/):
    pytest tests/test_chat_integration.py -v

Prasyarat:
- PostgreSQL running di localhost:5432 (atau sesuai DATABASE_URL di .env)
- alembic upgrade head sudah dijalankan sebelumnya
- Virtual environment aktif dengan semua dependency terinstall

Perbedaan dengan unit test (test_chat.py):
- Menggunakan koneksi PostgreSQL sungguhan, bukan fake/mock DB
- Menjalankan alembic upgrade/downgrade sungguhan untuk setup/teardown tabel
- Memverifikasi data benar-benar tersimpan dan terbaca dari DB
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.main import app
from app.models.chat_message import ChatMessage
from app.models.guest_quota import GuestQuota
from app.models.document import Document
from app.models.user import User
from app.schemas.auth import AuthUser
from app.services.nlp_client import get_nlp_client

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]  # direktori backend/

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        get_settings().database_url,
    ),
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# Setup / teardown tabel via Alembic sungguhan (bukan Base.metadata.create_all)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", autouse=True)
async def apply_migrations():
    """
    Jalankan 'alembic upgrade head' sebelum semua test dimulai.
    Jalankan 'alembic downgrade base' setelah semua test selesai.

    Ini memastikan tabel dibuat dari migration file sungguhan,
    persis seperti yang terjadi di environment production.
    """
    # Upgrade
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"alembic upgrade head GAGAL.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    yield

    # Downgrade — bersihkan semua tabel setelah test session selesai
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# DB session per test
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def db_session():
    """Session baru per test. Data dibersihkan di teardown."""
    async with TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Seed: buat user + document di DB sungguhan
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def seeded_user_and_doc():
    """
    Buat 1 user dan 1 document di PostgreSQL sungguhan.
    Hapus keduanya (beserta chat_messages dan guest_quotas terkait) setelah test.
    """
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    user = User(
        id=user_id,
        firebase_uid=f"firebase-inttest-{user_id}",
        email=f"inttest-{user_id}@legaleasier.test",
        display_name="Integration Tester",
        is_active=True,
    )
    document = Document(
        id=doc_id,
        owner_id=user_id,
        filename="kontrak_integrasi.pdf",
        storage_path=f"storage/test/{doc_id}.pdf",
        status="completed",
        extracted_text="Isi kontrak kerja untuk keperluan test integrasi Sprint 4.",
    )

    now = datetime.now(timezone.utc)

    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, firebase_uid, email, display_name, is_active, created_at) "
                "VALUES (:id, :firebase_uid, :email, :display_name, :is_active, :created_at)"
            ),
            {
                "id": user_id,
                "firebase_uid": user.firebase_uid,
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "created_at": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO documents (id, owner_id, filename, storage_path, status, extracted_text, created_at, updated_at) "
                "VALUES (:id, :owner_id, :filename, :storage_path, :status, :extracted_text, :created_at, :updated_at)"
            ),
            {
                "id": doc_id,
                "owner_id": user_id,
                "filename": document.filename,
                "storage_path": document.storage_path,
                "status": document.status,
                "extracted_text": document.extracted_text,
                "created_at": now,
                "updated_at": now,
            },
        )

    yield user, document

    # Teardown — urutan penting karena FK constraint
    async with test_engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM chat_messages WHERE document_id = :doc_id"),
            {"doc_id": doc_id},
        )
        await conn.execute(
            text("DELETE FROM guest_quotas WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        await conn.execute(
            text("DELETE FROM documents WHERE id = :doc_id"),
            {"doc_id": doc_id},
        )
        await conn.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )


# ---------------------------------------------------------------------------
# Fake NLP client — tidak perlu NLP service running saat integration test
# ---------------------------------------------------------------------------


class _FakeNLPClient:
    async def chat_document(self, document_id, query, history, top_k):
        return SimpleNamespace(
            answer=f"[IntTest] Jawaban untuk: {query}",
            suggestions=[
                "Apa risiko terbesar dalam kontrak ini?",
                "Bagian mana yang paling perlu diperhatikan?",
                "Apakah ada klausul yang merugikan?",
            ],
            context_chunks_used=2,
            context_chunks=["konteks-chunk-A", "konteks-chunk-B"],
            disclaimer=(
                "Hasil ini bersifat informatif dan bukan pengganti "
                "konsultasi hukum profesional."
            ),
        )


# ---------------------------------------------------------------------------
# Helper: buat AsyncClient dengan dependency override ke real DB session
# ---------------------------------------------------------------------------


def _build_client(user: User) -> AsyncClient:
    auth_user = AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=True,
    )

    async def _override_current_user():
        return auth_user

    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    def _override_nlp_client():
        return _FakeNLPClient()

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_nlp_client] = _override_nlp_client

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# TEST 1: Kirim pesan → response 200 + ChatMessage + GuestQuota tersimpan di DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_message_persisted_to_db(seeded_user_and_doc, db_session):
    """
    Kirim pesan chat via endpoint, lalu verifikasi lewat query langsung ke
    PostgreSQL bahwa ChatMessage dan GuestQuota benar-benar tersimpan.
    """
    user, document = seeded_user_and_doc

    async with _build_client(user) as client:
        response = await client.post(
            f"/api/v1/chat/{document.id}/message",
            json={
                "message": "Apa klausul paling berisiko dalam kontrak ini?",
                "history": [],
                "top_k": 3,
            },
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    # --- Verifikasi response HTTP ---
    assert response.status_code == 200, f"Unexpected: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Chat response generated."
    assert "[IntTest]" in body["data"]["answer"]
    assert body["data"]["context_chunks_used"] == 2
    assert len(body["data"]["sources"]) == 2
    assert body["data"]["sources"][0]["text"] == "konteks-chunk-A"
    assert body["data"]["remaining_quota"] == 4  # 5 - 1
    assert "informatif" in body["data"]["disclaimer"]

    # --- Verifikasi ChatMessage tersimpan di PostgreSQL ---
    # Buka session baru supaya tidak tergantung state session sebelumnya
    async with TestSessionLocal() as verify_session:
        result = await verify_session.execute(
            text(
                "SELECT question, answer, sources_json, user_id "
                "FROM chat_messages "
                "WHERE document_id = :doc_id "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"doc_id": document.id},
        )
        row = result.fetchone()

    assert row is not None, "ChatMessage tidak tersimpan ke PostgreSQL"
    assert row.question == "Apa klausul paling berisiko dalam kontrak ini?"
    assert "[IntTest]" in row.answer
    assert str(row.user_id) == str(user.id)
    sources_list = json.loads(row.sources_json)
    assert "konteks-chunk-A" in sources_list
    assert "konteks-chunk-B" in sources_list

    # --- Verifikasi GuestQuota tersimpan di PostgreSQL ---
    async with TestSessionLocal() as verify_session:
        result = await verify_session.execute(
            text(
                "SELECT remaining_quota FROM guest_quotas WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        )
        quota_row = result.fetchone()

    assert quota_row is not None, "GuestQuota tidak tersimpan ke PostgreSQL"
    assert quota_row.remaining_quota == 4


# ---------------------------------------------------------------------------
# TEST 2: GET history → kembalikan data dari DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_history_reads_from_db(seeded_user_and_doc, db_session):
    """
    Seed ChatMessage langsung ke DB (bypass endpoint), lalu panggil
    endpoint GET /history dan verifikasi data dikembalikan dengan benar.
    """
    user, document = seeded_user_and_doc

    # Seed langsung ke DB
    msg_id = uuid.uuid4()
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO chat_messages (id, user_id, document_id, question, answer, sources_json) "
                "VALUES (:id, :user_id, :document_id, :question, :answer, :sources_json)"
            ),
            {
                "id": msg_id,
                "user_id": user.id,
                "document_id": document.id,
                "question": "Pertanyaan yang di-seed langsung",
                "answer": "Jawaban yang di-seed langsung",
                "sources_json": json.dumps(["source-X", "source-Y"]),
            },
        )

    async with _build_client(user) as client:
        response = await client.get(
            f"/api/v1/chat/{document.id}/history",
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200, f"Unexpected: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Chat history loaded."
    assert body["data"]["document_id"] == str(document.id)

    items = body["data"]["items"]
    assert len(items) >= 1

    seeded = next(
        (i for i in items if i["question"] == "Pertanyaan yang di-seed langsung"),
        None,
    )
    assert seeded is not None, "Item seeded tidak muncul di response history"
    assert seeded["answer"] == "Jawaban yang di-seed langsung"
    assert seeded["document_id"] == str(document.id)
    assert seeded["sources"][0]["text"] == "source-X"
    assert seeded["sources"][1]["text"] == "source-Y"


# ---------------------------------------------------------------------------
# TEST 3: Quota habis → 429 Too Many Requests, NLP tidak dipanggil
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guest_quota_exhausted_returns_429(seeded_user_and_doc, db_session):
    """
    Set quota = 0 di DB, pastikan endpoint mengembalikan 429
    dan NLP service tidak dipanggil sama sekali.
    """
    user, document = seeded_user_and_doc

    # Seed GuestQuota dengan sisa = 0
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO guest_quotas (user_id, remaining_quota) VALUES (:user_id, :remaining_quota)"
            ),
            {"user_id": user.id, "remaining_quota": 0},
        )

    nlp_was_called = False

    class _TrackingNLPClient:
        async def chat_document(self, **_kwargs):
            nonlocal nlp_was_called
            nlp_was_called = True
            return None

    auth_user = AuthUser(
        id=user.id, email=user.email, display_name=user.display_name, is_active=True
    )

    async def _override_current_user():
        return auth_user

    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_nlp_client] = lambda: _TrackingNLPClient()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/chat/{document.id}/message",
            json={"message": "cek quota habis"},
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.json()["detail"] == "Guest quota exhausted"
    assert nlp_was_called is False, "NLP tidak boleh dipanggil saat quota habis"


# ---------------------------------------------------------------------------
# TEST 4: Document milik user lain → 403 Forbidden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_forbidden_cross_user(db_session):
    """
    User A mencoba chat pada dokumen milik User B — harus 403.
    """
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        firebase_uid=f"firebase-a-{user_a_id}",
        email=f"user-a-{user_a_id}@legaleasier.test",
        display_name="User A",
        is_active=True,
    )
    user_b = User(
        id=user_b_id,
        firebase_uid=f"firebase-b-{user_b_id}",
        email=f"user-b-{user_b_id}@legaleasier.test",
        display_name="User B",
        is_active=True,
    )
    doc_b = Document(
        id=doc_id,
        owner_id=user_b_id,
        filename="kontrak_milik_b.pdf",
        storage_path=f"storage/test/{doc_id}.pdf",
        status="completed",
    )

    now = datetime.now(timezone.utc)

    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, firebase_uid, email, display_name, is_active, created_at) "
                "VALUES (:id, :firebase_uid, :email, :display_name, :is_active, :created_at)"
            ),
            {
                "id": user_a_id,
                "firebase_uid": user_a.firebase_uid,
                "email": user_a.email,
                "display_name": user_a.display_name,
                "is_active": user_a.is_active,
                "created_at": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO users (id, firebase_uid, email, display_name, is_active, created_at) "
                "VALUES (:id, :firebase_uid, :email, :display_name, :is_active, :created_at)"
            ),
            {
                "id": user_b_id,
                "firebase_uid": user_b.firebase_uid,
                "email": user_b.email,
                "display_name": user_b.display_name,
                "is_active": user_b.is_active,
                "created_at": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO documents (id, owner_id, filename, storage_path, status, created_at, updated_at) "
                "VALUES (:id, :owner_id, :filename, :storage_path, :status, :created_at, :updated_at)"
            ),
            {
                "id": doc_id,
                "owner_id": user_b_id,
                "filename": doc_b.filename,
                "storage_path": doc_b.storage_path,
                "status": doc_b.status,
                "created_at": now,
                "updated_at": now,
            },
        )

    auth_user_a = AuthUser(
        id=user_a_id, email=user_a.email, display_name="User A", is_active=True
    )

    async def _override_current_user():
        return auth_user_a

    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_nlp_client] = lambda: _FakeNLPClient()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/chat/{doc_id}/message",
            json={"message": "coba akses dokumen user lain"},
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    # Teardown manual karena tidak pakai fixture seeded_user_and_doc
    async with test_engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM documents WHERE id = :id"), {"id": doc_id}
        )
        await conn.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": user_a_id}
        )
        await conn.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": user_b_id}
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


# ---------------------------------------------------------------------------
# TEST 5: Document tidak ada → 404 Not Found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_document_not_found(seeded_user_and_doc, db_session):
    """
    Kirim pesan ke document_id yang tidak ada di DB — harus 404.
    """
    user, _ = seeded_user_and_doc
    nonexistent_doc_id = uuid.uuid4()

    async with _build_client(user) as client:
        response = await client.post(
            f"/api/v1/chat/{nonexistent_doc_id}/message",
            json={"message": "dokumen ini tidak ada"},
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


# ---------------------------------------------------------------------------
# TEST 6: Kirim 3 pesan berturut → quota berkurang bertahap, semua tersimpan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_messages_quota_decrements_and_all_persisted(
    seeded_user_and_doc, db_session
):
    """
    Kirim 3 pesan berturut-turut.
    Verifikasi: quota berkurang 5→4→3→2, dan semua 3 ChatMessage ada di DB.
    """
    user, document = seeded_user_and_doc

    questions = [
        "Apa isi pasal 1?",
        "Apa konsekuensi jika kontrak dilanggar?",
        "Bagaimana mekanisme penyelesaian sengketa?",
    ]

    for i, question in enumerate(questions):
        async with _build_client(user) as client:
            response = await client.post(
                f"/api/v1/chat/{document.id}/message",
                json={"message": question, "top_k": 3},
                headers={"Authorization": "Bearer inttest-token"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 200, (
            f"Pesan ke-{i + 1} gagal: {response.text}"
        )
        expected_quota = 5 - (i + 1)
        actual_quota = response.json()["data"]["remaining_quota"]
        assert actual_quota == expected_quota, (
            f"Pesan ke-{i + 1}: quota seharusnya {expected_quota}, dapat {actual_quota}"
        )

    # Verifikasi semua 3 ChatMessage benar-benar ada di PostgreSQL
    async with TestSessionLocal() as verify_session:
        result = await verify_session.execute(
            text(
                "SELECT COUNT(*) FROM chat_messages "
                "WHERE document_id = :doc_id AND user_id = :user_id"
            ),
            {"doc_id": document.id, "user_id": user.id},
        )
        count = result.scalar()

    assert count == 3, (
        f"Seharusnya 3 ChatMessage tersimpan, tapi hanya {count} yang ada di DB"
    )

    # Verifikasi quota akhir di DB = 2
    async with TestSessionLocal() as verify_session:
        result = await verify_session.execute(
            text(
                "SELECT remaining_quota FROM guest_quotas WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        )
        quota_row = result.fetchone()

    assert quota_row is not None
    assert quota_row.remaining_quota == 2


# ---------------------------------------------------------------------------
# TEST 7: GET history — document tidak ada → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_history_document_not_found(seeded_user_and_doc, db_session):
    """
    GET history untuk document_id yang tidak ada — harus 404.
    """
    user, _ = seeded_user_and_doc
    nonexistent_doc_id = uuid.uuid4()

    async with _build_client(user) as client:
        response = await client.get(
            f"/api/v1/chat/{nonexistent_doc_id}/history",
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


# ---------------------------------------------------------------------------
# TEST 8: GET history — document milik user lain → 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_history_forbidden_cross_user(db_session):
    """
    GET history untuk dokumen milik user lain — harus 403.
    """
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        firebase_uid=f"firebase-ha-{user_a_id}",
        email=f"hist-a-{user_a_id}@legaleasier.test",
        display_name="Hist User A",
        is_active=True,
    )
    user_b = User(
        id=user_b_id,
        firebase_uid=f"firebase-hb-{user_b_id}",
        email=f"hist-b-{user_b_id}@legaleasier.test",
        display_name="Hist User B",
        is_active=True,
    )
    doc_b = Document(
        id=doc_id,
        owner_id=user_b_id,
        filename="kontrak_hist_b.pdf",
        storage_path=f"storage/test/{doc_id}.pdf",
        status="completed",
    )

    now = datetime.now(timezone.utc)

    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, firebase_uid, email, display_name, is_active, created_at) "
                "VALUES (:id, :firebase_uid, :email, :display_name, :is_active, :created_at)"
            ),
            {
                "id": user_a_id,
                "firebase_uid": user_a.firebase_uid,
                "email": user_a.email,
                "display_name": user_a.display_name,
                "is_active": user_a.is_active,
                "created_at": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO users (id, firebase_uid, email, display_name, is_active, created_at) "
                "VALUES (:id, :firebase_uid, :email, :display_name, :is_active, :created_at)"
            ),
            {
                "id": user_b_id,
                "firebase_uid": user_b.firebase_uid,
                "email": user_b.email,
                "display_name": user_b.display_name,
                "is_active": user_b.is_active,
                "created_at": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO documents (id, owner_id, filename, storage_path, status, created_at, updated_at) "
                "VALUES (:id, :owner_id, :filename, :storage_path, :status, :created_at, :updated_at)"
            ),
            {
                "id": doc_id,
                "owner_id": user_b_id,
                "filename": doc_b.filename,
                "storage_path": doc_b.storage_path,
                "status": doc_b.status,
                "created_at": now,
                "updated_at": now,
            },
        )

    auth_user_a = AuthUser(
        id=user_a_id, email=user_a.email, display_name="Hist User A", is_active=True
    )

    async def _override_current_user():
        return auth_user_a

    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/chat/{doc_id}/history",
            headers={"Authorization": "Bearer inttest-token"},
        )

    app.dependency_overrides.clear()

    # Teardown
    async with test_engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM documents WHERE id = :id"), {"id": doc_id}
        )
        await conn.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": user_a_id}
        )
        await conn.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": user_b_id}
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"