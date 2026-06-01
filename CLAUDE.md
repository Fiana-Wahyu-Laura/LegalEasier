# CLAUDE.md — LegalEasier

## 1. Project Overview

- Name : LegalEasier
- Description : AI-powered mobile app that translates Indonesian legal documents into plain language
- Goal : Help everyday Indonesians understand contracts, rental agreements, and other legal documents without a law background
- Target Users : General public (non-lawyers), young workers, students — Indonesian speakers
- Version : v0.1.0
- Status : Active development

---

## 2. Tech Stack

### Mobile Frontend (`/frontend`)

- Language : Dart
- Framework : Flutter 3.x
- State Mgmt : Riverpod 2.x
- Navigation : go_router
- HTTP Client : Dio
- Auth : Firebase Auth (Google + Email/Password)
- Package Mgr : pub (flutter pub)

### Backend API (`/backend`)

- Language : Python 3.11
- Framework : FastAPI
- ORM : SQLAlchemy 2.x (async)
- Database : PostgreSQL 16
- File Storage : PostgreSQL (bytea column) — served via GET /documents/{id}/file
- Auth : Firebase Admin SDK + JWT
- Package Mgr : pip (with virtualenv)
- Deployment : Railway / Render

### NLP Pipeline (`/nlp_pipeline`)

- Language : Python 3.11
- Framework : FastAPI (runs as separate microservice on port 8001)
- OCR : PyMuPDF + Tesseract OCR
- NLP : SpaCy + NLTK
- Chunking : LangChain Text Splitter (512 tokens, overlap 50)
- Embeddings : sentence-transformers (all-MiniLM-L6-v2)
- Vector DB : ChromaDB
- RAG : LangChain + LangGraph
- LLM : Claude API (primary), GPT-4 API (fallback)
- Package Mgr : pip (with virtualenv — SEPARATE from backend)

---

## 3. Commands

### Flutter Frontend

```bash
flutter pub get              # Install dependencies
flutter run                  # Run on connected device/emulator
flutter build apk            # Build Android APK
flutter build appbundle      # Build Android App Bundle
flutter analyze              # Static analysis
flutter test                 # Run all tests
flutterfire configure        # Re-configure Firebase
```

### FastAPI Backend

```bash
# Always activate venv first (Windows)
venv\Scripts\activate

uvicorn app.main:app --reload --port 8000   # Dev server
uvicorn app.main:app --port 8000            # Production
alembic upgrade head                         # Run DB migrations
alembic revision --autogenerate -m "msg"    # Create new migration
pip install -r requirements.txt             # Install dependencies
```

### NLP Pipeline

```bash
# Always activate its OWN venv (separate from backend)
venv\Scripts\activate

uvicorn main:app --reload --port 8001       # Dev server
pip install -r requirements.txt             # Install dependencies
pytest tests/ -v                            # Run all unit tests
pytest tests/test_ocr_extractor.py -v      # Run OCR tests only
python -m spacy download xx_ent_wiki_sm     # Download SpaCy model (first time only)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"  # First time only
```

> NEVER mix the backend and nlp_pipeline virtual environments. They must be separate.
> On Windows, Tesseract must be installed at C:\Program Files\Tesseract-OCR\ and added to PATH.

---

## 4. Project Structure

Architecture: Clean Architecture per feature (frontend), layered microservices (backend + NLP)

```
legaleasier/
├── frontend/                        # Flutter app
│   ├── lib/
│   │   ├── core/
│   │   │   ├── constants/           # App-wide constants (colors, strings, endpoints)
│   │   │   ├── theme/               # AppTheme, color tokens, text styles
│   │   │   └── utils/               # Shared helpers (formatters, validators)
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   │   ├── data/            # AuthRepository impl, Firebase calls
│   │   │   │   ├── domain/          # AuthRepository interface, User entity
│   │   │   │   └── presentation/    # LoginScreen, RegisterScreen, providers
│   │   │   ├── document/
│   │   │   │   ├── data/            # DocumentRepository impl, API calls
│   │   │   │   ├── domain/          # Document entity, repository interface
│   │   │   │   └── presentation/    # HomeScreen, UploadSheet, HistoryScreen
│   │   │   ├── analysis/
│   │   │   │   ├── data/
│   │   │   │   ├── domain/          # AnalysisResult, RiskClause entities
│   │   │   │   └── presentation/    # DetailScreen, RiskCard, ScoreWidget
│   │   │   └── chatbot/
│   │   │       ├── data/
│   │   │       ├── domain/
│   │   │       └── presentation/    # ChatScreen, MessageBubble, SuggestionChips
│   │   └── main.dart
│   ├── test/
│   ├── android/app/google-services.json   # DO NOT commit — add to .gitignore
│   └── pubspec.yaml
│
├── backend/                         # FastAPI server (port 8000)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/              # auth.py, documents.py, analysis.py, chat.py
│   │   │   └── deps.py              # Shared FastAPI dependencies (get_db, get_current_user)
│   │   ├── core/
│   │   │   ├── config.py            # Settings from .env via pydantic-settings
│   │   │   ├── security.py          # JWT utils
│   │   │   └── firebase.py          # Firebase Admin SDK init
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   └── main.py
│   ├── alembic/                     # DB migration files
│   ├── requirements.txt
│   └── .env.example
│
├── nlp_pipeline/                    # NLP microservice (port 8001)
│   ├── core/
│   │   └── config.py                # Settings from .env via pydantic-settings
│   ├── ocr/
│   │   ├── pdf_extractor.py         # PyMuPDF extraction (digital PDF)
│   │   └── image_ocr.py             # Tesseract OCR (scan PDF & images)
│   ├── preprocessing/
│   │   ├── cleaner.py               # Text normalization for Indonesian legal text
│   │   ├── tokenizer.py             # SpaCy tokenization
│   │   └── splitter.py              # Sentence splitting
│   ├── rag/
│   │   ├── chunker.py               # LangChain splitter (512 tokens, overlap 50)
│   │   ├── embedder.py              # sentence-transformers embeddings
│   │   ├── vector_store.py          # ChromaDB operations
│   │   └── retriever.py             # Semantic search for RAG
│   ├── llm/
│   │   ├── analyzer.py              # Risk clause detection & classification
│   │   ├── translator.py            # Plain language translation per clause
│   │   └── risk_scorer.py           # 0-100 risk score generation
│   ├── tests/
│   │   └── test_ocr_extractor.py    # Unit tests for OCR pipeline (Sprint 1)
│   ├── main.py                      # FastAPI entry point (port 8001)
│   ├── schemas.py                   # Pydantic request/response schemas
│   ├── requirements.txt
│   └── .env.example
│
├── database/
│   ├── schema.sql                   # Full DB schema (source of truth)
│   └── migrations/
│
├── .gitignore
├── docker-compose.yml
└── README.md
```

File placement rules:

- New Flutter screen → `features/<feature>/presentation/`
- New Flutter entity/model → `features/<feature>/domain/`
- New Flutter API call → `features/<feature>/data/`
- New FastAPI endpoint → `backend/app/api/routes/<domain>.py`
- New SQLAlchemy model → `backend/app/models/`
- New NLP processing step → appropriate subfolder in `nlp_pipeline/`
- Do NOT create new top-level folders without confirmation

---

## 5. Naming Conventions

```
# Flutter / Dart
- Screen files       : PascalCase    HomeScreen.dart, LoginScreen.dart
- Widget files       : PascalCase    RiskCard.dart, ScoreWidget.dart
- Provider files     : camelCase     authProvider.dart, documentProvider.dart
- Utility files      : camelCase     formatDate.dart, validateEmail.dart
- Folders            : snake_case    auth/, document/, risk_card/

# Inside Dart code
- Variables          : camelCase     documentList, isLoading
- Constants          : UPPER_SNAKE   MAX_FILE_SIZE_MB, BASE_URL
- Classes            : PascalCase    AnalysisResult, RiskClause
- Enums              : PascalCase    RiskLevel, DocumentStatus

# Python (Backend + NLP)
- Files              : snake_case    document_service.py, risk_scorer.py
- Classes            : PascalCase    DocumentService, RiskClause
- Functions          : snake_case    get_document_by_id(), extract_text()
- Constants          : UPPER_SNAKE   MAX_CHUNK_SIZE, CHROMA_COLLECTION_NAME
- Variables          : snake_case    raw_text, risk_score

# API Routes
- Resources          : plural nouns  /documents, /users, /analysis
- Kebab-case URLs    :               /chat-sessions, /risk-clauses
- No verbs in URL    :               POST /documents (not POST /upload-document)

# Git Branches
- New feature        : feat/frontend-login, feat/nlp-ocr-pipeline
- Bug fix            : fix/upload-crash, fix/risk-score-nan
- Refactor           : refactor/document-repository
- Hotfix             : hotfix/firebase-auth-token
```

---

## 6. Code Conventions

```
# General
- Apply DRY — if logic is used more than once, extract it
- Prefer readability over cleverness
- Every function should do one thing

# Dart / Flutter
- Use const constructors wherever possible
- Never use BuildContext across async gaps without checking mounted
- Use final for all variables that don't change
- Prefer early return over deeply nested if-else
- All Dio calls must be wrapped in try-catch

# Python
- Use type hints on all function signatures
- Never use bare except — always specify exception type
- Use async/await for all database and HTTP operations
- Pydantic models for all request and response schemas — no raw dicts
- Config values must come from Settings class (pydantic-settings), never hardcoded

# Import Order (Python)
1. Standard library
2. Third-party packages
3. Internal modules (relative imports)

# Error Handling
- FastAPI: return proper HTTP status codes (400, 401, 403, 404, 500)
- Never expose stack traces or internal error details in API responses
- Flutter: show user-friendly Indonesian error messages
- LLM errors must be caught — never let a failed LLM call crash the pipeline

# LLM Prompts
- All prompts live in dedicated files (llm/prompts.py or similar)
- Always include disclaimer in every LLM output:
  "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional."
- Always include confidence score in risk analysis output
```

---

## 7. Flutter Widget Rules

```
# Widget file structure order
1. Imports
2. Class declaration
3. final fields / constructor
4. State (if StatefulWidget): variables, initState, dispose
5. Build method
6. Private helper methods / sub-widgets

# Riverpod
- Use ConsumerWidget or ConsumerStatefulWidget (never manual Provider.of)
- One provider file per feature
- AsyncNotifier for providers with async operations
- Never put business logic inside the build() method

# Screen vs Widget
- "Screen" = full page navigated to via go_router
- "Widget" = reusable component used inside screens
- If a widget is only used in one screen, it can live in the same file

# UI Text
- All user-facing strings in Indonesian
- No hardcoded colors — use AppTheme tokens
- Risk levels must use color coding: Tinggi=red, Sedang=orange, Rendah=green, Aman=green

# Async in UI
- Always show loading indicator during async operations
- Always show error state with retry option
- Never leave a Future unhandled
```

---

## 8. API Design Rules

```
# Consistent Response Format
All endpoints must return:
{
  "success": true/false,
  "data": <T> | null,
  "message": "descriptive message"
}

# Document Upload Flow (critical path)
POST /documents/upload
  → Backend receives file bytes (multipart)
  → Backend saves file bytes to PostgreSQL (documents.file_data bytea)
  → Backend calls NLP service POST /nlp/process (multipart — kirim file bytes langsung)
  → NLP: OCR → preprocess → chunk → embed → store in ChromaDB
  → NLP: LLM analysis → returns JSON result
  → Backend saves result to PostgreSQL
  → Backend returns analysis to Flutter

# File Download
GET /documents/{document_id}/file
  → Hanya untuk user yang memiliki dokumen tersebut (cek ownership di deps.py)
  → Return file bytes dengan Content-Type yang sesuai
  → Jangan expose endpoint ini secara publik

# Auth
- All endpoints except /auth/* require Bearer JWT token
- Token validation happens in deps.py get_current_user()
- Firebase UID is stored in users table, used to link all data

# File Upload Limits
- Max file size: 20MB
- Accepted types: PDF, JPG, PNG, DOCX
- Validate on both Flutter (before upload) and Backend (on receive)

# Pagination
- List endpoints must support: ?page=1&limit=20
- Default limit: 20, max limit: 100
```

---

## 9. NLP Pipeline Rules

```
# Processing Order (never skip steps)
1. OCR / text extraction
2. Cleaning & normalization (Indonesian legal text quirks)
3. Tokenization & sentence splitting
4. Chunking: 512 tokens, overlap 50
5. Embedding with all-MiniLM-L6-v2
6. Store vectors in ChromaDB (collection named after document UUID)
7. LLM analysis (risk detection, plain language, summary, score)
8. Return structured JSON to backend

# ChromaDB
- One collection per document, named: "doc_{document_uuid}"
- Delete collection when document is deleted
- Never share collections between documents

# LLM Calls
- Always use RAG context — never ask LLM about document without providing chunks
- System prompt must include: language (Indonesian), format (JSON), disclaimer instruction
- Validate LLM JSON output before saving — retry once on parse error
- Risk levels: "Tinggi", "Sedang", "Rendah", "Aman" (no other values)
- Risk score range: 0-100 (integer, higher = riskier)

# OCR
- Try PyMuPDF first (faster, for digital PDFs)
- Fall back to Tesseract only if PyMuPDF returns empty/garbled text
- Set flag ocr_used=True in document_texts if Tesseract was used
```

---

## 10. Database Rules

```
# PostgreSQL
- All IDs are UUID (uuid_generate_v4())
- All timestamps use TIMESTAMP DEFAULT NOW()
- Always use CASCADE on foreign key deletes
- Never delete records permanently — add deleted_at column if soft delete needed

# Migrations
- Use Alembic for all schema changes
- Never edit schema.sql directly without also creating an Alembic migration
- Migration files must have descriptive names: 002_add_risk_clauses_table.py

# Sensitive Data
- Never log or return raw document text in API responses unless explicitly requested
- File bytes (bytea) hanya boleh diakses via GET /documents/{id}/file — jangan return raw bytes di response JSON lain
- User email must not appear in logs

# File Storage (PostgreSQL bytea)
- Kolom file_data bertipe BYTEA — jangan gunakan TEXT atau VARCHAR untuk binary data
- Selalu set Content-Type header yang benar saat serving file (application/pdf, image/jpeg, dst)
- Dokumen yang dihapus: set deleted_at, file_data boleh di-nullify untuk hemat storage
```

---

## 11. Security Rules

```
# Never do this
- Never hardcode API keys, database URLs, or secrets anywhere in code
- Never commit .env files (add to .gitignore immediately)
- Never log JWT tokens, API keys, or user passwords
- Never expose Firebase credentials JSON to the frontend
- Never skip input validation on file uploads

# Firebase credentials files — NEVER commit
- android/app/google-services.json
- ios/Runner/GoogleService-Info.plist
- backend/firebase-credentials.json

# Environment variables only
- CLAUDE_API_KEY
- DATABASE_URL
- FIREBASE_CREDENTIALS_PATH
- SECRET_KEY
- NLP_SERVICE_URL
```

---

## 12. Git Rules

```
# Commit message format
feat     : add OCR pipeline with PyMuPDF fallback to Tesseract
fix      : resolve null pointer on empty document upload
refactor : extract risk score logic into dedicated scorer module
style    : fix trailing whitespace in analysis screen
docs     : update CLAUDE.md with NLP pipeline rules
test     : add unit tests for risk clause parser
chore    : upgrade sentence-transformers to 2.7.0

# Branch naming
feat/frontend-onboarding
feat/backend-document-upload
feat/nlp-ocr-extractor
feat/nlp-rag-chatbot
fix/upload-file-validation
refactor/auth-repository

# Rules
- Never commit directly to main — always use a feature branch + PR
- Never commit .env, google-services.json, or firebase-credentials.json
- One logical change per commit
- Always pull latest main before starting a new branch
```

---

## 13. Features

```
# Sprint 1 — Completed
- [x] Flutter: Onboarding & Splash screen
- [x] Flutter: Login & Register (Firebase Auth)
- [x] Backend: /auth/register, /auth/login endpoints
- [x] NLP: OCR extraction (PyMuPDF + Tesseract)
- [x] Database: Initial schema setup

# Sprint 2 — Completed
- [x] Flutter: Home/Dashboard screen
- [x] Flutter: Upload & Scan document (bottom sheet)
- [x] Backend: /documents/upload endpoint
- [x] NLP: Preprocessing pipeline (SpaCy + NLTK)
- [x] NLP: Chunking & embedding to ChromaDB

# Sprint 3 — In progress
- [x] NLP: LLM risk analysis + plain language translation
- [x] Backend: /analysis/{document_id} endpoint
- [x] Flutter: Document detail & risk analysis screen

# Sprint 4 — In progress
- [x] NLP: RAG chatbot (LangGraph + ChromaDB)
- [x] Backend: /chat/{document_id}/message endpoint
- [x] Flutter: AI Chat screen with suggestion chips
- [x] Flutter: Limit gate (guest mode 5 free analyses)

# Sprint 5 — In progress
- [x] Flutter: Document history screen with search & filter
- [x] UI polish pass (all screens) — initial polish applied to Chat and Document screens; further visual refinements planned

# Sprint 6 — In progress
- [ ] Full integration testing
- [ ] Performance optimization
- [ ] API documentation
```

---

## 14. Testing

```
# Approach
- Flutter  : Widget tests for critical screens, unit tests for providers
- Backend  : Unit tests for service layer, integration tests for API routes
- NLP      : Unit tests for each pipeline step (OCR, cleaner, chunker, scorer)

# Priority order
1. NLP risk scorer (most critical logic)
2. FastAPI document upload & analysis routes
3. Flutter auth flow (login/register)
4. Flutter document upload & analysis display

# Test file naming
- Flutter  : test/features/auth/login_screen_test.dart
- Python   : tests/test_risk_scorer.py, tests/test_ocr_extractor.py

# What NOT to test
- Firebase SDK calls (mock them)
- LLM API responses (mock them)
- ChromaDB internals
```

---

## 15. Do Not

If a prompt is ambiguous, ASK before coding. Never assume.

```
# Structure
- Do not create new top-level folders without confirmation
- Do not move or rename existing files without confirmation
- Do not change the Clean Architecture layer structure in Flutter

# Code
- Do not hardcode any API keys, URLs, or secrets
- Do not mix backend and nlp_pipeline virtual environments
- Do not use synchronous database calls in FastAPI (always async)
- Do not call the LLM API without RAG context (always use retrieved chunks)
- Do not install new packages without confirmation

# Flutter specific
- Do not use setState in a screen that should use Riverpod
- Do not use BuildContext after an async gap without checking mounted
- Do not use hardcoded Indonesian strings outside of a future l10n setup

# LLM / AI
- Do not let the app present LLM output as legal advice
- Do not skip the disclaimer on any AI-generated result
- Do not cache LLM responses without invalidating on document update

# Database
- Do not run destructive SQL (DROP, TRUNCATE, DELETE without WHERE) without confirmation
- Do not create Alembic migrations without confirming schema changes
- Do not expose raw PostgreSQL errors to the API client
```

---

## 16. Environment Variables

```
# Never commit any .env file. Copy .env.example → .env to get started.

# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/legaleasier
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
CLAUDE_API_KEY=                    # From console.anthropic.com
OPENAI_API_KEY=                    # Fallback LLM
SECRET_KEY=                        # Random 32-char string for JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
NLP_SERVICE_URL=http://localhost:8001

# nlp_pipeline/.env
CLAUDE_API_KEY=
OPENAI_API_KEY=
CHROMA_PERSIST_DIR=./chroma_db
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe   # Windows path

# frontend — set in lib/core/constants/app_constants.dart
# Only non-secret values (base URL). Never put API keys in Flutter code.
const backendBaseUrl = 'http://10.0.2.2:8000';   # Android emulator localhost
```

---

## 17. Team & Ownership

| Area                                              | Folder           | Penanggung Jawab                 |
| ------------------------------------------------- | ---------------- | -------------------------------- |
| Flutter UI, Firebase Auth                         | `/frontend/`     | Ester Faninta, Fiana Wahyu Laura |
| FastAPI, PostgreSQL, File Storage, Deployment     | `/backend/`      | Masry Ryzki Yanditar, Jamalludin |
| NLP, OCR, RAG, LLM, ChromaDB                     | `/nlp_pipeline/` | Indra Sugara                      |

```
# Perubahan ownership akibat migrasi Firebase Storage → PostgreSQL (per 3 Mei 2026):
- Firebase Storage DIHAPUS dari stack
- Frontend (Ester/Fiana): TIDAK perlu integrasi Firebase Storage SDK — upload file
  cukup kirim multipart ke backend, selesai
- Backend (Masry/Jamal): BERTANGGUNG JAWAB PENUH atas file storage:
    → Simpan file bytes ke kolom file_data BYTEA di tabel documents
    → Sediakan GET /documents/{id}/file untuk serving file ke Flutter
    → Baca bytes dari DB lalu kirim ke NLP service sebagai multipart

# Rules
- Sebelum mengubah file di luar area ownership-mu, konfirmasi ke pemiliknya lebih dulu
- Perubahan pada API contract (request/response schema) HARUS disepakati bersama
  sebelum diimplementasi — jangan unilateral
- Jika ada konflik atau dependency antar area, komunikasikan ke seluruh tim
- Pull request yang menyentuh folder di luar ownership-mu wajib di-review
  oleh pemilik folder tersebut sebelum di-merge
```

---

## 18. API Contracts (Source of Truth)

Kontrak ini harus disepakati sebelum Sprint 2 dimulai. Jangan ubah field name atau
struktur tanpa koordinasi antar pihak terkait.

### Frontend ↔ Backend

Semua endpoint mengikuti format standar (lihat Section 8).
Perubahan pada response schema harus dikomunikasikan ke Frontend Dev sebelum di-push ke main.

### Backend ↔ NLP Service

```
# POST /nlp/process
# Request (Backend → NLP): multipart/form-data
# CATATAN: file_url dihapus — file dikirim langsung sebagai bytes (Firebase Storage tidak digunakan)
document_id : uuid-string
file_type   : "pdf" | "jpg" | "png" | "docx"
file        : <binary file bytes — dibaca dari PostgreSQL bytea oleh backend>

# Response (NLP → Backend): application/json
{
  "document_id": "uuid-string",
  "ocr_used": false,
  "full_text": "teks lengkap dokumen...",
  "summary": "ringkasan singkat dokumen dalam bahasa Indonesia...",
  "risk_score": 72,
  "risk_clauses": [
    {
      "clause_text": "teks asli klausul...",
      "plain_language": "penjelasan dalam bahasa sederhana...",
      "risk_level": "Tinggi" | "Sedang" | "Rendah" | "Aman",
      "confidence": 0.91
    }
  ],
  "disclaimer": "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional."
}

# Aturan kontrak ini:
- Jangan ubah field name tanpa koordinasi Backend (Masry/Jamal) + NLP (Indra)
- Jika ada field baru, tambahkan sebagai optional (nullable) dulu — jangan breaking change
- risk_level hanya boleh salah satu dari: "Tinggi", "Sedang", "Rendah", "Aman"
- risk_score harus integer antara 0-100
- confidence harus float antara 0.0-1.0
- disclaimer wajib selalu ada — tidak boleh null atau kosong
- file dikirim sebagai multipart — JANGAN encode base64 (boros bandwidth & memory)
```

### Dependency Antar Tim

```
Frontend (Ester, Fiana)
    │
    │  memanggil REST API
    ▼
Backend (Masry, Jamal)
    │
    │  memanggil NLP service internal
    ▼
NLP / AI (Indra)
```

```
# Implikasi dependency ini:
- Sprint 1 bisa full paralel — tidak ada dependency langsung antar tim
- Mulai Sprint 2: Backend dan NLP harus sepakat format /nlp/process SEBELUM coding
- Mulai Sprint 2: Backend dan Frontend harus sepakat response format endpoint
  /documents/upload SEBELUM Frontend mulai integrasi
- Jika NLP service belum siap, Backend wajib menyediakan mock response
  agar Frontend tidak terblokir
```
