"""
actions.py — AutomatedAction CRUD router for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import AuditLog, AutomatedAction
from schemas import ActionApproveRequest, ActionCreate, ActionOut, ActionRejectRequest

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


def _action_to_schema(a: AutomatedAction) -> ActionOut:
    def _load(val):
        if val is None:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    return ActionOut(
        id=a.id,
        name=a.name,
        description=a.description,
        parameter_schema=_load(a.parameter_schema),
        eligibility_rule=_load(a.eligibility_rule),
        approval_required=a.approval_required,
        lifecycle_status=a.lifecycle_status,
        author_id=a.author_id,
        reviewer_id=a.reviewer_id,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /actions
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ActionOut])
def list_actions(
    lifecycle_status: Optional[str] = Query(None),
    db: DBSession = Depends(get_db),
):
    query = db.query(AutomatedAction)
    if lifecycle_status:
        query = query.filter(AutomatedAction.lifecycle_status == lifecycle_status)
    actions = query.order_by(AutomatedAction.created_at.desc()).all()
    return [_action_to_schema(a) for a in actions]


# ---------------------------------------------------------------------------
# GET /actions/{id}
# ---------------------------------------------------------------------------

@router.get("/{action_id}", response_model=ActionOut)
def get_action(action_id: str, db: DBSession = Depends(get_db)):
    action = db.query(AutomatedAction).filter(AutomatedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return _action_to_schema(action)


# ---------------------------------------------------------------------------
# POST /actions
# ---------------------------------------------------------------------------

@router.post("", response_model=ActionOut, status_code=201)
def create_action(payload: ActionCreate, db: DBSession = Depends(get_db)):
    now = _utcnow()
    action = AutomatedAction(
        id=_new_uuid(),
        name=payload.name,
        description=payload.description,
        parameter_schema=(
            json.dumps(payload.parameter_schema) if payload.parameter_schema else None
        ),
        eligibility_rule=(
            json.dumps(payload.eligibility_rule) if payload.eligibility_rule else None
        ),
        approval_required=payload.approval_required,
        lifecycle_status="draft",
        author_id=payload.author_id,
        created_at=now,
        updated_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    log_audit(
        db,
        "action_created",
        payload.author_id,
        {"action_id": action.id, "name": action.name},
    )

    return _action_to_schema(action)


# ---------------------------------------------------------------------------
# PUT /actions/{id}
# ---------------------------------------------------------------------------

@router.put("/{action_id}", response_model=ActionOut)
def update_action(
    action_id: str, payload: ActionCreate, db: DBSession = Depends(get_db)
):
    action = db.query(AutomatedAction).filter(AutomatedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.lifecycle_status == "published":
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a published action. Retire it first.",
        )

    action.name = payload.name
    action.description = payload.description
    action.parameter_schema = (
        json.dumps(payload.parameter_schema) if payload.parameter_schema else None
    )
    action.eligibility_rule = (
        json.dumps(payload.eligibility_rule) if payload.eligibility_rule else None
    )
    action.approval_required = payload.approval_required
    action.lifecycle_status = "pending_review"
    action.updated_at = _utcnow()
    db.commit()
    db.refresh(action)

    log_audit(
        db,
        "action_updated",
        payload.author_id,
        {"action_id": action_id},
    )

    return _action_to_schema(action)


# ---------------------------------------------------------------------------
# POST /actions/{id}/submit
# ---------------------------------------------------------------------------

@router.post("/{action_id}/submit", response_model=ActionOut)
def submit_action(action_id: str, db: DBSession = Depends(get_db)):
    action = db.query(AutomatedAction).filter(AutomatedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.lifecycle_status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft actions can be submitted for review.",
        )
    action.lifecycle_status = "pending_review"
    action.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "action_submitted_for_review",
        action.author_id,
        {"action_id": action_id},
    )
    return _action_to_schema(action)


# ---------------------------------------------------------------------------
# POST /actions/{id}/approve
# ---------------------------------------------------------------------------

@router.post("/{action_id}/approve", response_model=ActionOut)
def approve_action(
    action_id: str,
    payload: ActionApproveRequest,
    db: DBSession = Depends(get_db),
):
    action = db.query(AutomatedAction).filter(AutomatedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Block self-approval
    if action.author_id == payload.reviewer_id:
        raise HTTPException(
            status_code=403,
            detail="Self-approval is not permitted.",
        )

    if action.lifecycle_status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail="Action must be in 'pending_review' to approve.",
        )

    action.lifecycle_status = "published"
    action.reviewer_id = payload.reviewer_id
    action.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "action_approved",
        payload.reviewer_id,
        {"action_id": action_id},
    )
    return _action_to_schema(action)


# ---------------------------------------------------------------------------
# POST /actions/{id}/reject
# ---------------------------------------------------------------------------

@router.post("/{action_id}/reject", response_model=ActionOut)
def reject_action(
    action_id: str,
    payload: ActionRejectRequest,
    db: DBSession = Depends(get_db),
):
    action = db.query(AutomatedAction).filter(AutomatedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.lifecycle_status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail="Action must be in 'pending_review' to reject.",
        )

    action.lifecycle_status = "draft"
    action.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "action_rejected",
        payload.reviewer_id,
        {"action_id": action_id, "reason": payload.reason},
    )
    return _action_to_schema(action)


# ---------------------------------------------------------------------------
# POST /actions/{id}/retire
# ---------------------------------------------------------------------------

@router.post("/{action_id}/retire", response_model=ActionOut)
def retire_action(action_id: str, db: DBSession = Depends(get_db)):
    action = db.query(AutomatedAction).filter(AutomatedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    action.lifecycle_status = "retired"
    action.updated_at = _utcnow()
    db.commit()

    log_audit(
        db,
        "action_retired",
        None,
        {"action_id": action_id},
    )
    return _action_to_schema(action)
