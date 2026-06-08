"""
Shared FastAPI dependencies for auth, db, and other shared services.
"""

import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase import is_mock_mode, verify_firebase_token
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import AuthUser

logger = logging.getLogger(__name__)

# Fixed mock user ID for development (consistent across requests)
_MOCK_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async for session in get_db_session():
        yield session


async def _get_or_create_user_from_firebase_token(
    db: AsyncSession,
    firebase_uid: str,
    email: str | None,
    display_name: str | None,
) -> User:
    """Return the local user for a Firebase UID, creating or linking it if needed."""
    stmt = select(User).where(User.firebase_uid == firebase_uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        return user

    if not email:
        email = f"guest_{firebase_uid}@legaleasier.local"
        if not display_name:
            display_name = "Tamu"

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.firebase_uid = firebase_uid
        if display_name and not user.display_name:
            user.display_name = display_name
        await db.commit()
        await db.refresh(user)
        logger.info("Linked existing local user to Firebase UID: %s", firebase_uid)
        return user

    user = User(
        id=uuid.uuid4(),
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Auto-provisioned local user for Firebase UID: %s", firebase_uid)
    return user


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    """
    Verify Firebase Bearer token and return authenticated user from DB.
    
    Rules per CLAUDE.md Section 8:
    - All endpoints except /auth/* require Bearer JWT token
    - Token validation happens in deps.py get_current_user()
    - Firebase UID is stored in users table, used to link all data
    
    In MOCK_MODE (no Firebase credentials):
    - Any Bearer token is accepted
    - Returns a fixed mock user without DB lookup
    
    Args:
        authorization: Authorization header (expected format: "Bearer <token>")
        request: FastAPI request object
        db: Database session
    
    Returns:
        AuthUser: Authenticated user with id, email, display_name, is_active
    
    Raises:
        HTTPException: 401 if no token, invalid token, or user not found in DB
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        with open("deps_error.log", "a") as f:
            f.write("Error: Missing authorization header\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Parse Bearer token
    if not authorization.startswith("Bearer "):
        with open("deps_error.log", "a") as f:
            f.write(f"Error: Invalid format - {authorization}\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        # Verify Firebase token and extract claims
        decoded_token = await verify_firebase_token(token)
        
        # MOCK_MODE: return a mock user directly (no DB lookup needed)
        if is_mock_mode():
            logger.debug("MOCK_MODE: returning mock user for development")
            return AuthUser(
                id=_MOCK_USER_ID,
                email=decoded_token.get("email", "dev@legaleasier.local"),
                display_name=decoded_token.get("name", "Development User"),
                is_active=True,
                is_guest=True,
            )
        
        # Production: extract Firebase UID and ensure a matching local user exists.
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            logger.warning("Firebase token missing 'uid' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing uid claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = await _get_or_create_user_from_firebase_token(
            db=db,
            firebase_uid=firebase_uid,
            email=decoded_token.get("email"),
            display_name=decoded_token.get("name"),
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        return AuthUser.model_validate(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error verifying Firebase token: %s", e)
        with open("deps_error.log", "a") as f:
            f.write(f"Error: {repr(e)}\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

