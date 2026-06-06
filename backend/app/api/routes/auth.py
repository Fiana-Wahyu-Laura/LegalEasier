"""
Authentication API routes.
Endpoints for user auth and profile management.
Per CLAUDE.md Section 8: All endpoints except /auth/* require Bearer JWT token.

Token flow:
- Register: Create Firebase user → sign in via REST API → get ID token → return ID token
- Login: Sign in via Firebase REST API → get ID token → return ID token
- Protected endpoints: Send ID token as "Bearer <id_token>" → verify_id_token() in deps.py
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.auth import AuthUser, AuthRegisterRequest, AuthLoginRequest, AuthTokenResponse
from app.schemas.common import StandardResponse
from app.models.user import User
from app.core.config import get_settings
from app.core.firebase import get_firebase_app, is_mock_mode, MOCK_MODE
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Firebase Auth REST API endpoint
FIREBASE_SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIREBASE_SIGN_UP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp"


async def _firebase_sign_in_with_password(email: str, password: str) -> dict:
    """
    Sign in with email/password via Firebase Auth REST API.
    
    Returns dict with idToken, refreshToken, localId, etc.
    Raises HTTPException on failure.
    """
    settings = get_settings()
    api_key = settings.firebase_web_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase Web API Key not configured. Set FIREBASE_WEB_API_KEY in .env",
        )
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FIREBASE_SIGN_IN_URL,
            params={"key": api_key},
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
            timeout=10.0,
        )
    
    if response.status_code != 200:
        error_data = response.json().get("error", {})
        error_message = error_data.get("message", "UNKNOWN_ERROR")
        logger.warning("Firebase sign-in failed: %s", error_message)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    return response.json()


async def _firebase_sign_up_with_password(email: str, password: str) -> dict:
    """
    Create user with email/password via Firebase Auth REST API.
    
    Returns dict with idToken, refreshToken, localId, etc.
    Raises HTTPException on failure.
    """
    settings = get_settings()
    api_key = settings.firebase_web_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase Web API Key not configured. Set FIREBASE_WEB_API_KEY in .env",
        )
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FIREBASE_SIGN_UP_URL,
            params={"key": api_key},
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
            timeout=10.0,
        )
    
    if response.status_code != 200:
        error_data = response.json().get("error", {})
        error_message = error_data.get("message", "UNKNOWN_ERROR")
        logger.warning("Firebase sign-up failed: %s", error_message)
        
        if "EMAIL_EXISTS" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        if "WEAK_PASSWORD" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak (minimum 6 characters)",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )
    
    return response.json()


@router.post("/register", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: AuthRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """
    Register a new user account.
    
    Flow:
    1. Check if email exists in local DB
    2. Create user in Firebase Auth (via REST API)
    3. Create user in local PostgreSQL
    4. Return the ID token (ready to use as Bearer token)
    
    Raises:
        400: Password too weak
        409: Email already registered
    """
    try:
        # Check if email already exists in local DB
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        
        app = get_firebase_app()
        
        if app == MOCK_MODE:
            # Development mode: generate mock data
            firebase_uid = f"mock-{uuid.uuid4().hex[:24]}"
            id_token = f"mock-id-token-{firebase_uid}"
            logger.info("MOCK_MODE: Creating user with UID %s", firebase_uid)
        else:
            # Production: create user via Firebase REST API (returns ID token directly)
            firebase_response = await _firebase_sign_up_with_password(
                request.email, request.password,
            )
            firebase_uid = firebase_response["localId"]
            id_token = firebase_response["idToken"]
        
        # Create user in local database
        new_user = User(
            id=uuid.uuid4(),
            firebase_uid=firebase_uid,
            email=request.email,
            display_name=request.display_name,
            is_active=True,
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        token_response = AuthTokenResponse(
            user=AuthUser.model_validate(new_user),
            token=id_token,
        )
        return StandardResponse(
            success=True,
            data=token_response.model_dump(mode="json"),
            message="Registration successful.",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Registration error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=StandardResponse)
async def login(
    request: AuthLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """
    Login with email and password.
    
    Flow:
    1. Verify email/password via Firebase Auth REST API (returns ID token)
    2. Look up user in local DB
    3. Return the ID token (ready to use as Bearer token)
    
    The returned token can be used directly as:
        Authorization: Bearer <token>
    
    Raises:
        401: Invalid email or password
        403: User account is inactive
    """
    try:
        app = get_firebase_app()
        
        if app == MOCK_MODE:
            # Development mode: skip password verification
            stmt = select(User).where(User.email == request.email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )
            
            id_token = f"mock-id-token-{user.firebase_uid}"
            logger.info("MOCK_MODE: Login for %s", request.email)
        else:
            # Production: verify email/password via Firebase REST API
            # This returns a real Firebase ID token that verify_id_token() can validate
            firebase_response = await _firebase_sign_in_with_password(
                request.email, request.password,
            )
            id_token = firebase_response["idToken"]
            
            # Look up user in local DB
            stmt = select(User).where(User.email == request.email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        token_response = AuthTokenResponse(
            user=AuthUser.model_validate(user),
            token=id_token,
        )
        return StandardResponse(
            success=True,
            data=token_response.model_dump(mode="json"),
            message="Login successful.",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.get("/me", response_model=StandardResponse)
async def get_me(
    authorization: str = Header(..., description="Bearer token"),
    current_user: AuthUser = Depends(get_current_user),
) -> StandardResponse:
    """
    Get current authenticated user profile.
    
    Requires: Bearer token (Firebase ID token)
    
    Response per CLAUDE.md Section 8:
    - id: UUID of user
    - email: Email address
    - display_name: Optional display name
    - is_active: Account status
    """
    return StandardResponse(
        success=True,
        data=current_user.model_dump(mode="json"),
        message="User profile retrieved.",
    )
