# LegalEasier

> Penerjemah dokumen hukum Indonesia ke bahasa yang lebih mudah dipahami.

LegalEasier membantu pengguna memahami isi dokumen hukum (kontrak kerja, sewa, perjanjian, dan dokumen serupa) dengan alur:
upload dokumen -> OCR -> preprocessing -> analisis AI -> ringkasan + deteksi klausul berisiko.

> Hasil analisis bersifat informatif dan edukatif, bukan pengganti nasihat hukum profesional.

## Status Proyek (per 23 Mei 2026)

| Sprint | Fokus | Status |
| --- | --- | --- |
| Sprint 1 | Fondasi backend, auth, OCR dasar, schema DB | Selesai |
| Sprint 2 | Upload dokumen, preprocessing, embedding, RAG storage | Selesai |
| Sprint 3 | Analisis risiko berbasis LLM + risk score | Selesai |
| Sprint 4 | Chatbot RAG end-to-end di app | Belum selesai |
| Sprint 5 | History, polishing UI/UX | Belum selesai |
| Sprint 6 | Hardening, deployment, optimization | Belum selesai |

## Update Terbaru

- Backend menyimpan file asli dokumen di PostgreSQL (`documents.file_content` / `bytea`) dan menyediakan download via endpoint file.
- Alur auth backend sudah berbasis Firebase token verification dengan auto-provision user lokal.
- Pemrosesan dokumen berjalan sebagai background task dengan retry ke NLP service.
- NLP pipeline sudah sampai analisis risiko + summary (Claude sebagai primary, NVIDIA NIM sebagai fallback).
- Endpoint analisis backend (`/documents/{id}/analysis`) sudah mengembalikan `summary`, `risk_score`, dan `risk_clauses`.

## Arsitektur

- `frontend/` -> Flutter app (Riverpod + GoRouter + Firebase Auth)
- `backend/` -> FastAPI REST API + SQLAlchemy async + PostgreSQL
- `nlp_pipeline/` -> FastAPI NLP microservice (OCR, preprocessing, RAG, LLM)
- `database/` -> artefak database/migrasi tambahan

## Struktur Direktori Ringkas

```text
LegalEasier/
|- frontend/
|- backend/
|  |- app/
|  |- alembic/
|  `- tests/
|- nlp_pipeline/
|  |- core/
|  |- ocr/
|  |- preprocessing/
|  |- rag/
|  |- llm/
|  `- tests/
|- database/
|- docker-compose.yml
`- README.md
```

## API Utama

Base URL Backend: `http://127.0.0.1:8000/api/v1`

- `GET /health`
- `GET /health/db`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/status`
- `GET /documents/{document_id}/text`
- `GET /documents/{document_id}/analysis`
- `GET /documents/{document_id}/file`
- `DELETE /documents/{document_id}`

Base URL NLP: `http://127.0.0.1:8001`

- `GET /health`
- `POST /ocr/extract`
- `POST /nlp/process`
- `POST /nlp/retrieve`
- `GET /nlp/info/{document_id}`
- `DELETE /nlp/{document_id}`

## Prasyarat

- Flutter SDK 3.x (Dart `>=3.2.0`)
- Python 3.11+
- PostgreSQL 16
- Tesseract OCR (Windows path default: `C:\Program Files\Tesseract-OCR\tesseract.exe`)

## Setup Lokal (Windows PowerShell)

### 1) Clone repository

```powershell
git clone https://github.com/Fiana-Wahyu-Laura/LegalEasier.git
cd LegalEasier
```

### 2) Siapkan environment file

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item nlp_pipeline\.env.example nlp_pipeline\.env
```

Catatan:

- Backend akan masuk `MOCK_MODE` untuk auth jika `FIREBASE_CREDENTIALS_PATH` tidak valid.
- Untuk flow register/login Firebase REST API di backend, isi `FIREBASE_WEB_API_KEY` di `backend/.env`.
- Untuk analisis LLM di NLP, isi minimal salah satu: `CLAUDE_API_KEY` atau `NIM_API_KEY` di `nlp_pipeline/.env`.

### 3) Jalankan PostgreSQL

Opsional via Docker:

```powershell
docker run --name legaleasier-db `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=password `
  -e POSTGRES_DB=legaleasier `
  -p 5432:5432 -d postgres:16-alpine
```

### 4) Jalankan backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 5) Jalankan NLP pipeline (terminal terpisah)

```powershell
cd nlp_pipeline
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download xx_ent_wiki_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords'); nltk.download('wordnet')"
uvicorn main:app --reload --port 8001
```

### 6) Jalankan frontend (terminal terpisah)

```powershell
cd frontend
flutter pub get
flutter run --dart-define=BACKEND_BASE_URL=http://127.0.0.1:8000
```

## Testing

Backend (contoh subset test yang dipakai di CI):

```powershell
cd backend
pytest tests/test_documents.py tests/test_nlp_contract.py -q
```

NLP pipeline:

```powershell
cd nlp_pipeline
pytest tests -v
```

## Catatan Implementasi Saat Ini

- Frontend untuk chat AI dan history dokumen masih tahap lanjutan (belum end-to-end).
- `docker-compose.yml` sudah ada, tetapi Dockerfile untuk service backend/NLP belum tersedia di repo ini.
- CI GitHub saat ini fokus ke backend test subset (`.github/workflows/backend-ci.yml`).

## Tim Pengembang

| Nama | NIM | Peran |
| --- | --- | --- |
| Ester Faninta | 2301020053 | Frontend (Flutter, Firebase Auth) |
| Fiana Wahyu Laura | 2301020082 | Frontend (Flutter, Firebase Auth) |
| Masry Ryzki Yanditar | 2301020087 | Backend (FastAPI, PostgreSQL, Storage) |
| Jamalludin | 2301020075 | Backend (FastAPI, PostgreSQL, Storage) |
| Indra Sugara | 2301020084 | NLP/AI (OCR, RAG, LLM, ChromaDB) |

## Mata Kuliah

Pemrograman Perangkat Mobile - Teknik Informatika  
Universitas Maritim Raja Ali Haji (2026)
