"""
schemas_auth.py — Pydantic schemas for authentication.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserLogin(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class UserCreate(BaseModel):
    """Schema for user creation request."""
    name: str = Field(..., min_length=2, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    role: str = Field(default="employee", description="User role")
    employment_type: str = Field(default="full_time", description="Employment type")


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for JWT token data."""
    user_id: str
    email: str
    role: str
    exp: int


class UserInfo(BaseModel):
    """Schema for user information response."""
    id: str
    name: str
    email: str
    role: str
    employment_type: Optional[str] = None
    last_login: Optional[str] = None
    is_active: bool


class UserList(BaseModel):
    """Schema for user list response (admin only)."""
    users: list[UserInfo]


class PasswordChange(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User email for password reset")
