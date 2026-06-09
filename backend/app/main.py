from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.chat import router as chat_router
from app.api.routes.guest import router as guest_router
from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# OpenAPI metadata
# ---------------------------------------------------------------------------

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Health check and readiness probes.",
    },
    {
        "name": "auth",
        "description": "Authentication — register, login, and current user.",
    },
    {
        "name": "documents",
        "description": "Document CRUD — upload, list, search, download, and delete.",
    },
    {
        "name": "analysis",
        "description": "Document analysis — risk scoring and clause extraction.",
    },
    {
        "name": "chat",
        "description": "RAG chatbot — ask questions about analysed documents.",
    },
    {
        "name": "guest",
        "description": "Guest quota — check remaining free analyses.",
    },
]

app = FastAPI(
    title="LegalEasier API",
    description=(
        "REST API for LegalEasier — an AI-powered platform that translates "
        "Indonesian legal documents into plain language.\n\n"
        "**Key features:**\n"
        "- Document upload and OCR extraction\n"
        "- AI-powered risk analysis and clause detection\n"
        "- RAG chatbot for document Q&A\n"
        "- Firebase authentication\n\n"
        "See [API_DOCS.md](https://github.com/IndraSugara/LegalEasier/blob/main/backend/API_DOCS.md) "
        "for full reference."
    ),
    version="0.6.0",
    contact={
        "name": "LegalEasier Team",
        "url": "https://github.com/IndraSugara/LegalEasier",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=OPENAPI_TAGS,
    debug=settings.debug,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(documents_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(analysis_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)
app.include_router(guest_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {
        "message": "LegalEasier backend is running",
        "version": "v0.6.0",
    }
