"""
Authentication schemas.
"""

import uuid
from pydantic import BaseModel, EmailStr, Field


class AuthUser(BaseModel):
    """Authenticated user response schema."""
    id: uuid.UUID
    email: str
    display_name: str | None = None
    is_active: bool
    is_guest: bool = False

    class Config:
        from_attributes = True


class AuthRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    display_name: str | None = Field(None, description="Optional display name")


class AuthLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AuthTokenResponse(BaseModel):
    """Authentication response with user and token."""
    user: AuthUser
    token: str = Field(..., description="Firebase custom token for authentication")
