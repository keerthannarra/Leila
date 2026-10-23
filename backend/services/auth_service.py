"""
auth_service.py — Authentication service for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import bcrypt as _bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from database import SessionLocal
from models import User

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 30)))


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str
    exp: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email, User.is_active == True).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify JWT token and return token data."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        exp: int = payload.get("exp")
        
        if user_id is None or email is None or role is None:
            return None
            
        # Check if token is expired
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        if exp < current_time.timestamp():
            return None
            
        return TokenData(
            user_id=user_id,
            email=email,
            role=role,
            exp=exp
        )
    except JWTError:
        return None


def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID."""
    with SessionLocal() as db:
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()


def update_last_login(user_id: str) -> bool:
    """Update user's last login timestamp."""
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
                db.commit()
                return True
            return False
    except Exception:
        return False


def create_user(name: str, email: str, password: str, role: str = "employee", employment_type: str = "full_time") -> Optional[User]:
    """Create a new user."""
    try:
        with SessionLocal() as db:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return None
            
            # Create new user
            hashed_password = get_password_hash(password)
            new_user = User(
                name=name,
                email=email,
                password_hash=hashed_password,
                role=role,
                employment_type=employment_type
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return new_user
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


def get_all_users() -> list[User]:
    """Get all users for admin purposes."""
    with SessionLocal() as db:
        return db.query(User).filter(User.is_active == True).all()


def validate_role_access(user_role: str, required_roles: list[str]) -> bool:
    """Check if user role has access to required functionality."""
    return user_role in required_roles


# Role-based access control configuration
ROLE_PERMISSIONS = {
    "employee": [
        "chat_access", "view_own_profile"
    ],
    "it_support_agent": [
        "chat_access", "escalation_management", "escalation_assign", 
        "view_own_profile", "escalation_resolve"
    ],
    "it_content_owner": [
        "chat_access", "content_management", "content_approval",
        "view_own_profile", "article_create", "article_edit"
    ],
    "it_operations_lead": [
        "chat_access", "escalation_management", "content_management",
        "view_own_profile", "analytics_view", "escalation_assign", "escalation_resolve"
    ],
    "it_operations_manager": [
        "chat_access", "escalation_management", "content_management",
        "analytics_view", "user_management", "system_config",
        "escalation_assign", "escalation_resolve"
    ],
    "resource_owner": [
        "chat_access", "resource_management", "view_own_profile"
    ],
    "administrator": [
        "chat_access", "escalation_management", "content_management",
        "analytics_view", "user_management", "system_config",
        "resource_management", "compliance_review", "escalation_assign", "escalation_resolve"
    ],
    "compliance_reviewer": [
        "chat_access", "compliance_review", "analytics_view", "view_own_profile"
    ]
}


def has_permission(user_role: str, permission: str) -> bool:
    """Check if user role has specific permission."""
    return permission in ROLE_PERMISSIONS.get(user_role, [])
