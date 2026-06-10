"""
Firebase Admin SDK initialization and utilities.

Requires a valid Firebase service account credentials file.
Set FIREBASE_CREDENTIALS_PATH in .env to the path of your credentials JSON file.
"""

import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_firebase_app = None


def initialize_firebase():
    """Initialize Firebase Admin SDK from credentials file.

    Raises:
        RuntimeError: If credentials file path is not set or file not found.
    """
    global _firebase_app

    if _firebase_app is not None:
        return

    settings = get_settings()
    creds_path = settings.firebase_credentials_path

    if not creds_path or not Path(creds_path).exists():
        raise RuntimeError(
            f"Firebase credentials file not found at '{creds_path}'. "
            "Set FIREBASE_CREDENTIALS_PATH in .env to the path of a valid "
            "Firebase service account JSON file."
        )

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
        Firebase app instance.

    Raises:
        RuntimeError: If Firebase cannot be initialized.
    """
    global _firebase_app
    if _firebase_app is None:
        initialize_firebase()
    return _firebase_app


async def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token claims.

    Args:
        token: Firebase ID token (without 'Bearer ' prefix)

    Returns:
        Decoded token claims including uid, email, etc.

    Raises:
        InvalidIdTokenError: Token is invalid or malformed
        ExpiredIdTokenError: Token has expired
        Exception: Other Firebase errors
    """
    app = get_firebase_app()

    # Production mode — real Firebase verification
    from firebase_admin import auth
    from firebase_admin.auth import (
        InvalidIdTokenError,
        ExpiredIdTokenError,
        ExpiredSessionCookieError,
    )

    try:
        logger.debug("verify_firebase_token: Attempting real Firebase verification (token length=%d)", len(token))
        decoded_token = auth.verify_id_token(token, app=app)
        logger.debug("verify_firebase_token: Token verified successfully - uid=%s", decoded_token.get("uid"))
        return decoded_token

    except (InvalidIdTokenError, ExpiredIdTokenError, ExpiredSessionCookieError) as e:
        logger.error("verify_firebase_token: Firebase token verification failed - error=%s (%s)",
                     str(e), type(e).__name__)
        raise
    except Exception as e:
        logger.error("verify_firebase_token: Unexpected error during Firebase token verification - error=%s (%s)",
                     str(e), type(e).__name__)
        raise
