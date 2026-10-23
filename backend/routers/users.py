"""
users.py — User management router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AuditLog, User
from schemas import UserCreate, UserOut

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def log_audit(
    db: DBSession,
    event_type: str,
    actor_id: Optional[str],
    event_details: dict,
) -> None:
    entry = AuditLog(
        id=_new_uuid(),
        event_type=event_type,
        actor_id=actor_id,
        event_details=json.dumps(event_details),
        data_classification_tag="Internal",
        timestamp=_utcnow(),
    )
    db.add(entry)
    db.commit()


def _user_to_schema(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        name=u.name,
        email=u.email,
        role=u.role,
        employment_type=u.employment_type,
        manager_id=u.manager_id,
        created_at=u.created_at,
    )


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

@router.get("", response_model=List[UserOut])
def list_users(db: DBSession = Depends(get_db)):
    users = db.query(User).order_by(User.created_at).all()
    return [_user_to_schema(u) for u in users]


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------

@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: DBSession = Depends(get_db)):
    # Check for duplicate email
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A user with email '{payload.email}' already exists.",
        )

    valid_roles = (
        "employee",
        "it_support_agent",
        "it_content_owner",
        "it_operations_lead",
        "it_operations_manager",
        "resource_owner",
        "administrator",
        "compliance_reviewer",
    )
    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{payload.role}'. Valid roles: {valid_roles}",
        )

    user = User(
        id=_new_uuid(),
        name=payload.name,
        email=payload.email,
        role=payload.role,
        employment_type=payload.employment_type,
        manager_id=payload.manager_id,
        created_at=_utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit(
        db,
        "user_created",
        None,
        {"user_id": user.id, "role": user.role, "email": user.email},
    )

    return _user_to_schema(user)


# ---------------------------------------------------------------------------
# GET /users/{id}
# ---------------------------------------------------------------------------

@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_schema(user)
