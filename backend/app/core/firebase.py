"""
Firebase Admin SDK initialization and utilities.

Supports two modes:
- PRODUCTION: Full Firebase token verification using service account credentials.
- MOCK_MODE: When FIREBASE_CREDENTIALS_PATH is not set or file not found,
  token verification is skipped and a mock user UID is returned.
  This allows development/testing without Firebase credentials.
"""

import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_firebase_app = None

# Sentinel value for mock mode (no credentials available)
MOCK_MODE = "MOCK_MODE"


def initialize_firebase():
    """Initialize Firebase Admin SDK from credentials file.

    If credentials are not found, sets mock mode flag instead of crashing.
    This allows local development without a Firebase service account.
    """
    global _firebase_app

    if _firebase_app is not None:
        return

    settings = get_settings()
    creds_path = settings.firebase_credentials_path

    if not creds_path or not Path(creds_path).exists():
        logger.warning(
            "Firebase credentials file not found at %s. "
            "Firebase Auth will be MOCKED for development/testing. "
            "For production, set FIREBASE_CREDENTIALS_PATH to valid credentials file.",
            creds_path,
        )
        # Set mock mode flag
        _firebase_app = MOCK_MODE
        return

    # Lazy import — only needed when credentials exist
    import firebase_admin
    from firebase_admin import credentials as fb_credentials

    try:
        creds = fb_credentials.Certificate(creds_path)
        _firebase_app = firebase_admin.initialize_app(creds)
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Firebase Admin SDK: %s", e)
        raise


def get_firebase_app():
    """Get Firebase app instance (initialize if needed).

    Returns:
        - Firebase app if credentials are configured
        - "MOCK_MODE" string if running in development mode without credentials
        - None should never happen (initialize always sets a value)
    """
    global _firebase_app
    if _firebase_app is None:
        initialize_firebase()
    return _firebase_app


def is_mock_mode() -> bool:
    """Check if Firebase is running in mock mode (no credentials)."""
    return get_firebase_app() == MOCK_MODE


async def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token claims.

    Args:
        token: Firebase ID token (without 'Bearer ' prefix)

    Returns:
        Decoded token claims including uid, email, etc.
        In MOCK_MODE: returns a mock claims dict with uid derived from token.

    Raises:
        InvalidIdTokenError: Token is invalid or malformed (production only)
        ExpiredIdTokenError: Token has expired (production only)
        Exception: Other Firebase errors
    """
    app = get_firebase_app()

    # Mock mode — skip real verification, return mock claims
    if app == MOCK_MODE:
        logger.debug("MOCK_MODE: skipping Firebase token verification")
        return {
            "uid": f"mock-uid-{token[:8]}",
            "email": "dev@legaleasier.local",
            "name": "Development User",
        }

    # Production mode — real Firebase verification
    from firebase_admin import auth
    from firebase_admin.auth import (
        InvalidIdTokenError,
        ExpiredIdTokenError,
        ExpiredSessionCookieError,
    )

    try:
        decoded_token = auth.verify_id_token(token, app=app)
        return decoded_token

    except (InvalidIdTokenError, ExpiredIdTokenError, ExpiredSessionCookieError) as e:
        logger.error("Firebase token verification failed: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error during Firebase token verification: %s", e)
        raise
