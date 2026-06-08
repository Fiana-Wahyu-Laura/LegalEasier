"""
Shared FastAPI dependencies for auth, db, and other shared services.
"""

import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import or_, select
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
    device_id: str | None = None,
) -> User:
    """Return the local user for a Firebase UID, creating or linking it if needed.
    
    For anonymous users with device_id:
    - If device_id exists → reuse the user (device session persistence)
    - If device_id doesn't exist → create new user with device_id
    """
    logger.debug("Looking up user for Firebase UID: %s, device_id: %s", firebase_uid, device_id)
    
    # First check: existing user with same firebase_uid
    stmt = select(User).where(User.firebase_uid == firebase_uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        logger.info("Found existing user with Firebase UID: %s", firebase_uid)
        changed = False
        if email and user.is_guest and user.email != email:
            user.email = email
            changed = True
        if display_name and not user.display_name:
            user.display_name = display_name
            changed = True
        # Update device_id if provided and not already set
        if device_id and not user.device_id:
            user.device_id = device_id
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
            logger.info("Linked device_id to existing user: %s → %s", firebase_uid, device_id)
        return user

    # For guests (anonymous): check if device_id already exists
    # This allows restoring previous anonymous session
    if device_id and not email:  # Guest user detection
        logger.debug("Checking for existing guest session with device_id: %s", device_id)
        stmt = (
            select(User)
            .where(User.device_id == device_id)
            .where(
                or_(
                    User.firebase_uid.ilike("anonymous:%"),
                    User.email.ilike("guest_%@legaleasier.local"),
                )
            )
        )
        result = await db.execute(stmt)
        existing_guest = result.scalar_one_or_none()
        
        if existing_guest:
            # Reuse existing guest user, just update firebase_uid for new session
            logger.info("Reusing existing guest session for device_id: %s (old_uid: %s, new_uid: %s)",
                       device_id, existing_guest.firebase_uid, firebase_uid)
            existing_guest.firebase_uid = firebase_uid
            await db.commit()
            await db.refresh(existing_guest)
            return existing_guest

    # For guests (no email), generate one
    if not email:
        email = f"guest_{firebase_uid}@legaleasier.local"
        if not display_name:
            display_name = "Tamu"
        logger.info("Generated guest email: %s", email)

    # Second check: existing user with same email (for linking)
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Link existing user to Firebase UID
        user.firebase_uid = firebase_uid
        if display_name and not user.display_name:
            user.display_name = display_name
        if device_id and not user.device_id:
            user.device_id = device_id
        await db.commit()
        await db.refresh(user)
        logger.info("Linked existing user (id=%s) to Firebase UID: %s, device_id: %s", 
                    user.id, firebase_uid, device_id)
        return user

    # Create new user
    user = User(
        id=uuid.uuid4(),
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name or "User",
        device_id=device_id,  # Store device_id for future session linking
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Auto-provisioned new user (id=%s) for Firebase UID: %s, email: %s, device_id: %s", 
                user.id, firebase_uid, email, device_id)
    return user


async def get_current_user(
    authorization: str = Header(None),
    x_device_id: str = Header(None),
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
        x_device_id: Optional device ID for linking anonymous sessions
        db: Database session
    
    Returns:
        AuthUser: Authenticated user with id, email, display_name, is_active
    
    Raises:
        HTTPException: 401 if no token, invalid token, or user not found in DB
    """
    if not authorization:
        logger.error("get_current_user: Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Parse Bearer token
    if not authorization.startswith("Bearer "):
        logger.error("get_current_user: Invalid authorization format (not Bearer): %s...", authorization[:20])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    logger.debug("get_current_user: Attempting to verify token (length=%d, device_id=%s)", len(token), x_device_id)
    
    try:
        # Verify Firebase token and extract claims
        decoded_token = await verify_firebase_token(token)
        logger.debug("get_current_user: Token verified successfully, uid=%s", decoded_token.get("uid"))
        
        # MOCK_MODE: return a mock user directly (no DB lookup needed)
        if is_mock_mode():
            logger.info("get_current_user: MOCK_MODE - returning mock user")
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
            logger.error("get_current_user: Firebase token missing 'uid' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing uid claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug("get_current_user: Firebase UID: %s", firebase_uid)
        user = await _get_or_create_user_from_firebase_token(
            db=db,
            firebase_uid=firebase_uid,
            email=decoded_token.get("email"),
            display_name=decoded_token.get("name"),
            device_id=x_device_id,  # Pass device_id for linking
        )
        logger.info("get_current_user: User authenticated - id=%s, email=%s, device_id=%s, is_guest=%s", 
                    user.id, user.email, user.device_id, user.is_active)
        
        if not user.is_active:
            logger.warning("get_current_user: User account is inactive - id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        return AuthUser.model_validate(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_current_user: Error verifying Firebase token: %s (type=%s)", e, type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

