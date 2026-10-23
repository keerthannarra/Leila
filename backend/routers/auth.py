"""
auth.py — Authentication router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DBSession

from database import get_db
from services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user, create_access_token, verify_token, get_user_by_id,
    update_last_login, create_user, get_all_users, has_permission
)
from schemas_auth import UserLogin, Token, UserInfo, UserCreate, UserList, PasswordChange

router = APIRouter()
security = HTTPBearer()


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)], db: DBSession = Depends(get_db)) -> UserInfo:
    """Get current user from JWT token."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        token_data = verify_token(token)
        if token_data is None:
            raise credentials_error
            
        user = get_user_by_id(token_data.user_id)
        if user is None:
            raise credentials_error
            
        return UserInfo(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            employment_type=user.employment_type,
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active
        )
    except Exception:
        raise credentials_error


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_dependency(current_user: UserInfo = Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required for role '{current_user.role}'"
            )
        return current_user
    return permission_dependency


def require_role(required_roles: list[str]):
    """Decorator to require specific roles."""
    def role_dependency(current_user: UserInfo = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return current_user
    return role_dependency


# ---------------------------------------------------------------------------
# Authentication endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: DBSession = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = authenticate_user(user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    update_last_login(user.id)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/register", response_model=UserInfo)
def register(user_data: UserCreate, db: DBSession = Depends(get_db)):
    """Register a new user (admin only in production)."""
    user = create_user(
        name=user_data.name,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role,
        employment_type=user_data.employment_type
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    return UserInfo(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        employment_type=user.employment_type,
        last_login=user.last_login.isoformat() if user.last_login else None,
        is_active=user.is_active
    )


@router.get("/me", response_model=UserInfo)
def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.get("/users", response_model=UserList)
def get_users(current_user: UserInfo = Depends(require_role(["administrator", "it_operations_manager"]))):
    """Get all users (admin/manager only)."""
    users = get_all_users()
    user_infos = [
        UserInfo(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            employment_type=user.employment_type,
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active
        )
        for user in users
    ]
    
    return UserList(users=user_infos)


@router.post("/logout")
def logout():
    """Logout user (client-side token removal)."""
    return {"message": "Successfully logged out"}
